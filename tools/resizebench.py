"""拉伸耗时对照：没有视频 / 一格 / 两格。用来判断卡顿来自 QML 还是 mpv。"""
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

user32 = V.user32


def bench(w, steps=30, label=""):
    w.refresh_rect()
    x, y, base_w, base_h = w.x, w.y, w.w, w.h_
    t0 = time.time()
    for i in range(steps):
        user32.SetWindowPos(wt.HWND(w.h), 0, x, y, base_w - i * 6, base_h, 0x0004)
        time.sleep(0.01)
    dt = time.time() - t0
    print(f"{label}: {steps} 步 {dt*1000:.0f} ms -> {dt/steps*1000:.1f} ms/步")
    user32.SetWindowPos(wt.HWND(w.h), 0, x, y, base_w, base_h, 0x0004)
    time.sleep(0.4)


def main():
    V.launch([])                     # 不打开任何片
    w = V.Win()
    P.post_click(w, 600, 16)         # 激活
    time.sleep(1.5)
    bench(w, label="0 格")

    P.post_click(w, 100, 620)        # 点一下空列表区域，确保焦点在窗口上
    # 用单实例通道喂一个文件
    env = dict(os.environ)
    env["PATH"] = os.path.join(V.ROOT, "qt", "6.10.2", "mingw_64", "bin") + ";" + env["PATH"]
    exe = os.path.join(V.ROOT, "build", "bin", "prism.exe")
    subprocess.run([exe, os.path.join(V.ROOT, "media_long", "s1.mp4")],
                   cwd=os.path.join(V.ROOT, "build", "bin"), env=env, timeout=30)
    time.sleep(2.5)
    bench(w, label="1 格")

    subprocess.run([exe, os.path.join(V.ROOT, "media_long", "s2.mp4")],
                   cwd=os.path.join(V.ROOT, "build", "bin"), env=env, timeout=30)
    time.sleep(3.0)
    bench(w, label="2 格")
    w.drop_topmost()


if __name__ == "__main__":
    main()
