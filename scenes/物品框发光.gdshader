shader_type canvas_item;

// 物品框外发光：selected=0 无发光，=1 全发光。可被 tween 平滑过渡。
uniform float selected : hint_range(0.0, 1.0) = 0.0;
uniform vec4 glow_color : source_color = vec4(0.42, 0.86, 1.0, 1.0);
uniform float glow_size = 4.0;

void fragment() {
	vec4 tex = texture(TEXTURE, UV);
	vec2 px = TEXTURE_PIXEL_SIZE * glow_size;
	// 采样周围8方向的 alpha，取最大 → 形成向外扩散的轮廓
	float a = 0.0;
	a = max(a, texture(TEXTURE, UV + vec2(px.x, 0.0)).a);
	a = max(a, texture(TEXTURE, UV + vec2(-px.x, 0.0)).a);
	a = max(a, texture(TEXTURE, UV + vec2(0.0, px.y)).a);
	a = max(a, texture(TEXTURE, UV + vec2(0.0, -px.y)).a);
	a = max(a, texture(TEXTURE, UV + px).a);
	a = max(a, texture(TEXTURE, UV - px).a);
	a = max(a, texture(TEXTURE, UV + vec2(px.x, -px.y)).a);
	a = max(a, texture(TEXTURE, UV + vec2(-px.x, px.y)).a);
	// 发光只出现在图形外围（当前透明、周围不透明处）
	float glow = clamp(a - tex.a, 0.0, 1.0) * selected;
	vec4 col = tex;
	col.rgb = mix(col.rgb, glow_color.rgb, glow);
	col.a = max(col.a, glow * glow_color.a);
	COLOR = col;
}
