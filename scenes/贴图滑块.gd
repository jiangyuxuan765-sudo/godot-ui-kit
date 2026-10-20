extends TextureProgressBar
## 贴图滑块：底层 TextureProgressBar(空槽+填充) + 一个名为 Grabber 的子 TextureRect(拖动键)
## 鼠标可拖动改变数值。挂在 TextureProgressBar 上，其下需有子节点 Grabber。

## 轨道起点(左)内边距（与 texture_progress_offset.x 一致，填充在空槽内的左留边）
@export var track_margin: float = 14.0
## 轨道终点(右)内边距。<0 时沿用 track_margin(对称，兼容其他套)。
## 空槽两端装饰不对称时(如左宝石大、右端小)，单独设右留边让填充/拖动键能拖到右端。
@export var track_margin_end: float = -1.0
## 拖动键整体留在空槽内(滚动条式大滑块用)。默认 false 保持原行为(键中心到端、
## 键可半探出端点，小圆键滑块需要)。true 时把中心行程各内缩半个键宽，
## 让大滑块两端不超出空槽。
@export var grabber_inside: bool = false

var _grabber: Control
## 可选：名为 Fill 的子节点(建议 NinePatchRect)。存在时由脚本控制其宽度，
## 让填充从 track_margin 起、末端正好接到拖动键中心；空槽两端有装饰时用此法避让。
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

## 拖动键中心的行程范围 [左 x, 右 x]。grabber_inside 时各内缩半个键宽，
## 让整块滑块留在空槽内。返回 Vector2(left, right)。
func _travel() -> Vector2:
	var left := track_margin
	var right := size.x - _end_margin()
	if grabber_inside and _grabber:
		var half := _grabber.size.x * 0.5
		left += half
		right -= half
	return Vector2(left, right)

func _update_grabber() -> void:
	if _grabber == null:
		return
	var t := 0.0
	if max_value > min_value:
		t = (value - min_value) / (max_value - min_value)
	var tr := _travel()
	var left := tr.x
	var right := tr.y
	var cx : float = lerp(left, right, t)
	_grabber.position = Vector2(cx - _grabber.size.x * 0.5, (size.y - _grabber.size.y) * 0.5)
	if _fill:
		var fh: float = _fill.custom_minimum_size.y
		_fill.size = Vector2(maxf(0.0, cx - left), fh)
		_fill.position = Vector2(left, (size.y - fh) * 0.5)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_dragging = true
			_set_from_x(event.position.x)
		else:
			_dragging = false
	elif event is InputEventMouseMotion and _dragging:
		_set_from_x(event.position.x)

func _set_from_x(x: float) -> void:
	var tr := _travel()
	var left := tr.x
	var right := tr.y
	if right <= left:
		return
	var t : float = clampf((x - left) / (right - left), 0.0, 1.0)
	value = min_value + t * (max_value - min_value)
