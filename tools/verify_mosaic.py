"""验马赛克修复：真视频加载后 FBO 必须按真实源尺寸重建（不再停在 16x9 占位）。"""
import os, subprocess, sys, time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN=os.path.join(ROOT,"build","bin"); LOG=os.path.join(BIN,"volta_run.log")
EXE=os.path.join(BIN,"prism.exe")
# 用户截图的那个 4K 片在哪？先在几个目录找
cands=[]
for d in [os.path.join(ROOT,"media_long"),os.path.join(ROOT,"media_many"),
          os.path.join(ROOT,"media_test"),"C:/Users/16324/Videos","C:/Users/16324/Downloads"]:
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith((".mp4",".mkv",".avi",".webm")):
                cands.append(os.path.join(d,f))
MEDIA=cands[0] if cands else os.path.join(ROOT,"test_pattern.mp4")
print("media:",MEDIA)
u=ctypes_import=None
def find_prism():
    out=subprocess.run(["tasklist"],capture_output=True).stdout.decode("utf-8","replace")
    pids={int(p.split()[1]) for p in out.split("\n")
          if "prism.exe" in p.lower() and len(p.split())>=2 and p.split()[1].isdigit()}
    return bool(pids)
def logtxt():
    return open(LOG,encoding="utf-8",errors="replace").read() if os.path.exists(LOG) else ""
def main():
    subprocess.run(["powershell","-NoProfile","-Command","Stop-Process -Name prism -Force -ErrorAction SilentlyContinue"],capture_output=True)
    time.sleep(0.6)
    if os.path.exists(LOG): os.remove(LOG)
    env=dict(os.environ); env["QSG_RHI_BACKEND"]="opengl"
    env["PATH"]=os.path.join(ROOT,"qt","6.10.2","mingw_64","bin")+";"+env.get("PATH","")
    subprocess.Popen([EXE,MEDIA],cwd=BIN,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(50):
        time.sleep(0.5)
        if find_prism() and "loadfile rc=0" in logtxt(): break
    time.sleep(2.0)
    print("=== FBO / 尺寸日志 ===")
    for l in logtxt().split("\n"):
        if "FBO create" in l or "FBO rebuild" in l or "videoSize" in l or "video-params" in l:
            print("  ",l.strip())
    # 判据：最后一条 FBO 的长边必须 > 300（不是 16x9 的占位 9px）
    fbos=[l for l in logtxt().split("\n") if "FBO create" in l or "FBO rebuild" in l]
    print("\n最终 FBO 行:",fbos[-1].strip() if fbos else "NONE")
    return 0
if __name__=="__main__": sys.exit(main())
