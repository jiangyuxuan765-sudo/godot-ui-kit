# -*- coding: utf-8 -*-
"""截图层验收：逐屏内容占比 + 色相构成。

合并了原 check_shots.py 与 check_hue.py。两者读同一批截图、用同一套背景判定，
分成两个文件的结果是底色改了一处忘另一处，然后两个脚本对同一张图给出不同结论。

两项检查的分工：
  逐屏占比  抓「整屏空白」和「被某面板铺满」这两类硬故障
  色相构成  抓「配色定位与实际不符」，需要腐蚀，理由见下

为什么色相要腐蚀：每个组件都有 1.5–3px 描边和辉光轮廓，边缘像素数量远多于
填充面积。直接逐像素统计，描边色会把结论压偏——曾经出现过「主色是红，但统计
说冷色占 2.6 倍」，因为青色描边遍布全图而红色只在少数组件上大面积填充。
腐蚀半径 K=4 大于最粗描边、小于任何填充块，只留结构性色块。

用法：
  python3 检查截图.py --套 义体裂界                    # 读默认截图目录
  python3 检查截图.py --套 义体裂界 --图 /tmp/cyb      # 指定目录
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 套别配置
from 图像 import 读PNG, 取像素器, 背景判定器

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
截图根 = os.path.join(ROOT, "tools", "验收", "截图")

ap = argparse.ArgumentParser()
ap.add_argument("--套", required=True)
ap.add_argument("--图", default=None,
                help="截图所在目录，默认 tools/验收/截图/<套别>")
a = ap.parse_args()
cfg = 套别配置.取(a.套)

# 按套分目录。共用一个目录时，沿用现有图（SKIP_SHOT=1）会静默拿到上一套的截图，
# 再用本套底色去判——皇室战争的深蓝底配星舰指令的靛蓝底，占比报 100%，而这种
# 荒谬数字仍然「有结论」，比直接报错更难发现。
图目录 = a.图 or os.path.join(截图根, a.套)
paths = sorted(glob.glob(os.path.join(图目录, "shot_*.png")))
if not paths:
    提示 = "没有截图：%s/shot_*.png" % 图目录
    旧 = sorted(glob.glob(os.path.join(截图根, "shot_*.png")))
    if 旧:
        提示 += ("\n注意：%s 下有 %d 张不分套别的旧截图，它们不会被使用"
                 "（无法确认属于哪一套）。" % (截图根, len(旧)))
    提示 += "\n先出图：bash tools/验收/全量验收.sh %s" % a.套
    raise SystemExit(提示)

is_bg = 背景判定器(cfg["底色"])
STEP = 4
K = 4          # 腐蚀半径
HUE_STEP = 3

占比下限, 占比上限 = 4.0, 92.0

print("=== 截图层验收：%s ===" % a.套)
print("底色 rgb%s，截图 %d 张，来源 %s" % (cfg["底色"], len(paths), 图目录))
print()

问题 = []
warm = cool = grey = 0
line_warm = line_cool = 0

print("[1] 逐屏内容占比（%.1f%% ~ %.1f%%）" % (占比下限, 占比上限))
for path in paths:
    W, H, nch, rows = 读PNG(path)
    px = 取像素器(nch, rows)

    tot = ink = 0
    for y in range(0, H, STEP):
        for x in range(0, W, STEP):
            tot += 1
            if not is_bg(*px(x, y)):
                ink += 1
    ratio = 100.0 * ink / tot
    判 = "OK"
    if ratio < 占比下限:
        判 = "★内容过少（疑似空屏／控件没渲染出来）"
    elif ratio > 占比上限:
        判 = "★几乎铺满（疑似拉伸失控）"
    if 判 != "OK":
        问题.append("%s 占比 %.2f%%" % (os.path.basename(path), ratio))
    print("      %-14s %dx%d  非背景 %5.2f%%  %s"
          % (os.path.basename(path), W, H, ratio, 判))

    # 腐蚀色相统计，与占比统计共用这次解码
    for y in range(K, H - K, HUE_STEP):
        for x in range(K, W - K, HUE_STEP):
            r, g, b = px(x, y)
            if is_bg(r, g, b):
                continue
            solid = (not is_bg(*px(x - K, y)) and not is_bg(*px(x + K, y))
                     and not is_bg(*px(x, y - K)) and not is_bg(*px(x, y + K)))
            if r > b + 18:
                if solid:
                    warm += 1
                else:
                    line_warm += 1
            elif b > r + 18:
                if solid:
                    cool += 1
                else:
                    line_cool += 1
            elif solid:
                grey += 1

tt = warm + cool + grey or 1
lt = line_warm + line_cool or 1
print()
print("[2] 色相构成（腐蚀 K=%d 后的结构性色块）" % K)
print("      色块   暖(红/黄) %.1f%% ／ 冷(青/蓝) %.1f%% ／ 中性 %.1f%%"
      % (100.0 * warm / tt, 100.0 * cool / tt, 100.0 * grey / tt))
print("      细线   暖 %.1f%% ／ 冷 %.1f%%   <- 被排除的描边/辉光轮廓"
      % (100.0 * line_warm / lt, 100.0 * line_cool / lt))

期望暖 = cfg.get("暖色占优")
if 期望暖 is None:
    print("      本套未声明色相定位，跳过占优断言")
else:
    实际暖 = warm > cool
    if 实际暖 != 期望暖:
        问题.append("色相占优不符：期望%s占优，实际%s占优"
                    % ("暖" if 期望暖 else "冷", "暖" if 实际暖 else "冷"))
        print("      ★不符：本套定位为%s色主导，但色块层面%s色占优"
              % ("暖" if 期望暖 else "冷", "暖" if 实际暖 else "冷"))
    else:
        print("      符合本套定位（%s色主导）" % ("暖" if 期望暖 else "冷"))

print()
print("结论:", "截图层全部通过" if not 问题 else "★需处理 -> %s" % 问题)
sys.exit(1 if 问题 else 0)
