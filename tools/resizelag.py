"""resizelag.py —— 「窗口跟不跟得上鼠标」的量化。这才是用户嘴里的「卡」。

poke.nresize 是 8 大步、每步 90ms，窗口有的是时间追上，所以它测不出卡。
这里改成真人手速：125Hz 鼠标 => 每 8ms 移 4px，连续 60 次，每次回读窗口矩形，
算「鼠标已经到哪 / 窗口实际到哪」的差（px）。差得越多 = 越粘。

用法： python tools/resizelag.py [组名...]      组名：default novsync basic nosync_basic
"""
import ctypes, ctypes.wintypes as wt, os, statistics, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

user32 = V.user32

MODES = {
    "default":      {},
    "novsync":      {"QSG_NO_VSYNC": "1"},
    "basic":        {"QSG_RENDER_LOOP": "basic"},
    "basic_novsync": {"QSG_RENDER_LOOP": "basic", "QSG_NO_VSYNC": "1"},
}


def rect(h):
    r = wt.RECT()
    user32.GetWindowRect(wt.HWND(h), ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def drag_lag(w, dx=300, steps=60, period=0.008):
    """从右边缘开始横向拖 dx 物理像素，逐渐加力，边拖边量落后多少。"""
    x, y, cw, ch = rect(w.h)
    sx, sy = x + cw - 3, y + ch // 2
    user32.SetCursorPos(sx, sy)
    time.sleep(0.25)
    user32.PostMessageW(w.h, 0x00A1, 11, ((sy << 16) | (sx & 0xFFFF)))   # WM_NCLBUTTONDOWN/HTRIGHT
    time.sleep(0.35)
    per = dx / steps
    lags = []
    acc = 0.0
    moved = 0
    t0 = time.perf_counter()
    for i in range(1, steps + 1):
        # 相对移动：真系统的拉伸循环吃的是相对位移（SetCursorPos 它不跟，试过）
        n = int(round(per))
        user32.mouse_event(0x0001, n, 0, 0, 0)
        moved += n
        time.sleep(period)
        _, _, aw, _ = rect(w.h)
        lags.append(cw + moved - aw)
    dur = time.perf_counter() - t0
    user32.mouse_event(0x0004, 0, 0, 0, 0)                                # LEFTUP
    time.sleep(0.6)
    _, _, fw, _ = rect(w.h)
    return {
        "lag_p50": round(statistics.median(lags), 1),
        "lag_p90": round(sorted(lags)[int(len(lags) * .9)], 1),
        "lag_max": round(max(lags), 1),
        "final_err": round(cw + moved - fw, 1),
        "dur_ms": round(dur * 1000),
    }


def run(mode, env_extra):
    for k in ("QSG_NO_VSYNC", "QSG_RENDER_LOOP"):
        os.environ.pop(k, None)
    os.environ.update(env_extra)
    V.launch([os.path.join(V.ROOT, "media_long", "s1.mp4")])
    w = V.Win()
    r = drag_lag(w)
    w.drop_topmost()
    print(f"{mode:13s} " + "  ".join(f"{k}={v}" for k, v in r.items()), flush=True)
    return r


def main():
    names = sys.argv[1:] or list(MODES)
    for n in names:
        try:
            run(n, MODES[n])
        except SystemExit as e:
            print(n, "FAILED", e, flush=True)
        time.sleep(1.2)


if __name__ == "__main__":
    main()
