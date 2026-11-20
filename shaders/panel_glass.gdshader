shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_back;
// The glass of the panel's vacuum tubes: thin and clear with a brighter edge and a highlight, and
// warmed by the filament inside it (`lit` 0..1). The works inside are part of the baked model.

uniform float lit = 0.5;

void fragment() {
	vec3 n = normalize(NORMAL);
	float edge = 1.0 - smoothstep(0.1, 0.8, n.z);
	float shine = smoothstep(0.93, 0.97, dot(n, normalize(vec3(-0.5, 0.62, 1.6))));
	// (boosting lights them: `lit` near 1 is a bright amber, the glass filled with it)
	float on = clamp(lit, 0.0, 1.0);
	ALBEDO = mix(vec3(0.6, 0.68, 0.64), mix(vec3(1.0, 0.5, 0.15), vec3(1.0, 0.85, 0.45), on * on), on) + shine * 0.6;
	ALPHA = clamp(0.1 + edge * 0.4 + shine * 0.6 + on * 0.6, 0.0, 1.0);
}
