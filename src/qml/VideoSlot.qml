import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA

/*
 * 视频槽位 —— 学 gridplayer：每个格子自己的播放条就长在自己脚底下。
 *
 * 交互改过一轮：
 *   鼠标移进去 = 选中（不用点）     单击 = 播放/暂停     双击 = 独占
 *   滚轮 = 音量
 * 状态全部来自引擎（MpvItem 的 mpv 属性回读），QML 不自己编。
 */
Rectangle {
    id: root

    property int slotId: 0
    property bool focused: false
    property string source: ""
    property string shaderProfile: ""     // "" | crt | vhs

    readonly property bool paused: video.paused
    readonly property bool loaded: video.loaded
    readonly property string lastError: video.lastError
    readonly property double position: video.position
    readonly property double duration: video.duration
    property bool abLoopActive: false
    property double abLoopA: -1
    property double abLoopB: -1
    property int loopMode: 0

    signal slotFocused(int id)
    signal slotDoubleClicked(int id)
    signal playbackStateChanged()
    signal playbackEnded(int id)
    signal closeRequested(int id)
    // 让控制条知道「这一格刚做了什么」，用来弹提示
    signal hint(string text)

    readonly property string status: {
        if (!root.source)
            return "空闲"
        if (root.lastError !== "")
            return root.lastError
        if (!root.loaded)
            return "加载中"
        return root.paused ? "暂停" : "播放"
    }

    color: Theme.panelAltColor
    radius: Theme.radiusPanel
    implicitWidth: 0
    implicitHeight: 0
    border.color: Theme.border
    border.width: 1

    // ── 音频：只有焦点格出声 ──
    function applyAudio() {
        video.setVolume(App.volume)
        video.setMuted(App.muted || !root.focused)
    }

    Component.onCompleted: {
        applyAudio()
        video.setShaderProfile(shaderProfile)
    }
    onFocusedChanged: applyAudio()
    onShaderProfileChanged: video.setShaderProfile(shaderProfile)

    Connections {
        target: App
        function onVolumeChanged() { video.setVolume(App.volume) }
        function onMutedChanged() { root.applyAudio() }
    }

    // cover 容器：视频等比放大到铺满格子，超出部分裁掉 —— 不留黑边也不拉伸变形。
    Item {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 46
        clip: true

        // ── 环境光（ambient light）：抓视频边缘色，糊到视频四周空白区 ──
        // 只在焦点格 + 有视频时启用；非焦点格不抓纹理，避免四路各抓一次 FBO 掉帧。
        ShaderEffectSource {
            id: videoSrc
            sourceItem: root.focused ? video : null
            hideSource: false
            recursive: false
            live: true
            textureSize: Qt.size(160, 90)   // 降采样：辉光本就模糊，小纹理足够且便宜
        }
        ShaderEffect {
            id: ambient
            anchors.fill: parent
            visible: root.focused && root.source !== "" && root.loaded && App.ambientLight
            z: -1                            // 在视频后面
            property var source: videoSrc
            property real uTime: 0
            property color uTint: Theme.accent
            property vector4d uVideoRect: {
                var pw = parent.width, ph = parent.height
                if (pw <= 0 || ph <= 0) return Qt.vector4d(0,0,1,1)
                return Qt.vector4d(video.x/pw, video.y/ph, video.width/pw, video.height/ph)
            }
            property real uPad0: 0
            property real uPad1: 0
            fragmentShader: "qrc:/qml/ambient_glow.frag.qsb"
            NumberAnimation on uTime {
                from: 0; to: 1000; duration: 1000000
                loops: Animation.Infinite
                running: ambient.visible
            }
        }

        MpvItem {
            id: video

            readonly property real slotW: parent.width
            readonly property real slotH: parent.height
            property real vidAR: (videoWidth > 0 && videoHeight > 0)
                                 ? videoWidth / videoHeight : 0

            // 保持视频宽高比居中（默认播放器行为，不拉伸变形）。
            // 黑边是保持比例的必然结果；用户明确要"默认那种、不要拉伸"。
            width: vidAR > 0
                   ? ((vidAR > slotW / slotH) ? slotW : Math.round(slotH * vidAR))
                   : slotW
            height: vidAR > 0
                    ? ((vidAR > slotW / slotH) ? Math.round(slotW / vidAR) : slotH)
                    : slotH
            x: Math.round((slotW - width) / 2)
            y: Math.round((slotH - height) / 2)

            clip: true
            source: root.source

        onPositionChanged: root.playbackStateChanged()
        onDurationChanged: root.playbackStateChanged()
        onPausedChanged: root.playbackStateChanged()
        onLastErrorChanged: root.playbackStateChanged()
        onVolumeChanged: root.playbackStateChanged()
        onMutedChanged: root.playbackStateChanged()
        onAbLoopChanged: {
            root.abLoopActive = abLoopActive
            root.abLoopA = abLoopA
            root.abLoopB = abLoopB
            root.playbackStateChanged()
        }
        onLoopModeChanged: { root.loopMode = loopMode; root.playbackStateChanged() }
        onPlaybackEnded: root.playbackEnded(root.slotId)
        }
    }

    // ── 着色器的动态部分（滚动亮带 + 闪烁）：mpv 的 glsl 只做静态畸变，
    //    时间维度在这里补，这样不碰渲染管线、不重编译、四路也不掉帧。──
    Item {
        id: fxLayer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(0, root.height - 46)
        visible: root.shaderProfile !== "" && root.source !== ""
        z: 40

        Rectangle {
            id: rollBand
            width: parent.width
            height: Math.max(24, parent.height * 0.18)
            y: -height
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.5; color: Qt.rgba(1, 1, 1, root.shaderProfile === "vhs" ? 0.09 : 0.05) }
                GradientStop { position: 1.0; color: "transparent" }
            }
            SequentialAnimation on y {
                running: fxLayer.visible
                loops: Animation.Infinite
                NumberAnimation {
                    from: -rollBand.height
                    to: fxLayer.height
                    duration: root.shaderProfile === "vhs" ? 2600 : 4800
                    easing.type: Easing.Linear
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            color: "black"
            opacity: 0
            SequentialAnimation on opacity {
                running: fxLayer.visible
                loops: Animation.Infinite
                NumberAnimation { to: root.shaderProfile === "vhs" ? 0.07 : 0.035; duration: 80 }
                NumberAnimation { to: 0.0; duration: 140 }
                PauseAnimation { duration: 700 }
            }
        }

        // 暗角：跟着着色器一起上，主题不背这个锅
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(0, 0, 0, 0.28) }
                GradientStop { position: 0.35; color: "transparent" }
                GradientStop { position: 0.65; color: "transparent" }
                GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.38) }
            }
        }
    }

    // 没有视频时显示占位底色
    Rectangle {
        anchors.fill: parent
        anchors.bottomMargin: 46
        anchors.margins: 1
        color: Theme.bg
        radius: Theme.radiusPanel
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.surfaceAlt }
            GradientStop { position: 1.0; color: Theme.bg }
        }
        visible: !root.source
        z: 1
    }

    // 暂停/加载中央提示
    Text {
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -17
        z: 45
        visible: root.source !== "" && (root.paused || !root.loaded) && !mouse.containsMouse
        text: !root.loaded ? "…" : "▮▮"
        color: Theme.ink
        opacity: 0.6
        font.family: Theme.fontMono
        font.pixelSize: Math.max(14, Math.min(root.width, root.height) * 0.09)
    }

    // 右上关闭（关掉这一格，不是关掉整个播放器）
    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 8
        z: 62
        width: 22
        height: 22
        radius: Theme.radiusButton
        color: closeHover.hovered ? Theme.danger : Theme.bg
        opacity: closeHover.hovered ? 0.95 : 0.7
        border.color: Theme.border
        border.width: 1
        Behavior on opacity { NumberAnimation { duration: Theme.motionDuration } }

        Text {
            anchors.centerIn: parent
            text: "✕"
            color: closeHover.hovered ? Theme.bg : Theme.inkDim
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSize
        }
        HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: { Sfx.play("toggle"); root.closeRequested(root.slotId) }
        }
    }

    // 左上焦点角标：焦点格显示四角取景框线 + 编号，像 HUD，不再是"SLOT 1 ●"调试字
    Item {
        anchors.fill: parent
        anchors.margins: 6
        z: 46
        visible: root.focused
        readonly property int c: 16           // 角线长度
        readonly property int t: 2            // 线宽
        Rectangle { anchors.left: parent.left;   anchors.top: parent.top;      width: parent.c; height: parent.t; color: Theme.accent; opacity: 0.9 }
        Rectangle { anchors.left: parent.left;   anchors.top: parent.top;      width: parent.t; height: parent.c; color: Theme.accent; opacity: 0.9 }
        Rectangle { anchors.right: parent.right; anchors.top: parent.top;      width: parent.c; height: parent.t; color: Theme.accent; opacity: 0.9 }
        Rectangle { anchors.right: parent.right; anchors.top: parent.top;      width: parent.t; height: parent.c; color: Theme.accent; opacity: 0.9 }
        Rectangle { anchors.left: parent.left;   anchors.bottom: parent.bottom; width: parent.c; height: parent.t; color: Theme.accent; opacity: 0.9 }
        Rectangle { anchors.left: parent.left;   anchors.bottom: parent.bottom; width: parent.t; height: parent.c; color: Theme.accent; opacity: 0.9 }
        Rectangle { anchors.right: parent.right; anchors.bottom: parent.bottom; width: parent.c; height: parent.t; color: Theme.accent; opacity: 0.9 }
        Rectangle { anchors.right: parent.right; anchors.bottom: parent.bottom; width: parent.t; height: parent.c; color: Theme.accent; opacity: 0.9 }
        Text {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.margins: 10
            text: "0" + (root.slotId + 1)
            color: Theme.accent
            font.family: Theme.fontMono
            font.pixelSize: 11
            font.letterSpacing: 1
            opacity: 0.85
        }
    }

    // ── 每格自己的控制条（gridplayer 那套）──
    Rectangle {
        id: ownBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 46
        z: 60
        color: Theme.bg
        opacity: root.focused ? 0.92 : 0.72
        Behavior on opacity { NumberAnimation { duration: Theme.motionDuration } }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.border
            opacity: 0.6
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            spacing: 8

            // 播放/暂停（按主题换形态）
            ChromeBtn {
                label: root.paused ? "▶" : "❚❚"
                Layout.preferredWidth: 30
                onClicked: { Sfx.play("toggle"); root.togglePlay() }
            }

            // 进度
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 26

                Rectangle {
                    id: miniTrack
                    anchors.fill: parent
                    anchors.topMargin: 7
                    anchors.bottomMargin: 7
                    color: Theme.surfaceAlt
                    border.color: Theme.border
                    border.width: 1

                    // 拖动时只跟手，不动播放器：mpv 每收到一次 seek 就要重解码，
                    // 按鼠标移动的频率发 seek 就是「进度条很不丝滑」的来源。
                    // 松手才 seek 一次。
                    property real dragFrac: -1
                    readonly property real shownFrac: dragFrac >= 0
                        ? dragFrac
                        : (root.duration > 0 ? Math.min(1, root.position / root.duration) : 0)

                    Rectangle {
                        width: parent.width * miniTrack.shownFrac
                        height: parent.height
                        color: Theme.accentDim
                    }
                    // A/B 标记
                    Rectangle {
                        visible: root.abLoopA >= 0
                        x: root.duration > 0 ? parent.width * (root.abLoopA / root.duration) : 0
                        width: 2; height: parent.height; color: Theme.warning
                    }
                    Rectangle {
                        visible: root.abLoopB >= 0
                        x: root.duration > 0 ? parent.width * (root.abLoopB / root.duration) : 0
                        width: 2; height: parent.height; color: Theme.warning
                    }
                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        function fracAt(px) { return Math.max(0, Math.min(1, px / miniTrack.width)) }
                        onPressed: function(m) { miniTrack.dragFrac = fracAt(m.x) }
                        onPositionChanged: function(m) { if (pressed) miniTrack.dragFrac = fracAt(m.x) }
                        onReleased: function(m) {
                            var f = fracAt(m.x)
                            miniTrack.dragFrac = -1
                            if (root.duration > 0)
                                root.seekTo(f * root.duration)
                        }
                        onCanceled: miniTrack.dragFrac = -1
                    }
                }
            }

            Text {
                text: root.fmt(root.position) + " / " + root.fmt(root.duration)
                color: Theme.inkDim
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSize
            }

            // 音量（也是每格自己的，因为四路音量本来就各管各的）
            Text {
                text: App.muted ? "🔇" : "🔊"
                color: App.muted ? Theme.danger : Theme.inkDim
                font.pixelSize: Theme.fontSize
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { Sfx.play("toggle"); App.muted = !App.muted }
                }
            }
        }
    }

    function fmt(sec) {
        if (!isFinite(sec) || sec <= 0) return "00:00"
        var h = Math.floor(sec / 3600)
        var m = Math.floor((sec % 3600) / 60)
        var s = Math.floor(sec % 60)
        function p2(n) { return (n < 10 ? "0" : "") + n }
        return (h > 0 ? h + ":" : "") + p2(m) + ":" + p2(s)
    }

    // ── 对外控制 ──
    function togglePlay() { video.togglePlay() }
    function play() { video.play() }
    function pause() { video.pause() }
    function seekTo(sec) {
        var d = video.duration
        video.seekTo(Math.max(0, (d > 0) ? Math.min(sec, d) : sec))
    }
    function seekRelative(d) { seekTo(video.position + d) }
    function setAbLoop(a, b) { video.setAbLoop(a, b) }
    function clearAbLoop() { video.clearAbLoop() }
    function setVolume(v) { video.setVolume(v) }
    function setMuted(m) { video.setMuted(m) }
    function stepFrame(d) { video.stepFrame(d) }
    function setLoopMode(m) { video.setLoopMode(m) }

    // ── 独占/多路 画质与播放状态（Main.qml 的 enterSolo/exitSolo 调）──
    // tier: 0=省电(多路) 1=均衡 2=最佳(独占)；renderScale<=0 表示跟随 item 自动。
    property bool wasPlaying: false        // 独占前是否在播，退出后照原样恢复
    property bool soloPaused: false        // 是否被独占逻辑暂停（区别于用户手动暂停）
    function setQualityTier(t) { video.setQualityTier(t) }
    function setRenderScale(px) { video.setRenderScale(px) }
    function applySoloState(isFocused) {
        if (isFocused) {
            video.setQualityTier(2)
            video.setRenderScale(2560)
        } else {
            if (!soloPaused) {
                wasPlaying = !video.paused
                soloPaused = true
                video.pause()
            }
            video.setQualityTier(0)
            video.setRenderScale(0)
        }
    }
    function exitSoloState() {
        video.setQualityTier(1)
        video.setRenderScale(0)
        if (soloPaused) {
            if (wasPlaying) video.play()
            soloPaused = false
        }
    }

    // ── 鼠标：移进来就选中，单击暂停，双击独占 ──
    MouseArea {
        id: mouse
        anchors.fill: parent
        anchors.bottomMargin: 46
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton
        onEntered: { Sfx.play("hover"); root.slotFocused(root.slotId) }
        onClicked: { Sfx.play("toggle"); root.togglePlay() }
        onDoubleClicked: {
            if (WindowCtl.fullScreen) { WindowCtl.setFullScreen(false); return }
            root.slotDoubleClicked(root.slotId)
        }
    }

    WheelHandler {
        acceptedDevices: PointerDevice.Mouse
        onWheel: function(event) {
            App.volume = Math.max(0, Math.min(100, App.volume + (event.angleDelta.y > 0 ? 5 : -5)))
        }
    }

    // ── 焦点描边：独立最上层，四边闭合，视频 FBO 盖不住 ──
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: root.focused ? Theme.accent : Theme.border
        border.width: root.focused ? 2 : 1
        radius: Theme.radiusPanel
        z: 100
        Behavior on border.color { ColorAnimation { duration: Theme.motionDuration } }
    }

    // 悬停提示：跟着主题走
    Rectangle {
        anchors.bottom: ownBar.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 6
        z: 61
        visible: mouse.containsMouse && root.source !== ""
        width: hintTxt.implicitWidth + 16
        height: 22
        radius: Theme.radiusButton
        color: Theme.surface
        opacity: 0.92
        border.color: Theme.border
        border.width: 1
        Text {
            id: hintTxt
            anchors.centerIn: parent
            text: (root.paused ? App.tr["hint.paused"] : App.tr["hint.playing"]) + " · " + App.tr["hint.click"]
            color: Theme.inkDim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSize
        }
    }
}
