import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA

/*
 * 底部控制条 —— 作用于「焦点槽位」。
 *
 * player 由 Main.qml 传入（= 焦点 VideoSlot），所有操作走它的接口。
 * 没有焦点时按钮置灰（disabled），不假装能点。
 */
Rectangle {
    id: root

    property var player: null      // 焦点 VideoSlot（null = 无焦点）
    property int loopMode: 0       // 0=off 1=file 2=playlist
    property bool abLoop: false
    property real position: 0
    property real duration: 0
    property bool pendingA: false  // 已设 A 点，等待 B 点
    property real abA: -1
    property real abB: -1

    implicitHeight: 52
    color: Theme.surface

    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.border
        opacity: 0.5
    }

    // 从焦点槽位同步状态
    function syncFromPlayer() {
        if (!player) {
            position = 0; duration = 0;
            abLoop = false; abA = -1; abB = -1;
            loopMode = 0; pendingA = false;
            return;
        }
        position = player.position;
        duration = player.duration;
        abLoop = player.abLoopActive;
        abA = player.abLoopA;
        abB = player.abLoopB;
        loopMode = player.loopMode;
    }

    function fmt(sec) {
        if (!isFinite(sec) || sec < 0) return "00:00:00";
        var h = Math.floor(sec / 3600);
        var m = Math.floor((sec % 3600) / 60);
        var s = Math.floor(sec % 60);
        function p2(n) { return (n < 10 ? "0" : "") + n; }
        return p2(h) + ":" + p2(m) + ":" + p2(s);
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 8

        // ── 播放控制 ──
        Repeater {
            model: [
                { id: "play",   glyph: "▶",  tip: "播放/暂停" },
                { id: "prev",   glyph: "◀◀", tip: "上一个" },
                { id: "next",   glyph: "▶▶", tip: "下一个" },
                { id: "frameB", glyph: "◀|", tip: "后退一帧" },
                { id: "frameF", glyph: "|▶", tip: "前进一帧" }
            ]
            delegate: Rectangle {
                required property var modelData
                Layout.preferredWidth: 32
                Layout.preferredHeight: 24
                radius: Theme.radiusButton
                color: hover.hovered ? Theme.accentDim : "transparent"
                border.color: Theme.border
                border.width: 1
                opacity: root.player ? 1.0 : 0.4

                Text {
                    anchors.centerIn: parent
                    text: modelData.glyph
                    color: Theme.ink
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontSize - 1
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        console.log("VOLTA tap " + modelData.id + " player=" + (root.player ? "yes" : "null"));
                        if (!root.player) return;
                        if (modelData.id === "play")   root.player.togglePlay();
                        else if (modelData.id === "prev") root.player.seekTo(0);
                        else if (modelData.id === "next") root.player.seekRelative(10);
                        else if (modelData.id === "frameB") root.player.stepFrame(-1);
                        else if (modelData.id === "frameF") root.player.stepFrame(1);
                    }
                }
            }
        }

        // ── 进度条 ──
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 18

            Rectangle {
                id: track
                anchors.fill: parent
                anchors.topMargin: 6
                anchors.bottomMargin: 6
                radius: Theme.radiusInput
                color: Theme.bg
                border.color: Theme.border
                border.width: 1

                Rectangle {
                    width: parent.width * (root.duration > 0 ? root.position / root.duration : 0)
                    height: parent.height
                    radius: parent.radius
                    color: Theme.accentDim
                }
                // A 点
                Rectangle {
                    visible: root.abA >= 0
                    x: root.duration > 0 ? track.width * (root.abA / root.duration) : 0
                    width: 2
                    height: parent.height
                    color: Theme.warning
                }
                // B 点
                Rectangle {
                    visible: root.abB >= 0
                    x: root.duration > 0 ? track.width * (root.abB / root.duration) : 0
                    width: 2
                    height: parent.height
                    color: Theme.warning
                }
                // 悬停预览位置
                Rectangle {
                    visible: hoverTrack.containsMouse && root.duration > 0
                    x: (hoverTrack.mouseX / track.width) * track.width
                    width: 2
                    height: parent.height
                    color: Theme.ink
                    opacity: 0.6
                }
                MouseArea {
                    id: hoverTrack
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: function(mouse) {
                        if (root.player && root.duration > 0)
                            root.player.seekTo((mouse.x / track.width) * root.duration);
                    }
                }
            }
        }

        Text {
            text: root.fmt(root.position) + " / " + root.fmt(root.duration)
            color: Theme.inkDim
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSize - 1
        }

        // ── 模式组 ──
        Repeater {
            model: [
                { id: "loop",  t: "LOOP",      on: root.loopMode !== 0 },
                { id: "ab",    t: "A-B",       on: root.abLoop },
                { id: "markA", t: "设A点",     on: root.pendingA },
                { id: "grid",  t: "GRID:2x2",  on: false },
                { id: "enh",   t: "ENH:BAL",   on: false }
            ]
            delegate: Rectangle {
                required property var modelData
                Layout.preferredHeight: 24
                width: modeText.implicitWidth + 16
                radius: Theme.radiusButton
                color: modelData.on ? Theme.accentDim : "transparent"
                border.color: modelData.on ? Theme.accent : Theme.border
                border.width: 1
                opacity: (modelData.id === "grid" || modelData.id === "enh") ? 0.5 : 1.0

                Text {
                    id: modeText
                    anchors.centerIn: parent
                    text: modelData.t
                    color: modelData.on ? Theme.ink : Theme.inkDim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSize - 3
                }
                HoverHandler { id: mh; cursorShape: Qt.PointingHandCursor }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        console.log("VOLTA mode " + modelData.id);
                        if (modelData.id === "loop") {
                            root.loopMode = (root.loopMode + 1) % 3;
                            if (root.player) root.player.setLoopMode(root.loopMode);
                        } else if (modelData.id === "ab") {
                            if (!root.player) return;
                            if (root.abLoop) { root.player.clearAbLoop(); root.abLoop = false; }
                            else { root.player.setAbLoop(root.position, root.duration); root.abLoop = true; }
                        } else if (modelData.id === "markA") {
                            if (!root.player) return;
                            if (root.pendingA) {
                                root.player.setAbLoop(root.abA, root.position);
                                root.pendingA = false;
                                root.abLoop = true;
                            } else {
                                root.abA = root.position;
                                root.pendingA = true;
                            }
                        }
                    }
                }
            }
        }
    }
}
