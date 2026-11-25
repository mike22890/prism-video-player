"""扫左面板右侧 430..458 这段每一列的亮度分布，判断滚动条到底在不在。

    python tools/scrollbar_probe2.py shots/lib-8items.png
"""
import sys

from PIL import Image

im = Image.open(sys.argv[1] if len(sys.argv) > 1 else "shots/lib-8items.png").convert("RGB")
W, H = im.size
print(f"图 {W}x{H}")
for x in range(430, min(459, W)):
    vals = []
    for y in range(120, H - 80, 3):
        r, g, b = im.getpixel((x, y))
        vals.append(max(r, g, b))
    vals.sort()
    p90 = vals[int(len(vals) * 0.9)]
    print(f"x={x}: max={vals[-1]:3d} p90={p90:3d} 中位={vals[len(vals)//2]:3d}")
