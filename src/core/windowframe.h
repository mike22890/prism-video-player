#pragma once
// 自绘窗口框架（frameless window）
//
// 背景：Mike 嫌 Windows 系统标题栏丑，要播放器自己的边框。
// Qt 6 对 frameless + 自绘标题栏支持很差（QTBUG-134283，P1），
// 所以这里不用 Qt::FramelessWindowHint 硬来，而是走 Win32 原生事件：
//
//   WM_NCCALCSIZE  → 把系统标题栏区域让给客户端区（去掉系统边框）
//   WM_NCHITTEST   → 标题栏区域返回 HTCAPTION（系统接管拖动/双击/Aero Snap）
//
// 这样保留：系统阴影、Aero Snap 贴靠、动画、任务栏行为、
//           Windows 11 圆角（DWM 保留 WS_THICKFRAME 时自动生效）
// 而丢掉：系统标题栏的最小化/最大化/关闭按钮 —— 我们自己画。
//
// 跨平台：非 Windows 走 Qt 原生路径（保持系统标题栏，不自绘）。

#include <QObject>
#include <QWindow>
#include <QAbstractNativeEventFilter>

class QWindow;

namespace volta {

class WindowFrame : public QObject, public QAbstractNativeEventFilter {
    Q_OBJECT
    Q_PROPERTY(bool frameless READ frameless WRITE setFrameless NOTIFY framelessChanged)
    Q_PROPERTY(bool fullScreen READ fullScreen NOTIFY fullScreenChanged)
    Q_PROPERTY(bool maximized READ maximized NOTIFY windowStateChanged)
    // 正在被鼠标拖边框（WM_ENTERSIZEMOVE..WM_EXITSIZEMOVE）。QML 拿它暂停动画、
    // 视频槽拿它停掉每帧重绘 —— 拖动期间每帧只该干一件事：跟上鼠标。
    Q_PROPERTY(bool resizing READ resizing NOTIFY resizingChanged)

public:
    explicit WindowFrame(QObject *parent = nullptr);
    ~WindowFrame() override;

    // 绑定到要改造的窗口
    void attach(QWindow *window);

    bool frameless() const { return m_frameless; }
    void setFrameless(bool on);

    // 全局唯一实例：MpvItem 在渲染线程上要问「现在是不是在拖边框」，
    // 不想为此在 QML 里多挂一条连接（QML 那层停不下来渲染线程的重绘）。
    static WindowFrame *instance() { return s_instance; }

    bool resizing() const { return m_resizing; }

    // 真全屏交给 QWindow::showFullScreen，样式由 WindowStateChange 统一处理。
    // 进/出全屏 0.3 秒内有 m_lastToggleMs 守卫：期间不把 WS_THICKFRAME 塞回
    // 半转换的窗口（那会踢掉 GL 交换链 → 黑屏且回不来）。
    bool fullScreen() const { return m_fullScreen; }
    Q_INVOKABLE void setFullScreen(bool on);
    bool maximized() const { return m_window && m_window->visibility() == QWindow::Maximized; }

    // 标题栏高度（物理像素）—— QML 加载后上报，用于 WM_NCHITTEST 判断拖动区
    Q_INVOKABLE void setTitleBarHeight(int px);
    int titleBarHeight() const { return m_titleBarHeight; }

    // 给 QML 用的动作
    Q_INVOKABLE void minimize();
    Q_INVOKABLE void toggleMaximize();
    Q_INVOKABLE void close();
    Q_INVOKABLE void showWindowMenu(const QPoint &globalPos);

signals:
    void framelessChanged();
    void fullScreenChanged();
    void windowStateChanged();
    void resizingChanged();

protected:
    bool eventFilter(QObject *obj, QEvent *event) override;
    // Qt6 里 QWindow::nativeEvent 是 protected 虚函数，不再是信号。
    // 想收 WM_* 消息只能用应用级原生事件过滤器。
    bool nativeEventFilter(const QByteArray &eventType, void *message, qintptr *result) override;

private:
    static WindowFrame *s_instance;
    QWindow *m_window = nullptr;
    bool m_frameless = false;
    int m_titleBarHeight = 0;   // 标题栏高度（像素），用于 WM_NCHITTEST 判断
    bool m_fullScreen = false;
    bool m_resizing = false;
    bool m_refreshQueued = false;   // 合并连续 WindowStateChange → 只刷一次原生样式
    int m_resizeSteps = 0;          // 本轮拖动的 WM_SIZING 次数（日志用，量化「一步多贵」）
    qint64 m_lastResizeMs = 0;
    // DWM 属性缓存：值没变就别再调。DwmExtendFrameIntoClientArea 会重算整个窗口框架，
    // DwmSetWindowAttribute 会重发一次框架变更 —— 每次最大化都白付这两笔。
    unsigned long m_lastCornerPref = 0xffffffffUL;
    int m_lastShadowKind = -1;
    qint64 m_lastToggleMs = 0;   // 上次进出全屏时间戳：转换期不刷原生样式
    // 注意：这里只能写 long，不能写 LONG —— windows.h 不在头文件里，
    // LONG 未定义会直接编译失败（踩过一次）。LLP64 下 long 就是 int32，和 LONG 同宽。
    long m_restoreStyle = 0;
    int m_restoreX = 0, m_restoreY = 0, m_restoreW = 0, m_restoreH = 0;

    // Windows 专用
#ifdef Q_OS_WIN
    void applyNativeFrame();
    bool handleNative(const QByteArray &eventType, void *message, qintptr *result);
    void applyWin11CornerPreference();
    void applyShadow();
#endif
};

} // namespace volta
