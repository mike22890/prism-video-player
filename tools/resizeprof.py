"""resizeprof.py —— 拖动边框逐帧剖析（用真·系统拉伸 + Qt 官方渲染循环计时日志）。

对照组：默认 / 关 vsync / basic 渲染循环 / 简单动画驱动。
每组跑同一段 nresize，统计拖动区间内的
  · 帧数、GUI 线程两帧间隔（= 拖动被拉慢多少）
  · sync / render / swap 三段耗时
用来回答「卡在哪一段、关掉它有没有用」——不靠感受。

用法： python tools/resizeprof.py
"""
import ctypes, ctypes.wintypes as wt, os, re, statistics, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

user32 = V.user32
LOG = V.LOG
MARK = "VOLTA focus slot="

MODES = [
    ("default",        {}),
    ("novsync",        {"QSG_NO_VSYNC": "1"}),
    ("basic_loop",     {"QSG_RENDER_LOOP": "basic"}),
    ("simple_anim",    {"QSG_USE_SIMPLE_ANIMATION_DRIVER": "1"}),
]


MARK_LINE = "=== PROF MARK ==="


def mark():
    with open(LOG, "a", encoding="utf-8") as f:      # 直接往 app 的日志里插一行
        f.write(MARK_LINE + "\n")


def _segment(text):
    lines = text.split("\n")
    idx = [k for k, l in enumerate(lines) if MARK_LINE in l]
    if len(idx) < 2:
        return []
    return lines[idx[-2]:idx[-1]]


def frames_between(text):
    out = []
    for l in _segment(text):
        m = re.search(r"frame rendered in (\d+)ms, sync=(\d+), render=(\d+), swap=(\d+)", l)
        if m:
            out.append(tuple(int(x) for x in m.groups()))
    return out


def pacing_between(text):
    return [int(m.group(1)) for l in _segment(text)
            for m in [re.search(r"elapsed since last call: (\d+) ms", l)] if m]


def run(mode, env_extra, drag=(300, 200)):
    for k in ("QSG_NO_VSYNC", "QSG_RENDER_LOOP", "QSG_USE_SIMPLE_ANIMATION_DRIVER"):
        os.environ.pop(k, None)
    os.environ.update(env_extra)
    V.launch([os.path.join(V.ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    mark(); time.sleep(0.3)
    P.nresize(w, 400, 400, drag[0], drag[1])
    time.sleep(0.4)
    mark(); time.sleep(0.5)
    txt = V.log_text()
    fr = frames_between(txt)
    pace = pacing_between(txt)
    w.drop_topmost()
    if not fr:
        print(f"{mode:12s} :: 没抓到帧（日志 {len(txt)} 字符）")
        return None
    r = {
        "mode": mode, "frames": len(fr),
        "swap_p50": statistics.median([f[3] for f in fr]),
        "swap_max": max(f[3] for f in fr),
        "swap_sum": sum(f[3] for f in fr),
        "render_p50": statistics.median([f[2] for f in fr]),
        "render_max": max(f[2] for f in fr),
        "frame_p50": statistics.median([f[0] for f in fr]),
        "frame_max": max(f[0] for f in fr),
        "gap_p50": statistics.median(pace) if pace else -1,
        "gap_max": max(pace) if pace else -1,
    }
    print(f"{mode:12s} frames={r['frames']:3d}  swap p50={r['swap_p50']:5.1f} sum={r['swap_sum']:5d} max={r['swap_max']:3d}"
          f"  render p50={r['render_p50']:4.1f} max={r['render_max']:3d}"
          f"  frame p50={r['frame_p50']:4.1f} max={r['frame_max']:3d}"
          f"  gap p50={r['gap_p50']:3d} max={r['gap_max']:3d}")
    return r


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    res = []
    for mode, env in MODES:
        if only and only not in mode:
            continue
        try:
            r = run(mode, env)
        except SystemExit as e:
            print(mode, "FAILED", e)
            r = None
        if r:
            res.append(r)
        time.sleep(1.0)
    print()


if __name__ == "__main__":
    main()
