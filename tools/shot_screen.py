"""真实屏幕抓取：把窗口置前，用 CopyFromScreen 抓屏幕区域。
PrintWindow 对 Qt Quick (GPU 合成) 窗口抓不全，必须走屏幕像素。
"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

SW_RESTORE = 9
SW_SHOW = 5
SRC_OVER = 0x00CC0020
CAPTUREBLT = 0x40000000


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


def find_windows(proc_name):
    r = subprocess.run(["tasklist"], capture_output=True)
    text = r.stdout.decode("utf-8", "replace")
    pids = {int(p.split()[1]) for p in text.split("\n")
            if proc_name.lower() in p.lower() and len(p.split()) >= 2 and p.split()[1].isdigit()}
    if not pids:
        return []
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return found


def screen_capture(hwnd, out_path):
    # 置前 + 移到主屏左上 + 最大化，避免被别的窗口盖住
    user32.ShowWindow(wt.HWND(hwnd), SW_RESTORE)
    user32.SetForegroundWindow(wt.HWND(hwnd))
    user32.BringWindowToTop(wt.HWND(hwnd))
    user32.SetWindowPos(wt.HWND(hwnd), -1, 0, 0, 1280, 820, 0)  # HWND_TOPMOST
    time.sleep(0.5)
    user32.SetWindowPos(wt.HWND(hwnd), -2, 0, 0, 1280, 820, 0)  # 取消置顶但保持位置
    time.sleep(1.5)

    rect = wt.RECT()
    user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        print(f"bad rect {w}x{h}")
        return False

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
    bi.bmiHeader.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(0, hdc)

    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(out_path)
    print(f"saved {out_path} {w}x{h} (screen capture)")
    return True


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "prism.exe"
    out = sys.argv[2] if len(sys.argv) > 2 else "volta_screen.png"
    hw = find_windows(name)
    print("windows:", len(hw))
    if hw:
        screen_capture(hw[0], out)
