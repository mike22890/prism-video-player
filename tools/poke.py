"""一步一条地戳 VOLTA：起一个干净实例，然后按命令行给的指令逐条执行。

    python tools/poke.py shot a.png
    python tools/poke.py click 500 400 key space shot b.png sleep 2 shot c.png
    python tools/poke.py -f media_long/s2.mp4 click ...

坐标是**逻辑像素**（窗口左上角为 0,0，1280x800 逻辑 = 1920x1200 物理，脚本自己乘 1.5）。
每条指令跑完都往 stdout 打一行，方便回头对日志。
"""
import os
import sys
import time
import ctypes
import ctypes.wintypes as wt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

ROOT = V.ROOT
user32 = V.user32


def _client_xy(w, lx, ly):
    """逻辑像素 → 客户区物理像素。窗口无边框，客户区原点≈窗口左上角。"""
    return int(lx * V.SCALE), int(ly * V.SCALE)


def _lparam(x, y):
    return (y << 16) | (x & 0xFFFF)


def post_click(w, lx, ly, dbl=False):
    cx, cy = _client_xy(w, lx, ly)
    lp = _lparam(cx, cy)
    hwnd = w.h
    user32.PostMessageW(hwnd, 0x0200, 0, lp)            # WM_MOUSEMOVE
    time.sleep(0.05)
    rounds = 2 if dbl else 1
    for _ in range(rounds):
        user32.PostMessageW(hwnd, 0x0201, 1, lp)        # WM_LBUTTONDOWN (MK_LBUTTON)
        time.sleep(0.04)
        user32.PostMessageW(hwnd, 0x0202, 0, lp)        # WM_LBUTTONUP
        time.sleep(0.10 if dbl else 0.25)


def post_key(w, name):
    vk = V.VK[name]
    user32.PostMessageW(w.h, 0x0100, vk, 0)             # WM_KEYDOWN
    time.sleep(0.05)
    user32.PostMessageW(w.h, 0x0101, vk, 0xC0000001)    # WM_KEYUP
    time.sleep(0.35)


def nresize(w, lx, ly, dx, dy):
    """真·走系统拉伸流程：WM_NCLBUTTONDOWN + HTRIGHT，再移动真光标，最后抬键。

    真鼠标拖不了 —— Hermes 桌面端永远在最前面，按下去落在它身上。
    但窗口消息不看 z 序：先塞一条非客户区按下让系统进拉伸循环（它会 SetCapture），
    之后真光标一动，输入就都路由给 VOLTA 了，Windows 自己算尺寸。
    """
    cx, cy = _client_xy(w, lx, ly)
    sx, sy = w.x + cx, w.y + cy
    user32.SetCursorPos(sx, sy)
    time.sleep(0.2)
    user32.PostMessageW(w.h, 0x00A1, 11, _lparam(sx, sy))   # WM_NCLBUTTONDOWN, HTRIGHT
    time.sleep(0.4)
    steps = 8
    ddx = int(dx * V.SCALE / steps)
    ddy = int(dy * V.SCALE / steps)
    for _ in range(steps):
        user32.mouse_event(0x0001, ddx, ddy, 0, 0)          # MOUSEEVENTF_MOVE（相对）
        time.sleep(0.09)
    time.sleep(0.2)
    user32.mouse_event(0x0004, 0, 0, 0, 0)                  # LEFTUP
    time.sleep(0.7)
    w.refresh_rect()
    print(f"nresize by {dx},{dy} -> {w.w}x{w.h_}")


def pshot(name):
    """PrintWindow 抓窗口自己（不被别的窗口遮挡）。"""
    import snap
    snap.main(name)


def active_state(w):
    fg = user32.GetForegroundWindow()
    return fg, (fg == w.h)


def capdbl(w, lx=640, ly=16):
    """双击标题栏（走 WM_NCLBUTTONDBLCLK，跟人手双击同一条路）。"""
    cx, cy = _client_xy(w, lx, ly)
    sx, sy = w.x + cx, w.y + cy
    user32.PostMessageW(w.h, 0x00A3, 2, _lparam(sx, sy))     # WM_NCLBUTTONDBLCLK, HTCAPTION
    time.sleep(1.2)
    w.refresh_rect()
    print(f"capdbl -> {w.w}x{w.h_} at {w.x},{w.y}")


def moninfo():
    """屏幕 / 工作区尺寸，用来判断「最大化铺到哪」「全屏铺到哪」。"""
    u = user32
    try:
        u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        u.SetProcessDPIAware()
    m = wt.RECT()
    u.SystemParametersInfoW(0x0030, 0, ctypes.byref(m), 0)   # SPI_GETWORKAREA
    print(f"workarea {m.right - m.left}x{m.bottom - m.top} at {m.left},{m.top}")
    return (m.right - m.left, m.bottom - m.top)


def main(argv):
    args = list(argv)
    files = [os.path.join(ROOT, "media_long", "s1.mp4")]
    if args and args[0] == "-f":
        files = [os.path.join(ROOT, args[1])]
        args = args[2:]

    V.launch(files)
    w = V.Win()
    print(f"launched {os.path.basename(files[0])}")

    i = 0
    while i < len(args):
        cmd = args[i]; i += 1
        if cmd == "click":
            x, y = float(args[i]), float(args[i + 1]); i += 2
            w.click(x, y)
            print(f"click {x},{y}")
        elif cmd == "pclick":
            # 直接从后门塞消息给 HWND：Hermes 桌面端永远抢前台，真鼠标点会落在它身上，
            # 窗口消息不看 z 序。坐标仍是逻辑像素（跟 click 一致）。
            x, y = float(args[i]), float(args[i + 1]); i += 2
            post_click(w, x, y)
            print(f"pclick {x},{y}")
        elif cmd == "pdbl":
            x, y = float(args[i]), float(args[i + 1]); i += 2
            post_click(w, x, y, dbl=True)
            print(f"pdbl {x},{y}")
        elif cmd == "pkey":
            k = args[i]; i += 1
            post_key(w, k)
            print(f"pkey {k}")
        elif cmd == "dbl":
            x, y = float(args[i]), float(args[i + 1]); i += 2
            w.click(x, y, dbl=True)
            print(f"dbl {x},{y}")
        elif cmd == "key":
            k = args[i]; i += 1
            w.key(k)
            print(f"key {k}")
        elif cmd == "sleep":
            s = float(args[i]); i += 1
            time.sleep(s)
            print(f"sleep {s}")
        elif cmd == "shot":
            n = args[i]; i += 1
            p = w.shot(n)
            print(f"shot {p}")
        elif cmd == "drag":
            # drag x1 y1 x2 y2 —— 按住左键从 (x1,y1) 拖到 (x2,y2)
            x1, y1, x2, y2 = (float(args[i + k]) for k in range(4)); i += 4
            sx, sy = w.x + int(x1 * V.SCALE), w.y + int(y1 * V.SCALE)
            ex, ey = w.x + int(x2 * V.SCALE), w.y + int(y2 * V.SCALE)
            u = V.user32
            u.SetCursorPos(sx, sy); time.sleep(0.2)
            u.mouse_event(0x0002, 0, 0, 0, 0); time.sleep(0.2)
            u.SetCursorPos(ex, ey); time.sleep(0.4)
            u.mouse_event(0x0004, 0, 0, 0, 0); time.sleep(0.4)
            w.refresh_rect()
            print(f"drag {x1},{y1}->{x2},{y2} now {w.w}x{w.h_}")
        elif cmd == "nresize":
            x, y, dx, dy = (float(args[i + k]) for k in range(4)); i += 4
            nresize(w, x, y, dx, dy)
        elif cmd == "pshot":
            n = args[i]; i += 1
            pshot(n)
            print(f"pshot {n}")
        elif cmd == "capdbl":
            capdbl(w)
        elif cmd == "mon":
            moninfo()
        elif cmd == "crect":
            rc = wt.RECT()
            user32.GetClientRect(wt.HWND(w.h), ctypes.byref(rc))
            print(f"client {rc.right - rc.left}x{rc.bottom - rc.top}")
        elif cmd == "active":
            fg, ok = active_state(w)
            print(f"active fg=0x{fg:x} volta=0x{w.h:x} match={ok}")
        elif cmd == "rect":
            w.refresh_rect()
            print(f"rect {w.w}x{w.h_} at {w.x},{w.y}")
        elif cmd == "log":
            m = args[i]; i += 1
            print("LOG", m, "->", V.log_tail(m, 6))
        else:
            raise SystemExit("unknown cmd: " + cmd)

    print("\n== log tail ==")
    for line in V.log_text().split("\n")[-14:]:
        if line.strip():
            print(" ", line.strip())
    w.drop_topmost()


if __name__ == "__main__":
    main(sys.argv[1:])
