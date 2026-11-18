shader_type spatial;
// The box jelly's bell (box_jelly.gd): its lower part squeezes in with each quick beat, the mouth a little
// after the top. What each point is comes from the model (tools/build_box_jelly.py): COLOR.r the part (0 the
// outside of the bell, 0.25 its inside with the lip and the velarium, 0.5 a stalk); UV.x round it (0..1, a
// face's middle at 0, 0.25, 0.5, 0.75), UV.y crown (0) to rim (1). The beat is worked out the same way in
// BoxJelly._bell_move, which hangs the ropes from it: keep them in step. Drawn here: no texture files. GL
// Compatibility.
//
// Clear jelly in one draw: the inside's triangles come first, then the stalks, then the outside (BoxJelly
// sorts them); the outside is drawn only where it is seen from outside.
render_mode blend_mix, depth_draw_never, cull_disabled;

const float HEIGHT = 0.25;
const float CONTRACT = 0.16;
const float LAG = 0.12;

uniform float phase = 0.0;
uniform float open = 0.2;
uniform vec3 trail = vec3(0.0);
uniform float glow = 0.0;
// (unused here: the strand shader's)
uniform bool roped = false;
uniform float self_light = 0.1;
uniform bool silhouette = false;
// Clear, faintly blue; its edges catch the light pale blue; the small dark eyes; the stalks a little milky.
uniform vec3 clear : source_color = vec3(0.72, 0.86, 1.0);
uniform vec3 edge_blue : source_color = vec3(0.6, 0.85, 1.0);
uniform vec3 eye : source_color = vec3(0.12, 0.08, 0.06);
uniform vec3 stalk : source_color = vec3(0.85, 0.92, 1.0);
uniform float bell_alpha = 0.1;
uniform float inside_alpha = 0.08;
// How brightly its edges glow (seen edge on, and along its four corners): it is nearly invisible but for them.
uniform float edge_light = 0.45;
uniform float shine = 0.4;

varying float part;
varying vec2 at;
varying vec3 rest;

float squeeze(float x) {
	x = fract(x);
	return smoothstep(0.0, 0.2, x) * (1.0 - smoothstep(0.25, 0.7, x));
}

vec3 bell_move(vec3 p) {
	float low_down = 1.0 - smoothstep(0.0, 0.8 * HEIGHT, p.y);
	float k = squeeze(phase - LAG * low_down) * (1.0 + open) - open;
	p.xz *= 1.0 - CONTRACT * k * low_down;
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
	vec3 c;
	float a;
	float lit;
	if (part < 0.125) {
		// its four corners, where the walls meet, run as faint brighter lines
		float q = fract(at.x * 4.0 + 0.5) - 0.5;
		float corner = 1.0 - smoothstep(0.0, 0.07, abs(abs(q) - 0.5));
		// an eye cluster low on each face: a dark dot in a pale ring
		vec2 spot = vec2(q * 0.28, rest.y - 0.045);
		float d = length(spot);
		float dot_ = 1.0 - smoothstep(0.004, 0.007, d);
		float ring = (1.0 - smoothstep(0.009, 0.013, d)) * (1.0 - dot_);
		c = mix(clear, edge_blue, corner);
		c = mix(c, vec3(0.9, 0.95, 1.0), ring * 0.6);
		c = mix(c, eye, dot_);
		a = bell_alpha + 0.25 * corner + 0.3 * ring + 0.85 * dot_;
		lit = edge_light * (edge * edge + 0.6 * corner) * (1.0 - dot_);
	} else if (part < 0.375) {
		// the inside, and the velarium a little milkier
		c = clear;
		a = inside_alpha + 0.08 * smoothstep(0.98, 1.0, at.y);
		lit = edge_light * edge * edge * 0.6;
	} else {
		c = stalk;
		a = 0.3;
		lit = edge_light * (0.3 + edge);
	}
	a = clamp(a + edge * edge * 0.25, 0.0, 0.97);
	if (silhouette) {
		ALBEDO = vec3(0.0);
		ALPHA = 1.0;
	} else {
		ALBEDO = c;
		ALPHA = a;
		ROUGHNESS = 0.2;
		EMISSION = edge_blue * (lit + glow * (0.3 + edge * 1.2)) + c * self_light;
	}
}

void light() {
	float n_dot_l = dot(NORMAL, LIGHT);
	float wrap = clamp((n_dot_l + 0.6) / 1.6, 0.0, 1.0);
	DIFFUSE_LIGHT += wrap * ATTENUATION * LIGHT_COLOR / 3.14159;
	vec3 half_way = normalize(LIGHT + VIEW);
	SPECULAR_LIGHT += pow(max(dot(NORMAL, half_way), 0.0), 80.0) * (silhouette ? 0.0 : shine) * ATTENUATION * LIGHT_COLOR;
}
