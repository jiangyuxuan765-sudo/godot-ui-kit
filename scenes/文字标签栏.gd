extends TextureRect
## 文字 tab bar（单选）：背景 TextureRect + 名为 Highlight 的选中框子节点 + 若干名为 Item0/Item1... 的 Label。
## 点击某标签 → 选中框移到它后面、该标签文字变亮、其余变暗。任意时刻只有一个选中。
## Label 节点请手动摆好位置（水平均分），脚本只负责移动选中框、改文字色、发信号。

signal selected(index: int)

## 初始选中项
@export var current: int = 0
## 选中文字色（亮青，呼应主题）
@export var color_on: Color = Color(0.55, 0.9, 1.0)
## 未选文字色（暗灰蓝）
@export var color_off: Color = Color(0.6, 0.68, 0.78)

var _highlight: Control
var _items: Array[Control] = []

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_highlight = get_node_or_null("Highlight")
	if _highlight:
		_highlight.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var i := 0
	while true:
		var n := get_node_or_null("Item%d" % i)
		if n == null:
			break
		var idx := i
		n.mouse_filter = Control.MOUSE_FILTER_STOP
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
	for i in _items.size():
		var lbl := _items[i]
		if lbl is Label:
			(lbl as Label).add_theme_color_override("font_color", color_on if i == index else color_off)
	selected.emit(index)

func _move_highlight_to(item: Control) -> void:
	if _highlight == null:
		return
	var item_center := item.position + item.size * 0.5
	_highlight.position = item_center - _highlight.size * 0.5
