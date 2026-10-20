extends TextureButton
## 弹窗关闭按钮：点击让目标节点（弹窗）隐藏。
## 按压有变暗动效（button_down 变暗、button_up 恢复）。
##
## 用法：把此脚本挂在弹窗右上角的 TextureButton 上，
## 在 inspector 里把 target 指向要关闭的弹窗节点（不设则关闭自己的父节点）。

## 要关闭的目标节点（留空则默认关闭父节点）
@export var target: NodePath

func _ready() -> void:
	button_down.connect(_on_down)
	button_up.connect(_on_up)
	pressed.connect(_on_pressed)

func _on_down() -> void:
	modulate = Color(0.6, 0.6, 0.6, 1)  # 按压变暗

func _on_up() -> void:
	modulate = Color(1, 1, 1, 1)        # 松开恢复

func _on_pressed() -> void:
	var node: Node = get_node_or_null(target) if not target.is_empty() else get_parent()
	if node and node is CanvasItem:
		(node as CanvasItem).hide()
