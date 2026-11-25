"""清场截图：把挡在 VOLTA 前面的窗口临时最小化 → 抓屏 → 原样恢复。

为什么需要它：Hermes 桌面端是置顶窗口，PrintWindow 对 GL 合成的窗口又只会吐旧帧。
要拍到「现在这一帧」只有两条路：置顶压过它（压不动），或者让它先躲开一秒。

    python tools/clean_shot.py 名字.png
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

user32 = V.user32
gdi32 = V.gdi32


def top_level_windows():
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, _):
        if not user32.IsWindowVisible(h):
            return True
        buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, buf, 64)
        if buf.value in ("Progman", "Shell_TrayWnd", "WorkerW"):
            return True
        r = wt.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        if r.right - r.left < 200 or r.bottom - r.top < 200:
            return True
        out.append(h)
        return True

    user32.EnumWindows(cb, 0)
    return out


def grab_rect(h, name):
    r = wt.RECT()
    user32.GetWindowRect(wt.HWND(h), ctypes.byref(r))
    w, hh = r.right - r.left, r.bottom - r.top
    hdc = user32.GetDC(0)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, hh)
    gdi32.SelectObject(memdc, bmp)
    gdi32.BitBlt(memdc, 0, 0, w, hh, hdc, r.left, r.top, 0x00CC0020 | 0x40000000)

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
    bi.bmiHeader.biHeight = -hh
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    buf = ctypes.create_string_buffer(w * hh * 4)
    gdi32.GetDIBits(memdc, bmp, 0, hh, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(0, hdc)

    from PIL import Image
    p = os.path.join(V.SHOTS, name)
    Image.frombuffer("RGBA", (w, hh), buf, "raw", "BGRA", 0, 1).convert("RGB").save(p)
    print(f"shot {w}x{hh} -> {p}")
    return p


def main(name):
    volta = V.find_window()
    if not volta:
        raise SystemExit("NO VOLTA WINDOW")
    hidden = []
    for h in top_level_windows():
        if h == volta:
            continue
        user32.ShowWindow(wt.HWND(h), 6)      # SW_MINIMIZE
        hidden.append(h)
    time.sleep(1.2)
    try:
        grab_rect(volta, name)
    finally:
        for h in hidden:
            user32.ShowWindow(wt.HWND(h), 9)  # SW_RESTORE
        time.sleep(0.6)
        print(f"restored {len(hidden)} window(s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "clean.png")
