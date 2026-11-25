# Prism

> 视频播放器（棱镜：一束光分成多格画面）：单窗口多视频网格 · 七个主题各自带专属音效和背景动画 · 四路并播只有焦点格出声

**只有一个版本**：`build/bin/`。`bash build.sh` 一条命令构建 + 部署，产物自带 Qt 运行时、mpv.exe、主题、着色器，双击 `build/bin/prism.exe` 就跑，拷走整个 `build/bin/` 就是交付。没有 dev/dist 之分。（唯一入口是 `prism.exe`，带棱镜分光图标；`prism.exe` 只是给老测试脚本的同名副本，别双击它。）

## 快速开始

```bash
cd "/c/Users/16324/Downloads/volta"

bash build.sh                            # 唯一的构建命令：构建 + 部署到 build/bin/（双击即跑）
build/bin/prism.exe                      # 空启动
build/bin/prism.exe "路径/视频.mp4"       # 带文件启动 → 自动收录同目录
python tools/verify2.py                  # 全量回归（拉伸/全屏/网格/循环/A-B/排序…）
```

工具链全在项目内（Qt 6.10.2 mingw / CMake 3.31.6 / Ninja / gcc 15.2.0 / mpv 0.42.0），
**本机没有 MSVC**，编译必须指向 mingw_64。

---

## 能干什么

| 入口 | 说明 |
|---|---|
| 拖文件 / 拖文件夹 | 拖一个视频进来 → 自动收录整个目录（自然排序，ep2 在 ep10 前，中文也按数字比）|
| 「打开…」/ Ctrl+O / O | 系统原生文件对话框，带视频后缀过滤，从上次目录起步 |
| 命令行 | `prism.exe <文件>`，同样自动收录同目录 |
| 四路网格 | **按需长出来**：默认一格，`G` 或双击列表项加一格（最多到队列长度），`D` 收最后一格；格子的 ✕ 只关那一格 |
| 单击槽位 | 切焦点（该格出声，控制条接管它）|
| 双击槽位 / F | 独占该格（面板让位），Esc 返回 |
| F11 | 全屏（顶栏/侧栏藏起来，格子的控制条保留）|
| 空格 | 播放 / 暂停 |
| ← → | ±5 秒（Shift ±30 秒）|
| ↑ ↓ / 滚轮 | 音量（0-100，跨会话记忆）|
| M | 静音 |
| L | 循环三档：关 → 单集 → 整个队列（每格一起听令）|
| B | A-B 循环：按一次记 A，再按一次记 B，再按清除 |
| 1-4 | 直接切焦点槽位 |
| 播放列表 | 队列 = 网格里正在放的几格；库 = 打开过的全部文件，可按名称/修改时间/创建时间排序 |
| 播完 | 自动下一集，到队尾停（不循环，除非按 LOOP）|
| 控制条 | 播放/上下集/帧步/进度拖点/音量/LOOP(关·单集·全列)/A-B/独占/全屏/主题/着色 |
| 主题切换 | 控制条「主题」按钮或按 T，循环七个主题；每个主题有**专属背景动画（落日/网格/像素云/绿坡，从半透明面板透出）+ 专属 shader + 成套交互音效**，字体/圆角/控件形态整套换，不用重启 |
| 音效 | 全局音效引擎 `Sfx`：点按钮、悬停、切列表、播放暂停、快捷键都有音，每个主题一整套音色（tap/hover/nav/toggle），带节流不吵 |
| 着色器切换 | 控制条「着色」按钮或按 S；六个档位（关/CRT/VHS/霓虹/掌机LCD/像素）；**切主题自动套用该主题的专属 shader**，之后按 S 仍可覆盖 |

### 七个主题

| 主题 | 视觉签名（背景从面板透出） | 交互音色 ×4 | 专属 shader |
|---|---|---|---|
| 终端 terminal | 磷光绿、扫描线、暗角、闪烁光标、硬直角 | 下滑方波滴答 | CRT |
| 暗夜 default | Segoe UI、圆角、蓝调、克制无特效 | 柔和大三和弦 | 无 |
| 8位 nes | 红白机蓝底 + 金币金 + 像素方块云横漂、硬边 | 方波上升琶音（power-up）| 像素化 |
| Determination | 黑白 + 决心红、点阵、闪烁光标 | 三角波渐升颤音 | VHS |
| 蓝天 winxp | Luna 蓝渐变 + 绿坡、Tahoma、圆润 | 明亮分解和弦 | 无 |
| 合成波 synthwave | 紫夜空 + 左侧条纹落日 + 滚动透视网格、霓虹粉青 | 锯齿 sweep + 回声 | 霓虹 |
| 掌机 gameboy | 四阶绿、点阵、LCD 扫描线、硬边 | 方波 jingle | 掌机 LCD |

每个主题一个目录：`theme.json`（令牌 + 背景 + shader + 面板透明度）+ 5 个 wav（`sound.wav` 切换音 + tap/hover/nav/toggle 四种交互音）。主题从 `themes/` 动态发现——**丢一个新目录进去就是新主题**，不用改代码。背景动画画在最底层，面板按 `panel.alpha` 半透明透出；落日/网格/云/绿坡都落在面板可见区，不是藏在视频底下。

---

## 目录

| 路径 | 内容 |
|---|---|
| `src/core/` | 纯逻辑：主题令牌、播放项、库、视图栈、目录扫描、应用控制器（不依赖 UI/引擎）|
| `src/engine/` | libmpv → QQuickFramebufferObject，播放控制 + 状态回读 |
| `src/qml/` | QML 界面，颜色字体只能从 Theme 单例取；`ThemeBackdrop.qml` 画各主题的背景动画 |
| `src/main.cpp` | 入口：主题加载 + 单例注册 + QML 加载 + 日志 |
| `app.ico` / `src/app.rc` | Prism 应用图标（棱镜分光 + 播放三角），嵌进 exe |
| `themes/<id>/` | 七个主题，每个一个 `theme.json`（令牌）+ `sound.wav`（专属音效）；动态发现 |
| `shaders/` | CRT / VHS 用户着色器（mpv `glsl-shaders` 语法，`//!HOOK MAIN`）|
| `tools/` | 构建/验证/截图脚本（`verify2.py` 全量回归 · `hittest.py` 八边命中 · `poke.py` 逐条戳）|
| `docs/` | 设计文档 + `adr/` 架构决策记录 |
| `HANDOFF.md` | **接手必读**：进度、坑、命令 |
| `mpv/ mpvbin/` | libmpv + 完整 mpv 0.42.0 |
| `media_long/` | 60 秒测试片（回归脚本固定件）|

---

## 文档

| 文件 | 内容 |
|---|---|
| `HANDOFF.md` | 当前进度、踩过的坑、接手命令（**先读这个**）|
| `docs/adr/0001-render-architecture.md` | 为什么最初想用 mpv 独立进程 |
| `docs/adr/0002-frame-transport.md` | 帧传输三条路径与实测带宽预算 |
| `docs/adr/0003-qml-module-layout.md` | 为什么 QML 走 qrc 而不是 qt_add_qml_module |
| `docs/VOLTA-ARCH.md` | 总架构 |
| `docs/VOLTA-DESIGN-v2.md` | i18n / 主题令牌 / 多路性能预算 |
| `docs/VOLTA-DESIGN-v3.md` | 三条渲染路径 / HDR×网格互斥 |
| `docs/VOLTA-INTERACTION-v4.md` | 视图历史栈（双击独占/还原）|
| `docs/VOLTA-PLAYLIST-v5.md` | Library / PlayItem / Slot 三层 |
| `docs/VOLTA-DIRECTORY-v5.1.md` | 打开文件自动收录同目录 |

---

## 当前状态

**已跑通（实机验证，`python tools/verify2.py` → 25/25，`tools/` 里都是可复跑的命令）**
- 多路 libmpv 同时解码（按需 1–4 格），`QSG_RHI_BACKEND=opengl` + beforeRendering 建渲染上下文
- 暂停/播放/音量/静音/位置全部从 mpv 回读，UI 不再自己编状态
- 片尾自动下一集（判定用 `eof-reached`，`keep-open` 下 mpv 不发 END_FILE）
- 单集循环 / A-B 循环（自己轮询，不依赖 mpv 的 loop 属性）
- 无边框窗口：八边拉伸、双击最大化、最小化、全屏（退出后不留白带）
- 键盘全键位、每格自带控制条、原生文件对话框、库排序、缩略图、主题/着色器切换
- 七个主题：各自专属背景动画（落日网格/像素云/Luna 绿坡/点阵）+ 专属合成音效 + 字体/圆角/控件形态差异；切主题有扫描线转场
- 反馈动效：toast 滑入弹入发光、列表项进出场、hover 侧边条滑入
- 版本统一：`bash build.sh` 一条命令产出可直接双击的完整版本，无 dev/dist 双轨

**没做**（详见 `NEXT.md`）
- 着色器逐帧动画（现在是静态 glsl + QML 叠加）、库目录筛选、拖动进度的时间气泡
