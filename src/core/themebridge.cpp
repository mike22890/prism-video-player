#include "core/themebridge.h"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QUrl>

namespace volta {

// 主题目录搜索顺序和 main.cpp 里一致：
//   当前目录（从项目根跑）/ 上一级（从 build/bin 跑）/ exe 往上两级
static QStringList themeRoots()
{
    QStringList roots;
    roots << QDir::current().absoluteFilePath(QStringLiteral("themes"));
    roots << QDir::current().absoluteFilePath(QStringLiteral("../themes"));
    roots << QDir(QCoreApplication::applicationDirPath())
                 .absoluteFilePath(QStringLiteral("../../themes"));
    // 打包目录：themes 就在 exe 旁边
    roots << QDir(QCoreApplication::applicationDirPath())
                 .absoluteFilePath(QStringLiteral("themes"));
    return roots;
}

QStringList ThemeBridge::availableThemes() const
{
    QStringList out;
    for (const QString &root : themeRoots()) {
        QDir d(root);
        if (!d.exists())
            continue;
        const QStringList subs = d.entryList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
        for (const QString &s : subs) {
            if (QFile::exists(d.absoluteFilePath(s + QStringLiteral("/theme.json")))
                && !out.contains(s))
                out << s;
        }
    }
    return out;
}

QString ThemeBridge::themeNameFor(const QString &id) const
{
    for (const QString &root : themeRoots()) {
        const QString p = QDir(root).absoluteFilePath(id + QStringLiteral("/theme.json"));
        if (!QFile::exists(p))
            continue;
        QFile f(p);
        if (!f.open(QIODevice::ReadOnly))
            continue;
        const QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
        const QString name = doc.object().value(QStringLiteral("name")).toString();
        if (!name.isEmpty())
            return name;
    }
    return QString();
}

bool ThemeBridge::loadTheme(const QString &id)
{
    if (id.isEmpty())
        return false;
    for (const QString &root : themeRoots()) {
        const QString p = QDir(root).absoluteFilePath(id + QStringLiteral("/theme.json"));
        if (!QFile::exists(p))
            continue;
        ThemeTokens t;
        QString err;
        if (!theme::loadTokens(p, &t, &err)) {
            qWarning("[VOLTA] theme '%s' load failed: %s", qPrintable(p), qPrintable(err));
            return false;
        }
        m_t = t;
        m_id = id;
        // 专属音效：themes/<id>/<sound文件>。找不到就留空，QML 侧静默跳过。
        m_soundPath.clear();
        if (!t.sound.isEmpty()) {
            const QString sp = QDir(root).absoluteFilePath(id + QStringLiteral("/") + t.sound);
            if (QFile::exists(sp))
                m_soundPath = QUrl::fromLocalFile(sp).toString();
        }
        // 主题默认着色器（video.defaultShader）。loadTokens 没带这个字段，直接从文件读。
        {
            QFile vf(p);
            if (vf.open(QIODevice::ReadOnly)) {
                const QJsonObject vdoc = QJsonDocument::fromJson(vf.readAll()).object();
                m_defaultShader = vdoc.value(QStringLiteral("video")).toObject()
                                      .value(QStringLiteral("defaultShader")).toString();
            } else {
                m_defaultShader.clear();
            }
        }
        qInfo("[VOLTA] theme switched -> %s (%s) sound=%s",
              qPrintable(id), qPrintable(p), qPrintable(m_soundPath));
        emit tokensChanged();
        return true;
    }
    qWarning("[VOLTA] theme '%s' not found", qPrintable(id));
    return false;
}

} // namespace volta
