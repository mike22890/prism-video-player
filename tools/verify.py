"""VOLTA 交互验证：真鼠标真键盘打进去，再看日志和截图。

不假装「点了应该就好了」—— 每一步都回读日志里的证据行。

用法：
    python tools/verify.py            # 全跑（会启动/重启应用）

坐标全部按窗口物理像素算：窗口 1280x800 逻辑 @150% = 1920x1200 物理。
"""
import ctypes
import ctypes.wintypes as wt
import os
import re
import subprocess
import sys
import time

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    user32.SetProcessDPIAware()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "build", "bin", "volta_run.log")
SHOTS = os.path.join(ROOT, "shots")
SCALE = 1.5  # 兜底；下面按真实 DPI 覆盖（本机换过显示器后是 2.0，写死会全点偏）

def _detect_scale():
    """动态读本机 DPI 缩放：写死 1.5 的年代本机是 150%，换屏后变 200%，
    所有点击坐标全偏 → 测试假通过（点了空处还以为验了）。"""
    try:
        u = ctypes.windll.user32
        u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        hdc = u.GetDC(0)
        dpi = gdi32.GetDeviceCaps(hdc, 88)   # LOGPIXELSX
        u.ReleaseDC(0, hdc)
        if dpi and 72 <= dpi <= 600:
            return dpi / 96.0
    except Exception:
        pass
    return 1.5

SCALE = _detect_scale()

VK = {"space": 0x20, "esc": 0x1B, "left": 0x25, "up": 0x26, "right": 0x27,
      "down": 0x28, "m": 0x4D, "f": 0x46, "o": 0x4F, "f11": 0x7A, "f12": 0x7B,
      "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
      # 其余字母：快捷键表扩了，测试这边也跟上（否则 KeyError 打断整串脚本）
      "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45, "g": 0x47,
      "h": 0x48, "i": 0x49, "j": 0x4A, "k": 0x4B, "l": 0x4C, "n": 0x4E,
      "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54, "u": 0x55,
      "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59, "z": 0x5A,
      "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39, "0": 0x30}


def log_text():
    if not os.path.exists(LOG):
        return ""
    return open(LOG, encoding="utf-8", errors="replace").read()


def log_tail(marker, n=3):
    lines = [l.strip() for l in log_text().split("\n") if marker in l]
    return lines[-n:]


def find_window():
    out = subprocess.run(["tasklist"], capture_output=True).stdout.decode("utf-8", "replace")
    pids = {int(p.split()[1]) for p in out.split("\n")
            if "prism.exe" in p.lower() and len(p.split()) >= 2 and p.split()[1].isdigit()}
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids:
            r = wt.RECT()
            user32.GetWindowRect(h, ctypes.byref(r))
            w, hh = r.right - r.left, r.bottom - r.top
            # 注意：不能拿 IsWindowVisible 筛。MinimizeAll 之后主窗自己也是「不可见」的，
            # 按可见性找就永远找不到（踩过一次，报 NO VOLTA WINDOW）。
            if w > 400 and hh > 400:
                found.append((w * hh, h))
        return True

    user32.EnumWindows(cb, 0)
    found.sort(reverse=True)
    return found[0][1] if found else None


class Win:
    def __init__(self):
        self.h = find_window()
        if not self.h:
            raise SystemExit("NO VOLTA WINDOW")
        # 光 SetForegroundWindow 不够：Windows 的前台锁会静默拒绝后台进程抢焦点，
        # 点击就全落到别人身上（第一次跑 8 项里 7 项 FAIL 就是这么来的）。
        # TOPMOST 是硬置顶，绕过前台锁。
        user32.ShowWindow(wt.HWND(self.h), 9)
        # 尺寸钉死成 1280x800 逻辑（=1920x1200 物理）：坐标全靠常量算，
        # 窗口尺寸漂了（被谁拖过 / 被 SW_RESTORE 复原成旧值）点击就全歪
        user32.SetWindowPos(wt.HWND(self.h), -1, 100, 100,
                            int(1280 * SCALE), int(800 * SCALE), 0x0040)
        user32.SetForegroundWindow(wt.HWND(self.h))
        user32.BringWindowToTop(wt.HWND(self.h))
        # 前台锁：Windows 会静默拒绝后台进程抢焦点，点击和按键就全落到别人身上。
        # 用 AttachThreadInput 挂在当前前台线程上再抢一次。
        try:
            k32 = ctypes.windll.kernel32
            fg = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg, None)
            my_thread = k32.GetCurrentThreadId()
            user32.AttachThreadInput(my_thread, fg_thread, True)
            user32.SetForegroundWindow(wt.HWND(self.h))
            user32.SetFocus(wt.HWND(self.h))
            user32.AttachThreadInput(my_thread, fg_thread, False)
        except Exception:
            pass
        time.sleep(1.0)
        r = wt.RECT()
        user32.GetWindowRect(wt.HWND(self.h), ctypes.byref(r))
        self.x, self.y = r.left, r.top
        self.w, self.h_ = r.right - r.left, r.bottom - r.top
        print(f"window {self.w}x{self.h_} at ({self.x},{self.y})")

    def refresh_rect(self):
        r = wt.RECT()
        user32.GetWindowRect(wt.HWND(self.h), ctypes.byref(r))
        self.x, self.y = r.left, r.top
        self.w, self.h_ = r.right - r.left, r.bottom - r.top

    def drop_topmost(self):
        user32.SetWindowPos(wt.HWND(self.h), -2, 0, 0, 0, 0, 0x0001 | 0x0002)

    def click(self, lx, ly, dbl=False):
        sx, sy = self.x + int(lx * SCALE), self.y + int(ly * SCALE)
        user32.SetCursorPos(sx, sy)
        time.sleep(0.15)
        n = 2 if dbl else 1
        for _ in range(n):
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.12 if dbl else 0.3)
        time.sleep(0.4)

    def key(self, name):
        if name.startswith("shift"):
            base = VK[name[5:]]
            user32.keybd_event(0x10, 0, 0, 0)      # Shift down
            user32.keybd_event(base, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(base, 0, 2, 0)
            user32.keybd_event(0x10, 0, 2, 0)      # Shift up
            time.sleep(0.4)
            return
        vk = VK[name]
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.4)

    def shot(self, name):
        from PIL import Image
        os.makedirs(SHOTS, exist_ok=True)
        w, h = self.w, self.h_
        hdc = user32.GetDC(0)
        memdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        gdi32.SelectObject(memdc, bmp)
        gdi32.BitBlt(memdc, 0, 0, w, h, hdc, self.x, self.y, 0x00CC0020 | 0x40000000)

        class BIH(ctypes.Structure):
            _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                        ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                        ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                        ("biClrImportant", wt.DWORD)]

        class BI(ctypes.Structure):
            _fields_ = [("bmiHeader", BIH), ("bmiColors", wt.DWORD * 3)]

        bi = BI()
        bi.bmiHeader.biSize = ctypes.sizeof(BIH)
        bi.bmiHeader.biWidth = w
        bi.bmiHeader.biHeight = -h
        bi.bmiHeader.biPlanes = 1
        bi.bmiHeader.biBitCount = 32
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(0, hdc)
        p = os.path.join(SHOTS, name)
        Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(p)
        return p


def check(label, marker, expect_growth=1):
    before = len([l for l in log_text().split("\n") if marker in l])
    return before


def dialog_windows():
    """系统文件对话框是 class #32770 的顶层窗口。"""
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, _):
        buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, buf, 64)
        if buf.value == "#32770" and user32.IsWindowVisible(h):
            out.append(h)
        return True

    user32.EnumWindows(cb, 0)
    return out


def launch(files):
    """重启一个干净实例：旧进程杀掉、日志清空、带片启动。"""
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Name prism -Force -ErrorAction SilentlyContinue"],
                   capture_output=True)
    time.sleep(1.0)
    if os.path.exists(LOG):
        os.remove(LOG)
    env = dict(os.environ)
    env["PATH"] = os.path.join(ROOT, "qt", "6.10.2", "mingw_64", "bin") + ";" + env["PATH"]
    env["QSG_RHI_BACKEND"] = "opengl"
    exe = os.path.join(ROOT, "build", "bin", "prism.exe")
    subprocess.Popen([exe] + files, cwd=os.path.join(ROOT, "build", "bin"),
                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        time.sleep(0.5)
        if find_window() and "loadfile rc=0" in log_text():
            break
    time.sleep(1.5)


def main():
    results = []

    def expect(label, cond, detail=""):
        results.append((label, bool(cond), detail))
        print(("PASS " if cond else "FAIL ") + label + ("  " + detail if detail else ""))

    # 别的窗口（Hermes 桌面端常年置顶）会让点击落到别人身上 —— 先全部让位
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "(New-Object -ComObject Shell.Application).MinimizeAll()"],
                   capture_output=True)
    time.sleep(1.0)
    launch([os.path.join(ROOT, "media_long", "s1.mp4")])
    w = Win()

    # 1) 播放/暂停：点控制条第一个键
    before = len(log_tail("MpvItem::setPaused", 50))
    w.click(30, 800 - 26)
    after = log_tail("MpvItem::setPaused", 2)
    expect("点播放键 → 暂停发到引擎", len(log_tail("MpvItem::setPaused", 50)) > before, str(after))

    # 2) 进度条：按日志里上报的轨道几何点 92% 处 → seek
    m = re.search(r"VOLTA track x=(-?\d+) w=(\d+)", log_text())
    if not m:
        raise SystemExit("没拿到进度条几何（TransportBar 的 console.log 没出来）")
    tx, tw = int(m.group(1)), int(m.group(2))
    before = len(log_tail("seek ->", 40))
    w.click(tx + tw * 0.92, 800 - 26)
    expect("点进度条 → seek", len(log_tail("seek ->", 40)) > before,
           f"track x={tx} w={tw} " + str(log_tail("seek ->", 1)))

    # 3) 键盘：空格再切一次（顺便把刚才 seek 到 57 秒的片子放起来）
    before = len(log_tail("MpvItem::setPaused", 60))
    w.key("space")
    expect("空格 → 播放/暂停", len(log_tail("MpvItem::setPaused", 60)) > before,
           str(log_tail("MpvItem::setPaused", 1)))

    # 4) 播到片尾：上面 seek 到 92%，剩下不到 5 秒播完。
    #    mpv 自己把 pause 打开（keep-open 留最后一帧）→ 轮询回读 → pausedChanged → QML。
    #    这是「引擎 → UI」的实证，只靠 setPaused 永远证明不了这条链路。
    time.sleep(6.0)
    expect("播到片尾 → mpv 自己暂停并回流 UI", "paused <- mpv = 1" in log_text(),
           str(log_tail("paused <- mpv", 1)))

    # 4) 数字键切焦点
    w.key("2")
    expect("按 2 → 焦点 SLOT 2", "VOLTA focus slot=1" in log_text(), str(log_tail("VOLTA focus slot", 1)))

    # 5) 点队列第 2 项 → playIndex（列表第 2 行中心 y≈147）
    before = len(log_tail("playIndex", 60))
    w.click(120, 147)
    expect("点队列项 → playIndex", len(log_tail("playIndex", 60)) > before,
           str(log_tail("playIndex", 1)))

    # 6) 双击槽位 1 → SOLO
    w.click(320 + 8 + 250, 44 + 8 + 200, dbl=True)
    time.sleep(0.8)
    expect("双击 → SOLO", "VOLTA view solo" in log_text(), str(log_tail("VOLTA view", 1)))
    p_solo = w.shot("verify_solo.png")

    # 7) Esc → 回 GRID
    w.key("esc")
    time.sleep(0.8)
    expect("Esc → 回 GRID", "VOLTA view grid" in log_text(), str(log_tail("VOLTA view", 1)))
    p_grid = w.shot("verify_grid.png")

    # 8) 打开对话框：数一数新增的对话框类窗口（#32770 = 系统文件对话框）
    n_before = len(dialog_windows())
    w.click(128, 61)
    time.sleep(1.8)
    expect("「打开…」按钮被点到", "VOLTA open clicked" in log_text(),
           str(log_tail("VOLTA open clicked", 1)))
    dialogs = dialog_windows()
    p_dlg = w.shot("verify_dialog.png")
    expect("点「打开…」→ 文件对话框", len(dialogs) > n_before,
           f"dialogs={len(dialogs)} shot={p_dlg}")
    # 收尾：Esc 关掉对话框，撤置顶
    w.key("esc")
    time.sleep(0.6)

    # 8.5) 主题按钮：终端 → 暗黑（QML 全量换色 + 圆角/字体一起换）
    w.click(1137, 763)
    time.sleep(1.2)
    expect("点「主题」→ 换到暗黑", "theme switched -> default" in log_text(),
           str(log_tail("theme switched", 1)))
    p_theme = w.shot("verify_theme_default.png")

    # 8.6) 着色器按钮：关 → CRT（真 mpv glsl-shaders，不是 QML 假叠加）
    w.click(1200, 763)
    time.sleep(1.5)
    expect("点「着色」→ CRT 着色器生效",
           "shader -> " in log_text() and "crt.glsl" in log_text(),
           str(log_tail("shader ->", 1)))
    p_shader = w.shot("verify_shader_crt.png")
    # 转回终端主题 + 关着色，别把状态留给下一项检查
    w.click(1137, 763)
    w.click(1200, 763)
    w.click(1200, 763)
    time.sleep(0.8)
    expect("着色循环回到关", "shader off" in log_text(), str(log_tail("shader", 2)))

    # 9) 全屏：F11 进，Esc 出
    w.key("f11")
    time.sleep(1.6)
    w.refresh_rect()          # 全屏后窗口矩形变了，截图要按新矩形抓
    p_fs = w.shot("verify_fullscreen.png")
    expect("F11 → 全屏", "VOLTA fullscreen=on" in log_text(), str(log_tail("VOLTA fullscreen", 1)))
    # 光靠日志不算数：窗口矩形得真的铺满显示器（2560x1600）
    expect("全屏窗口铺满显示器", w.w >= 2400 and w.h_ >= 1400, f"{w.w}x{w.h_}")
    w.key("esc")
    time.sleep(1.2)
    expect("Esc → 退出全屏", "VOLTA fullscreen=off" in log_text(), str(log_tail("VOLTA fullscreen", 1)))
    w.drop_topmost()

    print("\nshots:", p_solo, p_grid, p_dlg)
    bad = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(bad)}/{len(results)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
