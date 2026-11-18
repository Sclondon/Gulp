shader_type spatial;
render_mode unshaded;
// The control panel's paint: after the first concept picture (tools/art_src/panel_concept_1.png:
// rusted plate with verdigris, worn brass) but calm (the user: "the texture needs to be less
// noisy"): broad soft patches, no grain. Lit here by one fixed light from the upper left with a
// soft highlight, so it needs no lights and looks the same on every renderer. The patches are
// laid on by the model's own shape (three ways, by its normal), so nothing needs UVs.

uniform vec3 base : source_color = vec3(0.6, 0.3, 0.1);
uniform vec3 patch_a : source_color = vec3(0.4, 0.2, 0.08);
uniform vec3 patch_b : source_color = vec3(0.35, 0.45, 0.3);
// How strongly the patches show (0 none).
uniform float patches = 0.0;
uniform float patch_size = 1.6;
// Polished metal (0 dull paint or rust, 1 brass): a highlight, and the light and dark of a room
// mirrored in it.
uniform float shine = 0.0;
// Hammered, dented metal: how much the surface seems to rise and fall (0 flat).
uniform float dents = 0.0;
// Light of its own (the plunger held, the scope).
uniform vec3 glow : source_color = vec3(0.0);
uniform sampler2D noise : repeat_enable, filter_linear_mipmap;

varying vec3 at;
varying vec3 facing;

void vertex() {
	at = VERTEX;
	facing = NORMAL;
}

float blotch(vec2 where) {
	return texture(noise, where).r;
}

void fragment() {
	vec3 colour = base;
	if (patches > 0.0) {
		vec3 share = pow(abs(normalize(facing)), vec3(4.0));
		share /= share.x + share.y + share.z;
		// (stretched downwards, as rust and verdigris run)
		vec3 p = at * vec3(1.0, 0.45, 1.0) / patch_size;
		float a = blotch(p.yz) * share.x + blotch(p.xz) * share.y + blotch(p.xy) * share.z;
		vec3 q = p * 0.6 + vec3(0.37, 0.11, 0.73);
		float b = blotch(q.yz) * share.x + blotch(q.xz) * share.y + blotch(q.xy) * share.z;
		colour = mix(colour, patch_a, smoothstep(0.3, 0.75, a) * patches);
		colour = mix(colour, patch_b, smoothstep(0.5, 0.8, b) * patches * 0.8);
	}
	vec3 n = normalize(NORMAL);
	if (dents > 0.0) {
		vec2 d0 = at.xy * 0.55;
		float h = blotch(d0);
		n = normalize(n + vec3(h - blotch(d0 + vec2(0.03, 0.0)), h - blotch(d0 + vec2(0.0, 0.03)), 0.0) * dents * 5.0);
	}
	vec3 light = normalize(vec3(-0.5, 0.62, 0.6));
	float d = dot(n, light);
	float wrap = clamp(d * 0.5 + 0.5, 0.0, 1.0);
	float lit = 0.3 + 0.85 * wrap * wrap;
	// (darker where the surface turns away from the eye: depth in the creases)
	lit *= mix(0.6, 1.0, smoothstep(0.0, 0.45, n.z));
	vec3 half_way = normalize(light + vec3(0.0, 0.0, 1.0));
	float spark = pow(max(dot(n, half_way), 0.0), 36.0) * shine * 1.1;
	// (polished metal: bright where it faces up and the light, dark below)
	float mirror = mix(1.0, mix(0.55, 1.35, smoothstep(-0.5, 0.8, n.y * 0.6 + d * 0.5)), shine);
	ALBEDO = colour * lit * mirror + spark * mix(vec3(1.0), colour, 0.35) * 1.4 + glow;
}
