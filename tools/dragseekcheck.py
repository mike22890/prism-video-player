"""拖进度条：用窗口消息按下→移动→抬起，数 seek 次数（真鼠标会被置顶窗口吃掉）。"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

ROOT = V.ROOT


def seeks():
    return len([l for l in V.log_text().split("\n") if "seek ->" in l])


def main():
    V.launch([os.path.join(ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    P.post_click(w, 600, 16)
    time.sleep(1.2)
    P.post_click(w, 640, 400)
    time.sleep(0.6)

    h = w.h
    y = 729
    x0 = 600

    def lparam(lx, ly):
        return P._lparam(int(lx * V.SCALE), int(ly * V.SCALE))

    before = seeks()
    V.user32.PostMessageW(h, 0x0200, 0, lparam(x0, y))
    time.sleep(0.1)
    V.user32.PostMessageW(h, 0x0201, 1, lparam(x0, y))       # 按下
    time.sleep(0.15)
    for i in range(1, 9):
        V.user32.PostMessageW(h, 0x0200, 1, lparam(x0 + i * 40, y))   # 按住移动
        time.sleep(0.1)
    V.user32.PostMessageW(h, 0x0202, 0, lparam(x0 + 320, y))  # 抬起
    time.sleep(1.2)
    print(f"拖拽（按下→8 次移动→抬起）: {seeks() - before} 次 seek")
    w.drop_topmost()


if __name__ == "__main__":
    main()
