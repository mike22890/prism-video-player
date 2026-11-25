import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA
import "qrc:/qml"

/*
 * VOLTA 主入口。
 * 职责：装配 Shell + PlaylistPanel + 网格槽位 + TransportBar。
 * 不含业务逻辑 —— 那是 core/ 的事。
 */
ApplicationWindow {
    id: win
    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    visible: true
    title: "VOLTA"

    // 去掉 Qt 6 ApplicationWindow 自带的原生标题栏（内部窗口 _q_titlebar）
    // 原生样式位（Win11 圆角 / 系统阴影 / Aero Snap / 调整大小）
    // 由 C++ 侧 WindowFrame 补回，并在 WM_NCCALCSIZE 时重新断言 —— 见 ADR-0004
    flags: (typeof Qt !== "undefined" && Qt.platform && Qt.platform.os === "windows")
           ? (Qt.Window | Qt.FramelessWindowHint)
           : Qt.Window

    color: Theme.bg

    // 槽位的视频源由 AppController 分配（当前项 + 后续项）
    //
    // 不能写成 property var 数组 —— 数组元素在创建时求值一次，
    // 那时 App 还没数据，绑定不会重算，source 永远空。
    // 函数里读 App.playlist 会建立依赖 → playlistChanged 时自动重算
    function sourceForSlot(slotId) {
        var _ = App.playlist.length;   // 建立依赖
        return App.sourceForSlot(slotId);
    }

    // 视图栈深度（v4）：>0 时可以逐层返回
    property int viewStackDepth: 0
    property string viewMode: "grid"   // grid | solo
    property int focusSlotId: 0

    function enterSolo(slotId) {
        // v4：push 快照 → 进 SOLO
        viewStackDepth += 1
        viewMode = "solo"
        focusSlotId = slotId
    }

    // 焦点槽位（控制条作用于它）
    property var focusedSlot: null

    function exitSolo() {
        if (viewStackDepth > 0) {
            viewStackDepth -= 1
            viewMode = "grid"
        }
    }

    // 尺寸变化时打日志（排查最大化后 QML 布局未跟随的问题）
    onWidthChanged: console.log("VOLTA RESIZE win=" + win.width + "x" + win.height
                                + " rootCol=" + rootCol.width + "x" + rootCol.height
                                + " gridArea=" + gridArea.width)
    onHeightChanged: console.log("VOLTA RESIZE-H win=" + win.width + "x" + win.height
                                + " rootCol=" + rootCol.width + "x" + rootCol.height)

    Component.onCompleted: {
        // 默认焦点 = 第一个槽位，控制条立刻可用（不用先点一下才有反应）
        win.focusedSlot = slot0;
        console.log("VOLTA DEBUG win=" + win.width + "x" + win.height
                    + " rootCol=" + rootCol.width + "x" + rootCol.height
                    + " rowArea=" + rowArea.width + "x" + rowArea.height
                    + " gridArea=" + gridArea.width + "x" + gridArea.height
                    + " grid=" + grid.width + "x" + grid.height
                    + " list=" + listPanel.width);
    }

    // 拖放文件到窗口 → 自动收录同目录（v5.1）
    DropArea {
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop.hasUrls) {
                var files = [];
                for (var i = 0; i < drop.urls.length; ++i) {
                    if (drop.urls[i].toString().indexOf("file:") === 0)
                        files.push(drop.urls[i]);
                }
                if (files.length > 0) {
                    App.openFiles(files);
                    console.log("VOLTA dropped " + files.length + " file(s)");
                }
            }
        }
    }

    // 键盘：ApplicationWindow 不是 Item，Keys 挂不上 → 用 Shortcut
    Shortcut {
        sequences: [StandardKey.Cancel, "Esc", "Backspace"]
        onActivated: win.exitSolo()
    }
    Shortcut {
        sequences: ["G"]
        onActivated: win.viewMode = (win.viewMode === "grid") ? "solo" : "grid"
    }

    // ── 主题叠加层（Terminal 风格）─────────────────────────────
    // 放在 Main.qml 内联：qrc 里的跨文件 import 需要目录形式，
    // 为两个 Component 单独建文件不划算。
    Component {
        id: overlayScanlines
        Canvas {
            id: scanCanvas
            anchors.fill: parent
            visible: Theme.scanlines
            onPaint: {
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                ctx.fillStyle = Qt.rgba(0, 0, 0, 0.30);
                for (var y = 0; y < height; y += 3) {
                    ctx.fillRect(0, y, width, 1);
                }
            }
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
        }
    }

    Component {
        id: overlayVignette
        Rectangle {
            anchors.fill: parent
            visible: Theme.vignette
            color: "transparent"
            gradient: Gradient {
                GradientStop { position: 0.0;  color: "transparent" }
                GradientStop { position: 0.52; color: "transparent" }
                GradientStop { position: 1.0;  color: Qt.rgba(0, 0, 0, 0.62) }
            }
        }
    }

    ColumnLayout {
        id: rootCol
        anchors.fill: parent
        spacing: 0

        Shell {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            Layout.minimumHeight: 44
            Layout.maximumHeight: 44
            viewMode: win.viewMode
            viewStackDepth: win.viewStackDepth
            focusSlotId: win.focusSlotId
        }

        RowLayout {
            id: rowArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            PlaylistPanel {
                id: listPanel
                Layout.preferredWidth: 320
                Layout.minimumWidth: 320
                Layout.maximumWidth: 320
                Layout.fillHeight: true
            }

            // 视频网格区
            Rectangle {
                id: gridArea
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 0
                Layout.minimumHeight: 0
                color: Theme.bg

                GridLayout {
                    id: grid
                    anchors.fill: parent
                    anchors.margins: 8
                    Layout.minimumWidth: 0
                    Layout.minimumHeight: 0
                    columns: win.viewMode === "solo" ? 1 : 2
                    rows: win.viewMode === "solo" ? 1 : 2
                    // GridLayout 用 rowSpacing/columnSpacing，没有 spacing
                    rowSpacing: 8
                    columnSpacing: 8

                    VideoSlot {
                        id: slot0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 0
                        Layout.minimumHeight: 0
                        Layout.maximumWidth: Infinity
                        Layout.maximumHeight: Infinity
                        slotId: 0
                        source: win.sourceForSlot(0)
                        onSlotFocused: win.focusedSlot = this
                    }
                    VideoSlot {
                        id: slot1
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 0
                        Layout.minimumHeight: 0
                        Layout.maximumWidth: Infinity
                        Layout.maximumHeight: Infinity
                        slotId: 1
                        source: win.sourceForSlot(1)
                        onSlotFocused: win.focusedSlot = this
                    }
                    VideoSlot {
                        id: slot2
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 0
                        Layout.minimumHeight: 0
                        Layout.maximumWidth: Infinity
                        Layout.maximumHeight: Infinity
                        slotId: 2
                        source: win.sourceForSlot(2)
                        onSlotFocused: win.focusedSlot = this
                    }
                    VideoSlot {
                        id: slot3
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 0
                        Layout.minimumHeight: 0
                        Layout.maximumWidth: Infinity
                        Layout.maximumHeight: Infinity
                        slotId: 3
                        source: win.sourceForSlot(3)
                        onSlotFocused: win.focusedSlot = this
                    }
                }

                // 终端主题的扫描线/暗角覆盖在视频区
                Loader {
                    anchors.fill: parent
                    sourceComponent: overlayScanlines
                    z: 100
                }
                Loader {
                    anchors.fill: parent
                    sourceComponent: overlayVignette
                    z: 101
                }
            }
        }

        TransportBar {
            id: bar
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            Layout.minimumHeight: 52
            Layout.maximumHeight: 52
            player: win.focusedSlot
            // 焦点槽位的状态变化 → 同步到控制条
            onPlayerChanged: bar.syncFromPlayer()
            Connections {
                target: win.focusedSlot
                function onPlaybackStateChanged() { bar.syncFromPlayer(); }
            }
        }
    }
}
