# ADR-0001：渲染架构 —— mpv 独立进程，不嵌 libmpv

- **状态**：已定（2026-11-15）
- **相关**：ADR-0002（帧传输路径）、ADR-0003（QML 模块组织）

## 背景

VOLTA 需要：单窗口内多路视频同时播放、每路独立控制、完整 GPU 画质管线（HDR tonemap / scRGB / Dolby Vision P7）、单路崩溃不影响其他。

mpv 有两条渲染管线：

| 管线 | 能力 | 可嵌入渲染 API |
|---|---|---|
| `vo_gpu_next`（libplacebo） | HDR tonemap、scRGB、Dolay Vision P7、新色彩管理 | **mpv 0.42 仍没有** |
| `vo_gpu` / libmpv render API | 旧管线，能力弱一截 | 有（OpenGL / D3D11 / SW 三种） |

上游 `vo_libmpv` 的 gpu-next 渲染后端长期挂着未合并的 PR/RFC：
- PR #16818 `vo_libmpv: introduce 'gpu-next' render backend` —— open，2025-09-20 起
- RFC #18607 `vo_libmpv: add gpu-next OpenGL render API` —— open，2026-10-13

**RFC 和 open 的 PR 一律按「不存在」算。**

## 决策

**采用 mpv 独立进程 + 自建合成层，不嵌 libmpv。**

具体：
- 每个视频槽位 = 一个独立 mpv 进程（`vo=gpu-next`），保住完整 libplacebo 管线
- 帧传输走 D3D11 共享纹理（Windows），mpv 侧出共享句柄，UI 侧直接采样
- 我们自己的进程只负责「合成 + UI + 主题 + 调度」

## 备选与否决理由

| 备选 | 否决理由 |
|---|---|
| 嵌入 libmpv（render API） | 只有老 `vo_gpu`，丢 HDR/scRGB/DV P7，「画面全方面更好」的根基没了 |
| 单进程多 handle | mpv 内部会互相拖死；崩一个全崩。GridPlayer 的经验是每视频一进程 |
| 自写视频引擎 | 解码/色彩/缩放/硬解被 FFmpeg+mpv 打磨十几年，重写必屎山 |

## 后果

**好处**
- 画质上限保住（这是产品的核心卖点）
- 崩溃隔离白送：单格崩了只重启那一格
- 职责边界极清晰：mpv 管解码+色彩+缩放+着色器，我们管合成+UI+主题+调度

**代价（明说）**
- 多一个 IPC 边界，帧同步要做对
- 跨进程不能共享 GPU 纹理，需要共享句柄机制（见 ADR-0002）
- 进程数 = 视频数，每个进程有固定开销（~100MB 内存量级），空闲槽位要回收

## 何时推翻

- 上游 gpu-next 的 libmpv 渲染后端合并进稳定版 → 切回嵌入路径，`engine/` 一层隔离，切换成本 1–2 周
- 共享纹理方案实测延迟不可接受（>50ms）→ 改帧拷贝，代价是内存带宽

## 验证记录

M0a 探针（`m0a_probe/probe2.c`，纯 Win32，不依赖 Qt）实测：

```
zorder_child_is_first=1     子 HWND 在父窗口子窗口序列最前
mpv_alive=1                  mpv 进程存活
mpv_toplevel_count=4         全 visible=0 → mpv 没开额外顶层窗口
dpi_parent=144               本机 150% 缩放
scale_factor_x=1.50
```

截图 `m0a_child.png`：testsrc2 彩条完整渲染进子 HWND，左上角有 mpv OSD 时间码。
**证明 `vo=gpu-next` 走 `--wid` 可用，完整新管线保住了。**
