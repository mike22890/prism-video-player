import os, html

W, H = 1500, 1010
BG="#1c1b1a"; PANEL="#232120"; EDGE="#4a463f"; TEXT="#e6e0d4"; MUTED="#9a9488"
GREEN="#7fd1a8"; AMBER="#e0a24a"; RED="#d97a7a"
FONT="Consolas, 'Microsoft YaHei', monospace"

o=[]; A=o.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
A(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
A(f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{EDGE}"/></marker></defs>')

def esc(t): return html.escape(t)
def box(x,y,w,h,title,lines=(),accent=MUTED,fs=12.5):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PANEL}" stroke="{accent}" stroke-width="1.4"/>')
    A(f'<rect x="{x}" y="{y}" width="3.5" height="{h}" fill="{accent}"/>')
    A(f'<text x="{x+15}" y="{y+23}" font-family="{FONT}" font-size="13.5" fill="{TEXT}" font-weight="bold">{esc(title)}</text>')
    for i,ln in enumerate(lines):
        A(f'<text x="{x+15}" y="{y+43+i*18}" font-family="{FONT}" font-size="{fs}" fill="{MUTED}">{esc(ln)}</text>')
def region(x,y,w,h,label,color=EDGE):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" stroke="{color}" stroke-width="1.2" stroke-dasharray="5 5"/>')
    A(f'<text x="{x+14}" y="{y+21}" font-family="{FONT}" font-size="12" fill="{MUTED}" letter-spacing="2">{esc(label)}</text>')
def arrow(x1,y1,x2,y2,color=EDGE,dashed=False,label=None,anchor="middle"):
    d=' stroke-dasharray="5 4"' if dashed else ''
    A(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{d} marker-end="url(#ar)"/>')
    if label:
        A(f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-7}" font-family="{FONT}" font-size="11.5" fill="{color}" text-anchor="{anchor}">{esc(label)}</text>')
def band(x,y,w,h,fill,label,sub,color):
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{fill}" stroke="{color}" stroke-width="1.2"/>')
    A(f'<text x="{x+14}" y="{y+25}" font-family="{FONT}" font-size="14" fill="{color}" font-weight="bold">{esc(label)}</text>')
    A(f'<text x="{x+14}" y="{y+46}" font-family="{FONT}" font-size="12" fill="{MUTED}">{esc(sub)}</text>')

A(f'<text x="44" y="50" font-family="{FONT}" font-size="25" fill="{TEXT}" font-weight="bold">VOLTA</text>')
A(f'<text x="146" y="50" font-family="{FONT}" font-size="14.5" fill="{MUTED}">三件事的共同机制：分级 + 声明式 + 自动门禁</text>')
A(f'<line x1="44" y1="66" x2="{W-44}" y2="66" stroke="{EDGE}"/>')

# ── 左：多路性能分级 ──
region(36,90,470,860,"A · 多路性能分级")
A(f'<text x="56" y="126" font-family="{FONT}" font-size="13" fill="{TEXT}">同一时刻，格子分三档</text>')
band(56,140,430,66,"#1d2a22","focused（焦点格）","原生分辨率 · 全套着色器 · 出声",GREEN)
band(56,218,430,66,"#221f1a","active（可见格）","dwidth=显示尺寸 · 轻量着色器 · 静音",AMBER)
band(56,296,430,66,"#201d1d","dormant（休眠格）","dwidth=显示尺寸 · 无着色器 · 不渲染",RED)
A(f'<text x="56" y="392" font-family="{FONT}" font-size="12.5" fill="{MUTED}">像素吞吐（1600×900 窗口 / 2×2 网格）</text>')
for i,(name,val,pct,col) in enumerate([
    ("焦点 1080p60","124.4 Mpix/s","100%",GREEN),
    ("8 个背景格（按显示尺寸）","156.1 Mpix/s","125%",AMBER),
    ("8 路都按 1080p 渲染（错）","995.3 Mpix/s","800%",RED)]):
    y=408+i*30
    A(f'<text x="56" y="{y}" font-family="{FONT}" font-size="12" fill="{TEXT}">{esc(name)}</text>')
    A(f'<text x="270" y="{y}" font-family="{FONT}" font-size="12" fill="{col}">{esc(val)}</text>')
    A(f'<text x="400" y="{y}" font-family="{FONT}" font-size="12" fill="{col}">{esc(pct)}</text>')
A(f'<rect x="56" y="504" width="430" height="52" rx="5" fill="#241f18" stroke="{AMBER}" stroke-width="1.2"/>')
A(f'<text x="70" y="526" font-family="{FONT}" font-size="12.5" fill="{AMBER}">差距 6× —— 瓶颈不是「几路」，是「每路渲染多大」</text>')
A(f'<text x="70" y="546" font-family="{FONT}" font-size="12" fill="{MUTED}">手段：dwidth/dheight = 滤镜后显示尺寸（源尺寸是 width/height）</text>')
A(f'<text x="56" y="586" font-family="{FONT}" font-size="12.5" fill="{TEXT}">自适应降级（读 mpv 原生属性，不自写状态机）</text>')
for i,t in enumerate(["frame-drop-count 增长 → 降 dwidth 一档",
                       "仍掉帧 → 关可选着色器",
                       "仍掉帧 → 转 dormant（停渲染）",
                       "连续 N 次正常 → 逐级回升（迟滞防震荡）"]):
    A(f'<text x="70" y="{608+i*22}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">▸ {esc(t)}</text>')

# ── 中：主题令牌分层 ──
region(530,90,470,860,"B · 主题可扩展")
A(f'<text x="550" y="126" font-family="{FONT}" font-size="13" fill="{TEXT}">令牌三层，优先级低 → 高</text>')
for i,(t,s,c) in enumerate([("base.json","尺寸 / 动效基准（所有主题共有）",MUTED),
                              ("theme.json","颜色 / 字体 / 圆角 / 视频特效声明",GREEN),
                              ("组件私有微调","只允许引用令牌，禁止定义裸色",AMBER)]):
    y=140+i*58
    A(f'<rect x="550" y="{y}" width="430" height="48" rx="5" fill="{PANEL}" stroke="{c}" stroke-width="1.3"/>')
    A(f'<text x="566" y="{y+20}" font-family="{FONT}" font-size="13" fill="{c}" font-weight="bold">{esc(t)}</text>')
    A(f'<text x="566" y="{y+38}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">{esc(s)}</text>')
    if i<2: A(f'<line x1="565" y1="{y+48}" x2="565" y2="{y+58}" stroke="{EDGE}" stroke-width="1.5" marker-end="url(#ar)"/>')
A(f'<text x="550" y="330" font-family="{FONT}" font-size="12.5" fill="{TEXT}">新增一个主题 = 1 个 JSON（可选 1 个 QML）</text>')
A(f'<text x="550" y="356" font-family="{FONT}" font-size="11.5" fill="{MUTED}">theme.json 含 tokens + video(defaultShader / overlay) + capabilities</text>')
A(f'<text x="550" y="392" font-family="{FONT}" font-size="12.5" fill="{TEXT}">「全部生效」= 三道自动门禁</text>')
for i,(t,s,c) in enumerate([
    ("① 编译期","QML 出现裸色值 → 构建失败",GREEN),
    ("② 构建期","孤儿令牌 / 缺失引用 → CI 红",GREEN),
    ("③ 运行期","遍历 Item 检查属性是否在令牌集内",AMBER)]):
    y=410+i*52
    A(f'<rect x="550" y="{y}" width="430" height="42" rx="5" fill="{PANEL}" stroke="{c}" stroke-width="1.2"/>')
    A(f'<text x="566" y="{y+19}" font-family="{FONT}" font-size="12.5" fill="{c}" font-weight="bold">{esc(t)}</text>')
    A(f'<text x="646" y="{y+19}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">{esc(s)}</text>')
A(f'<rect x="550" y="576" width="430" height="60" rx="5" fill="#241f18" stroke="{AMBER}" stroke-width="1.2"/>')
A(f'<text x="566" y="{598}" font-family="{FONT}" font-size="12.5" fill="{AMBER}">④ 截图回归：每主题 6 张关键界面逐像素比对</text>')
A(f'<text x="566" y="{618}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">换主题后有差异 = 有人偷偷改了组件层</text>')

# ── 右：语言管线 ──
region(1024,90,440,860,"C · 中英切换")
A(f'<text x="1044" y="126" font-family="{FONT}" font-size="13" fill="{TEXT}">不用 .ts 文件，自建 JSON 词典</text>')
box(1044,140,400,78,"I18n 单例（QML）",["t(key) 查表 · 查不到回退 ??key?? + WARN","切换 = 换 map + 发信号，不重建 QML 树"],GREEN)
A(f'<line x1="1244" y1="218" x2="1244" y2="240" stroke="{EDGE}" stroke-width="1.5" marker-end="url(#ar)"/>')
for i,(t,s) in enumerate([("zh-CN.json","中文"),("en.json","English")]):
    A(f'<rect x="1044" y="{246+i*46}" width="195" height="38" rx="5" fill="{PANEL}" stroke="{MUTED}" stroke-width="1.2"/>')
    A(f'<text x="1060" y="{246+i*46+24}" font-family="{FONT}" font-size="12" fill="{TEXT}">{esc(t)}</text>')
    A(f'<text x="1246" y="{246+i*46+24}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">{esc(s)}</text>')
A(f'<rect x="1249" y="246" width="195" height="38" rx="5" fill="{PANEL}" stroke="{MUTED}" stroke-width="1.2"/>')
A(f'<text x="1265" y="270" font-family="{FONT}" font-size="12" fill="{TEXT}">locale.json</text>')
A(f'<text x="1428" y="270" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">语言清单/排序</text>')
A(f'<rect x="1249" y="292" width="195" height="38" rx="5" fill="{PANEL}" stroke="{MUTED}" stroke-width="1.2"/>')
A(f'<text x="1265" y="316" font-family="{FONT}" font-size="12" fill="{TEXT}">i18n.py</text>')
A(f'<text x="1428" y="316" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">构建期校验</text>')
A(f'<text x="1044" y="360" font-family="{FONT}" font-size="12.5" fill="{TEXT}">「残留别的语言」三道防线</text>')
for i,(t,s,c) in enumerate([
    ("① 编译期","QML 里裸字面量当文案 → 报错",GREEN),
    ("② 构建期","各语言 key 集合必须完全相等",GREEN),
    ("③ 运行期","查不到 → 显示 ??key?? 一眼可见",AMBER)]):
    y=378+i*50
    A(f'<rect x="1044" y="{y}" width="400" height="40" rx="5" fill="{PANEL}" stroke="{c}" stroke-width="1.2"/>')
    A(f'<text x="1060" y="{y+18}" font-family="{FONT}" font-size="12.5" fill="{c}" font-weight="bold">{esc(t)}</text>')
    A(f'<text x="1060" y="{y+33}" font-family="{FONT}" font-size="11" fill="{MUTED}">{esc(s)}</text>')
A(f'<rect x="1044" y="534" width="400" height="72" rx="5" fill="#241f18" stroke="{AMBER}" stroke-width="1.2"/>')
A(f'<text x="1060" y="556" font-family="{FONT}" font-size="12.5" fill="{AMBER}">易漏的坑</text>')
A(f'<text x="1060" y="575" font-family="{FONT}" font-size="11.5" fill="{MUTED}">· 中英长度差 → 按钮宽度不写死 px</text>')
A(f'<text x="1060" y="593" font-family="{FONT}" font-size="11.5" fill="{MUTED}">· 字体栈必须含 CJK 回退，否则中文变方块</text>')
A(f'<text x="1044" y="634" font-family="{FONT}" font-size="12.5" fill="{TEXT}">CI 可自动验：切 en 后截图，正则扫残留汉字</text>')
A(f'<text x="1044" y="656" font-family="{FONT}" font-size="11.5" fill="{MUTED}">[\\u4e00-\\u9fff] 命中数必须 = 0</text>')

# 底部：成本表
A(f'<text x="44" y="990" font-family="{FONT}" font-size="12.5" fill="{MUTED}">加新东西的代价：新主题 半天 ｜ 新语言 几小时 ｜ 新着色器 1 天 ｜ 新画质档 半天 ｜ 新引擎 1–2 周（只动 engine/ 一层）</text>')
A('</svg>')

p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"design.png.svg")
open(p,"w",encoding="utf-8").write("\n".join(o))
print("wrote",p,os.path.getsize(p))
