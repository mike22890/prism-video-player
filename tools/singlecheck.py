"""验单实例转交 + 窗口拉伸耗时。"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V

EXE = os.path.join(V.ROOT, "build", "bin", "prism.exe")
LOG = os.path.join(V.ROOT, "build", "bin", "volta_run.log")
user32 = V.user32


def count_procs():
    out = subprocess.run(["tasklist"], capture_output=True).stdout.decode("utf-8", "replace")
    return sum(1 for l in out.split("\n") if "prism.exe" in l.lower())


def main():
    V.launch([os.path.join(V.ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    time.sleep(1.2)
    print("进程数(第一个实例起来后):", count_procs())

    # 第二个进程：模拟「双击第二个视频」
    env = dict(os.environ)
    env["PATH"] = os.path.join(V.ROOT, "qt", "6.10.2", "mingw_64", "bin") + ";" + env["PATH"]
    t0 = time.time()
    rc = subprocess.run([EXE, os.path.join(V.ROOT, "media_long", "s3.mp4")],
                        cwd=os.path.join(V.ROOT, "build", "bin"), env=env,
                        capture_output=True, timeout=30).returncode
    print(f"第二个进程退出码={rc} 用时 {time.time() - t0:.2f}s")
    time.sleep(2.0)
    print("进程数(转交完):", count_procs())

    log = open(LOG, encoding="utf-8", errors="replace").read()
    got = [l for l in log.split("\n") if "single instance: got" in l or "external files" in l
           or "grid count=" in l]
    for l in got[-6:]:
        print("  日志:", l.strip())

    # 拉伸耗时：连续 30 步改宽度，量总时间
    w.refresh_rect()
    start = (w.w, w.h_)
    t0 = time.time()
    for i in range(30):
        user32.SetWindowPos(wt.HWND(w.h), 0, start[0], start[1],
                            start[0] - i * 6, start[1], 0x0004)
        time.sleep(0.01)
    dt = time.time() - t0
    w.refresh_rect()
    print(f"30 步改宽：{dt * 1000:.0f} ms（{dt / 30 * 1000:.1f} ms/步），尺寸 {start} -> {(w.w, w.h_)}")

    # 这段时间里日志涨了几行（改前每个像素一条）
    before_lines = len(log.split("\n"))
    after_lines = len(open(LOG, encoding="utf-8", errors="replace").read().split("\n"))
    print(f"拉伸期间日志新增 {after_lines - before_lines} 行（改前是每个尺寸变化一条）")
    w.drop_topmost()


if __name__ == "__main__":
    main()
