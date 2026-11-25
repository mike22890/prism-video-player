#pragma once
// 全局音效引擎 —— 任何交互都能喊它发声，音色跟着当前主题走。
// 每个主题目录下有四组 wav：tap / hover / nav / toggle。
// 用 QSoundEffect 轮转槽位，快速连点不会互相打断；hover 类带节流防吵。

#include <QObject>
#include <QUrl>
#include <QHash>
#include <QElapsedTimer>

class QSoundEffect;

namespace volta {

class SoundBank : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString themeId READ themeId WRITE setThemeId NOTIFY themeIdChanged)
    Q_PROPERTY(bool enabled READ enabled WRITE setEnabled NOTIFY enabledChanged)

public:
    explicit SoundBank(QObject *parent = nullptr);
    ~SoundBank() override;

    QString themeId() const { return m_themeId; }
    void setThemeId(const QString &id);

    bool enabled() const { return m_enabled; }
    void setEnabled(bool v) { if (m_enabled != v) { m_enabled = v; emit enabledChanged(); } }

    // kind: tap / hover / nav / toggle（其它值静默忽略）
    Q_INVOKABLE void play(const QString &kind);

signals:
    void themeIdChanged();
    void enabledChanged();

private:
    void rebuildUrls();
    QString findThemesDir() const;

    QString m_themeId = QStringLiteral("terminal");
    bool m_enabled = true;
    QHash<QString, QUrl> m_urls;      // kind -> 当前主题的音效 URL
    QHash<QString, qint64> m_last;    // kind -> 上次播放时刻（ms），节流
    QVector<QSoundEffect *> m_slots;  // 轮转槽位
    int m_rr = 0;
    QElapsedTimer m_clock;
};

} // namespace volta
