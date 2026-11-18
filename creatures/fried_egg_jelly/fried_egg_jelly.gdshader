shader_type spatial;
// The fried egg jelly's bell (fried_egg_jelly.gd): a slow, gentle beat, the rim a little after the middle.
// What each point is comes from the model (tools/build_fried_egg_jelly.py): COLOR.r the part (0 the top of the
// bell, the yolk its middle; 0.25 its underside, lip and stalk); UV.x round it (0..1), UV.y how far out (0 the
// middle, 1 the rim). The beat is worked out the same way in FriedEggJelly._bell_move, which hangs the ropes from
// it: keep them in step. Drawn here: no texture files. GL Compatibility.
//
// Clear jelly in one draw: the underside's triangles come first (FriedEggJelly sorts them), and the top is drawn
// only where it is seen from outside.
render_mode blend_mix, depth_draw_never, cull_disabled;

const float RADIUS = 0.2;
const float CONTRACT = 0.06;
const float DROP = 0.015;
const float LAG = 0.25;
// Where the yolk ends, as a share of the bell's radius (tools/build_fried_egg_jelly.py: YOLK / RADIUS).
const float YOLK = 0.475;

uniform float phase = 0.0;
uniform float open = 0.25;
uniform vec3 trail = vec3(0.0);
uniform float glow = 0.0;
// (unused here: the strand shader's)
uniform bool roped = false;
uniform float self_light = 0.2;
uniform bool silhouette = false;
// The white of the egg (pale, clear, finely ribbed), the groove round the yolk, the yolk itself (deeper at
// its middle), the underside.
uniform vec3 white : source_color = vec3(0.96, 0.94, 0.86);
uniform vec3 groove : source_color = vec3(0.9, 0.66, 0.24);
uniform vec3 yolk : source_color = vec3(1.0, 0.8, 0.18);
uniform vec3 yolk_deep : source_color = vec3(0.98, 0.58, 0.1);
uniform vec3 under : source_color = vec3(0.95, 0.92, 0.82);
uniform float bell_alpha = 0.42;
uniform float under_alpha = 0.22;
uniform float shine = 0.2;

varying float part;
varying vec2 at;
varying vec3 rest;

float squeeze(float x) {
	x = fract(x);
	return smoothstep(0.0, 0.25, x) * (1.0 - smoothstep(0.3, 1.0, x));
}

vec3 bell_move(vec3 p) {
	float reach = length(p.xz);
	float rim = smoothstep(0.3 * RADIUS, RADIUS, reach);
	float k = squeeze(phase - LAG * rim) * (1.0 + open) - open;
	p.xz *= 1.0 - CONTRACT * k * rim;
	p.y -= DROP * k * rim * rim;
	return p;
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
	vec3 c;
	float a;
	if (part < 0.125) {
		// the white: clear and pale, fine ribs out to the rim, a little milkier towards the yolk
		float ribs = pow(0.5 + 0.5 * cos(at.x * 64.0 * 6.2831853), 4.0) * smoothstep(YOLK + 0.05, 0.7, v);
		c = mix(white, white * 0.86, ribs * 0.5);
		a = bell_alpha + 0.12 * ribs + 0.15 * (1.0 - smoothstep(YOLK, 0.8, v));
		// the groove at the yolk's foot, and the yolk: dense and yellow, deeper orange at its crown
		float in_yolk = 1.0 - smoothstep(YOLK - 0.03, YOLK + 0.01, v);
		float ring = exp(-pow((v - YOLK * 1.04) / 0.035, 2.0));
		vec3 egg = mix(yolk_deep, yolk, smoothstep(0.0, YOLK * 0.8, v));
		c = mix(c, groove, ring * 0.7);
		c = mix(c, egg, in_yolk);
		a = mix(a, 0.95, max(in_yolk, ring * 0.6));
	} else {
		c = under;
		a = under_alpha;
	}
	a = clamp(a + edge * 0.18, 0.0, 0.97);
	if (silhouette) {
		ALBEDO = vec3(0.0);
		ALPHA = 1.0;
	} else {
		ALBEDO = c;
		ALPHA = a;
		ROUGHNESS = 0.4;
		EMISSION = c * (self_light + glow * (0.5 + edge));
	}
}

void light() {
	float n_dot_l = dot(NORMAL, LIGHT);
	float wrap = clamp((n_dot_l + 0.6) / 1.6, 0.0, 1.0);
	DIFFUSE_LIGHT += wrap * ATTENUATION * LIGHT_COLOR / 3.14159;
	vec3 half_way = normalize(LIGHT + VIEW);
	SPECULAR_LIGHT += pow(max(dot(NORMAL, half_way), 0.0), 60.0) * (silhouette ? 0.0 : shine) * ATTENUATION * LIGHT_COLOR;
}
