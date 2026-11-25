#pragma once
// 把 core 的 ThemeTokens 暴露给 QML（作为 VOLTA 模块的 Theme 单例）。
//
// 为什么用 C++ 注册而不是 qt_add_qml_module：
//   静态 QML 模块的 qmldir 会带 linktarget 指向 plugin dll，
//   找不到该 dll 时 Qt 判定模块无效 → "No module named VOLTA found"。
//   C++ 注册的单例走的是另一条路（qmlRegisterSingletonInstance），不依赖 plugin。
//   组件文件本身放 qrc 资源，同目录互相引用自动解析。
//
// 分层注意：core/ 不依赖 Qml 模块 —— 这里的 QObject 只用 QtCore，
// QML 注册在 main.cpp 里做。

#include <QObject>
#include <QColor>
#include "core/model.h"

namespace volta {

class ThemeBridge : public QObject {
    Q_OBJECT

    Q_PROPERTY(QString bg READ bg NOTIFY tokensChanged)
    Q_PROPERTY(QString surface READ surface NOTIFY tokensChanged)
    Q_PROPERTY(QString surfaceAlt READ surfaceAlt NOTIFY tokensChanged)
    Q_PROPERTY(QString ink READ ink NOTIFY tokensChanged)
    Q_PROPERTY(QString inkDim READ inkDim NOTIFY tokensChanged)
    Q_PROPERTY(QString accent READ accent NOTIFY tokensChanged)
    Q_PROPERTY(QString accentDim READ accentDim NOTIFY tokensChanged)
    Q_PROPERTY(QString border READ border NOTIFY tokensChanged)
    Q_PROPERTY(QString danger READ danger NOTIFY tokensChanged)
    Q_PROPERTY(QString warning READ warning NOTIFY tokensChanged)
    Q_PROPERTY(QString success READ success NOTIFY tokensChanged)
    Q_PROPERTY(QString fontFamily READ fontFamily NOTIFY tokensChanged)
    Q_PROPERTY(QString fontMono READ fontMono NOTIFY tokensChanged)
    Q_PROPERTY(int fontSize READ fontSize NOTIFY tokensChanged)
    Q_PROPERTY(int radiusPanel READ radiusPanel NOTIFY tokensChanged)
    Q_PROPERTY(int radiusButton READ radiusButton NOTIFY tokensChanged)
    Q_PROPERTY(int radiusInput READ radiusInput NOTIFY tokensChanged)
    Q_PROPERTY(int motionDuration READ motionDuration NOTIFY tokensChanged)
    Q_PROPERTY(bool reduceMotion READ reduceMotion NOTIFY tokensChanged)
    Q_PROPERTY(bool scanlines READ scanlines NOTIFY tokensChanged)
    Q_PROPERTY(bool vignette READ vignette NOTIFY tokensChanged)
    Q_PROPERTY(bool curvature READ curvature NOTIFY tokensChanged)
    Q_PROPERTY(bool glow READ glow NOTIFY tokensChanged)
    Q_PROPERTY(bool cursorBlink READ cursorBlink NOTIFY tokensChanged)
    Q_PROPERTY(QString themeId READ themeId NOTIFY tokensChanged)
    Q_PROPERTY(QString themeName READ themeName NOTIFY tokensChanged)
    Q_PROPERTY(QString style READ style NOTIFY tokensChanged)
    Q_PROPERTY(QString bgTop READ bgTop NOTIFY tokensChanged)
    Q_PROPERTY(QString bgBottom READ bgBottom NOTIFY tokensChanged)
    Q_PROPERTY(QString deco READ deco NOTIFY tokensChanged)
    Q_PROPERTY(QString soundPath READ soundPath NOTIFY tokensChanged)
    Q_PROPERTY(QString defaultShader READ defaultShader NOTIFY tokensChanged)
    Q_PROPERTY(qreal panelAlpha READ panelAlpha NOTIFY tokensChanged)
    Q_PROPERTY(QString panelColor READ panelColor NOTIFY tokensChanged)
    Q_PROPERTY(QString panelAltColor READ panelAltColor NOTIFY tokensChanged)

public:
    explicit ThemeBridge(const ThemeTokens &t, QObject *parent = nullptr)
        : QObject(parent), m_t(t) {}

    // 运行时换主题：重新读 themes/<id>/theme.json → setTokens → QML 里所有
    // 绑到 Theme.* 的颜色/圆角/字体当场换掉，不用重启。
    Q_INVOKABLE bool loadTheme(const QString &id);
    Q_INVOKABLE QStringList availableThemes() const;
    // 读某个主题的显示名（不切换），给 QML 生成主题标签
    Q_INVOKABLE QString themeNameFor(const QString &id) const;
    QString themeId() const { return m_id; }
    void setThemeId(const QString &id) { m_id = id; }

    QString themeName() const { return m_t.name.isEmpty() ? m_id : m_t.name; }
    QString style() const { return m_t.style; }
    QString bgTop() const { return m_t.bgTop; }
    QString bgBottom() const { return m_t.bgBottom; }
    QString deco() const { return m_t.deco; }
    qreal panelAlpha() const { return m_t.panelAlpha; }
    // 按 panelAlpha 预合成带 alpha 的颜色：#AARRGGBB，QML 直接用，避开 Qt.alpha() 对字符串色无效
    QString panelColor() const {
        QColor c(m_t.surface); c.setAlphaF(m_t.panelAlpha);
        return c.name(QColor::HexArgb);
    }
    QString panelAltColor() const {
        QColor c(m_t.surfaceAlt); c.setAlphaF(m_t.panelAlpha);
        return c.name(QColor::HexArgb);
    }
    // 专属音效的完整本地路径（QML 里 SoundEffect.source 直接用）
    QString soundPath() const { return m_soundPath; }
    void setSoundPath(const QString &p) { m_soundPath = p; }
    QString defaultShader() const { return m_defaultShader; }
    void setDefaultShader(const QString &s) { m_defaultShader = s; }

    QString bg() const { return m_t.bg; }
    QString surface() const { return m_t.surface; }
    QString surfaceAlt() const { return m_t.surfaceAlt; }
    QString ink() const { return m_t.ink; }
    QString inkDim() const { return m_t.inkDim; }
    QString accent() const { return m_t.accent; }
    QString accentDim() const { return m_t.accentDim; }
    QString border() const { return m_t.border; }
    QString danger() const { return m_t.danger; }
    QString warning() const { return m_t.warning; }
    QString success() const { return m_t.success; }
    QString fontFamily() const { return m_t.fontFamily; }
    QString fontMono() const { return m_t.fontMono; }
    int fontSize() const { return m_t.fontSize; }
    int radiusPanel() const { return m_t.radiusPanel; }
    int radiusButton() const { return m_t.radiusButton; }
    int radiusInput() const { return m_t.radiusInput; }
    int motionDuration() const { return m_t.motionDuration; }
    bool reduceMotion() const { return m_t.reduceMotion; }
    bool scanlines() const { return m_t.scanlines; }
    bool vignette() const { return m_t.vignette; }
    bool curvature() const { return m_t.curvature; }
    bool glow() const { return m_t.glow; }
    bool cursorBlink() const { return m_t.cursorBlink; }

    void setTokens(const ThemeTokens &t) { m_t = t; emit tokensChanged(); }

signals:
    void tokensChanged();

private:
    ThemeTokens m_t;
    QString m_id = QStringLiteral("terminal");
    QString m_soundPath;
    QString m_defaultShader;
};

} // namespace volta
