"""重做主题音效：纯单频哔声 -> 谐波泛音 + ADSR 包络 + 尾音。
每个主题一套音色，4 种动作音 (tap/hover/nav/toggle)。
确定性音质提升，不依赖审美猜测。输出 44.1kHz 16bit 立体声。
"""
import wave, struct, math, os, random

SR = 44100
ROOT = r'C:/Users/16324/Downloads/volta/themes'

# 每主题音色: (基频, 谐波强度列表[1x,2x,3x,4x], 波形, 衰减, 音高滑动)
TIMBRES = {
    'default':      dict(f=660,  harm=[1.0,0.25,0.10,0.03], wave='sine',     dec=2.2, slide=0.0),
    'determination':dict(f=440,  harm=[1.0,0.18,0.30,0.05], wave='triangle', dec=2.6, slide=-0.15),
    'synthwave':    dict(f=330,  harm=[1.0,0.45,0.22,0.12], wave='saw',      dec=1.8, slide=0.1),
    'nes':          dict(f=523,  harm=[1.0,0.0,0.33,0.0],   wave='square25', dec=3.0, slide=0.0),
    'gameboy':      dict(f=587,  harm=[1.0,0.0,0.25,0.0],   wave='square12', dec=2.8, slide=0.0),
    'terminal':     dict(f=880,  harm=[1.0,0.30,0.0,0.15],  wave='square50', dec=4.0, slide=-0.2),
    'winxp':        dict(f=784,  harm=[1.0,0.35,0.15,0.05], wave='sine',     dec=2.0, slide=0.05),
}

# 每种动作的时长/音高倍率/音量
KINDS = {
    'tap':    dict(dur=0.11, mul=1.0,  vol=0.55, attack=0.004),
    'hover':  dict(dur=0.05, mul=1.6,  vol=0.28, attack=0.002),
    'nav':    dict(dur=0.13, mul=0.85, vol=0.5,  attack=0.005),
    'toggle': dict(dur=0.19, mul=1.0,  vol=0.6,  attack=0.008),
}


def osc(phase, wave):
    p = phase % (2*math.pi)
    if wave == 'sine':
        return math.sin(p)
    if wave == 'triangle':
        return 2*abs(2*(p/(2*math.pi)) - 1) - 1
    if wave == 'saw':
        return 2*(p/(2*math.pi)) - 1
    if wave.startswith('square'):
        duty = {'square12':0.125, 'square25':0.25, 'square50':0.5}[wave]
        return 1.0 if (p/(2*math.pi)) < duty else -1.0
    return math.sin(p)


def synth(theme, kind):
    t = TIMBRES[theme]; k = KINDS[kind]
    n = int(SR * k['dur'])
    f0 = t['f'] * k['mul']
    out = []
    for i in range(n):
        time = i / SR
        # 音高滑动（指数）
        f = f0 * (2 ** (t['slide'] * time / k['dur']))
        # ADSR: attack 快, decay 指数
        if time < k['attack']:
            env = time / k['attack']
        else:
            env = math.exp(-t['dec'] * (time - k['attack']) / k['dur'])
        # 尾部轻微淡出防爆音
        tail = min(1.0, (n - i) / (SR * 0.006))
        s = 0.0
        for h, amp in enumerate(t['harm'], start=1):
            if amp == 0: continue
            s += amp * osc(2*math.pi*f*h*time, t['wave'])
        norm = sum(t['harm']) or 1.0
        s = s / norm * env * tail * k['vol']
        v = int(max(-1, min(1, s)) * 26000)
        out.append((v, v))  # 立体声
    return out


def write_wav(path, frames):
    w = wave.open(path, 'wb')
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<hh', l, r) for l, r in frames))
    w.close()


for theme in TIMBRES:
    d = os.path.join(ROOT, theme)
    if not os.path.isdir(d): continue
    for kind in KINDS:
        p = os.path.join(d, kind + '.wav')
        write_wav(p, synth(theme, kind))
        print('synth', theme, kind, os.path.getsize(p))
print('ALL SFX SYNTHED')
