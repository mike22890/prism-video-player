"""验三件事：排序跟资源管理器一致、库点击落到悬停的那一格、缩略图有显示。

    python tools/sortslotcheck.py
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


def main():
    V.launch([os.path.join(ROOT, "media_many", "clip01.mp4")])
    w = V.Win()
    P.post_click(w, 600, 16)
    time.sleep(1.5)

    # 库页签
    for x in (45, 50, 55, 60):
        P.post_click(w, x, 57)
        time.sleep(0.4)
        if "VOLTA mode=1" in V.log_text():
            break
    time.sleep(3)
    print("排序日志:", V.log_tail("VOLTA sort", 3))

    # 按名称（sortMode 0）
    # 先把排序切到名称：点排序按钮直到 sort=0
    for _ in range(3):
        if "VOLTA sort=0" in V.log_text():
            break
        P.post_click(w, 118, 57)
        time.sleep(0.7)
    print("当前排序:", V.log_tail("VOLTA sort", 1))

    # 截图看列表顺序与缩略图
    before = set(glob.glob(os.path.join(ROOT, "build", "bin", "shot-*.png")))
    P.post_key(w, "f12")
    time.sleep(3.0)
    new = sorted(set(glob.glob(os.path.join(ROOT, "build", "bin", "shot-*.png"))) - before)
    if new:
        for _ in range(20):
            try:
                shutil.copyfile(new[-1], os.path.join(V.SHOTS, "sort-after.png"))
                break
            except PermissionError:
                time.sleep(0.3)
        print("截图: shots/sort-after.png")

    # 悬停第二个格子 → 点库里第一项 → 应该换第 2 格
    P.post_key(w, "g")            # 长出第 2 格
    time.sleep(1.5)
    time.sleep(0.8)
    # 窗口尺寸被 prefs 恢复过，重新钉回 1280x800，后面坐标才算得准
    user32 = V.user32
    import ctypes.wintypes as wt
    user32.SetWindowPos(wt.HWND(w.h), 0, 100, 100, 1920, 1200, 0x0004)
    time.sleep(0.8)
    w.refresh_rect()
    P.post_click(w, 950, 300)     # 鼠标移进第 2 格（触发 onEntered → focus）
    time.sleep(0.8)
    print("焦点:", V.log_tail("focus slot", 1))
    P.post_click(w, 120, 105)     # 点库里第一行
    time.sleep(1.6)
    print("assign 日志:", V.log_tail("assign slot", 2))
    w.drop_topmost()


if __name__ == "__main__":
    main()
