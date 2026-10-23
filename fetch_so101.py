"""Fetch a pinned official SO-101 follower model and required meshes only."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
COMMIT = "a758567c3978dfeefe282ede0500085a48fe8f78"
BASE = f"https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/{COMMIT}/"


def download(relative):
    request = urllib.request.Request(BASE + relative, headers={"User-Agent": "SO101-simulation-project"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main():
    folder = ROOT / "assets/so101"
    folder.mkdir(parents=True, exist_ok=True)
    original = download("Simulation/SO101/so101_new_calib.urdf")
    (folder / "so101_new_calib.urdf").write_bytes(original)
    meshes = sorted({element.attrib["filename"] for element in ET.fromstring(original).iter("mesh")})
    remote = ["Simulation/SO101/" + name for name in meshes] + ["LICENSE", "Simulation/SO101/README.md"]
    manifest = [{"source": "Simulation/SO101/so101_new_calib.urdf", "sha256": hashlib.sha256(original).hexdigest()}]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        data = list(pool.map(download, remote))
    for name, payload in zip(remote, data):
        local = name.removeprefix("Simulation/SO101/")
        if name == "LICENSE":
            local = "LICENSE"
        elif name.endswith("README.md"):
            local = "UPSTREAM_README.md"
        target = folder / local
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        manifest.append({"source": name, "sha256": hashlib.sha256(payload).hexdigest()})
    (folder / "source_manifest.json").write_text(json.dumps({
        "repository": "https://github.com/TheRobotStudio/SO-ARM100", "commit": COMMIT,
        "license": "Apache-2.0", "files": manifest, "modified": False,
    }, indent=2), encoding="utf-8")
    print(f"Downloaded official SO-101 follower URDF and {len(meshes)} meshes")


if __name__ == "__main__":
    main()
