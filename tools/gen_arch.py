import os, html

W, H = 1440, 880
BG = "#1c1b1a"
PANEL = "#232120"
EDGE = "#4a463f"
TEXT = "#e6e0d4"
MUTED = "#9a9488"
GREEN = "#7fd1a8"
AMBER = "#e0a24a"
FONT = "Consolas, 'Microsoft YaHei', monospace"

out = []
A = out.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
A(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

def esc(t): return html.escape(t)

def box(x, y, w, h, title, lines=(), accent=MUTED, mono=13):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PANEL}" stroke="{accent}" stroke-width="1.4"/>')
    A(f'<rect x="{x}" y="{y}" width="3.5" height="{h}" fill="{accent}"/>')
    A(f'<text x="{x+16}" y="{y+24}" font-family="{FONT}" font-size="14" fill="{TEXT}" font-weight="bold">{esc(title)}</text>')
    for i, ln in enumerate(lines):
        A(f'<text x="{x+16}" y="{y+46+i*19}" font-family="{FONT}" font-size="{mono}" fill="{MUTED}">{esc(ln)}</text>')

def region(x, y, w, h, label):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" stroke="{EDGE}" stroke-width="1.2" stroke-dasharray="5 5"/>')
    A(f'<text x="{x+14}" y="{y+22}" font-family="{FONT}" font-size="12.5" fill="{MUTED}" letter-spacing="2">{esc(label)}</text>')

def arrow(x1, y1, x2, y2, color=EDGE, dashed=False, label=None):
    d = ' stroke-dasharray="5 4"' if dashed else ''
    A(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{d} marker-end="url(#ar)"/>')
    if label:
        A(f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-7}" font-family="{FONT}" font-size="11.5" fill="{color}" text-anchor="middle">{esc(label)}</text>')

A(f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
  f'<path d="M0,0 L10,5 L0,10 z" fill="{EDGE}"/></marker></defs>')

A(f'<text x="44" y="52" font-family="{FONT}" font-size="26" fill="{TEXT}" font-weight="bold">VOLTA</text>')
A(f'<text x="150" y="52" font-family="{FONT}" font-size="15" fill="{MUTED}">架构 · 单窗口多视频网格 · mpv 0.42.0 独立进程</text>')
A(f'<line x1="44" y1="70" x2="{W-44}" y2="70" stroke="{EDGE}" stroke-width="1"/>')

region(40, 96, 380, 640, "FRONTEND · Qt6 QML")
region(470, 96, 480, 640, "ENGINE · VOLTA CORE")
region(1000, 96, 400, 640, "RUNTIME · mpv 进程 x N")

box(64, 136, 332, 92, "Theme Shell", ["default.qml / terminal.qml", "Theme Tokens（唯一颜色来源）"], GREEN)
box(64, 248, 332, 92, "Slot Grid", ["1 / 2x2 / 3x3 / 拼贴", "每槽位 = 一个 QML Item"], AMBER)
box(64, 360, 332, 92, "Playlist View", ["懒加载缩略图", "循环模式 / A-B 区间标记"], AMBER)
box(64, 472, 332, 92, "Shader Overlay", ["QML 侧扫描线 / 暗角", "跟随主题切换"], GREEN)
box(64, 584, 332, 92, "Coverage Gate", ["CI 扫硬编码颜色", "不过就红"], GREEN)

box(494, 136, 432, 92, "Profile Engine", ["按分辨率/源类型自动切档", "→ 生成 mpv profile-cond"], AMBER)
box(494, 248, 432, 92, "Process Pool", ["每视频一个 mpv 进程", "崩溃不带走网格"], AMBER)
box(494, 360, 432, 92, "JSON IPC", ["属性订阅 / 事件推送", "A-B、loop 属性直推"], GREEN)
box(494, 472, 432, 92, "Frame Transport", ["D3D11 共享纹理", "零 CPU 回读（待 M0 验证）"], GREEN)
box(494, 584, 432, 92, "Thumbnail Service", ["离屏 mpv 抽帧", "mtime+size 缓存 key"], GREEN)

box(1024, 136, 352, 92, "hwdec", ["D3D11VA / Vulkan 硬解", "优先非拷贝路径"], AMBER)
box(1024, 248, 352, 92, "vo_gpu_next", ["libplacebo 管线", "HDR / scRGB / DV P7"], GREEN)
box(1024, 360, 352, 92, "Shaders", ["CRT · VHS · 增强", "参数运行时可调"], GREEN)
box(1024, 472, 352, 92, "缩略图旁路", ["离屏实例抽 1 帧", "不打扰播放实例"], MUTED)
box(1024, 584, 352, 92, "隔离边界", ["崩溃 / 卡死只影响一格", "可单独重启"], MUTED)

arrow(396, 182, 494, 182, GREEN, label="令牌")
arrow(396, 294, 494, 294, AMBER)
arrow(396, 406, 494, 406, AMBER)
arrow(396, 518, 494, 518, GREEN)
arrow(926, 406, 1024, 406, GREEN, label="属性")
arrow(926, 518, 1024, 518, GREEN, label="帧")
arrow(494, 518, 396, 294, EDGE, dashed=True, label="控制")
arrow(926, 182, 1024, 182, EDGE, dashed=True)

A(f'<text x="44" y="790" font-family="{FONT}" font-size="13" fill="{MUTED}">控制流：QML → JSON IPC → mpv 属性　│　数据流：mpv 进程 → D3D11 共享纹理 → QML FBO Item　│　零 CPU 回读</text>')
A(f'<text x="44" y="816" font-family="{FONT}" font-size="13" fill="{MUTED}">关键约束：gpu-next 至今没有 libmpv 渲染后端（PR #16818 / RFC #18607 仍 open）→ 必须走独立进程</text>')
A(f'<text x="44" y="842" font-family="{FONT}" font-size="13" fill="{MUTED}">生死线：M0 验证 D3D11 共享纹理帧传输（延迟 &lt; 30ms，CPU 拷贝 = 0）</text>')
A('</svg>')

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arch.svg")
open(path, "w", encoding="utf-8").write("\n".join(out))
print("wrote", path, os.path.getsize(path))
