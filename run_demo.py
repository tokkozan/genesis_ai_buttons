"""Run SO-101 color-button inspection in Genesis GPU physics, with actual camera frames."""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

import genesis as gs
import imageio.v2 as imageio
import numpy as np
from PIL import Image
import torch

from arm_control import ArmKinematics, JOINT_NAMES
from color_ai import ColorAI, LABELS, train
from prepare_model import prepare
from scene_assets import STATIONS, create_button_file
from video_ui import JAPANESE, compose

DT, FPS = 0.01, 20


def as_numpy(tensor):
    return tensor.detach().cpu().numpy()


def camera_patch(camera, station):
    # Fixed top-down camera: known panel geometry determines the ROI, not its color.
    pixels = camera.render()[0]
    depth = 0.40 - 0.04
    scale = 240 / (2 * depth * math.tan(math.radians(40 / 2)))
    x = round(160 - station["xy"][1] * scale)
    y = round(120 - (station["xy"][0] - 0.20) * scale)
    return pixels, pixels[y-3:y+3, x-3:x+3], [x, y]


def run(args):
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    urdf = prepare()
    metrics = train(ROOT / "models/color_model.json", ROOT / "models/training_metrics.json")
    ai = ColorAI(ROOT / "models/color_model.json")
    solver = ArmKinematics(urdf)
    gs.init(backend=gs.gpu if args.backend == "gpu" else gs.cpu, logging_level="warning", seed=41)
    if args.backend == "gpu" and str(gs.device).startswith("cpu"):
        raise RuntimeError("Genesis fell back to CPU. Set LD_LIBRARY_PATH=/usr/lib/wsl/lib before running.")
    print("Genesis backend:", gs.backend, "device:", gs.device, flush=True)
    scene = gs.Scene(show_viewer=args.gui,
                     sim_options=gs.options.SimOptions(dt=DT, substeps=2, gravity=(0, 0, -9.81)),
                     rigid_options=gs.options.RigidOptions(enable_self_collision=False),
                     viewer_options=gs.options.ViewerOptions(camera_pos=(0.75, -0.65, 0.53), camera_lookat=(0.12, 0, 0.09), camera_fov=34),
                     vis_options=gs.options.VisOptions(show_world_frame=False, plane_reflection=False, ambient_light=(0.4, 0.4, 0.4)))
    scene.add_entity(gs.morphs.Box(pos=(0.1, 0, -0.013), size=(1, 0.72, 0.02), fixed=True),
                     surface=gs.surfaces.Default(color=(0.83, 0.87, 0.90, 1)))
    arm = scene.add_entity(gs.morphs.URDF(file=urdf, fixed=True, links_to_keep=["press_tip"],
                                         prioritize_urdf_material=True, default_armature=0.01))
    buttons = [scene.add_entity(gs.morphs.URDF(file=create_button_file(s, ROOT), pos=(*s["xy"], 0),
                                               fixed=True, prioritize_urdf_material=True, default_armature=0.0001)) for s in STATIONS]
    for station in STATIONS:
        scene.add_entity(gs.morphs.Sphere(pos=(station["xy"][0]+0.065, station["xy"][1], 0.015), radius=0.007, fixed=True, collision=False),
                         surface=gs.surfaces.Default(color=(0.25, 0.30, 0.35, 1)))
    main_camera = scene.add_camera(res=(922, 614), pos=(0.75, -0.65, 0.53), lookat=(0.12, 0, 0.09), fov=34, GUI=False)
    top_camera = scene.add_camera(res=(320, 240), pos=(0.20, 0, 0.40), lookat=(0.20, 0, 0.035), up=(1, 0, 0), fov=40, GUI=False)
    print("Building Genesis GPU scene (first run compiles kernels)...", flush=True)
    scene.build()
    print("Genesis scene built", flush=True)
    motor_indices = [arm.get_joint(n).dofs_idx_local[0] for n in JOINT_NAMES]
    gripper_index = arm.get_joint("gripper").dofs_idx_local[0]
    tip = arm.get_link("press_tip")
    limits_lower, limits_upper = [as_numpy(t) for t in arm.get_dofs_limit(motor_indices)]
    arm.set_dofs_kp(np.array([120, 120, 120, 80, 50]), motor_indices)
    arm.set_dofs_kv(np.array([8, 8, 8, 5, 3]), motor_indices)
    arm.set_dofs_force_range(np.array([-2]*5), np.array([2]*5), motor_indices)
    arm.set_dofs_kp(np.array([20]), [gripper_index])
    arm.set_dofs_kv(np.array([1]), [gripper_index])
    arm.control_dofs_position(np.array([0]), [gripper_index])
    for button in buttons:
        button.set_dofs_kp(np.array([100]))
        button.set_dofs_kv(np.array([1]))
        button.set_dofs_force_range(np.array([-0.8]), np.array([0.8]))
        button.control_dofs_position(np.array([0]))
    home = solver.solve([0.16, 0, 0.055])
    arm.set_dofs_position(home, motor_indices)  # initial configuration only
    arm.control_dofs_position(home, motor_indices)
    for _ in range(100):
        scene.step()
    fk_xyz = solver.pose(home)[0]
    genesis_xyz = as_numpy(tip.get_pos())
    fk_error = float(np.linalg.norm(fk_xyz-genesis_xyz))
    print(f"Initial TCP vs URDF FK error: {fk_error:.5f}m", flush=True)
    request = args.colors.split(",")
    if sorted(request) != sorted(LABELS):
        raise ValueError("Specify red,green,blue once each; order may vary")
    scans, sequence, completed, events, samples, moves = [], [], [], [], [], None
    sensor, roi = None, [160, 120]
    max_depth, contact_seen, unexpected = [0.0]*3, [False]*3, set()
    max_limit_error, max_fk_disagreement = 0.0, fk_error
    last_stage, move_start_q, move_goal, stage_start = None, home.copy(), home.copy(), 0.0
    writer, frame_count, started = None, 0, time.monotonic()
    if args.record:
        writer = imageio.get_writer(out / "demo.mp4", fps=FPS, codec="libx264", quality=8, pixelformat="yuv420p", macro_block_size=16, ffmpeg_log_level="error")
    try:
        for step in range(72*100):
            elapsed = step*DT
            command, selected = home.copy(), None
            phase, status = "intro", "準備：色で検査順序を指定"
            if 3 <= elapsed < 9:
                phase, status = "scan", "Genesisカメラで色を確認"
                scan_index = min(2, int((elapsed-3)//2))
                if len(scans) <= scan_index:
                    station = STATIONS[scan_index]
                    sensor, patch, roi = camera_patch(top_camera, station)
                    color, prob, rgb = ai.predict(patch)
                    scans.append({"station": station["id"], "prediction": color, "probability": prob,
                                  "mean_camera_rgb": rgb, "camera_roi_center": roi, "ground_truth_for_validation": station["color"]})
                    Image.fromarray(sensor).save(out / f"camera_{station['id']}.png")
                    print(f"Genesis camera AI {station['id']}: {color} ({prob:.3f})", flush=True)
            if elapsed >= 9 and moves is None:
                mapping = {s["prediction"]: i for i, s in enumerate(scans)}
                if len(mapping) != 3:
                    raise RuntimeError("Camera AI did not recognize three distinct colors")
                sequence = [mapping[c] for c in request]
                moves = [(solver.solve([*STATIONS[i]["xy"], 0.060]), solver.solve([*STATIONS[i]["xy"], args.press_z])) for i in sequence]
                print("AI selected order:", sequence, flush=True)
            if 9 <= elapsed < 63:
                cycle, local = int((elapsed-9)//18), (elapsed-9)%18
                selected, color = sequence[cycle], request[cycle]
                hover, press = moves[cycle]
                if local < 5:
                    stage, duration, goal = 0, 5, hover
                    phase, status = "approach", f"{JAPANESE[color]}ボタンの上へ移動"
                elif local < 9:
                    stage, duration, goal = 1, 4, press
                    phase, status = "press", f"{JAPANESE[color]}ボタンを押す"
                elif local < 12:
                    stage, duration, goal = 2, 3, press
                    phase, status = "hold", "接触・押し込み量を確認"
                elif local < 15:
                    stage, duration, goal = 3, 3, hover
                    phase, status = "retract", "ボタンから先端を離す"
                else:
                    stage, duration, goal = 4, 3, home
                    phase, status = "return", "待機位置へ戻る"
                if last_stage != (cycle, stage):
                    move_start_q = as_numpy(arm.get_dofs_position(motor_indices))
                    move_goal, stage_start, last_stage = goal, elapsed, (cycle, stage)
                u = min(1, (elapsed-stage_start)/duration)
                command = move_start_q + u*u*(3-2*u)*(move_goal-move_start_q)
            elif elapsed >= 63:
                phase = "finish"
                status = "成功：3色の検査ボタンを押下" if len(completed) == 3 else "未完了：実行結果を確認"
            arm.control_dofs_position(command, motor_indices)
            scene.step()
            # Inspect real Genesis joint displacements and contact forces at 20 Hz.
            if step % 5 == 0:
                depths = []
                for index, button in enumerate(buttons):
                    depth = max(0.0, -float(button.get_dofs_position()[0].item()))
                    depths.append(depth)
                    max_depth[index] = max(max_depth[index], depth)
                    contact = arm.get_contacts(with_entity=button)
                    link_a, link_b = as_numpy(contact["link_a"]), as_numpy(contact["link_b"])
                    forces = np.linalg.norm(as_numpy(contact["force_a"]), axis=-1)
                    mask = ((link_a == tip.idx) | (link_b == tip.idx)) & (forces > 0.01)
                    if mask.any():
                        contact_seen[index] = True
                    if depth > 0.004 and mask.any() and index not in completed:
                        completed.append(index)
                        events.append({"event": "genesis_physical_press", "station": STATIONS[index]["id"], "color": STATIONS[index]["color"],
                                       "time": round(elapsed, 3), "depth_m": depth, "normal_force_n": float(forces[mask].max())})
                        print(f"Genesis physical press {STATIONS[index]['color']} at {elapsed:.2f}s, {depth*1000:.1f}mm", flush=True)
                    for a, b, force in zip(link_a, link_b, forces):
                        if force > 0.2 and a != tip.idx and b != tip.idx:
                            unexpected.add((index, int(a), int(b)))
                joint_q = as_numpy(arm.get_dofs_position(motor_indices))
                max_limit_error = max(max_limit_error, float(np.max(np.maximum(np.maximum(limits_lower-joint_q, joint_q-limits_upper), 0))))
                actual_tip = as_numpy(tip.get_pos())
                max_fk_disagreement = max(max_fk_disagreement, float(np.linalg.norm(actual_tip-solver.pose(joint_q)[0])))
                if step % 10 == 0:
                    samples.append({"time": round(elapsed, 2), "tip_position": actual_tip.tolist(), "joint_positions": joint_q.tolist()})
                if writer is not None or step in [0, 1800, 6600]:
                    frame = compose(main_camera.render()[0], elapsed, status, request, scans, sensor, completed,
                                    depths[selected] if selected is not None else 0, roi)
                    if writer is not None:
                        writer.append_data(frame)
                        frame_count += 1
                    if step in [0, 1800, 6600]:
                        Image.fromarray(frame).save(out / {0:"start.png",1800:"simulation.png",6600:"success.png"}[step])
            if args.gui:
                time.sleep(DT)
            if step % 2000 == 0:
                print(f"Genesis simulation {elapsed:.0f}s: {phase}", flush=True)
        final_q = as_numpy(arm.get_dofs_position(motor_indices))
        result = {"success": completed == sequence and max_limit_error < 0.02 and not unexpected,
                  "request": request, "pressed_colors": [STATIONS[i]["color"] for i in completed],
                  "camera_classifications": scans, "training": metrics, "physical_press_events": events,
                  "max_press_depth_m": max_depth, "probe_contact_observed": contact_seen,
                  "unexpected_arm_button_contacts": list(unexpected), "max_joint_limit_error_rad": max_limit_error,
                  "max_urdf_fk_vs_genesis_error_m": max_fk_disagreement,
                  "returned_to_home": float(np.max(np.abs(final_q-home))) < 0.03,
                  "simulation_seconds": 72, "video_seconds": frame_count/FPS if args.record else None, "video_frames": frame_count, "video_fps": FPS,
                  "joint_samples": samples, "simulator": "Genesis", "genesis_version": importlib.metadata.version("genesis-world"),
                  "backend": str(gs.backend), "device": str(gs.device), "requested_backend": args.backend, "torch_version": torch.__version__,
                  "gpu": torch.cuda.get_device_name(0) if args.backend == "gpu" else None, "renderer": "Genesis Rasterizer via EGL",
                  "robot": "official SO-101 follower with fixed press probe", "playback_speed": "1x simulation time",
                  "wall_time_seconds": round(time.monotonic()-started, 2),
                  "limitations": ["Known button coordinates", "Fixed image ROI", "Synthetic color data", "Virtual press probe", "No real hardware calibration"]}
        result["success"] = result["success"] and result["returned_to_home"]
        (out / "run_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k:result[k] for k in ["success", "simulator", "genesis_version", "gpu", "pressed_colors", "max_press_depth_m", "unexpected_arm_button_contacts"]}, ensure_ascii=False), flush=True)
        if not result["success"]:
            raise RuntimeError("Genesis physical button task failed; inspect run_summary.json")
    finally:
        if writer is not None:
            writer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--backend", choices=["gpu", "cpu"], default="gpu")
    parser.add_argument("--colors", default="red,green,blue")
    parser.add_argument("--press-z", type=float, default=0.040)
    parser.add_argument("--output", default=str(ROOT / "outputs"))
    run(parser.parse_args())
