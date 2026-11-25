import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA

/*
 * 播放列表面板。
 *
 * 两个模式（v5 §5）：队列 / 库。
 * 面板跟随焦点槽位 —— 切换焦点时内容跟着换，用户不需要理解「面板属于谁」。
 *
 * 数据来源：core/library + core/playitem（C++ 侧注入）。
 * 此处先用静态占位数据，M1 接入真实扫描结果。
 */
Rectangle {
    id: root

    property int mode: 0        // 0 = 队列, 1 = 库
    property int focusSlotId: 0

    // 占位数据（M1 接 core）
    // 数据来自 AppController（core 层）：
    //   打开文件 → 自动扫描同目录 → 自然排序 → 队列
    // 两种模式用同一套 key（n / d / cur / slot）——数据形状统一
    property var queueItems: App.playlist
    property var libraryItems: App.playlist

    color: Theme.surface
    // 右边界
    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: Theme.border
        opacity: 0.5
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 模式切换 + 来源条
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 34

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Repeater {
                    model: [{ t: "队列" }, { t: "库" }]
                    delegate: Rectangle {
                        width: lab.implicitWidth + 16
                        height: 22
                        radius: Theme.radiusButton
                        color: (root.mode === index) ? Theme.accentDim : "transparent"
                        border.color: Theme.border
                        border.width: 1

                        Text {
                            id: lab
                            anchors.centerIn: parent
                            text: modelData.t
                            color: (root.mode === index) ? Theme.ink : Theme.inkDim
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSize - 1
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.mode = index
                        }
                    }
                }
            }

            // 来源条（v5.1 §4.1）：显示当前目录与项数
            Text {
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                text: root.mode === 0
                      ? (App.currentDirectory !== ""
                         ? App.currentDirectory.split("/").pop() + "\\  (" + App.playlistCount + " 项)"
                         : "未打开文件")
                      : App.playlistCount + " 项"
                color: Theme.inkDim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSize - 2
                elide: Text.ElideMiddle
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.border
            opacity: 0.5
        }

        // 空状态提示（在 Layout 里 → 用 Layout.alignment，不能用 anchors）
        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
            visible: App.playlistCount === 0
            text: "拖入视频文件\n自动收录同目录"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            lineHeight: 1.6
            color: Theme.inkDim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSize - 1
        }

        // 列表（虚拟滚动：ListView 复用 delegate）
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.mode === 0 ? root.queueItems : root.libraryItems
            spacing: 2
            topMargin: 6
            bottomMargin: 6

            delegate: Item {
                width: list.width
                height: 40

                required property int index
                required property var modelData

                Rectangle {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    radius: Theme.radiusButton
                    color: (root.mode === 0 && modelData.cur === true) ? Theme.accentDim : "transparent"
                    border.color: (root.mode === 0 && modelData.cur === true) ? Theme.accent : "transparent"
                    border.width: 1
                    opacity: (root.mode === 0 && modelData.cur === true) ? 1.0 : 0.85
                }

                // 双击列表项 → 切到该项（并分配到槽位）
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    cursorShape: Qt.PointingHandCursor
                    onDoubleClicked: App.playIndex(index)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 10
                    spacing: 8

                    // 序号 / 缩略图占位
                    Rectangle {
                        Layout.preferredWidth: 22
                        Layout.preferredHeight: 16
                        Layout.alignment: Qt.AlignVCenter
                        color: "transparent"
                        border.color: Theme.border
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.mode === 0 ? (index + 1) : "·"
                            color: Theme.inkDim
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSize - 3
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: modelData.n
                        color: Theme.ink
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSize - 1
                        elide: Text.ElideMiddle
                    }

                    // 库模式显示占用徽标（v5 §5）
                    Text {
                        visible: root.mode === 1
                        text: modelData.slot
                        color: (modelData.slot && modelData.slot !== "未装载") ? Theme.accent : Theme.inkDim
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSize - 3
                    }

                    // 队列模式显示时长
                    Text {
                        visible: root.mode === 0
                        text: modelData.d
                        color: Theme.inkDim
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSize - 3
                    }
                }
            }
        }
    }
}
