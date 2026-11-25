#pragma once
// 进程内 libmpv 播放器 —— 把 mpv 的画面接到 QML。
//
// 架构（ADR-0001 的路径 C）：
//   libmpv 进程内跑 → 走 MPV_RENDER_API_TYPE_OPENGL 渲染到
//   QQuickFramebufferObject 提供的 FBO → QML 场景图合成。
//
// 为什么先做这个：
//   - libmpv-2.dll 和头文件已经有了（mpv-dev 包）
//   - 不需要跨进程传帧（共享纹理那条路 mpv 不导出 handle，见 ADR-0002）
//   - 画面能直接进 QML 场景图 → 主题叠加层（扫描线/暗角/CRT）能盖在视频上
//
// 代价（已知）：
//   - libmpv 渲染 API 目前走的是老 vo_gpu，拿不到 gpu-next 的 libplacebo 管线
//   - 多路同开时每个槽位一个 mpv_handle，开销比独立进程小但也不是零
//
// 后续：gpu-next 的 libmpv 后端上游合并后（PR #16818），这里换实现即可，
//       QML 侧和 core 侧一行不改。

#include <QObject>
#include <QQuickFramebufferObject>
#include <QImage>
#include <QUrl>
#include <QTimer>
#include <QElapsedTimer>
#include <atomic>

struct mpv_handle;
struct mpv_render_context;
class QOpenGLContext;

namespace volta {

class MpvPlayer;

// QML 侧可见的播放器对象
class MpvItem : public QQuickFramebufferObject {
    Q_OBJECT
    QML_NAMED_ELEMENT(MpvItem)
    Q_PROPERTY(QString source READ source WRITE setSource NOTIFY sourceChanged)
    Q_PROPERTY(bool paused READ paused WRITE setPaused NOTIFY pausedChanged)
    Q_PROPERTY(double position READ position WRITE setPosition NOTIFY positionChanged)
    Q_PROPERTY(double duration READ duration NOTIFY durationChanged)
    Q_PROPERTY(bool loaded READ loaded NOTIFY loadedChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(QString videoSize READ videoSize NOTIFY videoSizeChanged)
    Q_PROPERTY(int videoWidth READ videoWidth NOTIFY videoSizeChanged)
    Q_PROPERTY(int videoHeight READ videoHeight NOTIFY videoSizeChanged)
    Q_PROPERTY(int qualityTier READ qualityTier WRITE setQualityTier NOTIFY qualityTierChanged)
    Q_PROPERTY(int renderScale READ renderScale WRITE setRenderScale NOTIFY renderScaleChanged)

public:
    explicit MpvItem(QQuickItem *parent = nullptr);
    ~MpvItem() override;

    QString source() const { return m_source; }
    void setSource(const QString &s);
    bool paused() const { return m_paused; }
    void setPaused(bool p);
    double position() const { return m_position; }
    void setPosition(double p);
    double duration() const { return m_duration; }
    bool loaded() const { return m_loaded; }
    QString lastError() const { return m_lastError; }
    QString videoSize() const { return m_videoSize; }
    int videoWidth() const { return m_videoWidth; }
    int videoHeight() const { return m_videoHeight; }
    // 画质档位 0=省电 1=均衡 2=最佳；独占时设2、多路降1
    int qualityTier() const { return m_qualityTier; }
    void setQualityTier(int tier);
    // 渲染长边像素：0=自动(跟随item)；>0=固定(独占时给足清晰度)
    int renderScale() const { return m_renderScale; }
    void setRenderScale(int px);

    // QQuickFramebufferObject
    QQuickFramebufferObject::Renderer *createRenderer() const override;

    // ── 播放控制（给 TransportBar / 快捷键调）──
    Q_INVOKABLE void togglePlay();
    Q_INVOKABLE void play();
    Q_INVOKABLE void pause();
    Q_INVOKABLE void seekTo(double seconds);
    Q_INVOKABLE void seekRelative(double deltaSeconds);
    Q_INVOKABLE void setAbLoop(double a, double b);
    Q_INVOKABLE void clearAbLoop();
    Q_INVOKABLE void setVolume(double v);
    Q_INVOKABLE void setMuted(bool m);
    // 循环模式：0=关 1=单集 2=整列。QML 侧一直调的是 setLoopMode()，
    // 而 C++ 这边只有内部的 setLoopModeValue() —— 从没暴露给 QML，
    // 于是 LOOP 按钮点下去只有一句 TypeError。这个坑留一行注释在这儿。
    Q_INVOKABLE void setLoopMode(int mode);
    Q_INVOKABLE void stepFrame(int delta);
    // 着色器档位：""=关 / "crt" / "vhs"（文件在项目 shaders/ 目录）
    Q_INVOKABLE void setShaderProfile(const QString &name);
    Q_PROPERTY(double volume READ volume NOTIFY volumeChanged)
    Q_PROPERTY(bool muted READ muted NOTIFY mutedChanged)
    Q_PROPERTY(bool abLoopActive READ abLoopActive NOTIFY abLoopChanged)
    Q_PROPERTY(double abLoopA READ abLoopA NOTIFY abLoopChanged)
    Q_PROPERTY(double abLoopB READ abLoopB NOTIFY abLoopChanged)
    Q_PROPERTY(int loopMode READ loopMode NOTIFY loopModeChanged)

    double volume() const { return m_volume; }
    bool muted() const { return m_muted; }
    bool abLoopActive() const { return m_abA >= 0.0 && m_abB > m_abA; }
    double abLoopA() const { return m_abA; }
    double abLoopB() const { return m_abB; }
    int loopMode() const { return m_loopMode; }   // 0=off 1=file 2=playlist

    void setVolumeValue(double v);
    void setMutedValue(bool m);
    void setAbLoopValues(double a, double b);
    void setLoopModeValue(int mode);

    // 内部 setter（在 signals 段之外 —— moc 不允许信号段里有普通函数）
    void setDuration(double d);
    void setLoaded(bool v);
    void setLastError(const QString &e);
    void setVideoSize(const QString &s);
    void requestRender();

    // 目标 FBO 尺寸的唯一真源：createFramebufferObject() 和 synchronize()
    // 都从这里取，禁止各算一套（差 1px 就成了每帧重建）。
    QSize preferredFboSize() const;

    // 窗口正在被拖动/最大化（250ms 内有几何变化）。渲染线程用它决定
    // 「这一帧先别画」——拖动期间冻结在最后一帧，GPU 完全不碰 mpv，
    // 把带宽全留给 DWM 的窗口合成。跨线程读，所以是 atomic 的毫秒戳。
    bool resizingNow() const;

    // 引擎 → UI 的单向同步：mpv 自己改的状态（播完、外部暂停、音量）
    // 用这条路进来，不能再回写 mpv，否则形成回环。
    void setPausedFromEngine(bool p);

    MpvPlayer *player() const { return m_player; }

signals:
    void sourceChanged();
    void pausedChanged();
    void positionChanged();
    void durationChanged();
    void loadedChanged();
    void lastErrorChanged();
    void videoSizeChanged();
    void videoWidthChanged();
    void videoHeightChanged();
    void qualityTierChanged();
    void renderScaleChanged();
    void volumeChanged();
    void mutedChanged();
    void abLoopChanged();
    void loopModeChanged();
    // 播到文件末尾（EOF）。QML 侧据此推进队列。
    void playbackEnded();

private:
    // QQuickItem 的几何变化（GUI 线程）→ 记时间戳给渲染线程判断「在 resize」。
    void geometryChange(const QRectF &newGeometry, const QRectF &oldGeometry) override;

    QString m_source;
    // mpv 的默认 pause=no —— 初值跟着引擎走，不是跟着 UI 的错觉走
    bool m_paused = false;
    double m_position = 0.0;
    double m_duration = 0.0;
    bool m_loaded = false;
    QString m_lastError;
    QString m_videoSize;
    int m_videoWidth = 0;
    int m_videoHeight = 0;
    int m_qualityTier = 1;
    int m_renderScale = 0;
    double m_volume = 100.0;
    bool m_muted = false;
    double m_abA = -1.0;
    double m_abB = -1.0;
    int m_loopMode = 0;
    MpvPlayer *m_player = nullptr;
    bool m_updatePending = false;
    std::atomic<qint64> m_lastGeomChangeMs{0};   // GUI 线程写、渲染线程读
};

// 真正干活的：mpv handle + 渲染上下文
class MpvPlayer : public QObject {
    Q_OBJECT
public:
    explicit MpvPlayer(MpvItem *item);
    ~MpvPlayer() override;

    void load(const QString &path);
    void loadNow();
    void setPaused(bool p);
    void seek(double seconds);
    void command(const char *name);
    void setAbLoop(double a, double b);
    void setVolume(double v);
    void setMuted(bool m);
    void setLoopMode(int mode);   // 0=off 1=file 2=playlist
    void setShaderProfile(const QString &name);
    void setQualityTier(int tier);

    // 渲染（由 Renderer 调用）
    // prepareRender(): mpv 这一帧有没有新东西要画。没有就别画 ——
    // 无条件重画会把「帧率」变成「窗口重绘频率」，拖窗口时 GPU 成本直接翻倍。
    bool prepareRender();
    bool renderFrame(QOpenGLFramebufferObject *fbo);

    double position() const { return m_position; }
    double duration() const { return m_duration; }
    QString videoSize() const { return m_videoSize; }

private slots:
    // mpv 唤醒回调从 mpv 线程切回 Qt 线程
    void onEvent();

signals:
    void positionChanged(double);
    void durationChanged(double);
    void pausedChanged(bool);
    void ended();
    void volumeChanged(double);
    void mutedChanged(bool);
    void loadedChanged(bool);
    void errorOccurred(QString);
    void videoSizeChanged(QString);
    void videoWidthChanged(int);
    void videoHeightChanged(int);
    void needsRender();

private:
    void ensureRenderContext();
    void readProperties();

    mpv_handle *m_mpv = nullptr;
    mpv_render_context *m_render = nullptr;
    MpvItem *m_item = nullptr;

    double m_position = 0.0;
    double m_duration = 0.0;
    bool m_paused = false;
    double m_volume = 100.0;
    bool m_muted = false;
    bool m_eofReached = false;
    bool m_userPaused = false;   // 用户按下暂停的意图（区别于 EOF 自动暂停）
    int m_loopMode = 0;          // 0=关 1=单集循环 2=整列
    double m_abA = -1.0, m_abB = -1.0;
    QString m_videoSize;
    int m_videoWidth = 0;
    int m_videoHeight = 0;
    bool m_renderPending = false;
    bool m_initFailed = false;
    bool m_hookedBeforeRendering = false;
    QOpenGLContext *m_glContextForRender = nullptr;  // render context 绑定的是哪个 GL context
    int m_qualityTier = 1;
    QString m_pendingSource;   // 渲染上下文就绪前排队的源
};

// QQuickFramebufferObject 的渲染器：在场景图线程里把 mpv 帧画进 FBO
class MpvRenderer : public QQuickFramebufferObject::Renderer {
public:
    MpvRenderer(MpvItem *item) : m_item(item) {}

    QOpenGLFramebufferObject *createFramebufferObject(const QSize &size) override;
    void render() override;
    void synchronize(QQuickFramebufferObject *item) override;

private:
    MpvItem *m_item = nullptr;
    QSize m_fboSize;        // 当前 FBO 尺寸（createFramebufferObject 里落定）
    QSize m_wantSize;       // 上一帧算出来的目标尺寸
    QSize m_targetSize;     // 下一次 createFramebufferObject 要用的尺寸
    QElapsedTimer m_wantTimer;  // 目标尺寸的稳定计时（拖动期间不重建 FBO）
    bool m_forceRender = true;  // 新建的 FBO 是空的，必须先画一帧
};

} // namespace volta
