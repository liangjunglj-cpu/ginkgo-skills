"""Image with a labelled pixel grid (for picking points).  python tools/grid.py in out [step=50]"""
import sys, cv2
im = cv2.imread(sys.argv[1]); st = int(sys.argv[3]) if len(sys.argv) > 3 else 50
for x in range(0, im.shape[1], st):
    cv2.line(im, (x, 0), (x, im.shape[0]), (0, 255, 255) if x % (st * 2) == 0 else (0, 160, 255), 1)
    cv2.putText(im, str(x), (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
for y in range(0, im.shape[0], st):
    cv2.line(im, (0, y), (im.shape[1], y), (0, 255, 255) if y % (st * 2) == 0 else (0, 160, 255), 1)
    cv2.putText(im, str(y), (2, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
cv2.imwrite(sys.argv[2], im)
