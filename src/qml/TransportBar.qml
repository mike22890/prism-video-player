import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA

/*
 * 全局工具条（窗口底部）。2026-11-26 重排。
 * 之前：一排等宽的「主题:暗夜·静默 看色:关 格式:1 全屏 中/EN」标签按钮挤在右下，
 * 廉价感的主要来源。新取向：图标语义优先，分组 + 留白，标签只做短状态、悬停显示全称。
 * 播放/进度/音量在每个格子自己脚底下；这里只管全局：切集、循环、A-B、主题、着色、网格、全屏、语言。
 */
Rectangle {
    id: root

    property var player: null
    property string viewMode: "grid"
    property string themeLabel: "终端"
    property string shaderLabel: "关"
    property int gridCount: 1
    property int loopMode: 0
    property bool abLoop: false
    property bool pendingA: false
    property real abA: -1
    property real abB: -1

    signal viewToggleRequested()
    signal fullscreenRequested()
    signal themeRequested()
    signal shaderRequested()
    signal gridCountRequested()
    signal hintRequested(string text)
    signal loopModeRequested(int mode)

    implicitHeight: 52
    color: Theme.panelColor

    Rectangle {
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
        height: 1; color: Theme.border; opacity: 0.35
    }

    function syncFromPlayer() {
        if (!player) { abLoop = false; abA = -1; abB = -1; pendingA = false; return }
        if (pendingA) return
        abLoop = player.abLoopActive
        abA = player.abLoopA
        abB = player.abLoopB
    }

    // 精致的工具按钮：图标 + 可选短状态，圆点表示激活
    component ToolBtn: Item {
        id: tb
        property string glyph: ""
        property string status: ""
        property bool active: false
        property string tip: ""
        signal clicked()
        Layout.preferredWidth: tb.status !== "" ? tipText.implicitWidth + 30 : 34
        Layout.preferredHeight: 34
        Layout.alignment: Qt.AlignVCenter

        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusButton
            color: hov.hovered ? (tb.active ? Theme.accentDim : Theme.surfaceAlt)
                               : (tb.active ? Qt.rgba(0,0,0,0) : "transparent")
            border.color: tb.active ? Theme.accent : (hov.hovered ? Theme.border : "transparent")
            border.width: tb.active ? 1 : 1
            Behavior on color { ColorAnimation { duration: 120 } }
        }
        RowLayout {
            anchors.centerIn: parent
            spacing: 6
            Text {
                text: tb.glyph
                color: tb.active ? Theme.accent : (hov.hovered ? Theme.ink : Theme.inkDim)
                font.family: Theme.fontMono
                font.pixelSize: 15
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                id: tipText
                visible: tb.status !== ""
                text: tb.status
                color: tb.active ? Theme.ink : Theme.inkDim
                opacity: 0.9
                font.family: Theme.fontFamily
                font.pixelSize: 11
                elide: Text.ElideRight
                Layout.alignment: Qt.AlignVCenter
            }
        }
        HoverHandler { id: hov; cursorShape: Qt.PointingHandCursor }
        MouseArea { anchors.fill: parent; onClicked: tb.clicked() }
        ToolTip.visible: hov.hovered && tb.tip !== ""
        ToolTip.text: tb.tip
        ToolTip.delay: 500
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 6

        // ── 左组：切集 + 循环 + A-B ──
        ToolBtn { glyph: "|◀"; tip: App.tr["btn.prev"]; onClicked: { Sfx.play("nav"); App.previous() } }
        ToolBtn { glyph: "▶|"; tip: App.tr["btn.next"]; onClicked: { Sfx.play("nav"); App.next() } }

        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 20; color: Theme.border; opacity: 0.5; Layout.alignment: Qt.AlignVCenter; Layout.leftMargin: 4; Layout.rightMargin: 4 }

        ToolBtn {
            glyph: "↻"
            active: root.loopMode !== 0
            status: root.loopMode === 0 ? App.tr["loop.off"] : (root.loopMode === 1 ? App.tr["loop.file"] : App.tr["loop.all"])
            tip: App.tr["loop.all"]
            onClicked: { Sfx.play("toggle"); root.cycleLoop() }
        }
        ToolBtn {
            glyph: "◄►"
            active: root.abLoop || root.pendingA
            status: root.pendingA ? App.tr["btn.ab"] : (root.abLoop ? "A-B · ON" : "A-B")
            tip: App.tr["btn.ab"]
            onClicked: { Sfx.play("toggle"); root.markAb() }
        }

        Item { Layout.fillWidth: true }

        // ── 中组：音量 ──
        RowLayout {
            spacing: 8
            Layout.alignment: Qt.AlignVCenter
            Text { text: "VOL"; color: Theme.inkDim; opacity: 0.6; font.family: Theme.fontMono; font.pixelSize: 9; font.letterSpacing: 1 }
            Text { text: Math.round(App.volume); color: Theme.inkDim; font.family: Theme.fontMono; font.pixelSize: 11; Layout.minimumWidth: 20 }
            Item {
                Layout.preferredWidth: 84; Layout.preferredHeight: 20
                Rectangle {
                    id: volTrack
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width; height: 4; radius: 2
                    color: Theme.surfaceAlt
                    Rectangle { width: parent.width * Math.min(1, App.volume / 100); height: parent.height; radius: 2; color: Theme.accent }
                }
                MouseArea {
                    anchors.fill: parent
                    function setVol(px) { App.volume = Math.max(0, Math.min(100, Math.round((px / volTrack.width) * 100))) }
                    onClicked: function(m) { Sfx.play("tap"); setVol(m.x) }
                    onPositionChanged: function(m) { if (pressed) setVol(m.x) }
                }
            }
        }

        Item { Layout.fillWidth: true }

        // ── 右组：主题 / 着色 / 网格 / 全屏 / 语言 ──
        ToolBtn { glyph: "◆"; status: root.themeLabel; active: true; tip: App.tr["btn.theme"]; onClicked: { Sfx.play("toggle"); root.themeRequested() } }
        ToolBtn { glyph: "✦"; status: root.shaderLabel; active: root.shaderLabel !== App.tr["shader.off"]; tip: App.tr["btn.shader"]; onClicked: { Sfx.play("toggle"); root.shaderRequested() } }
        ToolBtn { glyph: "◉"; active: App.ambientLight; tip: "环境光 (A)"; onClicked: { Sfx.play("toggle"); App.ambientLight = !App.ambientLight } }
        ToolBtn { glyph: "▦"; status: "×" + root.gridCount; active: root.gridCount > 1; tip: App.tr["btn.grid"]; onClicked: { Sfx.play("toggle"); root.gridCountRequested() } }
        ToolBtn { glyph: "⛶"; tip: App.tr["btn.fullscreen"]; onClicked: { Sfx.play("toggle"); root.fullscreenRequested() } }
        ToolBtn {
            glyph: "文"
            tip: "中文 / English"
            onClicked: {
                Sfx.play("toggle")
                App.language = App.language === "zh-CN" ? "en" : "zh-CN"
            }
        }
    }

    function fmt(sec) {
        if (!isFinite(sec) || sec <= 0) return "00:00"
        var m = Math.floor(sec / 60), s = Math.floor(sec % 60)
        return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s
    }

    function cycleLoop() {
        var next = (root.loopMode + 1) % 3
        root.loopModeRequested(next)
        root.hintRequested(next === 0 ? "循环：关" : (next === 1 ? "循环：单集" : "循环：整个队列"))
    }

    function markAb() {
        if (!root.player) { console.log("VOLTA ab click: 没有焦点播放器"); return }
        if (root.abLoop) {
            root.player.clearAbLoop(); root.abLoop = false; root.pendingA = false
            root.hintRequested(App.tr["ab.cleared"])
        } else if (!root.pendingA) {
            root.abA = root.player.position; root.pendingA = true
            root.hintRequested("A 点：" + root.fmt(root.abA) + " —— 再点一次设 B")
        } else {
            var b = root.player.position
            if (b > root.abA) {
                root.player.setAbLoop(root.abA, b); root.abLoop = true
                root.hintRequested(App.tr["ab.range"].replace("%1", root.fmt(root.abA)).replace("%2", root.fmt(b)))
            } else {
                root.hintRequested("B 点要在 A 点之后")
            }
            root.pendingA = false
        }
    }
}
