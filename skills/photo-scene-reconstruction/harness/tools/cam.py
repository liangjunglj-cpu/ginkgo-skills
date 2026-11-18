"""Solved camera for this lab's target image (ref/photo.jpg) + pixel->world helpers. FROZEN.
Reads layout/camera.json: pos [x,y,z] (m), pitch (deg, negative = looking down), yaw (deg, 0 = looking along +Y,
positive turns left toward -X), roll, focal_mm, sensor_h (mm, vertical sensor fit), res [W, H].
Blender world: X right, Y forward (at yaw 0), Z up, ground z = 0."""
import json
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = json.load(open(os.path.join(ROOT, 'layout', 'camera.json')))['camera']
W, H = C['res']
F_MM, SENSOR_H = C['focal_mm'], C['sensor_h']
FPX = H * F_MM / SENSOR_H
POS = np.array(C['pos'], float)
PITCH, ROLL, YAW = C['pitch'], C.get('roll', 0.0), C['yaw']


def R(pitch=None, roll=None, yaw=None):
    p, r, y = map(math.radians, (PITCH if pitch is None else pitch, ROLL if roll is None else roll,
                                 YAW if yaw is None else yaw))
    fwd = np.array([0, math.cos(p), math.sin(p)]); up = np.array([0, -math.sin(p), math.cos(p)])
    rt = np.array([1.0, 0, 0])
    rt, up = rt * math.cos(r) + up * math.sin(r), up * math.cos(r) - rt * math.sin(r)
    cy, sy = math.cos(y), math.sin(y); Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ rt, Rz @ up, Rz @ fwd


def ray(px, py, **kw):
    rt, up, fwd = R(**kw)
    d = rt * (px - W / 2) + up * (H / 2 - py) + fwd * FPX
    return d / np.linalg.norm(d)


def on_z(px, py, z=0.0, **kw):
    """World point where the view ray through pixel (px, py) hits the horizontal plane z."""
    d = ray(px, py, **kw); t = (z - POS[2]) / d[2]; return POS + d * t


def on_plane(px, py, p0, n, **kw):
    """Hit any plane through p0 with normal n."""
    d = ray(px, py, **kw); n = np.asarray(n, float); t = (np.asarray(p0, float) - POS) @ n / (d @ n)
    return POS + d * t


def project(p, **kw):
    rt, up, fwd = R(**kw); v = np.asarray(p, float) - POS
    z = v @ fwd; return W / 2 + FPX * (v @ rt) / z, H / 2 - FPX * (v @ up) / z


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 3:
        z = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        print(on_z(float(sys.argv[1]), float(sys.argv[2]), z).round(2))
