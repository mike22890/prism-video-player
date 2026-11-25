import os, html

W, H = 1480, 900
BG="#1c1b1a"; PANEL="#232120"; EDGE="#4a463f"; TEXT="#e6e0d4"; MUTED="#9a9488"
GREEN="#7fd1a8"; AMBER="#e0a24a"; RED="#d97a7a"; BLUE="#7aa8d9"; VIOLET="#a98fd9"
FONT="Consolas, 'Microsoft YaHei', monospace"

o=[]; A=o.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
A(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
A(f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{EDGE}"/></marker></defs>')
def esc(t): return html.escape(t)
def box(x,y,w,h,title,lines=(),accent=MUTED,fs=11.5):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PANEL}" stroke="{accent}" stroke-width="1.4"/>')
    A(f'<rect x="{x}" y="{y}" width="3.5" height="{h}" fill="{accent}"/>')
    A(f'<text x="{x+15}" y="{y+23}" font-family="{FONT}" font-size="13.5" fill="{TEXT}" font-weight="bold">{esc(title)}</text>')
    for i,ln in enumerate(lines):
        A(f'<text x="{x+15}" y="{y+43+i*17}" font-family="{FONT}" font-size="{fs}" fill="{MUTED}">{esc(ln)}</text>')
def region(x,y,w,h,label,color=EDGE):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" stroke="{color}" stroke-width="1.2" stroke-dasharray="5 5"/>')
    A(f'<text x="{x+14}" y="{y+21}" font-family="{FONT}" font-size="12" fill="{MUTED}" letter-spacing="2">{esc(label)}</text>')
def arrow(x1,y1,x2,y2,color=EDGE,dashed=False,label=None,dx=0):
    d=' stroke-dasharray="5 4"' if dashed else ''
    A(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{d} marker-end="url(#ar)"/>')
    if label:
        A(f'<text x="{(x1+x2)/2+dx}" y="{(y1+y2)/2-9}" font-family="{FONT}" font-size="11.5" fill="{color}" text-anchor="middle">{esc(label)}</text>')

A(f'<text x="44" y="50" font-family="{FONT}" font-size="25" fill="{TEXT}" font-weight="bold">VOLTA</text>')
A(f'<text x="140" y="50" font-family="{FONT}" font-size="14.5" fill="{MUTED}">打开即有 · 目录自动收录 → 播放列表</text>')
A(f'<line x1="44" y1="66" x2="{W-44}" y2="66" stroke="{EDGE}"/>')

# ── 流程 ──
region(36,86,900,296,"FLOW · 零操作")
box(56,120,196,96,"① 打开视频",["双击 D:\\Movies\\Action\\2024\\","ep05.mkv"],GREEN)
box(276,120,196,96,"② 扫同目录",["不递归 · 扩展名白名单","排除 .part/.tmp 半成品"],BLUE)
box(496,120,196,96,"③ 队列=整目录",["自然排序","当前文件高亮定位"],AMBER)
box(716,120,196,96,"④ 面板显示来源",["路径 + 项数","可点 → 换目录"],VIOLET)
for i,(x1,x2) in enumerate([(252,276),(472,496),(692,716)]):
    arrow(x1,168,x2,168,GREEN)

A(f'<rect x="56" y="232" width="856" height="52" rx="6" fill="#241f18" stroke="{GREEN}" stroke-width="1.3"/>')
A(f'<text x="72" y="254" font-family="{FONT}" font-size="12.5" fill="{GREEN}" font-weight="bold">用户全程没点任何「添加」按钮</text>')
A(f'<text x="72" y="274" font-family="{FONT}" font-size="11.5" fill="{MUTED}">手动添加降级为次要操作：Ctrl+拖 = 只加这一个文件，普通拖 = 加整个目录</text>')
A(f'<text x="56" y="308" font-family="{FONT}" font-size="12.5" fill="{TEXT}">打开时的 toast：已载入 …\\2024\\ · 24 个视频 · 当前在第 3 个</text>')
A(f'<text x="56" y="332" font-family="{FONT}" font-size="11.5" fill="{MUTED}">定位到当前项并自动滚动可见 —— 用户不该自己找</text>')

# ── 排序 ──
region(960,86,484,296,"NATURAL SORT · 必须自然序")
A(f'<text x="980" y="126" font-family="{FONT}" font-size="12.5" fill="{TEXT}">字典序（错）</text>')
A(f'<text x="980" y="150" font-family="{FONT}" font-size="12" fill="{RED}">ep1, ep10, ep11, ep2, ep20, ep3</text>')
A(f'<text x="980" y="180" font-family="{FONT}" font-size="12.5" fill="{TEXT}">自然序（对）</text>')
A(f'<text x="980" y="204" font-family="{FONT}" font-size="12" fill="{GREEN}">ep1, ep2, ep3, ep10, ep11, ep20</text>')
A(f'<text x="980" y="238" font-family="{FONT}" font-size="12.5" fill="{TEXT}">混合中英文</text>')
A(f'<text x="980" y="262" font-family="{FONT}" font-size="12" fill="{GREEN}">EP01, intro, 第1集, 第2集, 第10集</text>')
A(f'<text x="980" y="292" font-family="{FONT}" font-size="11.5" fill="{MUTED}">数字段按整数比；中文按拼音（locale collation）</text>')
A(f'<text x="980" y="316" font-family="{FONT}" font-size="11.5" fill="{AMBER}">这是播放器里最常见的排序投诉来源</text>')
A(f'<text x="980" y="342" font-family="{FONT}" font-size="11.5" fill="{MUTED}">同扩展名同名（ep01.mp4 / ep01.mkv）都列出并标注格式</text>')

# ── 性能 ──
region(36,402,900,240,"PERFORMANCE · 实测不是瓶颈")
perf=[("100 项","1.0 ms"),("1000 项","2.1 ms"),("5000 项","9.9 ms")]
for i,(n,t) in enumerate(perf):
    x=56+i*286
    A(f'<rect x="{x}" y="438" width="266" height="70" rx="6" fill="{PANEL}" stroke="{GREEN}" stroke-width="1.3"/>')
    A(f'<text x="{x+16}" y="{464}" font-family="{FONT}" font-size="13" fill="{TEXT}">{esc(n)}</text>')
    A(f'<text x="{x+16}" y="{490}" font-family="{FONT}" font-size="17" fill="{GREEN}">{esc(t)}</text>')
A(f'<text x="56" y="540" font-family="{FONT}" font-size="12.5" fill="{TEXT}">目录列举根本不是瓶颈 —— 异步是为了网络盘和 QML 渲染几千行</text>')
for i,t in enumerate([
  "扫描放 QThreadPool（防网络盘卡 UI 线程）",
  "结果批量 emit（每 100 项 / 50ms），不是每文件一信号",
  "QML 侧 ListView 虚拟滚动，只实例化 ~15 个 delegate",
  "扫描时绝不抽缩略图 —— 那是独立任务队列"]):
    A(f'<text x="72" y="{566+i*20}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">▸ {esc(t)}</text>')

# ── 数据结构统一 ──
region(960,402,484,240,"DATA MODEL · 一种形状")
A(f'<text x="980" y="440" font-family="{FONT}" font-size="12.5" fill="{TEXT}">ScanSource</text>')
A(f'<rect x="980" y="452" width="444" height="80" rx="6" fill="{PANEL}" stroke="{VIOLET}" stroke-width="1.3"/>')
for i,(k,v) in enumerate([("rootPath","D:\\Movies\\Action\\2024\\"),
                            ("mode","FULL_DIR | SINGLE_FILE"),
                            ("items[]","扫描到的全部视频")]):
    A(f'<text x="996" y="{474+i*22}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">{esc(k)}  {esc(v)}</text>')
A(f'<text x="980" y="562" font-family="{FONT}" font-size="12" fill="{GREEN}">手动加的单文件 = mode=SINGLE_FILE</text>')
A(f'<text x="980" y="584" font-family="{FONT}" font-size="12" fill="{GREEN}">手动加的目录 = mode=FULL_DIR</text>')
A(f'<text x="980" y="612" font-family="{FONT}" font-size="11.5" fill="{AMBER}">不再有「手动项」和「目录项」两种数据形状</text>')

# ── 边界 ──
region(36,662,1408,204,"BOUNDARY")
edge=[
 ("大目录","5000 项上限，超出截断并提示","上限可调"),
 ("网络盘","扫描超时 10s 放弃，不无限等","异步的意义"),
 ("递归子目录","默认关，设置里可开","打开 Action\\ 不该拖进 Action\\2023\\"),
 ("半成品文件",".part/.tmp/.!ut 排除","下载中的文件"),
 ("同名不同格式","都列出并标注","ep01.mp4 vs ep01.mkv"),
 ("换目录","队列整体替换","有手动项时先确认，支持 Ctrl+Z 撤销"),
 ("源被删除","标灰不自动删","播放时给具体错误"),
 ("中文/emoji 路径","UTF-16 处理","Windows 安全"),
]
for i,(t,s,n) in enumerate(edge):
    col=i%2; row=i//2
    x=56+col*700; y=698+row*42
    A(f'<rect x="{x}" y="{y}" width="680" height="36" rx="5" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.1"/>')
    A(f'<text x="{x+12}" y="{y+22}" font-family="{FONT}" font-size="11.5" fill="{GREEN}" font-weight="bold">{esc(t)}</text>')
    A(f'<text x="{x+140}" y="{y+22}" font-family="{FONT}" font-size="11" fill="{MUTED}">{esc(s)}</text>')
    A(f'<text x="{x+668}" y="{y+22}" font-family="{FONT}" font-size="10.5" fill="{AMBER}" text-anchor="end">{esc(n)}</text>')
A(f'<text x="44" y="890" font-family="{FONT}" font-size="12" fill="{MUTED}">定位变化：VOLTA 不再是「要你整理播放列表的播放器」，是「打开文件就能连着看」的播放器 —— 和系统播放器一样自然，但多出网格 / 多主题 / 多路</text>')
A('</svg>')

p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"directory.svg")
open(p,"w",encoding="utf-8").write("\n".join(o))
print("wrote",p,os.path.getsize(p))
