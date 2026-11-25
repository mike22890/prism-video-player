"""直接问窗口：这个像素点你打算怎么处理？（WM_NCHITTEST 的返回值）

比「拖一下看会不会变大」确定得多：HTLEFT/HTRIGHT/... 就是 Windows 决定
要不要进入拉伸模式的依据。坐标用逻辑像素，脚本自己换算成屏幕物理像素。

    python tools/hittest.py
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

user32 = V.user32
WM_NCHITTEST = 0x0084

NAMES = {
    0: "HTNOWHERE", 1: "HTCLIENT", 2: "HTCAPTION", 10: "HTLEFT", 11: "HTRIGHT",
    12: "HTTOP", 13: "HTTOPLEFT", 14: "HTTOPRIGHT", 15: "HTBOTTOM",
    16: "HTBOTTOMLEFT", 17: "HTBOTTOMRIGHT",
}


def main():
    h = V.find_window()
    if not h:
        raise SystemExit("NO VOLTA WINDOW")
    r = wt.RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    x0, y0 = r.left, r.top
    w, hh = r.right - r.left, r.bottom - r.top
    print(f"window {w}x{hh} at {x0},{y0}")

    def probe(label, lx, ly, expect):
        sx, sy = x0 + int(lx * V.SCALE), y0 + int(ly * V.SCALE)
        lp = ((sy & 0xFFFF) << 16) | (sx & 0xFFFF)
        code = user32.SendMessageW(wt.HWND(h), WM_NCHITTEST, 0, lp)
        # 返回值按 16 位看（Windows 只认低字节，但会带符号扩展）
        code = ctypes.c_short(code).value if code > 0x7FFFFFFF else code
        name = NAMES.get(code, str(code))
        ok = "PASS" if name == expect else "FAIL"
        print(f"{ok} {label:22s} -> {name:14s} (expect {expect})")
        return name == expect

    res = []
    res.append(probe("右边中段", 1279, 400, "HTRIGHT"))
    res.append(probe("左边中段", 0, 400, "HTLEFT"))
    res.append(probe("下边中段", 640, 799, "HTBOTTOM"))
    res.append(probe("左上角", 1, 1, "HTTOPLEFT"))
    res.append(probe("右下角", 1278, 798, "HTBOTTOMRIGHT"))
    res.append(probe("上边中段", 640, 1, "HTTOP"))
    res.append(probe("标题栏中央", 640, 16, "HTCAPTION"))
    res.append(probe("画面中央", 640, 400, "HTCLIENT"))
    print(f"\n{sum(res)}/{len(res)} passed")


if __name__ == "__main__":
    main()
