"""抓 VOLTA 自己的窗口内容 —— 不管它被谁盖住。

BitBlt 抓的是屏幕像素，Hermes 桌面端常年在最前面，抓出来就是别人的画面。
PrintWindow(PW_RENDERFULLCONTENT) 让窗口自己往内存 DC 里画一遍，跟 z 序无关。

    python tools/snap.py out.png
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

user32 = V.user32
gdi32 = V.gdi32

PW_RENDERFULLCONTENT = 0x00000002


def main(name):
    h = V.find_window()
    if not h:
        raise SystemExit("NO VOLTA WINDOW")
    r = wt.RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    w, hh = r.right - r.left, r.bottom - r.top

    hdc = user32.GetWindowDC(h)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, hh)
    gdi32.SelectObject(memdc, bmp)
    ok = user32.PrintWindow(h, memdc, PW_RENDERFULLCONTENT)

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
    user32.ReleaseDC(h, hdc)

    from PIL import Image
    p = os.path.join(V.SHOTS, name)
    Image.frombuffer("RGBA", (w, hh), buf, "raw", "BGRA", 0, 1).convert("RGB").save(p)
    print(f"PrintWindow ok={ok} {w}x{hh} -> {p}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "snap.png")
