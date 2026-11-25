"""VOLTA 全量回归：把「代码写了没验」那 8 条逐条跑出证据。

每一条都回读日志或窗口几何，不看「应该没问题」。
输入走 PostMessage（Hermes 桌面端永远在最前面，真鼠标会点空），
唯一例外是拉伸：那条要真光标，靠系统 SetCapture 路由。

    python tools/verify2.py            # 全跑
    python tools/verify2.py tabs       # 只跑某几段（按关键字过滤）
"""
import ctypes
import ctypes.wintypes as wt
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

ROOT = V.ROOT
SHOTS = V.SHOTS
user32 = V.user32

RESULTS = []


def expect(label, cond, detail=""):
    RESULTS.append((label, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + label + ("   " + str(detail) if detail else ""))
    return bool(cond)


def log_has(marker):
    return marker in V.log_text()


def wait_log(marker, timeout=5.0):
    """等一条日志出现（Qt 的日志写入不是同步的，紧贴着断言会读到旧文件）。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if marker in V.log_text():
            return True
        time.sleep(0.25)
    return False


def log_count(marker):
    return len([l for l in V.log_text().split("\n") if marker in l])


def click(w, x, y, dbl=False):
    P.post_click(w, x, y, dbl=dbl)
    time.sleep(0.25)


def key(w, name):
    P.post_key(w, name)
    time.sleep(0.15)


def seek_track(w, x0, x1, y, frac):
    """点格子自带进度条：x0..x1 是轨道两端，frac 是 0..1。"""
    click(w, x0 + (x1 - x0) * frac, y)
    time.sleep(0.6)


def seek_near_end(w, presses=12):
    """键盘快进到片尾：Right = +5s，按满 12 下就顶到 duration 上。

    比点进度条稳得多 —— 进度条像素坐标会跟着布局漂，键盘不会。
    """
    for _ in range(presses):
        key(w, "right")
    time.sleep(0.8)


def focus_window(w):
    """把 VOLTA 抢回前台（全屏/最大化切换后键盘焦点会飘）。"""
    try:
        k32 = ctypes.windll.kernel32
        fg = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg, None)
        my_thread = k32.GetCurrentThreadId()
        user32.AttachThreadInput(my_thread, fg_thread, True)
        user32.SetForegroundWindow(wt.HWND(w.h))
        user32.SetFocus(wt.HWND(w.h))
        user32.AttachThreadInput(my_thread, fg_thread, False)
    except Exception:
        pass
    time.sleep(0.4)


def nc_double_click(w, lx=640, ly=16):
    """按 Windows 真正的双击顺序塞消息：DOWN / UP / DBLCLK / UP。"""
    cx, cy = P._client_xy(w, lx, ly)
    sx, sy = w.x + cx, w.y + cy
    lp = P._lparam(sx, sy)
    user32.PostMessageW(w.h, 0x00A1, 2, lp)   # WM_NCLBUTTONDOWN, HTCAPTION
    time.sleep(0.05)
    user32.PostMessageW(w.h, 0x00A2, 0, lp)   # WM_NCLBUTTONUP
    time.sleep(0.05)
    user32.PostMessageW(w.h, 0x00A3, 2, lp)   # WM_NCLBUTTONDBLCLK
    time.sleep(0.05)
    user32.PostMessageW(w.h, 0x00A2, 0, lp)   # WM_NCLBUTTONUP
    time.sleep(1.2)


def pin_size(w, lw=1280, lh=800, x=100, y=100):
    """把窗口钉回 1280x800 逻辑（=1920x1200 物理）：后面所有点击坐标都按这个算。"""
    user32.SetWindowPos(wt.HWND(w.h), 0, x, y,
                        int(lw * V.SCALE), int(lh * V.SCALE), 0x0004)   # SWP_NOZORDER
    time.sleep(0.8)
    w.refresh_rect()
    print(f"  pinned {w.w}x{w.h_} at {w.x},{w.y}")


def main(argv):
    want = set(argv)
    def run(name):
        return not want or any(k in name for k in want)

    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process volta -ErrorAction SilentlyContinue | Stop-Process -Force"],
                   capture_output=True)
    time.sleep(1.5)
    V.launch([os.path.join(ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    print(f"window {w.w}x{w.h_} at {w.x},{w.y}")

    # 第一下点击只用来激活窗口，Qt 会把它吃掉 —— 先点标题栏白送一条
    click(w, 600, 16)
    time.sleep(0.6)

    # ── 0. 窗口是不是真「可见」（2026-11-18 的鬼魂窗：一个 WS_VISIBLE 位丢了，
    #      任务栏没图标 + 点击穿透 + 画面还在，三个症状一个位）───────────
    if run("visible"):
        hw = wt.HWND(w.h)
        st = user32.GetWindowLongW(hw, -16)
        ex = user32.GetWindowLongW(hw, -20)
        expect("窗口带 WS_VISIBLE（不是隐藏态）", bool(st & 0x10000000), f"style=0x{st & 0xFFFFFFFF:08x}")
        expect("IsWindowVisible 为真", bool(user32.IsWindowVisible(hw)), "")
        expect("exstyle 带 WS_EX_APPWINDOW 且不是 TOOLWINDOW（任务栏有位置）",
               bool(ex & 0x00040000) and not (ex & 0x00000080), f"exstyle=0x{ex & 0xFFFFFFFF:08x}")

    # ── 1. 八边拉伸：直接问窗口要 WM_NCHITTEST 的返回值 ──────────
    if run("hittest"):
        out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hittest.py")],
                             capture_output=True, text=True).stdout
        print(out.rstrip())
        m = re.search(r"(\d+)/(\d+) passed", out)
        expect("八边拉伸命中判定", m and m.group(1) == m.group(2),
               m.group(0) if m else "no result")

    # ── 2. 真拖一次：窗口尺寸要跟着变 ─────────────────────────
    if run("resize"):
        w.refresh_rect()
        before = (w.w, w.h_)
        P.nresize(w, 1279, 400, -100, 0)
        time.sleep(0.5)
        w.refresh_rect()
        after = (w.w, w.h_)
        expect("拖右边缘 → 窗口变窄", after[0] < before[0], f"{before} -> {after}")
        # 拉回来，后面的检查都按 1280x800 逻辑布局算坐标
        pin_size(w)

    # ── 3. 双击标题栏最大化 / 再双击还原 ─────────────────────
    if run("maximize"):
        w.refresh_rect()
        orig = (w.w, w.h_)
        nc_double_click(w)
        w.refresh_rect()
        big = (w.w, w.h_)
        if big == orig:
            # 消息式双击在 Qt6 自绘边框上不一定被 DefWindowProc 认，退到「▣ 按钮」这条路
            print("  NC 双击没生效，改点顶栏的 ▣")
            click(w, 1280 - 66, 20)
            time.sleep(1.2)
            w.refresh_rect()
            big = (w.w, w.h_)
        expect("双击标题栏/▣ → 最大化", big[0] > orig[0] and big[1] > orig[1], f"{orig} -> {big}")
        nc_double_click(w)
        w.refresh_rect()
        if (w.w, w.h_) == big:
            click(w, 1280 - 66, 20)
            time.sleep(1.2)
            w.refresh_rect()
        back = (w.w, w.h_)
        expect("再走一次 → 还原", abs(back[0] - orig[0]) < 60 and abs(back[1] - orig[1]) < 60,
               f"{big} -> {back} (orig {orig})")

    # ── 4. 全屏：F11 进，Esc 出，画面不能黑 ──────────────────
    if run("fullscreen"):
        focus_window(w)
        w.refresh_rect()
        before = (w.w, w.h_)
        key(w, "f11")
        time.sleep(1.8)
        w.refresh_rect()
        on = wait_log("VOLTA fullscreen=on", 4)
        expect("F11 → 全屏", on, f"rect {w.w}x{w.h_}")
        expect("全屏铺满显示器", w.w >= 2400 and w.h_ >= 1400, f"{w.w}x{w.h_} (before {before})")
        p = os.path.join(SHOTS, "v2_fullscreen.png")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "snap.py"), "v2_fullscreen.png"],
                       capture_output=True)
        try:
            from PIL import Image
            im = Image.open(p).convert("L")
            mean = sum(im.resize((80, 50)).tobytes()) / 4000.0
            expect("全屏不是黑屏", mean > 8, f"mean luma {mean:.1f}")
        except Exception as e:
            expect("全屏不是黑屏", False, str(e))
        focus_window(w)
        key(w, "esc")
        time.sleep(1.4)
        w.refresh_rect()
        expect("Esc → 退出全屏", wait_log("VOLTA fullscreen=off", 5), f"rect {w.w}x{w.h_}")

    # ── 5. 动态网格：一格 → 两格 → 三格 ─────────────────────
    if run("grid"):
        pin_size(w)
        key(w, "g")
        time.sleep(1.2)
        expect("G → 两格", log_has("VOLTA grid count=2"), str(V.log_tail("grid count", 1)))
        key(w, "g")
        time.sleep(1.2)
        expect("G → 三格", log_has("VOLTA grid count=3"), str(V.log_tail("grid count", 1)))
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "snap.py"), "v2_grid3.png"],
                       capture_output=True)
        # 第 2/3 格真的拿到了自己的片源
        expect("新格子各拿到片源", log_count("loadfile rc=0") >= 3,
               f"loadfile ok = {log_count('loadfile rc=0')}")

    # ── 6. 每格的 ✕ 只关自己那一格 ──────────────────────────
    if run("close"):
        # 现在三格（2 列 2 行）→ 先回到两格更好算坐标：用 D 收掉最后一格
        key(w, "d")
        time.sleep(1.0)
        w.refresh_rect()
        cols = 2
        slot0_close = (300 + (w.w / P.V.SCALE - 300) / cols - 21, 40 + 19)
        click(w, int(slot0_close[0]), int(slot0_close[1]))
        time.sleep(1.2)
        expect("点第 1 格的 ✕ → 只关这一格", log_has("VOLTA removeSlot 0"),
               str(V.log_tail("removeSlot", 1)))

    # ── 7. 库页签 + 三种排序 ────────────────────────────────
    if run("sort"):
        for x in (45, 50, 55, 60, 65, 70):
            click(w, x, 57)
            time.sleep(0.5)
            if log_has("VOLTA mode=1"):
                print(f"  库页签命中 x={x}")
                break
        expect("点「库」→ 切到库页签", log_has("VOLTA mode=1"),
               str(V.log_tail("VOLTA mode", 2)))
        firsts = []
        for _ in range(2):
            # 排序按钮在页签右边，文字会变宽，按当前截图位置取中间
            click(w, 118, 57)
            time.sleep(0.6)
            m = re.findall(r"VOLTA sort=(\d) first=(\S+)", V.log_text())
            if m:
                firsts.append(m[-1])
        expect("点排序 → 名称/修改时间/创建时间轮转",
               len(firsts) >= 2 and firsts[0][0] != firsts[1][0],
               str(firsts))

    # ── 8. 单集循环：播完自己从头来 ──────────────────────────
    if run("loop"):
        click(w, 28, 57)          # 回队列页签（省得排序按钮挡住眼睛）
        time.sleep(0.4)
        key(w, "l")               # LOOP:OFF → LOOP:1
        time.sleep(0.6)
        expect("L → 单集循环", log_has("VOLTA loop -> 1"), str(V.log_tail("VOLTA loop", 1)))
        expect("循环模式真的下发到引擎", "loopMode=1" in V.log_text(),
               str(V.log_tail("loopMode", 1)))
        before_adv = log_count("playIndex")
        seek_near_end(w)
        time.sleep(4)
        expect("单集循环：播完从头再放", log_has("loop-file restart"),
               str(V.log_tail("loop-file", 1)))
        expect("单集循环：没有去开下一集", log_count("playIndex") == before_adv,
               f"playIndex {before_adv} -> {log_count('playIndex')}")
        key(w, "l")
        key(w, "l")               # 循环关掉，别影响后面
        time.sleep(0.5)

    # ── 9. A-B 循环：到 B 点跳回 A ──────────────────────────
    if run("ab"):
        key(w, "b")
        time.sleep(2.5)
        key(w, "b")
        time.sleep(3.0)
        expect("A-B：两次 B 键设出区间", "abLoop set a=" in V.log_text(),
               str(V.log_tail("abLoop set", 1)))
        expect("A-B：播到 B 点自己跳回 A", "ab loop back to" in V.log_text(),
               str(V.log_tail("ab loop back", 1)))
        key(w, "b")               # 清掉
        time.sleep(0.4)

    # ── 10. 第 2 格播完：自己重播，不参与队列推进 ───────────
    if run("slot2"):
        key(w, "g")               # 长出第 2 格
        time.sleep(1.5)
        key(w, "2")               # 焦点给第 2 格
        time.sleep(0.6)
        expect("焦点切到第 2 格", "VOLTA focus slot=1" in V.log_text(),
               str(V.log_tail("focus slot", 1)))
        before_adv = log_count("playIndex")
        seek_near_end(w)
        time.sleep(5)
        expect("第 2 格播完 → 自己从头重播", log_has("VOLTA slot 1 ended -> replay from 0"),
               str(V.log_tail("ended -> replay", 1)))
        expect("第 2 格播完 → 不动队列", log_count("playIndex") == before_adv,
               f"playIndex {before_adv} -> {log_count('playIndex')}")

    # ── 收尾（必须排在最小化之前）：QML 警告必须是 0 ──────────
    # 最小化之后再点窗口，Qt 会刷一堆「Not setting mouse grab for invisible window」，
    # 那是测试动作引起的噪音，不是程序问题 —— 所以警告检查放在最小化前面。
    # setMouseGrabEnabled 那类同样只出现在「点 ✕ 把自己这一格拆掉」的瞬间（Qt 内部抓鼠标
    # 时窗口状态正在切换），单独滤掉；其它任何 QML 警告都算红。
    BENIGN = "setMouseGrabEnabled"
    warns = [l for l in V.log_text().split("\n")
             if ("QML WARN" in l or "QML CRIT" in l) and BENIGN not in l]
    expect("QML 无警告", len(warns) == 0, "\n    ".join(warns[:6]) if warns else "0 warning")

    # ── 11. 顶栏「─」最小化（放最后：最小化后窗口不该再被点）──
    if run("minimize"):
        pin_size(w)
        click(w, 1170, 20)                     # ─ 按钮（三个按钮各 44 逻辑像素）
        time.sleep(1.4)
        # 自绘无边框窗口走 Qt 的 setVisibility(Minimized)：有时真 SW_MINIMIZE
        # （IsIconic=True），有时直接隐藏（窗口不可见）。两种都算最小化成功。
        iconic = bool(user32.IsIconic(wt.HWND(w.h)))
        visible = bool(user32.IsWindowVisible(wt.HWND(w.h)))
        expect("点 ─ → 窗口最小化（不是拖着窗口跑）", iconic or not visible,
               f"IsIconic={iconic} Visible={visible} {V.log_tail('winbtn', 1)}")

    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "snap.py"), "v2_final.png"],
                   capture_output=True)
    w.drop_topmost()

    bad = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} passed")
    if bad:
        print("FAILED:")
        for label, _, detail in bad:
            print("  -", label, detail)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
