import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Dialogs
import QtMultimedia
import Qt.labs.settings 1.1
import VOLTA
import "qrc:/qml"

/*
 * VOLTA 主入口。
 *
 * 网格是「按需长出来的」：默认一格，双击队列项再开一格，最多四格。
 * 一打开就把四个格子全塞满不是功能，那是把用户的选择权提前用完了。
 */
ApplicationWindow {
    id: win
    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    visible: true
    title: "Prism — 多格视频播放器"

    flags: (typeof Qt !== "undefined" && Qt.platform && Qt.platform.os === "windows")
           ? (Qt.Window | Qt.FramelessWindowHint)
           : Qt.Window

    // 不透明窗口底色：保住 GL surface，全屏切换不黑屏。
    // 桌面不透进来靠 ThemeBackdrop 里那层不透明实心底（面板半透明只透它上面的动画）。
    color: Theme.bg

    // ── 主题音效 ─────────────────────────────────────────────
    // 每个主题一个专属 wav，切主题时 loadTheme 设好 Theme.soundPath，这里播。
    // 静音/缺文件时 source 为空，play() 静默失败，不影响界面。
    SoundEffect { id: themeSfx; volume: 0.55 }

    // ── 网格状态 ────────────────────────────────────────────
    // slotIdx[i] = 第 i 格放队列里的第几项；-1 = 空。slot0 永远跟当前项。
    property var slotIdx: []   // slotIdx[i] = 第 i 格（i>=1）放的队列下标
    property int gridCount: 1
    // 循环模式：全局（0 关 / 1 单集 / 2 整个队列），每个格子一起听令
    property int loopMode: 0
    property string lastDir: ""
    onGridCountChanged: console.log("VOLTA grid count=" + gridCount + " slots=" + JSON.stringify(slotIdx))
    property int viewStackDepth: 0
    property string viewMode: "grid"
    property int focusSlotId: 0
    // 格子对象由 delegate 自己登记进来 —— 比 grid.itemAt() 稳：
    // 不依赖 Layout 的实现细节，也不依赖 id 在函数作用域里能不能解析。
    property var slotRefs: []
    function registerSlot(i, item) {
        var a = slotRefs.slice()
        a[i] = item
        slotRefs = a            // 整只重新赋值，绑定才会重算
    }
    function trimSlotRefs(n) {
        slotRefs = slotRefs.slice(0, n)
    }
    // 焦点格：跟着 focusSlotId 和登记表走
    readonly property var focusedSlot: {
        var id = focusSlotId
        return (id >= 0 && id < slotRefs.length) ? slotRefs[id] : null
    }

    readonly property bool isFullScreen: WindowCtl.fullScreen
    // 正在拖/拉窗口边框（WM_ENTERSIZEMOVE..WM_EXITSIZEMOVE）。拖动期间装饰动画
    // 一律停 —— 每一帧动画都要一次 present，而一次 present 就是 12~15ms；
    // 它和「跟手」抢的是同一个 vsync，抢输了窗口就掉到鼠标后面。
    readonly property bool windowResizing: WindowCtl.resizing

    // ── 主题 / 着色器 ─────────────────────────────────────────
    // 主题从 Theme 单例动态读（themes/ 下每个带 theme.json 的目录就是一个主题），
    // 加主题只要丢个目录进去，不用改这里 —— 不然「切换后逻辑死亡」。
    readonly property var themeIds: Theme.availableThemes()
    // 主题显示名：英文界面用英文名，中文界面用 theme.json 的中文名。
    // 读一次 App.language 建立依赖 —— 否则切语言时这个绑定不重算，名字卡在旧语言。
    readonly property var themeLabels: {
        var lang = App.language
        var enNames = {
            default: "Dark·Silence", gameboy: "GameBoy·4Green", nes: "8bit·NES",
            synthwave: "Synthwave·Sunset", terminal: "Terminal·Phosphor",
            determination: "Determination·Mono", winxp: "Blue·Luna"
        }
        var out = []
        for (var i = 0; i < themeIds.length; ++i) {
            var t = Theme.themeNameFor(themeIds[i])
            if (lang === "en") {
                var en = enNames[themeIds[i]]
                out.push(en || themeIds[i])
            } else {
                out.push(t || themeIds[i])
            }
        }
        return out
    }
    property int themeIdx: 0
    readonly property var shaderProfiles: ["", "crt", "vhs", "neon", "lcd", "pixel"]
    readonly property var shaderLabels: [App.tr["shader.off"], App.tr["shader.crt"], App.tr["shader.vhs"], App.tr["shader.neon"], App.tr["shader.lcd"], App.tr["shader.pixel"]]
    property int shaderIdx: 0
    readonly property string shaderProfile: shaderProfiles[shaderIdx]
    readonly property string themeLabel: themeLabels[themeIdx]
    readonly property string shaderLabel: shaderLabels[shaderIdx]

    // 队列页签 = 网格里正在放的这几格（跟「库」终于不是同一份数据了）
    readonly property var gridItems: {
        var _ = App.playlist.length          // 建立依赖
        var g = win.gridCount
        var out = []
        for (var i = 0; i < g; ++i) {
            var idx = (i === 0) ? App.currentIndex : win.slotIdx[i]
            if (idx === undefined || idx < 0) continue
            var p = App.pathAt(idx)
            if (p === "") continue
            var f = p.split(/[\\/]/).pop().replace(/\.[^.]+$/, "")
            out.push({ n: f, path: p, slot: "SLOT " + (i + 1), slotId: i,
                       cur: (i === win.focusSlotId), index: idx })
        }
        return out
    }

    function sourceForSlot(slotId) {
        var _ = App.playlist.length
        var idx = (slotId === 0) ? App.currentIndex : slotIdx[slotId]
        if (idx === undefined || idx < 0) return ""
        return App.pathAt(idx)
    }

    function addToGrid(index) {
        if (index < 0) return
        console.log("VOLTA addToGrid index=" + index + " gridBefore=" + gridCount)
        if (gridCount >= App.playlistCount) {
            toast(App.tr["msg.queued"])
            return
        }
        var a = slotIdx.slice()
        a[gridCount] = index
        slotIdx = a
        gridCount = gridCount + 1
        toast("第 " + gridCount + " 格：" + (App.pathAt(index) + "").split(/[\\/]/).pop())
    }

    function applyLoopMode(mode) {
        loopMode = mode
        console.log("VOLTA loop -> " + mode)
        for (var i = 0; i < gridCount; ++i) {
            var s = slotById(i)
            if (s) s.setLoopMode(mode)
        }
    }

    function onSlotEnded(slotId) {
        // 第 2..4 格不参与队列推进（推进只有第 1 格说了算），
        // 但也不能就停在最后一帧 —— 自己从头再放，画面一直在动。
        if (slotId !== 0) {
            var s = slotById(slotId)
            // 被独占逻辑暂停的格子播完不自启（否则「暂停其它」会被 EOF 偷偷解除）
            if (s && s.soloPaused) {
                console.log("VOLTA slot " + slotId + " ended while solo-paused, stay paused")
                return
            }
            if (s) { s.seekTo(0); s.play() }
            console.log("VOLTA slot " + slotId + " ended -> replay from 0")
            return
        }
        if (loopMode === 1) return                  // 单集：引擎自己重播，不会走到这
        if (loopMode === 2) { App.next(); return }  // 整列：到头绕回第一个
        App.advance()                               // 其余：播完下一个
    }

    // 把某个队列项直接塞进指定格子（库页签点击用：悬停哪格就开哪格）
    function assignToSlot(slotId, idx) {
        if (idx < 0) return
        if (slotId === 0) { App.playIndex(idx); return }
        var a = slotIdx.slice()
        a[slotId] = idx
        slotIdx = a
        focusSlot(slotId)
        console.log("VOLTA assign slot=" + slotId + " index=" + idx)
    }

    function removeSlot(slotId) {
        if (gridCount <= 1) {
            toast(App.tr["msg.lastSlot"])
            return
        }
        if (slotId === 0) {
            // 关掉第 1 格：把第 2 格的内容顶上来到当前项
            var nextIdx = (slotIdx[1] !== undefined) ? slotIdx[1] : App.currentIndex
            if (nextIdx >= 0) App.playIndex(nextIdx)
            var a0 = slotIdx.slice()
            a0.splice(1, 1)
            slotIdx = a0
        } else {
            var a = slotIdx.slice()
            a.splice(slotId, 1)
            slotIdx = a
        }
        gridCount = gridCount - 1
        trimSlotRefs(gridCount)      // delegate 已被 Repeater 销毁，别留悬空引用
        focusSlot(Math.min(focusSlotId, gridCount - 1))
        console.log("VOLTA removeSlot " + slotId + " -> grid=" + gridCount
                    + " slots=" + JSON.stringify(slotIdx))
        toast(App.tr["toast.slotClosed"].replace("%1", slotId + 1))
    }

    function removeLastSlot() {
        if (gridCount <= 1) return
        var a = slotIdx.slice()
        a[gridCount - 1] = -1
        slotIdx = a
        gridCount = gridCount - 1
        trimSlotRefs(gridCount)
        if (focusSlotId >= gridCount) focusSlot(focusSlotId - 1)
        toast(App.tr["toast.slotClosed"].replace("%1", gridCount + 1))
    }

    function cycleGridCount() {
        if (gridCount >= Math.min(9, App.playlistCount)) {
            slotIdx = [-1, -1, -1, -1]
            gridCount = 1
            trimSlotRefs(1)
            focusSlot(0)
            toast(App.tr["toast.backSingle"])
        } else {
            // 用队列里的下一项填新格子
            var next = App.currentIndex + gridCount
            if (next < App.playlistCount) addToGrid(next)
            else toast(App.tr["msg.noMore"])
        }
    }

    function slotById(id) {
        return (id >= 0 && id < slotRefs.length) ? slotRefs[id] : null;
    }

    function focusSlot(id) {
        focusSlotId = id
        // 打 player 是为了证明「焦点 → 播放器对象」这条线真的接上了：
        // 上一版这里永远是 null，空格键按下去跟按在键盘上没区别。
        console.log("VOLTA focus slot=" + id + " player=" + (focusedSlot ? "ok" : "null")
                    + " refs=" + slotRefs.length)
    }

    function enterSolo(slotId) {
        viewStackDepth += 1
        viewMode = "solo"
        focusSlot(slotId)
        // 独占：当前格最佳画质、其它格暂停并降档（用户要的「放大看清楚」）
        for (var i = 0; i < slotRefs.length; ++i) {
            var s = slotRefs[i]
            if (s) s.applySoloState(i === slotId)
        }
        toast(App.tr["toast.solo"].replace("%1", slotId + 1))
        console.log("VOLTA view solo slot=" + slotId)
    }

    function exitSolo() {
        if (viewStackDepth > 0) {
            viewStackDepth -= 1
            viewMode = "grid"
            for (var i = 0; i < slotRefs.length; ++i) {
                var s = slotRefs[i]
                if (s) s.exitSoloState()
            }
            console.log("VOLTA view grid")
        }
    }

    function toggleSolo(slotId) {
        if (viewMode === "solo" && focusSlotId === slotId) exitSolo()
        else enterSolo(slotId)
    }

    function toggleFullScreen() {
        WindowCtl.setFullScreen(!WindowCtl.fullScreen)
        console.log("VOLTA fullscreen=" + (WindowCtl.fullScreen ? "on" : "off"))
    }

    // 主题切换转场：一条发光扫描线从上扫到下 + 播该主题的专属音效。
    // 转场层在 rootCol 里（id: themeWipe），这里只发信号触发。
    signal themeSwitchFlash()
    function cycleTheme() {
        themeIdx = (themeIdx + 1) % themeIds.length
        var id = themeIds[themeIdx]
        Theme.loadTheme(id)
        App.themeId = id
        Sfx.themeId = id
        // 切主题只换外观，不动着色器 —— 着色器是用户自己按 S 选的，
        // 主题偷偷改它会导致「我明明关了 FX 怎么又花了」（用户明确要求）。
        // 专属音效：Theme.soundPath 是切主题后 loadTheme 设好的当前主题音效
        if (themeSfx && Theme.soundPath !== "") {
            themeSfx.source = Theme.soundPath
            themeSfx.play()
        }
        themeSwitchFlash()
        toast(App.tr["toast.theme"].replace("%1", themeLabels[themeIdx] || id))
        console.log("VOLTA theme -> " + id)
    }

    function cycleShader() {
        Sfx.play("toggle")
        shaderIdx = (shaderIdx + 1) % shaderProfiles.length
        toast(App.tr["toast.shader"].replace("%1", shaderLabels[shaderIdx]))
        console.log("VOLTA shader -> " + (shaderProfiles[shaderIdx] === ""
                                          ? "off" : shaderProfiles[shaderIdx]))
    }

    // ── 提示条 ───────────────────────────────────────────────
    property string toastText: ""
    function toast(t) { toastText = t; toastTimer.restart() }
    Timer { id: toastTimer; interval: 1700; onTriggered: win.toastText = "" }

    // 换目录时才把网格收回一格。
    // 注意：App.currentDirectory 的 NOTIFY 是 playlistChanged —— 每次切集都会响，
    // 之前直接在这里重置，结果「播完自动下一集」把两格打回一格（用户骂的那个）。
    Connections {
        target: App
        // 单实例：第二个进程把视频路径转交进来 → 开成新的一格，而不是新窗口
        function onExternalFilesReceived(paths) {
            console.log("VOLTA external files: " + paths.length)
            for (var i = 0; i < paths.length; ++i) {
                var idx = App.indexForPath(paths[i])
                if (idx < 0) {
                    App.openFile("file:///" + paths[i])
                    idx = App.currentIndex
                }
                if (idx >= 0) {
                    if (gridCount === 1 && App.currentIndex === idx && !sourceForSlot(0))
                        continue
                    addToGrid(idx)
                }
            }
        }
        function onPlaylistChanged() {
            if (App.currentDirectory !== win.lastDir) {
                win.lastDir = App.currentDirectory
                win.slotIdx = []
                win.gridCount = 1
                win.trimSlotRefs(1)
                win.focusSlot(0)
            }
        }
    }

    // 窗口尺寸变化不要再打日志：onWidthChanged 每变一像素响一次，
    // 拖一次窗口边缘就是几百条写盘，这就是「拖窗口卡」的来源之一。
    // 真要量尺寸，用窗口旁的 tools/vischeck.py 或者临时加回来。

    // ── 记住我动过的开关（2026-11-18：用户要求下次打开还是这套）──
    // 主题 / 着色器 / 循环 / 排序 / 窗口位置与大小，落在注册表（QSettings 的 Windows 后端）。
    // 写盘要防抖：拖窗口时每像素写一次注册表比写日志还贵。
    Settings {
        id: prefs
        category: "view"

        property int themeIdx: 0
        property int shaderIdx: 0
        property int loopMode: 0
        property int sortMode: 0
        property int windowX: -1
        property int windowY: -1
        property int windowW: 1280
        property int windowH: 800
    }

    Timer {
        id: geoDebounce
        interval: 700
        onTriggered: {
            // 最大化/全屏时的几何不是用户选的位置：存进去会让「还原」和下次启动
            // 都跑到最大化尺寸上（拖窗口松手 700ms 后正好是最大化状态）。
            if (win.visibility === Window.Maximized || win.visibility === Window.FullScreen)
                return
            prefs.windowX = Math.round(win.x)
            prefs.windowY = Math.round(win.y)
            prefs.windowW = Math.round(win.width)
            prefs.windowH = Math.round(win.height)
        }
    }

    onXChanged: geoDebounce.restart()
    onYChanged: geoDebounce.restart()
    onWidthChanged: geoDebounce.restart()
    onHeightChanged: geoDebounce.restart()
    onThemeIdxChanged: prefs.themeIdx = themeIdx
    onShaderIdxChanged: prefs.shaderIdx = shaderIdx
    onLoopModeChanged: prefs.loopMode = loopMode

    Component.onCompleted: {
        // 恢复上次的开关。先恢复窗口尺寸再摆位置，免得被最小尺寸夹一下。
        if (prefs.windowW >= minimumWidth && prefs.windowH >= minimumHeight) {
            win.width = prefs.windowW
            win.height = prefs.windowH
        }
        if (prefs.windowX > -100000 && prefs.windowY > -100000
                && prefs.windowX !== -1 && prefs.windowY !== -1) {
            win.x = prefs.windowX
            win.y = prefs.windowY
        }

        themeIdx = prefs.themeIdx % themeIds.length
        Theme.loadTheme(themeIds[themeIdx])
        App.themeId = themeIds[themeIdx]
        Sfx.themeId = themeIds[themeIdx]

        shaderIdx = prefs.shaderIdx % shaderProfiles.length
        applyLoopMode(prefs.loopMode % 3)
        console.log("VOLTA prefs restored: theme=" + themeIds[themeIdx]
                    + " shader=" + (shaderProfiles[shaderIdx] || "off")
                    + " loop=" + loopMode + " sort=" + prefs.sortMode)
        focusSlot(0)
        console.log("VOLTA DEBUG win=" + win.width + "x" + win.height
                    + " gridArea=" + gridArea.width + "x" + gridArea.height)

        // 诊断钩子：命令行带 --shot=<路径> 时延迟抓一张整窗自渲染图。
        // 绕开「GL 窗口 PrintWindow 只能抓到黑帧」+「键盘焦点被桌面端抢走 F12 收不到」两个坑。
        // 正常用户不带这个参数，这段静默跳过。
        var shotName = ""
        var wantFullScreen = false
        var forceTheme = ""
        try {
            var args = Qt.application.arguments
            for (var a = 1; a < args.length; ++a) {
                if (args[a].indexOf("--shot=") === 0) shotName = args[a]
                if (args[a] === "--fs") wantFullScreen = true
                if (args[a].indexOf("--theme=") === 0) forceTheme = args[a].substring(8)
            }
        } catch (e) {}
        // 命令行指定主题（验收入口）：覆盖 prefs，强制加载并同步索引
        if (forceTheme !== "") {
            var ti = themeIds.indexOf(forceTheme)
            if (ti >= 0) {
                themeIdx = ti
                Theme.loadTheme(forceTheme)
                App.themeId = forceTheme
                Sfx.themeId = forceTheme
                console.log("VOLTA forced theme -> " + forceTheme)
            }
        }
        if (shotName.indexOf("--shot=") === 0) {
            var shotFile = shotName.substring(7)
            diagTimer.path = shotFile
            if (wantFullScreen) {
                // 先延迟进全屏，再延迟截图，验全屏黑不黑
                fsTimer.path = shotFile
                fsTimer.start()
            } else {
                diagTimer.start()
            }
        }
    }

    Timer {
        id: fsTimer
        interval: 1000
        property string path: ""
        onTriggered: {
            win.toggleFullScreen()
            diagTimer.path = path
            diagTimer.interval = 1600
            diagTimer.start()
        }
    }

    Timer {
        id: diagTimer
        interval: 1800
        property string path: ""
        onTriggered: {
            if (path === "") return
            appRoot.grabToImage(function(result) {
                if (result && result.saveToFile(path))
                    console.log("VOLTA diag shot saved " + path)
                else
                    console.log("VOLTA diag shot FAILED " + path)
            })
            var bgPath = path.replace(/\.png$/i, "-bg.png")
            themeBg.grabToImage(function(result) {
                if (result && result.saveToFile(bgPath))
                    console.log("VOLTA diag bg saved " + bgPath)
                else
                    console.log("VOLTA diag bg FAILED " + bgPath)
            })
        }
    }

    function openDialogNow() {
        if (App.lastDirectory !== "")
            openDialog.currentFolder = "file:///" + App.lastDirectory
        openDialog.open()
    }

    FileDialog {
        id: openDialog
        title: "打开视频"
        fileMode: FileDialog.OpenFile
        nameFilters: [
            "视频文件 (*.mp4 *.mkv *.webm *.avi *.mov *.m4v *.ts *.flv *.wmv *.mpg *.mpeg)",
            "所有文件 (*)"
        ]
        onAccepted: {
            console.log("VOLTA dialog picked " + selectedFile)
            App.openFile(selectedFile)
        }
        onRejected: console.log("VOLTA dialog cancelled")
    }

    DropArea {
        anchors.fill: parent
        onDropped: function(drop) {
            if (!drop.hasUrls) return
            var files = []
            for (var i = 0; i < drop.urls.length; ++i) {
                if (drop.urls[i].toString().indexOf("file:") === 0)
                    files.push(drop.urls[i])
            }
            if (files.length > 0) {
                App.openFiles(files)
                toast(App.tr["toast.added"].replace("%1", files.length))
            }
        }
    }

    // ── 键盘 ────────────────────────────────────────────────
    Shortcut { sequences: [StandardKey.Open, "Ctrl+O", "O"]; onActivated: win.openDialogNow() }
    Shortcut { sequence: "Space"; onActivated: { Sfx.play("toggle"); if (win.focusedSlot) win.focusedSlot.togglePlay() } }
    Shortcut { sequence: "Right"; onActivated: { Sfx.play("tap"); if (win.focusedSlot) win.focusedSlot.seekRelative(5) } }
    Shortcut { sequence: "Shift+Right"; onActivated: if (win.focusedSlot) win.focusedSlot.seekRelative(30) }
    Shortcut { sequence: "Left"; onActivated: { Sfx.play("tap"); if (win.focusedSlot) win.focusedSlot.seekRelative(-5) } }
    Shortcut { sequence: "Shift+Left"; onActivated: if (win.focusedSlot) win.focusedSlot.seekRelative(-30) }
    Shortcut { sequence: "Up"; onActivated: App.volume = Math.min(100, App.volume + 5) }
    Shortcut { sequence: "Down"; onActivated: App.volume = Math.max(0, App.volume - 5) }
    Shortcut { sequence: "M"; onActivated: { Sfx.play("toggle"); App.muted = !App.muted; toast(App.muted ? "静音" : "取消静音") } }
    Shortcut { sequence: "F"; onActivated: win.toggleSolo(win.focusSlotId) }
    Shortcut { sequence: "F11"; onActivated: { Sfx.play("toggle"); win.toggleFullScreen() } }
    Shortcut { sequence: "T"; onActivated: win.cycleTheme() }
    Shortcut { sequence: "S"; onActivated: win.cycleShader() }
    Shortcut { sequence: "A"; onActivated: { App.ambientLight = !App.ambientLight; win.toast(App.ambientLight ? "环境光：开" : "环境光：关") } }
    Shortcut { sequence: "G"; onActivated: { Sfx.play("toggle"); win.cycleGridCount() } }
    Shortcut { sequence: "D"; onActivated: { Sfx.play("toggle"); win.removeLastSlot() } }
    // 循环 / A-B 的键盘口子：按钮在底栏，位置会随文字宽度漂，
    // 键盘是唯一稳定的入口（顺手也给用户用）。
    Shortcut { sequence: "L"; onActivated: { Sfx.play("toggle"); bar.cycleLoop() } }
    Shortcut { sequence: "B"; onActivated: { Sfx.play("toggle"); bar.markAb() } }
    // 调试用：F12 把整个窗口抓成 PNG（Qt 自己的 grabToImage，走 QQuick 渲染路径）。
    // 为什么需要：屏幕截图走 BitBlt/PrintWindow 对 GL 合成窗口只会吐旧帧，
    // 验收要看到「这一帧」只能让程序自己渲染一张。文件落在当前工作目录。
    Shortcut {
        sequence: "F12"
        onActivated: {
            var name = "shot-" + Date.now() + ".png"
            // 注意：contentItem 是 QQuickRootItem，它没有 QML engine，grabToImage 会直接拒绝。
            // 抓 rootCol（本文件里的 ColumnLayout，铺满整窗）才是能用的那个。
            rootCol.grabToImage(function (result) {
                if (result.saveToFile(name))
                    console.log("VOLTA shot saved " + name)
                else
                    console.log("VOLTA shot failed " + name)
            })
        }
    }
    Shortcut {
        sequences: ["Esc", "Backspace"]
        onActivated: {
            console.log("VOLTA esc: fullscreen=" + WindowCtl.fullScreen + " view=" + win.viewMode)
            if (WindowCtl.fullScreen) win.toggleFullScreen()
            else win.exitSolo()
        }
    }
    Shortcut { sequence: "1"; onActivated: { Sfx.play("nav"); win.focusSlot(0) } }
    Shortcut { sequence: "2"; onActivated: { Sfx.play("nav"); win.focusSlot(1) } }
    Shortcut { sequence: "3"; onActivated: { Sfx.play("nav"); win.focusSlot(2) } }
    Shortcut { sequence: "4"; onActivated: { Sfx.play("nav"); win.focusSlot(3) } }

    // 主题背景装饰 + 主内容，包在一个 Item 里：既是真实渲染层级，也能被 grabToImage
    // 一次抓全（backdrop 在底，rootCol 在上），不再出现「抓 rootCol 看不到背景」的自欺。
    Item {
        id: appRoot
        anchors.fill: parent

        // 主题背景装饰：铺满整窗，内容盖在它上面
        ThemeBackdrop {
            id: themeBg
            anchors.fill: parent
            paused: win.windowResizing
        }

        ColumnLayout {
            id: rootCol
            anchors.fill: parent
            spacing: 0

        Shell {
            Layout.fillWidth: true
            visible: !win.isFullScreen
            Layout.preferredHeight: win.isFullScreen ? 0 : 46
            Layout.minimumHeight: win.isFullScreen ? 0 : 46
            Layout.maximumHeight: win.isFullScreen ? 0 : 46
            viewMode: win.viewMode
            viewStackDepth: win.viewStackDepth
            focusSlotId: win.focusSlotId
            nowPlaying: win.toastText
            onDragRequested: {
                var w = win
                if (w) w.startSystemMove()
            }
        }

        RowLayout {
            id: rowArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            PlaylistPanel {
                id: listPanel
                sortMode: prefs.sortMode
                onSortModeChanged: prefs.sortMode = sortMode
                visible: win.viewMode === "grid" && !win.isFullScreen
                Layout.preferredWidth: visible ? 360 : 0
                Layout.minimumWidth: visible ? 360 : 0
                Layout.maximumWidth: visible ? 360 : 0
                Layout.fillHeight: true
                queueModel: win.gridItems
                onOpenRequested: win.openDialogNow()
                onFocusSlotRequested: function(id) { win.focusSlot(id) }
                onPlayIndexRequested: function(i) { App.playIndex(i); win.focusSlot(0) }
                onAddToGridRequested: function(i) { win.addToGrid(i) }
                onOpenLibraryRequested: function(path) {
                    // 之前这里走 App.openLibraryItem(i)，它总是塞进第 1 格 ——
                    // 用户在第二个格子上悬停，点库里的片子，结果换的是第一个格。
                    var idx = App.ensureInPlaylist(path)
                    win.assignToSlot(win.focusSlotId, idx)
                }
            }

            Rectangle {
                id: gridArea
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 0
                Layout.minimumHeight: 0
                // 透明：让主题背景从视频区四周透出（有视频时 MpvItem 盖住）
                color: "transparent"

                GridLayout {
                    id: grid
                    anchors.fill: parent
                    anchors.margins: 6
                    columns: win.gridCount === 1 ? 1 : Math.min(3, Math.ceil(Math.sqrt(win.gridCount)))
                    rows: win.gridCount <= 2 ? 1 : Math.ceil(win.gridCount / columns)
                    rowSpacing: 6
                    columnSpacing: 6

                    Repeater {
                        model: win.gridCount
                        // 新长出来的格子马上跟上当前的循环模式（否则加到第 2 格
                        // 时它还是「关」，跟其它格子不一致）
                        onItemAdded: function(index, item) { item.setLoopMode(win.loopMode) }
                        delegate: VideoSlot {
                            required property int index

                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumWidth: 0
                            Layout.minimumHeight: 0
                            Layout.maximumWidth: Infinity
                            Layout.maximumHeight: Infinity

                            slotId: index
                            Component.onCompleted: win.registerSlot(index, this)
                            visible: win.viewMode === "grid" || win.focusSlotId === index
                            focused: win.focusSlotId === index
                            shaderProfile: win.shaderProfile
                            source: win.sourceForSlot(index)

                            onSlotFocused: win.focusSlot(index)
                            onSlotDoubleClicked: win.toggleSolo(index)
                            onCloseRequested: win.removeSlot(index)
                            onPlaybackEnded: function(id) { win.onSlotEnded(id) }
                            onHint: function(t) { win.toast("SLOT " + (index + 1) + " · " + t) }
                        }
                    }
                }

                // 提示条（主题色）——滑入 + 轻微弹入 + 发光反馈
                Rectangle {
                    id: toastBox
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 12
                    z: 200
                    width: toastLab.implicitWidth + 24
                    height: 28
                    radius: Theme.radiusButton
                    color: Theme.surface
                    border.color: Theme.accent
                    border.width: 1
                    opacity: win.toastText !== "" ? 0.97 : 0
                    visible: opacity > 0.01
                    scale: win.toastText !== "" ? 1 : 0.9
                    transformOrigin: Item.Center
                    transform: Translate {
                        id: toastSlide
                        y: 0
                    }
                    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                    Behavior on scale { NumberAnimation { duration: 220; easing.type: Easing.OutBack } }
                    // 从下方滑入：先设偏移再动画归零（不动 anchors，避免 y 冲突）
                    onVisibleChanged: {
                        if (visible) {
                            toastSlide.y = 22
                            toastBack.start()
                        }
                    }
                    NumberAnimation { id: toastBack; target: toastSlide; property: "y"; to: 0; duration: 240; easing.type: Easing.OutCubic }
                    // 发光层（Theme.glow 才开）
                    Rectangle {
                        anchors.fill: parent
                        radius: parent.radius
                        color: "transparent"
                        border.color: Theme.accent
                        border.width: 3
                        opacity: Theme.glow ? 0.18 : 0
                        visible: Theme.glow
                    }

                    Text {
                        id: toastLab
                        anchors.centerIn: parent
                        text: win.toastText
                        color: Theme.ink
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSize
                    }
                }
            }
        }

        TransportBar {
            id: bar
            Layout.fillWidth: true
            visible: !win.isFullScreen
            Layout.preferredHeight: win.isFullScreen ? 0 : 52
            Layout.minimumHeight: win.isFullScreen ? 0 : 52
            Layout.maximumHeight: win.isFullScreen ? 0 : 52
            player: win.focusedSlot
            viewMode: win.viewMode
            themeLabel: win.themeLabel
            shaderLabel: win.shaderLabel
            gridCount: win.gridCount
            loopMode: win.loopMode
            onLoopModeRequested: function(m) { win.applyLoopMode(m) }
            onGridCountRequested: win.cycleGridCount()
            onViewToggleRequested: win.toggleSolo(win.focusSlotId)
            onFullscreenRequested: win.toggleFullScreen()
            onThemeRequested: win.cycleTheme()
            onShaderRequested: win.cycleShader()
            onHintRequested: function(t) { win.toast(t) }
            onPlayerChanged: bar.syncFromPlayer()
            Connections {
                target: win.focusedSlot
                function onPlaybackStateChanged() { bar.syncFromPlayer() }
            }
        }
    }
    }  // appRoot

    // ── 主题切换转场：发光扫描线从上扫到下 ─────────────────
    // 只在 cycleTheme 发信号时跑一遍，不常驻、不闪整屏。
    Rectangle {
        id: themeWipe
        anchors.fill: parent
        z: 1000
        visible: false
        color: "transparent"
        Rectangle {
            id: wipeLine
            anchors.left: parent.left; anchors.right: parent.right
            anchors.top: parent.top
            height: 4
            y: 0
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.5; color: Theme.accent }
                GradientStop { position: 1.0; color: "transparent" }
            }
            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 2
                height: 2
                color: Theme.accent
                opacity: 0.25
            }
        }
        SequentialAnimation {
            id: wipeAnim
            onStarted: { themeWipe.visible = true; console.log("VOLTA wipe start") }
            onStopped: { themeWipe.visible = false; console.log("VOLTA wipe done") }
            // 整屏主题色幕布：高度从上压下再淡出（比一条 4px 线明显得多）
            ParallelAnimation {
                NumberAnimation { target: wipeCurtain; property: "height"; from: 0; to: win.height; duration: 320; easing.type: Easing.OutCubic }
                NumberAnimation { target: wipeCurtain; property: "opacity"; from: 0.45; to: 0.0; duration: 640; easing.type: Easing.OutQuad }
            }
            NumberAnimation { target: wipeLine; property: "y"; from: -8; to: win.height; duration: 520; easing.type: Easing.InOutQuad }
        }
        // 半透明主题色幕布（顶对齐，高度动画从上压下）
        Rectangle {
            id: wipeCurtain
            anchors.left: parent.left; anchors.right: parent.right
            anchors.top: parent.top
            height: 0
            color: Theme.accent
            opacity: 0
        }
        Connections {
            target: win
            function onThemeSwitchFlash() { console.log("VOLTA theme flash signal"); wipeAnim.restart() }
        }
    }
}
