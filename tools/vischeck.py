"""验「窗口是不是真的可见」：可见位 / IsWindowVisible / 命中测试 / 真鼠标点击 / 截图是不是活帧。

    python tools/vischeck.py
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

user32 = V.user32
WS_VISIBLE = 0x10000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080


def main():
    V.launch([os.path.join(V.ROOT, "media_long", "s1.mp4")])
    w = V.Win()          # 顺带把窗口摆到 1280x800 逻辑、置顶一会儿
    time.sleep(1.0)
    h = wt.HWND(w.h)

    style = user32.GetWindowLongW(h, -16)
    ex = user32.GetWindowLongW(h, -20)
    print(f"style=0x{style & 0xFFFFFFFF:08x}  WS_VISIBLE={'ON' if style & WS_VISIBLE else 'off'}")
    print(f"exstyle=0x{ex & 0xFFFFFFFF:08x}  APPWINDOW={'ON' if ex & WS_EX_APPWINDOW else 'off'}"
          f"  TOOLWINDOW={'ON' if ex & WS_EX_TOOLWINDOW else 'off'}")
    print("IsWindowVisible:", bool(user32.IsWindowVisible(h)))

    # 命中测试：屏幕中心那一点归谁
    cx, cy = w.x + w.w // 2, w.y + w.h_ // 2
    pt = wt.POINT(cx, cy)
    under = user32.WindowFromPoint(pt)
    print(f"WindowFromPoint({cx},{cy}) -> 0x{under:x}  {'=VOLTA' if under == h else '≠VOLTA（被盖住或穿透）'}")

    # 真鼠标点一下画面中央：日志里应该出现 focus / togglePlay
    before = len(V.log_text())
    user32.SetCursorPos(cx, cy)
    time.sleep(0.3)
    user32.mouse_event(0x0002, 0, 0, 0, 0)   # 左键按下
    time.sleep(0.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0)   # 抬起
    time.sleep(1.2)
    tail = V.log_tail("VOLTA", 4)
    print("点击后日志:", tail if len(V.log_text()) > before else "无新日志（点空了）")

    # PrintWindow 是不是活帧：连拍两张，时间码应该不一样
    import subprocess
    for i in (1, 2):
        subprocess.run([sys.executable, os.path.join(V.ROOT, "tools", "snap.py"),
                        f"vis{i}.png"], capture_output=True)
        time.sleep(1.5)
    from PIL import Image, ImageChops
    a = Image.open(os.path.join(V.SHOTS, "vis1.png")).convert("L")
    b = Image.open(os.path.join(V.SHOTS, "vis2.png")).convert("L")
    diff = ImageChops.difference(a, b)
    mean = sum(diff.resize((80, 50)).tobytes()) / 4000.0
    print(f"两张 PrintWindow 平均差={mean:.2f}（>0.5 说明是活帧，≈0 说明还在吐旧帧）")
    w.drop_topmost()


if __name__ == "__main__":
    main()
