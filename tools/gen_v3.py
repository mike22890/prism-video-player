import os, html

W, H = 1520, 1000
BG="#1c1b1a"; PANEL="#232120"; EDGE="#4a463f"; TEXT="#e6e0d4"; MUTED="#9a9488"
GREEN="#7fd1a8"; AMBER="#e0a24a"; RED="#d97a7a"; BLUE="#7aa8d9"
FONT="Consolas, 'Microsoft YaHei', monospace"

o=[]; A=o.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
A(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
A(f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{EDGE}"/></marker></defs>')
def esc(t): return html.escape(t)
def box(x,y,w,h,title,lines=(),accent=MUTED,fs=12):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PANEL}" stroke="{accent}" stroke-width="1.4"/>')
    A(f'<rect x="{x}" y="{y}" width="3.5" height="{h}" fill="{accent}"/>')
    A(f'<text x="{x+15}" y="{y+23}" font-family="{FONT}" font-size="13.5" fill="{TEXT}" font-weight="bold">{esc(title)}</text>')
    for i,ln in enumerate(lines):
        A(f'<text x="{x+15}" y="{y+43+i*18}" font-family="{FONT}" font-size="{fs}" fill="{MUTED}">{esc(ln)}</text>')
def region(x,y,w,h,label,color=EDGE):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" stroke="{color}" stroke-width="1.2" stroke-dasharray="5 5"/>')
    A(f'<text x="{x+14}" y="{y+21}" font-family="{FONT}" font-size="12" fill="{MUTED}" letter-spacing="2">{esc(label)}</text>')
def arrow(x1,y1,x2,y2,color=EDGE,dashed=False,label=None):
    d=' stroke-dasharray="5 4"' if dashed else ''
    A(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{d} marker-end="url(#ar)"/>')
    if label:
        A(f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-8}" font-family="{FONT}" font-size="11.5" fill="{color}" text-anchor="middle">{esc(label)}</text>')
def banner(x,y,w,h,fill,stroke,title,lines=()):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    A(f'<text x="{x+15}" y="{y+25}" font-family="{FONT}" font-size="14" fill="{stroke}" font-weight="bold">{esc(title)}</text>')
    for i,ln in enumerate(lines):
        A(f'<text x="{x+15}" y="{y+47+i*19}" font-family="{FONT}" font-size="12" fill="{MUTED}">{esc(ln)}</text>')

A(f'<text x="44" y="50" font-family="{FONT}" font-size="25" fill="{TEXT}" font-weight="bold">VOLTA v3</text>')
A(f'<text x="180" y="50" font-family="{FONT}" font-size="14.5" fill="{MUTED}">三条渲染路径 · 帧传输方案被推翻重定 · HDR 与网格互斥</text>')
A(f'<line x1="44" y1="66" x2="{W-44}" y2="66" stroke="{EDGE}"/>')

# ── 修正区 ──
banner(36,86,560,150,"#2a1f1f",RED,"修正 ①：跨进程 D3D11 共享纹理 = 走不通",[
 "render_d3d11.h 原文：device 与 texture 都归「调用方」所有",
 "→ 这是嵌入 API 约定，不是跨进程共享接口",
 "→ mpv 不导出 device/纹理句柄，我们拿不到要共享的那个",
 "→ v1/v2 的「跨进程共享纹理」方案作废"])
banner(624,86,560,150,"#2a1f1f",RED,"修正 ②：性能预算按帧拷贝重算",[
 "1 路 1080p60 = 475 MB/s    9 路 760×428 = 670 MB/s",
 "合计 1145 MB/s ≈ 16 GB/s 机器的 7.2% —— 跑得动",
 "若背景格错按 1080p 渲染 → 4271 MB/s（26.7%）",
 "结论反而更硬：按显示尺寸渲染省的是 6 倍"])
banner(1212,86,272,150,"#2a2318",AMBER,"修正 ③：HDR × 网格",[
 "HDR 直通必须全屏独占",
 "（d3d11-exclusive-fs=yes）",
 "→ 多路不可能都独占",
 "单路全屏 = 直通",
 "网格多路 = tonemap SDR"])

# ── 三条路径 ──
region(36,256,1448,340,"RENDER PATHS · 封装在 engine/ 一层，ui/ 不感知")
paths=[
 (56,"路径 B · --wid 原生窗口嵌套","Windows 主选",GREEN,
  ["mpv 画进我们建的子 HWND","完整 gpu-next 画质保留","代价：原生窗口永远盖在 UI 之上",
   "→ 控制条移到网格下方（GridPlayer 风格）","证据：iptvnator Win32 走的就是这条"]),
 (516,"路径 C · 进程内 libmpv","UI 无缝覆盖时选",AMBER,
  ["mpv_render_context 回调渲染","我们提供 device + 纹理，零拷贝","代价：只有老 vo_gpu，无 libplacebo",
   "→ HDR/色彩管理能力腰斩","UI 可直接画在视频上，无层级问题"]),
 (976,"路径 A' · 帧拷贝回退","任何平台都能用",BLUE,
  ["helper 进程渲到共享内存","主进程上传纹理","代价：纯内存搬运，约 7.2% 带宽","+10ms 延迟，需 audio-delay 校准",
   "证据：iptvnator 最终选了这条路"]),
]
for x,title,tag,col,lines in paths:
    A(f'<rect x="{x}" y="288" width="440" height="180" rx="6" fill="{PANEL}" stroke="{col}" stroke-width="1.4"/>')
    A(f'<text x="{x+15}" y="313" font-family="{FONT}" font-size="13.5" fill="{TEXT}" font-weight="bold">{esc(title)}</text>')
    A(f'<text x="{x+425}" y="313" font-family="{FONT}" font-size="11.5" fill="{col}" text-anchor="end">{esc(tag)}</text>')
    for i,ln in enumerate(lines):
        A(f'<text x="{x+15}" y="{337+i*25}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">{esc(ln)}</text>')
A(f'<text x="56" y="500" font-family="{FONT}" font-size="12.5" fill="{GREEN}">选型规则：Windows 默认 B ｜ 需要 UI 覆盖视频 → C ｜ Linux/macOS 首版 → C 或 A\'（X11 原生嵌套不稳，macOS 层级脆）</text>')
A(f'<text x="56" y="524" font-family="{FONT}" font-size="12.5" fill="{GREEN}">抽象层：VideoSurface 接口统一 → gpu-next 后端哪天合并了，切路径只动 engine/，ui/ 一行不改</text>')
A(f'<text x="56" y="566" font-family="{FONT}" font-size="12" fill="{AMBER}">实测佐证：4K 源在 720p 视口只花 720p 的代价（iptvnator RESULTS.md）——印证「按显示尺寸渲染」</text>')

# ── 补全清单 ──
region(36,616,1448,340,"v3 补全的十个洞")
items=[
 ("字幕","libass 在 mpv 侧；样式随主题推属性；背景格可关字幕省 CPU","主题"),
 ("播放列表语义","自己管列表，不用 mpv playlist → 「全部循环」无歧义","语义"),
 ("状态持久化","JSON + schema 版本；异常退出后提示恢复会话","持久化"),
 ("错误三层","引擎 / 传输 / 逻辑各给不同信息；诊断 zip 一键导出","诊断"),
 ("打包分发","附 Vulkan loader（无驱动机拒载 DLL）；用 mpv-dev-lgpl","分发"),
 ("硬件矩阵","无 Vulkan 驱动、核显、多屏 HDR、热插拔、休眠唤醒","兼容"),
 ("电源发热","笔记本电池供电自动降档；dormant 停渲染","功耗"),
 ("无障碍","键盘全操作、焦点可见、字号可调、对比度 ≥4.5:1","可达"),
 ("测试策略","着色器 CI 要在两种缩放方向下验证 hook 真触发","测试"),
 ("可交接","ADR 记录「为什么」；代码只写「是什么」；make check 一键","交接"),
]
for i,(t,s,tag) in enumerate(items):
    col=i%2; row=i//2
    x=56+col*712; y=652+row*60
    A(f'<rect x="{x}" y="{y}" width="690" height="50" rx="5" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.1"/>')
    A(f'<text x="{x+14}" y="{y+21}" font-family="{FONT}" font-size="12.5" fill="{GREEN}" font-weight="bold">{esc(t)}</text>')
    A(f'<text x="{x+14}" y="{y+39}" font-family="{FONT}" font-size="11" fill="{MUTED}">{esc(s)}</text>')
    A(f'<text x="{x+676}" y="{y+21}" font-family="{FONT}" font-size="10.5" fill="{AMBER}" text-anchor="end">{esc(tag)}</text>')

A(f'<text x="44" y="984" font-family="{FONT}" font-size="12.5" fill="{MUTED}">M0 拆成三步：M0a 子 HWND 嵌套（z-order + DPI）｜ M0b 三路径最小 demo 量延迟 ｜ M0c 9 路性能基线 —— 揉成一步就不知道该换哪条路</text>')
A('</svg>')

p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"v3.svg")
open(p,"w",encoding="utf-8").write("\n".join(o))
print("wrote",p,os.path.getsize(p))
