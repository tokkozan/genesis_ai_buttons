"""Bounded inverse kinematics from the official URDF, using NumPy/SciPy only."""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]


class ArmKinematics:
    def __init__(self, urdf):
        model = ET.parse(Path(urdf)).getroot()
        joints = model.findall("joint")
        by_child = {j.find("child").attrib["link"]: j for j in joints}
        chain, child = [], "press_tip"
        while child in by_child:
            joint = by_child[child]
            chain.append(joint)
            child = joint.find("parent").attrib["link"]
        self.chain = list(reversed(chain))
        actuated = {j.attrib["name"]: j for j in joints if j.attrib["name"] in JOINT_NAMES}
        self.lower = np.array([float(actuated[n].find("limit").attrib["lower"]) for n in JOINT_NAMES])
        self.upper = np.array([float(actuated[n].find("limit").attrib["upper"]) for n in JOINT_NAMES])
        self.last = np.array([0.0, -0.3, 0.3, 1.5, 0.0])
        self.transforms = []
        for joint in self.chain:
            origin = joint.find("origin")
            xyz = np.fromstring(origin.attrib.get("xyz", "0 0 0"), sep=" ") if origin is not None else np.zeros(3)
            rpy = np.fromstring(origin.attrib.get("rpy", "0 0 0"), sep=" ") if origin is not None else np.zeros(3)
            matrix = np.eye(4)
            matrix[:3, :3] = Rotation.from_euler("xyz", rpy).as_matrix()
            matrix[:3, 3] = xyz
            axis = joint.find("axis")
            axis = np.fromstring(axis.attrib["xyz"], sep=" ") if axis is not None else np.array([0, 0, 1])
            index = JOINT_NAMES.index(joint.attrib["name"]) if joint.attrib["name"] in JOINT_NAMES else None
            self.transforms.append((matrix, axis, index))

    def pose(self, q):
        result = np.eye(4)
        for origin, axis, index in self.transforms:
            result = result @ origin
            if index is not None:
                rotation = np.eye(4)
                rotation[:3, :3] = Rotation.from_rotvec(axis * q[index]).as_matrix()
                result = result @ rotation
        return result[:3, 3], result[:3, 2]

    def solve(self, target):
        target = np.asarray(target)

        def residual(q):
            pos, axis = self.pose(q)
            return np.r_[(pos-target)*10, axis-[0, 0, -1], 0.005*q[4]]

        best = None
        seeds = [self.last, [0, -0.3, 0.3, 1.5, 0], [0, 0.7, 0.8, 0, 0], [0, 1.1, 0, 0.5, 0]]
        for seed in seeds:
            result = least_squares(residual, np.clip(seed, self.lower+0.001, self.upper-0.001),
                                   bounds=(self.lower+0.001, self.upper-0.001), max_nfev=200,
                                   ftol=1e-9, xtol=1e-9, gtol=1e-9)
            if best is None or np.linalg.norm(result.fun) < np.linalg.norm(best.fun):
                best = result
            if np.linalg.norm(best.fun) < 0.002:
                break
        pos, axis = self.pose(best.x)
        if np.linalg.norm(pos-target) > 0.003 or np.linalg.norm(axis-[0, 0, -1]) > 0.03:
            raise RuntimeError(f"Target is outside SO-101 press workspace: {target.tolist()}")
        self.last = best.x.copy()
        return self.last.copy()
