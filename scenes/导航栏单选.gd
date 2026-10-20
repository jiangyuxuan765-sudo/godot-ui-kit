extends TextureRect
## 导航栏(单选)：背景 TextureRect + 一个名为 Highlight 的选中框子节点 + 若干名为 Item0/Item1... 的图标子节点
## 点击某图标 → 选中框移到它后面、发 selected 信号。同时只有一个选中。
## 图标节点请手动摆好位置(水平均分)，脚本只负责移动选中框和响应点击。

signal selected(index: int)

## 初始选中项
@export var current: int = 0

var _highlight: Control
var _items: Array[Control] = []

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_highlight = get_node_or_null("Highlight")
	if _highlight:
		_highlight.mouse_filter = Control.MOUSE_FILTER_IGNORE
	# 收集 Item0, Item1, ... 顺序节点
	var i := 0
	while true:
		var n := get_node_or_null("Item%d" % i)
		if n == null:
			break
		var idx := i
		n.mouse_filter = Control.MOUSE_FILTER_STOP
		if n is BaseButton:
			(n as BaseButton).pressed.connect(func(): select(idx))
		else:
			n.gui_input.connect(func(e): _on_item_input(e, idx))
		_items.append(n)
		i += 1
	await get_tree().process_frame
	select(current)

func _on_item_input(event: InputEvent, idx: int) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		select(idx)

func select(index: int) -> void:
	if index < 0 or index >= _items.size():
		return
	current = index
	_move_highlight_to(_items[index])
	_apply_selected_tex(index)
	selected.emit(index)

## 可选：图标选中态换图。仅当 Item 设了 meta "normal_tex" / "selected_tex" 才生效。
## 选中项用 selected_tex，其余用 normal_tex。没设 meta 的项跳过（不影响别处复用）。
func _apply_selected_tex(index: int) -> void:
	for i in _items.size():
		var it := _items[i]
		if not it.has_meta("selected_tex") or not it.has_meta("normal_tex"):
			continue
		var tex: Texture2D = it.get_meta("selected_tex") if i == index else it.get_meta("normal_tex")
		if it is TextureRect:
			(it as TextureRect).texture = tex
		elif it is TextureButton:
			(it as TextureButton).texture_normal = tex

func _move_highlight_to(item: Control) -> void:
	if _highlight == null:
		return
	var item_center := item.position + item.size * 0.5
	_highlight.position = item_center - _highlight.size * 0.5
