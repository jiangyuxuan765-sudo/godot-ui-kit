# -*- coding: utf-8 -*-
"""从已有套派生新套的 theme(.tres) 与测试场景(.tscn)。

_orig_derive.py 的泛化版（那份把源套、目标套、两个 uid、配色表全写死在文件里，
每做一套要改五处）。本脚本只做机械替换，几何值和字色不会自动跟着变——派生完
必须跑四层验收。

做四件事，一件都不能漏：
  1 ext_resource 的贴图 path 指向目标套目录，uid 从目标套的 .svg.import 现查
  2 theme / 场景各自的头部 uid 换成新的（不换就和被派生那套撞 uid）
  3 场景里对 theme 的 ext_resource（path + uid）指向新 theme
  4 配色替换（可选，--配色 传 JSON）

用法：
  python3 tools/脚手架/派生主题.py --源 星舰指令 --目标 义体裂界 \
      --主题uid uid://xxx --场景uid uid://yyy

  # 带配色替换
  python3 tools/脚手架/派生主题.py --源 星舰指令 --目标 赛博霓虹 \
      --主题uid uid://xxx --场景uid uid://yyy --配色 /tmp/配色.json

配色 JSON 是 {"旧色字面量": "新色字面量"}，键必须与文件里的写法逐字符一致：

  {"Color(0.027, 0.051, 0.082, 1)": "Color(0.05, 0.02, 0.08, 1)"}

**精度必须照抄文件里的实际写法。** 场景里写 Color(0.043, 0.129, 0.235, 1) 三位
小数，你用六位 0.043137 去匹配会静默失败——替换脚本照样报成功，背景却一直是
上一套的颜色。本脚本会为每条规则单独报命中次数，0 次的那条会被标出来。
"""
import argparse
import json
import os
import re
import sys

_这里 = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_这里))
sys.path.insert(0, os.path.join(ROOT, "tools", "验收"))
import 套别配置

ap = argparse.ArgumentParser()
ap.add_argument("--源", required=True, help="已登记的源套别名")
ap.add_argument("--目标", required=True, help="已登记的目标套别名")
ap.add_argument("--主题uid", required=True, help="新 theme 的自身 uid，由 生成uid.gd 出")
ap.add_argument("--场景uid", required=True, help="新场景的自身 uid")
ap.add_argument("--配色", help="配色替换表 JSON 路径，可省")
ap.add_argument("--覆盖", action="store_true", help="目标文件已存在时允许覆写")
a = ap.parse_args()

源 = 套别配置.取(a.源)
# 目标场景正是本脚本要产出的东西，此刻还不存在 -> 需底色=False。
# 本脚本只用 目标["素材目录"]，不碰底色（详见 套别配置.取 的注释）。
目标 = 套别配置.取(a.目标, 需底色=False) if a.目标 in 套别配置.SUITES else None
if 目标 is None:
    raise SystemExit("目标套 %s 还没登记。先跑：\n"
                     "  python3 tools/脚手架/新建套别.py --套 %s --序号 <第N套> "
                     "--暖色占优 <是|否|未定>" % (a.目标, a.目标))

for 标, u in (("主题uid", a.主题uid), ("场景uid", a.场景uid)):
    if not re.fullmatch(r'uid://[0-9a-z]+', u):
        raise SystemExit("%s 不是合法 uid：%s\n"
                         "uid 是 base-N 编码，只含小写字母数字。手搓的串会被判\n"
                         "invalid 后静默回退到文本路径，不报错。请用：\n"
                         "  godot --headless --path . -s tools/脚手架/生成uid.gd"
                         % (标, u))
if a.主题uid == a.场景uid:
    raise SystemExit("主题uid 和 场景uid 不能相同")

print("=== 派生 %s -> %s ===" % (a.源, a.目标))

# --- 目标套的贴图 uid 表（从 .svg.import 现查，不能猜） ---
目标素材dir = os.path.join(ROOT, "UI", 目标["素材目录"])
uid表 = {}
未导入 = []
for f in sorted(os.listdir(目标素材dir)):
    if f.endswith(".svg"):
        imp = os.path.join(目标素材dir, f + ".import")
        if not os.path.exists(imp):
            未导入.append(f)
            continue
        m = re.search(r'uid="(uid://[^"]+)"', open(imp, encoding="utf-8").read())
        if m:
            uid表[f[:-4]] = m.group(1)
        else:
            未导入.append(f)
if 未导入:
    print("  ❌ 目标套有 %d 张 SVG 没有可用的 .import：%s"
          % (len(未导入), 未导入[:5]))
    print("     先让 Godot 导入一遍：godot --headless --path . --import")
    sys.exit(1)
print("  目标套贴图 uid %d 个" % len(uid表))

# --- 配色表 ---
配色 = {}
if a.配色:
    配色 = json.load(open(a.配色, encoding="utf-8"))
    print("  配色规则 %d 条" % len(配色))

失败 = False
配色命中 = {k: 0 for k in 配色}


def 派生(源文件, 目标文件, 新uid, 标签, 子目录):
    global 失败
    src = os.path.join(ROOT, 子目录, 源文件)
    dst = os.path.join(ROOT, 子目录, 目标文件)
    if not os.path.exists(src):
        print("  ❌ 源文件不存在：%s" % src)
        失败 = True
        return
    if os.path.exists(dst) and not a.覆盖:
        print("  ❌ 目标已存在：%s（要覆写请加 --覆盖）" % dst)
        失败 = True
        return
    d = open(src, encoding="utf-8").read()

    # 1 贴图 path + uid。按文件名查目标套 uid，查不到的记下来
    缺 = []

    def 换贴图(m):
        头, 名 = m.group(1), m.group(2)
        if 名 not in uid表:
            缺.append(名)
            return m.group(0)
        return '%suid="%s" path="res://UI/%s/%s.svg"' % (
            头, uid表[名], 目标["素材目录"], 名)

    d = re.sub(r'(\[ext_resource type="Texture2D" )uid="uid://[^"]+" '
               r'path="res://UI/%s/([^"]+)\.svg"' % re.escape(源["素材目录"]),
               换贴图, d)

    # 2 自身 uid。用 re.M 的 search 而不是锚文件开头的 match：
    # 这几套的文件头有一段 ; 开头的配色 token 注释排在 [gd_resource] 之前。
    新d, n = re.subn(r'^\[%s([^\]]*?)uid="uid://[^"]+"' % 标签,
                     lambda m: '[%s%suid="%s"' % (标签, m.group(1), 新uid),
                     d, count=1, flags=re.M)
    if n == 0:
        print("  ❌ %s 头部没找到 [%s ... uid=...]，自身 uid 未换"
              % (目标文件, 标签))
        失败 = True
    d = 新d

    # 3 配色
    for 旧, 新 in 配色.items():
        c = d.count(旧)
        if c:
            配色命中[旧] += c
            d = d.replace(旧, 新)

    # 4 残留源目录引用
    残留 = sorted(set(re.findall(r'res://UI/%s/[^"]+' % re.escape(源["素材目录"]), d)))

    open(dst, "w", encoding="utf-8").write(d)
    print("  %s -> %s" % (源文件, 目标文件))
    print("     贴图引用 %d 处指向本套" % len(re.findall(
        r'res://UI/%s/' % re.escape(目标["素材目录"]), d)))
    if 缺:
        print("     ❌ 源套引用了 %d 张目标套没有的图：%s"
              % (len(set(缺)), sorted(set(缺))))
        失败 = True
    if 残留:
        print("     ❌ 残留源目录引用 %d 处：%s" % (len(残留), 残留[:5]))
        失败 = True


派生(源["主题文件"], 目标["主题文件"], a.主题uid, "gd_resource", "theme")
派生(源["场景文件"], 目标["场景文件"], a.场景uid, "gd_scene", "scenes")

# --- 场景里对 theme 的引用要指向新 theme（path 和 uid 都要改） ---
sp = os.path.join(ROOT, "scenes", 目标["场景文件"])
if os.path.exists(sp):
    d = open(sp, encoding="utf-8").read()
    前 = d
    d = d.replace('path="res://theme/%s"' % 源["主题文件"],
                  'path="res://theme/%s"' % 目标["主题文件"])
    d = re.sub(r'(\[ext_resource type="Theme" )uid="uid://[^"]+"',
               r'\1uid="%s"' % a.主题uid, d)
    open(sp, "w", encoding="utf-8").write(d)
    if d == 前:
        print("  ❌ 场景的 theme 引用没被改写，请手工检查 ext_resource type=\"Theme\"")
        失败 = True
    else:
        print("  场景的 theme 引用已指向 %s" % 目标["主题文件"])
    if 源["主题文件"] in d:
        print("  ❌ 场景里仍残留对源主题 %s 的引用" % 源["主题文件"])
        失败 = True

# --- 配色规则 0 命中要报出来（静默失败是这一步最大的坑） ---
if 配色:
    print()
    print("  配色替换命中数：")
    for k, v in 配色命中.items():
        标 = "" if v else "   <- ★0 次，八成是小数精度和文件里写的不一致"
        print("     %3d  %s%s" % (v, k, 标))
    if any(v == 0 for v in 配色命中.values()):
        失败 = True

print()
if 失败:
    print("结论: ★派生有问题，先修上面标 ❌ 的项")
    sys.exit(1)
print("结论: 派生完成。几何值和字色不会自动跟着变，接着必须做：")
print("  1 godot --headless --path . --import      # uid 进 uid_cache.bin")
print("  2 bash tools/验收/全量验收.sh %s" % a.目标)
if 目标.get("亮底"):
    print("  3 本套是亮底：字色要按具名 key 逐项改墨色，modulate_color 提亮值压回 1")
sys.exit(0)
