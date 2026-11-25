#!/bin/bash
# 启动 → 等待 → 读日志
cd "$(dirname "$0")"
bash run.sh > /dev/null 2>&1 &
sleep 8
python dbg.py 2>&1 | head -14
