shader_type spatial;
// The pyrosome (pyrosome.gd): its thousands of members and their lights drawn here (no texture files), its sway like
// a windsock, its bend, and the waves of light that run along it. What each point is comes from the model
// (tools/build_pyrosome.py): UV2.y the part (0 the outer wall, 1 the open end's lip and diaphragm, 2 the inner wall);
// UV.y how far along (0 the closed end .. 1 the open end).
//
// It swims closed end first: the closed end is at -Z, the open end at +Z. The members (zooids) are drawn in
// staggered rows over the outer wall, ZOOIDS_AROUND round it: each a low pale dome with a dark opening and a pair of
// small light organs beside it. What lights up (EMISSION): those light organs, in waves that run along the colony
// from the closed end to the open end (`pulses` a beat, `light_waves` on it at once), each member a little out of
// step with its neighbours; and a faint blue-green glow over the whole tunic and inside its mouth. Everything that
// moves goes by `phase` alone, so it loops. Nothing here needs more than GL Compatibility has. One opaque draw, back
// faces culled.
render_mode cull_back, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


const float LENGTH = 2.0;
const float ZOOIDS_AROUND = 72.0;
const float ZOOID_ALONG = 0.022;

// How far through a beat (0..1, it wraps). Set by Pyrosome.
uniform float phase = 0.0;
// Waves of light that pass along it in a beat (a whole number), and how many stand on it at once.
uniform float pulses = 1.0;
uniform float light_waves = 1.6;
// How much it sways: 1 a slow wave running back along it, the open end swinging most (about 0.08 m either way), 0
// still (as built), 2 twice as much. `sway_waves` waves stand on it at once.
uniform float sway = 1.0;
uniform float sway_waves = 0.7;
// Bent round to one side behind its closed end, radians from end to end (more than 0 the open end comes round to +X).
uniform float curl = 0.0;
// How strongly it glows (0 dark, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;
// Its pale blue-green tunic, the members' openings, its light.
uniform vec3 tunic : source_color = vec3(0.62, 0.8, 0.8);
uniform vec3 opening : source_color = vec3(0.2, 0.3, 0.32);
uniform vec3 inside : source_color = vec3(0.32, 0.45, 0.48);
uniform vec3 light_colour : source_color = vec3(0.35, 1.0, 0.85);

varying float part;
varying vec3 rest;

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

// How far it is pushed aside (x, y) at `s` along it (0 the closed end, 1 the open end).
vec2 swing(float s) {
	float w = 6.2831853 * (phase - sway_waves * s);
	float reach = 0.085 * sway * pow(s, 1.6);
	return vec2(reach * sin(w), 0.35 * reach * sin(w + 1.3));
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float s = clamp((v.z + 1.0) / LENGTH, 0.0, 1.0);
	vec2 h = swing(s);
	vec2 slope = (swing(s + 0.005) - swing(s - 0.005)) / (0.01 * LENGTH);
	// (the ways round it and along it, for the members' domes in the fragment shader)
	float around = atan(v.x, v.y);
	TANGENT = vec3(cos(around), -sin(around), 0.0);
	BINORMAL = vec3(0.0, 0.0, 1.0);
	v.xy += h;
	// (the normal tipped by the sway's slope)
	n = normalize(vec3(n.x - slope.x * n.z, n.y - slope.y * n.z, n.z + slope.x * n.x + slope.y * n.y));
	if (abs(curl) > 0.001) {
		float d = v.z + 1.0;
		float k = curl / LENGTH;
		float a = d * k;
		float r = 1.0 / k;
		float c = cos(a);
		float sn = sin(a);
		n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
		v = vec3(r - (r - v.x) * c, v.y, -1.0 + (r - v.x) * sn);
	}
	VERTEX = v;
	NORMAL = n;
}

// How bright the light organs are at `s` along it, for a member with its own number `own`.
float lit_at(float s, float own) {
	float w = 0.5 + 0.5 * sin(6.2831853 * (pulses * phase - light_waves * s) + own * 1.2);
	return 0.12 + 0.88 * w * w * w * w;
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	EMISSION = texture(baked_glow, bake_uv).rgb * baked_glow_scale;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

