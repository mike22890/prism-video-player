"""swapprobe.py —— 拖动期间每帧 present(swap) 到底阻塞多久；关 vsync 有没有用。

固定脚本：起 → 等 → 8 大步拉伸 → 退。跳过启动前 120 帧（纹理/管线创建），
剩下的帧里 swap>=6ms 的就是拖动那一段。

用法： python tools/swapprobe.py default novsync
"""
import ctypes, os, re, statistics, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

MODES = {"default": {}, "novsync": {"QSG_NO_VSYNC": "1"},
         "basic": {"QSG_RENDER_LOOP": "basic"},
         "simple": {"QSG_USE_SIMPLE_ANIMATION_DRIVER": "1"}}
SKIP = 120


def one(env_extra, drags=3):
    for k in ("QSG_NO_VSYNC", "QSG_RENDER_LOOP", "QSG_USE_SIMPLE_ANIMATION_DRIVER"):
        os.environ.pop(k, None)
    os.environ.update(env_extra)
    V.launch([os.path.join(V.ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    time.sleep(0.5)
    for i in range(drags):
        P.nresize(w, 400, 400, 220 if i % 2 == 0 else -220, 120 if i % 2 == 0 else -120)
    w.drop_topmost()
    t = V.log_text().split("\n")
    fr = []
    for l in t:
        m = re.search(r"frame rendered in (\d+)ms, sync=(\d+), render=(\d+), swap=(\d+)", l)
        if m:
            fr.append(tuple(int(x) for x in m.groups()))
    tail = fr[SKIP:]
    swaps = [f[3] for f in tail]
    hot = [s for s in swaps if s >= 6]
    return {
        "frames_after_skip": len(tail),
        "hot_swap_n": len(hot),
        "hot_swap_p50": round(statistics.median(hot), 1) if hot else 0,
        "hot_swap_max": max(hot) if hot else 0,
        "all_swap_mean": round(sum(swaps) / max(1, len(swaps)), 2),
        "all_frame_mean": round(sum(f[0] for f in tail) / max(1, len(tail)), 2),
        "render_max": max((f[2] for f in tail), default=0),
    }


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["default"]):
        r = one(MODES[n])
        print(f"{n:9s} " + "  ".join(f"{k}={v}" for k, v in r.items()), flush=True)
        time.sleep(1.0)
