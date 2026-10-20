extends TextureProgressBar
## 信息卡片进度条：数值完全由【代码】控制，不可鼠标拖拽。
##
## 在你的游戏里直接设值即可：
##     $卡片/Bar.value = 75           # 0~100
## 或用节点引用：card_bar.value = 当前血量 / 最大血量 * 100
##
## 下面的 demo 只是"测试场景里能看到它在动"的演示（代码循环驱动数值）。
## 正式使用时把 demo 关掉（inspector 里取消勾选），改由你自己的代码写 value。

@export var demo: bool = true       ## 开：循环演示；关：静态，由外部代码控制
@export var demo_from: float = 0.0
@export var demo_to: float = 100.0
@export var demo_time: float = 2.0  ## 单程秒数

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE  # 纯展示，不拦截鼠标
	if demo:
		var t := create_tween().set_loops()
		t.tween_property(self, "value", demo_to, demo_time).set_trans(Tween.TRANS_SINE)
		t.tween_property(self, "value", demo_from, demo_time).set_trans(Tween.TRANS_SINE)
