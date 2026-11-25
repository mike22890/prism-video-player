"""后处理：把过长的交互音截断 + 淡出防爆音。toggle<=220ms, sound<=500ms, 其余<=130ms。"""
import wave, array, struct, glob, os

LIMIT = {'toggle': 0.22, 'sound': 0.50, 'tap': 0.13, 'hover': 0.06, 'nav': 0.13}
for f in sorted(glob.glob(r"C:\Users\16324\Downloads\volta\themes\*\*.wav")):
    kind = os.path.splitext(os.path.basename(f))[0]
    w = wave.open(f, 'rb'); sr = w.getframerate(); n = w.getnframes()
    ch = w.getnchannels(); a = array.array('h'); a.frombytes(w.readframes(n)); w.close()
    keep = int(sr * LIMIT[kind])
    if n <= keep:
        continue
    a = a[:keep * ch]
    fade = int(sr * 0.025)           # 25ms 淡出
    for i in range(fade):
        k = (fade - i) / fade
        for c in range(ch):
            idx = (len(a) // ch - fade + i) * ch + c
            if idx < len(a):
                a[idx] = int(a[idx] * k)
    w = wave.open(f, 'wb'); w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(a.tobytes()); w.close()
    print("trim", os.path.basename(os.path.dirname(f)), kind, f"{keep/sr*1000:.0f}ms")
print("TRIM DONE")
