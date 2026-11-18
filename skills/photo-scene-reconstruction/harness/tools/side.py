"""Side-by-side of any images at equal height (e.g. style reference | hero render).  python tools/side.py out a b [c ...]"""
import sys
from PIL import Image
out = sys.argv[1]; ims = [Image.open(p).convert('RGB') for p in sys.argv[2:]]
h = min(900, min(im.height for im in ims))
ims = [im.resize((int(im.width * h / im.height), h), Image.LANCZOS) for im in ims]
s = Image.new('RGB', (sum(im.width for im in ims) + 8 * (len(ims) - 1), h), (255, 0, 255)); x = 0
for im in ims:
    s.paste(im, (x, 0)); x += im.width + 8
s.save(out, quality=90)
