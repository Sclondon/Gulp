shader_type spatial;
// The lion's mane jelly's bell (lions_mane_jelly.gd): it draws in and lets go with each beat, the rim a
// little after the crown. What each point is comes from the model (tools/build_lions_mane_jelly.py):
// COLOR.r the part (0 the top of the bell, 0.25 its underside, lip and stalk); UV.x round it (0..1), UV.y
// crown (0) to rim (1). The beat is worked out the same way in LionsManeJelly._bell_move, which hangs the
// ropes from it: keep them in step. Markings drawn here: no texture files. GL Compatibility.
//
// Clear jelly in one draw: the underside's triangles come first (LionsManeJelly sorts them), and the top
// is drawn only where it is seen from outside.
render_mode blend_mix, depth_draw_never, cull_disabled;

const float RADIUS = 0.75;
const float CONTRACT = 0.1;
const float DROP = 0.07;
const float LAG = 0.2;

// Set by LionsManeJelly.
uniform float phase = 0.0;
uniform float open = 0.3;
// How the bell leans into the way it goes (its own space).
uniform vec3 trail = vec3(0.0);
uniform float glow = 0.0;
// (unused here: the strand shader's)
uniform bool roped = false;
// How much it shows by its own colour in dim water (0: only by the light it is given).
uniform float self_light = 0.18;
// Flat black, for silhouette checks.
uniform bool silhouette = false;
// Rust at the crown and in streaks and clefts; deep gold across the lobes; paler gold at the scalloped rim;
// the underside.
uniform vec3 rust : source_color = vec3(0.5, 0.13, 0.05);
uniform vec3 rust_deep : source_color = vec3(0.36, 0.07, 0.04);
uniform vec3 gold : source_color = vec3(0.86, 0.52, 0.12);
uniform vec3 gold_pale : source_color = vec3(0.98, 0.78, 0.4);
uniform vec3 under : source_color = vec3(0.96, 0.6, 0.28);
uniform float bell_alpha = 0.7;
uniform float under_alpha = 0.6;
uniform float shine = 0.12;

varying float part;
varying vec2 at;
varying vec3 rest;

float squeeze(float x) {
	x = fract(x);
	return smoothstep(0.0, 0.25, x) * (1.0 - smoothstep(0.3, 1.0, x));
}

vec3 bell_move(vec3 p) {
	float reach = length(p.xz);
	float rim = smoothstep(0.15 * RADIUS, RADIUS, reach);
	float k = squeeze(phase - LAG * rim) * (1.0 + open) - open;
	p.xz *= 1.0 - CONTRACT * k * rim;
	p.y -= DROP * k * rim * rim;
	return p;
}

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(
			mix(mix(hash3(i), hash3(i + vec3(1.0, 0.0, 0.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 0.0)), hash3(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
			mix(mix(hash3(i + vec3(0.0, 0.0, 1.0)), hash3(i + vec3(1.0, 0.0, 1.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 1.0)), hash3(i + vec3(1.0, 1.0, 1.0)), f.x), f.y),
			f.z);
}

void vertex() {
	part = COLOR.r;
	at = UV;
	rest = VERTEX;
	VERTEX = bell_move(VERTEX);
	VERTEX.xz -= trail.xz * max(VERTEX.y, 0.0) * 0.3;
}

void fragment() {
	if (part < 0.125 && !FRONT_FACING && !silhouette) {
		discard;
	}
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	float v = at.y;
	// across a lobe: 0 and 1 the clefts, 0.5 its middle
	float x = fract(at.x * 8.0);
	float cleft = 1.0 - smoothstep(0.0, 0.13, min(x, 1.0 - x));
	float mottle = noise3(rest * 7.0);
	vec3 c;
	float a;
	if (part < 0.125) {
		// rust at the crown, a ring of darker rust, deep gold across the lobes, paler at the scalloped rim
		c = mix(rust_deep, rust, smoothstep(0.0, 0.22, v));
		c = mix(c, gold, smoothstep(0.25, 0.62, v + (mottle - 0.5) * 0.12));
		// fine rust streaks running out over each lobe
		float streak = pow(0.5 + 0.5 * cos(x * 7.0 * 6.2831853 + (mottle - 0.5) * 1.5), 6.0);
		c = mix(c, rust, 0.5 * streak * smoothstep(0.3, 0.55, v) * (1.0 - smoothstep(0.86, 0.97, v)));
		c = mix(c, rust_deep, 0.65 * cleft * smoothstep(0.5, 0.85, v));
		c = mix(c, gold_pale, 0.45 * smoothstep(0.88, 1.0, v) * (1.0 - cleft));
		c *= 0.88 + 0.24 * noise3(rest * 18.0);
		a = mix(0.92, bell_alpha, smoothstep(0.1, 0.6, v));
	} else {
		// the underside: pale gold, rust bands out under each lobe; the stalk rust
		float band = pow(0.5 + 0.5 * cos(x * 6.2831853), 3.0);
		c = mix(under, rust, 0.35 * band * smoothstep(0.2, 0.7, v) + 0.4 * (1.0 - smoothstep(0.0, 0.2, v)));
		a = under_alpha + 0.2 * band;
	}
	a = clamp(a + edge * 0.2, 0.0, 0.97);
	if (silhouette) {
		ALBEDO = vec3(0.0);
		ALPHA = 1.0;
	} else {
		ALBEDO = c;
		ALPHA = a;
		ROUGHNESS = 0.45;
		EMISSION = c * (self_light + glow * (0.7 + edge * 1.2));
	}
}

void light() {
	// Soft bands: a jelly lets light through, so even its far side is lit.
	float n_dot_l = dot(NORMAL, LIGHT);
	float wrap = clamp((n_dot_l + 0.6) / 1.6, 0.0, 1.0);
	DIFFUSE_LIGHT += wrap * ATTENUATION * LIGHT_COLOR / 3.14159;
	vec3 half_way = normalize(LIGHT + VIEW);
	SPECULAR_LIGHT += pow(max(dot(NORMAL, half_way), 0.0), 50.0) * (silhouette ? 0.0 : shine) * ATTENUATION * LIGHT_COLOR;
}
