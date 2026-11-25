"""验收「点得到 + 任务栏有图标」：把挡路的窗口临时最小化，然后真点、真查任务栏。

    python tools/clickcheck.py
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import clean_shot as C

user32 = V.user32


def taskbar_has_volta():
    """任务栏按钮里有没有 VOLTA（UIA 读 Shell_TrayWnd 的子元素名字）。"""
    ps = r'''
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$tc = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty, "Shell_TrayWnd")
$bar = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $tc)
if (-not $bar) { Write-Output "NO TASKBAR"; exit }
$all = $bar.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
foreach ($e in $all) { $n = $e.Current.Name; if ($n) { Write-Output $n } }
'''
    p = os.path.join(os.environ.get("TEMP", "."), "tb.ps1")
    open(p, "w", encoding="utf-8").write(ps)
    out = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", p],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    names = [l.strip() for l in out.splitlines() if l.strip()]
    hit = [n for n in names if "VOLTA" in n.upper()]
    return hit, names


def main():
    V.launch([os.path.join(V.ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    time.sleep(1.0)
    h = wt.HWND(w.h)

    others = [x for x in C.top_level_windows() if x != w.h]
    for x in others:
        user32.ShowWindow(wt.HWND(x), 6)      # SW_MINIMIZE
    time.sleep(1.5)

    cx, cy = w.x + w.w // 2, w.y + w.h_ // 2
    under = user32.WindowFromPoint(wt.POINT(cx, cy))
    print(f"挡路的都让开后：WindowFromPoint({cx},{cy}) = 0x{under:x} "
          f"{'=VOLTA ✓' if under == w.h else '≠VOLTA ✗'}")

    before = V.log_text()
    user32.SetCursorPos(cx, cy)
    time.sleep(0.3)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(1.2)
    new = [l for l in V.log_text().split("\n") if l not in before.split("\n") and "VOLTA" in l]
    print("真鼠标点击后新增日志:", new[-3:] if new else "无（又点空了）")

    subprocess.run([sys.executable, os.path.join(V.ROOT, "tools", "shotnow.py"), "vis-live.png"],
                   capture_output=True)

    hit, names = taskbar_has_volta()
    print(f"任务栏按钮里 VOLTA：{'有 -> ' + str(hit) if hit else '没有'}"
          f"（共读到 {len(names)} 个按钮名）")

    for x in others:
        user32.ShowWindow(wt.HWND(x), 9)      # SW_RESTORE
    time.sleep(0.8)
    w.drop_topmost()


if __name__ == "__main__":
    main()
