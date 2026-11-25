import os, html

W, H = 1480, 900
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
def arrow(x1,y1,x2,y2,color=EDGE,dashed=False,label=None,side="above"):
    d=' stroke-dasharray="5 4"' if dashed else ''
    A(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{d} marker-end="url(#ar)"/>')
    if label:
        dy = -9 if side=="above" else 18
        A(f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2+dy}" font-family="{FONT}" font-size="11.5" fill="{color}" text-anchor="middle">{esc(label)}</text>')

A(f'<text x="44" y="50" font-family="{FONT}" font-size="25" fill="{TEXT}" font-weight="bold">VOLTA</text>')
A(f'<text x="140" y="50" font-family="{FONT}" font-size="14.5" fill="{MUTED}">视图历史栈 · 双击独占 / 还原 · 与渲染分级正交</text>')
A(f'<line x1="44" y1="66" x2="{W-44}" y2="66" stroke="{EDGE}"/>')

# ── 状态机 ──
region(36,86,880,380,"STATE MACHINE · 视图栈")
box(66,132,230,104,"GRID",["4 格 / 9 格网格","焦点格 focused","其余 visible = active"],GREEN)
box(392,132,230,104,"SOLO",["单格独占","焦点 = 唯一格","其余 hidden = dormant"],AMBER)
box(718,132,170,104,"SOLO′",["单格换内容","（从播放列表双击）"],BLUE)
arrow(296,168,392,168,GREEN,label="双击槽位 N")
arrow(622,168,718,168,BLUE,label="双击条目 M")
arrow(803,236,803,286,AMBER,dashed=True,label="")
arrow(803,290,190,290,AMBER,dashed=True,label="双击 / Esc / 返回按钮 → pop")
arrow(190,236,190,290,AMBER,dashed=True,label="")

A(f'<rect x="66" y="304" width="822" height="52" rx="6" fill="#241f18" stroke="{AMBER}" stroke-width="1.3"/>')
A(f'<text x="82" y="326" font-family="{FONT}" font-size="12.5" fill="{AMBER}">快照存的是「完整视图」不是「布局」——含每槽 source / timePos / pause / volume / muted / A-B / 轨道 / shader链 / dwidth</text>')
A(f'<text x="82" y="346" font-family="{FONT}" font-size="12" fill="{MUTED}">9 槽满快照 ≈ 4 KB，栈深上限 16 层 → 最坏 64 KB。还原后播放位置误差 &lt; 0.1s。</text>')

A(f'<text x="66" y="392" font-family="{FONT}" font-size="12.5" fill="{TEXT}">栈深 &gt; 1 时，Esc 逐层回退（不是一次退到底）</text>')
A(f'<text x="66" y="414" font-family="{FONT}" font-size="12" fill="{MUTED}">SOLO 态双击唯一视频区 = 返回（符合「再按 F11 缩回」直觉）</text>')
A(f'<text x="66" y="436" font-family="{FONT}" font-size="12" fill="{MUTED}">「G 切网格布局」与「双击独占」是两件事：前者改格子数（不 push），后者改看哪个（push）</text>')

# ── 正交性 ──
region(940,86,504,380,"ORTHOGONALITY · 职责不重叠")
A(f'<text x="960" y="126" font-family="{FONT}" font-size="12.5" fill="{TEXT}">视图栈管「谁可见」</text>')
A(f'<text x="960" y="148" font-family="{FONT}" font-size="12" fill="{MUTED}">分级机制管「可见的怎么渲染」</text>')
A(f'<rect x="960" y="164" width="464" height="150" rx="6" fill="{PANEL}" stroke="{GREEN}" stroke-width="1.3"/>')
A(f'<text x="976" y="188" font-family="{FONT}" font-size="12.5" fill="{GREEN}" font-weight="bold">computeRenderTier(slotId, viewState)</text>')
for i,(t,c) in enumerate([("focused —— 焦点格，原生分辨率 + 全特效 + 出声",GREEN),
                            ("active —— 可见非焦点，dwidth=显示尺寸 + 轻量着色器",AMBER),
                            ("dormant —— 不可见，停渲染但保解码位置",RED)]):
    A(f'<text x="976" y="{212+i*24}" font-family="{FONT}" font-size="11.5" fill="{c}">{esc(t)}</text>')
A(f'<text x="976" y="296" font-family="{FONT}" font-size="11.5" fill="{MUTED}">只有一个决策函数 → 没有「两处判断不一致」的 bug</text>')
A(f'<rect x="960" y="330" width="464" height="52" rx="6" fill="#241f18" stroke="{AMBER}" stroke-width="1.2"/>')
A(f'<text x="976" y="352" font-family="{FONT}" font-size="12" fill="{AMBER}">进 SOLO：3 格 → dormant，总像素 124.4 Mpix/s</text>')
A(f'<text x="976" y="370" font-family="{FONT}" font-size="12" fill="{MUTED}">4 格网格：78.1 Mpix/s → 独占反而更省 GPU（159%）</text>')

# ── 底部：用户群 × 交互 ──
region(36,486,1408,380,"USER GROUPS · 同一功能，不同人怎么用")
groups=[
 ("追剧党","一次看一个","拖进来就播","双击=沉浸单格，Esc 回来"),
 ("对比党","一屏看完，偶尔放大一个","网格常驻","双击放大；返回按钮常驻"),
 ("学习/剪辑党","反复看片段","A-B 打点 + 帧步进 , .","双击放大后精确到帧"),
 ("直播/监控党","多路同时看","每格独立进程","一格崩了不影响其他"),
 ("触屏用户","平板上划","没有右键","返回按钮 ≥44pt，双击手势"),
 ("键盘党","不用鼠标","全键盘操作","Enter 放大 / Esc 退 / G 切网格 / Tab 换格"),
]
for i,(g,scene,want,act) in enumerate(groups):
    col=i%2; row=i//2
    x=56+col*692; y=522+row*112
    A(f'<rect x="{x}" y="{y}" width="670" height="100" rx="6" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.2"/>')
    A(f'<text x="{x+15}" y="{y+24}" font-family="{FONT}" font-size="13" fill="{GREEN}" font-weight="bold">{esc(g)}</text>')
    A(f'<text x="{x+130}" y="{y+24}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">{esc(scene)}</text>')
    A(f'<text x="{x+15}" y="{y+50}" font-family="{FONT}" font-size="11.5" fill="{TEXT}">要：{esc(want)}</text>')
    A(f'<text x="{x+15}" y="{y+72}" font-family="{FONT}" font-size="11.5" fill="{AMBER}">做：{esc(act)}</text>')

A(f'<text x="44" y="890" font-family="{FONT}" font-size="12.5" fill="{MUTED}">易用性四原则：① 双击不是唯一入口（返回按钮常驻）② 状态可见（SOLO·1/4、◂2/3）③ 快捷键全覆盖 ④ 动画能解释变化（240ms，reduce-motion 时长 0）</text>')
A('</svg>')

p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"viewstack.svg")
open(p,"w",encoding="utf-8").write("\n".join(o))
print("wrote",p,os.path.getsize(p))
