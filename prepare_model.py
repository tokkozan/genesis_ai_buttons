"""Keep the official model unchanged; derive a URDF with a small press probe."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


def prepare():
    folder = ROOT / "assets/so101"
    original = folder / "so101_new_calib.urdf"
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    robot = ET.parse(original, parser=parser).getroot()
    # Append a 25 mm probe to the original TCP; official joints are unchanged.
    probe = ET.SubElement(robot, "link", name="press_tip")
    inertial = ET.SubElement(probe, "inertial")
    ET.SubElement(inertial, "mass", value="0.015")
    ET.SubElement(inertial, "inertia", ixx="0.000002", iyy="0.000002", izz="0.000002", ixy="0", ixz="0", iyz="0")
    visual = ET.SubElement(probe, "visual")
    geometry = ET.SubElement(visual, "geometry")
    ET.SubElement(geometry, "sphere", radius="0.009")
    material = ET.SubElement(visual, "material", name="probe")
    ET.SubElement(material, "color", rgba="0.15 0.45 0.62 1")
    collision = ET.SubElement(probe, "collision")
    ET.SubElement(ET.SubElement(collision, "geometry"), "sphere", radius="0.009")
    visual = ET.SubElement(probe, "visual")
    ET.SubElement(visual, "origin", xyz="0 0 -0.0125")
    ET.SubElement(ET.SubElement(visual, "geometry"), "cylinder", radius="0.004", length="0.025")
    ET.SubElement(visual, "material", name="probe")
    joint = ET.SubElement(robot, "joint", name="press_tip_mount", type="fixed")
    ET.SubElement(joint, "parent", link="gripper_frame_link")
    ET.SubElement(joint, "child", link="press_tip")
    ET.SubElement(joint, "origin", xyz="0 0 0.025", rpy="0 0 0")
    path = folder / "so101_press_probe.urdf"
    ET.indent(robot)
    content = ET.tostring(robot, encoding="unicode")
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n'
                    '<!-- MODIFIED for this project: added press_tip link and fixed 25 mm probe; original SO-101 joints/meshes unchanged. -->\n' + content, encoding="utf-8")
    return "assets/so101/so101_press_probe.urdf"


if __name__ == "__main__":
    print(prepare())
