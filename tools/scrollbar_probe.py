"""数一数左面板右边缘有没有滚动条：找那几条被点亮的列。

    python tools/scrollbar_probe.py shots/lib-8items.png
"""
import sys

from PIL import Image

im = Image.open(sys.argv[1] if len(sys.argv) > 1 else "shots/lib-8items.png").convert("RGB")
W, H = im.size
rows = []
for x in range(380, min(470, W)):
    lit = 0
    for y in range(120, H - 80, 4):
        r, g, b = im.getpixel((x, y))
        if r + g + b > 150:
            lit += 1
    rows.append((lit, x))
rows.sort(reverse=True)
print("最亮的十列 (点亮行数, x):", rows[:10])
print("面板右边界附近若有一列明显点亮，就是滚动条的轨道/滑块")
