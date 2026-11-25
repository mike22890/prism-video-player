"""真·屏幕截图：先把窗口顶到最上层，再 BitBlt 屏幕，最后撤掉置顶。

PrintWindow 对 GL 合成窗口会吐旧帧（截出来的画面停在上一次重绘），
所以验收用的截图走这条：SetWindowPos TOPMOST → 抓屏 → 恢复。
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
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE_NOSIZE_NOACTIVATE = 0x0001 | 0x0002 | 0x0010


def grab(name):
    h = V.find_window()
    if not h:
        raise SystemExit("NO VOLTA WINDOW")
    user32.SetWindowPos(wt.HWND(h), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE_NOSIZE_NOACTIVATE)
    time.sleep(0.7)
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
    user32.SetWindowPos(wt.HWND(h), HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE_NOSIZE_NOACTIVATE)
    print(f"screen shot {w}x{hh} -> {p}")
    return p


if __name__ == "__main__":
    grab(sys.argv[1] if len(sys.argv) > 1 else "screen.png")
