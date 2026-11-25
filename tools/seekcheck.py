"""验：设置写没写进注册表；拖进度条是不是只在松手时 seek 一次。"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

ROOT = V.ROOT


def seeks():
    return len([l for l in V.log_text().split("\n") if "seek ->" in l])


def main():
    out = subprocess.run(["reg", "query", r"HKCU\Software\VOLTA\VOLTA\view"],
                         capture_output=True, text=True, errors="replace").stdout
    print("注册表里的 view 键：")
    for line in out.splitlines():
        if any(k in line for k in ("themeIdx", "loopMode", "shaderIdx", "sortMode", "window")):
            print("   ", line.strip())

    V.launch([os.path.join(ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    P.post_click(w, 600, 16)          # 激活
    time.sleep(1.5)
    P.post_click(w, 640, 400)         # 点画面，确保焦点在这个格子
    time.sleep(0.6)

    # 进度条：单格时 x 约 346..1180，y 约 729
    y = 729
    before = seeks()
    P.post_click(w, 600, y)           # 按下（post_click 是按下+抬起，先看单击会不会 seek）
    time.sleep(0.6)
    click_seeks = seeks() - before
    print(f"单击进度条：seek 次数 {click_seeks}（应为 1）")

    # 拖拽：按下 → 连续移动 8 次 → 抬起
    before = seeks()
    cx = w.x + 600
    cy = w.y + int(y * V.SCALE)
    u = V.user32
    u.SetCursorPos(cx, cy)
    time.sleep(0.2)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.15)
    for i in range(1, 9):
        u.mouse_event(0x0001, 40, 0, 0, 0)
        time.sleep(0.12)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(1.0)
    print(f"拖拽一次：seek 次数 {seeks() - before}（改前是跟着鼠标每一次移动都 seek）")
    w.drop_topmost()


if __name__ == "__main__":
    main()
