shader_type spatial;
// Munk's devil ray (devil_ray.gd): every marking drawn here (no texture files), and everything
// that moves. What each point is comes from the model (tools/build_devil_ray.py): UV2.y the part
// (0 skin, 1 inside the mouth, 2 a cephalic fin, 3 the tail, 4 the dorsal fin, 5 a tail spine,
// 6 an eye). On the skin and in the mouth: UV.x the lower jaw's weight, UV.y from the leading
// edge (0) to the trailing edge (1), UV2.x +1 on top, -1 beneath, 0 along the edges. On a
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
const float HALF = 0.5;
const float DISC = 0.52;
const float TAIL_LENGTH = 0.5;
// The lower jaw's hinge (y, z) and how far it turns at `gape` 1 (radians).
const vec2 HINGE = vec2(-0.0473, -0.17);
const float JAW_TURN = 0.75;
// The mouth, as the markings need it: how far back it is (of the disc) and its half width (of a wing).
const float MOUTH_AT = 0.0769;
const float MOUTH_HALF = 0.104;
// The cephalic fins (the one on +X; the other is its mirror).
const vec3 CEPH_ROOT = vec3(0.07, 0.004, -0.215);
const vec3 CEPH_ALONG = vec3(0.11767, -0.15689, -0.98058);
const vec3 CEPH_DOWN = vec3(-0.25908, -0.95809, 0.12221);
const vec3 CEPH_IN = vec3(-0.95866, 0.23967, -0.15339);
const float CEPH_LENGTH = 0.105;
const float CEPH_WIDTH = 0.05;
const float CEPH_ROLL0 = 66.0;
const float CEPH_ROLL1 = 108.0;
const float CEPH_CUP = 14.0;
// How far out along a wing (0 the middle line, 1 the tip) the wing starts to bend.
const float ROOT = 0.15;
// How far the wing is bent at its tip at the top of a stroke (radians), how much higher it goes
// than it comes down, how far the tip lags the root and the back edge the front (parts of a beat).
const float FLAP = 0.72;
const float LIFT = 0.08;
const float TIP_LAG = 0.2;
const float BACK_LAG = 0.1;
// How far the body pitches (radians) and rides up and down (metres) at `sway` 1.
const float PITCH = 0.06;
const float HEAVE = 0.014;

// How far through a beat of its wings (0..1, it wraps). Set by DevilRay.
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
// The cephalic fins: 0 rolled up into short horns, 1 unrolled into scoops beside the mouth.
uniform float scoops = 0.0;

// The back (a brown mauve) and the paler mauve it turns to towards the wings' edges and where
// light glances off it; the dark collar across the back of the head; the belly; the grey of the
// wing tips beneath; the gill slits and the line of the mouth; the inside of the mouth.
uniform vec3 back : source_color = vec3(0.2, 0.15, 0.19);
uniform vec3 back_pale : source_color = vec3(0.36, 0.3, 0.37);
uniform vec3 collar : source_color = vec3(0.045, 0.035, 0.05);
uniform vec3 belly : source_color = vec3(0.94, 0.94, 0.92);
uniform vec3 belly_grey : source_color = vec3(0.5, 0.5, 0.54);
uniform vec3 slit_dark : source_color = vec3(0.12, 0.1, 0.12);
uniform vec3 mouth_inside : source_color = vec3(0.07, 0.03, 0.04);
// How strongly the collar shows.
uniform float collar_show = 1.0;

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

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	// (where a point is on the animal: across, 0 the middle line to 1 a wing tip; along, 0 the
	// snout to 1 the back of the disc)
	vec2 at = vec2(abs(rest.x) / HALF, rest.z / DISC + 0.5);
	vec3 c;
	float rough = 0.5;
	float spec = 0.4;
	vec3 dusk = mix(back, back_pale, 0.5 * glance * glance);
	if (p == 0) {
		float cloud = noise2(at * vec2(9.0, 7.0) + 3.0);
		float fine = noise2(at * vec2(70.0, 60.0));
		// Above: brown mauve, darkest down the middle of the back, paler out along the wings; a
		// dark collar across the back of the head from wing to wing, swept back at its ends.
		vec3 above = mix(back, back_pale, 0.55 * smoothstep(0.1, 0.9, at.x) + 0.4 * glance * glance);
		above *= 0.9 + 0.2 * fine;
		float line = 0.165 + 0.3 * at.x * at.x + (cloud - 0.5) * 0.02;
		float band = (1.0 - smoothstep(0.035, 0.075, abs(at.y - line))) * (1.0 - smoothstep(0.34, 0.62, at.x));
		above = mix(above, collar, band * collar_show * 0.92);
		// (the snout before the collar is a shade paler)
		above = mix(above, back_pale, 0.35 * (1.0 - smoothstep(0.04, 0.1, at.y)) * (1.0 - smoothstep(0.1, 0.2, at.x)));
		// Beneath: white, greying towards the wing tips and along their back edges; five short
		// gill slits a side; the line of the mouth.
		vec3 below = belly * (0.95 + 0.05 * fine);
		below = mix(below, belly_grey, 0.75 * smoothstep(0.55, 1.0, at.x) + 0.35 * smoothstep(0.8, 1.0, UV.y) * smoothstep(0.1, 0.3, at.x));
		for (int i = 0; i < 5; i++) {
			float k = float(i);
			float inner = 0.05 + 0.004 * k;
			float outer = 0.14 - 0.013 * k;
			float mid = 0.5 * (inner + outer);
			float along = 0.2 + 0.05 * k + 0.9 * (at.x - mid) * (at.x - mid) / (outer - inner) - 0.05 * (at.x - mid);
			float slit = (1.0 - smoothstep(0.003, 0.007, abs(at.y - along))) * smoothstep(inner - 0.004, inner + 0.004, at.x) * (1.0 - smoothstep(outer - 0.004, outer + 0.004, at.x));
			below = mix(below, slit_dark, slit * 0.9);
		}
		float lips = (1.0 - smoothstep(0.004, 0.012, abs(at.y - MOUTH_AT))) * (1.0 - smoothstep(MOUTH_HALF - 0.012, MOUTH_HALF, at.x));
		below = mix(below, slit_dark, lips * 0.8);
		c = mix(below, above, smoothstep(-0.25, 0.35, topness));
		rough = mix(0.55, 0.45, smoothstep(-0.2, 0.2, topness));
	} else if (p == 1) {
		c = mouth_inside;
		rough = 0.8;
		spec = 0.1;
	} else if (p == 2) {
		// A cephalic fin: mauve outside, pale inside.
		float inner = smoothstep(-0.0005, 0.0005, topness);
		c = mix(dusk, belly * 0.75, inner * smoothstep(0.02, 0.15, UV.x));
	} else if (p == 6) {
		// An eye: dark, a thin paler ring.
		float r = UV.x;
		c = mix(vec3(0.004, 0.005, 0.008), vec3(0.3, 0.27, 0.22), smoothstep(0.5, 0.6, r) * (1.0 - smoothstep(0.75, 0.9, r)));
		c = mix(c, back, smoothstep(0.85, 1.0, r));
		rough = 0.15;
		spec = 0.6;
	} else {
		// The tail and the dorsal fin: dark mauve (the fin's tip pale).
		c = mix(back * 0.6, back, glance);
		if (p == 4) {
			c = mix(c, back_pale * 1.6, smoothstep(0.7, 0.95, UV.x));
		}
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
