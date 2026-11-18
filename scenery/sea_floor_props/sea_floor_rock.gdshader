shader_type spatial;
// Sea floor rock (SeaFloorProps): the colour painted on the mesh's points, times the instance's
// colour and a tint, times the light, with a grain of noise so that big faces are not flat.
// No textures, nothing that needs Forward+: it runs in GL Compatibility. One opaque draw, back
// faces culled. The same shader with a fine grain and a little gloss draws the firm living
// things (shells, hard corals, sea stars).
//
// In GL Compatibility a MultiMesh needs use_colors on and its instances' colours set (white for
// no tint), or COLOR arrives black.
render_mode cull_back;

uniform vec3 tint : source_color = vec3(1.0);
// How strong the grain is (0 none) and how many metres across its biggest blotches are. The
// grain is laid in the world, not on the piece, so a scaled piece keeps the same grain.
uniform float grain : hint_range(0.0, 1.0) = 0.38;
uniform float grain_size = 0.45;
// 0 dull as dry stone, 1 wet and shiny.
uniform float gloss : hint_range(0.0, 1.0) = 0.0;

varying vec3 world_at;

float hash(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float noise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(
		mix(mix(hash(i), hash(i + vec3(1.0, 0.0, 0.0)), f.x),
			mix(hash(i + vec3(0.0, 1.0, 0.0)), hash(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
		mix(mix(hash(i + vec3(0.0, 0.0, 1.0)), hash(i + vec3(1.0, 0.0, 1.0)), f.x),
			mix(hash(i + vec3(0.0, 1.0, 1.0)), hash(i + vec3(1.0, 1.0, 1.0)), f.x), f.y),
		f.z);
}

void vertex() {
	world_at = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 p = world_at / grain_size;
	float n = 0.5 * noise(p) + 0.3 * noise(p * 3.1 + 7.0) + 0.2 * noise(p * 9.7 + 3.0);
	ALBEDO = COLOR.rgb * tint * (1.0 + grain * (n - 0.5) * 2.0);
	ROUGHNESS = 1.0 - 0.6 * gloss;
	SPECULAR = 0.5 * gloss;
}
