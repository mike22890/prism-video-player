#!/bin/bash
# 启动 VOLTA：设 PATH、拷 plugin dll、跑
cd "$(dirname "$0")"
ROOT="$(pwd)"
export PATH="$ROOT/qt/6.10.2/mingw_64/bin:$PATH"

# libmpv 的渲染 API 目前只有 OpenGL 后端（MPV_RENDER_API_TYPE_OPENGL），
# 而 Qt6 默认走 D3D11 RHI —— 两者不能共享 GL 上下文，所以强制 Qt 用 OpenGL。
export QSG_RHI_BACKEND=opengl

# plugin dll 必须在 exe 旁边的 qml/ 目录里（Qt 靠 libraryPaths 找它）
if [ -f "$ROOT/build/src/volta_uiplugin.dll" ]; then
    mkdir -p "$ROOT/build/bin/qml"
    cp -f "$ROOT/build/src/volta_uiplugin.dll" "$ROOT/build/bin/qml/"
fi

cd "$ROOT/build/bin"
exec ./prism.exe
