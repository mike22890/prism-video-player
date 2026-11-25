"""清场：杀掉所有 volta 实例，等它们真死透，再报还剩几个。"""
import subprocess
import time

subprocess.run(["powershell", "-NoProfile", "-Command",
                "Get-Process volta -ErrorAction SilentlyContinue | Stop-Process -Force"],
               capture_output=True)
for _ in range(20):
    time.sleep(0.3)
    out = subprocess.run(["tasklist"], capture_output=True).stdout.decode("utf-8", "replace")
    n = sum(1 for l in out.split("\n") if "prism.exe" in l.lower())
    if n == 0:
        print("clean")
        break
else:
    print("still running:", n)
