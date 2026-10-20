extends Tree
## Tree 控件示例填充：建几层可展开/折叠的层级，用于测试场景展示皮肤效果。
## 正式使用时你自行 create_item 填数据；这里只为看主题样式。

func _ready() -> void:
	columns = 1
	hide_root = false
	var root := create_item()
	root.set_text(0, "天赋树 · 根节点")

	var combat := create_item(root)
	combat.set_text(0, "战斗")
	var atk := create_item(combat)
	atk.set_text(0, "攻击强化")
	var atk2 := create_item(combat)
	atk2.set_text(0, "暴击精通")
	var def := create_item(combat)
	def.set_text(0, "防御姿态")

	var magic := create_item(root)
	magic.set_text(0, "法术")
	var fire := create_item(magic)
	fire.set_text(0, "火系精通")
	var ice := create_item(magic)
	ice.set_text(0, "冰系精通（未解锁）")
	ice.set_custom_color(0, Color(0.5, 0.56, 0.64))

	var util := create_item(root)
	util.set_text(0, "辅助")
	var heal := create_item(util)
	heal.set_text(0, "治疗回复")

	magic.collapsed = true  # 演示折叠态（法术一支收起，点箭头可展开）
