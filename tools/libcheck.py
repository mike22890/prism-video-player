"""库页签：缩略图对不对得上 + 滚动条在不在。

用法：python tools/libcheck.py
"""
import glob
import hashlib
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
import poke as P

ROOT = V.ROOT
BIN = os.path.join(ROOT, "build", "bin")


def key_of(path):
    fi = os.stat(path)
    raw = f"{os.path.abspath(path)}|{fi.st_size}|{int(fi.st_mtime)}".encode()
    return hashlib.md5(raw).hexdigest()


def main():
    V.launch([os.path.join(ROOT, "media_many", "clip01.mp4")])
    w = V.Win()
    P.post_click(w, 600, 16)
    time.sleep(1.0)

    # 库页签（x≈55 命中过，这里扫一遍）
    for x in (45, 50, 55, 60, 65):
        P.post_click(w, x, 57)
        time.sleep(0.5)
        if "VOLTA mode=1" in V.log_text():
            print("切到库页签 x=", x)
            break
    time.sleep(20)      # 等抽帧（8 个文件串行）

    td = glob.glob(os.path.join(os.environ["LOCALAPPDATA"], "VOLTA", "**", "thumbs"),
                   recursive=True)[0]
    print(f"{'文件':12s} {'thumb':9s} 存在")
    seen = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "media_many", "*.mp4"))):
        k = key_of(p)
        jpg = os.path.join(td, k + ".jpg")
        ok = os.path.exists(jpg)
        h = ""
        if ok:
            with open(jpg, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()[:8]
        print(f"{os.path.basename(p):12s} {h or '-':9s} {'有' if ok else '缺'}")
        seen.setdefault(h, []).append(os.path.basename(p))
    print("按图分组:", {k: v for k, v in seen.items()})

    before = set(glob.glob(os.path.join(BIN, "shot-*.png")))
    P.post_key(w, "f12")
    time.sleep(3.0)
    new = sorted(set(glob.glob(os.path.join(BIN, "shot-*.png"))) - before)
    if new:
        dst = os.path.join(V.SHOTS, "lib-8items.png")
        for _ in range(20):
            try:
                shutil.copyfile(new[-1], dst)
                break
            except PermissionError:
                time.sleep(0.3)
        print("截图:", dst)
    w.drop_topmost()


if __name__ == "__main__":
    main()
