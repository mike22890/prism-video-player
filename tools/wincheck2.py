"""验窗口：右侧边缘拖动改尺寸 + 点「全屏」不黑屏 + Esc 退出。

用法：python tools/wincheck2.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

w = V.Win()
u = V.user32
print("before:", w.w, w.h_, "at", w.x, w.y)

# 1) 右边缘拖动：把宽度拉大 160px
edge_x = w.x + w.w - 3
edge_y = w.y + w.h_ // 2
u.SetCursorPos(edge_x, edge_y)
time.sleep(0.3)
u.mouse_event(0x0002, 0, 0, 0, 0)          # down
time.sleep(0.15)
for dx in range(0, 161, 20):
    u.SetCursorPos(edge_x + dx, edge_y)
    time.sleep(0.03)
u.mouse_event(0x0004, 0, 0, 0, 0)          # up
time.sleep(0.8)
w.refresh_rect()
print("after right-edge drag:", w.w, w.h_)

# 2) 点「全屏」（底部条最右一个按钮）
w.click(w.w / 1.5 - 40, 800 - 22)
time.sleep(2.0)
w.refresh_rect()
print("after fullscreen click:", w.w, w.h_, "at", w.x, w.y)
p = w.shot("fs_check.png")

# 3) Esc 退出
V.user32.keybd_event(0x1B, 0, 0, 0)
time.sleep(0.05)
V.user32.keybd_event(0x1B, 0, 2, 0)
time.sleep(1.5)
w.refresh_rect()
print("after esc:", w.w, w.h_, "at", w.x, w.y)

log = open(V.LOG, encoding="utf-8", errors="replace").read()
print("fullscreen log:", [l.strip() for l in log.split("\n") if "fullscreen" in l][-3:])
print("warnings:", [l for l in log.split("\n") if "WARN" in l or "CRIT" in l][-3:])
print("shot:", p)
