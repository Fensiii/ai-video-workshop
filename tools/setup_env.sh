#!/usr/bin/env bash
# 一次性准备云端容器的渲染环境（可重复执行，已有的会跳过）。
#   source tools/setup_env.sh          # 装依赖 + 字体 + skia 的 libEGL，并导出环境变量
# 之后：VIDEO_FONT_DIR 指向中文/数字字体，LD_LIBRARY_PATH 能让 skia-python 正常加载。
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="$REPO/.cache"
FONTS="$CACHE/fonts"
mkdir -p "$FONTS" "$CACHE/egl"

# 1. Python 依赖
python3 -c "import skia, scipy, numpy, PIL" 2>/dev/null || pip install -q skia-python scipy numpy pillow

# 2. skia-python 需要 libEGL.so.1：借用 Playwright 自带 Chromium 里的那份
if [ ! -e "$CACHE/egl/libEGL.so.1" ]; then
  EGL=$(ls /opt/pw-browsers/chromium-*/chrome-linux/libEGL.so 2>/dev/null | head -1)
  [ -n "$EGL" ] && ln -sf "$EGL" "$CACHE/egl/libEGL.so.1"
fi
CHROME_DIR=$(dirname "$(readlink -f "$CACHE/egl/libEGL.so.1" 2>/dev/null || echo /nonexistent/x)")
export LD_LIBRARY_PATH="$CACHE/egl:$CHROME_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# 3. 字体：Google Fonts 被墙，走 npm 上的 Expo Google Fonts 包（内含 TTF）
fetch_font_pkg() {  # $1=npm 包名  其余=要的 ttf 文件名
  local pkg=$1; shift
  local need=0
  for f in "$@"; do [ -f "$FONTS/$f" ] || need=1; done
  [ $need = 0 ] && return
  local url tmp
  url=$(npm view "$pkg" dist.tarball 2>/dev/null) || { echo "取不到 $pkg"; return; }
  tmp=$(mktemp -d)
  curl -sSL "$url" | tar xz -C "$tmp"
  for f in "$@"; do find "$tmp" -name "$f" -exec cp {} "$FONTS/" \; ; done
  rm -rf "$tmp"
}
fetch_font_pkg @expo-google-fonts/noto-serif-sc NotoSerifSC_700Bold.ttf NotoSerifSC_900Black.ttf
fetch_font_pkg @expo-google-fonts/noto-sans-sc NotoSansSC_400Regular.ttf NotoSansSC_500Medium.ttf NotoSansSC_700Bold.ttf
fetch_font_pkg @expo-google-fonts/inter Inter_100Thin.ttf Inter_200ExtraLight.ttf Inter_300Light.ttf \
  Inter_400Regular.ttf Inter_500Medium.ttf Inter_600SemiBold.ttf Inter_700Bold.ttf
export VIDEO_FONT_DIR="$FONTS"

python3 -c "import skia" 2>/dev/null && echo "skia OK" || echo "skia 仍无法加载，检查 LD_LIBRARY_PATH"
echo "字体目录: $VIDEO_FONT_DIR ($(ls "$FONTS" | wc -l) 个)"
