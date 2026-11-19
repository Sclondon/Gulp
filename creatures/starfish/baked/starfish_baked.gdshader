shader_type spatial;
// The sea stars (starfish.gd): their colours, and all of their moving. What each point is comes from the
// model (tools/build_starfish.py): UV2.y the part (0 the disc, 1 an arm, 2 a tube foot, 3 a spine on an
// arm), UV2.x which arm it is on (arm k of n: k / n). UV, on the disc: x how far out, y how high; on an arm:
// x how far along it (of `arm_length`), y how high (0 its flat underside, 1 the top of its back); on a foot
// or a spine: y from its root (0) to its tip (1).
//
// Its arms bend in the vertex shader, each about the line where it leaves the disc: they lift and curl
// at their tips as it creeps (`phase`), snake from side to side (`writhe`), and `curl_up` lifts them all
// and rolls their tips over. All of it is a function of `phase` alone, so a picture of it loops exactly.
// The knobs of its skin are drawn here on a lattice in the plane of its top (the full model also has them
// in its shape, in the same places: the build script's knob_point is the same sum).
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
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


// How far through a beat (0..1, it wraps). Set by Starfish.
uniform float phase = 0.0;
// How strongly it moves at all (1 as it lives, 0 still).
uniform float sway = 1.0;
// 0 lying flat, 1 every arm lifted and its tip rolled over (a star turned on its back, or disturbed).
uniform float curl_up : hint_range(0.0, 1.0) = 0.0;
// How much its arm tips lift and fall as it creeps, and how much its arms snake from side to side.
uniform float tip_wave = 0.35;
uniform float writhe = 0.08;
// The kind's shape, as the model is built: from the middle to an arm's tip (metres), how many arms, and
// how far out (of the arm's length) an arm starts to lift.
uniform float arm_length = 0.135;
uniform float arms = 5.0;
uniform float lift_from = 0.3;

// The skin, the darker colour it is mottled with (or banded, for a brittle star), its knobs (and a
// brittle star's spines), its underside, its tube feet.
uniform vec3 skin : source_color = vec3(0.36, 0.12, 0.38);
uniform vec3 skin_dark : source_color = vec3(0.2, 0.06, 0.22);
uniform vec3 knob : source_color = vec3(0.92, 0.88, 0.8);
uniform vec3 under : source_color = vec3(0.88, 0.72, 0.52);
uniform vec3 foot : source_color = vec3(0.95, 0.78, 0.58);
// The knobs: the lattice's cell and a knob's radius (metres, as the build script's), and how much they show.
uniform float knob_cell = 0.0075;
uniform float knob_size = 0.0019;
uniform float knob_amount = 1.0;
// How much its skin is mottled, and banded across its arms (a brittle star's), and the bands' spacing.
uniform float mottle = 0.3;
uniform float bands = 0.0;
uniform float band_gap = 0.012;
// How much of its colour shows with no light on it.
uniform float vivid = 0.06;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;

// One arc of a bend in a plane: `a` along the arm, `b` out of the line it bends about; from `from` on, the
// arm is laid round a circle of curvature `k` (more than 0: towards +b). The normal turns with it.
void arc(inout float a, inout float b, inout float na, inout float nb, float from, float k) {
	if (a <= from || abs(k) < 0.001) {
		return;
	}
	float f = k * (a - from);
	float c = cos(f);
	float s = sin(f);
	float a2 = from + s / k - b * s;
	b = (1.0 - c) / k + b * c;
	a = a2;
	float n2 = na * c - nb * s;
	nb = na * s + nb * c;
	na = n2;
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	rest_normal = NORMAL;
	if (part > 0.5) {
		float angle = TAU * UV2.x;
		vec3 fwd = vec3(sin(angle), 0.0, -cos(angle));
		vec3 side = vec3(cos(angle), 0.0, sin(angle));
		float u = dot(VERTEX, fwd);
		float w = dot(VERTEX, side);
		float y = VERTEX.y;
		float nu = dot(NORMAL, fwd);
		float nw = dot(NORMAL, side);
		float ny = NORMAL.y;
		float turn = TAU * phase;
		// (each arm a little out of step with the next)
		float own = UV2.x * arms * 2.4;
		float from = lift_from * arm_length;
		float tip_from = 0.55 * arm_length;
		// Up: the tip rolled over, then the whole arm lifted from where it leaves the disc.
		float tip = curl_up * 2.1 + sway * tip_wave * (0.55 + 0.45 * sin(turn + own));
		arc(u, y, nu, ny, tip_from, tip / (arm_length - tip_from));
		float lift = curl_up * 1.35 + sway * tip_wave * 0.12 * (0.5 + 0.5 * sin(turn + own + 1.3));
		arc(u, y, nu, ny, from, lift / (arm_length - from));
		// Across: the arm snaking, its outer half one way while its inner half goes the other.
		float half_from = from + 0.5 * (arm_length - from);
		float outer = sway * writhe * 1.2 * sin(turn + own - 1.9);
		arc(u, w, nu, nw, half_from, outer / (arm_length - half_from));
		float inner = sway * writhe * 0.7 * sin(turn + own);
		arc(u, w, nu, nw, from, inner / (arm_length - from));
		vec3 v = fwd * u + side * w + vec3(0.0, y, 0.0);
		if (part > 1.5 && part < 2.5) {
			// a tube foot reaching and feeling about
			v += fwd * UV.y * arm_length * 0.006 * sway * sin(turn * 2.0 + UV.x * 61.0 + own);
		}
		VERTEX = v;
		NORMAL = normalize(fwd * nu + side * nw + vec3(0.0, ny, 0.0));
	}
}

uint hash32(uint x) {
	x ^= x >> 16u;
	x *= 0x7feb352du;
	x ^= x >> 15u;
	x *= 0x846ca68bu;
	x ^= x >> 16u;
	return x;
}

// A knob's middle in the lattice (the build script's knob_point).
vec2 knob_point(int i, int j) {
	uint seed = (uint(i + 4096) * 73856093u) ^ (uint(j + 4096) * 19349663u);
	uint a = hash32(seed);
	float jx = float(a & 65535u) / 65535.0;
	float jy = float((a >> 16u) & 65535u) / 65535.0;
	return vec2((float(i) + 0.5 * float(j & 1) + 0.6 * jx - 0.3) * knob_cell, (float(j) * 0.866 + 0.5 * jy - 0.25) * knob_cell);
}

// How far from the nearest knob's middle a point of the top is (in knob radii).
float knob_distance(vec2 p) {
	int j0 = int(floor(p.y / (0.866 * knob_cell)));
	float best = 9.0;
	for (int j = j0 - 1; j <= j0 + 1; j++) {
		int i0 = int(floor(p.x / knob_cell - 0.5 * float(j & 1)));
		for (int i = i0 - 1; i <= i0 + 1; i++) {
			best = min(best, length(p - knob_point(i, j)) / knob_size);
		}
	}
	return best;
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

