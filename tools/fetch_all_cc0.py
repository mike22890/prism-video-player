"""下载全部 100 个 Kenney CC0 音效并转 wav（GitHub raw 镜像）。"""
import urllib.request, ssl, json, os, subprocess

BASE = "https://raw.githubusercontent.com/hipdiscovery/Free-Sound-Effects/master/"
CACHE = r"C:\Users\16324\AppData\Local\hermes\cache\scratch\cc0_ogg"
OUT = r"C:\Users\16324\Downloads\volta\tools\_sfx_src"
os.makedirs(CACHE, exist_ok=True); os.makedirs(OUT, exist_ok=True)
cat = json.load(open(r"C:\Users\16324\Downloads\volta\tools\cc0_catalog.json", encoding="utf-8"))
ctx = ssl.create_default_context()
ok = fail = 0
for s in cat['sounds']:
    nm = os.path.splitext(os.path.basename(s['path']))[0]
    ogg = os.path.join(CACHE, nm + '.ogg')
    if not os.path.exists(ogg):
        try:
            req = urllib.request.Request(BASE + s['path'], headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=25, context=ctx).read()
            open(ogg, 'wb').write(data)
        except Exception as e:
            print("DL FAIL", nm, e); fail += 1; continue
    wav = os.path.join(OUT, nm + '.wav')
    if not os.path.exists(wav):
        subprocess.run(["ffmpeg", '-y', '-i', ogg, '-ar', '44100', '-ac', '1', '-c:a', 'pcm_s16le', wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(wav):
        ok += 1
    else:
        fail += 1
print(f"DOWNLOADED {ok} wav, {fail} failed, total {len(cat['sounds'])}")
