"""打包 Release 产物：从 build/bin 复制真实文件（含 LFS 二进制的实体），排除本地状态。
输出到 out/，不污染仓库（out/ 已在 .gitignore 默认排除）。
"""
import os, shutil, zipfile, hashlib
ROOT = r"C:\Users\16324\Downloads\volta"
SRC = os.path.join(ROOT, "build", "bin")
STAGE = os.path.join(ROOT, "out", "prism-win64-v1.0.0")
ZIP = os.path.join(ROOT, "out", "Prism-v1.0.0-win64.zip")
if os.path.exists(STAGE): shutil.rmtree(STAGE)
os.makedirs(STAGE, exist_ok=True)

# 本地状态/日志/截图一律不进包
BAD_EXT = ('.log', '.pid')
BAD_PREFIX = ('shot-', 'diag', 'ab_', 'volta_run')
copied = 0
for dp, dns, fns in os.walk(SRC):
    for fn in fns:
        if fn.endswith(BAD_EXT) or fn.startswith(BAD_PREFIX):
            continue
        rel = os.path.relpath(os.path.join(dp, fn), SRC)
        dst = os.path.join(STAGE, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(dp, fn), dst)
        copied += 1
print("copied files:", copied)

# 敏感/本地数据检查（技能铁律）
leaks = []
for dp, dns, fns in os.walk(STAGE):
    for fn in fns:
        low = fn.lower()
        if low.endswith(('.log', '.bak', '.env', '.pem', '.key', '.pid')) or low.startswith(('shot-', 'ab_')):
            leaks.append(os.path.relpath(os.path.join(dp, fn), STAGE))
print("LEAKS:", leaks if leaks else "NONE")
assert not leaks, "refuse to package: local state found"

# zip（deflate，二进制 DLL 本来就压不动，主要是文本资源获益）
os.makedirs(os.path.dirname(ZIP), exist_ok=True)
if os.path.exists(ZIP): os.remove(ZIP)
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for dp, dns, fns in os.walk(STAGE):
        for fn in fns:
            full = os.path.join(dp, fn)
            z.write(full, os.path.join("Prism-v1.0.0-win64", os.path.relpath(full, STAGE)))
h = hashlib.sha256()
with open(ZIP, 'rb') as f:
    for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
print("ZIP:", ZIP, os.path.getsize(ZIP), "bytes")
print("SHA256:", h.hexdigest())
