#!/bin/bash
# 跑一次回归：杀掉旧进程 → 清日志 → 增量构建 → 带片启动 → 等 N 秒 → 打日志摘要
# 用法：bash tools/t_run.sh [等待秒数] [要打开的文件]
set -u
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
WAIT="${1:-10}"
FILE="${2:-$ROOT/media_test/ep1.mp4}"
# 相对路径会在 build/bin 里解析，直接变绝对路径（踩过一次：开了 0 项还以为媒体炸了）
case "$FILE" in
  /*) ;;
  *) FILE="$ROOT/$FILE" ;;
esac
FILE="$(cygpath -w "$FILE")"

powershell -NoProfile -Command "Stop-Process -Name prism -Force -ErrorAction SilentlyContinue" >/dev/null 2>&1
sleep 1
rm -f build/bin/volta_run.log
bash build.sh > /tmp/b.log 2>&1
grep -E "BUILD OK|error:" /tmp/b.log | head -10

export PATH="$ROOT/qt/6.10.2/mingw_64/bin:$PATH"
export QSG_RHI_BACKEND=opengl
cd build/bin
./prism.exe "$FILE" >/dev/null 2>&1 &
sleep "$WAIT"
cd "$ROOT"

LOG=build/bin/volta_run.log
echo "== loadfile ok: $(grep -c 'loadfile rc=0' $LOG)  warnings: $(grep -cE 'WARN|CRIT' $LOG) =="
echo "== events =="
grep -oE "mpv event [0-9]+" "$LOG" | sort | uniq -c
echo "== ended/advance =="
grep -E "playback ended|playIndex|queue finished" "$LOG" | tail -8
echo "== warns =="
grep -E "WARN|CRIT" "$LOG" | head -6
