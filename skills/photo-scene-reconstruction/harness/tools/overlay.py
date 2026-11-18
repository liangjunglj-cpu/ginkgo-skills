"""target | render | 50% blend.  python overlay.py ref render out"""
import sys
from PIL import Image
ref, ren, out = sys.argv[1:4]
a = Image.open(ref).convert("RGB")
b = Image.open(ren).convert("RGB").resize(a.size, Image.LANCZOS)
c = Image.blend(a, b, 0.5)
s = Image.new("RGB", (a.width * 3 + 20, a.height), (255, 255, 255))
s.paste(a, (0, 0)); s.paste(b, (a.width + 10, 0)); s.paste(c, (2 * a.width + 20, 0))
s = s.resize((s.width * 2 // 3, s.height * 2 // 3), Image.LANCZOS)
s.save(out, quality=90)
