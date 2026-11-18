shader_type spatial;
// The spotted eagle ray (spotted_eagle_ray.gd): every marking drawn here (no texture files), and
// everything that moves. What each point is comes from the model
// (tools/build_spotted_eagle_ray.py): UV2.y the part (0 skin, 1 inside the mouth, 3 the tail,
// 4 the dorsal fin, 5 a tail spine, 6 an eye). On the skin and in the mouth: UV.x the lower jaw's
// weight, UV.y from the leading edge (0) to the trailing edge (1), UV2.x +1 on top, -1 beneath,
// 0 along the edges. On the tail: UV.x root to tip. On a fin or a spine: UV.x root to tip. On an
// eye: UV.x middle (0) to rim (1).
//
// It flies: each wing is bent upward and downward as a wave that runs out from its root to its
// tip, the tip lagging and curling; the back edge lags the front; the body pitches and rides up
// and down a little against the wings; the long tail trails with a late wave of its own. All of
// it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
// (The vertex half below is the same in GameCommon's manta-ray, devil-ray and spotted-eagle-ray
// but for these numbers and the cephalic fins, which this ray has not: improve one, copy it to
// the others.)
render_mode cull_back;

// Kept in step with the model (the builder prints them: its SHADER line).
const float HALF = 1.0;
const float DISC = 1.15;
const float TAIL_LENGTH = 2.7;
// The lower jaw's hinge (y, z) and how far it turns at `gape` 1 (radians).
const vec2 HINGE = vec2(-0.0801, -0.365);
const float JAW_TURN = 0.75;
// The mouth, as the markings need it: how far back it is (of the disc) and its half width (of a wing).
const float MOUTH_AT = 0.1217;
const float MOUTH_HALF = 0.05;
// How far out along a wing (0 the middle line, 1 the tip) the wing starts to bend.
const float ROOT = 0.14;
// How far the wing is bent at its tip at the top of a stroke (radians), how much higher it goes
// than it comes down, how far the tip lags the root and the back edge the front (parts of a beat).
const float FLAP = 0.7;
const float LIFT = 0.1;
const float TIP_LAG = 0.24;
const float BACK_LAG = 0.1;
// How far the body pitches (radians) and rides up and down (metres) at `sway` 1.
const float PITCH = 0.05;
const float HEAVE = 0.03;

// How far through a beat of its wings (0..1, it wraps). Set by SpottedEagleRay.
uniform float phase = 0.0;
// How widely it beats: 1 cruising, 0 gliding with its wings held still.
uniform float sway = 1.0;
// Turning: more than 0 it banks into a turn towards +X (as the fish's `curl`, whose tails come
// round to +X). At `curl` c: the whole animal is rolled 0.6 c radians about its long axis, its +X
// side down; the +X wing (inside the turn) droops a further 0.35 c radians by its tip and the
// other lifts 0.35 c; the tail trails round to +X, c radians by its tip.
uniform float curl = 0.0;
// The mouth (a slit under the head): 0 shut, 1 wide open.
uniform float gape = 0.0;

// The back (a dark blue-black) and the blue it glances; its white spots and rings; the belly;
// the dusk of the wings' edges beneath; the gill slits and the line of the mouth; the tail; its
// spines; the inside of the mouth.
uniform vec3 back : source_color = vec3(0.028, 0.04, 0.075);
uniform vec3 back_blue : source_color = vec3(0.07, 0.14, 0.3);
uniform vec3 spot : source_color = vec3(0.92, 0.94, 0.95);
uniform vec3 belly : source_color = vec3(0.95, 0.95, 0.93);
uniform vec3 belly_dusk : source_color = vec3(0.3, 0.33, 0.4);
uniform vec3 slit_dark : source_color = vec3(0.1, 0.1, 0.13);
uniform vec3 tail_dark : source_color = vec3(0.02, 0.025, 0.04);
uniform vec3 spine : source_color = vec3(0.62, 0.58, 0.5);
uniform vec3 mouth_inside : source_color = vec3(0.07, 0.03, 0.04);
// How strongly the spots show, and how far apart they are (metres).
uniform float spots_show = 1.0;
uniform float spots_apart = 0.072;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float topness;

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

// How far a wing is bent upward (radians) `e` of the way from where it starts to bend (0) to its
// tip (1), for a point `back_part` of a beat behind the front edge; `side` +1 the +X wing.
float wing_angle(float e, float back_part, float side) {
	float beat = 6.2831853 * (phase - TIP_LAG * e - back_part);
	float bend = pow(e, 1.15);
	// (the tip curls on past the rest of the wing, later still)
	float tip = 0.45 * pow(e, 4.0) * sin(beat - 0.9);
	return sway * (FLAP * (bend * sin(beat) + tip) + LIFT * bend) - side * 0.35 * curl * bend;
}

void vertex() {
	part = UV2.y;
	topness = UV2.x;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part < 1.5 && UV.x > 0.0) {
		// The lower jaw turns down about its hinge.
		float a = clamp(gape, 0.0, 1.0) * JAW_TURN * UV.x;
		vec2 d = v.yz - HINGE;
		v.yz = HINGE + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	}
	// The wings: from where they start to bend, each line across a wing is laid along a curve
	// whose slope is `wing_angle`, its length kept.
	float side = v.x >= 0.0 ? 1.0 : -1.0;
	float out_x = abs(v.x) / HALF;
	if (out_x > ROOT) {
		float e1 = (out_x - ROOT) / (1.0 - ROOT);
		float back_part = BACK_LAG * (v.z / DISC + 0.5);
		vec2 q = vec2(0.0);
		float de = e1 / 8.0;
		for (int i = 0; i < 8; i++) {
			float a = wing_angle((float(i) + 0.5) * de, back_part, side);
			q += vec2(cos(a), sin(a)) * de;
		}
		q *= (1.0 - ROOT) * HALF;
		float a = wing_angle(e1, back_part, side);
		float c = cos(a);
		float s = sin(a);
		float nx = n.x * side;
		v = vec3(side * (ROOT * HALF + q.x - s * v.y), q.y + c * v.y, v.z);
		n = vec3(side * (nx * c - n.y * s), nx * s + n.y * c, n.z);
	}
	// The tail: a wave that runs back along it, late, and grows towards its tip; round to +X
	// with `curl`.
	float behind = max(v.z - (DISC * 0.5 - 0.08 * DISC), 0.0);
	float f = behind / TAIL_LENGTH;
	v.y += sway * 0.035 * TAIL_LENGTH * pow(f, 1.3) * sin(6.2831853 * (phase - 0.2 - 1.6 * f));
	v.x += curl * behind * behind / (2.0 * TAIL_LENGTH);
	// The body pitches, and rides down as the wings go up.
	float pitch = sway * PITCH * cos(6.2831853 * phase);
	float pc = cos(pitch);
	float ps = sin(pitch);
	v = vec3(v.x, v.y * pc - v.z * ps, v.z * pc + v.y * ps);
	n = vec3(n.x, n.y * pc - n.z * ps, n.z * pc + n.y * ps);
	v.y -= sway * HEAVE * sin(6.2831853 * (phase - 0.08));
	// Banked into a turn: rolled about its long axis, its +X side down.
	float bank = 0.6 * curl;
	float bc = cos(bank);
	float bs = sin(bank);
	v = vec3(v.x * bc + v.y * bs, v.y * bc - v.x * bs, v.z);
	n = vec3(n.x * bc + n.y * bs, n.y * bc - n.x * bs, n.z);
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	// (where a point is on the animal: across, 0 the middle line to 1 a wing tip; along, 0 the
	// tip of the snout to 1 the back of the disc)
	vec2 at = vec2(abs(rest.x) / HALF, rest.z / DISC + 0.5);
	vec3 c;
	float rough = 0.5;
	float spec = 0.4;
	if (p == 0) {
		float fine = noise2(at * vec2(70.0, 80.0));
		// Above: blue-black, covered in white spots, some of them rings: one to a cell of a
		// grid laid over the back, each pushed about in its cell, a few cells left empty.
		vec3 above = back * (0.85 + 0.3 * fine) + back_blue * (0.25 * smoothstep(0.2, 1.0, at.x) + 0.7 * glance * glance);
		vec2 cell = vec2(rest.x, rest.z) / spots_apart + vec2(0.5, 0.0);
		vec2 id = floor(cell);
		vec2 in_cell = (fract(cell) - 0.5 - 0.45 * (vec2(hash2(id), hash2(id + 17.0)) - 0.5)) * spots_apart;
		float kind = hash2(id + 9.0);
		float size = 0.011 + 0.011 * hash2(id + 5.0);
		float far = length(in_cell);
		float dot_mark = 1.0 - smoothstep(size * 0.7, size, far);
		float ring_mark = (1.0 - smoothstep(0.004, 0.007, abs(far - 0.017 - 0.4 * size)));
		float mark = kind < 0.1 ? 0.0 : (kind > 0.78 ? ring_mark : dot_mark);
		// (drawn from above: left off where the skin stands too steeply to take them)
		mark *= smoothstep(0.45, 0.75, rest_normal.y);
		// (none on the bill, fewer on the head)
		mark *= smoothstep(0.03, 0.2, at.y + at.x);
		above = mix(above, spot, mark * spots_show);
		// Beneath: white, dusky along the wings' back edges and at their tips; five short gill
		// slits a side; the line of the mouth.
		vec3 below = belly * (0.95 + 0.05 * fine);
		below = mix(below, belly_dusk, 0.6 * smoothstep(0.8, 1.0, UV.y) * smoothstep(0.1, 0.3, at.x) + 0.5 * smoothstep(0.75, 1.0, at.x));
		for (int i = 0; i < 5; i++) {
			float k = float(i);
			float inner = 0.045 + 0.004 * k;
			float outer = 0.115 - 0.009 * k;
			float mid = 0.5 * (inner + outer);
			float along = 0.27 + 0.036 * k + 0.9 * (at.x - mid) * (at.x - mid) / (outer - inner) - 0.05 * (at.x - mid);
			float slit = (1.0 - smoothstep(0.002, 0.005, abs(at.y - along))) * smoothstep(inner - 0.003, inner + 0.003, at.x) * (1.0 - smoothstep(outer - 0.003, outer + 0.003, at.x));
			below = mix(below, slit_dark, slit * 0.9);
		}
		float lips = (1.0 - smoothstep(0.003, 0.008, abs(at.y - MOUTH_AT))) * (1.0 - smoothstep(MOUTH_HALF - 0.008, MOUTH_HALF, at.x));
		below = mix(below, slit_dark, lips * 0.8);
		c = mix(below, above, smoothstep(-0.25, 0.35, topness));
		rough = mix(0.55, 0.4, smoothstep(-0.2, 0.2, topness));
	} else if (p == 1) {
		c = mouth_inside;
		rough = 0.8;
		spec = 0.1;
	} else if (p == 5) {
		// A tail spine: bone pale, darker at its root.
		c = mix(tail_dark, spine, smoothstep(0.0, 0.3, UV.x));
		rough = 0.35;
	} else if (p == 6) {
		// An eye: dark, a thin gold ring.
		float r = UV.x;
		c = mix(vec3(0.004, 0.005, 0.008), vec3(0.45, 0.36, 0.16), smoothstep(0.5, 0.6, r) * (1.0 - smoothstep(0.75, 0.9, r)));
		c = mix(c, back, smoothstep(0.85, 1.0, r));
		rough = 0.15;
		spec = 0.6;
	} else {
		// The tail and the dorsal fin: near black; the tail a little paler beneath at its root.
		c = tail_dark + back_blue * 0.4 * glance * glance;
		if (p == 3) {
			c = mix(c, belly * 0.7, (1.0 - smoothstep(-0.02, 0.1, UV.x)) * smoothstep(0.1, -0.5, rest_normal.y) * 0.7);
		}
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
