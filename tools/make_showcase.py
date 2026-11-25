"""生成 README 展示用视频封面：黄昏海景（渐变天空+太阳+远山+海面），非彩条。"""
from PIL import Image, ImageDraw, ImageFilter
import math, os
W, H = 1280, 720
im = Image.new("RGB", (W, H))
d = ImageDraw.Draw(im)
# 黄昏天空：顶部深蓝紫 -> 地平线橙金
for y in range(H):
    t = y / (H * 0.72)
    t = min(1, t)
    r = int(24 + 231 * (t ** 1.5))
    g = int(28 + 138 * (t ** 1.8))
    b = int(74 + 60 * (1 - t))
    d.line([(0, y), (W, y)], fill=(r, g, b))
# 太阳
sx, sy, sr = 880, 430, 90
for yy in range(sy - sr, sy + sr):
    for xx in range(sx - sr, sx + sr):
        dist = math.hypot(xx - sx, yy - sy)
        if dist > sr: continue
        tt = (yy - (sy - sr)) / (2 * sr)
        c = (255, int(240 - 90 * tt), int(150 - 120 * tt))
        d.point((xx, yy), fill=c)
# 云带（水平软条）
for cy, cw, alpha in [(180, 340, 55), (250, 260, 40), (330, 420, 35)]:
    for k in range(30):
        x0 = (cx := int(sx - cw + (k / 30) * cw * 2))
        a = int(alpha * math.sin(math.pi * k / 30))
        d.line([(x0, cy - 6), (x0, cy + 6)], fill=(255, 200, 160, a))
# 远山剪影
d.polygon([(0, 520), (180, 440), (360, 505), (560, 410), (760, 500), (980, 430), (1280, 510), (1280, 720), (0, 720)], fill=(28, 24, 46))
d.polygon([(0, 570), (240, 520), (500, 575), (820, 505), (1120, 560), (1280, 530), (1280, 720), (0, 720)], fill=(16, 14, 28))
# 海面 + 倒影
for y in range(600, H):
    t = (y - 600) / (H - 600)
    c = (int(40 + 20 * t), int(30 + 12 * t), int(60 + 20 * t))
    d.line([(0, y), (W, y)], fill=c)
for i in range(60):
    y = 605 + i * 2
    w = int(60 * (1 - i / 60) + 10)
    d.line([(sx - w, y), (sx + w, y)], fill=(255, int(150 - i), int(90 - i // 2)))
im = im.filter(ImageFilter.GaussianBlur(0.6))
p = r"C:\Users\16324\Downloads\volta\shots\showcase_still.png"
im.save(p)
print("saved", p, im.size)
