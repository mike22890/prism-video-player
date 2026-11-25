import os, html

W, H = 1500, 940
BG="#1c1b1a"; PANEL="#232120"; EDGE="#4a463f"; TEXT="#e6e0d4"; MUTED="#9a9488"
GREEN="#7fd1a8"; AMBER="#e0a24a"; RED="#d97a7a"; BLUE="#7aa8d9"; VIOLET="#a98fd9"
FONT="Consolas, 'Microsoft YaHei', monospace"

o=[]; A=o.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
A(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
A(f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{EDGE}"/></marker>'
  f'<marker id="arv" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{VIOLET}"/></marker></defs>')
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
def arrow(x1,y1,x2,y2,color=EDGE,dashed=False,label=None):
    d=' stroke-dasharray="5 4"' if dashed else ''
    mk = "arv" if color==VIOLET else "ar"
    A(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{d} marker-end="url(#{mk})"/>')
    if label:
        A(f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-9}" font-family="{FONT}" font-size="11.5" fill="{color}" text-anchor="middle">{esc(label)}</text>')

A(f'<text x="44" y="50" font-family="{FONT}" font-size="25" fill="{TEXT}" font-weight="bold">VOLTA</text>')
A(f'<text x="140" y="50" font-family="{FONT}" font-size="14.5" fill="{MUTED}">播放列表归谁管 · 拆成三层，队列挂内容不挂槽位</text>')
A(f'<line x1="44" y1="66" x2="{W-44}" y2="66" stroke="{EDGE}"/>')

# ── 三层 ──
region(36,86,900,300,"THREE LAYERS")
box(56,120,250,116,"Library 素材库",["全局唯一 · 跨槽位共享","只回答「有什么可播的」","拖入 / 扫描 / 最近播放"],BLUE)
box(356,120,270,116,"PlayItem 播放项",["一个可播放单元","带自己的队列和设置：","source / queue / loopMode / abLoop /","volume / sid / aid / shader / timePos"],AMBER)
box(676,120,240,116,"Slot 槽位",["视图上的一个位置","只回答「现在显示谁」","index / layoutCell / focus"],GREEN)
arrow(306,178,356,178,BLUE,label="装载")
arrow(626,178,676,178,AMBER,label="持有")

A(f'<rect x="56" y="252" width="860" height="56" rx="6" fill="#241f18" stroke="{VIOLET}" stroke-width="1.4"/>')
A(f'<text x="72" y="274" font-family="{FONT}" font-size="12.5" fill="{VIOLET}" font-weight="bold">关键决策：队列绑定在 PlayItem 上，不是 Slot 上</text>')
A(f'<text x="72" y="294" font-family="{FONT}" font-size="11.5" fill="{MUTED}">否则 2×2 → 3×3 布局重排时，剧集队列跟着槽位一起错位丢失 —— 极难查的 bug</text>')

A(f'<text x="56" y="338" font-family="{FONT}" font-size="12.5" fill="{TEXT}">用户嘴里的「播放列表」其实是两个东西，多路同播逼着它们分开</text>')
A(f'<text x="56" y="362" font-family="{FONT}" font-size="11.5" fill="{MUTED}">「我加了这些视频」= 素材库（全局）　「接下来播什么」= 队列（每槽位独立）</text>')

# ── 队列归属三模式 ──
region(960,86,504,300,"QUEUE OWNERSHIP")
for i,(t,s,c) in enumerate([
  ("独立（默认）","每槽位自己的队列，各播各的","对比党"),
  ("同步","所有槽位共享一个队列 + 同步进度","对比同视频不同版本"),
  ("链式（v2 再做）","槽位1播完接槽位2的队列","串流播放")]):
    y=120+i*76
    A(f'<rect x="980" y="{y}" width="464" height="66" rx="6" fill="{PANEL}" stroke="{c}" stroke-width="1.3"/>')
    A(f'<text x="996" y="{y+23}" font-family="{FONT}" font-size="13" fill="{c}" font-weight="bold">{esc(t)}</text>')
    A(f'<text x="996" y="{y+43}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">{esc(s)}</text>')
    A(f'<text x="1428" y="{y+23}" font-family="{FONT}" font-size="11" fill="{AMBER}" text-anchor="end">{esc(c if False else ["","对比党","对比同视频不同版本","串流播放"][i+1])}</text>')
A(f'<text x="980" y="360" font-family="{FONT}" font-size="11.5" fill="{MUTED}">「同步」不是拍脑袋 —— GridPlayer 上游有 timecode seek sync mode</text>')

# ── 操作路由表 ──
region(36,406,900,300,"ROUTING · 拖到哪里进哪里")
rows=[
 ("拖文件 → 队列面板","追加到焦点槽位的队列"),
 ("拖文件 → 库面板","只进素材库，不入队"),
 ("拖文件 → 某个槽位","该槽位换播（PlayItem 替换）"),
 ("拖文件夹 → 队列面板","展开为一组，按名称排序追加"),
 ("库多选 N 项 → ▶ 并播","分配到 N 个槽位，每项一个 PlayItem"),
 ("库多选 N 项 → ▶ 串播","N 项进焦点槽位一个队列"),
 ("双击库项","载入到焦点槽位并聚焦"),
 ("双击队列项","插到当前项之后并跳转"),
]
for i,(a,b) in enumerate(rows):
    col=i%2; row=i//2
    x=56+col*440; y=442+row*64
    A(f'<rect x="{x}" y="{y}" width="420" height="54" rx="5" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.1"/>')
    A(f'<text x="{x+14}" y="{y+21}" font-family="{FONT}" font-size="12" fill="{GREEN}" font-weight="bold">{esc(a)}</text>')
    A(f'<text x="{x+14}" y="{y+40}" font-family="{FONT}" font-size="11" fill="{MUTED}">{esc(b)}</text>')
A(f'<rect x="56" y="702" width="860" height="0" fill="none"/>')

# ── 作用域 ──
region(960,406,504,300,"SCOPE · 循环和 A-B")
A(f'<text x="980" y="446" font-family="{FONT}" font-size="12.5" fill="{TEXT}">全部作用于「焦点槽位」</text>')
for i,(t,s) in enumerate([("loop-file / loop-playlist","该槽位当前文件 / 队列循环"),
                            ("ab-loop-a / ab-loop-b","该槽位的区间"),
                            ("volume / muted","该槽位（批量走多选）")]):
    y=460+i*50
    A(f'<rect x="980" y="{y}" width="464" height="42" rx="5" fill="{PANEL}" stroke="{AMBER}" stroke-width="1.2"/>')
    A(f'<text x="996" y="{y+19}" font-family="{FONT}" font-size="12" fill="{AMBER}" font-weight="bold">{esc(t)}</text>')
    A(f'<text x="996" y="{y+34}" font-family="{FONT}" font-size="11" fill="{MUTED}">{esc(s)}</text>')
A(f'<rect x="980" y="614" width="464" height="72" rx="6" fill="#241f18" stroke="{RED}" stroke-width="1.3"/>')
A(f'<text x="996" y="636" font-family="{FONT}" font-size="12.5" fill="{RED}" font-weight="bold">「全部循环」≠「所有槽位一起循环」</text>')
A(f'<text x="996" y="656" font-family="{FONT}" font-size="11.5" fill="{MUTED}">前者 = 焦点槽位的队列循环（单槽语义）</text>')
A(f'<text x="996" y="674" font-family="{FONT}" font-size="11.5" fill="{MUTED}">后者 = 同步模式（另一回事）· 按钮旁必须标作用对象</text>')

# ── 面板形态 ──
region(36,726,1428,180,"PANEL · 两个模式，面板跟随焦点")
A(f'<rect x="56" y="762" width="660" height="128" rx="6" fill="{PANEL}" stroke="{GREEN}" stroke-width="1.3"/>')
A(f'<text x="72" y="784" font-family="{FONT}" font-size="12.5" fill="{GREEN}" font-weight="bold">队列模式 —— 显示焦点槽位的队列</text>')
for i,t in enumerate(["[ 队列 ▾ ] [ 库 ]        焦点 SLOT 1",
                      "▶ 1  ep01.mkv              24:11   ← 当前播放，高亮+进度",
                      "  2  ep02.mkv              24:08",
                      "  3  ep03.mkv              23:57"]):
    A(f'<text x="72" y="{806+i*20}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">{esc(t)}</text>')
A(f'<rect x="740" y="762" width="704" height="128" rx="6" fill="{PANEL}" stroke="{BLUE}" stroke-width="1.3"/>')
A(f'<text x="756" y="784" font-family="{FONT}" font-size="12.5" fill="{BLUE}" font-weight="bold">库模式 —— 显示全部素材，徽标标出占用关系</text>')
for i,t in enumerate(["[ 队列 ] [ 库 ▾ ]",
                      "  ep01.mkv                [ SLOT 1 ]   ← 徽标：它在哪一格",
                      "  tutorial.mp4              未装载",
                      "  ep03.mkv                [ SLOT 3 ]"]):
    A(f'<text x="756" y="{806+i*20}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">{esc(t)}</text>')
A(f'<text x="1150" y="884" font-family="{FONT}" font-size="11.5" fill="{AMBER}">切焦点 → 面板内容跟着切（用户无需理解「面板属于谁」）</text>')
A(f'<text x="44" y="926" font-family="{FONT}" font-size="12" fill="{MUTED}">规模：库 2000 项必须 ListView 虚拟滚动（同时存在 ~15 个 delegate）｜ 面板跟随焦点要换 model 而非重建面板</text>')
A('</svg>')

p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"playlist.svg")
open(p,"w",encoding="utf-8").write("\n".join(o))
print("wrote",p,os.path.getsize(p))
