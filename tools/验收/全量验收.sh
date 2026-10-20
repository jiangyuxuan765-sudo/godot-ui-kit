#!/bin/bash
# 一套主题的四层验收，按依赖顺序跑，前一层不过就不进下一层。
#
# 用法：
#   bash tools/验收/全量验收.sh 义体裂界
#   SKIP_SHOT=1 bash tools/验收/全量验收.sh 义体裂界   # 跳过重出截图（沿用现有图）
#
# 为什么要按顺序、且卡住就停：素材尺寸错了会一路带到最后，表现为「截图里控件
# 变形」，那时已隔了派生和 import 两道工序，回溯成本高得多。四套的经验是每层
# 都会出错，且错了不当场发现就会带到下一层。
#
# 注意：变量名一律用 ASCII。bash 不接受中文变量名（zsh 可以），用了会报
# 「command not found」+「unbound variable」，而且报错信息完全不提变量名的事。

set -u
suite="${1:-}"
if [ -z "$suite" ]; then
  echo "用法: bash tools/验收/全量验收.sh <套别名>"
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
acc="$root/tools/验收"
GODOT="${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
if [ ! -x "$GODOT" ]; then
  echo "找不到 Godot：$GODOT（可用 GODOT=<路径> 覆盖）"
  exit 2
fi

cd "$root" || exit 2
failed=0

banner() {
  echo ""
  echo "══════════ $1 ══════════"
}

banner "1/4 素材层（尺寸契约 + SVG 合法性 + 零位图）"
python3 "$acc/检查素材.py" --套 "$suite" || {
  echo ""
  echo "★素材层未过。素材尺寸错了会一路带到截图层才暴露，先修这里。"
  exit 1
}

banner "2/4 静态层（uid / texture_margin / 引用 / 顺序）"
python3 "$acc/检查主题.py" --套 "$suite" || {
  echo ""
  echo "★静态层未过，不进几何层。"
  exit 1
}

banner "3/4 几何层（实测控件尺寸，headless 探针）"
probe_out="$("$GODOT" --headless --path "$root" -s tools/验收/探针.gd \
  -- --套 "$suite" 2>&1)"
echo "$probe_out" | grep -vE "^Godot Engine|^OpenGL API|^$"
# 探针跑一次就够，输出存下来判定。管道里 grep 会吃掉退出码，所以按结论行判。
if echo "$probe_out" | grep -q "★几何层未过"; then
  echo ""
  echo "★几何层未过，不进截图层（变形的图截出来也是变形的）。"
  exit 1
fi

if [ "${SKIP_SHOT:-0}" != "1" ]; then
  banner "4/4 截图层 —— 先真渲染出图"
  # 必须真窗口：--headless 会强制 dummy 驱动，存出来是空白图，而验收还会「通过」。
  # 分辨率高度必须 ≥ ScrollContainer 视口高（1500），否则底部截不到且不报错。
  "$GODOT" --rendering-driver opengl3 --resolution 1280x1500 --position 0,0 \
    --path "$root" -s tools/验收/截图.gd -- --套 "$suite" 2>&1 \
    | grep -vE "^Godot Engine|^OpenGL API|^$"
else
  banner "4/4 截图层（SKIP_SHOT=1，沿用现有截图）"
fi

python3 "$acc/检查截图.py" --套 "$suite" || failed=1

echo ""
echo "══════════ 汇总 ══════════"
if [ "$failed" -eq 0 ]; then
  echo "四层全部通过：$suite"
else
  echo "★截图层有未过项（见上）。$suite"
fi
exit "$failed"
