shader_type spatial;
// The clams (clam.gd): a giant clam, a scallop and a razor clam. Their colours and all their moving, in one
// shader; `kind` says which (Clam sets it, and every setting below, for its kind).
//
// What each point is comes from the model (tools/build_clam.py): UV2.y the part (0 the shell's outside, 1 its
// inside, 2 its lip, 3 a mantle, 4 a tentacle, 6 the razor clam's foot, 7 a siphon). UV2.x which way it swings
// as the shell opens (0 with the lower or right valve, 1 with the upper or left; across the giant clam's mantle,
// 0 its right edge to 1 its left). UV on the shell: x from the hinge (0) to the edge (1), y round it (0..1; the
// razor clam's: x along it from the front, y across from its hinged edge); on the giant clam's mantle: x along
// it, y across; on a scallop's mantle edge: x round it, y from its root (0) to its edge (1); on anything else x
// from its root (0) to its tip (1). COLOR.r on the giant clam's mantle: 1 its upper face.
//
// The models are built shut (the giant clam's mantle, open); `open` swings the valves about the hinge
// (`hinge_at`, `hinge_axis`; the lower or right valve by `lower_turn` radians at 1, the upper or left by
// `upper_turn`). All the moving is a function of `phase` alone, so a film of it loops exactly. Nothing here
// needs more than GL Compatibility has.
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


// Which clam: 0 the giant clam, 1 the scallop, 2 the razor clam.
uniform int kind = 0;
uniform float body_length = 1.0;
// How far through a beat (0..1, it wraps). Set by Clam.
uniform float phase = 0.0;
// How strongly it moves at all (1 as it lives, 0 still).
uniform float sway = 1.0;
// How far open its shell is (0 shut, 1 as wide as it opens).
uniform float open : hint_range(0.0, 1.0) = 0.0;
// The scallop: 0 lying still, 1 swimming, clapping its shell shut once a beat (`open` is then ignored).
uniform float swim : hint_range(0.0, 1.0) = 0.0;
// The razor clam: 0 lying on its side, 1 digging: stood up on its front end, its foot pumping down.
uniform float dig : hint_range(0.0, 1.0) = 0.0;
// The hinge: a point on it, the way it runs, and how far each valve turns about it at `open` 1.
uniform vec3 hinge_at = vec3(0.0);
uniform vec3 hinge_axis = vec3(0.0, 0.0, 1.0);
uniform float upper_turn = -0.2;
uniform float lower_turn = 0.2;

// The colours (Clam sets them for each kind): the outside of the shell (its upper or left valve, and its
// lower or right one), the inside, the lip; the mantle and its markings; the foot, tentacles or siphons.
uniform vec3 shell : source_color = vec3(0.82, 0.8, 0.74);
uniform vec3 shell_lower : source_color = vec3(0.82, 0.8, 0.74);
uniform vec3 shell_dark : source_color = vec3(0.45, 0.42, 0.34);
uniform vec3 inside : source_color = vec3(0.95, 0.94, 0.9);
uniform vec3 lip : source_color = vec3(0.85, 0.8, 0.66);
uniform vec3 mantle : source_color = vec3(0.04, 0.3, 0.4);
uniform vec3 mantle_mark : source_color = vec3(0.2, 0.75, 0.8);
uniform vec3 mantle_edge : source_color = vec3(0.15, 0.35, 0.95);
uniform vec3 flesh : source_color = vec3(0.9, 0.75, 0.6);
uniform vec3 flesh_dark : source_color = vec3(0.4, 0.25, 0.15);
// How much of its colour shows without any light on it (the giant clam's mantle glows a little).
uniform float vivid = 0.05;

// The razor clam's size and its foot's root (kept in step with the build script).
const float RAZOR_HALF = 0.075;
const float RAZOR_FOOT = -0.061;

varying vec3 rest;
varying float part;
varying float mark;

// Turns p (and n) about the line through `at` along `axis` (a unit vector) by `a` radians.
void turn_about(inout vec3 p, inout vec3 n, vec3 at, vec3 axis, float a) {
	float c = cos(a);
	float s = sin(a);
	vec3 d = p - at;
	p = at + d * c + cross(axis, d) * s + axis * dot(axis, d) * (1.0 - c);
	n = n * c + cross(axis, n) * s + axis * dot(axis, n) * (1.0 - c);
}

// A scallop's clap through a beat: open, snapped shut quickly, then opening slowly again.
float clap(float p) {
	return p < 0.16 ? 1.0 - smoothstep(0.0, 0.16, p) : smoothstep(0.16, 0.92, p);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	mark = COLOR.r;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	float turn = TAU * phase;
	float opened = open;
	if (kind == 1) {
		opened = mix(open, clap(phase), swim);
	}
	if (kind == 0 && p == 3) {
		// THE GIANT CLAM'S MANTLE, built as it is wide open: as the clam shuts it is drawn in narrow and
		// down, out of sight inside the shell; open, it heaves slowly.
		float m = smoothstep(0.25, 1.0, opened);
		vec3 shut = vec3(v.x * 0.15, v.y * 0.5, v.z * 0.7);
		v = mix(shut, v, m);
		v.y += m * sway * 0.008 * sin(turn - v.z * 6.0) * smoothstep(0.0, 0.3, UV.y) * smoothstep(1.0, 0.7, UV.y);
	} else {
		if (kind == 1 && p == 4) {
			// a scallop's tentacles draw in as it shuts, and wave a little
			vec3 out_way = normalize(vec3(v.x - hinge_at.x, 0.0, v.z - hinge_at.z));
			v -= out_way * UV.x * 0.0065 * (1.0 - smoothstep(0.1, 0.7, opened));
			v.y += UV.x * UV.x * 0.0012 * sway * sin(turn * 2.0 + UV.y * 6.0);
		}
		if (kind == 2 && p == 6) {
			// THE RAZOR CLAM'S FOOT: it pushes out long and thin, swells at its tip to grip, and draws back
			// (harder as it digs).
			float pump = sway * mix(0.35, 1.0, dig);
			float e = 1.0 + pump * 0.45 * sin(turn);
			float grip = pump * max(0.0, -sin(turn - 0.6)) * smoothstep(0.55, 0.95, UV.x);
			vec2 across = v.xy - vec2(0.0, hinge_at.y);
			across *= (1.0 + 0.5 * grip) / sqrt(e);
			v.xy = vec2(0.0, hinge_at.y) + across;
			v.z = RAZOR_FOOT + (v.z - RAZOR_FOOT) * e;
		}
		if (kind == 2 && p == 7) {
			v.z += sway * 0.0015 * UV.x * sin(turn + UV.y * 3.0);
		}
		float w = UV2.x;
		turn_about(v, n, hinge_at, hinge_axis, opened * mix(lower_turn, upper_turn, w));
	}
	if (kind == 2 && dig > 0.0) {
		// Digging: stood up on its front end (which goes into the sand: the game sinks it).
		vec3 at = vec3(0.0, 0.0, -RAZOR_HALF);
		turn_about(v, n, at, vec3(1.0, 0.0, 0.0), -dig * 1.25);
	}
	VERTEX = v;
	NORMAL = n;
}

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

float noise2(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash2(i), hash2(i + vec2(1.0, 0.0)), f.x), mix(hash2(i + vec2(0.0, 1.0)), hash2(i + vec2(1.0, 1.0)), f.x), f.y);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

