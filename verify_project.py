"""Verify physical presses, robot provenance, and actual video decoding."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent


def main(account=None):
    out = ROOT / "outputs"
    summary = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    video = out / "demo.mp4"
    reader = imageio.get_reader(video)
    meta = reader.get_meta_data()
    indices = [0, 140, 360, 720, 1080, 1439]
    selected = [np.asarray(reader.get_data(i)) for i in indices]
    reader.close()
    decoded = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(video), "-f", "null", "-"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    folder = ROOT / "assets/so101"
    provenance = json.loads((folder / "source_manifest.json").read_text(encoding="utf-8"))
    hashes_match = True
    for item in provenance["files"]:
        local = item["source"].removeprefix("Simulation/SO101/")
        if local == "README.md":
            local = "UPSTREAM_README.md"
        hashes_match &= hashlib.sha256((folder / local).read_bytes()).hexdigest() == item["sha256"]
    original = ET.parse(folder / "so101_new_calib.urdf").getroot()
    derived = ET.parse(folder / "so101_press_probe.urdf").getroot()
    limits_original = {e.attrib["name"]: e.find("limit").attrib for e in original.findall("joint") if e.find("limit") is not None}
    limits_derived = {e.attrib["name"]: e.find("limit").attrib for e in derived.findall("joint") if e.find("limit") is not None}
    reports = [ROOT / f"説明資料_PAI最終課題_{account}.pdf"] if account else list(ROOT.glob("説明資料_PAI最終課題_*.pdf"))
    required = ["run_demo.py", "color_ai.py", "arm_control.py", "prepare_model.py", "fetch_so101.py", "build_report.py",
                "package_project.py", "record_demo.bat", "run_wsl.sh", "requirements.txt", "requirements-lock.txt", "README.md", "scene_assets.py", "video_ui.py",
                "THIRD_PARTY.md", "models/color_model.json", "assets/so101/LICENSE"]
    scans = summary["camera_classifications"]
    joint_array = np.array([s["joint_positions"] for s in summary["joint_samples"]])
    checks = {
        "actual_simulator_is_genesis": summary["simulator"] == "Genesis" and summary["genesis_version"] == "0.3.3",
        "gpu_backend_used": summary["requested_backend"] == "gpu" and "A2000" in summary["gpu"] and "cuda" in summary["device"],
        "genesis_camera_used": "Genesis" in summary["renderer"],
        "urdf_fk_agrees_with_genesis": summary["max_urdf_fk_vs_genesis_error_m"] < 0.003,
        "task_succeeded": summary["success"] and summary["returned_to_home"],
        "press_order_matches_color_request": summary["pressed_colors"] == summary["request"],
        "camera_3_colors_correct": len(scans) == 3 and all(s["prediction"] == s["ground_truth_for_validation"] for s in scans),
        "all_buttons_physically_depressed": all(d > 0.004 for d in summary["max_press_depth_m"]),
        "presses_have_probe_contact": len(summary["physical_press_events"]) == 3 and all(summary["probe_contact_observed"]),
        "no_unexpected_arm_button_contact": not summary["unexpected_arm_button_contacts"],
        "joint_limits_respected": summary["max_joint_limit_error_rad"] < 0.02,
        "arm_actually_moved": bool(np.max(np.ptp(joint_array, axis=0)) > 0.3),
        "original_so101_files_match_pinned_hashes": bool(hashes_match),
        "official_joint_limits_preserved": limits_original == limits_derived,
        "so101_has_five_arm_axes_and_gripper": len(limits_original) == 6,
        "video_between_60_180_seconds": 60 <= meta["duration"] <= 180,
        "video_72_seconds_1x": abs(meta["duration"] - summary["simulation_seconds"]) < 0.1 and summary["video_frames"] == 1440,
        "video_720p_h264_20fps": tuple(meta["size"]) == (1280, 720) and meta["codec"] == "h264" and meta["fps"] == 20,
        "video_all_frames_decode": decoded.returncode == 0 and not decoded.stderr.strip(),
        "scene_changes_with_motion": float(np.abs(selected[2][106:650, :922].astype(float) - selected[3][106:650, :922]).mean()) > 0.2,
        "pdf_present": bool(reports) and all(p.is_file() and p.read_bytes().startswith(b"%PDF") for p in reports),
        "required_files_present": all((ROOT / f).is_file() for f in required),
    }
    alt_path = out / "check_alternate/run_summary.json"
    if alt_path.exists():
        alt = json.loads(alt_path.read_text(encoding="utf-8"))
        checks["alternate_color_order_works"] = alt["success"] and alt["pressed_colors"] == ["blue", "red", "green"]
    montage = Image.new("RGB", (960, 885), "#eef2f5")
    draw = ImageDraw.Draw(montage)
    for i, (frame, index) in enumerate(zip(selected, indices)):
        x, y = i % 2 * 480, i // 2 * 295
        montage.paste(Image.fromarray(frame).resize((480, 270)), (x, y+25))
        draw.text((x+8, y+5), f"t = {index / meta['fps']:.2f} sec", fill="#142d3d")
    montage.save(out / "video_contact_sheet.png")
    result = {"passed": all(checks.values()), "checks": checks,
              "video": {"duration_seconds": meta["duration"], "fps": meta["fps"], "codec": meta["codec"],
                        "size": list(meta["size"]), "bytes": video.stat().st_size},
              "simulator": summary["simulator"], "genesis_version": summary["genesis_version"], "gpu": summary["gpu"],
              "pdf_files": [p.name for p in reports], "ffmpeg_decode_error": decoded.stderr.strip()}
    (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", help="検証する説明PDFのOmniCampusアカウント名")
    main(parser.parse_args().account)
