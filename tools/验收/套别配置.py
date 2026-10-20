# -*- coding: utf-8 -*-
"""各套主题的验收参数集中表。

原先这些常量散在 derive.py / check_shots.py / check_hue.py 各自的文件头里，
每做一套就要改三个地方，且改漏了不会报错、只会静默按上一套的底色判背景。
集中到这里，验收脚本一律 `--套 义体裂界` 取值。

新增一套时在 SUITES 里加一条，字段含义：
  素材目录  UI/ 下的目录名，同时也是 SVG 文件所在处
  主题文件  theme/ 下的 .tres 文件名
  场景文件  scenes/ 下的 .tscn 文件名
  底色      一律填 None，由 取() 从场景的根 ColorRect 读真值（理由见 读场景底色）
  暖色占优  本套主色是否为暖色（红/橙/黄）。None = 不做色相占优断言
  亮底      组件贴图是否为浅色（决定字色该用墨色还是骨白），与场景底色无关
"""
import os
import re

_根 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUITES = {
    # 这是随 skill 分发的最小可运行包，只内置一套演示主题「深海泡泡」，
    # 用来跑通四层验收 / 给新套当派生源。要做新套：python3 tools/脚手架/新建套别.py
    # 会自动往这里加一条。完整历史套别在作者的完整库里，不在本包。
    "深海泡泡": {
        "素材目录": "深海泡泡",
        "主题文件": "第十七套-深海泡泡.tres",
        "场景文件": "theme测试-深海泡泡.tscn",
        "底色": None,          # 由 取() 从场景根 ColorRect 读实测值
        "暖色占优": False,
    },
    "云崖古笺": {
        "素材目录": "云崖古笺",
        "主题文件": "第十八套-云崖古笺.tres",
        "场景文件": "theme测试-云崖古笺.tscn",
        "底色": None,          # 由 取() 从场景根 ColorRect 读实测值
        "暖色占优": None,
    },
}


def 读场景底色(场景文件):
    """从测试场景的根 ColorRect 直接读底色，返回 (r, g, b) 0–255。

    为什么不信配置里手写的值：手抄两次两次错。「拓荒纪事」按风格名「旧纸」
    填了 (232,220,196)，实际场景底是深棕皮革 (103,81,60)，导致背景一个都判
    不出来、占比冲到 93% 误报拉伸失控；「皇室战争」填了紫黑 (26,20,46)，
    实际是深蓝 (11,33,60)。底色是场景里的一个字段，读它就行，别推测。
    """
    p = os.path.join(_根, "scenes", 场景文件)
    if not os.path.exists(p):
        return None
    d = open(p, encoding="utf-8").read()
    for blk in re.split(r'^\[node ', d, flags=re.M)[1:]:
        if not re.match(r'name="\w+" type="ColorRect"', blk):
            continue
        m = re.search(r'color = Color\(([\d.]+), ([\d.]+), ([\d.]+)', blk)
        if m:
            return tuple(round(float(m.group(i)) * 255) for i in (1, 2, 3))
    return None


def 取(名, 需底色=True):
    """需底色=False 用于**场景还不存在**的时候（派生前）。

    为什么要这个开关：派生主题.py 也要 取(目标套)，但它只用 素材目录 字段，
    而目标套的场景正是它要产出的东西 —— 场景还不在，读底色必然失败。
    原先无条件读底色，于是「登记完新套 → 派生」这条正常路径直接被自己的
    守卫拦死（第十五套开工时撞上）。
    **不能改成「读不到就返回 None」了事**：底色守卫保护的是后面三层的背景
    判定，手抄底色错过两次（拓荒纪事、皇室战争），每次都表现为背景一个都判
    不出来、占比冲到 93% 并误报拉伸失控。所以守卫保持严格，只给派生这一个
    明确的例外入口，且返回的 cfg 里 底色 仍是 None —— 谁拿它去判背景就会当场
    崩在 None 上，而不是静默按错值跑。
    """
    if 名 not in SUITES:
        raise SystemExit("未登记的套别：%s\n已登记：%s" % (名, "、".join(SUITES)))
    cfg = dict(SUITES[名])
    实测 = 读场景底色(cfg["场景文件"])
    if 实测 is not None:
        写的 = cfg.get("底色")
        if 写的 is not None and tuple(写的) != 实测:
            print("  [底色] %s 配置写 rgb%s，场景实测 rgb%s —— 用实测值"
                  % (名, tuple(写的), 实测))
        cfg["底色"] = 实测
    elif cfg.get("底色") is None:
        if not 需底色:
            return cfg          # 底色留 None，见上面的理由
        raise SystemExit("%s 的场景里找不到根 ColorRect，且配置没写底色" % 名)
    return cfg
