shader_type spatial;
// The lion's mane jelly's strands (lions_mane_jelly.gd): four oral arms (folded curtains, real sheets) and
// eight clusters of fine tentacles (each tentacle a thin line, drawn as a strip turned to face the camera).
// Each strand follows a rope simulated by LionsManeJelly and sent here as a picture (`ropes`); with
// `roped` off (the low model) they hang as built, lean back by `trail` and sway by `phase`.
//
// What each point is (tools/build_lions_mane_jelly.py): COLOR.r the part (0.5 an arm, 0.75 a tentacle);
// COLOR.g on a tentacle half its width / LINE_SCALE; COLOR.b the rope ((row + 0.5) / 32); COLOR.a how far
// along its rope the strand reaches; UV.x across (0..1); UV.y how far along its rope; UV2.x the rope's
// length; UV2.y a number of its own. GL Compatibility.
render_mode blend_mix, depth_draw_always, cull_disabled, skip_vertex_transform;

const int ROPE_ROW = 12;
const int ARM_POINTS = 8;
const int TENTACLE_POINTS = 10;
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
uniform float self_light = 0.18;
uniform bool silhouette = false;
// The tentacles' width, for 1 as built, and the least a tentacle is drawn wide as seen (radians), so that
// far off it stays a faint line rather than breaking up.
uniform float line_width = 1.0;
uniform float min_angle = 0.0016;
// The mane: deep rust-red at the root, orange-gold, straw at the tips. The arms: cream folds, rust edges.
uniform vec3 hair_root : source_color = vec3(0.45, 0.09, 0.05);
uniform vec3 hair : source_color = vec3(0.86, 0.4, 0.12);
uniform vec3 hair_tip : source_color = vec3(0.98, 0.78, 0.5);
uniform vec3 frill : source_color = vec3(0.99, 0.72, 0.5);
uniform vec3 frill_edge : source_color = vec3(0.66, 0.18, 0.08);
uniform float arm_alpha = 0.7;
uniform float hair_alpha = 0.85;

varying float part;
varying vec2 at;
varying float along;
varying float seed;
varying float fade;

void vertex() {
	part = COLOR.r;
	at = UV;
	seed = UV2.y;
	along = UV.y / max(COLOR.a, 0.001);
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
		// An oral arm: a cream curtain, deeply folded, its frilled edges rust; paler further down.
		float e = abs(at.x * 2.0 - 1.0);
		c = mix(frill, frill_edge, smoothstep(0.55, 0.95, e) * (1.0 - 0.5 * smoothstep(0.3, 1.0, along)));
		float pleat = 0.5 + 0.5 * sin(along * 140.0 + e * 6.0);
		c *= 0.86 + 0.2 * pleat;
		a = mix(arm_alpha, 0.92, smoothstep(0.6, 0.95, e));
		float cut = 0.95 + 0.05 * sin(along * 90.0 + seed * 20.0);
		a *= 1.0 - smoothstep(cut - 0.04, cut, e);
		float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
		a = clamp(a + edge * 0.15, 0.0, 0.96);
	} else {
		// A tentacle of the mane: rust-red at the root, orange-gold, straw towards its tip; each its own shade.
		float own = fract(seed * 7.13);
		c = mix(hair_root, hair, smoothstep(0.0, 0.08 + 0.12 * own, along));
		c = mix(c, hair_tip, smoothstep(0.45, 1.0, along) * (0.6 + 0.4 * own));
		c *= 0.8 + 0.35 * fract(seed * 13.7);
		float across = abs(at.x * 2.0 - 1.0);
		a = hair_alpha * fade * (1.0 - across * across) * (1.0 - 0.6 * smoothstep(0.7, 1.0, along)) * (0.55 + 0.45 * smoothstep(0.0, 0.12, along));
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
