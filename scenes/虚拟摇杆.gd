extends TextureRect
## 虚拟摇杆：背景 TextureRect + 名为 Knob 的子 TextureRect(摇杆键)
## 鼠标在背景内按下拖动，摇杆键跟随(限制在半径内)，松手回中。
## 对外提供 output(Vector2, 范围-1~1) 和 moved 信号，可接移动逻辑。

signal moved(vector: Vector2)

## 摇杆键可移动的最大半径(相对背景中心)。留 0 则自动取背景半宽的一半
@export var max_radius: float = 0.0

var _knob: Control
var _dragging := false
var _center := Vector2.ZERO
var output := Vector2.ZERO

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_knob = get_node_or_null("Knob")
	if _knob:
		_knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(_recenter)
	await get_tree().process_frame
	_recenter()

func _recenter() -> void:
	_center = size * 0.5
	if max_radius <= 0.0:
		max_radius = size.x * 0.25
	_move_knob(_center)

func _move_knob(pos: Vector2) -> void:
	if _knob == null:
		return
	_knob.position = pos - _knob.size * 0.5

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_dragging = true
			_drag_to(event.position)
		else:
			_dragging = false
			output = Vector2.ZERO
			_move_knob(_center)
			moved.emit(output)
	elif event is InputEventMouseMotion and _dragging:
		_drag_to(event.position)

func _drag_to(pos: Vector2) -> void:
	var offset := pos - _center
	if offset.length() > max_radius:
		offset = offset.normalized() * max_radius
	_move_knob(_center + offset)
	output = offset / max_radius if max_radius > 0.0 else Vector2.ZERO
	moved.emit(output)
