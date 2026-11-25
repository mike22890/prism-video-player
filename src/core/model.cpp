#include "core/model.h"

#include <QDir>
#include <QDirIterator>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QSet>
#include <algorithm>

namespace volta {

// ─────────────────────────────────────────────────────────────
// Library
// ─────────────────────────────────────────────────────────────

void Library::addSource(const ScanSource &src)
{
    if (src.rootPath.isEmpty())
        return;
    for (const auto &s : m_sources) {
        if (s.rootPath == src.rootPath) {
            m_sources.removeAll(s);
            break;
        }
    }
    m_sources.append(src);
}

void Library::removeSource(const QString &rootPath)
{
    for (const auto &s : m_sources) {
        if (s.rootPath == rootPath) {
            m_sources.removeAll(s);
            return;
        }
    }
}

void Library::clear() { m_sources.clear(); }

bool Library::contains(const QString &path) const
{
    for (const auto &s : m_sources) {
        if (s.items.contains(path))
            return true;
    }
    return false;
}

QStringList Library::allItems() const
{
    QSet<QString> seen;
    QStringList out;
    for (const auto &s : m_sources) {
        for (const auto &it : s.items) {
            if (!seen.contains(it)) {
                seen.insert(it);
                out.append(it);
            }
        }
    }
    return out;
}

// ─────────────────────────────────────────────────────────────
// ViewStack
// ─────────────────────────────────────────────────────────────

bool ViewStack::push(const ViewSnapshot &snap)
{
    if (m_stack.size() >= kMaxDepth) {
        // 丢最老的（LRU），不崩
        m_stack.removeFirst();
    }
    m_stack.append(snap);
    return true;
}

bool ViewStack::pop(ViewSnapshot *out)
{
    if (m_stack.isEmpty())
        return false;
    if (out)
        *out = m_stack.takeLast();
    return true;
}

void ViewStack::clear() { m_stack.clear(); }

// ─────────────────────────────────────────────────────────────
// 目录扫描
// ─────────────────────────────────────────────────────────────

namespace scan {

static const QStringList kVideoExt = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".wmv",
    ".flv",  ".mpg", ".mpeg", ".m2ts", ".rmvb", ".3gp", ".vob", ".iso", ".ogv"
};

static const QStringList kPartialExt = {
    ".part", ".tmp", ".!ut", ".download", ".crdownload", ".filepart"
};

bool isVideoExtension(const QString &path)
{
    const QString lower = path.toLower();
    for (const auto &e : kVideoExt) {
        if (lower.endsWith(e))
            return true;
    }
    return false;
}

bool isPartialFile(const QString &path)
{
    const QString lower = path.toLower();
    for (const auto &e : kPartialExt) {
        if (lower.endsWith(e))
            return true;
    }
    return false;
}

// 自然序 key：把连续数字段当整数
static QList<QVariant> naturalKey(const QString &s)
{
    QList<QVariant> key;
    static QRegularExpression re(QStringLiteral("(\\d+)"));
    int pos = 0;
    auto it = re.globalMatch(s);
    while (it.hasNext()) {
        auto m = it.next();
        int start = m.capturedStart();
        if (start > pos) {
            key.append(s.mid(pos, start - pos).toLower());
        }
        key.append(m.captured(1).toLongLong());
        pos = m.capturedEnd();
    }
    if (pos < s.size())
        key.append(s.mid(pos).toLower());
    return key;
}

bool naturalLess(const QString &a, const QString &b)
{
    const auto ka = naturalKey(a);
    const auto kb = naturalKey(b);
    const int n = qMin(ka.size(), kb.size());
    for (int i = 0; i < n; ++i) {
        if (ka[i] == kb[i])
            continue;
        if (ka[i].typeId() == QMetaType::LongLong && kb[i].typeId() == QMetaType::LongLong) {
            return ka[i].toLongLong() < kb[i].toLongLong();
        }
        return ka[i].toString() < kb[i].toString();
    }
    return ka.size() < kb.size();
}

QStringList scanDirectory(const QString &dirPath, bool recursive, int maxItems, bool *truncated)
{
    QStringList out;
    if (truncated)
        *truncated = false;

    QDir dir(dirPath);
    if (!dir.exists())
        return out;

    QFileInfoList entries = dir.entryInfoList(
        QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot | QDir::Readable,
        QDir::NoSort);   // 排序我们自己来

    for (const QFileInfo &fi : entries) {
        if (fi.isDir()) {
            if (recursive) {
                bool subTrunc = false;
                const QStringList sub = scanDirectory(fi.absoluteFilePath(), true, maxItems, &subTrunc);
                out += sub;
                if (subTrunc && truncated)
                    *truncated = true;
            }
            continue;
        }
        if (!fi.isFile())
            continue;
        if (fi.fileName().startsWith(QLatin1Char('.')))
            continue;
        if (isPartialFile(fi.fileName()))
            continue;
        if (!isVideoExtension(fi.fileName()))
            continue;

        out.append(fi.absoluteFilePath());
        if (out.size() >= maxItems) {
            if (truncated)
                *truncated = true;
            break;
        }
    }

    std::sort(out.begin(), out.end(), naturalLess);
    return out;
}

} // namespace scan

// ─────────────────────────────────────────────────────────────
// 主题加载
// ─────────────────────────────────────────────────────────────

namespace theme {

bool loadTokens(const QString &jsonPath, ThemeTokens *out, QString *err)
{
    QFile f(jsonPath);
    if (!f.open(QIODevice::ReadOnly)) {
        if (err)
            *err = QStringLiteral("cannot open %1").arg(jsonPath);
        return false;
    }
    QJsonParseError pe {};
    const QJsonDocument doc = QJsonDocument::fromJson(f.readAll(), &pe);
    if (pe.error != QJsonParseError::NoError) {
        if (err)
            *err = QStringLiteral("json parse error at %1: %2").arg(pe.offset).arg(pe.errorString());
        return false;
    }
    if (!doc.isObject()) {
        if (err)
            *err = QStringLiteral("theme root must be object");
        return false;
    }
    const QJsonObject root = doc.object();
    const QJsonObject tk = root.value(QStringLiteral("tokens")).toObject();
    if (tk.isEmpty()) {
        if (err)
            *err = QStringLiteral("missing 'tokens' object");
        return false;
    }

    ThemeTokens t;
    // 身份字段在 root 层（不在 tokens 里）
    t.id = root.value(QStringLiteral("id")).toString();
    t.name = root.value(QStringLiteral("name")).toString();
    t.sound = root.value(QStringLiteral("sound")).toString();
    t.style = root.value(QStringLiteral("style")).toString();
    const QJsonObject cap = root.value(QStringLiteral("capabilities")).toObject();
    t.deco = cap.value(QStringLiteral("deco")).toString();
    auto str = [&](const char *k, QString &dst) {
        const QJsonValue v = tk.value(QLatin1String(k));
        if (v.isString())
            dst = v.toString();
    };
    auto num = [&](const char *k, int &dst) {
        const QJsonValue v = tk.value(QLatin1String(k));
        if (v.isDouble())
            dst = v.toInt();
    };
    auto boolean = [&](const char *k, bool &dst) {
        const QJsonValue v = tk.value(QLatin1String(k));
        if (v.isBool())
            dst = v.toBool();
    };

    str("color.bg", t.bg);
    str("color.surface", t.surface);
    str("color.surfaceAlt", t.surfaceAlt);
    str("color.bgTop", t.bgTop);
    str("color.bgBottom", t.bgBottom);
    const QJsonValue pa = tk.value(QStringLiteral("panel.alpha"));
    if (pa.isDouble()) t.panelAlpha = pa.toDouble();
    str("color.ink", t.ink);
    str("color.inkDim", t.inkDim);
    str("color.accent", t.accent);
    str("color.accentDim", t.accentDim);
    str("color.border", t.border);
    str("color.danger", t.danger);
    str("color.warning", t.warning);
    str("color.success", t.success);
    str("font.family", t.fontFamily);
    str("font.mono", t.fontMono);
    num("font.size", t.fontSize);
    num("radius.panel", t.radiusPanel);
    num("radius.button", t.radiusButton);
    num("radius.input", t.radiusInput);
    num("motion.duration", t.motionDuration);
    boolean("motion.reduce", t.reduceMotion);
    boolean("cap.scanlines", t.scanlines);
    boolean("cap.vignette", t.vignette);
    boolean("cap.curvature", t.curvature);
    boolean("cap.glow", t.glow);
    boolean("cap.cursorBlink", t.cursorBlink);

    if (!t.isValid()) {
        if (err)
            *err = QStringLiteral("theme missing required tokens (color.bg / color.ink / font.family)");
        return false;
    }

    // 缺省值兜底：缺失的可选令牌不该让主题挂掉
    if (t.surface.isEmpty())  t.surface  = t.bg;
    if (t.inkDim.isEmpty())   t.inkDim   = t.ink;
    if (t.accent.isEmpty())  t.accent  = t.ink;
    if (t.accentDim.isEmpty()) t.accentDim = t.accent;
    if (t.border.isEmpty())  t.border  = t.inkDim;
    if (t.danger.isEmpty())  t.danger  = QStringLiteral("#d97a7a");
    if (t.warning.isEmpty()) t.warning = QStringLiteral("#e0a24a");
    if (t.success.isEmpty()) t.success = QStringLiteral("#7fd1a8");
    if (t.fontMono.isEmpty()) t.fontMono = t.fontFamily;

    if (out)
        *out = t;
    return true;
}

QStringList validateTokenKeys(const QVariantMap &tokens, const QStringList &requiredKeys)
{
    QStringList missing;
    for (const QString &k : requiredKeys) {
        if (!tokens.contains(k))
            missing.append(k);
    }
    return missing;
}

} // namespace theme

} // namespace volta
