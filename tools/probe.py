"""快速交互探针：给一个动作序列，跑完打印日志命中 + 截图。

用法：
    python tools/probe.py shot 名字.png                # 只截图
    python tools/probe.py key g g                      # 连按 g 两次
    python tools/probe.py click 80 173                 # 单击（逻辑坐标）
    python tools/probe.py dbl 80 173                   # 双击
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

V.VK.setdefault("g", 0x47)
V.VK.setdefault("t", 0x54)
V.VK.setdefault("s", 0x53)
V.LOG = os.path.join(V.ROOT, "build", "bin", "volta_run.log")


def main():
    args = sys.argv[1:]
    # 别的窗口（Hermes 桌面端）会一直压在上面抢焦点，先全部最小化
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "(New-Object -ComObject Shell.Application).MinimizeAll()"],
                   capture_output=True)
    time.sleep(1.0)
    w = V.Win()
    shots = []
    i = 0
    while i < len(args):
        cmd = args[i]
        if cmd == "shot":
            pat = args[i + 1]
            w.refresh_rect()
            shots.append(w.shot(pat))
            i += 2
        elif cmd == "key":
            i += 1
            while i < len(args) and args[i] not in ("click", "dbl", "shot"):
                V.user32.keybd_event(V.VK[args[i]], 0, 0, 0)
                time.sleep(0.05)
                V.user32.keybd_event(V.VK[args[i]], 0, 2, 0)
                time.sleep(1.2)
                i += 1
        elif cmd in ("click", "dbl"):
            x, y = int(args[i + 1]), int(args[i + 2])
            w.click(x, y, dbl=(cmd == "dbl"))
            time.sleep(1.0)
            i += 3
        else:
            i += 1

    txt = open(V.LOG, encoding="utf-8", errors="replace").read()
    keys = ("grid count", "addToGrid", "loadfile:", "shader ->", "theme switched",
            "playIndex", "WARN", "CRIT", "focus slot")
    for line in txt.split("\n"):
        if any(k in line for k in keys):
            print(line.strip()[:130])
    for s in shots:
        print("shot:", s)


if __name__ == "__main__":
    main()
