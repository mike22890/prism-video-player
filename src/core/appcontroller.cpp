#include "core/appcontroller.h"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QCollator>
#include <QDir>
#include <QFileInfo>
#include <QLocale>
#include <QProcess>
#include <QSettings>
#include <QStandardPaths>

#include <algorithm>

namespace volta {

QString AppController::thumbCacheDir() const
{
    const QString d = QStandardPaths::writableLocation(QStandardPaths::CacheLocation)
                      + QStringLiteral("/thumbs");
    QDir().mkpath(d);
    return d;
}

QString AppController::thumbKey(const QString &path) const
{
    const QFileInfo fi(path);
    const QString raw = fi.absoluteFilePath() + QStringLiteral("|")
                        + QString::number(fi.size()) + QStringLiteral("|")
                        + QString::number(fi.lastModified().toSecsSinceEpoch());
    return QString::fromLatin1(QCryptographicHash::hash(raw.toUtf8(),
                                                        QCryptographicHash::Md5).toHex());
}

QString AppController::findMpv() const
{
    // mpvbin/mpv.exe：从项目根、build/bin、或 exe 旁边往上找
    const QStringList roots = {
        QDir::current().absoluteFilePath(QStringLiteral("mpvbin/mpv.exe")),
        QDir::current().absoluteFilePath(QStringLiteral("../mpvbin/mpv.exe")),
        QDir::current().absoluteFilePath(QStringLiteral("../../mpvbin/mpv.exe")),
        // 打包目录：mpv.exe 跟 volta.exe 放一起（package.sh 拷进去的）
        QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("mpv.exe")),
        QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("mpvbin/mpv.exe"))
    };
    for (const QString &p : roots) {
        if (QFile::exists(p))
            return p;
    }
    return QString();
}

QString AppController::thumbnailForPath(const QString &path)
{
    qInfo("[VOLTA] thumb ask: %s", qPrintable(QFileInfo(path).fileName()));
    if (path.isEmpty())
        return QString();
    const QString dir = thumbCacheDir();
    const QString key = thumbKey(path);
    const QString jpg = dir + QStringLiteral("/") + key + QStringLiteral(".jpg");
    if (QFile::exists(jpg))
        return QStringLiteral("file:///") + jpg;

    // 失败过就别反复抽（.fail 标记，跟着缓存一起过期）
    if (QFile::exists(dir + QStringLiteral("/") + key + QStringLiteral(".fail")))
        return QString();

    if (!m_thumbQueued.contains(path)) {
        m_thumbQueued.insert(path);
        m_thumbQueue.append(path);
        pumpThumbQueue();
    }
    return QString();
}

void AppController::pumpThumbQueue()
{
    if (m_thumbProc || m_thumbQueue.isEmpty())
        return;

    const QString mpv = findMpv();
    if (mpv.isEmpty()) {
        qWarning("[VOLTA] 缩略图：找不到 mpvbin/mpv.exe，跳过");
        m_thumbQueue.clear();
        return;
    }

    const QString current = m_thumbQueue.takeFirst();
    m_thumbCurrent = current;
    const QString key = thumbKey(current);
    m_thumbKey = key;

    const QString sub = thumbCacheDir() + QStringLiteral("/") + key;
    QDir().mkpath(sub);
    runThumbExtract(current, key, sub, 5.0, true);
}

// 一次抽帧。
//
// 关键：path / key / sub 全部按值捕获。上一版这里读的是成员 m_thumbKey / m_thumbCurrent ——
// errorOccurred 与 finished 两个回调都会把 m_thumbProc 清空并去取下一个任务，
// 于是「上一个的图」被写到「下一个的 key」名下：这就是库里缩略图张冠李戴的根。
void AppController::runThumbExtract(const QString &path, const QString &key,
                                    const QString &sub, double startAt, bool allowRetry)
{
    const QString mpv = findMpv();
    if (mpv.isEmpty())
        return;

    auto *p = new QProcess(this);
    m_thumbProc = p;

    const QStringList args = {
        QStringLiteral("--no-config"), QStringLiteral("--no-audio"),
        QStringLiteral("--really-quiet"), QStringLiteral("--load-scripts=no"),
        QStringLiteral("--start=%1").arg(startAt, 0, 'f', 2),
        QStringLiteral("--frames=1"),
        QStringLiteral("--vo=image"), QStringLiteral("--vo-image-format=jpg"),
        QStringLiteral("--vo-image-outdir=") + QDir::toNativeSeparators(sub),
        QDir::toNativeSeparators(path)
    };

    QObject::connect(p, &QProcess::finished, this,
                     [this, p, path, key, sub, startAt, allowRetry](int code, QProcess::ExitStatus) {
        if (m_thumbProc != p) {          // 已经由 errorOccurred 处理过，别重复收尾
            p->deleteLater();
            return;
        }
        const QString dir = thumbCacheDir();
        const QStringList made = QDir(sub).entryList(QStringList() << QStringLiteral("*.jpg"),
                                                    QDir::Files);
        if (!made.isEmpty()) {
            const QString dst = dir + QStringLiteral("/") + key + QStringLiteral(".jpg");
            QFile::remove(dst);
            QFile::rename(sub + QStringLiteral("/") + made.first(), dst);
            QFile::remove(dir + QStringLiteral("/") + key + QStringLiteral(".fail"));
            qInfo("[VOLTA] thumb ok: %s", qPrintable(QFileInfo(path).fileName()));
            emit thumbnailReady(path);
        } else if (allowRetry && startAt > 0.6) {
            // 片头黑 / 短片不到 5 秒：换个更靠前的时间再试一次
            QDir(sub).removeRecursively();
            QDir().mkpath(sub);
            p->deleteLater();
            m_thumbProc = nullptr;
            runThumbExtract(path, key, sub, 0.5, false);
            return;
        } else {
            qInfo("[VOLTA] thumb fail: %s (rc=%d)",
                  qPrintable(QFileInfo(path).fileName()), code);
            QFile f(dir + QStringLiteral("/") + key + QStringLiteral(".fail"));
            if (f.open(QIODevice::WriteOnly))
                f.write(QByteArray::number(code));
        }
        QDir(sub).removeRecursively();
        p->deleteLater();
        m_thumbProc = nullptr;
        pumpThumbQueue();
    });

    QObject::connect(p, &QProcess::errorOccurred, this, [this, p, path](QProcess::ProcessError) {
        if (m_thumbProc != p)
            return;
        qWarning("[VOLTA] thumb process error: %s", qPrintable(QFileInfo(path).fileName()));
        m_thumbProc = nullptr;
        p->deleteLater();
        pumpThumbQueue();
    });

    p->start(mpv, args);
}

void AppController::openLibraryItem(int index)
{
    if (index < 0 || index >= m_libraryPaths.size())
        return;
    openFiles({ QUrl::fromLocalFile(m_libraryPaths.at(index)) });
}

AppController::AppController(QObject *parent)
    : QObject(parent)
{
    // 音量/静音跨会话记忆 —— 每次打开都把音量拧回去是故意的恶作剧，不是功能
    QSettings s;
    m_volume = qBound(0.0, s.value(QStringLiteral("audio/volume"), 80.0).toDouble(), 130.0);
    m_muted = s.value(QStringLiteral("audio/muted"), false).toBool();
    m_ambientLight = s.value(QStringLiteral("view/ambientLight"), true).toBool();
    m_language = s.value(QStringLiteral("ui/language"), QStringLiteral("zh-CN")).toString();
    if (m_language != QStringLiteral("en")) m_language = QStringLiteral("zh-CN");
    rebuildTr();

    // 清掉上一版留下的 .fail 标记：旧代码有竞态，把好片子也标成失败过，
    // 那些条目会永远显示编号。清一次让它们重新抽。
    QDir td(thumbCacheDir());
    for (const QString &f : td.entryList(QStringList() << QStringLiteral("*.fail"), QDir::Files))
        QFile::remove(td.absoluteFilePath(f));
}

QStringList AppController::availableLanguages() const
{
    return { QStringLiteral("zh-CN"), QStringLiteral("en") };
}

QString AppController::lastDirectory() const
{
    const QString d = QSettings().value(QStringLiteral("last/dir")).toString();
    return QDir::fromNativeSeparators(d);
}

QStringList AppController::availableThemes() const
{
    // 扫描 themes/ 目录下的子目录（每个含 theme.json）
    QStringList out;
    const QStringList roots = {
        QDir::current().absoluteFilePath(QStringLiteral("themes")),
        QDir::current().absoluteFilePath(QStringLiteral("../themes"))
    };
    for (const QString &root : roots) {
        QDir d(root);
        if (!d.exists())
            continue;
        const QStringList subs = d.entryList(QDir::Dirs | QDir::NoDotAndDotDot);
        for (const QString &s : subs) {
            if (QFile::exists(d.absoluteFilePath(s + QStringLiteral("/theme.json"))))
                out.append(s);
        }
        if (!out.isEmpty())
            break;
    }
    return out;
}

QStringList AppController::scanDirectory(const QString &dir)
{
    bool truncated = false;
    return volta::scan::scanDirectory(dir, false, 5000, &truncated);
}

void AppController::openFile(const QUrl &url)
{
    openFiles({ url });
}

void AppController::openFiles(const QList<QUrl> &urls)
{
    if (urls.isEmpty())
        return;

    // 打开文件 → 自动收录同目录（v5.1 设计：打开即有，不用手动添加）
    //
    // 旧版只在「目录变了」的时候重扫，结果：
    //   · 同目录再打开第二集 → 下标没更新，画面还停在第一集
    //   · 打开的文件不在扫描结果里 → indexOf 返回 -1 → 播了列表第一个
    // 现在改成每次都归一化路径、都重设当前项。
    QStringList locals;
    for (const QUrl &u : urls) {
        const QString p = u.toLocalFile();
        if (!p.isEmpty())
            locals.append(p);
    }
    if (locals.isEmpty())
        return;

    const QFileInfo firstInfo(locals.first());
    // 支持「拖一个文件夹进来」
    const QString dir = firstInfo.isDir() ? firstInfo.absoluteFilePath()
                                          : firstInfo.absolutePath();
    const QString openedFile = firstInfo.isDir() ? QString()
                                                 : firstInfo.absoluteFilePath();

    if (dir != m_currentDir) {
        m_currentDir = dir;
        m_playlist = scanDirectory(dir);
    } else if (m_playlist.isEmpty()) {
        m_playlist = scanDirectory(dir);
    }

    // 多选打开时，把目录里没有的（别的目录的、非白名单后缀的）也加进来
    for (int i = 1; i < locals.size(); ++i) {
        const QString p = QFileInfo(locals.at(i)).absoluteFilePath();
        if (!p.isEmpty() && indexOfPath(p) < 0)
            m_playlist.append(p);
    }

    int idx = openedFile.isEmpty() ? 0 : indexOfPath(openedFile);
    if (idx < 0 && !m_playlist.isEmpty())
        idx = 0;
    if (m_playlist.isEmpty())
        idx = -1;
    m_currentIndex = idx;

    QSettings().setValue(QStringLiteral("last/dir"), m_currentDir);

    // 库累积：这次扫到的都记下来（去重），队列仍然只是当前目录
    bool libChanged = false;
    for (const QString &p : m_playlist) {
        if (!m_libraryPaths.contains(p)) {
            m_libraryPaths.append(p);
            libChanged = true;
        }
    }

    rebuildModel();
    assignToSlots();
    emit playlistChanged();
    if (libChanged)
        emit libraryChanged();
    emit currentIndexChanged(m_currentIndex);
    qInfo("[VOLTA] open: dir=%s items=%d cur=%d",
          qPrintable(m_currentDir), m_playlist.size(), m_currentIndex);
}

int AppController::indexOfPath(const QString &path) const
{
    // Windows 大小写不敏感 + 扫描结果与 QFileInfo 的路径分隔符可能不一致
    const QString needle = QDir::cleanPath(path);
    for (int i = 0; i < m_playlist.size(); ++i) {
        if (QDir::cleanPath(m_playlist.at(i)).compare(needle, Qt::CaseInsensitive) == 0)
            return i;
    }
    return -1;
}

int AppController::indexForPath(const QString &path) const
{
    return indexOfPath(path);
}

void AppController::handleExternalFiles(const QStringList &paths)
{
    // 只做路径规整和转发：怎么放格子是 QML 的事（它才知道当前有几格）。
    QStringList norm;
    for (const QString &p : paths) {
        const QString abs = QFileInfo(p).absoluteFilePath();
        if (!abs.isEmpty())
            norm << abs;
    }
    if (norm.isEmpty())
        return;
    qInfo("[VOLTA] external files: %d", int(norm.size()));
    emit externalFilesReceived(norm);
}

QVariantList AppController::librarySorted(int mode) const
{
    QVariantList arr = m_libraryModel;

    if (mode == 0) {
        // 按名称：数值感知比较。没有这个，「clip10」会排在「clip2」前面，
        // 跟资源管理器的顺序对不上（用户 2026-11-18 报的就是这个）。
        QCollator col(QLocale(QLocale::Chinese, QLocale::China));
        col.setNumericMode(true);
        col.setCaseSensitivity(Qt::CaseInsensitive);
        std::sort(arr.begin(), arr.end(), [&col](const QVariant &a, const QVariant &b) {
            return col.compare(a.toMap().value(QStringLiteral("full")).toString(),
                               b.toMap().value(QStringLiteral("full")).toString()) < 0;
        });
    } else {
        // 按修改/创建时间：跟资源管理器一致用升序（先点列头就是老的在上面）
        const QString key = (mode == 1) ? QStringLiteral("mtime") : QStringLiteral("ctime");
        std::sort(arr.begin(), arr.end(), [&key](const QVariant &a, const QVariant &b) {
            return a.toMap().value(key).toDouble() < b.toMap().value(key).toDouble();
        });
    }
    return arr;
}

QString AppController::libraryPathAt(int index) const
{
    if (index < 0 || index >= m_libraryPaths.size())
        return QString();
    return m_libraryPaths.at(index);
}

int AppController::ensureInPlaylist(const QString &path)
{
    const int existing = indexOfPath(path);
    if (existing >= 0)
        return existing;
    const QString abs = QFileInfo(path).absoluteFilePath();
    if (abs.isEmpty() || !QFileInfo::exists(abs))
        return -1;
    m_playlist.append(QDir::cleanPath(abs));
    if (m_currentIndex < 0)
        m_currentIndex = 0;
    rebuildModel();
    emit playlistChanged();
    qInfo("[VOLTA] ensureInPlaylist: +1 -> %d item(s)", int(m_playlist.size()));
    return m_playlist.size() - 1;
}

void AppController::next()
{
    if (m_playlist.isEmpty())
        return;
    playIndex((m_currentIndex + 1 + m_playlist.size()) % m_playlist.size());
}

void AppController::previous()
{
    if (m_playlist.isEmpty())
        return;
    playIndex((m_currentIndex - 1 + m_playlist.size()) % m_playlist.size());
}

void AppController::advance()
{
    // 播完自动下一集：到末尾就停。循环留给用户自己按 LOOP。
    if (m_currentIndex + 1 < m_playlist.size())
        playIndex(m_currentIndex + 1);
    else
        qInfo("[VOLTA] queue finished at index %d", m_currentIndex);
}

void AppController::playIndex(int index)
{
    if (index < 0 || index >= m_playlist.size())
        return;
    m_currentIndex = index;
    rebuildModel();
    qInfo("[VOLTA] playIndex %d -> %s", index, qPrintable(QFileInfo(m_playlist.at(index)).fileName()));
    assignToSlots();
    // 队列项的「当前」标记变了 → 模型变了 → 必须发 playlistChanged
    // （否则 QML 里依赖 App.playlist 的绑定不会重算，槽位拿不到新源）
    emit playlistChanged();
    emit currentIndexChanged(index);
}

void AppController::removeIndex(int index)
{
    if (index < 0 || index >= m_playlist.size())
        return;
    m_playlist.removeAt(index);
    if (m_currentIndex == index)
        m_currentIndex = -1;
    else if (m_currentIndex > index)
        --m_currentIndex;
    rebuildModel();
    assignToSlots();
    emit playlistChanged();
}

void AppController::clearPlaylist()
{
    m_playlist.clear();
    m_currentIndex = -1;
    rebuildModel();
    assignToSlots();
    emit playlistChanged();
}

QString AppController::pathAt(int index) const
{
    if (index < 0 || index >= m_playlist.size())
        return QString();
    return m_playlist.at(index);
}

QString AppController::sourceForSlot(int slotId) const
{
    // 槽位分配：当前项优先给 slot 0，其余槽位放后续项
    // （真正的多路并行播放由 M3 的「每槽位独立队列」细化）
    if (slotId < 0)
        return QString();
    const int idx = m_currentIndex >= 0 ? m_currentIndex : 0;
    const int target = idx + slotId;
    if (target < 0 || target >= m_playlist.size())
        return QString();
    return m_playlist.at(target);
}

void AppController::setLanguage(const QString &lang)
{
    const QString normalized = (lang == QStringLiteral("en"))
                               ? QStringLiteral("en") : QStringLiteral("zh-CN");
    if (m_language == normalized)
        return;
    m_language = normalized;
    QSettings().setValue(QStringLiteral("ui/language"), m_language);
    rebuildTr();
    emit languageChanged();
}

void AppController::rebuildTr()
{
    static const QVariantMap zh = {
        {QStringLiteral("app.title"), QStringLiteral("Prism — 多格视频播放器")},
        {QStringLiteral("tab.queue"), QStringLiteral("队列")},
        {QStringLiteral("tab.library"), QStringLiteral("库")},
        {QStringLiteral("btn.open"), QStringLiteral("打开…")},
        {QStringLiteral("btn.prev"), QStringLiteral("上一集")},
        {QStringLiteral("btn.next"), QStringLiteral("下一集")},
        {QStringLiteral("btn.ab"), QStringLiteral("设B点?")},
        {QStringLiteral("btn.theme"), QStringLiteral("主题:")},
        {QStringLiteral("btn.shader"), QStringLiteral("着色:")},
        {QStringLiteral("btn.grid"), QStringLiteral("格数:")},
        {QStringLiteral("btn.fullscreen"), QStringLiteral("全屏")},
        {QStringLiteral("loop.off"), QStringLiteral("循环：关")},
        {QStringLiteral("loop.file"), QStringLiteral("循环：单集")},
        {QStringLiteral("loop.all"), QStringLiteral("循环：整个队列")},
        {QStringLiteral("hint.playing"), QStringLiteral("播放中")},
        {QStringLiteral("hint.paused"), QStringLiteral("已暂停")},
        {QStringLiteral("hint.click"), QStringLiteral("单击切换 · 双击独占")},
        {QStringLiteral("status.playing"), QStringLiteral("正在播 %1 格")},
        {QStringLiteral("status.all"), QStringLiteral("全部 %1 项")},
        {QStringLiteral("empty.drop"), QStringLiteral("拖入视频 / 拖入文件夹\n或点「打开…」\n双击队列项可以再开一格")},
        {QStringLiteral("shader.off"), QStringLiteral("关")},
        {QStringLiteral("shader.crt"), QStringLiteral("CRT")},
        {QStringLiteral("shader.vhs"), QStringLiteral("VHS")},
        {QStringLiteral("shader.neon"), QStringLiteral("霓虹")},
        {QStringLiteral("shader.lcd"), QStringLiteral("掌机LCD")},
        {QStringLiteral("shader.pixel"), QStringLiteral("像素")},
        {QStringLiteral("ab.cleared"), QStringLiteral("A-B 已清除")},
        {QStringLiteral("ab.needB"), QStringLiteral("A 点：%1 —— 再点一次设 B")},
        {QStringLiteral("ab.range"), QStringLiteral("A-B 循环 %1 → %2")},
        {QStringLiteral("ab.order"), QStringLiteral("B 点要在 A 点之后")},
        {QStringLiteral("toast.solo"), QStringLiteral("独占 SLOT %1 · 其它已暂停")},
        {QStringLiteral("toast.theme"), QStringLiteral("主题：%1")},
        {QStringLiteral("toast.shader"), QStringLiteral("着色器：%1")},
        {QStringLiteral("toast.mute"), QStringLiteral("静音")},
        {QStringLiteral("toast.unmute"), QStringLiteral("取消静音")},
        {QStringLiteral("toast.slotClosed"), QStringLiteral("关掉第 %1 格")},
        {QStringLiteral("toast.backSingle"), QStringLiteral("回到单格")},
        {QStringLiteral("toast.added"), QStringLiteral("已加入：%1 个文件")},
        {QStringLiteral("msg.noMore"), QStringLiteral("队列里没有更多可以放进格子的了")},
        {QStringLiteral("msg.lastSlot"), QStringLiteral("最后一格不能关 —— 先打开别的片子")},
        {QStringLiteral("msg.queued"), QStringLiteral("队列里的都放上来了")},
        {QStringLiteral("sort.name"), QStringLiteral("按名称")},
        {QStringLiteral("sort.mtime"), QStringLiteral("按修改时间")},
        {QStringLiteral("sort.ctime"), QStringLiteral("按创建时间")}
    };
    static const QVariantMap en = {
        {QStringLiteral("app.title"), QStringLiteral("Prism — Multi-View Player")},
        {QStringLiteral("tab.queue"), QStringLiteral("Queue")},
        {QStringLiteral("tab.library"), QStringLiteral("Library")},
        {QStringLiteral("btn.open"), QStringLiteral("Open…")},
        {QStringLiteral("btn.prev"), QStringLiteral("Prev")},
        {QStringLiteral("btn.next"), QStringLiteral("Next")},
        {QStringLiteral("btn.ab"), QStringLiteral("Set B?")},
        {QStringLiteral("btn.theme"), QStringLiteral("Theme:")},
        {QStringLiteral("btn.shader"), QStringLiteral("FX:")},
        {QStringLiteral("btn.grid"), QStringLiteral("GRID:")},
        {QStringLiteral("btn.fullscreen"), QStringLiteral("Full")},
        {QStringLiteral("loop.off"), QStringLiteral("Loop: Off")},
        {QStringLiteral("loop.file"), QStringLiteral("Loop: File")},
        {QStringLiteral("loop.all"), QStringLiteral("Loop: All")},
        {QStringLiteral("hint.playing"), QStringLiteral("Playing")},
        {QStringLiteral("hint.paused"), QStringLiteral("Paused")},
        {QStringLiteral("hint.click"), QStringLiteral("Click: play/pause · DblClick: solo")},
        {QStringLiteral("status.playing"), QStringLiteral("%1 playing")},
        {QStringLiteral("status.all"), QStringLiteral("%1 items")},
        {QStringLiteral("empty.drop"), QStringLiteral("Drop video / folder\nor hit Open…\nDouble-click a queue item to add a slot")},
        {QStringLiteral("shader.off"), QStringLiteral("Off")},
        {QStringLiteral("shader.crt"), QStringLiteral("CRT")},
        {QStringLiteral("shader.vhs"), QStringLiteral("VHS")},
        {QStringLiteral("shader.neon"), QStringLiteral("Neon")},
        {QStringLiteral("shader.lcd"), QStringLiteral("LCD")},
        {QStringLiteral("shader.pixel"), QStringLiteral("Pixel")},
        {QStringLiteral("ab.cleared"), QStringLiteral("A-B cleared")},
        {QStringLiteral("ab.needB"), QStringLiteral("A: %1 — click again to set B")},
        {QStringLiteral("ab.range"), QStringLiteral("A-B loop %1 → %2")},
        {QStringLiteral("ab.order"), QStringLiteral("B must be after A")},
        {QStringLiteral("toast.solo"), QStringLiteral("Solo SLOT %1 · others paused")},
        {QStringLiteral("toast.theme"), QStringLiteral("Theme: %1")},
        {QStringLiteral("toast.shader"), QStringLiteral("Shader: %1")},
        {QStringLiteral("toast.mute"), QStringLiteral("Muted")},
        {QStringLiteral("toast.unmute"), QStringLiteral("Unmuted")},
        {QStringLiteral("toast.slotClosed"), QStringLiteral("Closed slot %1")},
        {QStringLiteral("toast.backSingle"), QStringLiteral("Back to single")},
        {QStringLiteral("toast.added"), QStringLiteral("Added: %1 files")},
        {QStringLiteral("msg.noMore"), QStringLiteral("No more items for slots")},
        {QStringLiteral("msg.lastSlot"), QStringLiteral("Last slot — open another first")},
        {QStringLiteral("msg.queued"), QStringLiteral("All queued items loaded")},
        {QStringLiteral("sort.name"), QStringLiteral("Name")},
        {QStringLiteral("sort.mtime"), QStringLiteral("Modified")},
        {QStringLiteral("sort.ctime"), QStringLiteral("Created")}
    };
    m_tr = (m_language == QStringLiteral("en")) ? en : zh;
    if (QSet<QString>(zh.keyBegin(), zh.keyEnd()) != QSet<QString>(en.keyBegin(), en.keyEnd()))
        qWarning("[VOLTA] i18n key mismatch: zh=%d en=%d", zh.size(), en.size());
}

void AppController::setThemeId(const QString &id)
{
    if (m_themeId == id)
        return;
    m_themeId = id;
    emit themeChanged();
}

void AppController::setVolume(double v)
{
    const double nv = qBound(0.0, v, 130.0);
    if (qFuzzyCompare(m_volume + 1.0, nv + 1.0))
        return;
    m_volume = nv;
    QSettings().setValue(QStringLiteral("audio/volume"), m_volume);
    emit volumeChanged();
}

void AppController::setMuted(bool m)
{
    if (m_muted == m)
        return;
    m_muted = m;
    QSettings().setValue(QStringLiteral("audio/muted"), m_muted);
    emit mutedChanged();
}

void AppController::setAmbientLight(bool on)
{
    if (m_ambientLight == on)
        return;
    m_ambientLight = on;
    QSettings().setValue(QStringLiteral("view/ambientLight"), m_ambientLight);
    emit ambientLightChanged();
}

void AppController::rebuildModel()
{
    m_playlistModel.clear();
    for (int i = 0; i < m_playlist.size(); ++i) {
        const QFileInfo fi(m_playlist.at(i));
        QVariantMap m;
        m[QStringLiteral("n")] = fi.completeBaseName();
        m[QStringLiteral("full")] = fi.fileName();
        m[QStringLiteral("path")] = m_playlist.at(i);
        m[QStringLiteral("cur")] = (i == m_currentIndex);
        m[QStringLiteral("slot")] = QStringLiteral("—");
        m[QStringLiteral("d")] = QString();
        m_playlistModel.append(m);
    }

    // 库：跨目录累积，去重后重新编号（跟队列是两回事 —— 队列只装当前目录）
    m_libraryModel.clear();
    for (int i = 0; i < m_libraryPaths.size(); ++i) {
        const QFileInfo fi(m_libraryPaths.at(i));
        QVariantMap m;
        m[QStringLiteral("n")] = fi.completeBaseName();
        m[QStringLiteral("full")] = fi.fileName();
        m[QStringLiteral("path")] = m_libraryPaths.at(i);
        m[QStringLiteral("dir")] = fi.absolutePath();
        // 给「库」页签的排序用（毫秒时间戳）
        m[QStringLiteral("mtime")] = double(fi.lastModified().toMSecsSinceEpoch());
        m[QStringLiteral("ctime")] = double(fi.birthTime().toMSecsSinceEpoch());
        m[QStringLiteral("cur")] = (indexOfPath(m_libraryPaths.at(i)) == m_currentIndex
                                    && m_currentIndex >= 0);
        m[QStringLiteral("slot")] = QStringLiteral("—");
        m_libraryModel.append(m);
    }
}

void AppController::assignToSlots()
{
    // 槽位 → 列表项的映射写回模型（UI 用 SLOT 徽标显示占用关系）
    for (int slot = 0; slot < m_slotCount; ++slot) {
        const QString src = sourceForSlot(slot);
        if (src.isEmpty())
            continue;
        const int idx = m_playlist.indexOf(src);
        if (idx >= 0 && idx < m_playlistModel.size()) {
            QVariantMap m = m_playlistModel.at(idx).toMap();
            m[QStringLiteral("slot")] = QStringLiteral("SLOT %1").arg(slot + 1);
            m_playlistModel[idx] = m;
        }
    }
}

} // namespace volta
