"""Check Genesis GPU physics and EGL camera in WSL2 before recording."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))
import genesis as gs
from PIL import Image
import torch

os.chdir(ROOT)
gs.init(backend=gs.gpu, logging_level="warning")
print("Genesis initialized:", gs.backend, "device:", gs.device, flush=True)
if str(gs.device).startswith("cpu"):
    raise RuntimeError("GPU unavailable to Genesis. Set LD_LIBRARY_PATH=/usr/lib/wsl/lib.")
scene = gs.Scene(show_viewer=False, sim_options=gs.options.SimOptions(dt=0.01),
                 vis_options=gs.options.VisOptions(show_world_frame=False, plane_reflection=False))
scene.add_entity(gs.morphs.Plane())
cube = scene.add_entity(gs.morphs.Box(pos=(0, 0, 0.4), size=(0.1, 0.1, 0.1)),
                        surface=gs.surfaces.Default(color=(0.9, 0.2, 0.1, 1)))
cam = scene.add_camera(res=(640, 480), pos=(1, -1, 0.8), lookat=(0, 0, 0.1), fov=40, GUI=False)
scene.build()
print("Genesis environment scene built", flush=True)
for _ in range(100):
    scene.step()
image = cam.render()[0]
(ROOT / "outputs").mkdir(exist_ok=True)
Image.fromarray(image).save(ROOT / "outputs/genesis_environment.png")
print("Genesis:", gs.__version__, "PyTorch:", torch.__version__, "GPU:", torch.cuda.get_device_name(0),
      "cube_z:", cube.get_pos().cpu().tolist()[2], "camera:", image.shape)
