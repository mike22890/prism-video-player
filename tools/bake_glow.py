"""离线烘焙真散射光晕 PNG —— 核心陡 + 1/r² 长尾 + 色温随距离偏暖→品红。
不用 Canvas 画光，用预烘焙纹理，一个 quad 零 shader，绝不 banding（加 dither）。
输出：themes/_fx/glow_warm.png（暖光，synthwave/default 用）、glow_cyan.png（青光/terminal 用）。
"""
from PIL import Image
import math, random
SZ = 512
C = (SZ - 1) / 2.0

def bake(path, core_rgb, tail_rgb):
    px = Image.new("RGBA", (SZ, SZ))
    data = []
    rnd = random.Random(7)
    for y in range(SZ):
        for x in range(SZ):
            dx, dy = (x - C) / C, (y - C) / C
            r = math.sqrt(dx * dx + dy * dy)
            # 核心陡 + 长尾（模拟 Mie 前向散射 + 短波衰减）
            core = math.exp(-r * r * 3.2)
            tail = 1.0 / (1.0 + r * r * 6.0)
            g = core * 0.78 + tail * tail * 0.42
            t = min(1.0, r / 1.6)
            rgb = tuple(int(core_rgb[i] * (1 - t) + tail_rgb[i] * t) for i in range(3))
            a = max(0.0, min(1.0, g))
            # dither 打散 8bit banding
            d = (rnd.random() - 0.5) * 0.008
            a = max(0.0, min(1.0, a + d))
            data.append((rgb[0], rgb[1], rgb[2], int(a * 255)))
    px.putdata(data)
    px.save(path)
    print("baked", path)

base = r"C:\Users\16324\Downloads\volta\shaders"
import os
os.makedirs(os.path.join(os.path.dirname(base), "themes", "_fx"), exist_ok=True)
fx = os.path.join(os.path.dirname(base), "themes", "_fx")
bake(os.path.join(fx, "glow_warm.png"), (255, 190, 96), (236, 60, 140))
bake(os.path.join(fx, "glow_cyan.png"), (120, 240, 235), (70, 120, 200))
