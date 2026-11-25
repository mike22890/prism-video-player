import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA

/*
 * 顶栏 —— 自绘窗口框架 + 极简状态。
 * 2026-11-26 重排：之前那行 "PRISM | SLOT 1 | 正在播 N 格 | 竖线" 是调试字，廉价感来源。
 * 新取向：一个品牌标记 + 产品名，右侧一个「正在播放」状态点 + 片名，最右窗口键。
 * 字重分层、留白、去掉所有装饰性竖线和方括号。拖动交给 C++ 的 startSystemMove。
 */
Rectangle {
    id: root

    property string viewMode: "grid"
    property int viewStackDepth: 0
    property int focusSlotId: 0
    property string nowPlaying: ""
    signal dragRequested()

    implicitHeight: 46
    color: Theme.panelColor

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        onPressed: root.dragRequested()
    }

    // 底部分隔：极细，收尾干净
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.border
        opacity: 0.35
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 18
        anchors.rightMargin: 0
        spacing: 0

        // ── 品牌：实心几何标记 + 字，一个焦点 ──
        Rectangle {
            Layout.preferredWidth: 12
            Layout.preferredHeight: 12
            Layout.alignment: Qt.AlignVCenter
            color: Theme.accent
            radius: Theme.style === "neon" || Theme.style === "modern" ? 3 : 0
        }
        Text {
            text: "PRISM"
            color: Theme.ink
            font.family: Theme.fontFamily
            font.pixelSize: 15
            font.bold: true
            font.letterSpacing: (Theme.style === "pixel" || Theme.style === "lcd") ? 3
                                : (Theme.style === "neon" ? 4 : 2.4)
            Layout.leftMargin: 10
        }
        // 版本号小字，弱化
        Text {
            text: "MEDIA"
            color: Theme.inkDim
            opacity: 0.55
            font.family: Theme.fontMono
            font.pixelSize: 9
            font.letterSpacing: 2
            Layout.leftMargin: 8
            Layout.alignment: Qt.AlignVCenter
        }

        Item { Layout.fillWidth: true }

        // ── 正在播放：呼吸点 + 片名 ──
        Item {
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredHeight: 20
            Layout.preferredWidth: playRow.implicitWidth
            visible: root.nowPlaying !== "" && root.width > 560
            RowLayout {
                id: playRow
                spacing: 8
                Rectangle {
                    width: 6; height: 6; radius: 3
                    color: Theme.success
                    Layout.alignment: Qt.AlignVCenter
                    SequentialAnimation on opacity {
                        running: true; loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 1100; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 1.0; duration: 1100; easing.type: Easing.InOutSine }
                    }
                }
                Text {
                    text: root.nowPlaying
                    color: Theme.inkDim
                    opacity: 0.8
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: 240
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                }
            }
        }

        Item { Layout.preferredWidth: 16 }

        // ── 窗口按钮组：细线图标，hover 才显色 ──
        RowLayout {
            spacing: 0
            Layout.fillHeight: true

            Repeater {
                model: [
                    { bid: "min",   glyph: "─" },
                    { bid: "max",   glyph: "□" },
                    { bid: "close", glyph: "✕" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillHeight: true
                    Layout.preferredWidth: 48
                    color: "transparent"

                    Rectangle {
                        anchors.centerIn: parent
                        width: 26; height: 26
                        radius: Theme.radiusButton
                        color: wh.hovered
                               ? (modelData.bid === "close" ? Theme.danger : Theme.surfaceAlt)
                               : "transparent"
                        Behavior on color { ColorAnimation { duration: 120 } }
                        Text {
                            anchors.centerIn: parent
                            text: modelData.glyph
                            color: wh.hovered ? (modelData.bid === "close" ? "#ffffff" : Theme.ink)
                                              : Theme.inkDim
                            opacity: wh.hovered ? 1 : 0.6
                            font.family: Theme.fontMono
                            font.pixelSize: modelData.bid === "close" ? 13 : 15
                        }
                    }
                    HoverHandler { id: wh; cursorShape: Qt.PointingHandCursor }
                    TapHandler {
                        onTapped: {
                            Sfx.play("tap")
                            if (modelData.bid === "min") WindowCtl.minimize()
                            else if (modelData.bid === "max") WindowCtl.toggleMaximize()
                            else WindowCtl.close()
                        }
                    }
                }
            }
        }
    }

    function reportTitleBarHeight() {
        var ratio = 1.0
        if (typeof Screen !== "undefined" && Screen.devicePixelRatio)
            ratio = Screen.devicePixelRatio
        WindowCtl.setTitleBarHeight(Math.round(root.height * ratio))
    }
    Component.onCompleted: reportTitleBarHeight()
    onHeightChanged: reportTitleBarHeight()
}
