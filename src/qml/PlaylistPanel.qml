import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA

/*
 * 左面板。
 *   队列 = 当前目录的播放顺序（打开一个文件就是它整目录）
 *   库   = 这次运行里打开过的所有目录汇总，跨目录、去重
 * 之前两个页签绑的是同一份数据，点来点去一模一样 —— 那不是「两个模式」，
 * 那是同一个列表换了个标题。
 *
 * 单击 = 放到第 1 格并播；双击 = 再开一格（1 → 2 → 3 → 4）。
 */
Rectangle {
    id: root

    property int mode: 0        // 0 = 队列(网格里正在放的), 1 = 库(全部文件)
    onModeChanged: console.log("VOLTA mode=" + mode + " lib=" + App.library.length)
    property var queueModel: []
    property int sortMode: 0     // 0=名称 1=修改时间 2=创建时间
    // 排序是「看得见的逻辑」，日志里得留一条 —— 不然验的时候只能靠眼睛猜
    onSortModeChanged: console.log("VOLTA sort=" + sortMode + " first="
                                   + (librarySorted.length ? librarySorted[0].n : "-"))
    // 只依赖 App.library.length —— 绝不能依赖 App.currentIndex！
    // 点库项会 currentIndexChanged，若这里依赖它，librarySorted 返回全新数组，
    // ListView 的 model 被整个替换 → 滚动位置丢失、列表"乱动"（用户报的 bug）。
    // 高亮改走下面独立的 curPath，不碰 model。
    readonly property var librarySorted: {
        var _ = App.library.length
        return App.librarySorted(sortMode)
    }

    // 当前播放项路径：由 App 的 currentIndexChanged 驱动，只更新这个字符串，
    // 不重建 model。delegate 的 isCurrent 绑它 → 高亮跟着走，列表位置不动。
    property string curPath: ""
    Connections {
        target: App
        function onCurrentIndexChanged() { curPath = App.pathAt(App.currentIndex) }
        function onLibraryChanged() { curPath = App.pathAt(App.currentIndex) }
    }
    Component.onCompleted: curPath = App.pathAt(App.currentIndex)

    signal openRequested()
    signal focusSlotRequested(int slotId)
    signal playIndexRequested(int index)
    signal addToGridRequested(int index)
    // 库页签用路径传：列表是排过序的，下标跟 App.library 的下标对不上
    signal openLibraryRequested(string path)

    color: Theme.panelColor

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

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 34

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Repeater {
                    model: [{ t: App.tr["tab.queue"] }, { t: App.tr["tab.library"] }]
                    delegate: ChromeBtn {
                        label: modelData.t
                        active: root.mode === index
                        onClicked: { Sfx.play("nav"); root.mode = index }
                    }
                }

                ChromeBtn {
                    visible: root.mode === 1
                    label: (root.sortMode === 0 ? App.tr["sort.name"]
                           : (root.sortMode === 1 ? App.tr["sort.mtime"] : App.tr["sort.ctime"])) + " ▾"
                    active: true
                    onClicked: { Sfx.play("toggle"); root.sortMode = (root.sortMode + 1) % 3 }
                }

                ChromeBtn {
                    label: App.tr["btn.open"]
                    active: true
                    onClicked: {
                        Sfx.play("tap")
                        console.log("VOLTA open clicked")
                        root.openRequested()
                    }
                }
            }

            Text {
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(implicitWidth, parent.width - 240)
                horizontalAlignment: Text.AlignRight
                text: root.mode === 0
                      ? App.tr["status.playing"].replace("%1", root.queueModel.length)
                      : App.tr["status.all"].replace("%1", App.library.length)
                color: Theme.inkDim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSize
                elide: Text.ElideMiddle
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.border
            opacity: 0.5
        }

        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
            visible: App.playlistCount === 0
            text: App.tr["empty.drop"]
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            lineHeight: 1.6
            color: Theme.inkDim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSize
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            visible: root.mode === 0 ? root.queueModel.length > 0 : App.library.length > 0
            model: root.mode === 0 ? root.queueModel : root.librarySorted
            spacing: 2
            topMargin: 6
            bottomMargin: 6
            // 不要在这里 positionViewAtIndex —— 用户点一个视频会触发 playIndex→
            // rebuildModel→model 变，若每次都定位，列表会「擅自跳到另一行」
            // （库模式排序后 currentIndex 是 playlist 下标，定位还是错的）。
            // 列表滚动交给用户；首次填充时用 populate 过渡即可。

            // 列表项进出场：淡入 + 轻微右移（反馈感，不是整屏闪）
            add: Transition {
                NumberAnimation { properties: "x"; from: 16; duration: 180; easing.type: Easing.OutCubic }
                NumberAnimation { properties: "opacity"; from: 0; duration: 180 }
            }
            remove: Transition {
                NumberAnimation { properties: "opacity"; to: 0; duration: 120 }
            }
            populate: Transition {
                NumberAnimation { properties: "opacity"; from: 0; duration: 220 }
            }

            // 滚动条：之前只有滚轮能滚，鼠标用户没法拖 —— 加一条跟着主题走的细条
            ScrollBar.vertical: ScrollBar {
                id: vbar
                policy: ScrollBar.AsNeeded
                width: 8
                contentItem: Rectangle {
                    implicitWidth: 6
                    radius: 3
                    color: vbar.pressed ? Theme.accent : Theme.border
                    opacity: vbar.active ? 0.9 : 0.45
                }
                background: Rectangle { color: "transparent" }
            }

            delegate: Item {
                width: list.width
                height: 72

                required property int index
                required property var modelData

                // 高亮必须跟「这条目的身份」走，不能跟它在列表里的行号走。
                // 库列表是 librarySorted（排过序的），index 是排序后的行号，
                // App.currentIndex 是 playlist（当前目录队列）的下标 —— 两个坐标系，
                // 用 index===currentIndex 判高亮，排序一变就点 A 亮 B（用户报的 bug）。
                // C++ 的 modelData.cur 是按路径算的（indexOfPath(path)==currentIndex），
                // 与排序无关，两种模式都用它才对得上。
                // 队列模式用 modelData.cur；库模式用 curPath 按路径比对，
                // 都不依赖会重建 model 的东西 —— 点视频时列表位置不动。
                readonly property bool isCurrent: (root.mode === 0)
                                                  ? (modelData.cur === true)
                                                  : (modelData.path === root.curPath && root.curPath !== "")
                property string thumb: ""
                property bool thumbAsked: false
                // 这个 delegate 现在挂的是哪个文件 —— ListView 复用 delegate 时
                // 不重置就会出现「缩略图跟视频对不上」：格子里还是上一条的图。
                property string thumbPath: ""

                function refreshThumb() {
                    var p = (modelData && modelData.path) ? modelData.path : ""
                    if (p === thumbPath) return
                    thumbPath = p
                    thumb = ""
                    thumbAsked = false
                    thumbRetry.retry = 0
                    if (p !== "") askThumb()
                }

                // 缩略图：第一次要的时候排队抽帧，抽好了 App 会发 thumbnailReady
                function askThumb() {
                    if (thumbAsked) return
                    thumbAsked = true
                    thumb = App.thumbnailForPath(modelData.path)
                    if (thumb === "") {
                        thumbRetry.retry = 0
                        thumbRetry.start()
                    }
                }
                Timer {
                    id: thumbRetry
                    // 抽帧是串行的（一次一个 mpv 进程），书多的时候要等；
                    // 12 次太快放弃，后面那些就永远没图。放宽到 40 次（约 16 秒）。
                    interval: 400
                    onTriggered: {
                        var t = App.thumbnailForPath(thumbPath)
                        if (t !== "") thumb = t
                        else if (retry < 40) { retry++; thumbRetry.start() }
                    }
                    property int retry: 0
                }
                Component.onCompleted: refreshThumb()
                onModelDataChanged: refreshThumb()

                Connections {
                    target: App
                    function onThumbnailReady(p) {
                        if (p === thumbPath)
                            thumb = App.thumbnailForPath(p)
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    anchors.topMargin: 2
                    anchors.bottomMargin: 2
                    radius: Theme.radiusButton
                    color: isCurrent ? Theme.accentDim
                                     : (itemHover.hovered ? Theme.surfaceAlt : "transparent")
                    border.color: isCurrent ? Theme.accent : "transparent"
                    border.width: isCurrent ? 1 : 0
                    Behavior on color { ColorAnimation { duration: Theme.motionDuration } }

                    // hover / 当前项：左侧强调条滑入（反馈感）
                    Rectangle {
                        width: 3
                        anchors.left: parent.left
                        anchors.top: parent.top; anchors.bottom: parent.bottom
                        anchors.topMargin: 6; anchors.bottomMargin: 6
                        color: Theme.accent
                        opacity: isCurrent || itemHover.hovered ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: 130 } }
                    }
                }

                HoverHandler { id: itemHover }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    cursorShape: Qt.PointingHandCursor
                    // 自己判双击：单击会触发 playIndex → 模型重建 → delegate 被换掉，
                    // 系统级的 onDoubleClicked 永远等不到第二下（踩过）。
                    property bool armed: false
                    onClicked: {
                        Sfx.play("tap")
                        if (armed) {
                            armed = false
                            clickTimer.stop()
                            if (root.mode === 0) root.focusSlotRequested(modelData.slotId)
                            else root.addToGridRequested(App.indexForPath(modelData.path))
                        } else {
                            armed = true
                            clickTimer.start()
                        }
                    }
                    Timer {
                        id: clickTimer
                        interval: 220
                        onTriggered: {
                            parent.armed = false
                            if (root.mode === 0) root.focusSlotRequested(modelData.slotId)
                            else root.openLibraryRequested(modelData.path)
                        }
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    anchors.topMargin: 4
                    anchors.bottomMargin: 4
                    spacing: 8

                    // 缩略图（16:9）
                    Rectangle {
                        Layout.preferredWidth: 96
                        Layout.preferredHeight: 54
                        Layout.alignment: Qt.AlignVCenter
                        color: Theme.bg
                        border.color: isCurrent ? Theme.accent : Theme.border
                        border.width: 1
                        clip: true

                        Image {
                            anchors.fill: parent
                            source: thumb
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            // cache: false —— 抽帧是「先给 URL、稍后文件才落盘」，
                            // 开缓存时同一 URL 的失败结果会被记住，那一行就永远只有编号。
                            cache: false
                            visible: thumb !== "" && status === Image.Ready
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: thumb === "" || parent.children[0].status !== Image.Ready
                            text: isCurrent ? "▶" : (index + 1)
                            color: isCurrent ? Theme.accent : Theme.inkDim
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSize
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            Layout.fillWidth: true
                            text: modelData.n
                            color: isCurrent ? Theme.accent : Theme.ink
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSize
                            elide: Text.ElideMiddle
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.mode === 1
                                  ? String(modelData.dir).split("/").pop()
                                  : (modelData.slot || "")
                            color: Theme.inkDim
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSize
                            elide: Text.ElideMiddle
                        }
                    }

                    Text {
                        visible: modelData.slot && modelData.slot !== "—"
                        text: modelData.slot
                        color: Theme.accent
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSize
                    }
                }
            }
        }
    }
}
