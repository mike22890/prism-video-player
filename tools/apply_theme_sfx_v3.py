"""音效 v3：每个主题用完全不同的 Kenney CC0 采样集。
切换音(sound)用 7 个不同类别的标志性音，从根上解决「所有主题切换音一样」。
每主题 5 种交互音各用不同文件 + 主题化处理（变调/滤波/8bit量化）。
输出 44.1k 16bit 立体声 wav，峰值 -3dBFS。
"""
import wave, struct, os, subprocess, array

SRC = r"C:\Users\16324\Downloads\volta\tools\_sfx_src"
OUT = r"C:\Users\16324\Downloads\volta\themes"
FF = "ffmpeg"

# 每主题：5 种交互音各自用「不同类别、不同文件」的采样
# sound(切换音) 7 主题来自 7 个不同类别 —— 绝不再重复
THEME_MAP = {
 'default':       dict(tap='click_004',  hover='tick_004',   nav='select_005', toggle='switch_005', sound='glass_003'),
 'determination': dict(tap='drop_002',   hover='back_003',   nav='pluck_002',  toggle='switch_006', sound='bong_001'),
 'synthwave':     dict(tap='click_005',  hover='tick_002',   nav='select_006', toggle='toggle_003', sound='pluck_001'),
 'nes':           dict(tap='click_002',  hover='tick_001',   nav='select_007', toggle='toggle_004', sound='maximize_005'),
 'gameboy':       dict(tap='click_003',  hover='tick_004',   nav='select_008', toggle='switch_007', sound='open_003'),
 'terminal':      dict(tap='scratch_003',hover='scroll_002', nav='back_004',   toggle='switch_002', sound='error_002'),
 'winxp':         dict(tap='click_001',  hover='scroll_004', nav='select_003', toggle='toggle_002', sound='confirmation_004'),
}

# 主题音色处理（在各自采样基础上进一步拉开差异）
TIMBRE = {
 'default':       dict(pitch=1.00, lp=0,     hp=0,  bit=0),
 'determination': dict(pitch=0.76, lp=3400,  hp=0,  bit=0),
 'synthwave':     dict(pitch=1.16, lp=0,     hp=240, bit=0),
 'nes':           dict(pitch=1.32, lp=0,     hp=0,  bit=4),
 'gameboy':       dict(pitch=1.48, lp=6000,  hp=0,  bit=3),
 'terminal':      dict(pitch=1.08, lp=4800,  hp=380, bit=0),
 'winxp':         dict(pitch=0.94, lp=7200,  hp=0,  bit=0),
}

def process(src_wav, dst_wav, cfg):
    filters=[]
    if cfg['pitch']!=1.0:
        filters.append(f"asetrate=44100*{cfg['pitch']},aresample=44100")
    if cfg['lp']: filters.append(f"lowpass={cfg['lp']}")
    if cfg['hp']: filters.append(f"highpass={cfg['hp']}")
    af=",".join(filters) if filters else "anull"
    subprocess.run([FF,'-y','-i',src_wav,'-af',af,'-ar','44100','-ac','1','-c:a','pcm_s16le',dst_wav],
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if cfg['bit']:
        w=wave.open(dst_wav,'rb'); n=w.getnframes(); d=array.array('h'); d.frombytes(w.readframes(n)); w.close()
        levels=2**cfg['bit']; step=32768//levels
        qd=array.array('h',(max(-32768,min(32767,(x//step)*step+step//2)) for x in d))
        w=wave.open(dst_wav,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(qd.tobytes()); w.close()
    w=wave.open(dst_wav,'rb'); n=w.getnframes(); d=array.array('h'); d.frombytes(w.readframes(n)); w.close()
    peak=max((abs(x) for x in d),default=1) or 1
    gain=int(32767*0.71)/peak
    frames=bytearray()
    for x in d:
        v=int(max(-32768,min(32767,x*gain))); frames+=struct.pack('<hh',v,v)
    w=wave.open(dst_wav,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
    w.writeframes(bytes(frames)); w.close()

count=0
for theme, kinds in THEME_MAP.items():
    d=os.path.join(OUT,theme)
    if not os.path.isdir(d): print('skip',theme); continue
    for kind, base in kinds.items():
        src=os.path.join(SRC,base+'.wav')
        if not os.path.exists(src): print('MISSING SRC',src); continue
        process(src, os.path.join(d,kind+'.wav'), TIMBRE[theme])
        count+=1
print("TOTAL",count,"(35 expected)")
