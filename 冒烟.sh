#!/bin/bash
# 冒烟测试：5 分钟内验证这个包在你的环境里能跑。
# 任何 AI 拿到这个包，第一件事就是跑它 —— 全过才敢往下做换肤。
#
# 用法：
#   cd <本包目录>
#   bash 冒烟.sh
#
# 它验四件事，缺一都会在对应步停下并说清楚怎么补：
#   [0] python3 在不在
#   [1] Godot 4 可执行文件找没找到（没找到就告诉你怎么设 GODOT=）
#   [2] Godot 能不能对这个包跑 --import（这一步会生成 .godot/ 缓存，
#       后面一切验收都靠它；import 不过通常意味着包拷坏了或 Godot 版本太旧）
#   [3] 演示套「深海泡泡」的素材层 + 静态层验收全过
#
# 通过 ≠ 已经能出截图。截图层要开真窗口，冒烟不验；能在真窗口里跑
#   bash tools/验收/全量验收.sh 深海泡泡
# 才算环境齐。

set -u
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 2

echo "══════════ 冒烟测试：godot-ui-kit ══════════"
echo "包目录：$(pwd)"

echo ""
echo "── [0/4] python3 ──"
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ 找不到 python3。请先装 Python 3（验收脚本只用标准库，不用 pip）。"
  exit 1
fi
python3 --version
echo "✅ python3 在"

echo ""
echo "── [1/4] Godot 可执行文件 ──"
GODOT="${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
if [ ! -x "$GODOT" ]; then
  echo "❌ 找不到 Godot：$GODOT"
  echo ""
  echo "请下载 Godot 4（https://godotengine.org/download），然后用环境变量指过来："
  echo "  macOS:   export GODOT=\"/Applications/Godot.app/Contents/MacOS/Godot\""
  echo "  Windows: set GODOT=C:\\path\\to\\Godot.exe"
  echo "  Linux:   export GODOT=/usr/local/bin/godot"
  echo "设好再重跑本脚本。"
  exit 1
fi
"$GODOT" --version 2>/dev/null | head -1
echo "✅ Godot 在：$GODOT"

echo ""
echo "── [2/4] 对包跑 Godot --import（生成 .godot 缓存，约 1-2 分钟）──"
"$GODOT" --headless --path . --import >/dev/null 2>&1
if [ ! -d ".godot" ]; then
  echo "❌ import 后没有生成 .godot/ 目录，包可能拷坏了或 Godot 版本不对。"
  exit 1
fi
echo "✅ import 完成（.godot/ 已生成）"

echo ""
echo "── [3/4] 演示套「深海泡泡」素材层 + 静态层 ──"
python3 tools/验收/检查素材.py --套 深海泡泡 || { echo "❌ 素材层未过"; exit 1; }
python3 tools/验收/检查主题.py --套 深海泡泡 || { echo "❌ 静态层未过"; exit 1; }

echo ""
echo "══════════ 冒烟通过 ══════════"
echo "环境齐了：python3 + Godot + 包完整，无窗口验收两层全过。"
echo ""
echo "下一步（要能开真窗口的机器）："
echo "  bash tools/验收/全量验收.sh 深海泡泡"
echo "那条会把几何层和截图层也跑了 —— 全绿才算这套环境能做完整换肤。"
