#pragma once
// 核心数据模型 —— 全部不依赖引擎、不依赖 UI，可单测。
// 分层契约（见 docs/adr）：
//   core/  纯逻辑，主题令牌、播放项、队列、库、视图栈、目录扫描
//   engine/ 引擎进程管理、IPC、帧传输（不碰 core 的数据结构语义）
//   ui/    只从 Theme 取样式，不含业务逻辑

#include <QString>
#include <QStringList>
#include <QVector>
#include <QVariantMap>

namespace volta {

// ─────────────────────────────────────────────────────────────
// 主题令牌（v2 §2.3 三层：base → theme → 组件私有）
// ─────────────────────────────────────────────────────────────

struct ThemeTokens {
    // 身份
    QString id, name;           // 主题 id / 显示名（字幕用，如「合成波·落日」）
    QString sound;              // 切主题时播的专属音效文件名（themes/<id>/ 下）
    QString style;              // 控件形态标记：terminal / pixel / luna / neon / lcd / modern
    // 颜色
    QString bg, surface, surfaceAlt, ink, inkDim, accent, accentDim;
    QString border, danger, warning, success;
    // 渐变（synthwave/luna 用；为空则退回纯 bg）
    QString bgTop, bgBottom;
    // 面板不透明度：有背景动画的主题透一点出来，纯色主题保持实心
    qreal panelAlpha = 1.0;
    // 字体
    QString fontFamily, fontMono;
    int fontSize = 13;
    // 形状
    int radiusPanel = 0, radiusButton = 0, radiusInput = 0;
    // 动效
    int motionDuration = 120;
    bool reduceMotion = false;
    // 能力开关（终端主题有扫描线/暗角，默认主题没有）
    bool scanlines = false, vignette = false, curvature = false, glow = false;
    bool cursorBlink = false;
    // 背景装饰层（QML 侧按这个画：grid=透视网格 / clouds=像素云 / bliss=草地天空 / none）
    QString deco;

    bool isValid() const { return !bg.isEmpty() && !ink.isEmpty() && !fontFamily.isEmpty(); }
};

// ─────────────────────────────────────────────────────────────
// 播放项（v5 §2）—— 队列和播放设置挂在这里，不是挂在槽位上
// ─────────────────────────────────────────────────────────────

enum class LoopMode { Off, File, Playlist };

struct PlayItem {
    QString source;             // 文件绝对路径
    QString title;              // 显示名（不含扩展名）
    int durationSec = 0;

    // 队列（该播放项接下来播什么）
    QStringList queue;

    // 播放设置
    LoopMode loopMode = LoopMode::Off;
    double abLoopA = -1.0, abLoopB = -1.0;
    double volume = 100.0;
    bool muted = false;
    int sid = -1, aid = -1;
    QStringList shaderChain;

    // 播放位置
    double timePos = 0.0;
    bool paused = false;

    // 渲染尺寸（按显示尺寸渲染，不是源分辨率）
    int renderWidth = 0, renderHeight = 0;

    QString displayName() const { return title.isEmpty() ? source : title; }
};

// ─────────────────────────────────────────────────────────────
// 素材来源（v5.1 §6）—— 目录扫描与手动添加统一成一种形状
// ─────────────────────────────────────────────────────────────

enum class ScanMode { FullDir, SingleFile };

struct ScanSource {
    QString rootPath;
    ScanMode mode = ScanMode::FullDir;
    QStringList items;          // 扫描到的视频绝对路径
    bool recursive = false;

    bool operator==(const ScanSource &o) const { return rootPath == o.rootPath; }
};

// ─────────────────────────────────────────────────────────────
// 库（全局唯一）
// ─────────────────────────────────────────────────────────────

class Library {
public:
    void addSource(const ScanSource &src);
    void removeSource(const QString &rootPath);
    void clear();

    const QVector<ScanSource> &sources() const { return m_sources; }

    // 某路径是否已在库中（用于去重）
    bool contains(const QString &path) const;

    // 库里所有条目（跨 source 汇总，去重）
    QStringList allItems() const;

private:
    QVector<ScanSource> m_sources;
};

// ─────────────────────────────────────────────────────────────
// 视图栈（v4）—— 存「完整视图快照」，不是「上一个布局」
// ─────────────────────────────────────────────────────────────

struct SlotState {
    int slotId = -1;
    QString source;
    double timePos = 0.0;
    bool paused = false;
    double volume = 100.0;
    bool muted = false;
    double abLoopA = -1.0, abLoopB = -1.0;
    int sid = -1, aid = -1;
    QStringList shaderChain;
    int renderWidth = 0, renderHeight = 0;
    QStringList queue;
    LoopMode loopMode = LoopMode::Off;
};

struct ViewSnapshot {
    QString viewMode;           // "grid" / "solo"
    int layoutCols = 2, layoutRows = 2;
    int focusSlotId = -1;
    // 注意：不能叫 slots —— Qt 的 qtmetamacros.h 把 slots 定义成宏 (#define slots Q_SLOTS)
    QVector<SlotState> slotStates;
    QVector<SlotState> detached;   // 被替换掉的播放项，还原时挂回
};

class ViewStack {
public:
    static constexpr int kMaxDepth = 16;

    bool push(const ViewSnapshot &snap);
    bool pop(ViewSnapshot *out);
    void clear();

    int depth() const { return m_stack.size(); }
    bool canPop() const { return !m_stack.isEmpty(); }
    const QVector<ViewSnapshot> &stack() const { return m_stack; }

private:
    QVector<ViewSnapshot> m_stack;
};

// ─────────────────────────────────────────────────────────────
// 目录扫描（v5.1）—— 自然排序是硬要求
// ─────────────────────────────────────────────────────────────

namespace scan {

// 视频扩展名白名单
bool isVideoExtension(const QString &path);

// 半成品/临时文件（下载中的）
bool isPartialFile(const QString &path);

// 自然排序 key：数字段按整数比，ep2 < ep10
bool naturalLess(const QString &a, const QString &b);

// 扫描目录（不递归），返回自然序排列的视频路径
QStringList scanDirectory(const QString &dirPath, bool recursive = false,
                          int maxItems = 5000, bool *truncated = nullptr);

} // namespace scan

// ─────────────────────────────────────────────────────────────
// 主题加载（v2 §2）
// ─────────────────────────────────────────────────────────────

namespace theme {

// 从 JSON 文件加载令牌；失败返回 false 并填 err
bool loadTokens(const QString &jsonPath, ThemeTokens *out, QString *err);

// 校验令牌完整性：主题之间必须提供同一套 key
// 返回缺失的 key 列表
QStringList validateTokenKeys(const QVariantMap &tokens,
                               const QStringList &requiredKeys);

} // namespace theme

} // namespace volta
