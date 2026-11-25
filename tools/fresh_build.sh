#!/bin/bash
# 停掉正在跑的实例再构建 —— 否则链接器会撞上 exe 被占用（Permission denied）。
# 用法：bash tools/fresh_build.sh
set -u
cd "$(dirname "$0")/.."
powershell -NoProfile -Command "Stop-Process -Name prism -Force -ErrorAction SilentlyContinue" >/dev/null 2>&1
sleep 2
bash build.sh 2>&1 | grep -E "BUILD OK|BUILD FAILED|error:"
