"""Enlarged crop.  python tools/crop.py in out x0 y0 x1 y1 scale  (box in the input image's own pixels)"""
import sys
from PIL import Image
i, o = sys.argv[1:3]; x0, y0, x1, y1 = map(int, sys.argv[3:7]); s = float(sys.argv[7])
im = Image.open(i).convert('RGB')
c = im.crop((x0, y0, x1, y1)); c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS); c.save(o, quality=92)
