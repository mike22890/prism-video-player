"""用新的 app-icon.png 生成多尺寸 app.ico（Windows 图标必须逐档 LANCZOS 降采样）。"""
from PIL import Image
import os
SRC = r"C:\Users\16324\Downloads\volta\app-icon.png"
DST = r"C:\Users\16324\Downloads\volta\app.ico"
SIZES = [(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)]
im = Image.open(SRC).convert("RGBA")
# 关键：传原始大图 + sizes 列表，PIL 内部逐档降采样；不能 append_images 小图（会只剩一档）
im.save(DST, format="ICO", sizes=SIZES)
chk = Image.open(DST)
print("saved", DST, os.path.getsize(DST), "bytes")
print("sizes:", sorted(chk.ico.sizes()))
