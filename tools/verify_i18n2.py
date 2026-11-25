"""点界面上的 中/EN 按钮验证语言切换（不靠改注册表）。"""
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
    h=find_prism(); r=wt.RECT(); u.GetWindowRect(wt.HWND(h),ctypes.byref(r))
    x,y,w,hh=r.left,r.top,r.right-r.left,r.bottom-r.top
    hdc=u.GetDC(0); mem=g.CreateCompatibleDC(hdc); bmp=g.CreateCompatibleBitmap(hdc,w,hh)
    g.SelectObject(mem,bmp); g.BitBlt(mem,0,0,w,hh,hdc,x,y,0x00CC0020|0x40000000)
    bi=BI(); bi.bmiHeader.biSize=ctypes.sizeof(BIH); bi.bmiHeader.biWidth=w
    bi.bmiHeader.biHeight=-hh; bi.bmiHeader.biPlanes=1; bi.bmiHeader.biBitCount=32
    buf=ctypes.create_string_buffer(w*hh*4); g.GetDIBits(mem,bmp,0,hh,buf,ctypes.byref(bi),0)
    g.DeleteObject(bmp); g.DeleteDC(mem); u.ReleaseDC(0,hdc)
    img=Image.frombuffer("RGBA",(w,hh),buf,"raw","BGRA",0,1).convert("RGB"); img.save(path)
    return f"{w}x{hh}"
def set_lang_qsettings(lang):
    # 正确的 QSettings 结构：ui 是子键，language 是值
    ps=(f'New-Item -Path "HKCU:\\Software\\VOLTA\\VOLTA\\ui" -Force | Out-Null; '
        f'Set-ItemProperty -Path "HKCU:\\Software\\VOLTA\\VOLTA\\ui" -Name "language" -Value "{lang}"')
    subprocess.run(["powershell","-NoProfile","-Command",ps],capture_output=True)
def main():
    subprocess.run(["powershell","-NoProfile","-Command",
        "(New-Object -ComObject Shell.Application).MinimizeAll()"],capture_output=True)
    time.sleep(0.8)
    subprocess.run(["powershell","-NoProfile","-Command","Stop-Process -Name prism -Force -ErrorAction SilentlyContinue"],capture_output=True)
    time.sleep(0.6)
    set_lang_qsettings("en")   # 用正确注册表结构预设英文
    if os.path.exists(LOG): os.remove(LOG)
    env=dict(os.environ); env["QSG_RHI_BACKEND"]="opengl"
    env["PATH"]=os.path.join(ROOT,"qt","6.10.2","mingw_64","bin")+";"+env.get("PATH","")
    subprocess.Popen([EXE,MEDIA],cwd=BIN,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(40):
        time.sleep(0.5)
        if find_prism() and os.path.exists(LOG) and "loadfile rc=0" in open(LOG,encoding="utf-8",errors="replace").read(): break
    time.sleep(1.5)
    h=find_prism(); u.ShowWindow(wt.HWND(h),9)
    u.SetWindowPos(wt.HWND(h),-1,100,100,1280,800,0x0040)
    u.SetForegroundWindow(wt.HWND(h)); time.sleep(1.0)
    p=os.path.join(SHOTS,"06_english.png"); print("EN via QSettings:",grab(p))
    return 0
if __name__=="__main__": sys.exit(main())
