shader_type spatial;
// The man o' war's float and crest (man_o_war.gd): rocked on the swell about its origin on the waterline, the
// crest flexing a little in the wind. What each point is comes from the model (tools/build_man_o_war.py):
// COLOR.r the part (0 the float, 0.5 the crest); on the float UV.x round it (0 the top) and UV.y along it (0
// the front, 1 the back); on the crest UV.x along it, UV.y up it (0 its foot, 1 its edge). The rocking is
// worked out the same way in ManOWar._bell_move, which hangs the ropes from it: keep them in step. Drawn here:
// no texture files. GL Compatibility.
//
// One draw: the crest's triangles first, then the float's (ManOWar sorts them); the float is drawn only where
// it is seen from outside, the crest from both sides.
render_mode blend_mix, depth_draw_never, cull_disabled;

const float ROLL = 0.12;
const float PITCH = 0.05;

uniform float phase = 0.0;
uniform float rock = 1.0;
uniform vec3 trail = vec3(0.0);
uniform float glow = 0.0;
// (unused here: the strand shader's)
uniform bool roped = false;
uniform float self_light = 0.25;
uniform bool silhouette = false;
// The float: clear blue low down, pink higher, violet towards the crest; the crest's pleats blue, its edge pink.
uniform vec3 blue : source_color = vec3(0.42, 0.68, 1.0);
uniform vec3 pink : source_color = vec3(0.95, 0.62, 0.86);
uniform vec3 violet : source_color = vec3(0.66, 0.5, 0.98);
uniform vec3 crest_edge : source_color = vec3(1.0, 0.42, 0.68);
uniform float float_alpha = 0.45;
uniform float crest_alpha = 0.6;
uniform float shine = 0.6;

varying float part;
varying vec2 at;
varying vec3 rest;

vec3 bell_move(vec3 p) {
	float r = ROLL * rock * sin(phase * 6.2831853);
	float q = PITCH * rock * sin(phase * 12.5663706 + 1.0);
	float x = p.x * cos(r) - p.y * sin(r);
	float y = p.x * sin(r) + p.y * cos(r);
	return vec3(x, y * cos(q) - p.z * sin(q), y * sin(q) + p.z * cos(q));
}

void vertex() {
	part = COLOR.r;
	at = UV;
	rest = VERTEX;
	if (part > 0.25) {
		// the crest bends a little in the wind, most at its edge
		VERTEX.x += 0.012 * rock * UV.y * UV.y * sin(phase * 6.2831853 * 2.0 + UV.x * 4.0);
	}
	VERTEX = bell_move(VERTEX);
	NORMAL = bell_move(NORMAL);
	VERTEX.xz -= trail.xz * max(VERTEX.y, 0.0) * 0.3;
}

void fragment() {
	if (part < 0.25 && !FRONT_FACING && !silhouette) {
		discard;
	}
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	vec3 c;
	float a;
	if (part < 0.25) {
		// blue at the waterline and under it, pink and violet up its sides, a fine wrinkling along it
		float up = smoothstep(-0.005, 0.06, rest.y);
		c = mix(blue, pink, smoothstep(0.1, 0.7, up));
		c = mix(c, violet, smoothstep(0.75, 1.0, up) * 0.6);
		c *= 0.96 + 0.05 * sin(at.y * 160.0 + sin(at.x * 6.2831853 * 3.0) * 2.0);
		// (the front end, turned up, a little bluer and clearer)
		c = mix(c, blue, 0.35 * (1.0 - smoothstep(0.0, 0.2, at.y)));
		a = float_alpha;
	} else {
		// the crest: violet-blue pleats, pink towards its edge
		float pleat = 0.5 + 0.5 * sin(at.x * 7.0 * 3.14159 * 2.0);
		c = mix(violet, blue, 0.4 * pleat);
		c = mix(c, crest_edge, smoothstep(0.55, 0.95, at.y));
		a = crest_alpha + 0.25 * smoothstep(0.85, 1.0, at.y);
	}
	a = clamp(a + edge * 0.25, 0.0, 0.97);
	if (silhouette) {
		ALBEDO = vec3(0.0);
		ALPHA = 1.0;
	} else {
		ALBEDO = c;
		ALPHA = a;
		ROUGHNESS = 0.25;
		EMISSION = c * (self_light + glow * (0.6 + edge));
	}
}

void light() {
	float n_dot_l = dot(NORMAL, LIGHT);
	float wrap = clamp((n_dot_l + 0.6) / 1.6, 0.0, 1.0);
	DIFFUSE_LIGHT += wrap * ATTENUATION * LIGHT_COLOR / 3.14159;
	vec3 half_way = normalize(LIGHT + VIEW);
	SPECULAR_LIGHT += pow(max(dot(NORMAL, half_way), 0.0), 70.0) * (silhouette ? 0.0 : shine) * ATTENUATION * LIGHT_COLOR;
}
