"""Texture energy per region (realism check): fine = std(Y - blur5), panel = std(blur5 - blur25), target vs render.
    tools/py.sh tools/hf.py renders/x.png [domain]"""
import json, os, sys
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = cv2.imread(os.path.join(ROOT, 'ref', 'photo.jpg'), 0).astype(float)
b = cv2.resize(cv2.imread(sys.argv[1], 0), (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA).astype(float)
regs = json.load(open(os.path.join(ROOT, 'layout', 'regions.json')))['regions']
pre = sys.argv[2] if len(sys.argv) > 2 else ''
def e(im):
    b5 = cv2.GaussianBlur(im, (0, 0), 1.6); b25 = cv2.GaussianBlur(im, (0, 0), 8)
    return im - b5, b5 - b25
fa, pa = e(a); fb, pb = e(b)
for k, (x0, y0, x1, y1) in regs.items():
    if k.startswith(pre):
        s = np.s_[y0:y1, x0:x1]
        print(f'{k:16s} fine {fa[s].std():5.1f} -> {fb[s].std():5.1f}   panel {pa[s].std():5.1f} -> {pb[s].std():5.1f}')
