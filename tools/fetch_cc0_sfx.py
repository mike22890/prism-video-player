"""下载 Kenney Interface CC0 音效（GitHub raw 镜像，官方直链 403）并转 44.1k wav。
来源：https://github.com/hipdiscovery/Free-Sound-Effects (CC0-1.0, catalog 2026-10-20)
"""
import urllib.request, ssl, json, os, subprocess, sys

BASE = "https://raw.githubusercontent.com/hipdiscovery/Free-Sound-Effects/master/"
CACHE = r"C:\Users\16324\AppData\Local\hermes\cache\scratch\cc0_ogg"
OUT = r"C:\Users\16324\Downloads\volta\tools\_sfx_src"
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
cat = json.load(open(r"C:\Users\16324\Downloads\volta\tools\cc0_catalog.json", encoding="utf-8"))

# 每类挑 2-3 个候选（不同编号），给主题映射留选择空间
PICK = {
    'tap':    ['click_001', 'click_002', 'click_003'],
    'hover':  ['tick_001', 'tick_002', 'tick_003'],
    'nav':    ['select_001', 'switch_001', 'switch_002'],
    'toggle': ['switch_003', 'switch_004', 'toggle_001'],
    'sound':  ['bong_001', 'confirmation_001', 'pluck_001'],
}
# path 反查
bypath = {os.path.splitext(os.path.basename(s['path']))[0]: s['path'] for s in cat['sounds']}

ctx = ssl.create_default_context()
FF = "ffmpeg"
fetched = []
for kind, names in PICK.items():
    for nm in names:
        rel = bypath.get(nm)
        if not rel:
            print("SKIP no such sound", nm); continue
        ogg = os.path.join(CACHE, nm + ".ogg")
        if not os.path.exists(ogg):
            try:
                req = urllib.request.Request(BASE + rel, headers={'User-Agent': 'Mozilla/5.0'})
                data = urllib.request.urlopen(req, timeout=25, context=ctx).read()
                open(ogg, 'wb').write(data)
            except Exception as e:
                print("DL FAIL", nm, e); continue
        # ogg -> 44.1k mono wav
        wav = os.path.join(OUT, nm + ".wav")
        subprocess.run([FF, '-y', '-i', ogg, '-ar', '44100', '-ac', '1', '-c:a', 'pcm_s16le', wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(wav):
            fetched.append(wav)
            print("OK", kind, nm, os.path.getsize(wav))

json.dump(fetched, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
print("TOTAL", len(fetched))
