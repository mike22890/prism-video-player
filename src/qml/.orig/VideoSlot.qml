import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import VOLTA

/*
 * 视频槽位。
 *
 * M0b 阶段：这里先是一个占位矩形（真实视频由 mpv 渲染进原生子 HWND，
 * 路径 B）或由 libmpv 直接画（路径 C）。
 *
 * 交互（v4）：
 *   单击 → 聚焦（切换焦点格 + 出声）
 *   双击 → 独占 / 返回（enterSolo / exitSolo）
 */
Rectangle {
    id: root

    property int slotId: 0
    property bool focused: false
    property string source: ""
    property string status: "就绪"     // 加载中/缓冲/播放/暂停/错误/休眠
    property bool paused: true
    property double position: 0.0
    property double duration: 0.0
    property bool abLoopActive: false
    property double abLoopA: -1
    property double abLoopB: -1
    property int loopMode: 0

    signal slotFocused(int id)
    signal slotDoubleClicked(int id)
    // 播放状态变化（供控制条读取）
    signal playbackStateChanged()

    color: Theme.surfaceAlt
    radius: Theme.radiusPanel
    // 内部子项（OSD/状态徽标）会撑出 implicitWidth，
    // 导致 GridLayout 的列最小宽把容器撑破 —— 归零让 Layout 自己分配
    implicitWidth: 0
    implicitHeight: 0
    border.color: focused ? Theme.accent : Theme.border
    border.width: focused ? 2 : 1

    // 聚焦时的辉光（终端主题）
    Behavior on border.width { NumberAnimation { duration: Theme.animMs } }

    // 视频画面（MpvItem = 进程内 libmpv → QQuickFramebufferObject）
    //
    // 宽高比处理：mpv 侧关掉了 keepaspect（画多少算多少），
    // 这里让 QML 按源宽高比摆 —— 保持比例，居中，上下/左右留黑边。
    MpvItem {
        id: video

        // 按源宽高比约束尺寸。
        // 不能用 anchors.centerIn —— anchors 会覆盖 width/height，
        // 导致画面溢出槽位（顶部 OSD 跑到边框外）。
        // 正确做法：只设 width/height，用 x/y 居中。
        readonly property real slotW: Math.max(1, root.width - 2)
        readonly property real slotH: Math.max(1, root.height - 2)
        readonly property real vidAR: (video.videoWidth > 0 && video.videoHeight > 0)
                                     ? video.videoWidth / video.videoHeight : 0

        width: vidAR > 0
               ? ((vidAR > slotW / slotH) ? slotW : Math.round(slotH * vidAR))
               : slotW
        height: vidAR > 0
                ? ((vidAR > slotW / slotH) ? Math.round(slotW / vidAR) : slotH)
                : slotH

        x: Math.round((root.width - width) / 2)
        y: Math.round((root.height - height) / 2)

        clip: true

        // source 由外部注入（AppController / 播放列表）
        source: root.source
        paused: root.paused
        onPositionChanged: { root.position = position; root.playbackStateChanged(); }
        onDurationChanged: { root.duration = duration; root.playbackStateChanged(); }
        onLastErrorChanged: { root.status = lastError; root.playbackStateChanged(); }
        onVolumeChanged: root.playbackStateChanged()
        onMutedChanged: root.playbackStateChanged()
        onAbLoopChanged: {
            root.abLoopActive = abLoopActive;
            root.abLoopA = abLoopA;
            root.abLoopB = abLoopB;
            root.playbackStateChanged();
        }
        onLoopModeChanged: { root.loopMode = loopMode; root.playbackStateChanged(); }
    }

    // 没有视频时显示占位底色
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        color: Theme.bg
        radius: Theme.radiusPanel
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.surfaceAlt }
            GradientStop { position: 1.0; color: Theme.bg }
        }
        visible: !root.source
    }

    // 左上角 OSD
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 8
        width: osd.implicitWidth + 12
        height: 20
        radius: Theme.radiusButton
        color: Theme.bg
        opacity: 0.75
        Text {
            id: osd
            anchors.centerIn: parent
            text: "SLOT " + (root.slotId + 1)
            color: Theme.inkDim
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSize - 3
        }
    }

    // 状态徽标（右下）
    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 8
        width: statusText.implicitWidth + 12
        height: 20
        radius: Theme.radiusButton
        color: Theme.bg
        opacity: 0.75
        Text {
            id: statusText
            anchors.centerIn: parent
            text: root.status
            color: Theme.inkDim
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSize - 3
        }
    }

    // 四角标记（终端主题的 CRT 取景框感）
    // Rectangle 没有单边宽度属性，L 形用「横条 + 竖条」两个矩形拼
    Repeater {
        model: 4
        delegate: Item {
            required property int index
            visible: Theme.scanlines || Theme.vignette
            width: 13
            height: 13
            x: (index % 2 === 0) ? 6 : parent.width - 19
            y: (index < 2) ? 6 : parent.height - 19

            // 横条
            Rectangle {
                width: parent.width
                height: 1
                color: Theme.accent
                x: 0
                y: (index < 2) ? 0 : parent.height - 1
            }
            // 竖条
            Rectangle {
                width: 1
                height: parent.height
                color: Theme.accent
                x: (index % 2 === 0) ? 0 : parent.width - 1
                y: 0
            }
        }
    }

    // ── 对外控制接口（TransportBar / 快捷键通过焦点槽位调用）──
    function togglePlay() { video.togglePlay(); }
    function play() { video.play(); }
    function pause() { video.pause(); }
    function seekTo(sec) { video.seekTo(sec); }
    function seekRelative(d) { video.seekRelative(d); }
    function setAbLoop(a, b) { video.setAbLoop(a, b); }
    function clearAbLoop() { video.clearAbLoop(); }
    function setVolume(v) { video.setVolume(v); }
    function setMuted(m) { video.setMuted(m); }
    function stepFrame(d) { video.stepFrame(d); }
    function setLoopMode(m) { video.setLoopMode(m); }

    // 鼠标交互
    MouseArea {
        id: slotMouse
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton
        onClicked: root.slotFocused(root.slotId)
        onDoubleClicked: root.slotDoubleClicked(root.slotId)
        // 悬停高亮，提前告知「可双击」
        hoverEnabled: true
        onEntered: root.opacity = 1.0
        onExited: root.opacity = 0.92
    }

    // 悬停提示
    Rectangle {
        anchors.centerIn: parent
        visible: slotMouse.containsMouse
        width: hintText.implicitWidth + 16
        height: 26
        radius: Theme.radiusButton
        color: Theme.bg
        opacity: 0.9
        border.color: Theme.border
        border.width: 1
        Text {
            id: hintText
            anchors.centerIn: parent
            text: "双击独占"
            color: Theme.ink
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSize - 1
        }
    }
}
