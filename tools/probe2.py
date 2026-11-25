"""找轨道：在格子自带进度条附近逐点点击，看哪个 y 真的触发了 seek。

    python tools/probe2.py
"""
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
    P.post_click(w, 600, 16)          # 激活
    time.sleep(0.6)
    for line in V.log_text().split("\n"):
        if "DEBUG win=" in line or "gridArea" in line:
            print("  ", line.strip())

    for y in (690, 705, 720, 729, 738, 748, 755):
        before = seeks()
        P.post_click(w, 700, y)
        time.sleep(0.5)
        after = seeks()
        tail = V.log_tail("seek ->", 1)
        print(f"y={y:4d} seek {before}->{after} {tail}")

    print("\n-- 横向：同一条 y 上改 x --")
    best_y = 729
    for x in (350, 500, 800, 1100, 1170):
        before = seeks()
        P.post_click(w, x, best_y)
        time.sleep(0.5)
        print(f"x={x:5d} seek {before}->{seeks()} {V.log_tail('seek ->', 1)}")

    w.drop_topmost()


if __name__ == "__main__":
    main()
