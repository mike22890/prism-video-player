#include "core/soundbank.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QSoundEffect>
#include <QUrl>

namespace volta {

SoundBank::SoundBank(QObject *parent)
    : QObject(parent)
{
    m_clock.start();
    // 6 个轮转槽：快速连点（列表滚动、连按快捷键）时后一个音不打断前一个。
    for (int i = 0; i < 6; ++i) {
        auto *e = new QSoundEffect(this);
        e->setVolume(0.65);   // 新音源峰值−6dB，0.35 会压到几乎听不见
        m_slots.append(e);
    }
    rebuildUrls();
}

SoundBank::~SoundBank() = default;

QString SoundBank::findThemesDir() const
{
    const QStringList roots = {
        QDir::current().absoluteFilePath(QStringLiteral("themes")),
        QDir::current().absoluteFilePath(QStringLiteral("../themes")),
        QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("themes")),
        QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("../../themes"))
    };
    for (const QString &r : roots)
        if (QDir(r).exists())
            return r;
    return QString();
}

void SoundBank::rebuildUrls()
{
    m_urls.clear();
    const QString dir = findThemesDir();
    if (dir.isEmpty() || m_themeId.isEmpty())
        return;
    static const char *kinds[] = { "tap", "hover", "nav", "toggle" };
    for (const char *k : kinds) {
        const QString p = QDir(dir).absoluteFilePath(m_themeId + QStringLiteral("/") + k + QStringLiteral(".wav"));
        if (QFile::exists(p))
            m_urls.insert(QString::fromLatin1(k), QUrl::fromLocalFile(p));
    }
    qInfo("[VOLTA] Sfx theme=%s kinds=%d", qPrintable(m_themeId), m_urls.size());
}

void SoundBank::setThemeId(const QString &id)
{
    if (m_themeId == id)
        return;
    m_themeId = id;
    rebuildUrls();
    emit themeIdChanged();
}

void SoundBank::play(const QString &kind)
{
    if (!m_enabled || !m_urls.contains(kind))
        return;

    // hover 节流：鼠标划过一排列表项时别像机关枪
    const qint64 now = m_clock.elapsed();
    const qint64 gap = (kind == QStringLiteral("hover")) ? 70 : 0;
    if (now - m_last.value(kind, -9999) < gap)
        return;
    m_last.insert(kind, now);

    QSoundEffect *e = m_slots.at(m_rr % m_slots.size());
    m_rr = (m_rr + 1) % m_slots.size();
    e->setSource(m_urls.value(kind));
    e->play();
}

} // namespace volta
