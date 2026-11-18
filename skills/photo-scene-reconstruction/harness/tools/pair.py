"""Target crop | render crop, enlarged (box in target pixels).  python tools/pair.py target render out x0 y0 x1 y1"""
import sys
from PIL import Image
a, b, out = sys.argv[1:4]
x0, y0, x1, y1 = map(int, sys.argv[4:8])
A = Image.open(a).convert('RGB')
Bm = Image.open(b).convert('RGB').resize(A.size, Image.LANCZOS)
ca, cb = A.crop((x0, y0, x1, y1)), Bm.crop((x0, y0, x1, y1))
s = min(4.0, 900 / max(ca.width, 1), 1000 / max(ca.height, 1))
ca = ca.resize((int(ca.width * s), int(ca.height * s)), Image.LANCZOS)
cb = cb.resize(ca.size, Image.LANCZOS)
sh = Image.new('RGB', (ca.width * 2 + 8, ca.height), (255, 0, 255))
sh.paste(ca, (0, 0)); sh.paste(cb, (ca.width + 8, 0))
sh.save(out, quality=90)
