# -*- coding: utf-8 -*-
"""主题/场景层静态验收：把规范里能静态查的 ❌ 条目变成断言。

规范 5.x 攒了几十条踩坑，绝大多数当时是靠肉眼复查发现的。这里挑出「不跑
Godot 就能判定」的那批，逐条做成断言。判不了的（如字色在贴图上是否可见、
控件实际尺寸）留给截图层和探针，不在这里假装能查。

对应关系（方括号是本文件的检查号）：
  [1] ext_resource 必须全在 sub_resource 之前     规范 5.26 ❌（.tscn 会直接解析失败）
  [2] texture_margin 越界                        规范 5.25/三、（T+B ≥ 贴图高 → 九图退化）
  [3] 贴图引用全部存在且指向本套目录              派生残留（曾整套指向上一套）
  [4] 自身 uid 唯一、格式合法                     规范 5.26（手搓 uid 被判 invalid 回退文本路径）
  [5] 素材着落自查：每张图都被用到                规范 5.6b
  [6] HBoxContainer 子节点纵向拉伸                规范 5.26/5.27 ❌（两套都栽过）
  [7] 亮底套字色未改                              规范 5.27 ❌（骨白落浅纸上不可见）

用法：
  python3 检查主题.py --套 义体裂界
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 套别配置
from 图像 import 读PNG  # noqa: F401  (占位，保持模块依赖一致)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
本目录 = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--套", required=True)
a = ap.parse_args()
cfg = 套别配置.取(a.套)

tres_path = os.path.join(ROOT, "theme", cfg["主题文件"])
tscn_path = os.path.join(ROOT, "scenes", cfg["场景文件"])
for p in (tres_path, tscn_path):
    if not os.path.exists(p):
        raise SystemExit("找不到文件：%s" % p)
tres = open(tres_path, encoding="utf-8").read()
tscn = open(tscn_path, encoding="utf-8").read()

契约path = os.path.join(本目录, "尺寸契约-%s.json" % a.套)
契约 = {}
if os.path.exists(契约path):
    契约 = {k: [int(v[0]), int(v[1])]
            for k, v in json.load(open(契约path, encoding="utf-8")).items()}

print("=== 主题/场景层静态验收：%s ===" % a.套)
print("主题 %s" % cfg["主题文件"])
print("场景 %s" % cfg["场景文件"])
print()

问题 = []


def 记(号, 文):
    问题.append("[%d] %s" % (号, 文))
    print("      ❌ %s" % 文)


# ---- [1] ext_resource 必须全在 sub_resource 之前 ----
print("[1] ext_resource / sub_resource 顺序")
for 名, d in (("theme", tres), ("scene", tscn)):
    首个sub = None
    for m in re.finditer(r'^\[(ext_resource|sub_resource)', d, re.M):
        if m.group(1) == "sub_resource" and 首个sub is None:
            首个sub = m.start()
        elif m.group(1) == "ext_resource" and 首个sub is not None:
            行 = d[:m.start()].count("\n") + 1
            记(1, "%s 第 %d 行有 ext_resource 排在 sub_resource 之后"
               "（.tscn 会 Unknown tag 解析失败）" % (名, 行))
            break
if not 问题:
    print("      通过")

# ---- [2] texture_margin 越界 ----
# 九图把贴图切九块，四边 margin 是「不拉伸的保护区」。若 T+B ≥ 贴图高，
# 中心行就是 0 或负，九图完全退化：控件一拉高，整张图被当边框拉长。
print("[2] texture_margin 越界（T+B < 图高、L+R < 图宽）")
名到尺寸 = dict(契约)
# ext_resource id -> 素材名
id到名 = {}
for m in re.finditer(r'\[ext_resource type="Texture2D"[^\]]*?'
                     r'path="res://UI/[^/]+/([^"]+)\.svg"[^\]]*?id="([^"]+)"', tres):
    id到名[m.group(2)] = m.group(1)
越界 = 0
块 = re.split(r'^\[sub_resource ', tres, flags=re.M)[1:]
for blk in 块:
    mid = re.match(r'type="(\w+)" id="([^"]+)"', blk)
    if not mid or mid.group(1) != "StyleBoxTexture":
        continue
    sid = mid.group(2)
    mtex = re.search(r'texture = ExtResource\("([^"]+)"\)', blk)
    if not mtex:
        continue
    素材 = id到名.get(mtex.group(1))
    if 素材 is None or 素材 not in 名到尺寸:
        continue
    w, h = 名到尺寸[素材]

    def mg(边):
        m = re.search(r'texture_margin_%s = ([\d.]+)' % 边, blk)
        return float(m.group(1)) if m else 0.0
    L, T, R, B = mg("left"), mg("top"), mg("right"), mg("bottom")
    if T + B >= h:
        记(2, "%s（图 %s %dx%d）T%.0f+B%.0f=%.0f ≥ 图高 %d，中心行 %.0f px"
           % (sid, 素材, w, h, T, B, T + B, h, h - T - B))
        越界 += 1
    if L + R >= w:
        记(2, "%s（图 %s %dx%d）L%.0f+R%.0f=%.0f ≥ 图宽 %d，中心列 %.0f px"
           % (sid, 素材, w, h, L, R, L + R, w, w - L - R))
        越界 += 1
if not 名到尺寸:
    print("      跳过（没有尺寸契约，先跑 检查素材.py --写契约）")
elif 越界 == 0:
    print("      通过（%d 个 StyleBoxTexture 全部在界内）"
          % sum(1 for b in 块 if b.startswith('type="StyleBoxTexture"')))

# ---- [3] 贴图引用存在且指向本套 ----
print("[3] 贴图引用指向本套且文件存在")
本套目录 = cfg["素材目录"]
坏引用 = 0
for 名, d in (("theme", tres), ("scene", tscn)):
    for m in re.finditer(r'path="res://UI/([^/]+)/([^"]+\.svg)"', d):
        目录, 文件 = m.group(1), m.group(2)
        if 目录 != 本套目录:
            记(3, "%s 引用了别套素材：UI/%s/%s" % (名, 目录, 文件))
            坏引用 += 1
        elif not os.path.exists(os.path.join(ROOT, "UI", 目录, 文件)):
            记(3, "%s 引用的文件不存在：UI/%s/%s" % (名, 目录, 文件))
            坏引用 += 1
if 坏引用 == 0:
    print("      通过")

# ---- [4] 自身 uid 合法且不与他套相撞 ----
print("[4] 自身 uid 合法且全库唯一")
uid问题 = 0
自身uid = {}
# 用 search + 多行模式，不能用 match 锚文件开头：这几套的文件头有一段 ; 开头的
# 配色 token 说明注释排在 [gd_resource] 之前（Godot 照常加载，HEAD 版本就是这样），
# 用 match 会判成「头部没有 uid」而误报。
_头uid = re.compile(r'^\[gd_(?:resource|scene)[^\]]*?uid="(uid://[^"]+)"', re.M)

for 名, d, path in (("theme", tres, tres_path), ("scene", tscn, tscn_path)):
    m = _头uid.search(d)
    if not m:
        记(4, "%s 头部没有 uid" % 名)
        uid问题 += 1
        continue
    u = m.group(1)
    自身uid[path] = u
    # Godot 的 uid 是 base-N 编码，只含小写字母和数字。手搓的串（如带下划线、
    # 带数字前缀的自造名）会被判 invalid UID，静默回退到文本路径并报 WARNING。
    if not re.fullmatch(r'uid://[a-z0-9]+', u):
        记(4, "%s 的 uid 格式不合法：%s（须为 base-N，只含小写字母数字）" % (名, u))
        uid问题 += 1
# 全库撞 uid 扫描
全库 = {}
for pat in ("theme/*.tres", "scenes/*.tscn"):
    for p in glob.glob(os.path.join(ROOT, pat)):
        d = open(p, encoding="utf-8").read()
        m = _头uid.search(d)
        if m:
            全库.setdefault(m.group(1), []).append(os.path.basename(p))
for path, u in 自身uid.items():
    撞 = 全库.get(u, [])
    if len(撞) > 1:
        记(4, "uid %s 被多个文件共用：%s（派生时忘换自身 uid）" % (u, 撞))
        uid问题 += 1

# 交叉引用对账：场景引用 theme/脚本时同时写 uid 和 path，两者必须都对得上。
# uid 失效时 Godot 会静默回退到 path 并照常加载，不报错也不告警——皇室战争的
# 场景引用 uid://cr11royaletheme 而 theme 自身已是 uid://cu6h6pjgy0g8s，
# 断链一直没被发现。只查自身 uid 查不出这类问题。
文件到uid = {}
for pat in ("theme/*.tres", "scenes/*.tscn", "scenes/*.gd", "UI/*/*.svg"):
    for p in glob.glob(os.path.join(ROOT, pat)):
        rel = "res://" + os.path.relpath(p, ROOT)
        d2 = None
        if p.endswith((".tres", ".tscn")):
            # 读 2000 字节而不是 400：文件头注释最长的一套占 54 行，
            # 400 字节根本读不到 [gd_resource] 那一行，uid 会被当成 None 而漏检。
            d2 = open(p, encoding="utf-8").read(2000)
            m = _头uid.search(d2)
            文件到uid[rel] = m.group(1) if m else None
        else:
            # .gd 的 uid 在同名 .uid 文件里；.svg 的在 .import 里。
            侧 = p + ".uid"
            if os.path.exists(侧):
                文件到uid[rel] = open(侧, encoding="utf-8").read().strip()
            elif os.path.exists(p + ".import"):
                m = re.search(r'uid="(uid://[^"]+)"',
                              open(p + ".import", encoding="utf-8").read())
                文件到uid[rel] = m.group(1) if m else None
for 名, d in (("theme", tres), ("scene", tscn)):
    for m in re.finditer(r'\[ext_resource [^\]]*?uid="(uid://[^"]+)"'
                         r'[^\]]*?path="([^"]+)"', d):
        引用uid, 引用path = m.group(1), m.group(2)
        真 = 文件到uid.get(引用path, "缺")
        if 真 == "缺":
            continue          # 目标不在扫描范围内（如引擎内置资源），跳过
        if 真 is None:
            continue          # 目标没有 uid 可比
        if 真 != 引用uid:
            记(4, "%s 引用 %s 写的是 %s，而该文件实际 uid 是 %s"
               "（Godot 会静默回退到 path，不报错）" % (名, 引用path, 引用uid, 真))
            uid问题 += 1

if uid问题 == 0:
    print("      通过（theme %s／scene %s，交叉引用全部对账）"
          % (自身uid.get(tres_path, "?"), 自身uid.get(tscn_path, "?")))

# ---- [5] 素材着落自查 ----
print("[5] 素材着落（每张 SVG 都被 theme 或场景用到）")
全部素材 = {os.path.basename(p)[:-4]
         for p in glob.glob(os.path.join(ROOT, "UI", 本套目录, "*.svg"))}
被用 = set()
for d in (tres, tscn):
    for m in re.finditer(r'path="res://UI/%s/([^"]+)\.svg"' % re.escape(本套目录), d):
        被用.add(m.group(1))
没用上 = sorted(全部素材 - 被用)
if 没用上:
    # 这不算硬错（有意备用的图允许存在），但历史上多次是「出了图忘了接」。
    print("      ⚠️ %d 张没被引用：%s" % (len(没用上), 没用上))
else:
    print("      通过（%d 张全部用到）" % len(全部素材))

# ---- [6] HBoxContainer 子节点纵向拉伸 ----
# HBox 会把子节点纵向拉到最高兄弟的高度。第十二、十三套都在这栽过：
# 竖进度条/卡牌框被旁边的高卡片拉高，图案被纵向拉扁。
print("[6] HBoxContainer 子节点纵向拉伸")
节点块 = re.split(r'^\[node ', tscn, flags=re.M)[1:]
节点 = []
for blk in 节点块:
    m = re.match(r'name="([^"]+)" type="([^"]+)"(?: parent="([^"]*)")?', blk)
    if not m:
        continue
    节点.append({"名": m.group(1), "类": m.group(2),
                "父": m.group(3) or "", "体": blk})
hbox路径 = set()
for n in 节点:
    if n["类"] == "HBoxContainer":
        hbox路径.add((n["父"] + "/" + n["名"]).lstrip("/") if n["父"] != "."
                    else n["名"])
# 关键是「比同排最高兄弟矮」才会被拉。只看「有固定高且没设 shrink」会把同高的
# 整排兄弟全报一遍（初版就报了 37 条假警，其中真问题只有 1 处）。
同排 = {}
for n in 节点:
    if n["父"] not in hbox路径 or n["名"].startswith("@"):
        # @ 开头是引擎给 ScrollContainer/PopupMenu 自动生成的内部节点，不是本套素材。
        continue
    m = re.search(r'custom_minimum_size = Vector2\(([\d.]+), ([\d.]+)\)', n["体"])
    高 = float(m.group(2)) if m else 0.0
    同排.setdefault(n["父"], []).append((n["名"], 高, n["体"]))
风险 = 0
for 父, 兄弟 in sorted(同排.items()):
    高度 = [h for _, h, _ in 兄弟 if h > 0]
    if len(高度) < 2:
        continue
    最高 = max(高度)
    for 名, 高, 体 in 兄弟:
        if 高 <= 0 or 高 >= 最高:
            continue
        if re.search(r'size_flags_vertical = (4|8|10)', 体):
            continue
        print("      ⚠️ %s/%s 固定高 %.0f < 同排最高 %.0f，会被 HBox 纵向拉伸"
              "（需 size_flags_vertical = 4）" % (父, 名, 高, 最高))
        风险 += 1
if 风险 == 0:
    print("      通过（%d 个 HBox）" % len(hbox路径))

# ---- [7] 亮底套字色 ----
print("[7] 亮底套近白字色（只提示，判不了对错）")
if not cfg.get("亮底"):
    print("      跳过（本套非亮底）")
else:
    # 这条只能提示，不能断言。三个理由：
    #  1 骨白字色配深色 font_outline_color 在浅底上是能看清的，是正当做法；
    #  2 同一个骨白落在深色鞍革按钮上本来就是对的（规范 5.27 原话）；
    #  3 要判「这个色落在那张贴图上可见吗」，得知道该控件用的是哪张图、图那块
    #    区域什么明度——静态读 .tres 做不到。
    # 初版把它写成断言，对已交付的拓荒纪事报了 28 处，其中 7 处是 modulate_color
    # （贴图着色乘数，压根不是字色），剩下的多数配了深描边。故降级为提示。
    近白 = r'Color\(0\.9\d+, 0\.9\d+, 0\.[89]\d+, 1\)'
    分组 = {}
    for m in re.finditer(r'^(\S*colors/font\S*)\s*=\s*(%s)' % 近白, tres, re.M):
        key = m.group(1)
        # font_outline_color 是描边色，近白描边配深字才是问题，与这里要看的相反。
        if "outline" in key:
            continue
        前缀 = key.split("/")[0]
        分组.setdefault(前缀, []).append(key)
    if not 分组:
        print("      未发现近白字色")
    else:
        无描边 = []
        for 前缀 in sorted(分组):
            有深描边 = re.search(
                r'^%s/colors/font_outline_color\s*=\s*Color\(0\.[0-4]'
                % re.escape(前缀), tres, re.M)
            if not 有深描边:
                无描边.append(前缀)
        print("      %d 个控件用近白字色：%s" % (len(分组), "、".join(sorted(分组))))
        if 无描边:
            print("      ⚠️ 其中 %d 个没有深色描边兜底，需人工看图确认可见性：%s"
                  % (len(无描边), "、".join(无描边)))
        else:
            print("      全部配了深色 font_outline_color，浅底上可读")

# ---- [8] 轨道/分隔线类 stylebox 短轴厚度塌成 0 ----
# 「战术锋线」注入 战术交火 后用户一眼看出「没有拖拽条，只有按钮」，而四层+五层
# 全绿。根因：StyleBoxTexture 的 content_margin 缺省（-1）时**逐边回退到
# texture_margin**；滑块/滚动条/分隔线这几张图只沿长轴做九宫格，短轴 texture_margin
# 天然是 0，于是 get_minimum_size() 短轴 = 0。
#
# 而 HSlider / ScrollBar / Separator 正是拿这个值当**轨道（控件）厚度**：
#   滑块  —— 槽和填充条 0 像素高，只剩走 icons/grabber 的拖动键（Texture2D 不经
#            stylebox），屏幕上就是一个悬空的小键，即用户看到的症状；
#   分隔线 —— 更彻底，整个控件厚度就是它，实测画 0/420 列，一个像素都没有。
#
# ★判据只覆盖这几个「厚度项」，不能推广到所有 min 短轴为 0 的 stylebox。
# 实测反证：第一套 ProgressBar 的 fill.min=(32,0)、第六套 HSlider 的
# grabber_area.min=(16,0)，渲染出来都是满格 —— ProgressBar 的填充高度另有来源。
# 一刀切会对每套报一堆假警，把真问题淹掉。
print("[8] 轨道/分隔线 stylebox 短轴厚度（缺省 content_margin 会塌成 0）")
厚度项 = {
    # 主题项 -> 哪一轴是"厚度"轴（'y' = 纵向厚度，'x' = 横向厚度）
    "HSlider/styles/slider": "y",
    "HSlider/styles/grabber_area": "y",
    "HSlider/styles/grabber_area_highlight": "y",
    "VSlider/styles/slider": "x",
    "VSlider/styles/grabber_area": "x",
    "VSlider/styles/grabber_area_highlight": "x",
    "HScrollBar/styles/scroll": "y",
    "HScrollBar/styles/grabber": "y",
    "HScrollBar/styles/grabber_highlight": "y",
    "HScrollBar/styles/grabber_pressed": "y",
    "VScrollBar/styles/scroll": "x",
    "VScrollBar/styles/grabber": "x",
    "VScrollBar/styles/grabber_highlight": "x",
    "VScrollBar/styles/grabber_pressed": "x",
    "HSeparator/styles/separator": "y",
    "VSeparator/styles/separator": "x",
}
# sub_resource id -> 块正文
块表 = {}
for blk in re.split(r"^\[sub_resource ", tres, flags=re.M)[1:]:
    m2 = re.match(r'type="(\w+)" id="([^"]+)"', blk)
    if m2 and m2.group(1) == "StyleBoxTexture":
        块表[m2.group(2)] = blk
塌 = 0
查过项 = 0
for 项, 轴 in sorted(厚度项.items()):
    m3 = re.search(r"^%s = SubResource\(\"([^\"]+)\"\)" % re.escape(项), tres, re.M)
    if not m3:
        continue
    blk = 块表.get(m3.group(1))
    if blk is None:
        continue  # 用的是 StyleBoxFlat/Empty 等，厚度不由贴图边距决定
    查过项 += 1
    边 = ("top", "bottom") if 轴 == "y" else ("left", "right")

    def 取(前缀, 边名, b=blk):
        mm = re.search(r"%s_margin_%s = ([\d.-]+)" % (前缀, 边名), b)
        return float(mm.group(1)) if mm else None
    c1, c2 = 取("content", 边[0]), 取("content", 边[1])
    有c = (c1 is not None and c1 > 0) or (c2 is not None and c2 > 0)
    t和 = (取("texture", 边[0]) or 0.0) + (取("texture", 边[1]) or 0.0)
    if not 有c and t和 == 0:
        记(8, "%s（%s）%s 轴厚度 = 0：content_margin 未写、texture_margin_%s/%s 也是 0，"
              "控件会画不出来（滑块只剩拖动键，分隔线一个像素都没有）"
           % (项, m3.group(1), 轴, 边[0], 边[1]))
        塌 += 1
if 查过项 == 0:
    print("      跳过（本套这些项都不是 StyleBoxTexture）")
elif 塌 == 0:
    print("      通过（%d 个厚度项短轴均非 0）" % 查过项)

print()
print("结论:", "静态层全部通过" if not 问题
      else "★静态层未过（%d 项）" % len(问题))
sys.exit(1 if 问题 else 0)
