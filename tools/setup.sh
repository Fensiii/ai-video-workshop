#!/usr/bin/env bash
# 一键准备云端容器的视频环境，只输出一行结果（省 token）。
# 用法：tools/setup.sh [字体目录]；之后用 tools/skpy 代替 python3 跑 skia 脚本（自动带 libEGL 路径）
FONT_DIR="${1:-$HOME/fonts}"
LOG=/tmp/setup_env.log
{
  pip install -q --disable-pip-version-check skia-python numpy scipy pillow
  mkdir -p "$HOME/.egl" "$FONT_DIR"
  EGL=$(ls /opt/pw-browsers/chromium-*/chrome-linux/libEGL.so 2>/dev/null | head -1)
  [ -n "$EGL" ] && ln -sf "$EGL" "$HOME/.egl/libEGL.so.1"
  if ! ls "$FONT_DIR"/NotoSerifSC_*.ttf >/dev/null 2>&1; then
    TMP=$(mktemp -d)
    for p in noto-serif-sc noto-sans-sc inter; do
      (cd "$TMP" && npm pack -q "@expo-google-fonts/$p" && tar xzf expo-google-fonts-$p-*.tgz && rm -f ./*.tgz)
      find "$TMP/package" -name '*.ttf' -exec cp {} "$FONT_DIR"/ \;
      rm -rf "$TMP/package"
    done
    rm -rf "$TMP"
  fi
} >"$LOG" 2>&1
export LD_LIBRARY_PATH="$HOME/.egl${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
if python3 -c 'import skia, scipy' 2>/dev/null; then S=ok; else S="FAIL(见 $LOG)"; fi
echo "setup: skia=$S fonts=$(ls "$FONT_DIR"/*.ttf 2>/dev/null | wc -l)个@$FONT_DIR 用 tools/skpy 运行"
