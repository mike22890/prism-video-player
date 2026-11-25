"""VOLTA 截图工具：先最小化所有别的窗口，再把 VOLTA 顶到最前抓屏。

为什么不用 PrintWindow：Qt Quick 的画面在 DWM 合成层，PrintWindow 抓出来是空白的；
手记里那句「PrintWindow 对 Qt Quick 抓不全」就是这么来的。BitBlt 屏幕区域才是真像素，
前提是这台机器上不能有别的窗口压在它上面（Hermes 桌面端常年置顶，靠 MinimizeAll 让位）。

用法：
    python tools/cap.py <输出png> [窗口宽度x高度]

窗口会先被挪到 (0,0)，保证整块都在屏幕内。
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# 这台机器是 150% 缩放。进程不声明 DPI 感知时 GetWindowRect 返回的是
# 「虚拟化逻辑坐标」，而 BitBlt 抓的是物理像素 —— 两边差 1.5 倍，
# 抓出来就是右边下边被切掉一大块。先声明，再干活。
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

SRC_OVER = 0x00CC0020
CAPTUREBLT = 0x40000000
SW_RESTORE = 9
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
        ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


def find_window(proc_name="prism.exe"):
    out = subprocess.run(["tasklist"], capture_output=True).stdout.decode("utf-8", "replace")
    pids = {int(p.split()[1]) for p in out.split("\n")
            if proc_name.lower() in p.lower() and len(p.split()) >= 2 and p.split()[1].isdigit()}
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(h):
            rect = wt.RECT()
            user32.GetWindowRect(h, ctypes.byref(rect))
            if rect.right - rect.left > 200 and rect.bottom - rect.top > 200:
                found.append(h)
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def capture(rect, out_path):
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetDC(0)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(memdc, bmp)
    gdi32.BitBlt(memdc, 0, 0, w, h, hdc, rect.left, rect.top, SRC_OVER | CAPTUREBLT)

    bi = BITMAPINFO()
    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = w
    bi.bmiHeader.biHeight = -h
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(0, hdc)

    from PIL import Image
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(out_path)
    return w, h


def main():
    out = sys.argv[1]
    size = None
    if len(sys.argv) > 2 and "x" in sys.argv[2]:
        a, b = sys.argv[2].lower().split("x")
        size = (int(a), int(b))

    hwnd = find_window()
    if not hwnd:
        print("NO VOLTA WINDOW")
        return 1

    # 1) 别的窗口全部让位（Hermes 桌面端会一直压在上面）
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "(New-Object -ComObject Shell.Application).MinimizeAll()"],
                   capture_output=True)
    time.sleep(0.8)

    # 2) VOLTA 挪到左上角、置顶、给键盘
    user32.ShowWindow(wt.HWND(hwnd), SW_RESTORE)
    flags = SWP_SHOWWINDOW
    w, h = size if size else (0, 0)
    if not size:
        r = wt.RECT()
        user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
    user32.SetWindowPos(wt.HWND(hwnd), HWND_TOPMOST, 0, 0, w, h, flags)
    user32.SetForegroundWindow(wt.HWND(hwnd))
    user32.BringWindowToTop(wt.HWND(hwnd))
    time.sleep(1.6)

    rect = wt.RECT()
    user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(rect))
    w, h = capture(rect, out)
    # 抓完撤掉 TOPMOST，别赖在别人头上
    user32.SetWindowPos(wt.HWND(hwnd), -2, 0, 0, 0, 0, 0x0001 | 0x0002)
    print(f"saved {out} {w}x{h} at ({rect.left},{rect.top})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
