"""拍几张「程序自己渲染的」截图：一格 / 三格 / 全屏。

F12 = QML 里的 grabToImage，走 QQuick 渲染路径，不受窗口遮挡影响。
产物在 build/bin/shot-*.png。

    python tools/shots_tour.py
"""
import glob
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

ROOT = V.ROOT
BIN = os.path.join(ROOT, "build", "bin")


def shoot(w, tag):
    before = set(glob.glob(os.path.join(BIN, "shot-*.png")))
    P.post_key(w, "f12")
    for _ in range(24):
        time.sleep(0.25)
        new = set(glob.glob(os.path.join(BIN, "shot-*.png"))) - before
        if new:
            src = sorted(new)[-1]
            dst = os.path.join(V.SHOTS, f"grab-{tag}.png")
            for _ in range(20):
                try:
                    shutil.copyfile(src, dst)
                    print(f"{tag}: {dst}")
                    return dst
                except PermissionError:
                    time.sleep(0.2)
            print(f"{tag}: COPY LOCKED {src}")
            return None
    print(f"{tag}: NO FILE")
    return None


def main():
    V.launch([os.path.join(ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    P.post_click(w, 600, 16)
    time.sleep(1.0)
    shoot(w, "1slot")
    P.post_key(w, "g")
    time.sleep(1.5)
    P.post_key(w, "g")
    time.sleep(2.0)
    shoot(w, "3slot")
    P.post_key(w, "f11")
    time.sleep(2.0)
    w.refresh_rect()
    shoot(w, "fullscreen")
    P.post_key(w, "esc")
    time.sleep(1.5)
    shoot(w, "afterfullscreen")
    w.drop_topmost()


if __name__ == "__main__":
    main()
