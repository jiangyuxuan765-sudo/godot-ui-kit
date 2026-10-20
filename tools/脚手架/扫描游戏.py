# -*- coding: utf-8 -*-
"""换肤前体检：静态扫描一个 Godot 项目的所有 .tscn，列出会挡住换肤的东西。

**这一步的产物是一份清单，不是一次改动。** 换肤失效最常见的原因不是 theme 配错，
而是节点上有 inline override 盖着它——theme 换了，界面纹丝不动，而且不报任何错。
所以先扫出来看清楚，再决定哪些改节点、哪些改 theme、哪些重出素材。

报六节，编号与输出一致：
  [1] theme_override_styles/*   .tscn 里节点自带 StyleBox，完全盖掉 theme 的同名项
  [2] 其它 theme_override       .tscn 里的字色/字号/常量
  [3] theme 引用点              哪些节点挂了 theme，挂的是哪套
  [4] texture = ExtResource()   直接指到某套的贴图，换 theme 时不会跟着走
  [5] 代码里的 override         .gd 里 add_theme_*_override 造的样式
  [6] TextureRect 尺寸对表      与某套的尺寸契约比横纵缩放比（需 --套）

硬拦路项是 [1]、[5] 的 StyleBox 部分和 [6]：前两者不清换肤就是无效的，
[6] 不等比就是被拉歪。[2][4] 是清单，要人过一遍，不是错。

**[5] 不能省。** 在「卡牌对战」项目上实测时，.tscn 报了 26 处而代码里造整张
牌面的 3 处 add_theme_stylebox_override 一处没报 —— 效果和 .tscn 里的完全一样，
但改场景文件不管用，必须改代码，所以更难找。

用法：
  # 扫描目标项目（不需要打开 Godot，纯文本解析）
  python3 tools/脚手架/扫描游戏.py --项目 /path/to/游戏项目

  # 顺带跟某套的尺寸契约对表
  python3 tools/脚手架/扫描游戏.py --项目 /path/to/游戏项目 --套 义体裂界

  # 只看某个子目录
  python3 tools/脚手架/扫描游戏.py --项目 /path/to/游戏 --子目录 ui

注意 [6] 只能对 .tscn 里**显式写了** offset 的节点。用 anchors 撑满父容器、或靠
Container 布局算出来的尺寸，静态读不到——那部分要等注入后跑 tools/验收/探针.gd
实测。本脚本把「读不到尺寸」的数量单独报出来，不当成通过。

[5] 的计数按**行**算，不按 key 算：`for 态 in [...]: add_theme_stylebox_override(态, ...)`
这种循环里的一行，实际造了四个态却只报 1 处。所以 [5] 的数字是下限，用来定位
文件和行，不要拿它当精确的 key 数。

跑过的项目：UI组件（21 场景 / 817 处贴图引用 / 1 处 inline StyleBox / 3 处不等比）、
卡牌对战（2 场景 / 26 处 inline StyleBox / 代码里 11 处 override）。正则解析覆盖
的是这两个项目的写法，别的项目可能有没见过的写法，第一次跑要人眼过一遍结论
是否讲得通，尤其是 [3] 报「没有 theme 引用点」时。
"""
import argparse
import collections
import json
import os
import re
import sys

_这里 = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_这里))

ap = argparse.ArgumentParser()
ap.add_argument("--项目", required=True, help="目标 Godot 项目根目录（含 project.godot）")
ap.add_argument("--套", help="要换上去的套别名，用于尺寸契约对表")
ap.add_argument("--子目录", help="只扫项目下这个子目录")
ap.add_argument("--详细", action="store_true", help="逐条列出全部命中，不做截断")
a = ap.parse_args()

项目 = os.path.abspath(a.项目)
if not os.path.exists(os.path.join(项目, "project.godot")):
    raise SystemExit("不像 Godot 项目（缺 project.godot）：%s" % 项目)

扫描根 = os.path.join(项目, a.子目录) if a.子目录 else 项目
if not os.path.isdir(扫描根):
    raise SystemExit("目录不存在：%s" % 扫描根)

契约 = None
if a.套:
    p = os.path.join(ROOT, "tools", "验收", "尺寸契约-%s.json" % a.套)
    if not os.path.exists(p):
        raise SystemExit("找不到契约 %s\n已有：%s" % (
            p, "、".join(sorted(
                f[5:-5] for f in os.listdir(os.path.join(ROOT, "tools", "验收"))
                if f.startswith("尺寸契约-")))))
    契约 = {k: (int(v[0]), int(v[1]))
            for k, v in json.load(open(p, encoding="utf-8")).items()}

tscns = []
gds = []
for dp, dn, fn in os.walk(扫描根):
    dn[:] = [x for x in dn if x not in (".godot", ".git", "android")]
    for f in fn:
        if f.endswith(".tscn"):
            tscns.append(os.path.join(dp, f))
        elif f.endswith(".gd"):
            gds.append(os.path.join(dp, f))
tscns.sort()
gds.sort()

print("=== 换肤前体检：%s ===" % 项目)
print("场景 %d 个，脚本 %d 个%s"
      % (len(tscns), len(gds), "（子目录 %s）" % a.子目录 if a.子目录 else ""))
if not tscns:
    raise SystemExit("没找到 .tscn")

# 节点块用 [node ... ] 分段。ext_resource 表用来把 ExtResource("id") 解回路径。
_节点头 = re.compile(r'name="([^"]*)"(?:\s+type="([^"]*)")?(?:\s+parent="([^"]*)")?')

样式override = []       # (场景, 节点路径, 类型, key)
其它override = collections.Counter()
其它明细 = []
theme引用 = collections.Counter()
贴图直引 = []           # (场景, 节点路径, 类型, 资源路径)
尺寸命中 = []           # (场景, 节点路径, 类型, 图名, 契约wh, 实测wh, 横纵缩放)
尺寸读不到 = []         # (场景, 节点路径, 类型, 图名)
尺寸对上 = 0            # 单独计数，不能用 len(贴图直引) 减出来：贴图直引含全部
                       # 类型（817 处），而尺寸只查 TextureRect，减出来的数没意义

for p in tscns:
    相对 = os.path.relpath(p, 项目)
    d = open(p, encoding="utf-8", errors="replace").read()

    # ext_resource id -> path
    ext = {}
    for m in re.finditer(r'\[ext_resource[^\]]*?path="([^"]+)"[^\]]*?id="([^"]+)"', d):
        ext[m.group(2)] = m.group(1)
    for m in re.finditer(r'\[ext_resource[^\]]*?id="([^"]+)"[^\]]*?path="([^"]+)"', d):
        ext.setdefault(m.group(1), m.group(2))

    for blk in re.split(r'^\[node ', d, flags=re.M)[1:]:
        头 = _节点头.match(blk)
        if not 头:
            continue
        名, 类型, 父 = 头.group(1), 头.group(2) or "(继承)", 头.group(3)
        路径 = ("%s/%s" % (父, 名)) if 父 and 父 != "." else 名

        for m in re.finditer(r'^theme_override_(\w+)/(\S+)\s*=', blk, re.M):
            组, key = m.group(1), m.group(2)
            if 组 == "styles":
                样式override.append((相对, 路径, 类型, key))
            else:
                其它override[组] += 1
                其它明细.append((相对, 路径, 类型, "%s/%s" % (组, key)))

        m = re.search(r'^theme = ExtResource\("([^"]+)"\)', blk, re.M)
        if m:
            theme引用[ext.get(m.group(1), "?" + m.group(1))] += 1

        # 贴图直引 + 尺寸对表
        for m in re.finditer(r'^(texture|texture_under|texture_progress|texture_over'
                             r'|texture_normal|texture_pressed|texture_hover|texture_disabled|icon)'
                             r' = ExtResource\("([^"]+)"\)', blk, re.M):
            资源 = ext.get(m.group(2))
            if 资源 is None:
                continue
            贴图直引.append((相对, 路径, 类型, 资源))
            # 只查 TextureRect。NinePatchRect 有九图保护，被拉伸是它的正常用法，
            # 拿等比判据去查它会把每个九图面板都报一遍（本项目自测时 ui拼入.tscn
            # 的 inventory 就这么被误报了）。九图真正的风险在 texture_margin 是否
            # 退化，那一条由 tools/验收/检查主题.py [2] 负责。
            if 契约 is None or 类型 != "TextureRect":
                continue
            图名 = os.path.basename(资源)
            图名 = re.sub(r'\.(svg|png)$', '', 图名)
            if 图名 not in 契约:
                continue
            ms = re.search(r'^offset_right = (-?[\d.]+)', blk, re.M)
            mb = re.search(r'^offset_bottom = (-?[\d.]+)', blk, re.M)
            ml = re.search(r'^offset_left = (-?[\d.]+)', blk, re.M)
            mt = re.search(r'^offset_top = (-?[\d.]+)', blk, re.M)
            if not (ms and mb):
                尺寸读不到.append((相对, 路径, 类型, 图名))
                continue
            w = float(ms.group(1)) - (float(ml.group(1)) if ml else 0.0)
            h = float(mb.group(1)) - (float(mt.group(1)) if mt else 0.0)
            cw, ch = 契约[图名]
            if w <= 0.0 or h <= 0.0:
                尺寸读不到.append((相对, 路径, 类型, 图名))
                continue
            # 判据必须与 tools/验收/探针.gd 一致：看横纵缩放比是否相等，不是看
            # 尺寸是否相等。图标有意放大（56x56 的图放到 120x120 的框）是等比的，
            # 视觉上完全正常。初版按「尺寸必须相等」判，报了 24 处，其中 23 处是
            # 这种等比放大的假警——判据比探针严，就会淹掉真问题。
            sx, sy = w / cw, h / ch
            if abs(sx - sy) > 0.02:
                尺寸命中.append((相对, 路径, 类型, 图名,
                             (cw, ch), (round(w), round(h)), (sx, sy)))
            else:
                尺寸对上 += 1


# --- 代码里的 override。**不扫这一节就会漏掉一整类拦路项。**
# 在「卡牌对战」项目上第一次实测时暴露的：那个项目的 .tscn 里报了 26 处，而
# 卡牌控件.gd 用 add_theme_stylebox_override 在代码里造了整张牌面，一处都没报。
# 代码里的 override 和 .tscn 里的效果完全一样 —— 一样盖掉 theme，一样不报错，
# 而且更难找（改场景文件不管用，得改代码）。
_代码override = re.compile(
    r'add_theme_(stylebox|color|font|font_size|constant)_override\s*\(\s*["\']([^"\']*)')
代码样式 = []      # (脚本, 行号, key)
代码其它 = []      # (脚本, 行号, 组, key)
for p in gds:
    相对 = os.path.relpath(p, 项目)
    for n, 行 in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
        # 跳过注释行：本项目自己的脚本注释里就提到了这个函数名，会被算进去
        if 行.lstrip().startswith("#"):
            continue
        for m in _代码override.finditer(行):
            组, key = m.group(1), m.group(2)
            if 组 == "stylebox":
                代码样式.append((相对, n, key))
            else:
                代码其它.append((相对, n, 组, key))


def 列出(条目, 上限=15):
    for x in (条目 if a.详细 else 条目[:上限]):
        print("      %s" % x)
    if not a.详细 and len(条目) > 上限:
        print("      …… 另 %d 条，加 --详细 看全部" % (len(条目) - 上限))


print()
print("[1] inline StyleBox override —— 换肤失效的头号原因  %s"
      % ("无" if not 样式override else "★%d 处" % len(样式override)))
if 样式override:
    print("      这些节点自带 StyleBox，会完全盖掉 theme 的同名项。换肤前必须删掉，")
    print("      否则 theme 换了界面纹丝不动，且不报任何错。")
    按场景 = collections.Counter(x[0] for x in 样式override)
    for 场景, n in 按场景.most_common(10):
        print("      %-52s %d 处" % (场景, n))
    if len(按场景) > 10:
        print("      …… 另 %d 个场景" % (len(按场景) - 10))
    print("      明细：")
    列出(["%s  %s (%s)  %s" % (s, np, t, k) for s, np, t, k in 样式override])

print()
print("[2] 其它 theme_override（字色/字号/常量）  %s"
      % ("无" if not 其它override else "%d 处" % sum(其它override.values())))
if 其它override:
    print("      %s" % "，".join("%s %d 处" % (k, v)
                                for k, v in 其它override.most_common()))
    print("      这些不一定要删——局部强调色往往是有意的。但换肤后字色可能和新")
    print("      底色撞（浅底白字看不见），要逐项过一遍。")
    列出(["%s  %s (%s)  %s" % (s, np, t, k) for s, np, t, k in 其它明细], 10)

print()
# 全局 theme 自己读 project.godot，别让人去 grep。
# 初版这里只解析 .tscn，于是「卡牌对战」换肤做完、theme 已经挂在
# gui/theme/custom 上了，这一节还在报「整个项目没有节点显式设 theme」——
# 结论与事实相反，比不报更糟。
全局theme = None
_pg = os.path.join(项目, "project.godot")
if os.path.exists(_pg):
    _m = re.search(r'^\s*theme/custom\s*=\s*"([^"]+)"',
                   open(_pg, encoding="utf-8", errors="replace").read(), re.M)
    if _m:
        全局theme = _m.group(1)

print("[3] theme 引用点  %s" % (
    "无" if not theme引用 and not 全局theme
    else "、".join(([("全局 1 个")] if 全局theme else [])
                   + ([("节点 %d 个" % sum(theme引用.values()))] if theme引用 else []))))
if 全局theme:
    print("      project.godot  gui/theme/custom = %s" % 全局theme)
    print("      （全局默认 theme：所有 Control 都继承它，不用逐个节点挂）")
for 路径, n in theme引用.most_common():
    print("      %-56s %d 个节点" % (路径, n))
if not theme引用 and not 全局theme:
    print("      整个项目既没有节点挂 theme，project.godot 里也没有")
    print("      gui/theme/custom —— 换肤还没开始做，或者 theme 没接上。")

print()
print("[4] 直接引用贴图的节点  %s" % ("无" if not 贴图直引 else "%d 处" % len(贴图直引)))
if 贴图直引:
    按目录 = collections.Counter(os.path.dirname(x[3]) for x in 贴图直引)
    print("      按素材目录分布（换 theme 时这些引用不会跟着走，要逐个改）：")
    for 目录, n in 按目录.most_common(12):
        print("      %-56s %d 处" % (目录, n))
    if len(按目录) > 12:
        print("      …… 另 %d 个目录" % (len(按目录) - 12))

print()
print("[5] 代码里的 theme override  %s"
      % ("无" if not (代码样式 or 代码其它)
         else "★StyleBox %d 处 + 其它 %d 处" % (len(代码样式), len(代码其它))))
if 代码样式:
    print("      ★代码里的 add_theme_stylebox_override 和 [1] 一样会盖掉 theme，")
    print("      而且更难找 —— 改场景文件不管用，必须改代码：")
    列出(["%s:%d  %s" % (f, n, k) for f, n, k in 代码样式])
if 代码其它:
    组计 = collections.Counter(x[2] for x in 代码其它)
    print("      其它（字色/字号/常量）：%s"
          % "，".join("%s %d 处" % (k, v) for k, v in 组计.most_common()))
    列出(["%s:%d  %s/%s" % (f, n, g, k) for f, n, g, k in 代码其它], 10)

if 契约 is not None:
    print()
    print("[6] TextureRect 尺寸对表（九图不查，理由见代码注释；契约 %s，%d 条）"
          % (a.套, len(契约)))
    print("      等比 %d 处，不等比 %d 处，静态读不到尺寸 %d 处"
          % (尺寸对上, len(尺寸命中), len(尺寸读不到)))
    if 尺寸命中:
        print("      ★横纵缩放不等比的（TextureRect 无九图保护，会被拉歪）：")
        列出(["%s  %s (%s)  %s 契约 %dx%d ← 场景 %dx%d，缩放 %.3f vs %.3f"
              % (s, np, t, g, c[0], c[1], r[0], r[1], k[0], k[1])
              for s, np, t, g, c, r, k in 尺寸命中])
    if 尺寸读不到:
        print("      靠 anchors/Container 算尺寸，静态读不到 %d 处 —— 这部分要等"
              % len(尺寸读不到))
        print("      注入后跑 tools/验收/探针.gd 实测，不能当成通过。")

print()
print("══════ 结论 ══════")
拦路 = len(样式override) + len(代码样式) + len(尺寸命中)
if 拦路 == 0:
    print("没有硬拦路项。[2][4][5] 仍要人过一遍：字色会不会和新底色撞、")
    print("贴图直引要逐个改到新套目录。")
else:
    print("★%d 处硬拦路项：场景里 StyleBox %d 处 + 代码里 StyleBox %d 处 "
          "+ 尺寸不等比 %d 处。"
          % (拦路, len(样式override), len(代码样式), len(尺寸命中)))
    print("先清 [1] 和 [5]（不清换肤就是无效的），再决定 [6] 是改节点尺寸还是重出素材。")
# 体检工具报告现状，不做通过/失败判定 —— 有 override 不等于有错，
# 只等于「这些地方换肤不会自动生效」。退出码一律 0，别让它卡住流水线。
sys.exit(0)
