"""音效重做 v2 —— 2026-11-26。
旧版是单频哔（一个正弦+ADP包络），廉价。新版每个主题一套音色配方：
  - 加法合成（基频+泛音列，各自包络）
  - 真实 ADSR（attack/decay/sustain/release）
  - 主题特有的调制（滑音/颤音/低通扫频/方波占空比）
  - 四类交互音 tap/hover/nav/toggle 音高与时长各异，sound 是切主题和弦
输出 44.1kHz 16bit 立体声 WAV，峰值归一化到 -3dBFS，无削波。纯标准库。
"""
import wave, struct, math, os, random

SR = 44100
ROOT = r'C:/Users/16324/Downloads/volta/themes'

# 每主题音色配方
# wave: sine|tri|saw|square:duty
# harm: 泛音强度列表（第1项是基频）
# env : (attack_s, decay_s, sustain_level, release_s)
# vib : (depth_hz, rate_hz) 颤音；slide: 起止频率倍率；lp: 低通截断随时间从 f0*lp0 -> f0*lp1
T = {
 'default': dict(f=520, wave='sine',   harm=[1.0,0.32,0.12,0.05],
                 env=(0.004,0.07,0.35,0.14), slide=(1.0,0.72), vib=(4,6), lp=None),
 'determination': dict(f=320, wave='triangle', harm=[1.0,0.22,0.42,0.10],
                 env=(0.003,0.10,0.30,0.20), slide=(1.15,0.85), vib=(2,4), lp=None),
 'synthwave': dict(f=300, wave='saw',   harm=[1.0,0.5,0.28,0.16,0.09],
                 env=(0.006,0.12,0.45,0.22), slide=(1.0,1.0), vib=(6,5), lp=(8.0,1.2)),
 'nes': dict(f=480, wave='square:0.25', harm=[1.0,0.0,0.33,0.0],
              env=(0.002,0.05,0.5,0.06), slide=(1.0,0.6), vib=(0,0), lp=None),
 'gameboy': dict(f=560, wave='square:0.125', harm=[1.0,0.0,0.25,0.0],
                 env=(0.002,0.05,0.5,0.06), slide=(1.0,0.8), vib=(0,0), lp=None),
 'terminal': dict(f=740, wave='square:0.5', harm=[1.0,0.28,0.0,0.15],
                  env=(0.001,0.03,0.2,0.04), slide=(1.0,0.9), vib=(0,0), lp=(10.0,3.0)),
 'winxp': dict(f=440, wave='sine', harm=[1.0,0.5,0.25,0.12,0.06],
               env=(0.008,0.18,0.4,0.35), slide=(1.0,1.0), vib=(3,3), lp=None),
}

# 交互音：时长 / 音高倍率 / 音量 / 泛音裁剪（越短越亮）
KIND = {
 'tap':    dict(dur=0.13, mul=1.0,  vol=0.62, hcut=5),
 'hover':  dict(dur=0.06, mul=1.5,  vol=0.34, hcut=3),
 'nav':    dict(dur=0.16, mul=0.85, vol=0.58, hcut=5),
 'toggle': dict(dur=0.22, mul=1.0,  vol=0.66, hcut=5),
 'sound':  dict(dur=0.55, mul=0.75, vol=0.60, hcut=5, chord=True),  # 切主题和弦
}

def osc(phase, wave):
    p = phase % (2*math.pi)
    u = p/(2*math.pi)
    if wave == 'sine':   return math.sin(p)
    if wave == 'tri':    return 2*abs(2*u-1)-1
    if wave == 'saw':    return 2*u-1
    if wave.startswith('square'):
        duty = float(wave.split(':')[1])
        return 1.0 if u < duty else -1.0
    return math.sin(p)

def adsr(t, dur, env):
    a,d,s,r = env
    if t < a:            return t/a
    if t < a+d:          return 1.0-(1.0-s)*((t-a)/d)
    if t < dur-r:        return s
    return max(0.0, s*((dur-t)/r))

def synth(theme, kind):
    tcfg = T[theme]; k = KIND[kind]
    dur = k['dur']; n = int(SR*dur)
    f0 = tcfg['f']*k['mul']
    slide0, slide1 = tcfg['slide']
    vibd, vibr = tcfg['vib']
    lp = tcfg['lp']
    # 和弦：切主题音叠三度五度
    chord_mult = [1.0, 1.26, 1.5] if k.get('chord') else [1.0]
    raw = []
    phase_acc = [0.0]*5
    for i in range(n):
        time = i/SR
        frac = time/dur
        # 滑音（指数）
        f = f0*(slide0*(slide1/slide0)**frac)
        # 颤音
        if vibd: f += vibd*math.sin(2*math.pi*vibr*time)
        # 低通：一阶 IIR 对噪声/锯齿粗糙感有用，这里用泛音幅度随截断频率衰减近似
        cut = None
        if lp:
            c0,c1 = lp
            cut = f*(c0+(c1-c0)*frac)
        s = 0.0
        hcut = k['hcut']
        for h,amp in enumerate(tcfg['harm'][:hcut], start=1):
            if amp == 0: continue
            a = amp
            if cut is not None:
                hf = f*h
                a *= 1.0/(1.0+(hf/cut)**2)   # 简单低通：高于截断的泛音衰减
            for ci,cm in enumerate(chord_mult):
                ph = 2*math.pi*f*cm*h*time
                s += a*osc(ph, tcfg['wave'])*(0.6 if ci else 1.0)/len(chord_mult)
        norm = sum(x for x in tcfg['harm'][:hcut] if x>0) or 1.0
        env = adsr(time, dur, tcfg['env'])
        tail = min(1.0, (n-i)/(SR*0.005))
        v = s/norm*env*tail*k['vol']
        raw.append(v)
    peak = max(abs(x) for x in raw) or 1.0
    gain = 0.70/peak   # 归一化到 -3dBFS
    # 立体声：轻微声像展宽（左右差 2% 采样延迟，模拟空间感，不糊）
    d = max(1, int(SR*0.0009))
    frames = []
    for i,x in enumerate(raw):
        l = max(-1,min(1,x*gain))
        r = max(-1,min(1,(raw[i-d] if i>=d else 0)*gain))
        frames.append(struct.pack('<hh', int(l*32767), int(r*32767)))
    return frames

def write_wav(path, frames):
    w = wave.open(path,'wb')
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(frames)); w.close()

for theme in T:
    d = os.path.join(ROOT, theme)
    if not os.path.isdir(d):
        print('skip (no dir)', theme); continue
    for kind in KIND:
        p = os.path.join(d, kind+'.wav')
        write_wav(p, synth(theme, kind))
        print('synth', theme, kind, os.path.getsize(p))
print('ALL SFX v2 SYNTHED')
