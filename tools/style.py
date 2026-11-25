"""看一眼真实窗口样式位：WS_THICKFRAME 在不在（不在就别指望系统能拉伸）。"""
import ctypes, ctypes.wintypes as wt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V
h = V.find_window()
if not h: raise SystemExit("NO VOLTA WINDOW")
u = V.user32
u.SetProcessDPIAware()
st = u.GetWindowLongW(wt.HWND(h), -16)          # GWL_STYLE
ex = u.GetWindowLongW(wt.HWND(h), -20)          # GWL_EXSTYLE
names = {"WS_CAPTION":0x00C00000,"WS_THICKFRAME":0x00040000,"WS_MAXIMIZEBOX":0x00010000,
         "WS_MINIMIZEBOX":0x00020000,"WS_SYSMENU":0x00080000,"WS_POPUP":0x80000000,
         "WS_VISIBLE":0x10000000}
print(f"style=0x{st & 0xFFFFFFFF:08x}")
for k,v in names.items(): print(f"  {k:16s} {'ON' if st & v == v else 'off'}")
print(f"exstyle=0x{ex & 0xFFFFFFFF:08x}")
wp = (ctypes.c_byte*44)()
u.GetWindowPlacement(wt.HWND(h), ctypes.byref(wp))
show = int.from_bytes(bytes(wp[0:4]),'little')
print("showCmd:", show, "(1=normal 2=minimized 3=maximized)")
