# godot-ui-kit —— Godot UI 换肤套件（可分发包）

把这个包交给**任何一个会跑命令的 AI**（GPT、Codex、Copilot、Claude……），
它就能照着 `skill/SKILL.md` 从一张参考图做到「游戏换肤完成、四层验收全绿」，
效果和作者本机一致。

> 这套流程的发动机是**脚本**，不是说明书。说明书谁都能读，但脚本不在场，
> AI 跑到「跑验收」那步就只能干瞪眼。所以这个包 = **说明书 + 全部脚本 +
> 一个能跑的演示套**，缺一不可。

---

## 这个包里有什么

| 路径 | 作用 |
|---|---|
| `skill/SKILL.md` | 主说明书：五阶段工作流 + 每阶段的闸门。**AI 从这份读起** |
| `tools/脚手架/` | 建套 / 派生主题 / 扫描游戏 的脚本 |
| `tools/验收/` | 四层验收脚本 + 硬约束清单 + 套别配置 |
| `theme/规范.md` | 叙事体踩坑记录（按「第几套踩了什么坑」组织），出问题来查 |
| `scenes/` `theme/` `UI/深海泡泡/` | 一套**完整可跑**的演示主题，用来验证环境 + 当新套的派生源 |
| `冒烟.sh` | 5 分钟环境自检，**拿到包先跑它** |
| `project.godot` | Godot 项目壳，验收在这跑 |

## 你要先准备什么（只有三样）

1. **Python 3**（只用标准库，不用 pip 装任何东西）
2. **Godot 4 可执行文件**，设进环境变量 `GODOT`
3. **一台能开真窗口的机器**（截图层要真渲染；纯无头服务器跑不了最后一层）

## 三步上手

```bash
cd godot-ui-kit          # 进包
export GODOT=...         # 指向你的 Godot 4（见下）
bash 冒烟.sh             # 第一步：环境自检，全过才敢往下
```

`GODOT` 怎么设：

| 系统 | 命令 |
|---|---|
| macOS | `export GODOT="/Applications/Godot.app/Contents/MacOS/Godot"` |
| Windows | `set GODOT=C:\path\to\Godot.exe`（PowerShell 用 `$env:GODOT=...`） |
| Linux | `export GODOT=/usr/local/bin/godot` |

冒烟全过后，跑一条完整验收确认截图层也能跑：

```bash
bash tools/验收/全量验收.sh 深海泡泡
```

**这条全绿，环境就齐了。** 之后照 `skill/SKILL.md` 做新套即可。

---

## 给「分发这个包的人」

- **整个目录一起给**，别只发 `SKILL.md` —— 那等于只给了说明书没给发动机。
- 作者本机的完整库（含全部历史套别、各游戏项目）在别处；这个包是自洽的最小子集，
  新套可以基于演示套「深海泡泡」派生，不需要完整库。
- 换肤目标（游戏项目）在别人的电脑上，不在这个包里；`SKILL.md` 阶段 4 会教 AI
  怎么对目标项目体检、备份、注入。

## 给「用 Claude Code 的人」

`skill/` 目录下的 `SKILL.md` 同时是一份标准 Claude skill。想让 Claude Code 认得它，
软链过去即可（见仓库根 `README.md`）。其它 AI 不用管这节，直接读 `skill/SKILL.md` 的正文。
