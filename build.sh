#!/bin/bash
# VOLTA —— 唯一的构建脚本。
# 构建完，build/bin/ 就是能双击运行的完整版本（Qt 运行时 + mpv.exe + 主题 + 着色器
# 全在 exe 旁边）。不再有 dev/dist 两套：只有这一份，改完跑它，交付也拷它。
set -e
cd "$(dirname "$0")"

export PATH="/c/Users/16324/scoop/apps/gcc/current/bin:$PATH"
ROOT="$(pwd)"
WROOT="$(cygpath -w "$ROOT")"
BIN="$ROOT/build/bin"

CMAKE="$ROOT/tools/cmake-3.31.6-windows-x86_64/bin/cmake.exe"
NINJA_W="$(cygpath -w "$ROOT/tools/ninja.exe")"
QT_W="$(cygpath -w "$ROOT/qt/6.10.2/mingw_64")"

export CMAKE_PREFIX_PATH="$QT_W"

# 构建前先杀掉正在跑的 exe —— 不杀链接器报 Permission denied（老坑）
powershell -NoProfile -Command "Stop-Process -Name prism -Force -ErrorAction SilentlyContinue; Stop-Process -Name prism -Force -ErrorAction SilentlyContinue" >/dev/null 2>&1 || true
sleep 0.6

if [ ! -d build ]; then
    "$CMAKE" -S "$WROOT" -B "$WROOT/build" -G Ninja \
        -DCMAKE_MAKE_PROGRAM="$NINJA_W" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH="$QT_W" > cfg.log 2>&1 || {
            echo "=== CONFIG FAILED ==="; tail -30 cfg.log; exit 1; }
fi

# 每次都重配（约1.6秒）：configure_file 生成的 app.rc（图标绝对路径）依赖 src/app.rc.in，
# 只增量构建会在模板变更后继续用旧的空图标路径。
"$CMAKE" -S "$WROOT" -B "$WROOT/build" > cfg.log 2>&1 || {
    echo "=== CONFIG FAILED ==="; tail -30 cfg.log; exit 1; }

"$CMAKE" --build "$WROOT/build" > build.log 2>&1 || {
    echo "=== BUILD FAILED ==="; grep -E "error:|Error" build.log | head -25; exit 1; }
echo "=== BUILD OK ==="

# ── 部署：把 exe 变成「双击就能跑」的完整版本 ──────────────────
# Qt 运行时 + QML 插件。--qmldir 必须是原生 Windows 路径，MSYS 的 /c/... 会让
# qmlimportscanner 吐无效 JSON（老坑）。
"$ROOT/qt/6.10.2/mingw_64/bin/windeployqt.exe" --release --no-translations \
    --qmldir "$(cygpath -w "$ROOT/src/qml")" \
    "$(cygpath -w "$BIN/prism.exe")" > deploy.log 2>&1 || {
        echo "=== DEPLOY FAILED ==="; tail -20 deploy.log; exit 1; }

# 缩略图抽帧用的独立 mpv.exe（vo=image），不是进程内 libmpv。
# findMpv() 会从 exe 同目录找；缺了它缩略图全静默跳过。
cp -f "$ROOT/mpvbin/mpv.exe" "$BIN/"
cp -f "$ROOT/mpvbin/d3dcompiler_43.dll" "$BIN/"

# 主题 + 着色器 + 字体，跟 exe 走（main.cpp / ThemeBridge 搜索根已含 exe 同目录）
cp -rf "$ROOT/themes" "$BIN/" 2>/dev/null || true
cp -rf "$ROOT/shaders" "$BIN/" 2>/dev/null || true
cp -rf "$ROOT/fonts" "$BIN/" 2>/dev/null || true

# 只有一个 exe：prism.exe。测试脚本已全部改用 prism.exe，不再拷副本。

echo "=== DEPLOY OK ==="
echo "唯一可运行版本：$BIN/prism.exe  （双击即跑，拷走整个 build/bin/ 即可交付）"
