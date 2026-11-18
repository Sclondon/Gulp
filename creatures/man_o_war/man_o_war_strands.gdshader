shader_type spatial;
// The man o' war's tentacles and polyps (man_o_war.gd): each a line, drawn as a strip turned to face the camera,
// that follows one of its six ropes, simulated by ManOWar and sent here as a picture (`ropes`); with `roped`
// off (the low model) they hang as built, lean back by `trail` and sway by `phase`. The tentacles' coils are
// in the model (offsets from the rope's line, turned with it).
//
// What each point is (tools/build_man_o_war.py): COLOR.r the part (0.75 a tentacle, 0.875 a polyp); COLOR.g half
// its width / LINE_SCALE (the beads' width: between them it is drawn narrower); COLOR.b the rope ((rope + 0.5) /
// 32); COLOR.a how far along its rope it reaches; UV.x across (0..1); UV.y how far along its rope; UV2.x the
// rope's length; UV2.y a number of its own. GL Compatibility.
render_mode blend_mix, depth_draw_always, cull_disabled, skip_vertex_transform;

const int ROPE_ROW = 13;
const int ARM_POINTS = 12;
const int TENTACLE_POINTS = 12;
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
uniform float self_light = 0.22;
uniform bool silhouette = false;
// The tentacles' width, for 1 as built, and the least a tentacle is drawn wide as seen (radians), so that
// far off it stays a faint line rather than breaking up.
uniform float line_width = 1.0;
uniform float min_angle = 0.0016;
// Dark blue tentacles, beaded paler blue-violet with stinging cells; the polyps blue-violet, paler at their tips.
uniform vec3 tentacle : source_color = vec3(0.06, 0.1, 0.4);
uniform vec3 bead : source_color = vec3(0.38, 0.45, 0.95);
uniform vec3 polyp : source_color = vec3(0.14, 0.12, 0.48);
uniform float tentacle_alpha = 0.9;

varying float part;
varying vec2 at;
// (how far along its rope, metres; and its rope's length)
varying float along;
varying float long_is;
varying float seed;
varying float fade;

void vertex() {
	part = COLOR.r;
	at = UV;
	seed = UV2.y;
	along = UV.y * UV2.x;
	long_is = COLOR.a * UV2.x;
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
	// (a coiled tentacle: its part code says how many coils in its first 0.6 m; the coil is laid round its rest
	// line here, turned with the rope as the rest of its offset is, and the strip is turned by the coil's way)
	float curl = (part > 0.745 && part < 0.82) ? floor((part - 0.75) * 100.0 + 0.5) : 0.0;
	vec3 coil_way = vec3(0.0);
	if (curl > 0.0) {
		float metres = s * long;
		float radius = 0.028 * (1.0 - smoothstep(0.0, 0.7, metres)) + 0.006;
		float turns = curl * 6.2831853 / 0.6;
		float angle = metres * turns + seed * 6.2831853;
		centre += vec3(cos(angle), 0.0, sin(angle)) * radius;
		coil_way = vec3(-sin(angle), 0.0, cos(angle)) * radius * turns;
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
		coil_way += (cross(w, coil_way) + cross(w, cross(w, coil_way)) / (1.0 + c)) * follows;
		centre = on_line + offset;
	} else {
		// (no ropes: hanging as built, leaning back as it goes, swaying with the beat)
		float bend = s * s * long;
		centre += vec3(trail.x, 0.0, trail.z) * bend * 0.8;
		centre += vec3(sin(phase * 6.2831853 + ph + s * 4.0), 0.0, cos(phase * 6.2831853 + ph * 1.7 + s * 3.0)) * 0.04 * bend;
		way = normalize(vec3(trail.x * 1.6 * s, -1.0, trail.z * 1.6 * s));
	}
	way = normalize(way + coil_way);
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
	float across = abs(at.x * 2.0 - 1.0);
	if (part < 0.8125) {
		// a tentacle: dark blue, beaded every few centimetres; between the beads it is narrower
		float b = smoothstep(0.7, 0.95, 0.5 + 0.5 * sin(along * 6.2831853 / 0.05 + seed * 30.0));
		float shown = mix(0.45, 1.0, b);
		c = mix(tentacle, bead, b * 0.8);
		a = tentacle_alpha * fade * (1.0 - smoothstep(shown - 0.15, shown, across)) * (1.0 - 0.5 * smoothstep(0.8, 1.0, along / max(long_is, 0.01)));
	} else {
		// a polyp: blue-violet, paler at its tip
		c = mix(polyp, bead, 0.5 * smoothstep(0.08, 0.18, along));
		a = 0.9 * fade * (1.0 - across * across * across);
	}
	if (silhouette) {
		ALBEDO = vec3(0.0);
		ALPHA = a > 0.02 ? 1.0 : 0.0;
	} else {
		ALBEDO = c;
		ALPHA = a;
		ROUGHNESS = 0.55;
		EMISSION = c * (self_light + glow * 1.5);
	}
}

void light() {
	float n_dot_l = dot(NORMAL, LIGHT);
	float wrap = clamp((n_dot_l + 0.7) / 1.7, 0.0, 1.0);
	DIFFUSE_LIGHT += wrap * ATTENUATION * LIGHT_COLOR / 3.14159;
}
