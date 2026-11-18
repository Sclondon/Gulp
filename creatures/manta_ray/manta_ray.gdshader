shader_type spatial;
// The giant oceanic manta ray (manta_ray.gd): every marking drawn here (no texture files), and
// everything that moves. What each point is comes from the model (tools/build_manta_ray.py): UV2.y
// the part (0 skin, 1 inside the mouth, 2 a cephalic fin, 3 the tail, 4 the dorsal fin, 5 a tail
// spine, 6 an eye). On the skin and in the mouth: UV.x the lower jaw's weight, UV.y from the
// leading edge (0) to the trailing edge (1), UV2.x +1 on top, -1 beneath, 0 along the edges. On a
// cephalic fin: UV.x root (0) to tip (1), UV.y metres across from its top edge, UV2.x metres off
// the middle of its sheet (+ its inner skin). On the tail: UV.x root to tip. On an eye: UV.x
// middle (0) to rim (1).
//
// It flies: each wing is bent upward and downward as a wave that runs out from its root to its
// tip, the tip lagging and curling; the back edge lags the front; the body pitches and rides up
// and down a little against the wings; the tail trails with a late wave of its own. All of it is
// a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
// (The vertex half below is the same in GameCommon's manta-ray, devil-ray and spotted-eagle-ray
// but for these numbers: improve one, copy it to the others.)
render_mode cull_back;

// Kept in step with the model (the builder prints them: its SHADER line).
const float HALF = 2.5;
const float DISC = 2.2;
const float TAIL_LENGTH = 1.5;
// The lower jaw's hinge (y, z) and how far it turns at `gape` 1 (radians).
const vec2 HINGE = vec2(-0.2012, -0.6);
const float JAW_TURN = 0.55;
// The cephalic fins (the one on +X; the other is its mirror).
const vec3 CEPH_ROOT = vec3(0.5, 0.035, -0.96);
const vec3 CEPH_ALONG = vec3(0.04969, -0.09938, -0.99381);
const vec3 CEPH_DOWN = vec3(-0.12429, -0.98792, 0.09258);
const vec3 CEPH_IN = vec3(-0.99100, 0.11892, -0.06144);
const float CEPH_LENGTH = 0.58;
const float CEPH_WIDTH = 0.30;
const float CEPH_ROLL0 = 11.0;
const float CEPH_ROLL1 = 18.0;
const float CEPH_CUP = 2.6;
// How far out along a wing (0 the middle line, 1 the tip) the wing starts to bend.
const float ROOT = 0.13;
// How far the wing is bent at its tip at the top of a stroke (radians), how much higher it goes
// than it comes down, how far the tip lags the root and the back edge the front (parts of a beat).
const float FLAP = 0.62;
const float LIFT = 0.1;
const float TIP_LAG = 0.24;
const float BACK_LAG = 0.1;
// How far the body pitches (radians) and rides up and down (metres) at `sway` 1.
const float PITCH = 0.045;
const float HEAVE = 0.07;

// How far through a beat of its wings (0..1, it wraps). Set by MantaRay.
uniform float phase = 0.0;
// How widely it beats: 1 cruising, 0 gliding with its wings held still.
uniform float sway = 1.0;
// Turning: more than 0 it banks into a turn towards +X (as the fish's `curl`, whose tails come
// round to +X). At `curl` c: the whole animal is rolled 0.6 c radians about its long axis, its +X
// side down; the +X wing (inside the turn) droops a further 0.35 c radians by its tip and the
// other lifts 0.35 c; the tail trails round to +X, c radians by its tip.
uniform float curl = 0.0;
// The mouth: 0 shut, 1 wide open, as it is held when it feeds.
uniform float gape = 0.0;
// The cephalic fins: 0 rolled up into horns, 1 unrolled into scoops beside the mouth.
uniform float scoops = 0.0;

// The back; the blue-grey it glances; the pale shoulder marks; the belly; its dark spots and
// the grey of its rear edge; the inside of the mouth.
uniform vec3 back : source_color = vec3(0.022, 0.024, 0.03);
uniform vec3 back_sheen : source_color = vec3(0.1, 0.13, 0.18);
uniform vec3 shoulder : source_color = vec3(0.74, 0.76, 0.78);
uniform vec3 belly : source_color = vec3(0.93, 0.93, 0.91);
uniform vec3 belly_dark : source_color = vec3(0.07, 0.07, 0.085);
uniform vec3 mouth_inside : source_color = vec3(0.06, 0.03, 0.04);
// How strongly the shoulder marks and the belly's spots show.
uniform float shoulder_show = 1.0;
uniform float spots_show = 1.0;

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

// A point of a cephalic fin and the way its skin faces: `t` along it, `h` metres across from its
// top edge, `off` metres off the middle of its sheet; `sx` which side. The sheet is curled across
// its width: tightly, more so towards its free edge, when rolled (a spiral, the horn); gently
// when spread (the scoop).
void ceph_point(float t, float h, float off, float sx, out vec3 p, out vec3 n) {
	float open = clamp(scoops, 0.0, 1.0);
	float k0 = mix(CEPH_ROLL0, CEPH_CUP, open);
	float k1 = CEPH_ROLL1 * (1.0 - open) / (2.0 * CEPH_WIDTH);
	vec2 q = vec2(0.0);
	float dh = h / 12.0;
	for (int i = 0; i < 12; i++) {
		float hm = (float(i) + 0.5) * dh;
		float th = k0 * hm + k1 * hm * hm;
		q += vec2(cos(th), sin(th)) * dh;
	}
	float th = k0 * h + k1 * h * h;
	vec3 flip = vec3(sx, 1.0, 1.0);
	vec3 normal = (CEPH_IN * cos(th) - CEPH_DOWN * sin(th)) * flip;
	p = (CEPH_ROOT + CEPH_ALONG * (t * CEPH_LENGTH) + CEPH_DOWN * q.x + CEPH_IN * q.y) * flip + normal * off;
	n = normal * (off >= 0.0 ? 1.0 : -1.0);
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
	if (part > 1.5 && part < 2.5) {
		ceph_point(UV.x, UV.y, UV2.x, v.x >= 0.0 ? 1.0 : -1.0, v, n);
	} else if (part < 1.5 && UV.x > 0.0) {
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
	v.y += sway * 0.05 * TAIL_LENGTH * pow(f, 1.5) * sin(6.2831853 * (phase - 0.2 - 0.9 * f));
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

// How much of a soft-edged ellipse at `at`, turned by `turn`, of half sizes `size`, covers `p`.
float patch_of(vec2 p, vec2 at, vec2 size, float turn, float edge) {
	vec2 d = p - at;
	d = vec2(d.x * cos(turn) + d.y * sin(turn), d.y * cos(turn) - d.x * sin(turn)) / size;
	return 1.0 - smoothstep(1.0 - edge, 1.0 + edge, length(d));
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	// (where a point is on the animal: across, 0 the middle line to 1 a wing tip; along, 0 the
	// mouth to 1 the back of the disc)
	vec2 at = vec2(abs(rest.x) / HALF, rest.z / DISC + 0.5);
	vec3 c;
	float rough = 0.5;
	float spec = 0.4;
	if (p == 0) {
		float cloud = noise2(at * vec2(9.0, 7.0) + 3.0);
		float fine = noise2(at * vec2(60.0, 50.0));
		// Above: black, with the pale shoulder marks: a bar across each shoulder behind the head,
		// hooked back at its outer end, and a pale flash by each wing tip.
		float wobble = (cloud - 0.5) * 0.25;
		float mark = patch_of(at, vec2(0.19, 0.17), vec2(0.165, 0.05), 0.22, 0.25 + wobble);
		mark = max(mark, patch_of(at, vec2(0.335, 0.27), vec2(0.04, 0.1), 0.55, 0.3 + wobble));
		mark *= smoothstep(0.02, 0.06, at.x);
		float flash = patch_of(at, vec2(0.86, 0.5), vec2(0.1, 0.03), 0.25, 0.6) * 0.45;
		vec3 above = back * (0.85 + 0.3 * fine) + back_sheen * glance * glance;
		above = mix(above, shoulder * (0.9 + 0.1 * fine), clamp(max(mark, flash) * shoulder_show, 0.0, 1.0));
		// Beneath: white; five gill slits a side; dark spots on the belly between and behind
		// them; a grey margin along the back edge of the wings; the lower lip dark.
		vec3 below = belly * (0.94 + 0.06 * fine);
		float margin = smoothstep(0.72, 1.0, UV.y) * smoothstep(0.08, 0.3, at.x);
		below = mix(below, belly_dark * 3.5, margin * 0.6);
		for (int i = 0; i < 5; i++) {
			float k = float(i);
			// (each slit a shallow arc, shorter towards the back)
			float inner = 0.05 + 0.004 * k;
			float outer = 0.155 - 0.016 * k;
			float mid = 0.5 * (inner + outer);
			float along = 0.2 + 0.052 * k + 0.9 * (at.x - mid) * (at.x - mid) / (outer - inner) - 0.05 * (at.x - mid);
			float slit = (1.0 - smoothstep(0.003, 0.007, abs(at.y - along))) * smoothstep(inner - 0.004, inner + 0.004, at.x) * (1.0 - smoothstep(outer - 0.004, outer + 0.004, at.x));
			below = mix(below, belly_dark, slit * 0.92);
		}
		vec2 cell = vec2(rest.x, rest.z) / 0.11;
		vec2 id = floor(cell);
		vec2 in_cell = fract(cell) - 0.5 - 0.5 * (vec2(hash2(id), hash2(id + 17.0)) - 0.5);
		float size = 0.12 + 0.2 * hash2(id + 5.0);
		float spot = (1.0 - smoothstep(size * 0.75, size, length(in_cell))) * step(0.42, hash2(id + 9.0));
		float where = (1.0 - smoothstep(0.1, 0.2, at.x)) * smoothstep(0.42, 0.52, at.y) * (1.0 - smoothstep(0.78, 0.9, at.y));
		below = mix(below, belly_dark, spot * where * spots_show);
		float lip = (1.0 - smoothstep(0.0, 0.035, at.y)) * (1.0 - smoothstep(0.15, 0.175, at.x));
		below = mix(below, belly_dark * 1.6, lip * 0.85);
		c = mix(below, above, smoothstep(-0.25, 0.35, topness));
		rough = mix(0.55, 0.42, smoothstep(-0.2, 0.2, topness));
	} else if (p == 1) {
		c = mouth_inside;
		rough = 0.8;
		spec = 0.1;
	} else if (p == 2) {
		// A cephalic fin: black outside, pale inside.
		float inner = smoothstep(-0.002, 0.002, topness);
		c = mix(back + back_sheen * glance * glance, belly * 0.8, inner * smoothstep(0.02, 0.15, UV.x));
	} else if (p == 6) {
		// An eye: dark, a thin paler ring.
		float r = UV.x;
		c = mix(vec3(0.004, 0.005, 0.008), vec3(0.2, 0.2, 0.19), smoothstep(0.5, 0.6, r) * (1.0 - smoothstep(0.75, 0.9, r)));
		c = mix(c, back, smoothstep(0.85, 1.0, r));
		rough = 0.15;
		spec = 0.6;
	} else {
		// The tail and the dorsal fin: black.
		c = back + back_sheen * glance * glance;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
