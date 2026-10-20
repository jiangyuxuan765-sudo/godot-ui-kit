extends SceneTree

# 几何探针：实测控件渲染后的尺寸，与素材尺寸对账，找非等比拉伸。
#
# 用法（headless 可以，本脚本不截图，不需要真渲染）：
#   godot --headless --path . -s tools/验收/探针.gd -- --套 义体裂界
#
# 三个不能省的坑：
#   1 Control.size 必须 add_child 之后 await process_frame 才有值，刚实例化全是 0。
#   2 要排除 @ 开头的节点：那是引擎给 ScrollContainer/PopupMenu 自动生成的内部
#     滚动条，贴图为空、尺寸被拉到 512/3000，算进来会报一堆假变形。
#   3 九图保护只对 NinePatchRect 和 StyleBoxTexture 有效，TextureRect 没有。
#     所以 TextureRect 的实测尺寸必须等于贴图尺寸，差一像素就是拉伸；
#     NinePatchRect 只要中心区不退化就允许拉伸，判定标准不同。

const 容差 := 1.0


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
		printerr("缺参数：--套 <套别名>")
		quit(2)
		return

	var 场景路径 := "res://scenes/theme测试-%s.tscn" % 套
	if not ResourceLoader.exists(场景路径):
		printerr("场景不存在：%s" % 场景路径)
		quit(2)
		return

	var root: Node = load(场景路径).instantiate()
	get_root().add_child(root)
	await process_frame
	await process_frame

	print("=== 几何探针：%s ===" % 套)

	var 拉伸 := []
	var 零尺寸 := []
	var 查过 := 0
	for n in _遍历(root):
		if n.name.begins_with("@"):
			continue
		if not (n is Control):
			continue
		var c := n as Control
		if c is TextureRect:
			var tr := c as TextureRect
			if tr.texture == null:
				continue
			查过 += 1
			var 图 := tr.texture.get_size()
			if c.size.x <= 0.0 or c.size.y <= 0.0:
				零尺寸.append("%s（%s）" % [c.name, c.get_class()])
				continue
			# expand_mode=IGNORE_SIZE(1) + stretch_mode 会主动缩放，这类是有意为之，
			# 但缩放比例必须等比，否则切角/角括会被拉歪。
			var sx: float = c.size.x / 图.x
			var sy: float = c.size.y / 图.y
			if absf(sx - sy) > 0.02:
				拉伸.append("%s 贴图 %dx%d → 实测 %.0fx%.0f，横纵缩放 %.3f vs %.3f 不等比"
					% [c.name, int(图.x), int(图.y), c.size.x, c.size.y, sx, sy])
		elif c is TextureProgressBar:
			var pb := c as TextureProgressBar
			var under := pb.texture_under
			if under == null:
				continue
			查过 += 1
			var 图2 := under.get_size()
			if not pb.nine_patch_stretch and (absf(c.size.x - 图2.x) > 容差
					or absf(c.size.y - 图2.y) > 容差):
				拉伸.append("%s 空槽图 %dx%d → 实测 %.0fx%.0f，未开 nine_patch_stretch 却被拉伸"
					% [c.name, int(图2.x), int(图2.y), c.size.x, c.size.y])

	print("[1] 贴图控件尺寸对账（查了 %d 个）" % 查过)
	if 拉伸.is_empty():
		print("      通过")
	else:
		for s in 拉伸:
			print("      ❌ %s" % s)
	if not 零尺寸.is_empty():
		print("      ⚠️ %d 个控件尺寸为 0（可能没进布局）：%s"
			% [零尺寸.size(), ", ".join(零尺寸)])

	# HBox 纵向拉伸实测：静态检查只能看 custom_minimum_size，这里看真实结果。
	print("[2] HBoxContainer 子节点纵向拉伸实测")
	var 被拉 := []
	for n in _遍历(root):
		if not (n is HBoxContainer):
			continue
		var 最高 := 0.0
		for ch in n.get_children():
			if ch is Control and not ch.name.begins_with("@"):
				最高 = maxf(最高, (ch as Control).size.y)
		for ch in n.get_children():
			if not (ch is Control) or ch.name.begins_with("@"):
				continue
			var cc := ch as Control
			# 基准必须是 get_combined_minimum_size()，不是 custom_minimum_size。
			# Button 的自然高还含字体行高和 content_margin：cms 写 82，组合最小其实
			# 是 86，拿 82 当基准会把整排没被拉伸的按钮全报一遍（初版就这么假报了 4 条）。
			var 自然 := cc.get_combined_minimum_size().y
			if 自然 > 0.0 and cc.size.y > 自然 + 容差:
				被拉.append("%s/%s 自然高 %.0f → 实测 %.0f（同排最高 %.0f）"
					% [n.name, cc.name, 自然, cc.size.y, 最高])
	if 被拉.is_empty():
		print("      通过")
	else:
		for s in 被拉:
			print("      ❌ %s" % s)

	# 视口宽自查：Label 不换行会把 VBox 最小宽撑爆，右侧内容被裁（规范 5.25）。
	print("[3] 内容宽度不超视口")
	var inner := root.get_node_or_null("Scroll/VBox/Margin/Inner") as Control
	var 宽超 := false
	if inner != null:
		var 需要: float = inner.get_combined_minimum_size().x
		var 可用: float = float(ProjectSettings.get_setting("display/window/size/viewport_width"))
		var margin := root.get_node_or_null("Scroll/VBox/Margin") as MarginContainer
		var 左右 := 0.0
		if margin != null:
			左右 = margin.get_theme_constant("margin_left") + margin.get_theme_constant("margin_right")
		print("      Inner 最小宽 %.0f，视口宽 %.0f，Margin 左右 %.0f"
			% [需要, 可用, 左右])
		if 需要 > 可用 - 左右 + 容差:
			print("      ❌ 超出 %.0f px，右侧内容会被裁（Label 加 autowrap_mode = 2）"
				% [需要 - (可用 - 左右)])
			宽超 = true
		else:
			print("      通过")
	else:
		print("      跳过（找不到 Scroll/VBox/Margin/Inner）")

	var 坏 := 拉伸.size() + 被拉.size() + (1 if 宽超 else 0)
	print("")
	print("结论: %s" % ("几何层全部通过" if 坏 == 0 else "★几何层未过（%d 项）" % 坏))
	quit(1 if 坏 > 0 else 0)


func _遍历(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out.append_array(_遍历(c))
	return out
