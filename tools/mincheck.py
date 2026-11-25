"""顶栏三个按钮到底哪个响应了：点一下 ─ / ▣，再报 IsIconic / IsZoomed / 日志。"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P


def state(w, tag):
    u = V.user32
    r = wt.RECT()
    u.GetWindowRect(wt.HWND(w.h), ctypes.byref(r))
    print(f"{tag}: iconic={bool(u.IsIconic(wt.HWND(w.h)))} zoomed={bool(u.IsZoomed(wt.HWND(w.h)))} "
          f"rect={r.right - r.left}x{r.bottom - r.top} at {r.left},{r.top}")
    print("   log:", V.log_tail("winbtn", 2))


def hittest(w, lx, ly):
    from ctypes import c_short
    code = V.user32.SendMessageW(wt.HWND(w.h), 0x0084, 0,
                                 ((((w.y + int(ly * V.SCALE)) & 0xFFFF) << 16)
                                  | ((w.x + int(lx * V.SCALE)) & 0xFFFF)))
    print(f"hittest at {lx},{ly} -> {code}")


def main():
    V.launch([os.path.join(V.ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    P.post_click(w, 600, 16)
    time.sleep(0.8)
    state(w, "start")
    for x, name in ((1170, "min(─)"), (1214, "max(▣)")):
        hittest(w, x, 20)
        P.post_click(w, x, 20)
        time.sleep(1.5)
        state(w, f"after click {name}")
        if V.user32.IsIconic(wt.HWND(w.h)):
            V.user32.ShowWindow(wt.HWND(w.h), 9)
            time.sleep(1.2)
        P.post_click(w, 600, 16)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
