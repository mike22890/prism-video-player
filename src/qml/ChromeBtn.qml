import QtQuick
import VOLTA

/*
 * ChromeBtn —— 按主题形态画按钮，不是只换颜色。
 * 替掉 TransportBar/PlaylistPanel/Shell/VideoSlot 里 12 处手写 Rectangle 按钮。
 * 形态由 Theme.style 决定：modern/lcd/pixel/neon/terminal/determination/luna。
 * 用 Theme.style（不用 themeId 字符串），控件里不许出现主题名。
 */
Rectangle {
    id: btn
    property string label: ""
    property bool active: false
    property string kind: ""          // 语义：loop/ab/theme/shader/grid/fs/lang/prev/next...
    signal clicked()

    // 形态参数（一次算好，各 shape 分支共用）
    readonly property string sh: Theme.style || "modern"
    readonly property bool isPixel: sh === "pixel" || sh === "lcd"
    readonly property bool isLcd: sh === "lcd"
    readonly property bool isTerminal: sh === "terminal"
    readonly property bool isDet: sh === "determination"
    readonly property bool isLuna: sh === "luna"
    readonly property bool isNeon: sh === "neon"

    implicitWidth: lbl.implicitWidth + (isTerminal ? 4 : (isDet ? 10 : 12))
    implicitHeight: isLuna ? 22 : (isPixel ? 24 : (isNeon ? 26 : 22))

    // 星号连根删掉。决心主题改成干净白框方框：选中红框红字，非选中白框白字。
    border.width: (isPixel || isTerminal) ? 0 : 1
    border.color: isDet
                  ? (active ? "#ff2d2d" : "#f2f2f2")
                  : (active ? Theme.accent : Theme.border)
    radius: isNeon ? 2 : (isLuna ? 3 : (isPixel || isTerminal || isDet ? 0 : Theme.radiusButton))
    gradient: isLuna ? lunaGrad : null

    Gradient { id: lunaGrad
        GradientStop { position: 0.0; color: "#FDFDFD" }
        GradientStop { position: 0.5; color: active ? "#D6E6FA" : "#ECE9D8" }
        GradientStop { position: 1.0; color: "#D2CEC0" }
    }

    // pixel 双层框（外深内亮），lcd 反色，luna 内高光，neon 底渐变，terminal/UT 无框
    Rectangle {
        anchors.fill: parent; anchors.margins: 2
        visible: isPixel
        color: "transparent"; border.color: active ? "#9BBC0F" : "#306230"; border.width: 1
        radius: 0
    }
    Rectangle {
        anchors.fill: parent
        visible: isLuna
        color: "transparent"; radius: 3
        border.color: "#003C74"; border.width: 1
    }
    Rectangle {   // luna 上/左白高光 + 下/右灰阴影（3D bevel 的全部秘密）
        anchors.fill: parent; visible: isLuna; color: "transparent"; radius: 3
        border.color: "#FFFFFF"; border.width: 1
        Rectangle {
            anchors.fill: parent; anchors.margins: 1; color: "transparent"; radius: 2
            border.color: "#ACA899"; border.width: 1
        }
    }

    Text {
        id: lbl
        anchors.centerIn: parent
        // 去装饰符号：不再给按钮文字套 [ ] 方括号，标签就是标签本身
        text: btn.label
        color: active
               ? (isPixel || isLcd ? "#0F380F" : (isLuna ? "#000000" : (isDet ? "#ff2d2d" : Theme.ink)))
               : (isLuna ? "#1f2226" : (isDet ? "#f2f2f2" : Theme.inkDim))
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSize
        font.letterSpacing: isNeon ? 2 : 0
        font.capitalization: isNeon || isTerminal ? Font.AllUppercase : Font.MixedCase
    }

    // hover 态：pixel/lcd 反色块，luna 淡蓝，neon 青边，决心暗红，其余 accentDim
    property bool hovered: false
    color: hovered
           ? (isPixel || isLcd ? "#9BBC0F"
             : (isLuna ? "#E4EDFA" : (isNeon ? "#2A1145" : (isDet ? "#2a0a0a" : Theme.accentDim))))
           : (active ? Theme.accentDim : "transparent")

    HoverHandler { id: hv; cursorShape: Qt.PointingHandCursor
                   onHoveredChanged: btn.hovered = hv.hovered }
    MouseArea {
        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
        onClicked: btn.clicked()
    }
}
