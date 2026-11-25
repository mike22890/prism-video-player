"""验窗口行为：双击标题栏是否最大化、有没有变尺寸。

用法：python tools/wincheck.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

w = V.Win()
u = V.user32
print("before:", w.w, w.h_, "at", w.x, w.y)

x, y = w.x + 700, w.y + 18
u.SetCursorPos(x, y)
time.sleep(0.3)
for _ in range(2):
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.12)
time.sleep(1.8)
w.refresh_rect()
print("after title dblclick:", w.w, w.h_, "at", w.x, w.y)

# 再双击一次，应该还原
u.SetCursorPos(w.x + 700, w.y + 18)
time.sleep(0.2)
for _ in range(2):
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.12)
time.sleep(1.8)
w.refresh_rect()
print("after 2nd dblclick (restore):", w.w, w.h_, "at", w.x, w.y)

log = open(V.LOG, encoding="utf-8", errors="replace").read()
print("warnings:", [l for l in log.split("\n") if "WARN" in l or "CRIT" in l][-3:])
