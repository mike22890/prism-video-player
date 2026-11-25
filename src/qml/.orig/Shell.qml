import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA

/*
 * 顶栏 —— 自绘窗口框架 + 状态条合一。
 *
 * 为什么合并：播放器本来就该有自己的顶栏，Windows 那个灰条是外挂的。
 * 分成两行浪费 40px 竖向空间，而状态信息完全可以塞进标题栏左侧。
 *
 * 拖动靠 C++ 侧的 WM_NCHITTEST（返回 HTCAPTION）→ 系统接管，
 * 拖动 / 双击最大化 / Aero Snap 全是原生行为，不自己模拟。
 * 右侧按钮区在 C++ 侧被排除（140px），所以点按钮不会变成拖窗口。
 */
Rectangle {
    id: root

    property string viewMode: "grid"
    property int viewStackDepth: 0
    property int focusSlotId: 0

    implicitHeight: 40
    color: Theme.surface

    // 底部分隔线
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.border
        opacity: 0.6
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 0
        spacing: 16

        // ── 品牌 + 光标 ──
        RowLayout {
            spacing: 6
            Text {
                text: "VOLTA"
                color: Theme.accent
                font.family: Theme.fontFamily
                font.pixelSize: 16
                font.bold: true
                font.letterSpacing: 1.5
            }
            Loader {
                sourceComponent: Theme.cursorBlinkComponent
                active: true
                Layout.alignment: Qt.AlignVCenter
            }
        }

        // ── 状态信息 ──
        Repeater {
            model: [
                { k: "引擎", v: "mpv 0.42.0" },
                { k: "管线", v: "gpu-next" },
                { k: "视图", v: root.viewMode === "solo" ? "SOLO" : "GRID" },
                { k: "回退", v: root.viewStackDepth > 0 ? root.viewStackDepth + " 层" : "—" }
            ]
            delegate: RowLayout {
                required property var modelData
                spacing: 4
                visible: root.width > 860
                Text {
                    text: modelData.k
                    color: Theme.inkDim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSize - 2
                }
                Text {
                    text: modelData.v
                    color: Theme.ink
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSize - 2
                }
            }
        }

        Item { Layout.fillWidth: true }

        // ── 窗口按钮组 ──
        RowLayout {
            spacing: 0
            Layout.fillHeight: true

            Repeater {
                model: [
                    { bid: "min",   glyph: "─", label: "最小化" },
                    { bid: "max",   glyph: "▣", label: "最大化" },
                    { bid: "close", glyph: "✕", label: "关闭" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillHeight: true
                    Layout.preferredWidth: 44
                    color: hover.hovered
                           ? (modelData.bid === "close" ? Theme.danger : Theme.accentDim)
                           : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: modelData.glyph
                        color: hover.hovered ? Theme.bg : Theme.ink
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSize
                    }

                    HoverHandler {
                        id: hover
                        cursorShape: Qt.PointingHandCursor
                    }

                    TapHandler {
                        onTapped: {
                            if (modelData.bid === "min")
                                WindowCtl.minimize();
                            else if (modelData.bid === "max")
                                WindowCtl.toggleMaximize();
                            else
                                WindowCtl.close();
                        }
                    }
                }
            }
        }
    }

    // 把标题栏的实际物理高度告诉 C++（WM_NCHITTEST 用它判断拖动区）
    // 注意：要用物理像素，QML 的 height 是逻辑像素，需乘 devicePixelRatio
    function reportTitleBarHeight() {
        var ratio = 1.0;
        if (typeof Screen !== "undefined" && Screen.devicePixelRatio)
            ratio = Screen.devicePixelRatio;
        WindowCtl.setTitleBarHeight(Math.round(root.height * ratio));
    }

    Component.onCompleted: reportTitleBarHeight()
    onHeightChanged: reportTitleBarHeight()
}
