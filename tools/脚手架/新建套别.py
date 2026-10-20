# -*- coding: utf-8 -*-
"""把一套新主题登记进 套别配置.py，并预检命名冲突与 uid 占用。

为什么要脚本：登记是四层验收的总开关，`套别配置.py` 里少一个字段后面三层
全部跑不起来，而漏填不会报「你漏填了」，只会以别的形态爆出来——底色字段
写错过两次，两次都表现为「背景一个都判不出来、占比冲到 93% 并误报拉伸失控」。

用法：
  python3 tools/脚手架/新建套别.py --套 赛博霓虹 --序号 第十五套 --暖色占优 是
  python3 tools/脚手架/新建套别.py --套 赛博霓虹 --序号 第十五套 --暖色占优 否 --亮底
  python3 tools/脚手架/新建套别.py --套 赛博霓虹 --序号 第十五套 --暖色占优 未定

--暖色占优 未定 会写 None，即不做色相占优断言。风格没定死时先用它，
别为了让验收全绿而填一个假值。

只写配置和建目录，不碰素材/主题/场景。素材由生成脚本出，主题由 派生主题.py 派生。
"""
import argparse
import os
import re
import subprocess
import sys

_这里 = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_这里))
配置path = os.path.join(ROOT, "tools", "验收", "套别配置.py")

ap = argparse.ArgumentParser()
ap.add_argument("--套", required=True, help="套别名，同时用作 UI/ 下的素材目录名")
ap.add_argument("--序号", required=True, help="如 第十五套，用于主题文件名")
ap.add_argument("--暖色占优", required=True, choices=["是", "否", "未定"])
ap.add_argument("--亮底", action="store_true",
                help="组件贴图是浅色（决定字色该用墨色还是骨白），与场景底色无关")
a = ap.parse_args()

套 = a.套
主题文件 = "%s-%s.tres" % (a.序号, 套)
场景文件 = "theme测试-%s.tscn" % 套
素材dir = os.path.join(ROOT, "UI", 套)

print("=== 新建套别：%s ===" % 套)

# --- 1 名字冲突 ---
问题 = []
d = open(配置path, encoding="utf-8").read()
if '"%s": {' % 套 in d:
    问题.append("套别 %s 已在 套别配置.py 里登记过" % 套)
for 路径, 标 in ((素材dir, "素材目录"),
               (os.path.join(ROOT, "theme", 主题文件), "主题文件"),
               (os.path.join(ROOT, "scenes", 场景文件), "场景文件")):
    if os.path.exists(路径):
        # 素材目录允许已存在（生成脚本可能先跑过），主题/场景不允许被覆盖
        if 标 == "素材目录":
            print("  [提示] 素材目录已存在，沿用：%s" % 路径)
        else:
            问题.append("%s 已存在，不覆盖：%s" % (标, 路径))

# --- 2 序号是否已被占用（同一序号两套主题会让规范的编号对不上） ---
# 两处都要查：已派生出文件的看 theme/ 目录，只登记还没派生的看配置里的主题文件名。
# 只查目录会漏掉「登记了但还没派生」这个窗口期——新建两套之间正好都在这个窗口里。
for f in sorted(os.listdir(os.path.join(ROOT, "theme"))):
    if f.startswith(a.序号 + "-") and f != 主题文件:
        问题.append("序号 %s 已被 theme/%s 占用" % (a.序号, f))
for 登记名 in re.findall(r'"主题文件":\s*"([^"]+)"', d):
    if 登记名.startswith(a.序号 + "-") and 登记名 != 主题文件:
        问题.append("序号 %s 已被登记给 %s（尚未派生）" % (a.序号, 登记名))

if 问题:
    for x in 问题:
        print("  ❌ %s" % x)
    sys.exit(1)

# --- 3 生成两个 uid（theme 自身 + 场景自身）并全库查重 ---
GODOT = os.environ.get("GODOT", "/Applications/Godot.app/Contents/MacOS/Godot")
if not os.access(GODOT, os.X_OK):
    print("  ❌ 找不到 Godot：%s（可用 GODOT=<路径> 覆盖）" % GODOT)
    sys.exit(2)

已占 = set()
for 目录 in ("theme", "scenes"):
    for f in sorted(os.listdir(os.path.join(ROOT, 目录))):
        if f.endswith((".tres", ".tscn")):
            已占 |= set(re.findall(r'uid://[0-9a-z]+',
                                  open(os.path.join(ROOT, 目录, f),
                                       encoding="utf-8").read(2000)))

uid = []
for _ in range(6):          # 多要几个，撞了还有余量
    if len(uid) >= 2:
        break
    r = subprocess.run([GODOT, "--headless", "--path", ROOT,
                        "-s", "tools/脚手架/生成uid.gd", "--", "--个数", "4"],
                       capture_output=True, text=True)
    for 行 in r.stdout.splitlines():
        行 = 行.strip()
        if re.fullmatch(r'uid://[0-9a-z]+', 行) and 行 not in 已占 and 行 not in uid:
            uid.append(行)
if len(uid) < 2:
    print("  ❌ 生成 uid 失败，Godot 输出：\n%s" % r.stdout + r.stderr)
    sys.exit(1)
主题uid, 场景uid = uid[0], uid[1]

# --- 4 写配置。插在 SUITES 末尾那个 } 之前 ---
暖 = {"是": "True", "否": "False", "未定": "None"}[a.暖色占优]
条目 = ['    "%s": {' % 套,
        '        "素材目录": "%s",' % 套,
        '        "主题文件": "%s",' % 主题文件,
        '        "场景文件": "%s",' % 场景文件,
        '        "底色": None,          # 由 取() 从场景根 ColorRect 读实测值',
        '        "暖色占优": %s,' % 暖]
if a.亮底:
    条目.append('        "亮底": True,      # 组件贴图是浅色 -> 字色须为墨色')
条目.append('    },')

m = re.search(r'\n\}\n', d[d.index("SUITES = {"):])
if not m:
    print("  ❌ 没在 套别配置.py 里找到 SUITES 的收尾 }，请手工登记")
    sys.exit(1)
切点 = d.index("SUITES = {") + m.start() + 1
d = d[:切点] + "\n".join(条目) + "\n" + d[切点:]
open(配置path, "w", encoding="utf-8").write(d)

os.makedirs(素材dir, exist_ok=True)

print("  已登记进 %s" % os.path.relpath(配置path, ROOT))
print("  素材目录 %s" % os.path.relpath(素材dir, ROOT))
print("  主题文件 theme/%s（待派生）" % 主题文件)
print("  场景文件 scenes/%s（待派生）" % 场景文件)
print()
print("已生成两个未占用的 uid，派生时用：")
print("  主题自身 uid  %s" % 主题uid)
print("  场景自身 uid  %s" % 场景uid)
print()
print("下一步：")
print("  1 写 tools/生成%s素材.py 出素材" % 套)
print("  2 python3 tools/验收/检查素材.py --套 %s --写契约" % 套)
print("  3 python3 tools/脚手架/派生主题.py --源 <源套> --目标 %s \\" % 套)
print("        --主题uid %s --场景uid %s" % (主题uid, 场景uid))
sys.exit(0)
