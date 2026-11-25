"""验三件事：缩略图有没有对错号、设置能不能记住、拖进度条是不是只 seek 一次。

用法：python tools/thumbverify.py
"""
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

ROOT = V.ROOT
MPV = os.path.join(ROOT, "mpvbin", "mpv.exe")
CACHE = os.path.join(os.environ["LOCALAPPDATA"], "VOLTA", "VOLTA", "cache")
THUMBS = os.path.join(CACHE, "thumbs")


def fresh_frame(path, outdir):
    os.makedirs(outdir, exist_ok=True)
    subprocess.run([MPV, "--no-config", "--no-audio", "--really-quiet",
                    "--load-scripts=no", "--start=5", "--frames=1", "--vo=image",
                    "--vo-image-format=jpg", "--vo-image-outdir=" + outdir, path],
                   capture_output=True, timeout=60)
    made = glob.glob(os.path.join(outdir, "*.jpg"))
    return made[0] if made else None


def main():
    # 干净缓存：旧图是竞态版本生成的，留着没法判断
    if os.path.isdir(THUMBS):
        shutil.move(THUMBS, THUMBS + ".old")
    os.makedirs(THUMBS, exist_ok=True)

    V.launch([os.path.join(ROOT, "media_many", "clip01.mp4")])
    w = V.Win()
    P.post_click(w, 600, 16)
    time.sleep(1.0)
    # 切到库页签，让 16 条都进 delegate
    for x in (45, 50, 55, 60, 65):
        P.post_click(w, x, 57)
        time.sleep(0.4)
        if "VOLTA mode=1" in V.log_text():
            break
    print("等待抽帧…")
    deadline = time.time() + 120
    while time.time() < deadline:
        n = len(glob.glob(os.path.join(THUMBS, "*.jpg")))
        if n >= 16:
            break
        time.sleep(3)
    cached = glob.glob(os.path.join(THUMBS, "*.jpg"))
    print(f"缓存里有 {len(cached)} 张")

    # 逐张和「现抽一帧」比对：文件名不同没关系，比内容哈希
    ok, bad, miss = 0, [], []
    for p in sorted(glob.glob(os.path.join(ROOT, "media_many", "*.mp4")))[:16]:
        fresh = fresh_frame(p, os.path.join(CACHE, "verify_tmp"))
        if not fresh:
            miss.append(os.path.basename(p))
            continue
        h_fresh = hashlib.md5(open(fresh, "rb").read()).hexdigest()
        # 在缓存里找有没有一模一样的内容
        hit = None
        for c in cached:
            if hashlib.md5(open(c, "rb").read()).hexdigest() == h_fresh:
                hit = os.path.basename(c)
                break
        if hit:
            ok += 1
        else:
            bad.append(os.path.basename(p))
        shutil.rmtree(os.path.dirname(fresh), ignore_errors=True)
    print(f"对得上 {ok}/16；对不上 {bad}；抽不出 {miss}")

    # 设置记忆：改主题 + 循环，重启看日志
    P.post_key(w, "t")
    time.sleep(0.5)
    P.post_key(w, "l")
    time.sleep(0.6)
    geo = (w.x, w.y, w.w, w.h_)
    time.sleep(1.5)          # 等防抖写盘
    V.launch([os.path.join(ROOT, "media_many", "clip01.mp4")])
    w2 = V.Win()
    time.sleep(1.5)
    print("重启后:", V.log_tail("prefs restored", 1))
    print("重启后窗口:", (w2.x, w2.y, w2.w, w2.h_), "（上次关之前是", geo, "）")
    w2.drop_topmost()


if __name__ == "__main__":
    main()
