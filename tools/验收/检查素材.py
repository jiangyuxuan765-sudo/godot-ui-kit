# -*- coding: utf-8 -*-
"""素材层验收：文件名对账 + 尺寸逐张对账 + SVG 合法性。

这是最靠前的闸门。素材尺寸错了不在这里拦住，要一路等到阶段 3 真渲染截图
才会以「控件变形」的形式暴露出来，那时已经隔了派生和 import 两道工序，
回溯成本高得多。

尺寸为什么必须逐张对账：九图保护（texture_margin）只对 NinePatchRect 和
StyleBoxTexture 有效，TextureRect 没有——它直接把贴图拉到控件尺寸。所以
凡是走 TextureRect 的素材，图的尺寸必须等于控件尺寸，差一像素就是拉伸。

用法：
  python3 检查素材.py --套 义体裂界
  python3 检查素材.py --套 义体裂界 --写契约     # 首次建契约或有意改版时
"""
import argparse
import glob
import json
import os
import re
import sys
import xml.dom.minidom as MD

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 套别配置

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ap = argparse.ArgumentParser()
ap.add_argument("--套", required=True)
ap.add_argument("--写契约", action="store_true",
                help="以当前素材尺寸覆写契约文件。仅在首次建套或有意改版时用。")
a = ap.parse_args()
# 需底色=False：本脚本只用 cfg["素材目录"]，从不碰底色。而阶段 1（出素材）跑在
# 阶段 2（派生场景）之前，此刻场景还不存在，无条件读底色会把「出素材 → 查素材」
# 这条正常路径拦死 —— 派生主题.py 撞过同一个守卫，第十六套开工又撞一次。
# 守卫本身保持严格（底色抄错过两次，见 套别配置.取 的注释），只开这个明确例外。
cfg = 套别配置.取(a.套, 需底色=False)

素材dir = os.path.join(ROOT, "UI", cfg["素材目录"])
契约path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "尺寸契约-%s.json" % a.套)

svgs = sorted(glob.glob(os.path.join(素材dir, "*.svg")))
if not svgs:
    raise SystemExit("素材目录没有 SVG：%s" % 素材dir)

print("=== 素材层验收：%s ===" % a.套)
print("素材目录 %s，共 %d 张" % (素材dir, len(svgs)))

# --- 1 SVG 合法性 + 读出三处尺寸 ---
实测 = {}
坏 = []
for p in svgs:
    名 = os.path.basename(p)[:-4]
    d = open(p, encoding="utf-8").read()
    try:
        MD.parseString(d.encode("utf-8"))
    except Exception as e:
        坏.append((名, "XML 非法: %s" % e))
        continue
    mw = re.search(r'<svg[^>]*\bwidth="(\d+(?:\.\d+)?)"', d)
    mh = re.search(r'<svg[^>]*\bheight="(\d+(?:\.\d+)?)"', d)
    mv = re.search(r'<svg[^>]*\bviewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"', d)
    if not (mw and mh and mv):
        坏.append((名, "根 svg 缺 width/height/viewBox"))
        continue
    w, h = float(mw.group(1)), float(mh.group(1))
    vw, vh = float(mv.group(1)), float(mv.group(2))
    # width/height 与 viewBox 不一致 = Godot 导入后按 width/height 栅格化但
    # 内容按 viewBox 布局，等于整张图被缩放，边框粗细会变。
    if (w, h) != (vw, vh):
        坏.append((名, "width/height (%g,%g) 与 viewBox (%g,%g) 不一致"
                   % (w, h, vw, vh)))
        continue
    实测[名] = [int(w), int(h)]

# --- 2 位图混入检测（本系列要求零位图） ---
位图 = []
for p in svgs:
    d = open(p, encoding="utf-8").read()
    if "<image" in d or "data:image" in d:
        位图.append(os.path.basename(p)[:-4])

# --- 3 写契约模式 ---
if a.写契约:
    if 坏:
        print("有 %d 张 SVG 不合法，拒绝写契约：" % len(坏))
        for 名, 因 in 坏:
            print("  ❌ %s —— %s" % (名, 因))
        sys.exit(1)
    with open(契约path, "w", encoding="utf-8") as f:
        json.dump(实测, f, ensure_ascii=False, sort_keys=True, indent=1)
    print("已写契约 %s（%d 条）" % (契约path, len(实测)))
    sys.exit(0)

# --- 4 对账 ---
if not os.path.exists(契约path):
    print("★ 没有契约文件 %s" % 契约path)
    print("  首次建套请先跑：python3 检查素材.py --套 %s --写契约" % a.套)
    sys.exit(1)
契约 = json.load(open(契约path, encoding="utf-8"))
# 旧契约里尺寸曾以字符串存过，统一成 int 再比，否则 "64" != 64 全员误报。
契约 = {k: [int(v[0]), int(v[1])] for k, v in 契约.items()}

缺 = sorted(set(契约) - set(实测))
多 = sorted(set(实测) - set(契约))
错 = [(k, 契约[k], 实测[k]) for k in sorted(set(契约) & set(实测))
      if 契约[k] != 实测[k]]

print()
print("[1] SVG 合法性       %s" % ("通过" if not 坏 else "★%d 张有问题" % len(坏)))
for 名, 因 in 坏:
    print("      ❌ %s —— %s" % (名, 因))
print("[2] 零位图           %s" % ("通过" if not 位图 else "★%d 张含位图: %s"
                                 % (len(位图), 位图)))
print("[3] 文件名对账       契约 %d ／ 实际 %d" % (len(契约), len(实测)))
for k in 缺:
    print("      ❌ 契约有而文件无: %s" % k)
for k in 多:
    print("      ❌ 文件有而契约无: %s" % k)
print("[4] 尺寸逐张对账     %s" % ("通过" if not 错 else "★%d 张不符" % len(错)))
for k, c, r in 错:
    print("      ❌ %s 契约 %dx%d，实际 %dx%d" % (k, c[0], c[1], r[0], r[1]))

问题 = bool(坏 or 位图 or 缺 or 多 or 错)
print()
print("结论:", "素材层全部通过" if not 问题 else "★素材层未过，不得进入派生阶段")
sys.exit(1 if 问题 else 0)
