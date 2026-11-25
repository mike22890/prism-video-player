"""为 GitHub README 生成展示图：七主题拼图 + 环境光单图。"""
from PIL import Image, ImageDraw, ImageFont
import os
ROOT = r"C:\Users\16324\Downloads\volta"
OUT = os.path.join(ROOT, "screenshots")
os.makedirs(OUT, exist_ok=True)

themes = [
    ("default", "Dark Silence"),
    ("determination", "Determination"),
    ("synthwave", "Synthwave Sunset"),
    ("terminal", "Phosphor Terminal"),
    ("nes", "8-bit NES"),
    ("gameboy", "Game Boy"),
    ("winxp", "Blue Luna"),
]
TW, TH, PAD, LABEL = 640, 400, 12, 30
cols, rows = 2, 4
W = cols * TW + (cols + 1) * PAD
H = rows * (TH + LABEL) + (rows + 1) * PAD
sheet = Image.new("RGB", (W, H), (14, 15, 20))
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
except Exception:
    font = ImageFont.load_default()

for i, (tid, name) in enumerate(themes):
    src = os.path.join(ROOT, "shots", f"show_{tid}.png")
    if not os.path.exists(src):
        print("MISSING", src); continue
    im = Image.open(src).convert("RGB")
    im.thumbnail((TW, TH), Image.LANCZOS)
    r, c = divmod(i, cols)
    x = PAD + c * (TW + PAD)
    y = PAD + r * (TH + LABEL + PAD)
    sheet.paste(im, (x, y))
    draw.text((x + 6, y + TH + 4), f"{name}  ({tid})", fill=(210, 215, 225), font=font)

p = os.path.join(OUT, "themes.png")
sheet.save(p, optimize=True)
print("saved", p, sheet.size, os.path.getsize(p))

# 环境光单图（竖屏视频 + 跟颜色走的辉光）
amb = Image.open(os.path.join(ROOT, "shots", "ambpromo.png")).convert("RGB")
amb.thumbnail((1100, 1100), Image.LANCZOS)
p2 = os.path.join(OUT, "ambilight.png")
amb.save(p2, optimize=True)
print("saved", p2, amb.size, os.path.getsize(p2))
