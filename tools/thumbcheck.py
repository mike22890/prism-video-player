"""验缩略图 + 滚动条：用 media_many（8 个文件）打开，等缩略图全出，抓图。"""
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
BIN = os.path.join(ROOT, "build", "bin")


def thumb_dir():
    # QStandardPaths::CacheLocation = %LOCALAPPDATA%/VOLTA/VOLTA
    import subprocess as sp
    base = os.path.join(os.environ["LOCALAPPDATA"], "VOLTA")
    hits = glob.glob(os.path.join(base, "**", "thumbs"), recursive=True)
    return hits[0] if hits else None


def main():
    V.launch([os.path.join(ROOT, "media_many", "clip01.mp4")])
    w = V.Win()
    P.post_click(w, 600, 16)
    time.sleep(1.0)

    # 等缩略图：队列 8 项，串行抽帧，给足时间
    td = thumb_dir()
    print("缩略图目录:", td)
    deadline = time.time() + 60
    last = -1
    while time.time() < deadline:
        n = len(glob.glob(os.path.join(td, "*.jpg"))) if td else 0
        if n != last:
            print(f"  已生成 {n} 张")
            last = n
        if n >= 8:
            break
        time.sleep(2)

    jpgs = sorted(glob.glob(os.path.join(td, "*.jpg"))) if td else []
    print(f"jpg 总数 {len(jpgs)}；fail 标记 {len(glob.glob(os.path.join(td, '*.fail')))}")
    for p in jpgs[:10]:
        with open(p, "rb") as f:
            print("   ", hashlib.md5(f.read()).hexdigest()[:8], os.path.basename(p))

    # 抓一张程序自己渲染的图（滚轮滚到底，看滚动条）
    before = set(glob.glob(os.path.join(BIN, "shot-*.png")))
    P.post_key(w, "f12")
    time.sleep(3.0)
    new = sorted(set(glob.glob(os.path.join(BIN, "shot-*.png"))) - before)
    if new:
        dst = os.path.join(V.SHOTS, "thumbs-scroll.png")
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
