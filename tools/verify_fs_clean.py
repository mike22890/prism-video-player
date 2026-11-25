"""干净全屏验证：启动就带 --fs（绕开收不到的键盘 Shortcut），抓真屏幕。
同时枚举可见顶层窗口，查清盖在播放器上面的是谁。
"""
import ctypes, ctypes.wintypes as wt, os, subprocess, sys, time
from PIL import Image
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN=os.path.join(ROOT,"build","bin"); SHOTS=os.path.join(ROOT,"shots","realscreen")
os.makedirs(SHOTS,exist_ok=True); LOG=os.path.join(BIN,"volta_run.log")
EXE=os.path.join(BIN,"prism.exe"); MEDIA=os.path.join(ROOT,"test_pattern.mp4")
u=ctypes.windll.user32; g=ctypes.windll.gdi32
try: u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception: u.SetProcessDPIAware()
class BIH(ctypes.Structure):
    _fields_=[("biSize",wt.DWORD),("biWidth",ctypes.c_long),("biHeight",ctypes.c_long),
              ("biPlanes",wt.WORD),("biBitCount",wt.WORD),("biCompression",wt.DWORD),
              ("biSizeImage",wt.DWORD),("biXPelsPerMeter",ctypes.c_long),
              ("biYPelsPerMeter",ctypes.c_long),("biClrUsed",wt.DWORD),("biClrImportant",wt.DWORD)]
class BI(ctypes.Structure): _fields_=[("bmiHeader",BIH),("bmiColors",wt.DWORD*3)]
def enum_windows():
    res=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool,wt.HWND,wt.LPARAM)
    def cb(h,_):
        if not u.IsWindowVisible(h): return True
        n=u.GetWindowTextLengthW(h)
        if n==0: return True
        b=ctypes.create_unicode_buffer(n+1); u.GetWindowTextW(h,b,n+1)
        cls=ctypes.create_unicode_buffer(128); u.GetClassNameW(h,cls,128)
        r=wt.RECT(); u.GetWindowRect(h,ctypes.byref(r))
        res.append((h,b.value,cls.value,(r.left,r.top,r.right-r.left,r.bottom-r.top)))
        return True
    u.EnumWindows(cb,0); return res
def find_prism():
    out=subprocess.run(["tasklist"],capture_output=True).stdout.decode("utf-8","replace")
    pids={int(p.split()[1]) for p in out.split("\n")
          if "prism.exe" in p.lower() and len(p.split())>=2 and p.split()[1].isdigit()}
    found=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool,wt.HWND,wt.LPARAM)
    def cb(h,_):
        pid=wt.DWORD(); u.GetWindowThreadProcessId(h,ctypes.byref(pid))
        if pid.value in pids:
            r=wt.RECT(); u.GetWindowRect(h,ctypes.byref(r))
            if (r.right-r.left)>400 and (r.bottom-r.top)>400: found.append(((r.right-r.left)*(r.bottom-r.top),h))
        return True
    u.EnumWindows(cb,0); found.sort(reverse=True); return found[0][1] if found else None
def grab(path):
    h=find_prism()
    if not h: return "NO WINDOW"
    r=wt.RECT(); u.GetWindowRect(wt.HWND(h),ctypes.byref(r))
    x,y,w,hh=r.left,r.top,r.right-r.left,r.bottom-r.top
    hdc=u.GetDC(0); mem=g.CreateCompatibleDC(hdc); bmp=g.CreateCompatibleBitmap(hdc,w,hh)
    g.SelectObject(mem,bmp); g.BitBlt(mem,0,0,w,hh,hdc,x,y,0x00CC0020|0x40000000)
    bi=BI(); bi.bmiHeader.biSize=ctypes.sizeof(BIH); bi.bmiHeader.biWidth=w
    bi.bmiHeader.biHeight=-hh; bi.bmiHeader.biPlanes=1; bi.bmiHeader.biBitCount=32
    buf=ctypes.create_string_buffer(w*hh*4); g.GetDIBits(mem,bmp,0,hh,buf,ctypes.byref(bi),0)
    g.DeleteObject(bmp); g.DeleteDC(mem); u.ReleaseDC(0,hdc)
    img=Image.frombuffer("RGBA",(w,hh),buf,"raw","BGRA",0,1).convert("RGB")
    img.save(path)
    px=list(img.resize((min(w,200),min(hh,120))).getdata())
    lum=sum((rr+gg+bb)/3 for rr,gg,bb in px)/len(px)
    return f"{w}x{hh} luma={lum:.1f} colors={len(img.resize((200,120)).getcolors(1000000) or [])}"
def main():
    print("=== 可见顶层窗口（启动前）===")
    for h,t,c,r in enum_windows():
        print(f"  [{c}] {t[:40]!r} rect={r}")
    subprocess.run(["powershell","-NoProfile","-Command","Stop-Process -Name prism -Force -ErrorAction SilentlyContinue"],capture_output=True)
    time.sleep(0.6)
    if os.path.exists(LOG): os.remove(LOG)
    env=dict(os.environ); env["QSG_RHI_BACKEND"]="opengl"
    env["PATH"]=os.path.join(ROOT,"qt","6.10.2","mingw_64","bin")+";"+env.get("PATH","")
    shotflag="--shot="+os.path.join(SHOTS,"diag_trigger.png")
    subprocess.Popen([EXE,MEDIA,"--fs",shotflag],cwd=BIN,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(40):
        time.sleep(0.5)
        if find_prism() and os.path.exists(LOG) and "loadfile rc=0" in open(LOG,encoding="utf-8",errors="replace").read(): break
    time.sleep(4.0)
    log=open(LOG,encoding="utf-8",errors="replace").read() if os.path.exists(LOG) else ""
    print("=== fs 日志 ===")
    for line in log.split("\n"):
        if "fullscreen" in line or "FBO create" in line or "context" in line.lower(): print("  ",line.strip())
    h=find_prism()
    r=wt.RECT(); u.GetWindowRect(wt.HWND(h),ctypes.byref(r)) if h else None
    print("=== 播放器窗口 rect ===", (r.left,r.top,r.right-r.left,r.bottom-r.top) if h else "none")
    p=os.path.join(SHOTS,"04_fs_direct.png")
    print("FS DIRECT:",grab(p))
    print("判据：luma 不能接近 0（纯黑），colors 要 >50（有真实画面）")
    return 0
if __name__=="__main__": sys.exit(main())
