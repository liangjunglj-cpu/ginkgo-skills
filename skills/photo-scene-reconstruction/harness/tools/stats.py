"""Mean sRGB per region, target vs render, plus SCORE (mean abs diff, 0-255, lower is better).
Regions come from layout/regions.json {"regions": {name: [x0,y0,x1,y1]}} in target pixels.
    tools/py.sh tools/stats.py renders/x.png [domain]   (domain: only regions whose name starts with it)"""
import json, os, sys
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = np.asarray(Image.open(os.path.join(ROOT, 'ref', 'photo.jpg')).convert('RGB')).astype(float)
regs = json.load(open(os.path.join(ROOT, 'layout', 'regions.json')))['regions']
pre = sys.argv[2] if len(sys.argv) > 2 else ''
b = np.asarray(Image.open(sys.argv[1]).convert('RGB').resize((a.shape[1], a.shape[0]), Image.LANCZOS)).astype(float)
d = {}
for k, (x0, y0, x1, y1) in regs.items():
    if not k.startswith(pre):
        continue
    ra, rb = a[y0:y1, x0:x1].reshape(-1, 3), b[y0:y1, x0:x1].reshape(-1, 3)
    d[k] = np.abs(ra.mean(0) - rb.mean(0)).mean()
    print(f'{k:16s} ref {ra.mean(0).round(0)} sd {ra.std(0).mean():4.0f} | ours {rb.mean(0).round(0)} sd {rb.std(0).mean():4.0f} | diff {d[k]:5.1f}')
print(f'SCORE {np.mean(list(d.values())):.1f}  ({len(d)} regions)')
