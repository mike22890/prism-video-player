// VOLTA 入口。
//
// 架构要点：
//   core/   纯逻辑（主题令牌、播放项、队列、视图栈、目录扫描）—— 不依赖 UI/引擎
//   ui/     QML —— 颜色/字体只能从 Theme 单例取
//   engine/ mpv 进程管理（后续阶段）
//
// 主题用 C++ 注册单例（qmlRegisterSingletonInstance）而不是 qt_add_qml_module：
//   静态 QML 模块的 qmldir 带 linktarget 指向 plugin dll，
//   找不到该 dll 时 Qt 判定模块无效（"No module named VOLTA found"）。
//   组件文件放 qrc，同目录互相引用自动解析。

#include <QGuiApplication>
#include <QIcon>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQuickStyle>
#include <QWindow>
#ifdef Q_OS_WIN
#include <windows.h>
#include <shellapi.h>
#endif
#include <QFontDatabase>
#include <QDir>
#include <QFile>
#include <QLocalServer>
#include <QLocalSocket>
#include <QDebug>

#include "core/model.h"
#include "core/themebridge.h"
#include "core/windowframe.h"
#include "engine/mpvitem.h"
#include "core/appcontroller.h"
#include "core/soundbank.h"
#include "core/appassoc.h"

// 日志路径：优先环境变量 VOLTA_LOG，否则用 exe 同目录
// （不要硬编码绝对路径 —— 项目会搬家）
static QString logPath()
{
    const QByteArray env = qgetenv("VOLTA_LOG");
    if (!env.isEmpty())
        return QString::fromLocal8Bit(env);
    return QCoreApplication::applicationDirPath() + QStringLiteral("/volta_run.log");
}

// 一个常驻句柄，不是每条日志都 open/close。
//
// 2026-11-18 排查「拖窗口卡」时发现：QML 里 onWidthChanged/onHeightChanged 每变一个像素打一条，
// 而 vlog 每次都 open→write→close 一个文件。拖一次边 = 几百次 open/close，
// 那不是在写日志，是在拿磁盘当节拍器。
static void vlog(const QString &msg)
{
    static QFile s_log;
    if (!s_log.isOpen()) {
        s_log.setFileName(logPath());
        if (!s_log.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text))
            return;
    }
    s_log.write(msg.toUtf8());
    s_log.write("\n");
    s_log.flush();
}

int main(int argc, char *argv[])
{
    // 必须在 QGuiApplication 之前：libmpv 渲染 API 只有 OpenGL 后端，
    // 而 Qt6 默认走 D3D11 RHI，两者不能共享 GL 上下文。
    // 以前靠 run.sh 里 export 这个变量 —— 双击 exe 就没人给它设，直接黑屏。
    if (qEnvironmentVariableIsEmpty("QSG_RHI_BACKEND"))
        qputenv("QSG_RHI_BACKEND", "opengl");

    // 拖动卡顿的量化结论（tools/swapprobe.py + qt.scenegraph.time.renderloop）：
    // 每步 render 只 1~2ms，present(SwapBuffers) 阻塞 12~15ms —— 一步的底价就是
    // 一个 vsync；错过 vblank 就翻倍成 25~33ms，这就是「有时顺畅有时卡」。
    // Qt 官方给的对症开关是「别让 present 卡住线程」（文档：Qt Quick Scene Graph
    // 一节的 threaded render loop / vsync 一节 —— swapInterval=0 或 QSG_NO_VSYNC
    // 会让渲染循环改用系统定时器驱动动画）。实测本机：节拍从 66ms 掉到 9ms
    // （不再受 vsync 节流），但出现过一次 2.7s 的 present 尖峰，所以不默认开，
    // 用 VOLTA_NO_VSYNC=1 单独试。
    if (qEnvironmentVariableIsSet("VOLTA_NO_VSYNC"))
        qputenv("QSG_NO_VSYNC", "1");

    QGuiApplication app(argc, argv);
    app.setApplicationName("VOLTA");
    app.setOrganizationName("VOLTA");
    app.setApplicationVersion("0.1.0");
    // 任务栏/Alt-Tab 图标：不设这个，Windows 给无边框 Qt 窗一个默认白板，
    // 即使 exe 资源里嵌了图标也没用（exe 图标只管任务管理器/文件管理器）。
    // （多窗口分组靠 AppUserModelID，MinGW shellapi 声明不全；单窗口产品不需要）
    app.setWindowIcon(QIcon(QStringLiteral(":/app.ico")));

    // 首次运行（或版本变更）注册文件关联到 HKCU —— 让 mp4 显示 Prism 图标，
    // 并在设置→默认应用里能看到。不动 UserChoice（带 Hash，写了被系统重置）。
    volta::AppAssociation::registerIfNeeded();

    vlog(QStringLiteral("=== VOLTA start ==="));

    // ── 单实例：双击第二个视频时，把路径转给已经在跑的那个 ──────────
    // 不这么做的话，系统文件关联每点一次就开一个新播放器 —— 用户要的是
    // 「第二个视频进第 2 格」，不是「桌面上多一个窗口」。
    const QString kInstance = QStringLiteral("volta-single-instance-v1");
    QStringList launchFiles;
    {
        const QStringList a = QCoreApplication::arguments();
        for (int i = 1; i < a.size(); ++i) {
            if (a.at(i).startsWith(QLatin1Char('-')))
                continue;
            launchFiles.append(QDir::toNativeSeparators(a.at(i)));
        }
    }
    {
        QLocalSocket probe;
        probe.connectToServer(kInstance);
        if (probe.waitForConnected(250)) {
            QByteArray payload;
            for (const QString &f : launchFiles)
                payload += f.toUtf8() + '\n';
            probe.write(payload);
            probe.flush();
            probe.waitForBytesWritten(800);
            probe.disconnectFromServer();
            probe.waitForDisconnected(300);
            return 0;          // 交接完就退，第二个进程不留痕
        }
    }

    // 基础字体栈必须含 CJK 回退，否则中文变方块（v2 §1.3）
    bool hasCjk = false;
    for (const QString &f : QFontDatabase::families()) {
        if (f.contains(QStringLiteral("YaHei")) || f.contains(QStringLiteral("SimSun"))
            || f.contains(QStringLiteral("Noto Sans CJK")) || f.contains(QStringLiteral("Source Han"))) {
            hasCjk = true;
            break;
        }
    }
    vlog(QStringLiteral("CJK font available: %1").arg(hasCjk ? "yes" : "NO"));

    QQuickStyle::setStyle("Basic");   // 不依赖系统原生风格，主题完全自控

    // ── 加载主题 ──────────────────────────────────────────────
    volta::ThemeTokens tokens;
    bool themeOk = false;
    {
        const QStringList themeDirs = {
            QDir::current().absoluteFilePath(QStringLiteral("themes")),
            QDir::current().absoluteFilePath(QStringLiteral("../themes")),
            QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("../../themes")),
            // 打包后的目录结构：exe 旁边直接放着 themes/
            QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("themes"))
        };
        for (const QString &d : themeDirs) {
            const QString p = QDir(d).absoluteFilePath(QStringLiteral("terminal/theme.json"));
            if (!QFile::exists(p))
                continue;
            QString err;
            if (volta::theme::loadTokens(p, &tokens, &err)) {
                vlog(QStringLiteral("theme loaded: %1").arg(p));
                themeOk = true;
            } else {
                vlog(QStringLiteral("theme load FAILED: %1 : %2").arg(p, err));
            }
            break;
        }
    }
    if (!themeOk) {
        vlog(QStringLiteral("theme not found -- using built-in fallback tokens"));
        tokens.bg = QStringLiteral("#0a0f0a");
        tokens.surface = tokens.bg;
        tokens.surfaceAlt = QStringLiteral("#04160a");
        tokens.ink = QStringLiteral("#33ff66");
        tokens.inkDim = QStringLiteral("#2bbf5c");
        tokens.accent = tokens.ink;
        tokens.accentDim = QStringLiteral("#0f3a18");
        tokens.border = QStringLiteral("#1e5c33");
        tokens.fontFamily = QStringLiteral("Consolas, 'Microsoft YaHei Mono', monospace");
        tokens.fontMono = tokens.fontFamily;
        tokens.scanlines = true;
        tokens.vignette = true;
        tokens.cursorBlink = true;
    }

    // Theme 单例注册到 VOLTA 模块（不依赖 plugin dll）
    volta::ThemeBridge themeBridge(tokens);
    qmlRegisterSingletonInstance("VOLTA", 1, 0, "Theme", &themeBridge);

    // 自绘窗口框架（去掉 Windows 系统标题栏）
    volta::WindowFrame windowFrame;

    QQmlApplicationEngine engine;

    // QML 错误必须抓出来 —— 否则只有一句 "failed to load"，debug 地狱
    QObject::connect(
        static_cast<QQmlEngine *>(&engine), &QQmlEngine::warnings, &app,
        [](const QList<QQmlError> &warnings) {
            for (const QQmlError &e : warnings)
                vlog(QStringLiteral("[QML WARN] %1").arg(e.toString()));
        });

    // QML console.log/warn 也要落盘 —— 否则量不到尺寸（debug 地狱第二层）
    qInstallMessageHandler([](QtMsgType type, const QMessageLogContext &,
                                        const QString &msg) {
        switch (type) {
        case QtDebugMsg:    vlog(QStringLiteral("[QML LOG] ") + msg); break;
        case QtInfoMsg:     vlog(QStringLiteral("[QML INFO] ") + msg); break;
        case QtWarningMsg:  vlog(QStringLiteral("[QML WARN] ") + msg); break;
        case QtCriticalMsg: vlog(QStringLiteral("[QML CRIT] ") + msg); break;
        default: break;
        }
    });

    // WindowCtl 暴露给 QML（自绘标题栏按钮调用）
    qmlRegisterSingletonInstance("VOLTA", 1, 0, "WindowCtl", &windowFrame);

    // MpvItem = 进程内 libmpv 播放器（QML 侧直接用）
    qmlRegisterType<volta::MpvItem>("VOLTA", 1, 0, "MpvItem");

    // AppController = core 与 QML 之间的桥（打开文件 → 自动收录同目录 → 分配槽位）
    volta::AppController appController;
    qmlRegisterSingletonInstance("VOLTA", 1, 0, "App", &appController);

    // 全局音效引擎：QML 里任何交互调 Sfx.play("tap"/"hover"/"nav"/"toggle")
    volta::SoundBank soundBank;
    qmlRegisterSingletonInstance("VOLTA", 1, 0, "Sfx", &soundBank);

    // 单实例的接收端：上一个进程崩了会留下同名的 server 文件，先清再听
    QLocalServer instanceServer;
    QLocalServer::removeServer(kInstance);
    if (instanceServer.listen(kInstance)) {
        vlog(QStringLiteral("single instance: listening on %1").arg(kInstance));
        QObject::connect(&instanceServer, &QLocalServer::newConnection, &app, [&]() {
            while (QLocalSocket *s = instanceServer.nextPendingConnection()) {
                QObject::connect(s, &QLocalSocket::readyRead, &app, [&appController, s]() {
                    const QByteArray data = s->readAll();
                    QStringList paths;
                    for (const QByteArray &line : data.split('\n')) {
                        const QByteArray t = line.trimmed();
                        if (!t.isEmpty())
                            paths << QString::fromUtf8(t);
                    }
                    if (!paths.isEmpty()) {
                        vlog(QStringLiteral("single instance: got %1 file(s)").arg(paths.size()));
                        appController.handleExternalFiles(paths);
                    }
                    s->disconnectFromServer();
                });
                QObject::connect(s, &QLocalSocket::disconnected, s, &QObject::deleteLater);
            }
        });
    } else {
        vlog(QStringLiteral("single instance: listen FAILED (%1)").arg(instanceServer.errorString()));
    }

    // 命令行传入文件 → 直接打开（并自动收录同目录）
    // 用法：volta.exe <file> [file2 ...]
    QList<QUrl> startupFiles;
    for (const QString &f : launchFiles)
        startupFiles.append(QUrl::fromLocalFile(f));

    vlog(QStringLiteral("loading QML root..."));
    engine.load(QUrl(QStringLiteral("qrc:/qml/Main.qml")));
    if (engine.rootObjects().isEmpty()) {
        vlog(QStringLiteral("FAILED to load QML root"));
        return 1;
    }

    // 把窗口交给 WindowFrame：启用 frameless
    //
    // 关键：不能在 QML 里设 flags —— 那会重建 HWND 并让窗口不可见。
    // 正确顺序：窗口先显示出来 → 再改原生样式 → 系统重算非客户区。
    if (auto *win = qobject_cast<QWindow *>(engine.rootObjects().first())) {
        windowFrame.attach(win);
        vlog(QStringLiteral("window attached, waiting for show"));

#ifdef Q_OS_WIN
        // 诊断：确认窗口样式位真的改了
        HWND hwnd = reinterpret_cast<HWND>(win->winId());
        LONG style = GetWindowLongPtrW(hwnd, GWL_STYLE);
        vlog(QStringLiteral("style after frameless: 0x%1 WS_CAPTION=%2 WS_THICKFRAME=%3")
                 .arg(QString::number(static_cast<quint64>(style), 16))
                 .arg((style & WS_CAPTION) ? 1 : 0)
                 .arg((style & WS_THICKFRAME) ? 1 : 0));
        RECT rc;
        GetWindowRect(hwnd, &rc);
        vlog(QStringLiteral("window rect: %1,%2 %3x%4 client-h=%5")
                 .arg(rc.left).arg(rc.top)
                 .arg(rc.right - rc.left).arg(rc.bottom - rc.top)
                 .arg(win->height()));
#endif
    } else {
        vlog(QStringLiteral("WARNING: root object is not a QWindow"));
    }
    vlog(QStringLiteral("QML root loaded OK"));

    // 打开命令行给的文件
    if (!startupFiles.isEmpty()) {
        vlog(QStringLiteral("opening %1 startup file(s)").arg(startupFiles.size()));
        appController.openFiles(startupFiles);
        vlog(QStringLiteral("playlist now has %1 item(s), dir=%2")
                 .arg(appController.playlistCount())
                 .arg(appController.currentDirectory()));
    }

    return app.exec();
}
