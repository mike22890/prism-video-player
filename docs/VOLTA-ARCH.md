# VOLTA — 视频播放器技术方案

> 状态：方案稿 v1 ｜ 日期 2026-11-15 ｜ 目标平台 Windows 11 优先（可移植 Linux/macOS）

---

## 0. 一句话定位

**VOLTA** = 单窗口多视频网格播放器 + 真主题系统（终端磷光 / 默认）+ GPU 画质增强 + CRT/VHS 着色器。
不是「换个 mpv 皮肤」，是从解码到像素输出的整条管线自己控。

---

## 1. 关键事实（2026-11-15 实查，非记忆）

| 事实 | 出处 | 对方案的影响 |
|---|---|---|
| mpv 最新稳定版 **0.42.0**，发布于 2026-11-05 | mpv-player/mpv Releases | 底座锁 0.42.0 |
| 0.42 新增 **libmpv 的 D3D11 渲染后端**（`MPV_RENDER_API_TYPE_D3D11`） | RELEASE_NOTES / DOCS/client-api-changes.rst | Windows 上不必绕 OpenGL 互操作，性能路径更短 |
| 0.42 新增 **libcurl 网络后端**（HTTP/2、HTTP/3、连接复用） | 同上 | 流媒体直连不再需要外挂 yt-dlp 管道 |
| 0.42 新增 **OSC ↔ 第三方缩略图脚本通信 API**（`user-data/osc/draw-preview`） | commit 09d075f | 进度条预览缩略图有官方对接点，不用自造协议 |
| 0.42 初步支持**着色器参数运行时可调**（specialization constants，免重编译） | 9to5Linux 报道 | CRT/VHS 参数可实时拖动 |
| **`vo_gpu_next`（libplacebo）至今没有 libmpv 渲染后端** | PR #16818 open（2025-09-20）、RFC #18607 open（2026-10-13） | **决定性约束，见 §2** |
| libplacebo 自定义着色器语法 = mpv `//!HOOK` 语法，但 hook 点与 mpv 不完全一致（无 `MAINPRESUB`） | libplacebo.org/custom-shaders | 着色器要按 libplacebo 语法写，不能直接抄 mpv 老 shader |
| mpv 原生支持 `--loop-file` / `--loop-playlist` / `--ab-loop-a` / `--ab-loop-b` / `--ab-loop-count` | mpv manual | A-B 循环不要自己写状态机，直接映射属性 |
| mpv `--profile-cond` 可按分辨率/文件名**自动切 shader 档** | mpv manual + 各社区配置 | 「智能增强」的落点就是 profile 条件 |
| Haruna（KDE）= Qt6/QML + libmpv，331★，2026-11-13 仍在提交 | GitHub API 实查 | 前端栈选型的活证据 |
| mpvqt（KDE）= Qt6 + libmpv 封装，2026-10-26 有更新 | GitHub API 实查 | libmpv↔QML 桥接不必自己写 |
| GridPlayer 用 VLC + **每视频一进程**（2166★，2026-11-03 更新） | GitHub API 实查 | 崩溃隔离的现成参考模式 |
| shinchiro/mpv-winbuild-cmake 每月发 Windows 构建（最新 tag 20261111），`mpv-dev-*.7z` 内含 `libmpv-2.dll` + 头文件 | Releases | Windows 分发方案 = 打包官方 dev 构建，不自编 FFmpeg |

---

## 2. 架构决策：为什么渲染后端选独立进程而非嵌入 libmpv

mpv 有两条画质管线：

- **vo_gpu_next**（libplacebo）：HDR tonemap、scRGB、Dolby Vision P7、色彩管理全面领先。
- **vo_gpu / libmpv 渲染 API**：能被第三方 GUI 嵌入的那条路。

**问题**：gpu-next 至今（2026-11）没有 libmpv 渲染后端。要嵌进自己的窗口就得放弃 gpu-next。

**本方案的选择**：**不嵌 libmpv，改用 mpv 独立进程 + 自研前端合成**。

理由三条：
1. **保住 gpu-next**：画质上限（色彩/HDR/锐化）是「画面全方面更好且损耗小」的根基，砍掉它整条产品线就废了。
2. **保住隔离**：GridPlayer 的经验是每视频独立进程，一个解码崩了不带走整个网格。mpv 进程天然满足。
3. **保住可维护**：mpv 负责「解码+色彩+缩放+着色器」，我们的进程只负责「合成+UI+主题+调度」。职责边界极清晰，第三方 GUI 要重写的部分我们一个都不用重写。

**代价**（明说）：多一个 IPC 边界，帧同步要做对；跨进程不能共享 GPU 纹理，需要走 D3D11 共享纹理或共享内存。

**缓解**：mpv 0.42 刚加的 **D3D11 渲染后端** 正是为跨进程/跨 API 共享准备的——Windows 上用 D3D11 共享句柄传帧，避免 CPU 回读。这是本方案的技术赌注，也是要先做技术验证的第一件事。

---

## 3. 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 播放内核 | **mpv 0.42.0 独立进程**，每个视频槽位一个实例 | 拿 gpu-next 画质 + 崩溃隔离 |
| 帧传输 | **D3D11 共享纹理**（Windows），Linux/macOS 走 Vulkan/Metal 共享 | 零 CPU 回读，延迟可控 |
| 前端框架 | **Qt 6.10 QML** | Haruna 已验证；QML 声明式 → 主题可整套换掉；`QQuickFramebufferObject` 接 D3D11 帧 |
| 主题系统 | **QML 主题单例 + 设计令牌**，全部控件只读令牌 | 换主题 = 换令牌集，天然全生效 |
| 着色器 | libplacebo `//!HOOK` 语法自研 + 社区移植（crt-lottes / vhs / ArtCNN / FSRCNNX） | 增益可控、参数可调 |
| 缩略图 | mpv 进程内离屏抽帧 + 磁盘缓存 | 复用同一个内核，零额外依赖 |
| 构建 | CMake + vcpkg（Qt6）+ 官方 mpv-dev 二进制 | 不自编 FFmpeg/mpv |

---

## 4. 模块结构

```
volta/
├─ core/                    # 与播放无关的纯逻辑，易测
│  ├─ theme/                # 主题令牌定义 + 切换广播
│  ├─ playlist/             # 播放列表模型、循环模式机、A-B 区间
│  ├─ layout/               # 网格布局计算（1/2x2/3x3/自由拼贴）
│  └─ enhance/              # 画质档位决策 → 生成 mpv profile
├─ engine/                  # mpv 进程管理
│  ├─ mpvprocess/           # 启停、IPC（JSON IPC）、属性订阅
│  ├─ frametransport/       # D3D11 共享纹理 / Vulkan 共享
│  └─ profiles/             # 高质量档、SD 修复档、HDR→SDR 档
├─ ui/                      # QML
│  ├─ shells/               # default.qml / terminal.qml  ← 主题壳
│  ├─ components/           # 播放列表项、槽位、控制条、设置面板
│  └─ shaders/              # QML 侧 CRT 扫描线 / 暗角叠加层
└─ shaders/                 # libplacebo 侧（GLSL）
   ├─ crt/  vhs/  enhance/  noise/
```

**错误定位约定**：崩溃日志带 `[层/文件:行]`，播放失败永远指到具体 mpv 属性（如 `ab-loop-b` 越界）而非「播放出错」。

---

## 5. 需求 → 实现映射

| 你的需求 | 实现 | 落点 |
|---|---|---|
| 瞬间迅速 | 播放列表项**懒加载**：只解析元数据+抽一帧缩略图，不预解码；mpv 进程按需启停 | core/playlist |
| 缩略图播放列表 | 每个文件用离屏 mpv 抽 1 帧 → JPEG 落盘缓存（按 mtime+size 做 key） | engine/mpvprocess |
| 单个循环 / 全部循环 | `loop-file=inf` / `loop-playlist=inf`，属性直推 | core/playlist → mpv 属性 |
| A-B 点循环 | `ab-loop-a` / `ab-loop-b` / `ab-loop-count`，UI 上打点存时间戳 | core/playlist |
| 自动智能增强（色彩/画面全面更好、损耗小） | mpv `profile-cond` 按分辨率/源类型自动切档：低分辨率→去色带+锐化；1080p→ewa_lanczossharp；4K→纯透传不浪费算力 | core/enhance → engine/profiles |
| 主题切换**全部生效** | 令牌化 + 壳层切换 + **构建期令牌覆盖率检查**（任何硬编码颜色/字体直接 CI 失败） | ui/shells |
| 终端主题（辐射/CRT 味） | 独立 shell：磷光绿 `#33ff66`、扫描线、暗角、辉光、CRT 弯曲、闪烁光标 | ui/shells/terminal.qml |
| 默认主题 | 深色现代材质（毛玻璃 + 高对比） | ui/shells/default.qml |
| 一实例多视频（GridPlayer 式） | 每个槽位 = 一个 mpv 进程 + 一个 D3D11 共享纹理 → 一个 QML Item | engine + ui |
| CRT 着色器 | 自研 libplacebo 版（barrel 弯曲 + 孔栅 + 辉光 + 色散） | shaders/crt |
| VHS 着色器 | 自研（色度渗漏 + 水平撕裂 + 噪点 + 场抖动） | shaders/vhs |
| 易辨认错误位置 | 分层日志 + mpv 属性级错误映射表 | core + engine |

---

## 6. 主题系统：怎么保证「切换了到处都变了」

这是最容易做成半成品的部分。规矩：

1. **所有颜色/字体/间距/圆角/动效时长，只能从 `Theme` 令牌取**，QML 里出现字面量 `#rrggbb` 即构建失败。
2. **主题 = 令牌集 + 壳层文件 + 视频侧 shader 预设**，三者绑定。终端主题会同时切：UI 壳 + 视频区 CRT 叠加 + 缩略图边框样式。
3. **切换是热插拔**：令牌是绑定属性，切换只重发信号，不重建 QML 树 → 切换耗时 < 16ms。
4. **覆盖检查脚本**：扫描 QML 源码，输出未走令牌的硬编码清单，CI 红则不过。

---

## 7. 里程碑

| 阶段 | 产出 | 验收标准 |
|---|---|---|
| **M0 验证**（最优先） | D3D11 共享纹理把 mpv 帧送进 QML 显示，延迟 < 30ms | 1080p60 连续 10 分钟不撕裂、CPU 拷贝为 0 |
| **M1 单视频** | 单槽位 + 完整控制条 + A-B 循环 + 缩略图 | 一条视频的所有循环模式可切换且正确 |
| **M2 主题** | 两套壳 + 令牌化 + 覆盖率检查 | 切主题后截图逐像素比对，零硬编码残留 |
| **M3 网格** | 多进程多槽位 + 布局切换 | 4 路 1080p 同时播，掉帧 < 1% |
| **M4 着色器** | CRT + VHS + 增强档 | 参数实时可调，不重启 |
| **M5 打磨** | 快捷键、错误提示、性能面板 | 崩溃日志能直接指到模块 |

M0 是生死线，先做；M0 不通就退回 OpenGL 共享路径（性能差一点，但不换架构）。

---

## 8. 风险与对策

| 风险 | 概率 | 对策 |
|---|---|---|
| D3D11 共享纹理跨进程不稳 | 中 | M0 优先验证；备选 OpenGL 共享 / 内存映射 |
| mpv 多进程音频打架 | 中 | 每个实例静音除主控槽；音量统一由主控管理 |
| 着色器语法 gpu-next/vo_gpu 差异 | 中 | 只写 libplacebo 语法并锁版本；建 shader CI（逐个编译通过才合） |
| 主题覆盖率漏网 | 高 | 令牌化 + CI 硬门禁（§6.4） |
| FFmpeg/mpv 版本漂移 | 低 | 锁 0.42.0 tag + 官方 dev 二进制 |
| GridPlayer 式进程开销 | 低 | 懒启动 + 空闲回收策略 |

---

## 9. 待你拍板的三个岔路

1. **前端框架**：Qt 6 QML（我推荐，Haruna 背书、主题最好做）vs Tauri/Rust + Web（UI 快但接 D3D11 帧更绕）vs 原生 WinUI3（丑且难跨平台）。
2. **终端主题色**：磷光绿 `#33ff66`（辐射味）vs 琥珀 `#ffb000`（老终端味）vs 青绿（vt220）。默认我给磷光绿。
3. **画质增强档默认强度**：`平衡`（推荐）vs `极致`（开 AI 超分，掉帧风险）vs `保守`（只色彩）。
