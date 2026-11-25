#include "core/windowframe.h"

#include <QEvent>
#include <QTimer>
#include <QDateTime>
#include <QGuiApplication>
#include <QCoreApplication>
#include <QWindow>

#ifdef Q_OS_WIN
#include <windows.h>
#include <windowsx.h>
#include <dwmapi.h>
#endif

namespace volta {

WindowFrame *WindowFrame::s_instance = nullptr;

WindowFrame::WindowFrame(QObject *parent)
    : QObject(parent)
{
    s_instance = this;
}

WindowFrame::~WindowFrame() = default;

void WindowFrame::attach(QWindow *window)
{
    if (!window)
        return;
    m_window = window;
    m_window->installEventFilter(this);
    // QML 里设了 Qt.FramelessWindowHint，但 C++ 这边 m_frameless 一直是 false ——
    // handleNative 的第一行 `if (!m_frameless) return false` 把所有消息全挡了。
    // 结果：拉边框、双击最大化、全屏全都不工作，而窗口看着还是无边框（那是 QML 的功）。
    m_frameless = true;
    // Qt6 里原生消息走 QWindow::nativeEvent 信号，不是 eventFilter。
    // 上一版只写了 nativeEvent() 函数却没连信号 —— 于是 WM_NCCALCSIZE /
    // WM_NCHITTEST 一次都没执行：拉不了边、双击标题栏不最大化、全屏发黑，
    // 全是这一个漏接线引起的。
    // 收 WM_* 消息：Qt6 没有 QWindow::nativeEvent 信号，只能挂应用级过滤器
    QCoreApplication::instance()->installNativeEventFilter(this);

    // 等窗口真正显示后再改样式：
    //   - QML 的 ApplicationWindow 会在 show 事件里做自己的初始化
    //   - 太早改样式会被 Qt 重置
    // 用多级延迟确保在 show 之后生效
    QTimer::singleShot(0, this, [this]() {
        QTimer::singleShot(120, this, [this]() {
            if (m_frameless)
                applyNativeFrame();
        });
    });

    if (m_frameless)
        setFrameless(true);
}

void WindowFrame::setFrameless(bool on)
{
    if (m_frameless == on)
        return;
    m_frameless = on;

    if (!m_window) {
        emit framelessChanged();
        return;
    }

    if (on) {
        // 不动 Qt 的 flag（会重建 HWND 并让窗口不可见）。
        // 只改原生样式位 + 让 Qt 知道没有系统装饰：
        //   - WM_NCCALCSIZE 吃掉标题栏区域（nativeEvent 里处理）
        //   - 原生样式位补回 WS_THICKFRAME 等（保住圆角/阴影/Aero Snap）
        QTimer::singleShot(0, this, [this]() {
            QTimer::singleShot(120, this, [this]() { applyNativeFrame(); });
        });
    }

#ifdef Q_OS_WIN
    if (on) {
        applyNativeFrame();
    }
#else
    // 非 Windows：直接用 Qt 的窗口 flag（系统标题栏保留）
    m_window->setFlag(Qt::FramelessWindowHint, on);
#endif

    emit framelessChanged();
}

void WindowFrame::setTitleBarHeight(int px)
{
    if (m_titleBarHeight == px)
        return;
    m_titleBarHeight = px;
    qDebug("[VOLTA] titleBarHeight = %d px", m_titleBarHeight);
}

void WindowFrame::minimize()
{
    if (m_window)
        m_window->setVisibility(QWindow::Minimized);
}

void WindowFrame::toggleMaximize()
{
    if (!m_window)
        return;
    // showMaximized/showNormal 比 setVisibility 干净（后者额外触发一次 flags 重算）。
    // windowStateChanged 由 eventFilter 的 WindowStateChange 发，这里不再手动 emit（原来发两次）。
    if (m_window->visibility() == QWindow::Maximized)
        m_window->showNormal();
    else
        m_window->showMaximized();
}

void WindowFrame::close()
{
    if (m_window)
        m_window->close();
}

void WindowFrame::showWindowMenu(const QPoint &globalPos)
{
    if (!m_window)
        return;
#ifdef Q_OS_WIN
    HWND hwnd = reinterpret_cast<HWND>(m_window->winId());
    if (!hwnd)
        return;
    // 弹出系统窗口菜单（Alt+Space 同款）
    SendMessageW(hwnd, WM_SYSCOMMAND, SC_KEYMENU, MAKELPARAM(globalPos.x(), globalPos.y()));
#else
    m_window->setVisibility(QWindow::Maximized);
#endif
}

bool WindowFrame::eventFilter(QObject *obj, QEvent *event)
{
    if (obj == m_window) {
        if (event->type() == QEvent::WindowStateChange) {
            emit windowStateChanged();
#ifdef Q_OS_WIN
            // 最大化时 Windows 会把系统标题栏塞回来（framelss 窗口的老毛病），
            // 客户区被推下 40px，顶栏上方多一条白带。下一拍重刷原生样式吃掉它。
            // 全屏（m_fullScreen）时不碰 —— 全屏本来就该没有边框。
            // 进出全屏那 0.3 秒别碰样式：那时 m_fullScreen 已被 setFullScreen 改写，
            // 守卫会误通过，对着仍是全屏尺寸的窗口塞回 WS_THICKFRAME → 交换链被踢 → 黑屏。
            //
            // 合并：一次最大化会连着来好几条 WindowStateChange（Qt 自己也会改状态），
            // 以前每条都排一次 applyNativeFrame → 同一帧里反复改样式 + 反复
            // DwmExtendFrameIntoClientArea（它会让 DWM 重算整个窗口框架）。
            const bool transitioning =
                (QDateTime::currentMSecsSinceEpoch() - m_lastToggleMs) < 300;
            if (m_frameless && !m_fullScreen && !transitioning && !m_refreshQueued) {
                m_refreshQueued = true;
                QTimer::singleShot(0, this, [this]() {
                    m_refreshQueued = false;
                    applyNativeFrame();   // 内部只在样式/DWM 属性真变时才发调用
                });
            }
#endif
        }
        if (event->type() == QEvent::Show && m_frameless) {
#ifdef Q_OS_WIN
            applyWin11CornerPreference();
            applyShadow();
#endif
        }
    }
    return QObject::eventFilter(obj, event);
}

#ifdef Q_OS_WIN

void WindowFrame::applyNativeFrame()
{
    if (!m_window)
        return;
    HWND hwnd = reinterpret_cast<HWND>(m_window->winId());
    if (!hwnd)
        return;

    // 补回原生窗口能力：
    //   WS_POPUP      无系统边框
    //   WS_CAPTION    保留标题栏语义（双击最大化/任务栏悬停预览/Aero Snap）
    //   WS_THICKFRAME 可调整大小 + Windows 11 圆角 + 阴影
    //   WS_MAXIMIZEBOX / WS_MINIMIZEBOX / WS_SYSMENU  按钮行为 + Alt+Tab
    //
    // ⚠️ 这里**必须**保留 WS_VISIBLE 之类的位。上一版直接 `SetWindowLongPtr(GWL_STYLE, want)`，
    // want 里没有 WS_VISIBLE —— 于是窗口被自己的代码改成「隐藏」：
    //   · 任务栏上没有图标
    //   · 点击穿透，鼠标落到下面的文件管理器
    //   · 屏幕上还能看到画面（那是 DWM 留下的旧 surface），所以看着像「鬼魂」
    // 症状看着像三件事，其实是一个位。
    LONG style = WS_POPUP | WS_CAPTION | WS_THICKFRAME
                | WS_MAXIMIZEBOX | WS_MINIMIZEBOX | WS_SYSMENU;
    const LONG cur = GetWindowLongPtrW(hwnd, GWL_STYLE);
    // 绝不保留 WS_DISABLED：一旦带进来窗口收不到任何输入（点/键全废，只能杀进程）。
    const LONG keep = WS_VISIBLE | WS_CLIPSIBLINGS | WS_CLIPCHILDREN;
    const LONG want = (cur & keep) | style;
    bool changed = false;
    if (cur != want) {
        SetWindowLongPtrW(hwnd, GWL_STYLE, want);
        changed = true;
    }

    // 清掉 EXSTYLE 里的 3D 边框，否则窗口四周留一圈系统灰边
    LONG exStyle = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
    LONG exWant = exStyle & ~(WS_EX_DLGMODALFRAME | WS_EX_CLIENTEDGE | WS_EX_STATICEDGE);
    exWant |= WS_EX_APPWINDOW;   // 保留任务栏上的独立窗口身份
    if (exStyle != exWant) {
        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, exWant);
        changed = true;
    }

    // 只在样式真变了时通知系统重算 NC。每次点最大化都发 FRAMECHANGED 会
    // 作废整个客户区重绘缓存，这是「点最大化也卡」的元凶之一。
    if (changed) {
        SetWindowPos(hwnd, nullptr, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED);
    }

    applyWin11CornerPreference();
    applyShadow();
}

void WindowFrame::setFullScreen(bool on)
{
    if (!m_window || m_fullScreen == on)
        return;
    m_fullScreen = on;
    m_lastToggleMs = QDateTime::currentMSecsSinceEpoch();

    // 不要自己 SetWindowPos + 改样式：实测那么干屏幕直接黑（GL 交换链被踢掉）。
    // 全屏交给 Qt，它知道怎么保住 surface；顶栏/侧栏的显隐由 QML 读 fullScreen 决定。
    if (on)
        m_window->showFullScreen();
    else {
        m_window->showNormal();
        // 退出全屏后 Windows 会把系统边框/标题栏塞回来：客户区被推下 40px，
        // 顶栏上方多出一条白带（实测截图里就是这么个鬼样子）。
        // 下一拍把原生样式和 NC 区重新按无边框处理，把那条带子收回去。
        // 退出全屏必须抢回焦点，否则 F11/Esc 全落到别的窗口 —— 用户以为「退不出来」。
        QTimer::singleShot(0, this, [this]() {
            applyNativeFrame();
            if (m_window) {
                HWND h = reinterpret_cast<HWND>(m_window->winId());
                SetForegroundWindow(h);
                SetFocus(h);
            }
        });
    }
    emit fullScreenChanged();
}

bool WindowFrame::nativeEventFilter(const QByteArray &eventType, void *message, qintptr *result)
{
    if (!m_window || !message)
        return false;
    MSG *msg = reinterpret_cast<MSG *>(message);
    if (msg->hwnd != reinterpret_cast<HWND>(m_window->winId()))
        return false;
    return handleNative(eventType, message, result);
}

bool WindowFrame::handleNative(const QByteArray &eventType, void *message, qintptr *result)
{
    Q_UNUSED(eventType);
    if (!m_frameless || !m_window)
        return false;

    MSG *msg = reinterpret_cast<MSG *>(message);
    HWND hwnd = reinterpret_cast<HWND>(m_window->winId());

    switch (msg->message) {
    case WM_NCCALCSIZE: {
        // NC 区任何情况下都必须为空，否则 Windows 会把系统标题栏那条带子塞回来。
        // 关键：wParam==FALSE 是「改样式期间」Windows 发来的重算。旧代码只处理 TRUE，
        // 那条路径落到 DefWindowProc → 客户区被下推一个标题栏高度 → 最大化后顶上漏桌面。
        if (!m_fullScreen) {
            if (msg->wParam == TRUE) {
                auto *p = reinterpret_cast<NCCALCSIZE_PARAMS *>(msg->lParam);
                if (IsZoomed(hwnd)) {
                    // 最大化时 WS_THICKFRAME 会让窗口各边膨胀一帧边框。
                    // 不补偿则客户区比屏幕大一圈（左右出屏、底栏沉进任务栏下）。
                    const UINT dpi = GetDpiForWindow(hwnd);
                    const int fx = GetSystemMetricsForDpi(SM_CXSIZEFRAME, dpi)
                                 + GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi);
                    const int fy = GetSystemMetricsForDpi(SM_CYSIZEFRAME, dpi)
                                 + GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi);
                    p->rgrc[0].left += fx;
                    p->rgrc[0].right -= fx;
                    p->rgrc[0].top += fy;
                    p->rgrc[0].bottom -= fy;
                }
                // 不碰 rgrc[1]：那是变化前的窗口矩形，只用于动画，动了会错位。
            } else {
                RECT wr;
                GetWindowRect(hwnd, &wr);
                auto *rc = reinterpret_cast<RECT *>(msg->lParam);
                rc->left = 0;
                rc->top = 0;
                rc->right = wr.right - wr.left;
                rc->bottom = wr.bottom - wr.top;
            }
        }
        *result = 0;
        return true;   // 无条件吃掉，不再 break 给 DefWindowProc
    }

    case WM_SIZING: {
        // ── 这里曾经按 16 物理像素做网格吸附，2026-11-25 撤掉 ─────────────
        // 当时的推断是对的（每步 = 一次 surface 重配 + 全窗重绘 + present），
        // 但杠杆用错了地方。用 Qt 自己的渲染循环计时（qt.scenegraph.time.renderloop）
        // 量出来的真相是：
        //     render（画）= 1~2ms        ← 场景图很便宜
        //     swap（present）= 12~15ms   ← 几乎全部成本，约等于 1 个 vsync
        // 也就是说「一步」的真实底价是 1 个 vsync，量化把步数除以 16，
        // 换来的是：鼠标在 16px 内移动时窗口一动不动（125Hz 鼠标 ≈ 每档 120ms 静止），
        // 越过边界再跳 16px —— 用户嘴里的「有时候顺畅有时候卡住」就是这么来的。
        // 正确做法是保留连续跟手、把每步的重绘内容砍掉（见 mpvitem.cpp 的
        // 拖动期挂起 + QML 侧暂停装饰动画），而不是把步数变少。
        if (!m_fullScreen) {
            // 只计数，不动几何：最小尺寸由 WM_GETMINMAXINFO 的 ptMinTrackSize 管，
            // 系统在发 WM_SIZING 之前已经夹过了。这里再去夹一次只会和系统打架。
            ++m_resizeSteps;
            m_lastResizeMs = QDateTime::currentMSecsSinceEpoch();
        }
        *result = TRUE;   // WM_SIZING 的返回值语义就是「这个矩形有效」
        return true;
    }

    case WM_ENTERSIZEMOVE: {
        // 拖动/拉伸开始。QML 拿它暂停装饰动画，MpvItem 拿它停掉每帧 mpv 重绘。
        m_resizing = true;
        m_resizeSteps = 0;
        m_lastResizeMs = QDateTime::currentMSecsSinceEpoch();
        qInfo("[VOLTA] resize begin");
        emit resizingChanged();
        break;            // 不吞：系统自己要靠它切进模态尺寸循环
    }

    case WM_EXITSIZEMOVE: {
        m_resizing = false;
        qInfo("[VOLTA] resize end: %d sizing steps", m_resizeSteps);
        emit resizingChanged();
        // 松手后再收一次尾：拖动过程中样式位没动过（我们不动它），
        // 但边角/阴影可能因为进出最大化而失效 → 这里只做「值没变就不调」的刷新。
        applyNativeFrame();
        break;
    }

    case WM_WINDOWPOSCHANGING: {
        // 拖动期间丢掉「把旧客户区内容保存并在尺寸变化后拷回去」的整窗拷贝。
        // Win32 文档（SetWindowPos 备注）：不指定 SWP_NOCOPYBITS 时系统会保留
        // 有效客户区内容并拷回；对一个每帧都由场景图整窗重画的窗口，这份拷贝
        // 纯属浪费，而且它就跑在 gui 线程的尺寸变化路径上（= 直接拖慢跟手）。
        if (m_resizing) {
            auto *wp = reinterpret_cast<WINDOWPOS *>(msg->lParam);
            wp->flags |= SWP_NOCOPYBITS;
        }
        break;            // 不吞：交给 Qt / DefWindowProc 继续
    }

    case WM_NCHITTEST: {
        // 自绘边框的窗口，系统默认不给 resize 边框（WS_POPUP + 吃掉 NC 区之后），
        // 所以八条边自己判：8px 以内返回 HTLEFT/HTTOP/... 系统就会接管拉伸手柄。
        {
            RECT wr;
            GetWindowRect(hwnd, &wr);
            // 写死 8 物理像素在 150%/200% 下只有 5/4 逻辑像素，抓不住 → 反复拖。
            const int border = GetSystemMetrics(SM_CXSIZEFRAME)
                             + GetSystemMetrics(SM_CXPADDEDBORDER) + 3;
            POINT pt = { GET_X_LPARAM(msg->lParam), GET_Y_LPARAM(msg->lParam) };
            const bool left   = pt.x <= wr.left + border;
            const bool right  = pt.x >= wr.right - border;
            const bool top    = pt.y <= wr.top + border;
            const bool bottom = pt.y >= wr.bottom - border;
            if (!m_fullScreen && (left || right || top || bottom)) {
                if (top && left)        { *result = HTTOPLEFT; return true; }
                if (top && right)       { *result = HTTOPRIGHT; return true; }
                if (bottom && left)     { *result = HTBOTTOMLEFT; return true; }
                if (bottom && right)    { *result = HTBOTTOMRIGHT; return true; }
                if (left)               { *result = HTLEFT; return true; }
                if (right)              { *result = HTRIGHT; return true; }
                if (top)                { *result = HTTOP; return true; }
                if (bottom)             { *result = HTBOTTOM; return true; }
            }
        }

        // 标题栏区域交给系统 → 拖动窗口、双击最大化、Aero Snap 全是原生行为
        if (!m_fullScreen && m_titleBarHeight > 0) {
            POINT pt = { GET_X_LPARAM(msg->lParam), GET_Y_LPARAM(msg->lParam) };
            ScreenToClient(hwnd, &pt);

            // 单位别混：local 是物理像素，m_titleBarHeight 也是物理（Shell 里乘过 dpr），
            // 所以窗口宽度和按钮区也得先换成物理。上一版拿物理的 x 去比逻辑的 1280-140，
            // 结果「─ 最小化」按钮的左半个落在可拖动区里 —— 想最小化，窗口跟着鼠标跑。
            const double dpr = m_window->devicePixelRatio() > 0 ? m_window->devicePixelRatio() : 1.0;
            const int wPhysical = qRound(m_window->width() * dpr);
            const int buttonZone = qRound(140 * dpr);   // 三个窗口按钮 3×44 逻辑像素
            if (pt.y >= 0 && pt.y <= m_titleBarHeight && pt.x < wPhysical - buttonZone) {
                *result = HTCAPTION;
                return true;
            }
        }
        break;
    }

    case WM_GETMINMAXINFO: {
        // 最大化时不要盖住任务栏（frameless 窗口常见问题）。
        // 注意：MINMAXINFO 里根本没有 rcWork / rcMonitor 字段 ——
        // 上一版往这两个不存在的字段里写 32 字节，直接踩烂后面的内存，
        // 表现就是「拖边框，窗口跳到 1528x900 这种莫名其妙的大小」。
        // 正确写法是填 ptMaxSize / ptMaxPosition。
        HMONITOR monitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
        MONITORINFO mi = { sizeof(mi) };
        if (GetMonitorInfoW(monitor, &mi)) {
            auto *m = reinterpret_cast<MINMAXINFO *>(msg->lParam);
            m->ptMaxPosition.x = mi.rcWork.left - mi.rcMonitor.left;
            m->ptMaxPosition.y = mi.rcWork.top - mi.rcMonitor.top;
            m->ptMaxSize.x = mi.rcWork.right - mi.rcWork.left;
            m->ptMaxSize.y = mi.rcWork.bottom - mi.rcWork.top;
            // 最大化后没有边框，最小追踪尺寸按 640x400 兜底
            m->ptMinTrackSize.x = 640;
            m->ptMinTrackSize.y = 400;
        }
        break;
    }

    case WM_SETTINGCHANGE: {
        // 显示设置变化（主题/缩放）→ 重刷阴影。缩放变了，DWM 属性得重发。
        m_lastShadowKind = -1;
        m_lastCornerPref = 0xffffffffUL;
        applyShadow();
        break;
    }
    }
    return false;
}

void WindowFrame::applyWin11CornerPreference()
{
    HWND hwnd = m_window ? reinterpret_cast<HWND>(m_window->winId())
                               : reinterpret_cast<HWND>(0);
    if (!hwnd)
        return;
    // DWMWA_WINDOW_CORNER_PREFERENCE = 33
    // DWMWCP_ROUND = 2（系统默认是 DON'TROUND for frameless）
    // 最大化/全屏时 DONOTROUND：圆角 + 铺满屏幕 = 四角各露一块桌面。
    const DWORD pref = (IsZoomed(hwnd) || m_fullScreen) ? 1 /*DONOTROUND*/ : 2 /*ROUND*/;
    // 值没变就别调：DwmSetWindowAttribute(33) 会让 DWM 重发一次框架变更，
    // 而每次 WindowStateChange / WM_SETTINGCHANGE 都会走到这里。
    if (pref == m_lastCornerPref)
        return;
    m_lastCornerPref = pref;
    DwmSetWindowAttribute(hwnd, 33, &pref, sizeof(pref));
}

void WindowFrame::applyShadow()
{
    HWND hwnd = m_window ? reinterpret_cast<HWND>(m_window->winId())
                               : reinterpret_cast<HWND>(0);
    if (!hwnd)
        return;
    // 把 DWM 阴影延伸到客户区外 1px → 有系统阴影
    // 最大化/全屏时 1px 阴影延伸会在底边留一条透明缝。
    // 0 = 无阴影（最大化/全屏），1 = 底边 1px 阴影
    const int kind = (IsZoomed(hwnd) || m_fullScreen) ? 0 : 1;
    // DwmExtendFrameIntoClientArea 是「重算整个窗口框架」级别的调用：
    // 每次最大化都发一遍 = 在 DWM 的最大化动画中间插一次框架重建（肉眼就是一顿）。
    if (kind == m_lastShadowKind)
        return;
    m_lastShadowKind = kind;
    MARGINS margins = (kind == 0) ? MARGINS{ 0, 0, 0, 0 } : MARGINS{ 0, 0, 1, 0 };
    DwmExtendFrameIntoClientArea(hwnd, &margins);
}

#endif // Q_OS_WIN

} // namespace volta
