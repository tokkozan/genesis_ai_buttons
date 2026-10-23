"""Create the small physical button panel; robot model is official SO-101."""
from pathlib import Path
from color_ai import BASE_RGB, LABELS

STATIONS = [{"id": "A", "xy": [0.20, -0.07], "color": "blue"},
            {"id": "B", "xy": [0.20, 0.0], "color": "red"},
            {"id": "C", "xy": [0.20, 0.07], "color": "green"}]


def create_button_file(station, root):
    color = BASE_RGB[LABELS.index(station["color"])]
    text = f'''<robot name="inspection_button">
<link name="base"><inertial><mass value="0.1"/><inertia ixx="0.001" iyy="0.001" izz="0.001" ixy="0" ixz="0" iyz="0"/></inertial>
<visual><origin xyz="0 0 0.012"/><geometry><box size="0.05 0.05 0.024"/></geometry><material name="base"><color rgba="0.20 0.25 0.32 1"/></material></visual>
<collision><origin xyz="0 0 0.012"/><geometry><box size="0.05 0.05 0.024"/></geometry></collision></link>
<link name="cap"><inertial><mass value="0.015"/><inertia ixx="0.000003" iyy="0.000003" izz="0.000003" ixy="0" ixz="0" iyz="0"/></inertial>
<visual><geometry><cylinder radius="0.020" length="0.010"/></geometry><material name="color"><color rgba="{color[0]} {color[1]} {color[2]} 1"/></material></visual>
<collision><geometry><cylinder radius="0.020" length="0.010"/></geometry></collision></link>
<joint name="button_travel" type="prismatic"><parent link="base"/><child link="cap"/><origin xyz="0 0 0.035"/><axis xyz="0 0 1"/><limit lower="-0.010" upper="0" effort="2" velocity="0.1"/></joint></robot>'''
    file = Path(root) / f"assets/button_{station['id']}.urdf"
    file.write_text(text, encoding="utf-8")
    return str(file)
