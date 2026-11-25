#!/bin/bash
# 全新配置 + 构建（清 build 目录）
cd "$(dirname "$0")"
rm -rf build
bash build.sh
