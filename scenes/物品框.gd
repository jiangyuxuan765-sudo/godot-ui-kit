extends TextureButton
## 物品框：点击切换外发光（动态淡入/淡出）。用 toggle_mode + 发光 shader。
## 节点需挂 ShaderMaterial（物品框发光.gdshader）。

var _tween: Tween

func _ready() -> void:
	toggle_mode = true
	toggled.connect(_on_toggled)

func _on_toggled(on: bool) -> void:
	if material == null:
		return
	if _tween and _tween.is_running():
		_tween.kill()
	_tween = create_tween()
	var target := 1.0 if on else 0.0
	_tween.tween_method(
		func(v): material.set_shader_parameter("selected", v),
		material.get_shader_parameter("selected") if material.get_shader_parameter("selected") != null else 0.0,
		target, 0.2)
