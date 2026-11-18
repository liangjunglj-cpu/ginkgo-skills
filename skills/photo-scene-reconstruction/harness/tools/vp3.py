"""Lead tool: three vanishing points (vertical + two horizontal) from LSD segments -> focal, pitch, roll, yaw of the
first horizontal family.   tools/py.sh tools/vp3.py image.jpg [sensor_h=24]
Prints a camera.json block (pos is left for the lead to set from a known dimension)."""
import math, sys
import numpy as np, cv2
im = cv2.imread(sys.argv[1]); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
SH = float(sys.argv[2]) if len(sys.argv) > 2 else 24.0
H, W = g.shape; cx, cy = W / 2, H / 2
L = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(g)[0].reshape(-1, 4)
ln = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1]); k = ln > 22; L, ln = L[k], ln[k]
ang = np.degrees(np.arctan2(L[:, 3] - L[:, 1], L[:, 2] - L[:, 0])) % 180
def homog(s):
    a = np.c_[s[:, 0], s[:, 1], np.ones(len(s))]; b = np.c_[s[:, 2], s[:, 3], np.ones(len(s))]
    l = np.cross(a, b); return l / np.linalg.norm(l[:, :2], axis=1, keepdims=True)
def ransac(sel, it=6000, tol=1.2, seed=0):
    idx = np.where(sel)[0]; s = L[idx]; w = ln[idx]; hl = homog(s); rng = np.random.default_rng(seed)
    mid = np.c_[(s[:, 0] + s[:, 2]) / 2, (s[:, 1] + s[:, 3]) / 2]
    dirs = np.c_[s[:, 2] - s[:, 0], s[:, 3] - s[:, 1]]; dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    best = (0, None, None)
    for _ in range(it):
        i, j = rng.choice(len(s), 2, replace=False); v = np.cross(hl[i], hl[j])
        if abs(v[2]) < 1e-12: continue
        v = v / v[2]; d = v[:2] - mid; d /= np.linalg.norm(d, axis=1, keepdims=True)
        err = np.degrees(np.arccos(np.clip(np.abs((d * dirs).sum(1)), 0, 1)))
        sc = w[err < tol].sum()
        if sc > best[0]: best = (sc, v, idx[err < tol])
    return best
vert = (ang > 65) & (ang < 115)
_, vv, vin = ransac(vert)
rest = ~vert
_, h1, h1in = ransac(rest, seed=1)
rest2 = rest.copy(); rest2[h1in] = False
_, h2, h2in = ransac(rest2, seed=2)
print('vertical VP', vv[:2].round(1), len(vin), '| h1', h1[:2].round(1), len(h1in), '| h2', h2[:2].round(1), len(h2in))
f2 = -((h1[0] - cx) * (h2[0] - cx) + (h1[1] - cy) * (h2[1] - cy))
f2v = [-((h[0] - cx) * (vv[0] - cx) + (h[1] - cy) * (vv[1] - cy)) for h in (h1, h2)]
print('f^2 from h1.h2', round(f2), ' from v.h1, v.h2', [round(x) for x in f2v])
cands = [x for x in [f2] + f2v if x > 0]
f = math.sqrt(np.median(cands)) if cands else W
# down direction in camera coords (x right, y up, z forward): vertical VP below centre for a downward camera
dv = np.array([vv[0] - cx, cy - vv[1], f]); dv /= np.linalg.norm(dv)
if dv[1] > 0: dv = -dv     # world down must point to -y in camera space for a normal (not upside-down) view
pitch = -math.degrees(math.asin(np.clip(dv[2], -1, 1)))   # camera forward . world down = sin(-pitch)
roll = math.degrees(math.atan2(dv[0], -dv[1]))
d1 = np.array([h1[0] - cx, cy - h1[1], f]); d1 /= np.linalg.norm(d1)
print(f'focal_px {f:.0f}  focal_mm(sensor_h {SH}) {f * SH / H:.2f}  pitch {pitch:.2f}  roll {roll:.2f}')
print('h1 direction in camera coords', d1.round(3), '(choose yaw so this family runs along world +X or +Y)')
