extends TextureProgressBar
## 竖版贴图滑块：TextureProgressBar(竖向) + 名为 Grabber 的子 TextureRect(拖动键)
## 鼠标上下拖动改变数值。fill_mode 应设为 3(FILL_BOTTOM_TO_TOP)。
## 与横版 贴图滑块.gd 同源，改用 y 轴。

## 轨道起点(底)内边距（填充在空槽内的底部留边）
@export var track_margin: float = 14.0
## 轨道终点(顶)内边距。<0 时沿用 track_margin(对称，兼容其他套)。
## 空槽两端装饰不对称时，单独设顶留边让填充/拖动键能拖到顶端。
@export var track_margin_end: float = -1.0
## 拖动键整体留在空槽内(滚动条式大滑块用)。默认 false 保持原行为(键中心到端、
## 键可半探出端点，小圆键滑块需要)。true 时把中心行程各内缩半个键高，
## 让大滑块两端不超出空槽。
@export var grabber_inside: bool = false

var _grabber: Control
## 可选：名为 Fill 的子节点(建议 NinePatchRect)。存在时由脚本控制其高度，
## 让填充从底部 track_margin 起、末端正好接到拖动键中心；空槽两端有装饰时用此法避让。
## 不存在则退化为原行为(用内置 texture_progress 填充)，不影响其他套。
var _fill: Control
var _dragging := false

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_grabber = get_node_or_null("Grabber")
	if _grabber:
		_grabber.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fill = get_node_or_null("Fill")
	if _fill:
		_fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	value_changed.connect(func(_v): _update_grabber())
	resized.connect(_update_grabber)
	await get_tree().process_frame
	_update_grabber()

func _end_margin() -> float:
	return track_margin_end if track_margin_end >= 0.0 else track_margin

## 拖动键中心的行程范围 [顶 y, 底 y]。grabber_inside 时各内缩半个键高，
## 让整块滑块留在空槽内。返回 Vector2(top, bottom)。
func _travel() -> Vector2:
	var bottom := size.y - track_margin
	var top := _end_margin()
	if grabber_inside and _grabber:
		var half := _grabber.size.y * 0.5
		bottom -= half
		top += half
	return Vector2(top, bottom)

func _update_grabber() -> void:
	if _grabber == null:
		return
	var t := 0.0
	if max_value > min_value:
		t = (value - min_value) / (max_value - min_value)
	# 底部 = 最小值，顶部 = 最大值（与 FILL_BOTTOM_TO_TOP 一致）
	var tr := _travel()
	var top := tr.x
	var bottom := tr.y
	var cy : float = lerp(bottom, top, t)
	_grabber.position = Vector2((size.x - _grabber.size.x) * 0.5, cy - _grabber.size.y * 0.5)
	if _fill:
		var fw: float = _fill.custom_minimum_size.x
		_fill.size = Vector2(fw, maxf(0.0, bottom - cy))
		_fill.position = Vector2((size.x - fw) * 0.5, cy)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_dragging = true
			_set_from_y(event.position.y)
		else:
			_dragging = false
	elif event is InputEventMouseMotion and _dragging:
		_set_from_y(event.position.y)

func _set_from_y(y: float) -> void:
	var tr := _travel()
	var top := tr.x
	var bottom := tr.y
	if bottom <= top:
		return
	# y 越小(越靠顶) → 值越大
	var t : float = clampf((bottom - y) / (bottom - top), 0.0, 1.0)
	value = min_value + t * (max_value - min_value)
