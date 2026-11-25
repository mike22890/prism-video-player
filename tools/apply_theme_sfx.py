"""把 Kenney CC0 采样按主题做音色处理，生成 7 主题 × 5 交互音。
真实采样底子 + 主题化处理（变调/滤波/量化），不是单频哔声。
变调用 ffmpeg asetrate（变调不改时长），滤波用 lowpass/highpass，8bit 用 downsample+up。
输出 44.1k 16bit 立体声 wav，峰值归一 -3dBFS。
"""
import wave, struct, os, subprocess, math, array, json

SRC = r"C:\Users\16324\Downloads\volta\tools\_sfx_src"
OUT = r"C:\Users\16324\Downloads\volta\themes"
FF = "ffmpeg"

# 每个 kind 用哪个采样做底
BASE_SOUND = {
    'tap':    'click_001',
    'hover':  'tick_001',
    'nav':    'select_001',
    'toggle': 'switch_003',
    'sound':  'bong_001',
}

# 每主题音色处理：pitch 变调倍率, lp 低通Hz(0=不滤), hp 高通Hz, bit 8bit量化(0=不量化), vol 音量
THEME = {
    'default':       dict(pitch=1.00, lp=0,     hp=0,  bit=0,  vol=1.00),
    'determination': dict(pitch=0.78, lp=3800,  hp=0,  bit=0,  vol=1.05),
    'synthwave':     dict(pitch=1.18, lp=0,     hp=220, bit=0,  vol=1.00),
    'nes':           dict(pitch=1.30, lp=0,     hp=0,  bit=4,  vol=0.95),
    'gameboy':       dict(pitch=1.45, lp=6000,  hp=0,  bit=3,  vol=0.92),
    'terminal':      dict(pitch=1.10, lp=5000,  hp=400, bit=0,  vol=0.95),
    'winxp':         dict(pitch=0.92, lp=7000,  hp=0,  bit=0,  vol=1.00),
}

def process(src_wav, dst_wav, cfg):
    # ffmpeg filter chain: asetrate(变调) -> aresample(回44100) -> 滤波 -> 音量
    filters = []
    if cfg['pitch'] != 1.0:
        filters.append(f"asetrate=44100*{cfg['pitch']},aresample=44100")
    if cfg['lp']:
        filters.append(f"lowpass={cfg['lp']}")
    if cfg['hp']:
        filters.append(f"highpass={cfg['hp']}")
    if cfg['vol'] != 1.0:
        filters.append(f"volume={cfg['vol']}")
    af = ",".join(filters) if filters else "anull"
    subprocess.run([FF, '-y', '-i', src_wav, '-af', af, '-ar', '44100', '-ac', '1',
                    '-c:a', 'pcm_s16le', dst_wav],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # 8bit 量化（芯片感）：读回降位深再写回
    if cfg['bit']:
        w = wave.open(dst_wav, 'rb')
        n = w.getnframes(); d = array.array('h'); d.frombytes(w.readframes(n)); w.close()
        levels = 2 ** cfg['bit']
        step = 32768 // levels
        qd = array.array('h', (max(-32768, min(32767, (x // step) * step + step // 2)) for x in d))
        w = wave.open(dst_wav, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(qd.tobytes()); w.close()
    # 立体声化 + 峰值归一 -3dBFS
    w = wave.open(dst_wav, 'rb')
    n = w.getnframes(); d = array.array('h'); d.frombytes(w.readframes(n)); w.close()
    peak = max((abs(x) for x in d), default=1) or 1
    gain = int(32767 * 0.71) / peak
    frames = bytearray()
    for x in d:
        v = int(max(-32768, min(32767, x * gain)))
        frames += struct.pack('<hh', v, v)
    w = wave.open(dst_wav, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
    w.writeframes(bytes(frames)); w.close()

count = 0
for theme, cfg in THEME.items():
    d = os.path.join(OUT, theme)
    if not os.path.isdir(d):
        print('skip', theme); continue
    for kind, base_name in BASE_SOUND.items():
        src = os.path.join(SRC, base_name + '.wav')
        if not os.path.exists(src):
            print('MISSING SRC', src); continue
        dst = os.path.join(d, kind + '.wav')
        process(src, dst, cfg)
        count += 1
        print(f"{theme:14} {kind:7} {os.path.getsize(dst)}")
print("TOTAL", count)
