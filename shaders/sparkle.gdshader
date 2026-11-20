shader_type spatial;
// The gold sparkles round what the player can eat (scripts/food_marks.gd): every one a small card
// in one MultiMesh, turned to face the eye, drawn as a four-pointed star that twinkles. The colour
// and strength come from each card's instance colour (alpha: how strong); each twinkles on its own
// beat (by its instance number).
render_mode blend_add, unshaded, cull_disabled, depth_draw_never, shadows_disabled;

varying float beat;
varying vec4 tint;

void vertex() {
	// (a card facing the eye: its place (from the node, which is kept by the player: small numbers, so
	// that they keep their precision) and size are the instance's custom data, not its transform, so
	// the card is turned to the eye here whatever Compatibility does with an instance's transform)
	vec3 world = MODEL_MATRIX[3].xyz + INSTANCE_CUSTOM.xyz + (INV_VIEW_MATRIX[0].xyz * VERTEX.x + INV_VIEW_MATRIX[1].xyz * VERTEX.y) * INSTANCE_CUSTOM.w;
	POSITION = PROJECTION_MATRIX * (VIEW_MATRIX * vec4(world, 1.0));
	beat = float(INSTANCE_ID) * 1.7;
	tint = COLOR;
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float twinkle = 0.55 + 0.45 * sin(TIME * 5.5 + beat);
	// (a star: a bright core and two thin crossed rays)
	float core = exp(-dot(p, p) * 18.0);
	float rays = exp(-abs(p.x) * 26.0) * (1.0 - abs(p.y)) + exp(-abs(p.y) * 26.0) * (1.0 - abs(p.x));
	float light = min((core + rays * mix(0.45, 1.0, twinkle)) * twinkle, 1.0);
	ALBEDO = tint.rgb * light * tint.a;
	ALPHA = clamp(light * tint.a, 0.0, 1.0);
}
