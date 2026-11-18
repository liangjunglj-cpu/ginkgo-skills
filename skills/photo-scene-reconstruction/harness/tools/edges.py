"""Target edges (red) over the render, target resolution, 80 px grid.  python edges.py ref render out"""
import sys, numpy as np, cv2
ref, ren, out = sys.argv[1:4]
a = cv2.imread(ref); b = cv2.imread(ren)
b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
e = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (3, 3), 0), 80, 180)
o = (b * 0.75).astype(np.uint8)
o[e > 0] = (0, 0, 255)
for y in range(0, a.shape[0], 80):
    cv2.putText(o, str(y), (2, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
for x in range(0, a.shape[1], 80):
    cv2.putText(o, str(x), (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
cv2.imwrite(out, o)
