extends SceneTree

# 测试场景真渲染逐屏截图（shot_tmp.gd 的参数化版，套别由命令行传）。
#
# 用法（-- 之后的才是本脚本的参数）：
#   godot --headless --rendering-driver opengl3 -s tools/验收/截图.gd -- --套 义体裂界
#
# 两个不能省的坑：
#   1 必须 --rendering-driver opengl3。headless 默认的 dummy 驱动不出图，
#     get_texture().get_image() 拿到的是空白，存出来是纯色，验收还会「通过」。
#   2 翻屏步长必须用窗口高 get_root().size.y，不能用 ScrollContainer.size.y。
#     窗口比视口矮时按视口高翻会跳过中间几行，漏掉的组件不会有任何报错。

# 按套分目录。共用一个目录的话，SKIP_SHOT 沿用现有图时会静默拿到上一套的截图，
# 用本套的底色去判：皇室战争的深蓝底配星舰指令的靛蓝底，占比报 100%，而且这种
# 荒谬数字仍然「有结论」，比直接报错更难发现。
const 输出根 := "res://tools/验收/截图"


func _init() -> void:
	var 套 := ""
	var args := OS.get_cmdline_user_args()
	var i := 0
	while i < args.size():
		if args[i] == "--套" and i + 1 < args.size():
			套 = args[i + 1]
			i += 2
		else:
			i += 1
	if 套 == "":
		printerr("缺参数：--套 <套别名>，例如 --套 义体裂界")
		quit(2)
		return

	var 场景路径 := "res://scenes/theme测试-%s.tscn" % 套
	if not ResourceLoader.exists(场景路径):
		printerr("场景不存在：%s" % 场景路径)
		quit(2)
		return

	# 清掉上一轮的图，否则套别换了而旧图还在，验收会把两套的图混在一起统计。
	var 绝对输出 := ProjectSettings.globalize_path(输出根.path_join(套))
	DirAccess.make_dir_recursive_absolute(绝对输出)
	var d := DirAccess.open(绝对输出)
	if d != null:
		for f in d.get_files():
			if f.begins_with("shot_") and f.ends_with(".png"):
				d.remove(f)

	# Godot 会把项目目录里的 PNG 当资源导入，每次截图都生成一堆 .import 文件，
	# 污染 git diff。截图根目录下已有一个 .gdignore，它对整棵子树生效，
	# 所以这里不再往每个套别子目录里放——那只会多出一堆空文件。

	var root: Node = load(场景路径).instantiate()
	get_root().add_child(root)
	# Control.size 要等一帧才有值，刚 add_child 时全是 0。
	await process_frame
	await process_frame

	var sc := root.get_node_or_null("Scroll") as ScrollContainer
	var inner := root.get_node_or_null("Scroll/VBox") as Control
	if sc == null or inner == null:
		printerr("场景里找不到 Scroll / Scroll/VBox，本脚本假定测试场景是这个结构")
		quit(2)
		return

	var total: float = inner.size.y
	var 视口 : float = sc.size.y
	var win: float = float(get_root().size.y)
	if win <= 0.0:
		printerr("窗口高为 0，八成是加了 --headless（它会强制 dummy 驱动）")
		quit(2)
		return
	print("套别 %s，内容高 %.0f，视口高 %.0f，窗口高 %.0f" % [套, total, 视口, win])

	# scroll_vertical 的上限是 内容高 - 视口高，而画面只能看到窗口高那一截。
	# 所以窗口比视口矮时，最远只能看到 (内容高-视口高) + 窗口高 = 内容高 - (视口高-窗口高)，
	# 底部那 视口高-窗口高 像素永远截不到，且不会有任何报错。
	# 旧的 900 高窗口配 1500 视口就漏了尾部 600px，四套验收都没覆盖到。
	if win < 视口 - 1.0:
		printerr("★窗口高 %.0f 小于视口高 %.0f，底部 %.0f px 无法截到。"
			% [win, 视口, 视口 - win])
		printerr("  请用 --resolution <宽>x%d 起，使窗口不低于视口。" % int(视口))
		quit(2)
		return

	var 最大滚 : float = maxf(0.0, total - 视口)
	var k := 0
	var 滚 := 0.0
	while true:
		sc.scroll_vertical = int(round(滚))
		# 滚动后要多等几帧：滚动位置生效、重绘、纹理回读各占一帧，
		# 少等会截到上一屏的画面（表现为两张图几乎一样）。
		await process_frame
		await process_frame
		await process_frame
		var img := get_root().get_texture().get_image()
		var 文件 := 绝对输出.path_join("shot_%02d.png" % k)
		var err := img.save_png(文件)
		if err != OK:
			printerr("存图失败 %s，错误码 %d" % [文件, err])
			quit(1)
			return
		print("存图 shot_%02d.png  scroll=%d" % [k, sc.scroll_vertical])
		k += 1
		# 滚到底就收工。不判这个会在末尾重复截好几张同样的图（scroll 被钳位），
		# 而重复图会让「逐屏占比」多出几个雷同样本，把统计权重压歪。
		if 滚 >= 最大滚:
			break
		滚 = minf(滚 + 视口, 最大滚)

	print("共 %d 屏，输出目录 %s" % [k, 绝对输出])
	quit(0)
