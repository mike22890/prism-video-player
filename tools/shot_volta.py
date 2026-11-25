"""抓 VOLTA 窗口（按进程名枚举顶层窗口 + PrintWindow）。"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

PW_RENDERFULLCONTENT = 0x00000002


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
    pids = set()
    for line in text.split("\n"):
        if proc_name.lower() in line.lower():
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                pids.add(int(parts[1]))
    if not pids:
        return []
    targets = [int(x) for x in pids]

    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in targets and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return found


def capture(hwnd, out_path):
    rect = wt.RECT()
    user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        print(f"bad rect {w}x{h}")
        return False
    hdc = user32.GetWindowDC(wt.HWND(hwnd))
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(memdc, bmp)
    ok = user32.PrintWindow(wt.HWND(hwnd), memdc, PW_RENDERFULLCONTENT)
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
    user32.ReleaseDC(wt.HWND(hwnd), hdc)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(out_path)
    print(f"saved {out_path} {w}x{h} PrintWindow={ok}")
    return True


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "prism.exe"
    out = sys.argv[2] if len(sys.argv) > 2 else "volta_shot.png"
    hw = find_windows(name)
    print("windows found:", len(hw))
    for i, h in enumerate(hw):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(wt.HWND(h), buf, 256)
        print(f"  [{i}] hwnd={h} title={buf.value!r}")
        capture(h, out if i == 0 else out.replace(".png", f"_{i}.png"))
