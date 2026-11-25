#include "engine/mpvitem.h"

#include <QGuiApplication>
#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QOpenGLContext>
#include <QQuickWindow>
#include <QOpenGLFramebufferObject>
#include <QOpenGLFunctions>
#include <QThread>
#include <QTimer>

#include <mpv/client.h>
#include <mpv/render_gl.h>

namespace volta {

// mpv 的 GL 入口解析回调（C 函数指针，不能用捕获 lambda）
static void *getGlProcAddress(void *ctx, const char *name)
{
    auto *c = static_cast<QOpenGLContext *>(ctx);
    return c ? reinterpret_cast<void *>(c->getProcAddress(name)) : nullptr;
}

// ─────────────────────────────────────────────────────────────
// MpvItem
// ─────────────────────────────────────────────────────────────

MpvItem::MpvItem(QQuickItem *parent)
    : QQuickFramebufferObject(parent)
{
    m_player = new MpvPlayer(this);

    // ── resize 卡死的根治（用户报「动一下窗口卡好几秒」）────────────
    // QQuickFramebufferObject 默认 textureFollowsItemSize=true：item 尺寸每变
    // 一像素，Qt 就销毁旧 FBO、按新尺寸 createFramebufferObject、mpv 重绑渲染
    // 目标。拖一次窗口 = 几十上百次重建，每次都分配 GL 纹理 + 重配管线 → 卡死。
    // 关掉它：FBO 尺寸固定（createFramebufferObject 里按视频宽高比给），
    // item 缩放时 Qt 只做纹理坐标缩放，纯 GPU 采样，几乎免费。
    // 视频源宽高比变了（换片）时，由 synchronize() 主动重建一次。
    setTextureFollowsItemSize(false);

    // 帧就绪信号 → 请求重绘
    // 拖动边框期间不主动请求重绘：尺寸变化本身已经要求整窗重画，视频再叠一次
    // update() 只会让「一次尺寸变化」变成两帧（第二帧还得再等一个 vsync），
    // 这就是那记 2×16.7ms 的来路。画面在拖动期间保持上一帧，松手立刻续上。
    connect(m_player, &MpvPlayer::needsRender, this, [this]() {
        m_updatePending = true;
        if (resizingNow())
            return;         // 渲染循环在拖动时已被尺寸变化驱动，别再插队
        update();
    });
    connect(m_player, &MpvPlayer::positionChanged, this, [this](double p) {
        m_position = p;
        emit positionChanged();
    });
    connect(m_player, &MpvPlayer::durationChanged, this, [this](double d) {
        m_duration = d;
        emit durationChanged();
    });
    connect(m_player, &MpvPlayer::loadedChanged, this, [this](bool v) {
        m_loaded = v;
        emit loadedChanged();
    });
    connect(m_player, &MpvPlayer::errorOccurred, this, [this](const QString &e) {
        m_lastError = e;
        emit lastErrorChanged();
    });
    connect(m_player, &MpvPlayer::videoSizeChanged, this, [this](const QString &s) {
        m_videoSize = s;
        emit videoSizeChanged();
    });
    connect(m_player, &MpvPlayer::videoWidthChanged, this, [this](int w) {
        m_videoWidth = w;
        emit videoWidthChanged();
    });
    connect(m_player, &MpvPlayer::videoHeightChanged, this, [this](int h) {
        m_videoHeight = h;
        emit videoHeightChanged();
    });
    // 引擎 → UI：paused / volume / mute 是 mpv 自己也会改的属性
    // （外部命令、播完 keep-open、播放列表切换），必须同步回来，
    // 否则按钮显示的状态是假的。
    connect(m_player, &MpvPlayer::pausedChanged, this, &MpvItem::setPausedFromEngine);
    connect(m_player, &MpvPlayer::volumeChanged, this, &MpvItem::setVolumeValue);
    connect(m_player, &MpvPlayer::mutedChanged, this, &MpvItem::setMutedValue);
    connect(m_player, &MpvPlayer::ended, this, [this]() {
        qInfo("[VOLTA] slot(%d) playback ended", m_source.isEmpty() ? -1 : 1);
        emit playbackEnded();
    });
}

void MpvItem::setPausedFromEngine(bool p)
{
    if (m_paused == p)
        return;
    m_paused = p;
    qInfo("[VOLTA] paused <- mpv = %d", p ? 1 : 0);
    emit pausedChanged();
}

MpvItem::~MpvItem()
{
    delete m_player;
    m_player = nullptr;
}

void MpvItem::setSource(const QString &s)
{
    if (m_source == s)
        return;
    m_source = s;
    qInfo("[VOLTA] MpvItem::setSource('%s')", qPrintable(s));
    emit sourceChanged();
    if (m_player)
        m_player->load(s);
}

void MpvItem::setPaused(bool p)
{
    qInfo("[VOLTA] MpvItem::setPaused(%d) current=%d", p ? 1 : 0, m_paused ? 1 : 0);
    if (m_paused == p)
        return;
    m_paused = p;
    emit pausedChanged();
    if (m_player)
        m_player->setPaused(p);
}

void MpvItem::setPosition(double p)
{
    m_position = p;
    emit positionChanged();
    if (m_player)
        m_player->seek(p);
}

void MpvItem::setDuration(double d) { m_duration = d; emit durationChanged(); }
void MpvItem::setLoaded(bool v) { m_loaded = v; emit loadedChanged(); }
void MpvItem::setLastError(const QString &e) { m_lastError = e; emit lastErrorChanged(); }
void MpvItem::setVideoSize(const QString &s) { m_videoSize = s; emit videoSizeChanged(); }
void MpvItem::requestRender() { m_updatePending = true; update(); }

// ─────────────────────────────────────────────────────────────
// 播放控制
// ─────────────────────────────────────────────────────────────

void MpvItem::togglePlay()
{
    qInfo("[VOLTA] MpvItem::togglePlay m_paused=%d player=%p",
          m_paused ? 1 : 0, static_cast<void *>(m_player));
    if (m_paused)
        play();
    else
        pause();
}

void MpvItem::play()
{
    setPaused(false);
}

void MpvItem::pause()
{
    setPaused(true);
}

void MpvItem::seekTo(double seconds)
{
    if (!m_player)
        return;
    m_player->seek(seconds);
}

void MpvItem::seekRelative(double deltaSeconds)
{
    seekTo(m_position + deltaSeconds);
}

void MpvItem::setAbLoop(double a, double b)
{
    setAbLoopValues(a, b);
    if (!m_player)
        return;
    m_player->setAbLoop(a, b);
}

void MpvItem::clearAbLoop()
{
    setAbLoopValues(-1.0, -1.0);
    if (m_player)
        m_player->setAbLoop(-1.0, -1.0);
}

void MpvItem::setVolume(double v)
{
    setVolumeValue(v);
    if (m_player)
        m_player->setVolume(v);
}

void MpvItem::setMuted(bool m)
{
    setMutedValue(m);
    if (m_player)
        m_player->setMuted(m);
}

void MpvItem::stepFrame(int delta)
{
    // 帧步进：mpv 用 "frame-step" 命令（配合 pause=yes）
    if (!m_player)
        return;
    m_player->setPaused(true);
    m_player->command(delta > 0 ? "frame-step" : "frame-back-step");
}

void MpvItem::setVolumeValue(double v)
{
    if (qFuzzyCompare(m_volume + 1.0, v + 1.0))
        return;
    m_volume = v;
    emit volumeChanged();
}

void MpvItem::setMutedValue(bool m)
{
    if (m_muted == m)
        return;
    m_muted = m;
    emit mutedChanged();
}

void MpvItem::setAbLoopValues(double a, double b)
{
    if (qFuzzyCompare(m_abA + 1.0, a + 1.0) && qFuzzyCompare(m_abB + 1.0, b + 1.0))
        return;
    m_abA = a;
    m_abB = b;
    emit abLoopChanged();
}

void MpvItem::setLoopMode(int mode)
{
    // QML 的入口。旧版 VideoSlot 直接调 video.setLoopMode() —— 那个函数不存在，
    // 所以 LOOP 从上线起就是死的（日志里只有 TypeError）。现在补上真身。
    setLoopModeValue(mode);
}

void MpvItem::setLoopModeValue(int mode)
{
    if (m_loopMode == mode)
        return;
    m_loopMode = mode;
    emit loopModeChanged();
    if (m_player)
        m_player->setLoopMode(mode);
}

void MpvItem::setQualityTier(int tier)
{
    if (m_qualityTier == tier)
        return;
    m_qualityTier = tier;
    emit qualityTierChanged();
    if (m_player)
        m_player->setQualityTier(tier);
}

void MpvItem::setRenderScale(int px)
{
    if (m_renderScale == px)
        return;
    m_renderScale = px;
    emit renderScaleChanged();
    update();
}

// 窗口/布局每变一次几何就记一笔。渲染线程读这个时间戳判断「现在是不是在
// 拖窗口」，用来跳过 mpv 渲染（见 MpvRenderer::render）。
void MpvItem::geometryChange(const QRectF &newGeometry, const QRectF &oldGeometry)
{
    if (newGeometry.size() != oldGeometry.size())
        m_lastGeomChangeMs.store(QDateTime::currentMSecsSinceEpoch());
    QQuickFramebufferObject::geometryChange(newGeometry, oldGeometry);
}

bool MpvItem::resizingNow() const
{
    const qint64 t = m_lastGeomChangeMs.load(std::memory_order_relaxed);
    if (t == 0)
        return false;
    return QDateTime::currentMSecsSinceEpoch() - t < 250;
}

// 目标 FBO 尺寸 —— createFramebufferObject() 和 synchronize() 的**唯一**算法。
// 以前两处各算一套（一处按 renderScale 不夹源、一处把 wantEdge 夹到源，
// 还拿 width 当长边比），于是「目标尺寸 != 实际尺寸」在源长边 < renderScale
// 时恒成立 → synchronize 每帧 invalidate → 每帧 new 一张 2560x1440 纹理，
// 驱动每帧分配/释放 14MB，表现为拖窗口/最大化时随机卡死，CPU 还不高。
QSize MpvItem::preferredFboSize() const
{
    const qreal dpr = (window() && window()->devicePixelRatio() > 0)
                      ? window()->devicePixelRatio() : 1.0;

    int vw = m_videoWidth;
    int vh = m_videoHeight;
    const bool srcKnown = (vw > 0 && vh > 0);
    if (!srcKnown) { vw = 16; vh = 9; }   // 占位只影响 AR，不再把长边夹成 9

    const int srcLong = qMax(vw, vh);
    int longEdge;
    if (m_renderScale > 0) {
        // 独占最佳档：按 renderScale，但**不超过源分辨率**。
        // 2560 去放大 720p 只是白烧 4 倍像素和 14MB 显存，一个像素都不会变清楚。
        longEdge = srcKnown ? qMin(m_renderScale, srcLong) : m_renderScale;
    } else {
        // 自动档：跟窗口显示像素，上限 2560、下限 320。
        const qreal logical = qMax<qreal>(width()  > 16 ? width()  : 980.0,
                                          height() > 16 ? height() : 560.0);
        longEdge = qBound(320, qRound(logical * dpr), 2560);
        // 只在源尺寸已知时才夹源。源未知时 vw/vh 是 16/9 的占位值，
        // 拿 9 去夹会把 FBO 夹成 64x36 拉满全屏 = 马赛克（这个坑踩过两次）。
        if (srcKnown)
            longEdge = qMin(longEdge, srcLong);
    }
    longEdge = qMax(64, longEdge);   // Qt 文档：小于 64x64 有硬件兼容问题

    const double ar = double(vw) / double(vh);
    if (ar >= 1.0) return QSize(longEdge, qMax(1, qRound(longEdge / ar)));
    return QSize(qMax(1, qRound(longEdge * ar)), longEdge);
}

void MpvItem::setShaderProfile(const QString &name)
{
    qInfo("[VOLTA] setShaderProfile('%s')", qPrintable(name));
    if (m_player)
        m_player->setShaderProfile(name);
}

QQuickFramebufferObject::Renderer *MpvItem::createRenderer() const
{
    return new MpvRenderer(const_cast<MpvItem *>(this));
}

// ─────────────────────────────────────────────────────────────
// MpvPlayer
// ─────────────────────────────────────────────────────────────

MpvPlayer::MpvPlayer(MpvItem *item)
    : QObject(item), m_item(item)
{
    m_mpv = mpv_create();
    if (!m_mpv) {
        m_initFailed = true;
        qWarning("[VOLTA] mpv_create failed");
        emit errorOccurred(QStringLiteral("无法创建 mpv 实例"));
        return;
    }

    mpv_set_option_string(m_mpv, "vo", "libmpv");
    mpv_set_option_string(m_mpv, "hwdec", "auto-safe");
    // mpv 按 FBO 尺寸铺满渲染；FBO 已是视频宽高比（见 createFramebufferObject），
    // 所以画面铺满 FBO 且不变形。QML 侧再把 MpvItem 等比放大 cover 填满格子。
    mpv_set_option_string(m_mpv, "keepaspect", "no");
    mpv_set_option_string(m_mpv, "video-aspect-override", "no");
    mpv_set_option_string(m_mpv, "panscan", "no");
    mpv_set_option_string(m_mpv, "keep-open", "yes");
    mpv_set_option_string(m_mpv, "idle", "yes");
    mpv_set_option_string(m_mpv, "pause", "no");
    mpv_set_option_string(m_mpv, "terminal", "no");
    mpv_set_option_string(m_mpv, "audio-display", "no");
    mpv_set_option_string(m_mpv, "osc", "no");
    mpv_set_option_string(m_mpv, "input-default-bindings", "no");
    mpv_set_option_string(m_mpv, "input-vo-keyboard", "no");

    // ── 轻量画质增强（上网查的社区共识，原生选项、GPU 开销小）────────
    // 缩放：放大用 ewa_lanczos（锐而不糊）、缩小用 mitchell；correct-downscaling
    // 让缩小在正确色彩空间做；sigmoid-upscaling 减少放大振铃。都是原生、无 shader。
    mpv_set_option_string(m_mpv, "scale", "ewa_lanczos");
    mpv_set_option_string(m_mpv, "dscale", "mitchell");
    mpv_set_option_string(m_mpv, "cscale", "ewa_lanczos");
    mpv_set_option_string(m_mpv, "correct-downscaling", "yes");
    mpv_set_option_string(m_mpv, "sigmoid-upscaling", "yes");
    // 去色带（暗场渐变断层），便宜；HDR 峰值检测（有 HDR 源才起作用，否则零开销）
    mpv_set_option_string(m_mpv, "deband", "yes");
    mpv_set_option_string(m_mpv, "hdr-compute-peak", "yes");
    // HDR→SDR tonemap：vo_gpu 下 hable 可用，HDR 源自动生效，SDR 源不动
    mpv_set_option_string(m_mpv, "tone-mapping", "hable");
    // 默认均衡档。真·HDR 直通进程内做不到（要独占全屏+gpu-next，与多路互斥），
    // tone-mapping 只在 HDR 源时把 PQ 压到 SDR 并如实标注，不冒充真 HDR。

    if (mpv_initialize(m_mpv) < 0) {
        m_initFailed = true;
        qWarning("[VOLTA] mpv_initialize failed");
        emit errorOccurred(QStringLiteral("mpv 初始化失败"));
        return;
    }

    // 渲染上下文必须在「有 GL context 的线程」创建 —— 即 Qt 场景图的渲染线程。
    // QQuickWindow::beforeRendering 在渲染线程、且 GL context 已 current 时发出，
    // 是唯一正确的时机（QQuickFramebufferObject 的 renderer() 也在那个线程，
    // 但那时才创建已经太晚）。
    // 连接到窗口的 beforeRendering（渲染线程 + GL context 就绪）
    // 注意：UniqueConnection 不能用在 lambda 上（Qt 不支持）→ 用成员标志防重复
    connect(m_item, &MpvItem::windowChanged, this, [this]() {
        if (m_hookedBeforeRendering)
            return;
        auto *w = m_item->window();
        if (!w)
            return;
        m_hookedBeforeRendering = true;
        connect(w, &QQuickWindow::beforeRendering, this, [this]() {
            // 全屏切换/表面重建会换 GL context。旧 render context 指向死 context →
            // mpv 每帧渲染失败 → 满屏黑、只能重启。检测到 context 变了就重建。
            QOpenGLContext *ctx = QOpenGLContext::currentContext();
            if (m_render && ctx && m_glContextForRender && ctx != m_glContextForRender) {
                qInfo("[VOLTA] GL context changed -> rebuild render context");
                mpv_render_context_free(m_render);
                m_render = nullptr;
            }
            ensureRenderContext();
        }, Qt::DirectConnection);
    });

    mpv_set_wakeup_callback(m_mpv, [](void *ctx) {
        // 回调在 mpv 线程 → 通知 Qt 线程处理事件
        QMetaObject::invokeMethod(static_cast<MpvPlayer *>(ctx), "onEvent",
                                  Qt::QueuedConnection);
    }, this);

    // 属性轮询（位置/时长/尺寸）
    auto *timer = new QTimer(this);
    timer->setInterval(250);
    connect(timer, &QTimer::timeout, this, &MpvPlayer::readProperties);
    timer->start();
}

MpvPlayer::~MpvPlayer()
{
    if (m_render) {
        mpv_render_context_free(m_render);
        m_render = nullptr;
    }
    if (m_mpv) {
        mpv_terminate_destroy(m_mpv);
        m_mpv = nullptr;
    }
}

void MpvPlayer::ensureRenderContext()
{
    if (m_render || !m_mpv || m_initFailed)
        return;
    if (!QOpenGLContext::currentContext())
        return;   // 还没进渲染线程的 GL 上下文

    // get_proc_address 必须提供 —— mpv 通过它拿 GL 入口，自己不链接 GL 库。
    // 用当前线程的 QOpenGLContext 实例解析（Qt6 的 getProcAddress 是成员函数）。
    QOpenGLContext *glCtx = QOpenGLContext::currentContext();
    if (!glCtx) {
        qWarning("[VOLTA] no current GL context for render context creation");
        return;
    }
    m_glContextForRender = glCtx;   // 记录绑定的是哪个 context（换 context 时重建）
    mpv_opengl_init_params glInit{ &getGlProcAddress, glCtx };
    mpv_render_param params[] = {
        { MPV_RENDER_PARAM_API_TYPE, const_cast<char *>(MPV_RENDER_API_TYPE_OPENGL) },
        { MPV_RENDER_PARAM_OPENGL_INIT_PARAMS, &glInit },
        { MPV_RENDER_PARAM_INVALID, nullptr }
    };
    int rc = mpv_render_context_create(&m_render, m_mpv, params);
    if (rc < 0) {
        qWarning("[VOLTA] mpv_render_context_create failed: %d", rc);
        emit errorOccurred(QStringLiteral("渲染上下文创建失败"));
        return;
    }
    qInfo("[VOLTA] libmpv render context ready");

    // 渲染上下文就绪 → 现在才能真正加载视频。
    // **不能在这里直接 loadNow()**：当前线程是场景图渲染线程，而
    // mpv_command_string() 是阻塞的 core 调用；渲染线程调非 mpv_render_*
    // 的 API，core 和 VO 会互相等，libmpv 只能用超时兜底（日志里那行
    // "mpv_render_context_render() not being called or stuck" 就是它），
    // 表现出来就是「启动/换集偶尔卡一秒」。派回 GUI 线程执行。
    QMetaObject::invokeMethod(this, [this]() { loadNow(); }, Qt::QueuedConnection);

    mpv_render_context_set_update_callback(m_render, [](void *ctx) {
        auto *p = static_cast<MpvPlayer *>(ctx);
        QMetaObject::invokeMethod(p, [p]() { emit p->needsRender(); },
                                  Qt::QueuedConnection);
    }, this);
}

void MpvPlayer::load(const QString &path)
{
    if (!m_mpv || m_initFailed)
        return;
    if (path.isEmpty()) {
        // 槽位被回收 —— 停掉画面，别留上一部的残帧
        m_pendingSource.clear();
        mpv_command_string(m_mpv, "stop");
        return;
    }
    // 渲染上下文没建好之前不能 loadfile ——
    // mpv 在 render_context 之前产生的帧无处可送，会被丢掉。
    // 所以这里只排队，等 ensureRenderContext() 成功后再真正加载。
    m_pendingSource = path;
    if (m_render)
        loadNow();
}

void MpvPlayer::loadNow()
{
    if (!m_mpv || m_pendingSource.isEmpty())
        return;
    const QUrl url = QUrl::fromLocalFile(m_pendingSource);
    const QString cmd = QStringLiteral("loadfile \"%1\" replace").arg(url.toString());
    qInfo("[VOLTA] loadfile: %s", qPrintable(cmd));
    int rc = mpv_command_string(m_mpv, cmd.toUtf8().constData());
    qInfo("[VOLTA] loadfile rc=%d", rc);
    if (rc == 0) {
        m_pendingSource.clear();
        // keep-open=yes 在片尾会把 pause 打开（留住最后一帧）。这个暂停是
        // 播放器自己干的，不是用户的意思 —— 新文件必须按用户意图重新设定，
        // 否则自动连播到第二集就永远卡在暂停状态（实测：一次 advance 之后再不动）。
        mpv_set_property_string(m_mpv, "pause", m_userPaused ? "yes" : "no");
    }
}

void MpvPlayer::setPaused(bool p)
{
    if (!m_mpv)
        return;
    m_userPaused = p;          // 用户意图：切集后要沿用，但 EOF 的自动暂停不算
    mpv_set_property_string(m_mpv, "pause", p ? "yes" : "no");
}

void MpvPlayer::seek(double seconds)
{
    if (!m_mpv)
        return;
    qInfo("[VOLTA] seek -> %.2fs", seconds);
    mpv_set_property(m_mpv, "time-pos", MPV_FORMAT_DOUBLE, &seconds);
}

void MpvPlayer::command(const char *name)
{
    if (!m_mpv)
        return;
    mpv_command_string(m_mpv, name);
}

void MpvPlayer::setAbLoop(double a, double b)
{
    if (!m_mpv)
        return;
    m_abA = (a >= 0.0 && b > a) ? a : -1.0;
    m_abB = (a >= 0.0 && b > a) ? b : -1.0;
    // 只用我们自己的轮询（见 readProperties），**不**设 mpv 的 ab-loop-a/b：
    //   - keep-open 下 mpv 那套不生效（注释写了半年的坑）
    //   - 就算它生效了，两套一起跳会让「到底谁跳的」无法区分，日志里啥也看不见
    // 单一实现、单一日志，验收才验得动。
    qInfo("[VOLTA] abLoop set a=%.2f b=%.2f", m_abA, m_abB);
}

void MpvPlayer::setVolume(double v)
{
    if (!m_mpv)
        return;
    mpv_set_property(m_mpv, "volume", MPV_FORMAT_DOUBLE, &v);
}

void MpvPlayer::setMuted(bool m)
{
    if (!m_mpv)
        return;
    mpv_set_property_string(m_mpv, "mute", m ? "yes" : "no");
}

void MpvPlayer::setLoopMode(int mode)
{
    if (!m_mpv)
        return;
    m_loopMode = mode;
    qInfo("[VOLTA] loopMode=%d", mode);
    // 这里**不**碰 mpv 的 loop-file / loop-playlist：
    // 只要 mpv 自己会绕，eof-reached 就永远不出现，我们的轮询（和日志）就全成了摆设，
    // 上一版就是「看着能循环、日志里一条证据都没有」。循环只由 readProperties 里的
    // eof-reached 分支 + QML 的队列推进负责，单一实现。
    // 单集 → 自己 seek 回 0；关 → 交给 App.advance()/next()；整列 → QML 绕回第一集。
}

void MpvPlayer::setQualityTier(int tier)
{
    if (!m_mpv)
        return;
    m_qualityTier = qBound(0, tier, 2);
    const char *deband = m_qualityTier >= 1 ? "yes" : "no";
    const char *scale  = m_qualityTier >= 2 ? "ewa_lanczossharp"
                       : (m_qualityTier >= 1 ? "ewa_lanczos" : "bilinear");
    mpv_set_property_string(m_mpv, "deband", deband);
    mpv_set_property_string(m_mpv, "scale", scale);
    mpv_set_property_string(m_mpv, "cscale", scale);
    mpv_set_property_string(m_mpv, "dscale", m_qualityTier >= 1 ? "mitchell" : "bilinear");
    qInfo("[VOLTA] quality tier -> %d (deband=%s scale=%s)", m_qualityTier, deband, scale);
}

void MpvPlayer::setShaderProfile(const QString &name)
{
    if (!m_mpv)
        return;
    if (name.isEmpty()) {
        mpv_set_property_string(m_mpv, "glsl-shaders", "");
        qInfo("[VOLTA] shader off");
        return;
    }
    // 文件在项目 shaders/ 下，按「从项目根跑 / 从 build/bin 跑」两种位置找
    const QString file = name + QStringLiteral(".glsl");
    QStringList roots = {
        QDir::current().absoluteFilePath(QStringLiteral("shaders")),
        QDir::current().absoluteFilePath(QStringLiteral("../shaders")),
        QDir::current().absoluteFilePath(QStringLiteral("../../shaders")),
        QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("../../shaders")),
        // 打包目录：shaders 就在 exe 旁边
        QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("shaders"))
    };
    for (const QString &root : roots) {
        const QString p = QDir(root).absoluteFilePath(file);
        if (!QFile::exists(p))
            continue;
        // glsl-shaders 是多路径字符串，Windows 用 ; 分隔
        const QString native = QDir::toNativeSeparators(p);
        mpv_set_property_string(m_mpv, "glsl-shaders", native.toUtf8().constData());
        qInfo("[VOLTA] shader -> %s", qPrintable(native));
        return;
    }
    qWarning("[VOLTA] shader file not found: %s", qPrintable(file));
}

void MpvPlayer::onEvent()
{
    if (!m_mpv)
        return;
    while (m_mpv) {
        mpv_event *e = mpv_wait_event(m_mpv, 0);
        if (!e || e->event_id == MPV_EVENT_NONE)
            break;
        if (e->event_id == MPV_EVENT_FILE_LOADED) {
            qInfo("[VOLTA] FILE_LOADED");
            emit loadedChanged(true);
        } else if (e->event_id == MPV_EVENT_START_FILE) {
            qInfo("[VOLTA] START_FILE");
        } else if (e->event_id == MPV_EVENT_END_FILE) {
            qInfo("[VOLTA] END_FILE reason=%d",
                  e->data ? static_cast<int>(reinterpret_cast<mpv_event_end_file *>(e->data)->reason) : -99);
            // 出错时给出具体原因；正常播完通知队列推进
            if (e->data) {
                auto *end = reinterpret_cast<mpv_event_end_file *>(e->data);
                if (end->reason == MPV_END_FILE_REASON_ERROR)
                    emit errorOccurred(QStringLiteral("播放失败：文件无法解码"));
            }
        } else if (e->event_id == MPV_EVENT_LOG_MESSAGE) {
            auto *msg = reinterpret_cast<mpv_event_log_message *>(e->data);
            if (msg && msg->log_level <= MPV_LOG_LEVEL_ERROR)
                qWarning("[VOLTA mpv] %s", msg->text);
        }
    }
}

void MpvPlayer::readProperties()
{
    if (!m_mpv)
        return;

    double pos = 0.0;
    if (mpv_get_property(m_mpv, "time-pos", MPV_FORMAT_DOUBLE, &pos) >= 0) {
        if (!qFuzzyCompare(pos + 1.0, m_position + 1.0)) {
            m_position = pos;
            emit positionChanged(pos);
        }
    }

    double dur = 0.0;
    if (mpv_get_property(m_mpv, "duration", MPV_FORMAT_DOUBLE, &dur) >= 0) {
        if (!qFuzzyCompare(dur + 1.0, m_duration + 1.0)) {
            m_duration = dur;
            emit durationChanged(dur);
        }
    }

    // pause/volume/mute 用轮询而不是属性观察：这里有现成的 250ms 心跳，
    // 加监听器要多一套 mpv_observe_property 的生命周期管理，不划算。
    int pauseFlag = 0;
    if (mpv_get_property(m_mpv, "pause", MPV_FORMAT_FLAG, &pauseFlag) >= 0) {
        const bool p = pauseFlag != 0;
        if (p != m_paused) {
            m_paused = p;
            emit pausedChanged(p);
        }
    }

    double vol = 100.0;
    if (mpv_get_property(m_mpv, "volume", MPV_FORMAT_DOUBLE, &vol) >= 0) {
        if (!qFuzzyCompare(vol + 1.0, m_volume + 1.0)) {
            m_volume = vol;
            emit volumeChanged(vol);
        }
    }

    int muteFlag = 0;
    if (mpv_get_property(m_mpv, "mute", MPV_FORMAT_FLAG, &muteFlag) >= 0) {
        const bool muted = muteFlag != 0;
        if (muted != m_muted) {
            m_muted = muted;
            emit mutedChanged(muted);
        }
    }

    // 循环模式 + A-B 都自己判，不依赖 mpv 的 loop-file/ab-loop 属性：
    // 那两个在 keep-open 下会互相打架（实测按了没反应）。
    int eofFlag = 0;
    if (mpv_get_property(m_mpv, "eof-reached", MPV_FORMAT_FLAG, &eofFlag) >= 0) {
        const bool eof = eofFlag != 0;
        if (eof && !m_eofReached) {
            m_eofReached = true;
            if (m_loopMode == 1) {
                // 单集循环：自己倒回去，别惊动队列
                qInfo("[VOLTA] loop-file restart");
                double zero = 0.0;
                mpv_set_property(m_mpv, "time-pos", MPV_FORMAT_DOUBLE, &zero);
                mpv_set_property_string(m_mpv, "pause", "no");
            } else {
                qInfo("[VOLTA] eof-reached");
                emit ended();
            }
        } else if (!eof) {
            m_eofReached = false;
        }
    }

    // A-B：到 B 点自己跳回 A（mpv 的 ab-loop 属性在 keep-open 下不生效）
    if (m_abA >= 0.0 && m_abB > m_abA && m_position > m_abB - 0.06) {
        double a = m_abA;
        mpv_set_property(m_mpv, "time-pos", MPV_FORMAT_DOUBLE, &a);
        // 每绕一圈只打一条，用来证明「真的跳回去了」而不是停在 B 点
        qInfo("[VOLTA] ab loop back to %.2f (was %.2f)", a, m_position);
    }

    // 视频尺寸：用 video-params（源尺寸），不是 out-params（缩放后的）——
    // QML 侧要按源宽高比摆画面
    int64_t w = 0, h = 0;
    if (mpv_get_property(m_mpv, "video-params/w", MPV_FORMAT_INT64, &w) >= 0
        && mpv_get_property(m_mpv, "video-params/h", MPV_FORMAT_INT64, &h) >= 0) {
        if (w != m_videoWidth) {
            m_videoWidth = static_cast<int>(w);
            emit videoWidthChanged(m_videoWidth);
        }
        if (h != m_videoHeight) {
            m_videoHeight = static_cast<int>(h);
            emit videoHeightChanged(m_videoHeight);
        }
        const QString s = QStringLiteral("%1×%2").arg(w).arg(h);
        if (s != m_videoSize) {
            m_videoSize = s;
            emit videoSizeChanged(s);
        }
    }
}

// 这一帧有没有新东西要画。mpv 自己的建议：只有 mpv_render_context_update()
// 带 MPV_RENDER_UPDATE_FRAME 时才需要调 mpv_render_context_render()；没有新帧
// 时再调一次，是把上一帧的整条 GPU 链（scaling + deband + tonemap）白跑一遍。
// 拖窗口/最大化时 QQuickFramebufferObject 每帧都调 render()，没有这个判断，
// 渲染次数就从「视频帧率」变成「窗口重绘频率」——GPU 满载、CPU 不高，正好对上。
bool MpvPlayer::prepareRender()
{
    if (!m_render)
        return false;
    return (mpv_render_context_update(m_render) & MPV_RENDER_UPDATE_FRAME) != 0;
}

bool MpvPlayer::renderFrame(QOpenGLFramebufferObject *fbo)
{
    if (!m_render || !fbo)
        return false;
    if (!QOpenGLContext::currentContext())
        return false;

    mpv_opengl_fbo glFbo{
        static_cast<int>(fbo->handle()),
        static_cast<int>(fbo->width()),
        static_cast<int>(fbo->height()),
        0
    };
    int flip = 0;
    // 不让 mpv 在渲染线程里阻塞等显示时间：那会卡住 Qt 场景图/GUI 同步阶段，
    // 拖窗口每个 WM_SIZE 都排在它后面 → 卡好几秒。时间交给 Qt/vsync。
    int block = 0;
    mpv_render_param params[] = {
        {MPV_RENDER_PARAM_OPENGL_FBO, &glFbo},
        {MPV_RENDER_PARAM_FLIP_Y, &flip},
        {MPV_RENDER_PARAM_BLOCK_FOR_TARGET_TIME, &block},
        {MPV_RENDER_PARAM_INVALID, nullptr}
    };
    mpv_render_context_render(m_render, params);
    return true;
}

// ─────────────────────────────────────────────────────────────
// MpvRenderer
// ─────────────────────────────────────────────────────────────

QOpenGLFramebufferObject *MpvRenderer::createFramebufferObject(const QSize &size)
{
    Q_UNUSED(size);   // 尺寸只由 preferredFboSize() 决定，这里不再重复一套算法
    // 尺寸从 synchronize() 落定的 m_targetSize 拿。绝不在这里读 item 的
    // width/height 现算 —— 那样又会和 synchronize 的判断差出 1px，
    // 差 1px 就是每帧 invalidate，拖窗口必卡。
    m_fboSize = m_targetSize.isValid() ? m_targetSize : QSize(1280, 720);
    m_wantSize = m_fboSize;
    m_wantTimer.restart();
    m_forceRender = true;   // 新 FBO 是空的，必须画一帧
    qInfo("[VOLTA] FBO create %dx%d (renderScale=%d, src %dx%d)",
          m_fboSize.width(), m_fboSize.height(),
          m_item ? m_item->renderScale() : 0,
          m_item ? m_item->videoWidth() : 0,
          m_item ? m_item->videoHeight() : 0);
    // NoAttachment：mpv 只要颜色附件。纹理尺寸固定，item 缩放由 Qt 采样纹理完成。
    return new QOpenGLFramebufferObject(m_fboSize, QOpenGLFramebufferObject::NoAttachment);
}

void MpvRenderer::render()
{
    MpvPlayer *p = m_item ? m_item->player() : nullptr;
    if (!p)
        return;
    // 用 Qt 的访问器拿当前 FBO，不自己存指针：invalidate 时 Qt 会 delete 旧 FBO，
    // 自存的指针在「已删、还没重建」那一帧是野指针。
    QOpenGLFramebufferObject *fbo = framebufferObject();
    if (!fbo)
        return;
    // 没有新帧就什么都不做：FBO 里的上一帧原样保留，Qt 直接采样它。
    // 以前这里无条件调 mpv_render_context_render()，等于按窗口重绘频率
    // 重跑整条 GPU 链（ewa_lanczos + deband + tonemap），拖窗口时成本翻倍。
    if (!m_forceRender && !p->prepareRender())
        return;
    // 正在拖窗口/最大化：先别画。冻结在上一帧，mpv 的 GPU 链一秒都不跑 ——
    // 实测 resize 期间 Qt 的 sync≤13ms、render≤137ms，而 swap（DWM 合成）
    // 会尖到 2 秒；这时候还让 mpv 占 GPU 队列，只会把 swap 拖得更长。
    // 停手 250ms 后自动恢复，mpv 会直接给出最新帧（旧帧在队列里被丢弃）。
    if (!m_forceRender && m_item->resizingNow())
        return;
    m_forceRender = false;
    p->renderFrame(fbo);
}

void MpvRenderer::synchronize(QQuickFramebufferObject *item)
{
    m_item = static_cast<MpvItem *>(item);
    if (!m_item)
        return;

    const QSize want = m_item->preferredFboSize();

    if (!m_fboSize.isValid()) {          // 首帧：还没有 FBO，直接按目标建
        m_targetSize = want;
        return;
    }
    if (want == m_fboSize) {             // 已经一致：清掉待重建状态
        m_wantSize = want;
        m_wantTimer.restart();
        return;
    }
    if (want != m_wantSize) {            // 目标又变了 → 重新计时
        m_wantSize = want;
        m_wantTimer.restart();
        return;
    }
    // 目标连续稳定 250ms 才重建（防抖）。拖窗口/最大化过程中目标尺寸每帧
    // 都在变，一段拖动里一次都不会重建；手松开 250ms 后只重建一次。
    // 原来那套 arChanged/scaleUp/scaleDown 是「立刻重建」+ 判据还夹了源，
    // 源长边 < renderScale 时判据永远成立 → 每帧重建，这才是间歇卡顿的真凶。
    if (m_wantTimer.elapsed() < 250)
        return;
    // 最后一道闸：慢速拖动时每步之间可能 >250ms，上面的防抖计时器会到点，
    // 误以为「尺寸稳定了」而重建。拖动脉冲还在（松手 250ms 内）就一律不重建，
    // 松手后下一帧再建一次。这样无论拖多慢，FBO 都只在松手后重建一次。
    if (m_item->resizingNow())
        return;
    m_targetSize = want;
    m_wantTimer.restart();
    qInfo("[VOLTA] FBO rebuild -> %dx%d (was %dx%d, renderScale=%d)",
          want.width(), want.height(), m_fboSize.width(), m_fboSize.height(),
          m_item->renderScale());
    invalidateFramebufferObject();
}

} // namespace volta
