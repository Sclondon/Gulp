shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
// The Atlantis ruins' paint (scripts/ruins.gd; built and baked by tools/build_ruins.py): one baked
// picture (colour, growth on the tops, silt low down, soft shadow in the hollows) lit by the sea's
// own lights and fogged by its water like everything else. The one shader of the whole set piece:
// the stone, the statue (its own picture) and what glows are three materials of it.

uniform sampler2D atlas : source_color, filter_linear_mipmap, repeat_disable;
// Day and night can dim it (multiplies the paint).
uniform vec3 tint : source_color = vec3(1.0);
// Light of its own: 0 for stone; the crystal and the orichalcum inlays have it on.
uniform float glow = 0.0;
// A little grain in the stone, from where it is in the world, so the paint holds up close.
uniform float grain = 0.08;

varying vec3 world;

float hash(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise(vec3 x) {
	vec3 i = floor(x);
	vec3 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash(i), hash(i + vec3(1.0, 0.0, 0.0)), f.x), mix(hash(i + vec3(0.0, 1.0, 0.0)), hash(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
			mix(mix(hash(i + vec3(0.0, 0.0, 1.0)), hash(i + vec3(1.0, 0.0, 1.0)), f.x), mix(hash(i + vec3(0.0, 1.0, 1.0)), hash(i + vec3(1.0, 1.0, 1.0)), f.x), f.y), f.z);
}

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 colour = texture(atlas, UV).rgb;
	float n = noise(world * 2.1) * 0.55 + noise(world * 6.3) * 0.45;
	colour *= 1.0 + grain * (n * 2.0 - 1.0);
	ALBEDO = colour * tint;
	ROUGHNESS = 0.92;
	SPECULAR = 0.25;
	EMISSION = colour * tint * glow;
}
