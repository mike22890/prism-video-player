import QtQuick
import VOLTA

/*
 * 主题背景装饰层 —— 2026-11-26 第五次重写：换维度。
 * 前四轮死在「自己画几何色块」（Canvas → 预烘焙 PNG），同手法换皮，越画越廉价。
 * 这一版用 GLSL 片段着色器（shaders/bg_dynamic.frag → qsb 预编译）做像素级真动态
 * 背景：极光流动 / 红心粒子 / LCD 栅格 / 像素云 / 落日霓虹网格 / 字符雨 / 绿坡。
 * 7 种视觉走同一个 shader 的 uMode 分支，配色由主题 token 传入。
 *
 * 兜底：底层保留纯色 + 预烘焙 PNG。ShaderEffect 若运行时加载失败，只是这层不渲染，
 * 露出下面的 PNG，不会黑屏、不会拖垮整个 QML 根。
 * 拖动窗口边框时 Main.qml 置 paused=true，uTime 动画停 —— present 是拖动时最贵的动作。
 */
Item {
    id: root
    property string deco: Theme.deco || "none"
    property bool reduce: Theme.reduceMotion || false
    property bool paused: false
    readonly property bool animate: !root.paused && !root.reduce
    clip: true

    // deco -> shader mode（7 主题各一种视觉）
    readonly property int mode: {
        if (root.deco === "aurora") return 0     // default 暗夜极光
        if (root.deco === "heart")  return 1     // determination 红心粒子
        if (root.deco === "lcd")    return 2     // gameboy LCD
        if (root.deco === "clouds") return 3     // nes 像素云
        if (root.deco === "grid")   return 4     // synthwave 落日网格
        if (root.deco === "scan")   return 5     // terminal 字符雨
        if (root.deco === "bliss")  return 6     // winxp 绿坡
        return 0
    }

    // 兜底纹理（shader 失败时露出）
    readonly property string texture: {
        if (root.deco === "aurora") return "qrc:/qml/bg_default.png"
        if (root.deco === "heart")   return "qrc:/qml/bg_determination.png"
        if (root.deco === "lcd")     return "qrc:/qml/bg_gameboy.png"
        if (root.deco === "clouds")  return "qrc:/qml/bg_nes.png"
        if (root.deco === "grid")    return "qrc:/qml/bg_synthwave.png"
        if (root.deco === "scan")    return "qrc:/qml/bg_terminal.png"
        if (root.deco === "bliss")   return "qrc:/qml/bg_winxp.png"
        return ""
    }

    // ── 兜底层 ───────────────────────────────────────────────
    Rectangle { anchors.fill: parent; color: Theme.bg }
    Image {
        anchors.fill: parent
        source: root.texture
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: false
        smooth: true
    }

    // ── 动态层：GLSL ─────────────────────────────────────────
    ShaderEffect {
        id: sh
        anchors.fill: parent

        // uniform 名字必须与 frag 里 std140 block 成员一致
        property real uTime: 0
        property int  uMode: root.mode
        property real uPad: 0
        property color uA: Theme.bg
        property color uB: Theme.accent
        property color uAccent: Theme.warning
        property vector2d uRes: Qt.vector2d(root.width, root.height)

        fragmentShader: "qrc:/qml/bg_dynamic.frag.qsb"

        // 时间线性前进，约 1000 秒一轮；拖动/减动效时停
        NumberAnimation on uTime {
            from: 0; to: 1000; duration: 1000000
            loops: Animation.Infinite
            easing.type: Easing.Linear
            running: root.animate
        }
    }
}
