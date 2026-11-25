#pragma once
// 应用控制器 —— 把 core（纯逻辑）接到 QML（界面）。
//
// 分层：core 不认识 QML，QML 不认识 mpv，这个类是中间那层。
// 它负责：
//   - 打开文件 → 自动扫描同目录 → 生成队列 → 分配到槽位
//   - 播放列表增删改
//   - 语言切换（i18n）
//   - 主题切换

#include <QObject>
#include <QVariantMap>
#include <QStringList>
#include <QUrl>
#include <QVariantList>
#include <QVariantMap>
#include <QSet>

#include "core/model.h"

class QProcess;

namespace volta {

class AppController : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantList playlist READ playlist NOTIFY playlistChanged)
    Q_PROPERTY(int playlistCount READ playlistCount NOTIFY playlistChanged)
    Q_PROPERTY(int currentIndex READ currentIndex NOTIFY currentIndexChanged)
    Q_PROPERTY(QString currentDirectory READ currentDirectory NOTIFY playlistChanged)
    Q_PROPERTY(QString lastDirectory READ lastDirectory NOTIFY playlistChanged)
    Q_PROPERTY(QString language READ language WRITE setLanguage NOTIFY languageChanged)
    Q_PROPERTY(QVariantMap tr READ tr NOTIFY languageChanged)
    Q_PROPERTY(QString themeId READ themeId WRITE setThemeId NOTIFY themeChanged)
    Q_PROPERTY(QStringList availableLanguages READ availableLanguages CONSTANT)
    Q_PROPERTY(QStringList availableThemes READ availableThemes CONSTANT)
    // 全局音量：四个槽位共用一套值，切焦点不会突然爆音或失声
    Q_PROPERTY(double volume READ volume WRITE setVolume NOTIFY volumeChanged)
    Q_PROPERTY(bool muted READ muted WRITE setMuted NOTIFY mutedChanged)
    Q_PROPERTY(bool ambientLight READ ambientLight WRITE setAmbientLight NOTIFY ambientLightChanged)
    // 库 = 这次运行里打开过的所有目录汇总（队列只是当前目录）
    Q_PROPERTY(QVariantList library READ library NOTIFY libraryChanged)

public:
    explicit AppController(QObject *parent = nullptr);

    QVariantList playlist() const { return m_playlistModel; }
    int playlistCount() const { return m_playlist.count(); }
    int currentIndex() const { return m_currentIndex; }
    QString currentDirectory() const { return m_currentDir; }
    // 上次打开过的目录（文件对话框从这里起步，别每次都从「文档」翻）
    QString lastDirectory() const;
    QString language() const { return m_language; }
    QVariantMap tr() const { return m_tr; }
    QString themeId() const { return m_themeId; }
    QStringList availableLanguages() const;
    QStringList availableThemes() const;
    double volume() const { return m_volume; }
    bool muted() const { return m_muted; }
    bool ambientLight() const { return m_ambientLight; }
    QVariantList library() const { return m_libraryModel; }

    // 缩略图：返回缓存里的 file:// URL；没有就先排队生成，生成完发 thumbnailReady
    Q_INVOKABLE QString thumbnailForPath(const QString &path);
    Q_INVOKABLE void openLibraryItem(int index);

    // 打开一个文件：自动收录同目录视频，并分配到槽位
    Q_INVOKABLE void openFile(const QUrl &url);
    Q_INVOKABLE void openFiles(const QList<QUrl> &urls);
    // 目录扫描（供 UI 调用）
    Q_INVOKABLE QStringList scanDirectory(const QString &dir);
    // 队列操作
    Q_INVOKABLE void playIndex(int index);
    Q_INVOKABLE void removeIndex(int index);
    Q_INVOKABLE void clearPlaylist();
    Q_INVOKABLE QString pathAt(int index) const;
    // 上一项 / 下一项（循环），播完推进（到末尾就停，不循环）
    Q_INVOKABLE void next();
    Q_INVOKABLE void previous();
    Q_INVOKABLE void advance();

    void setLanguage(const QString &lang);
    void setThemeId(const QString &id);
    void setVolume(double v);
    void setMuted(bool m);
    void setAmbientLight(bool on);

    // 槽位 → 播放列表下标的映射（QML 用它给槽位分配 source）
    Q_INVOKABLE QString sourceForSlot(int slotId) const;

    // 单实例：路径转交进来（main.cpp 的 QLocalServer 收，QML 去开格）
    Q_INVOKABLE int indexForPath(const QString &path) const;
    void handleExternalFiles(const QStringList &paths);

    // 库排序交给 C++：QCollator 的 numericMode 才会把 clip2 排在 clip10 前面，
    // 跟资源管理器一致。QML 里 localeCompare 是字典序，clip10 会跑到 clip2 前头。
    Q_INVOKABLE QVariantList librarySorted(int mode) const;
    Q_INVOKABLE QString libraryPathAt(int index) const;
    // 把某个文件塞进播放列表（已在里面就返回下标），给「悬停哪格就开哪格」用
    Q_INVOKABLE int ensureInPlaylist(const QString &path);

signals:
    void playlistChanged();
    void languageChanged();
    void themeChanged();
    void volumeChanged();
    void mutedChanged();
    void ambientLightChanged();
    void libraryChanged();
    // 缩略图做好了（参数是原文件路径）
    void thumbnailReady(const QString &path);
    // 另一个实例转交进来的文件（QML 负责把它们放进新格子）
    void externalFilesReceived(const QStringList &paths);
    // 播放列表推进（当前项变了）
    void currentIndexChanged(int index);

private:
    void rebuildTr();
    void rebuildModel();
    void assignToSlots();
    void runThumbExtract(const QString &path, const QString &key, const QString &sub,
                         double startAt, bool allowRetry);
    int indexOfPath(const QString &path) const;
    void pumpThumbQueue();
    QString thumbCacheDir() const;
    QString thumbKey(const QString &path) const;
    QString findMpv() const;

    QVariantList m_libraryModel;
    QStringList m_libraryPaths;       // 打开过的所有文件（跨目录累积）
    QStringList m_thumbQueue;         // 待抽帧的文件
    QSet<QString> m_thumbQueued;
    QProcess *m_thumbProc = nullptr;
    QString m_thumbCurrent;           // 正在抽的源文件
    QString m_thumbKey;               // 当前缓存 key

    Library m_library;
    QStringList m_playlist;       // 播放队列（= 当前目录的视频）
    QVariantList m_playlistModel; // 给 QML 的展示模型
    QString m_currentDir;
    int m_currentIndex = -1;
    QString m_language = QStringLiteral("zh-CN");
    QVariantMap m_tr;
    QString m_themeId = QStringLiteral("terminal");
    int m_slotCount = 4;
    double m_volume = 80.0;
    bool m_muted = false;
    bool m_ambientLight = true;
};

} // namespace volta
