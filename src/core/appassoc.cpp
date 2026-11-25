#include "core/appassoc.h"

#include <QCoreApplication>
#include <QDir>
#include <QSettings>
#include <QFileInfo>
#include <QDebug>
#ifdef Q_OS_WIN
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#endif

namespace volta {

// 视频扩展名清单（SupportedTypes / Capabilities / OpenWithProgids 三处共用）
static const char *kVideoExts[] = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts", ".wmv", ".m4v"
};
static const int kVideoExtCount = int(sizeof(kVideoExts) / sizeof(kVideoExts[0]));

// QSettings 写注册表（NativeFormat 在 Windows 落到 HKEY_CURRENT_USER）
static void setReg(const QString &key, const QString &name, const QString &value)
{
    QSettings s(key, QSettings::NativeFormat);
    s.setValue(name, value);
}

void AppAssociation::registerIfNeeded()
{
    // 幂等：版本一致就跳过，别每次启动重写一栈注册表
    QSettings ver(QStringLiteral("HKEY_CURRENT_USER\\Software\\Prism"), QSettings::NativeFormat);
    if (ver.value(QStringLiteral("assocVersion")).toInt() >= 4)
        return;

    const QString exe = QDir::toNativeSeparators(QCoreApplication::applicationFilePath());
    if (exe.isEmpty() || !QFileInfo::exists(exe)) {
        qWarning("[VOLTA] assoc skip: cannot resolve exe path");
        return;
    }
    const QString dir = QFileInfo(exe).absolutePath();
    const QString exeQ = QStringLiteral("\"%1\"").arg(exe);
    const QString icon = exeQ + QStringLiteral(",0");
    const QString openCmd = exeQ + QStringLiteral(" \"%1\"");

    const QString clsRoot = QStringLiteral("HKEY_CURRENT_USER\\Software\\Classes\\");

    // 自有 ProgID —— 让 mp4 在"打开方式"里显示 Prism 而不是未知程序
    const QString pid = clsRoot + QStringLiteral("Prism.Video");
    setReg(pid, QStringLiteral("."), QStringLiteral("Prism Video"));
    setReg(pid, QStringLiteral("FriendlyTypeName"), QStringLiteral("Prism 视频"));
    setReg(pid + QStringLiteral("\\DefaultIcon"), QStringLiteral("."), icon);
    setReg(pid + QStringLiteral("\\shell"), QStringLiteral("."), QStringLiteral("open"));
    setReg(pid + QStringLiteral("\\shell\\open"), QStringLiteral("."), QStringLiteral("用 Prism 播放"));
    setReg(pid + QStringLiteral("\\shell\\open\\command"), QStringLiteral("."), openCmd);

    // Applications\prism.exe —— 单这一条 DefaultIcon 就修好当前 UserChoice 指向的图标
    const QString app = clsRoot + QStringLiteral("Applications\\prism.exe");
    setReg(app, QStringLiteral("FriendlyAppName"), QStringLiteral("Prism"));
    setReg(app, QStringLiteral("ApplicationName"), QStringLiteral("Prism"));
    setReg(app, QStringLiteral("ApplicationIcon"), icon);
    setReg(app + QStringLiteral("\\DefaultIcon"), QStringLiteral("."), icon);
    setReg(app + QStringLiteral("\\shell\\open\\command"), QStringLiteral("."), openCmd);
    for (int i = 0; i < kVideoExtCount; ++i)
        setReg(app + QStringLiteral("\\SupportedTypes"), QString::fromLatin1(kVideoExts[i]), QString());

    // 每个扩展名的 OpenWithProgids —— "打开方式"列表出现 Prism
    for (int i = 0; i < kVideoExtCount; ++i) {
        const QString extKey = clsRoot + QString::fromLatin1(kVideoExts[i]);
        const QString ow = extKey + QStringLiteral("\\OpenWithProgids");
        setReg(ow, QStringLiteral("Prism.Video"), QString());
        // .mp4 等扩展名的默认 ProgID —— 资源管理器里显示 Prism 图标而不是未知图标。
        // 只写扩展名的"(默认)"，不动 UserChoice（那个有哈希保护，写了反而破坏关联）。
        // 用户已经把 Prism 设为默认时，这里补上 ProgID 就能修好未知图标。
        setReg(extKey, QStringLiteral("."), QStringLiteral("Prism.Video"));
    }

    // 系统"设置 → 默认应用"里能看到 Prism
    const QString cap = QStringLiteral("HKEY_CURRENT_USER\\Software\\Prism\\Capabilities");
    setReg(cap, QStringLiteral("ApplicationName"), QStringLiteral("Prism"));
    setReg(cap, QStringLiteral("ApplicationDescription"), QStringLiteral("多格视频播放器"));
    setReg(cap, QStringLiteral("ApplicationIcon"), icon);
    for (int i = 0; i < kVideoExtCount; ++i)
        setReg(cap + QStringLiteral("\\FileAssociations"), QString::fromLatin1(kVideoExts[i]),
               QStringLiteral("Prism.Video"));
    setReg(QStringLiteral("HKEY_CURRENT_USER\\Software\\RegisteredApplications"),
           QStringLiteral("Prism"), QStringLiteral("Software\\Prism\\Capabilities"));

    // App Paths —— 开始菜单/运行里能按名字找到
    const QString ap = QStringLiteral("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\prism.exe");
    setReg(ap, QStringLiteral("."), exe);
    setReg(ap, QStringLiteral("Path"), dir);

    ver.setValue(QStringLiteral("assocVersion"), 4);
    qInfo("[VOLTA] file association registered (Prism.Video, %d ext)", kVideoExtCount);
    // 通知壳层：图标/关联变了，刷新资源管理器与任务栏的图标缓存
#ifdef Q_OS_WIN
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, nullptr, nullptr);
#endif
}

} // namespace volta
