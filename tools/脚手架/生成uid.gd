extends SceneTree

# 生成合法的 Godot 资源 uid（供 theme/.tscn 的自身 uid 用）。
#
# 用法：
#   godot --headless --path . -s tools/脚手架/生成uid.gd -- --个数 2
#
# 为什么不能手搓：uid 是 Godot 的 base-N 编码，只含小写字母数字。手写的串会被
# 判 invalid UID，加载时静默回退到文本路径——不报错、只在日志里留一行 WARNING。
# 第十一、十二套的场景就引用着 uid://cr11royaletheme 这类手搓串，断链潜伏了
# 两套主题才被验收的交叉引用对账查出来。
#
# 本脚本只负责生成。查重交给 新建套别.py / 派生主题.py，它们能 grep 全库。

func _init() -> void:
	var 个数 := 2
	var args := OS.get_cmdline_user_args()
	var i := 0
	while i < args.size():
		if args[i] == "--个数" and i + 1 < args.size():
			个数 = maxi(1, args[i + 1].to_int())
			i += 2
		else:
			i += 1
	for k in range(个数):
		print(ResourceUID.id_to_text(ResourceUID.create_id()))
	quit(0)
