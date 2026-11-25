# ADR-0002：帧传输 —— 共享纹理 vs 帧拷贝

- **状态**：待验证（M0b）
- **相关**：ADR-0001

## 背景

mpv 独立进程后，帧必须跨进程送到 UI 侧。三档，按损耗从低到高：

| 档 | 做法 | 带宽（1080p BGRA8） |
|---|---|---|
| 共享纹理 | mpv 侧出 D3D11 共享句柄，UI 侧直接采样 | GPU→GPU，0 CPU 拷贝 |
| 共享内存 | mpv 侧写内存，UI 侧上传纹理 | 475 MB/s 单向（CPU 拷贝）|
| CPU 回读 | mpv 侧读回像素 | 同上但同步阻塞 |

## 关键发现：跨进程共享纹理走不通

读 mpv 0.42 的 `include/mpv/render_d3d11.h` 原文：

```c
typedef struct mpv_d3d11_init_params {
    /** The ID3D11Device to use for rendering. libmpv will add a reference... */
    void *device;
} mpv_d3d11_init_params;

typedef struct mpv_d3d11_fbo {
    /** The D3D11 texture to render into. This must be a 2D texture
        (ID3D11Texture2D) created on the same ID3D11Device... */
    void *tex;
} mpv_d3d11_fbo;
```

**device 与 texture 都归「调用方」所有。** 这是**嵌入 API** 的约定 —— 语义是「我给你 device 和纹理，你往里画」。

跨进程要共享纹理，得走 D3D11 shared handle + keyed mutex，**需要 mpv 侧导出它持有的 device 或纹理句柄**。而 mpv 不导出任何句柄：外部拿不到要共享的那个 `ID3D11Device`。

**结论：mpv 现有 API 下，跨进程共享纹理这条路走不通。**

## 决策

**并列三条，按平台与需求路由，全部封装在 `engine/` 一层后面：**

| 路径 | 做法 | 适用 | 状态 |
|---|---|---|---|
| **B** | `--wid` 原生窗口嵌套 | Windows 主路 | **已验证可用**（ADR-0001） |
| **C** | 进程内 libmpv + `render_context` | 需要 UI 无缝覆盖视频 | 待验证 |
| **A'** | 帧拷贝（共享内存 → 纹理） | 任何平台兜底 | 待验证 |

UI 侧接口统一为：

```cpp
class VideoSurface {
    virtual void attach(int slotId, const QString &source) = 0;
    virtual void setFocus(bool focused) = 0;
    virtual void setRenderSize(int w, int h) = 0;   // dwidth/dheight
    virtual void setShaderChain(const QStringList &chain) = 0;
    virtual void setAudioEnabled(bool) = 0;
};
```

将来 gpu-next 的 libmpv 后端合并 → 切路径只动 `engine/`，`ui/` 一行不改。

## 路径 B 的 z-order 难题（已知，未解决）

原生子 HWND **永远在 QML 之上** → 控制条、弹窗盖不住视频。

iptvnator 项目（4gray/iptvnator）的实战教训写得很清楚：
- macOS: `NSOpenGLView` layered under/over Chromium —— "fragile against OS compositor changes"，他们撞过 macOS 26.2 layering regression
- Windows: `--wid` 对着子 HWND —— "native surface stacking, no DOM overlays"
- 他们最终放弃这条路，全面转向帧拷贝（`spikes/mpv-frame-copy/DESIGN.md`）

**我们选的解法（比 iptvnator 简单）**：
- 网格布局里控制条固定在**下方**（GridPlayer 本来就这样），槽位内不放 UI → 绕开层级问题
- 单路沉浸模式才用「QML 挖洞露出子 HWND」
- 这样不用搞「独立透明 overlay 窗口 + 焦点/DPI/多屏同步」那套

## 帧拷贝路径的实测预算

1080p BGRA8 = 7.91 MB/帧：

| 场景 | 带宽 | 16 GB/s 机器占比 |
|---|---|---|
| 1 路 1920×1080@60 | 475 MB/s | 3.0% |
| 9 路 760×428@60 | 670 MB/s | 4.2% |
| 9 路背景 + 1 路焦点 | 1145 MB/s | 7.2% |
| （若背景格错按 1080p 渲染）9 路 | 4271 MB/s | 26.7% |

**关键：瓶颈不是「几路」，是「每路渲染多大」，差 6 倍。**
背景格按实际显示尺寸渲染（`dwidth`/`dheight`），省下的不是一点，是 6 倍。

iptvnator 的实测佐证：「4K 源在 720p 视口只花 720p 的代价」（`spikes/mpv-frame-copy/RESULTS.md`）。

## 何时推翻

- M0b 实测三条路径的延迟与 CPU 拷贝，如果共享纹理（B 变体）可行 → 优先用它
- 如果路径 B 的 z-order 在真实多屏环境下无法稳定工作 → 主路切 A'
