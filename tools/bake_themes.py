"""离线烘焙七个主题的背景纹理 PNG。
换手法：不再用 QML Canvas 手画几何，改用 PIL 精修纹理，QML 只贴图 + 少量属性动画。
准则（taste-drill）：一个焦点一个隐喻、低对比慢动作、焦点落在左侧面板可见区(0..600)。
复古主题( nes/gameboy/determination )严禁渐变；只有 synthwave/terminal 允许辉光。
"""
from PIL import Image, ImageDraw, ImageFilter
import math, random, os

W, H = 1920, 1200
OUT = r"C:\Users\16324\Downloads\volta\themes\_fx"
os.makedirs(OUT, exist_ok=True)

def save(im, name):
    p = os.path.join(OUT, name)
    im.convert("RGB").save(p, optimize=True)
    print("baked", name, os.path.getsize(p))

# ── default 暗夜·静默：极夜 + 三道极光帘幕（上散下锐，绿主紫边）+ 针叶林剪影 ──
def bake_default():
    im = Image.new("RGB", (W, H), (6, 9, 18))
    d = ImageDraw.Draw(im, "RGBA")
    rnd = random.Random(11)
    for _ in range(150):
        x = rnd.randrange(0, 620); y = rnd.randrange(0, 720)
        s = 1 if rnd.random() < 0.85 else 2
        d.ellipse([x, y, x+s, y+s], fill=(232, 244, 255, rnd.randrange(50, 170)))
    p = im.load()
    def curtain(cx, width, phase, strength):
        for y in range(0, int(H*0.80)):
            t = y / (H*0.80)
            env = math.sin(math.pi*min(1.0, t*1.12)) ** 1.3
            c = cx + 34*math.sin(t*2.6 + phase)
            w = width*(1 - 0.52*t)
            for x in range(max(0, int(c-w*2.2)), min(W, int(c+w*2.2))):
                u = (x - c)/w
                g = math.exp(-u*u*2.0)
                stripe = 0.72 + 0.28*math.sin(x*0.09 + phase + math.sin(y*0.018)*2.0)
                a = g*env*stripe*strength
                if a < 0.012: continue
                r, gr, b = p[x, y]
                purple = max(0.0, 0.30-t)*1.6       # 顶部镶紫边
                p[x, y] = (int(r*(1-a)+(57+120*purple)*a),
                           int(gr*(1-a)+(255-110*purple)*a),
                           int(b*(1-a)+(139+95*purple)*a))
    curtain(150, 150, 0.0, 0.46)
    curtain(340, 110, 1.9, 0.38)
    curtain(505, 88, 3.6, 0.30)
    im = im.filter(ImageFilter.GaussianBlur(3))
    # 雪原 + 针叶林剪影（纯黑）
    d = ImageDraw.Draw(im, "RGBA")
    gy = int(H*0.86)
    d.rectangle([0, gy, W, H], fill=(5, 8, 16, 255))
    def tree(px, py, th):
        for k in range(3):
            tw = th*(1-k*0.24); ty = py+k*th*0.30
            d.polygon([(px, ty), (px-tw/2, ty+th*0.44), (px+tw/2, ty+th*0.44)], fill=(3, 5, 11, 255))
    rnd = random.Random(5)
    x = 10
    while x < 640:
        tree(x, gy-26-(x % 3)*9, 34+rnd.randrange(0, 14))
        x += 46+rnd.randrange(0, 24)
    save(im, "bg_default.png")

# ── gameboy 掌机·四阶绿：机身 + 有限屏幕面板 + 稀疏点阵（中心留白） ──
def bake_gameboy():
    im = Image.new("RGB", (W, H), (139, 160, 160))   # 机身灰
    d = ImageDraw.Draw(im, "RGBA")
    # 屏幕面板：左侧可见区内，四阶绿，硬边框
    sx, sy, sw, sh = 40, 150, 520, 430
    d.rounded_rectangle([sx-16, sy-16, sx+sw+16, sy+sh+16], radius=18, fill=(155, 188, 15, 255))
    d.rectangle([sx, sy, sx+sw, sy+sh], fill=(155, 188, 15, 255), outline=(48, 98, 48, 255), width=10)
    # 稀疏点阵：<1% 面积，中心留白
    cx, cy = sx+sw/2, sy+sh/2
    R = min(sw, sh)*0.5
    for yy in range(sy+18, sy+sh-18, 26):
        for xx in range(sx+18, sx+sw-18, 26):
            rr = math.hypot(xx-cx, yy-cy)/R
            if rr < 0.42: continue
            a = int(30 + 50*min(1.0, (rr-0.42)/0.58))
            d.rectangle([xx, yy, xx+3, yy+3], fill=(15, 56, 15, a))
    # 机身细节：屏幕下.command 文字 + 电源灯（经典 DMG 真实感）
    d.rectangle([sx+70, sy+sh+52, sx+160, sy+sh+58], fill=(90, 105, 105, 255))
    d.ellipse([sx+sw-70, sy+sh+44, sx+sw-52, sy+sh+62], fill=(200, 60, 60, 255))
    d.ellipse([sx+sw-66, sy+sh+48, sx+sw-56, sy+sh+58], fill=(255, 130, 130, 255))
    save(im, "bg_gameboy.png")

# ── nes 8bit·红白机：纯天蓝 + 经典 SMB 平底鼓包云（硬边黑描边，零渐变） ──
def bake_nes():
    im = Image.new("RGB", (W, H), (92, 148, 252))
    d = ImageDraw.Draw(im, "RGBA")
    def smb_cloud(px, py, s):
        cy = py + 40*s; r1, r2, r3 = 12*s, 18*s, 11*s
        c1, c2, c3 = px+11*s, px+24*s, px+37*s
        # 平底 + 三鼓包，硬边黑描边
        d.polygon([(px+3*s, py+40*s), (px+3*s, cy), (px+45*s, cy), (px+45*s, py+40*s)],
                  fill=(252, 252, 252, 255))
        for c, r in ((c1,r1),(c2,r2),(c3,r3)):
            d.ellipse([c-r, cy-r, c+r, cy+r], fill=(252, 252, 252, 255))
        # 黑描边（外轮廓）
        d.arc([c1-r1-2, cy-r1-2, c1+r1+2, cy+r1+2], 180, 360, fill=(0,0,0,255), width=2)
        d.arc([c2-r2-2, cy-r2-2, c2+r2+2, cy+r2+2], 180, 360, fill=(0,0,0,255), width=2)
        d.arc([c3-r3-2, cy-r3-2, c3+r3+2, cy+r3+2], 180, 360, fill=(0,0,0,255), width=2)
        d.line([(px+3*s, py+40*s), (px+3*s, cy)], fill=(0,0,0,255), width=2)
        d.line([(px+45*s, py+40*s), (px+45*s, cy)], fill=(0,0,0,255), width=2)
        # 云底蓝阴影带
        d.rectangle([px+4*s, py+32*s, px+44*s, py+40*s], fill=(60, 188, 252, 255))
    smb_cloud(60, 120, 2.1)
    smb_cloud(330, 300, 1.4)
    smb_cloud(180, 470, 1.0)
    # 草地 + 土块（SMB 硬边）
    gy = int(H*0.88)
    d.rectangle([0, gy, W, gy+18], fill=(0, 168, 0, 255))
    d.rectangle([0, gy+18, W, H], fill=(184, 116, 60, 255))
    for x in range(0, W, 32):
        d.rectangle([x+4, gy+26, x+12, gy+34], fill=(120, 76, 40, 255))
    save(im, "bg_nes.png")

# ── synthwave 合成波·落日：条纹落日 + 透视网格 + 楔形跑车 + 远山 ──
def bake_synthwave():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im, "RGBA")
    # 夜空渐变
    for y in range(H):
        t = y/H
        if t < 0.55:
            a = t/0.55; c = (int(11+25*a), int(2+14*a), int(33+41*a))
        else:
            a = (t-0.55)/0.45; c = (int(36+70*a), int(16+11*a), int(74+78*a))
        d.line([(0,y),(W,y)], fill=c+(255,))
    hy = int(H*0.58); cx = 210; r = 190
    # 太阳：黄→橙→粉渐变圆
    for yy in range(int(hy-r*1.2), int(hy+r)):
        for xx in range(cx-r, cx+r):
            dy = yy-(hy-30)
            if (xx-cx)**2 + dy**2 > r*r: continue
            t = max(0, min(1, (yy-(hy-30-r))/(2*r)))
            c = (int(255-40*t), int(210-140*t), int(63+80*t))
            d.point((xx,yy), fill=c+(255,))
    # 下半条纹：递增间距的深幽夜空色横条，把太阳下半切开（真 synthwave 认牌）
    stripe_y = hy - 30 + 8
    gap = 4.0
    while stripe_y < hy + r:
        gh = max(3, int(gap*0.55))
        d.rectangle([cx-r-2, int(stripe_y), cx+r+2, int(stripe_y)+gh], fill=(30, 12, 62, 255))
        stripe_y += gap + gh
        gap *= 1.42
    # 远山剪影
    d.polygon([(0,hy),(90,hy-70),(190,hy-10),(300,hy-90),(430,hy),(600,hy+30),(0,hy+30)],
              fill=(20, 6, 40, 255))
    # 透视网格：竖线扇形 + 横线（静态，QML 层做滚动叠加）
    for i in range(-12, 13):
        d.line([(cx, hy), (cx+i*130, H)], fill=(5, 217, 232, 90), width=2)
    for i in range(1, 14):
        y = hy + (H-hy)*(i/14)**2.2
        d.line([(0,int(y)),(W,int(y))], fill=(255, 45, 158, int(20+60*i/14)), width=2)
    # 楔形跑车剪影（压在太阳前）
    def car(px, s, flip=False):
        L, HH = 200*s, 62*s
        pts = [(0,-HH*0.42),(L*0.18,-HH*0.74),(L*0.42,-HH*0.80),(L*0.56,-HH*1.02),
               (L*0.80,-HH*1.02),(L*0.91,-HH*0.72),(L,-HH*0.68),(L,-HH*0.12),(0,-HH*0.12)]
        if flip: pts = [(2*px-x, y) for x,y in pts]  # 简单镜像占位
        pts = [(px+x, hy+y) for x,y in pts]
        d.polygon(pts, fill=(5, 1, 15, 255))
        for fx in (0.25, 0.79):
            wx = px+L*fx
            d.ellipse([wx-14*s, hy-14*s, wx+14*s, hy+14*s], fill=(5,1,15,255))
        d.rectangle([px+L-10*s, hy-HH*0.62, px+L-2*s, hy-HH*0.44], fill=(255, 45, 111, 255))
    car(cx-30, 0.95)
    save(im, "bg_synthwave.png")

# ── terminal 终端·磷光：深绿黑 + 扫描线 + 幽灵字符 + 打字行 + 暗角 ──
def bake_terminal():
    im = Image.new("RGB", (W, H), (10, 23, 15))
    d = ImageDraw.Draw(im, "RGBA")
    # 幽灵字符（淡绿等宽，静态）
    rnd = random.Random(7)
    for y in range(20, H-20, 26):
        for x in range(8, 620, 15):
            ch = chr(33 + rnd.randrange(0, 90))
            d.text((x, y), ch, fill=(51, 255, 102, 26))
    # 打字行 + 块状光标（静态底，光标闪由 QML 层）
    d.text((28, int(H*0.40)), "> PRISM://MEDIA READY [OK] SIGNAL=STABLE", fill=(51, 255, 102, 150))
    # 扫描线：每 4px 一条暗线
    for y in range(0, H, 4):
        d.line([(0,y),(W,y)], fill=(0,0,0, 34))
    # 暗角
    vig = Image.new("L", (W,H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W*0.25, -H*0.25, W*1.25, H*1.25], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(180))
    dark = Image.new("RGB", (W,H), (0,0,0))
    im = Image.composite(im, dark, vig)
    save(im, "bg_terminal.png")

# ── winxp 蓝天·Luna：Bliss 真实感绿坡（不对称 S 形）+ 软积云 ──
def bake_winxp():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(H):
        t = y/H
        c = (int(47+96*t), int(108+83*t), int(207+24*t))
        d.line([(0,y),(W,y)], fill=c+(255,))
    # 软积云：三层白椭圆叠加（软边靠叠加，不靠模糊）
    def soft_cloud(px, py, s):
        blobs = [(px+0.28*90*s, py+0.62*40*s, 0.22*90*s, 0.30*40*s),
                 (px+0.52*90*s, py+0.48*40*s, 0.28*90*s, 0.42*40*s),
                 (px+0.76*90*s, py+0.64*40*s, 0.20*90*s, 0.28*40*s)]
        for pass_ in range(3):
            a = [70, 95, 140][pass_]; shrink = pass_*0.18
            for bx, by, bw, bh in blobs:
                d.ellipse([bx-bw*(1-shrink), by-bh*(1-shrink), bx+bw*(1-shrink), by+bh*(1-shrink)],
                          fill=(255,255,255,a))
    soft_cloud(70, 110, 2.4); soft_cloud(360, 250, 1.6); soft_cloud(180, 420, 1.1)
    # S 形绿坡：两段斜坡 + 右侧远处缓坡，全部平滑衔接铺满整宽（无直角台阶）
    def slope(y0, c1x, c1y, c2x, c2y, y1, fill, xend=W):
        pts = [(0, H)]
        for i in range(0, 241):
            t = i/240; mt = 1-t
            x = 2*mt*t*c1x + t*t*c2x
            y = mt*mt*y0 + 2*mt*t*c1y + t*t*y1
            pts.append((int(x), int(y)))
        # 从曲线末端平滑接到右边缘（用一段浅缓坡，不垂直切）
        last_y = pts[-1][1]
        for i in range(1, 41):
            t = i/40
            x = pts[-1][0] + (W - pts[-1][0])*t
            y = last_y + (int(H*0.62) - last_y)*t*t
            pts.append((int(x), int(y)))
        pts.append((W, H)); pts.append((0, H))
        d.polygon(pts, fill=fill)
    slope(int(H*0.60), 260, int(H*0.46), 760, int(H*0.60), int(H*0.56), (155, 214, 90, 255))
    slope(int(H*0.74), 340, int(H*0.62), 900, int(H*0.80), int(H*0.72), (94, 160, 42, 255))
    save(im, "bg_winxp.png")

# ── determination 决心：纯黑 + 白直线边框 + 精确居中红像素心（唯一焦点） ──
def bake_determination():
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    # 白直线框：左侧可见区，无圆角无阴影
    bx0, by0, bx1, by1 = 120, 300, 380, 560
    d.rectangle([bx0, by0, bx1, by1], outline=(255,255,255,255), width=4)
    # 精确居中的 16×11 对称像素心
    rows = ["..####....####..", ".######..######.", "################", "################",
            "################", ".##############.", "..############..", "...##########...",
            "....########....", ".....######.....", ".......##......."]
    u = 13; cols = 16; rws = 11
    iw, ih = cols*u, rws*u
    ox = (bx0+bx1)//2 - iw//2
    oy = (by0+by1)//2 - ih//2
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                d.rectangle([ox+c*u, oy+r*u, ox+(c+1)*u-1, oy+(r+1)*u-1], fill=(244, 0, 28, 255))
    save(im, "bg_determination.png")

if __name__ == "__main__":
    bake_default()
    bake_determination()
    bake_gameboy()
    bake_nes()
    bake_synthwave()
    bake_terminal()
    bake_winxp()
    print("ALL BAKED")
