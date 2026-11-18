shader_type spatial;
// The fried egg jelly's arms (fried_egg_jelly.gd): eight short arms, each a frilly cream bunch (real sheets)
// with clubs sticking out of it (each a line, drawn as a strip turned to face the camera, wider at its purple
// tip). Each arm's frills and clubs follow its rope, simulated by FriedEggJelly and sent here as a picture
// (`ropes`); with `roped` off (the low model) they hang as built, lean back by `trail` and sway by `phase`.
//
// What each point is (tools/build_fried_egg_jelly.py): COLOR.r the part (0.5 a frill, 0.75 a club); COLOR.g
// on a club half its width / LINE_SCALE; COLOR.b the rope ((arm + 0.5) / 32); COLOR.a how far along its rope
// it reaches; UV.x across (0..1); UV.y how far along its rope; UV2.x the rope's length; UV2.y a number of its
// own. GL Compatibility.
render_mode blend_mix, depth_draw_always, cull_disabled, skip_vertex_transform;

const int ROPE_ROW = 7;
const int ARM_POINTS = 6;
const int TENTACLE_POINTS = 6;
const float LINE_SCALE = 0.02;

// Set by LionsManeJelly: the ropes (a row a strand, as `LionsManeJelly.strands()` lists them; each point in
// its own space; the last column the strand's root at rest), and whether to lay the strands along them.
uniform sampler2D ropes : filter_nearest, repeat_disable;
uniform bool roped = false;
uniform float phase = 0.0;
uniform vec3 trail = vec3(0.0);
uniform float glow = 0.0;
// (unused here: the bell's)
uniform float open = 0.3;
uniform float self_light = 0.2;
uniform bool silhouette = false;
// The tentacles' width, for 1 as built, and the least a tentacle is drawn wide as seen (radians), so that
// far off it stays a faint line rather than breaking up.
uniform float line_width = 1.0;
uniform float min_angle = 0.0016;
// The frills cream to pale yellow, their edges white; the clubs pale, their knobbed tips purple.
uniform vec3 frill : source_color = vec3(0.98, 0.93, 0.74);
uniform vec3 frill_edge : source_color = vec3(1.0, 0.99, 0.95);
uniform vec3 club : source_color = vec3(0.92, 0.9, 0.86);
uniform vec3 purple : source_color = vec3(0.45, 0.22, 0.72);
uniform float arm_alpha = 0.78;

varying float part;
varying vec2 at;
// (how far from the strand's tip, metres)
varying float along;
varying float seed;
varying float fade;

void vertex() {
	part = COLOR.r;
	at = UV;
	seed = UV2.y;
	along = (COLOR.a - UV.y) * UV2.x;
	float s = UV.y;
	float long = UV2.x;
	float ph = UV2.y * 6.2831853;
	int row = int(floor(COLOR.b * 32.0));
	bool line = part > 0.625;
	float half_w = COLOR.g * LINE_SCALE;
	vec3 centre = VERTEX;
	if (line) {
		centre.x -= (UV.x * 2.0 - 1.0) * half_w;
	}
	vec3 way = vec3(0.0, -1.0, 0.0);
	vec3 normal = NORMAL;
	if (roped) {
		int count = line ? TENTACLE_POINTS : ARM_POINTS;
		vec3 root = texelFetch(ropes, ivec2(ROPE_ROW - 1, row), 0).xyz;
		vec3 offset = centre - (root - vec3(0.0, s * long, 0.0));
		float f = clamp(s, 0.0, 1.0) * float(count - 1);
		int i1 = min(int(f), count - 2);
		float t = f - float(i1);
		vec3 p0 = texelFetch(ropes, ivec2(max(i1 - 1, 0), row), 0).xyz;
		vec3 p1 = texelFetch(ropes, ivec2(i1, row), 0).xyz;
		vec3 p2 = texelFetch(ropes, ivec2(i1 + 1, row), 0).xyz;
		vec3 p3 = texelFetch(ropes, ivec2(min(i1 + 2, count - 1), row), 0).xyz;
		// (a smooth curve through the points)
		vec3 c1 = p2 - p0;
		vec3 c2 = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3;
		vec3 c3 = 3.0 * (p1 - p2) + p3 - p0;
		vec3 on_line = 0.5 * (2.0 * p1 + c1 * t + c2 * t * t + c3 * t * t * t);
		way = normalize(0.5 * (c1 + 2.0 * c2 * t + 3.0 * c3 * t * t) + vec3(0.0, -0.0001, 0.0));
		// (the smallest turn that takes straight down to the way the rope runs; at the root the offset
		// stays as the bell has it)
		vec3 w = cross(vec3(0.0, -1.0, 0.0), way);
		float c = max(-way.y, -0.98);
		float follows = smoothstep(0.0, 0.08, s);
		offset += (cross(w, offset) + cross(w, cross(w, offset)) / (1.0 + c)) * follows;
		normal = normalize(normal + (cross(w, normal) + cross(w, cross(w, normal)) / (1.0 + c)) * follows);
		centre = on_line + offset;
	} else {
		// (no ropes: hanging as built, leaning back as it goes, swaying with the beat)
		float bend = s * s * long;
		centre += vec3(trail.x, 0.0, trail.z) * bend * 0.8;
		centre += vec3(sin(phase * 6.2831853 + ph + s * 4.0), 0.0, cos(phase * 6.2831853 + ph * 1.7 + s * 3.0)) * 0.04 * bend;
		way = normalize(vec3(trail.x * 1.6 * s, -1.0, trail.z * 1.6 * s));
	}
	// (a tentacle is turned to face the camera)
	vec3 pv = (MODELVIEW_MATRIX * vec4(centre, 1.0)).xyz;
	if (line) {
		vec3 wv = normalize(mat3(MODELVIEW_MATRIX) * way);
		vec3 side = cross(wv, normalize(pv));
		side = length(side) > 0.0001 ? normalize(side) : vec3(1.0, 0.0, 0.0);
		float wanted = half_w * line_width * length(MODELVIEW_MATRIX[0].xyz);
		float drawn = max(wanted, -pv.z * min_angle);
		fade = wanted / max(drawn, 0.000001);
		pv += side * (UV.x * 2.0 - 1.0) * drawn;
		vec3 n = normalize(cross(side, wv));
		NORMAL = dot(n, pv) > 0.0 ? -n : n;
	} else {
		fade = 1.0;
		NORMAL = normalize(mat3(MODELVIEW_MATRIX) * normal);
	}
	VERTEX = pv;
}

void fragment() {
	vec3 c;
	float a;
	if (part < 0.625) {
		// a frill: cream, crinkled, its edges paler and lacy
		float e = abs(at.x * 2.0 - 1.0);
		c = mix(frill, frill_edge, smoothstep(0.5, 0.95, e));
		c *= 0.88 + 0.16 * (0.5 + 0.5 * sin(along * 250.0 + e * 5.0));
		a = arm_alpha;
		float cut = 0.94 + 0.06 * sin(along * 300.0 + seed * 20.0);
		a *= 1.0 - smoothstep(cut - 0.05, cut, e);
		float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
		a = clamp(a + edge * 0.15, 0.0, 0.96);
	} else {
		// a club: pale, its knob purple
		// (along is how far from its tip, metres: see the vertex shader)
		c = mix(club, purple, 1.0 - smoothstep(0.008, 0.02, along));
		a = 0.95 * fade * (1.0 - pow(abs(at.x * 2.0 - 1.0), 3.0));
	}
	if (silhouette) {
		ALBEDO = vec3(0.0);
		ALPHA = a > 0.02 ? 1.0 : 0.0;
	} else {
		ALBEDO = c;
		ALPHA = a;
		ROUGHNESS = 0.55;
		EMISSION = c * (self_light + glow * 1.2);
	}
}

void light() {
	float n_dot_l = dot(NORMAL, LIGHT);
	float wrap = clamp((n_dot_l + 0.7) / 1.7, 0.0, 1.0);
	DIFFUSE_LIGHT += wrap * ATTENUATION * LIGHT_COLOR / 3.14159;
}
