shader_type spatial;
// The stoplight parrotfish (parrotfish.gd): every marking drawn here (no texture files), its
// rowing pectoral fins, its trailing tail and its working jaw. What each point is comes from the
// model (tools/build_parrotfish.py): UV2.y the part (0 body, 1 lower jaw, 2 dorsal fin, 3 anal
// fin, 4 tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body and jaw: x how far
// along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x
// root (0) to edge (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim
// (1). UV2.x, on the body and jaw, how much the point is inside the mouth; on the dorsal fin, how
// far it stands above the fin's root.
//
// It swims as parrotfish do (labriform): it rows with its pectoral fins, both together, its body
// bobbing a little with each stroke, its tail trailing and only beating hard (`sway`) when it
// hurries. All of it is a function of `phase` alone, so a picture of it loops exactly. Nothing
// here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model (tools/build_parrotfish.py), in body lengths.
const float LENGTH = 0.5;
// Where the tail fin is hinged: behind it the tail is one plate.
const float JOINT = 0.82;
// How far the tail wrist swings to each side at `sway` 1 (a parrotfish's tail mostly trails).
const float SWING = 0.045;
// The jaw's hinge, where the line of the mouth starts and how it bows; how far the jaw swings
// down at `gape` 1 (radians); how far the snout (the upper beak) lifts, from where, about what
// height.
const float HINGE_S = 0.075;
const float HINGE_Y = -0.05;
const float MOUTH_Y0 = -0.024;
const float MOUTH_BOW = 1.3;
const float GAPE_ANGLE = 0.6;
const float LIFT = 0.1;
const float LIFT_TO = 0.075;
const float LIFT_Y = 0.03;
// A pectoral fin's root (to the side, up, along); how far it rows back and forth and flaps up
// and down (radians); whether the two row in turn (1) or together (0); how far it folds in
// when `scull` is 0.
const vec3 PEC_ROOT = vec3(0.0682, -0.005, 0.265);
const float PEC_SWING = 0.55;
const float PEC_FLAP = 0.4;
const float PEC_ALT = 0.0;
const float PEC_HOLD = -0.3;
// How far the body rises and falls, and pitches, with each stroke at `scull` 1.
const float BOB = 0.006;
const float BOB_PITCH = 0.025;
const float FIN_WAVE = 0.006;
// How much of the dorsal fin is spines.
const float SPINE_SHARE = 0.5;
// The gill cover's edge (its rearmost reach, at what height, how it curves); the eye; its pupil.
const vec3 GILL = vec3(0.25, -0.005, 2.6);
const vec2 EYE_AT = vec2(0.118, 0.045);
const float PUPIL = 0.4;

// How long the wave along its body is, in body lengths.
uniform float wave = 1.1;

// The body: blue-green above, emerald on the flank, a paler sea green below.
uniform vec3 back : source_color = vec3(0.04, 0.42, 0.42);
uniform vec3 flank : source_color = vec3(0.12, 0.66, 0.48);
uniform vec3 belly : source_color = vec3(0.45, 0.8, 0.66);
// The edge of every scale, and the stripes of the head: rose and salmon.
uniform vec3 scale_edge : source_color = vec3(0.95, 0.46, 0.52);
uniform vec3 stripe : source_color = vec3(0.98, 0.55, 0.42);
// The yellow spot high on the gill cover and the yellow bar at the root of the tail.
uniform vec3 yellow : source_color = vec3(1.0, 0.82, 0.18);
// The beak: the fused teeth, pale and enamel-smooth.
uniform vec3 beak : source_color = vec3(0.86, 0.93, 0.84);
// The fins: rose to orange, edged with blue.
uniform vec3 fin : source_color = vec3(0.96, 0.5, 0.42);
uniform vec3 fin_edge : source_color = vec3(0.16, 0.5, 0.86);
// The eye: its iris and the ring round its pupil.
uniform vec3 iris : source_color = vec3(0.98, 0.7, 0.2);
uniform vec3 iris_ring : source_color = vec3(0.85, 0.22, 0.15);

// The gills (added 2026-11-18): four arches a side in the throat behind the mouth (part 8), seen
// only through the open mouth: pale rakers on the inner edge, a pinker bar, a fringe of blood-red
// filaments, all darker deeper in the throat. The throat runs from THROAT.x to THROAT.y (how far
// along), as the model is built (the build's THROAT line).
const vec2 THROAT = vec2(0.0965, 0.215);
uniform vec3 gill_red : source_color = vec3(0.62, 0.04, 0.06);
uniform vec3 gill_bar : source_color = vec3(0.82, 0.42, 0.42);
uniform vec3 gill_raker : source_color = vec3(0.93, 0.86, 0.78);

// ---------------------------------------------------------------------------------------------
// The cartoon eye (added 2026-11-18; the user: "the eyes for most of them should be more
// cartoony and personalized"). `cartoon_eyes` 0 is the eye as it was (the default), 1 the
// cartoon eye: grown about its own middle by `eye_grow`, a white, a coloured iris, a big dark
// pupil, a highlight that stays put (up and forward), a dark outline, and lids that give it its
// character. `eye_look` slides the iris and pupil (x towards the nose, y up; -1..1) and `blink`
// (0 open, 1 shut) closes a lid the colour of the skin about the eye over it (on either eye).
// ---------------------------------------------------------------------------------------------
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// Its character (a contented grazer: a big round golden eye, the lids relaxed top and bottom, a smile in the eye): how much bigger than life, the white, the iris, the
// lid (the skin about the eye), how wide the iris is (a share of the eye), the pupil (a share
// of the iris; its shape: 0 round, 1 an upright slit, 2 a flat bar), where the upper lid's edge
// sits (1.4 out of sight, 0 half shut), how it slants (more than 0 lower towards the nose: a
// frown), and the lower lid's edge (-1.4 out of sight).
uniform float eye_grow = 1.55;
uniform vec3 sclera : source_color = vec3(0.9700, 0.9500, 0.8600);
uniform vec3 eye_iris : source_color = vec3(1.0000, 0.7200, 0.1500);
uniform vec3 lid : source_color = vec3(0.0500, 0.4500, 0.4200);
uniform float iris_size = 0.50;
uniform float pupil_size = 0.55;
uniform int pupil_shape = 0;
uniform float lid_top = 0.50;
uniform float lid_slant = 0.00;
uniform float lid_low = -0.80;
// As the model is built (the build's EYE line), in body lengths: the eye's middle on the skin of
// its left side (x, y, how far along), the way the skin faces there, how far the skin falls away
// under its rim, its radius. The eye grows about a point just out from its middle, so that its
// rim stays on the skin.
uniform vec3 eye_mid = vec3(0.0564, 0.0450, 0.1180);
uniform vec3 eye_facing = vec3(0.9547, 0.2043, -0.2164);
uniform float eye_sink = 0.0009;
uniform float eye_radius = 0.0210;

// ---------------------------------------------------------------------------------------------
// Inside, everything is in body lengths (the fish 1 long, `s` 0 at the tip of its snout to 1 at
// the tips of its tail), as the build script has it. (From GameCommon's snapper's shader, with
// the rowing and bobbing of a labriform swimmer.)
// ---------------------------------------------------------------------------------------------

// How far before and behind the jaw's hinge the corner of the mouth runs (as the model has it).
const float CORNER_B = 0.012;
const float CORNER_C = 0.035;

// How far through a beat of its tail (0..1, it wraps). Set by the node.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left).
uniform float curl = 0.0;
// How widely its body and tail beat (1 cruising with its tail trailing, 2 hurrying, 0 still).
uniform float sway = 1.0;
// How hard its pectoral fins row (1 as it cruises, 0 folded back and still).
uniform float scull = 1.0;
// The mouth: 0 shut, 1 wide open, as when it bites. The lower jaw swings down about its hinge
// and the upper beak lifts a little.
uniform float gape = 0.0;
// How far its dorsal fin is raised (0 folded down, 1 up).
uniform float dorsal = 1.0;
// The inside of the mouth.
uniform vec3 mouth : source_color = vec3(0.2, 0.06, 0.07);

varying vec3 rest;
varying float part;
varying float inside;

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

// Scales: rounds in rows, every other row half a scale along. 1 at a scale's middle, falling
// to 0 between scales. `p` counts scales (x along the fish, y round it).
float scales(vec2 p) {
	float column = floor(p.x);
	vec2 f = vec2(fract(p.x) - 0.5, fract(p.y + 0.5 * mod(column, 2.0)) - 0.5);
	// (far off, where the scales are smaller than the picture's dots, they fade to their average)
	float far = smoothstep(0.35, 0.9, max(fwidth(p.x), fwidth(p.y)));
	return mix(1.0 - smoothstep(0.3, 0.6, length(f * vec2(1.15, 1.0))), 0.6, far);
}

// How far to one side the middle line of the body is at `s`: a wave that runs back along it,
// small at the head, growing to the tail.
float side_at(float s) {
	float k = s / JOINT;
	float reach = SWING * (0.1 - 0.5 * k + 1.4 * k * k);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / 0.7;
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

void vertex() {
	part = UV2.y;
	int p = int(part + 0.5);
	vec3 v = VERTEX / LENGTH;
	vec3 n = NORMAL;
	rest = v;
	if (p == 7 && cartoon_eyes > 0.0) {
		// The cartoon eye grows about a point just out from its middle (its rim stays on the skin).
		float g = mix(1.0, eye_grow, clamp(cartoon_eyes, 0.0, 1.0));
		float sg = sign(v.x);
		vec3 face = vec3(sg * eye_facing.x, eye_facing.y, eye_facing.z);
		vec3 mid = vec3(sg * eye_mid.x, eye_mid.y, eye_mid.z - 0.5) + face * (g * eye_sink + 0.02 * eye_radius);
		v = mid + (v - mid) * g;
	}
	inside = p <= 1 ? UV2.x : 0.0;
	float open = clamp(gape, 0.0, 1.0);
	float row = clamp(scull, 0.0, 1.5);
	if (p == 1) {
		// The lower jaw swings down about its hinge; the throat behind it stays.
		float a = open * GAPE_ANGLE * (1.0 - smoothstep(HINGE_S - CORNER_B, HINGE_S + CORNER_C, v.z + 0.5));
		vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	} else if (p == 0 && v.z + 0.5 < LIFT_TO) {
		// The upper beak lifts a little as the mouth opens.
		float a = -open * LIFT * (1.0 - smoothstep(0.0, LIFT_TO, v.z + 0.5));
		vec2 hinge = vec2(LIFT_Y, LIFT_TO - 0.5);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	} else if (p == 2) {
		// The dorsal fin folds back and down.
		float down = UV2.x * (1.0 - clamp(dorsal, 0.0, 1.0));
		v.y -= down * 0.9;
		v.z += down * 0.5;
	} else if (p == 5) {
		// A pectoral fin rows: it swings back and forth about its root like an oar, its tip
		// trailing, and flaps down on the stroke back and up on the way forward.
		float sg = sign(v.x);
		vec3 root = vec3(sg * PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z - 0.5);
		float ph = 6.2831853 * (phase + (sg > 0.0 ? 0.0 : 0.5 * PEC_ALT)) - 1.1 * UV.x;
		float a = sg * (PEC_HOLD * (1.0 - min(row, 1.0)) + row * PEC_SWING * sin(ph));
		float b = sg * row * PEC_FLAP * cos(ph);
		vec3 d = v - root;
		d = vec3(d.x * cos(a) + d.z * sin(a), d.y, -d.x * sin(a) + d.z * cos(a));
		d = vec3(d.x * cos(b) - d.y * sin(b), d.x * sin(b) + d.y * cos(b), d.z);
		n = vec3(n.x * cos(a) + n.z * sin(a), n.y, -n.x * sin(a) + n.z * cos(a));
		n = vec3(n.x * cos(b) - n.y * sin(b), n.x * sin(b) + n.y * cos(b), n.z);
		v = root + d;
	}
	if (p >= 2 && p <= 4) {
		// The soft rays of the middle fins ripple.
		float soft = p == 2 ? smoothstep(SPINE_SHARE - 0.1, SPINE_SHARE + 0.1, UV.y) : 1.0;
		v.x += FIN_WAVE * (0.3 + 0.7 * sway) * soft * UV.x * UV.x * sin(6.2831853 * phase - 5.0 * UV.y - 1.0);
	}
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float s = v.z + 0.5;
	float zc = min(s, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, s - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - 0.5 - o.x * sn + o.z * c);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(v, n);
	// Each stroke of the pectoral fins lifts the body a little and tips its nose (the bob).
	float stroke = 6.2831853 * phase;
	float pitch = row * BOB_PITCH * cos(stroke);
	v.y += row * BOB * sin(stroke) + v.z * sin(pitch);
	n.yz = vec2(n.y + n.z * sin(pitch), n.z);
	VERTEX = v * LENGTH;
	NORMAL = normalize(n);
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float s) {
	return MOUTH_Y0 + (HINGE_Y - MOUTH_Y0) * pow(max(s, 0.0) / HINGE_S, MOUTH_BOW);
}

float gill_s(float y) {
	return GILL.x - GILL.z * (y - GILL.y) * (y - GILL.y);
}

float gill_crease(float s, float y, float q) {
	float behind = s - gill_s(y);
	float span = smoothstep(-0.97, -0.75, q) * (1.0 - smoothstep(0.35, 0.6, q));
	return ((1.0 - smoothstep(0.0, 0.004, abs(behind - 0.002))) * 0.6 + (1.0 - smoothstep(0.0, 0.03, behind)) * step(0.0, behind) * 0.25) * span;
}

// 1 on a line `wide` across through (s0, y0) and (s1, y1), between those two points.
float band(float s, float y, vec2 a, vec2 b, float wide) {
	vec2 d = b - a;
	vec2 p = vec2(s, y) - a;
	float t = clamp(dot(p, d) / dot(d, d), 0.0, 1.0);
	return 1.0 - smoothstep(wide * 0.5, wide * 0.5 + 0.004, length(p - d * t));
}

// An eye: a black pupil, an iris of `tint` ringed with `ring` round the pupil, a dark rim.
vec3 eye_colour(float r, vec3 tint, vec3 ring) {
	float grain = 0.85 + 0.15 * noise2(vec2(atan(rest.y - EYE_AT.y, rest.z + 0.5 - EYE_AT.x) * 12.0, r * 3.0));
	vec3 c = mix(ring, tint, smoothstep(0.55, 0.75, r)) * grain;
	c = mix(vec3(0.004, 0.005, 0.008), c, smoothstep(PUPIL, PUPIL + 0.06, r));
	return mix(c, ring * 0.4, smoothstep(0.86, 1.0, r) * 0.85);
}

// The eye's own flat: x towards the nose, y up, `r` (0 its middle, 1 its rim) from the middle.
vec2 eye_flat(float r) {
	vec2 d = vec2(EYE_AT.x - (rest.z + 0.5), rest.y - EYE_AT.y);
	return length(d) > 1e-6 ? normalize(d) * r : vec2(0.0);
}

float pupil_dist(vec2 q) {
	if (pupil_shape == 1) {
		return length(q * vec2(3.2, 1.0));
	} else if (pupil_shape == 2) {
		return length(q * vec2(1.0, 2.8));
	}
	return length(q);
}

vec3 cartoon_eye(vec2 e, float aa) {
	vec2 o = clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.8 - iris_size);
	vec2 q = (e - o) / iris_size;
	float ir = length(q);
	float qa = aa / iris_size;
	vec3 c = sclera * (1.0 - 0.25 * smoothstep(0.2, 1.0, e.y));
	vec3 ic = mix(eye_iris * 1.3, eye_iris * 0.75, smoothstep(0.25, 0.85, ir));
	ic = mix(ic, eye_iris * 0.3, smoothstep(0.8, 1.0, ir));
	c = mix(c, ic, 1.0 - smoothstep(1.0 - qa, 1.0 + qa, ir));
	float pa = 2.0 * qa / pupil_size;
	c = mix(c, vec3(0.01, 0.01, 0.02), 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pupil_dist(q) / pupil_size));
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.15 - aa, 0.15 + aa, length(e - vec2(0.24, 0.3))));
	c = mix(c, vec3(1.0), 0.8 * (1.0 - smoothstep(0.06 - aa, 0.06 + aa, length(e - vec2(-0.12, -0.12)))));
	return c;
}

// The eye as drawn (`c`, the eye as it was), turned cartoon by `cartoon_eyes`, lidded by `blink`.
vec3 eye_finish(vec3 c, float r) {
	float k = clamp(cartoon_eyes, 0.0, 1.0);
	vec2 e = eye_flat(r);
	float aa = fwidth(r) + 0.003;
	if (k > 0.0) {
		vec3 t = cartoon_eye(e, aa);
		t = mix(t, vec3(0.03, 0.025, 0.03), smoothstep(0.86 - aa, 0.88 + aa, r));
		c = mix(c, t, k);
	}
	float b = clamp(blink, 0.0, 1.0);
	float top = mix(mix(1.4, lid_top, k) - k * (lid_slant * e.x + 0.15 * e.x * e.x), -0.1, b);
	float low = mix(mix(-1.4, lid_low, k) + k * 0.12 * e.x * e.x, -0.1, b);
	float ea = fwidth(e.y) + 0.004;
	float under = max(smoothstep(top - ea, top + ea, e.y), 1.0 - smoothstep(low - ea, low + ea, e.y));
	c = mix(c, lid * (0.8 + 0.3 * clamp(e.y * 0.5 + 0.5, 0.0, 1.0)), under);
	float line = max(1.0 - smoothstep(0.04, 0.04 + 2.0 * ea, abs(e.y - top)), 1.0 - smoothstep(0.03, 0.03 + 2.0 * ea, abs(e.y - low)));
	return mix(c, vec3(0.03, 0.02, 0.02), line * 0.85 * max(k, step(0.001, b)));
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	if (p <= 1) {
		float s = rest.z + 0.5;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		float round_it = acos(clamp(q, -1.0, 1.0)) / 3.14159265;
		c = mix(flank, back, smoothstep(0.2, 0.95, q));
		c = mix(belly, c, smoothstep(-0.95, -0.2, q));
		// Big scales, each green at its middle, edged with rose. The head and beak have none.
		float body_part = smoothstep(0.0, 0.012, s - gill_s(y)) * (1.0 - smoothstep(0.79, 0.82, s));
		float sc = scales(vec2(s * 30.0, round_it * 12.0));
		float edge = (1.0 - smoothstep(0.03, 0.22, sc)) * body_part;
		c *= mix(1.0, 0.9 + 0.16 * sc, body_part);
		c = mix(c, scale_edge, edge * 0.8);
		// The head: deeper blue-green above, two salmon stripes from the beak back past the eye.
		float head = 1.0 - smoothstep(0.2, 0.26, s);
		c = mix(c, mix(back, flank, 0.4), head * smoothstep(0.0, 0.6, q) * 0.6);
		float stripes = band(s, y, vec2(0.045, 0.004), vec2(0.105, 0.04), 0.009) + band(s, y, vec2(0.135, 0.044), vec2(0.2, 0.06), 0.009) + band(s, y, vec2(0.075, -0.042), vec2(0.19, -0.022), 0.009);
		c = mix(c, stripe, min(stripes, 1.0) * head * 0.9);
		// The yellow spot high on the gill cover, and the yellow bar at the root of the tail.
		c = mix(c, yellow, 1.0 - smoothstep(0.016, 0.022, length(vec2(s - 0.228, y - 0.072))));
		c = mix(c, yellow, smoothstep(0.765, 0.785, s) * (1.0 - smoothstep(0.81, 0.83, s)) * 0.9);
		c = mix(c, c * 0.35, gill_crease(s, y, q));
		// The beak: two pale plates of fused teeth, each side of the line of the mouth, a fine
		// seam along each plate's cutting edge.
		float ym = mouth_y(s);
		float plate = (1.0 - smoothstep(HINGE_S - 0.012, HINGE_S + 0.002, s));
		float upper = p == 0 ? (1.0 - smoothstep(0.016, 0.022, y - ym)) * step(ym - 0.003, y) : 0.0;
		float lower = p == 1 ? (1.0 - smoothstep(0.016, 0.022, ym - y)) : 0.0;
		float on_beak = max(upper, lower) * plate;
		float teeth = 0.92 + 0.08 * sin(s * 900.0) * (1.0 - smoothstep(0.003, 0.008, abs(y - ym)));
		c = mix(c, beak * teeth, on_beak);
		c = mix(c, beak * 0.55, on_beak * (1.0 - smoothstep(0.0, 0.0025, abs(y - ym))));
		c = mix(c, mouth, inside);
		rough = mix(mix(0.38, 0.22, on_beak), 0.6, inside);
		spec = mix(mix(0.5, 0.7, on_beak), 0.2, inside);
		c = mix(c, c * 1.15 + 0.03, glance * 0.25 * (1.0 - inside));
	} else if (p == 2 || p == 3) {
		// The dorsal and anal fins: rose-orange, a blue edge and a blue line along the root.
		float ray = 0.5 + 0.5 * cos(UV.y * (p == 2 ? 120.0 : 60.0));
		c = fin * (0.86 + 0.14 * ray);
		c = mix(c, fin_edge, smoothstep(0.8, 0.95, UV.x));
		c = mix(c, fin_edge * 0.8 + back * 0.2, (1.0 - smoothstep(0.08, 0.2, UV.x)) * 0.7);
		rough = 0.5;
	} else if (p == 4) {
		// The tail: green in the middle, a rose crescent, a blue edge on its corners.
		float ray = 0.5 + 0.5 * cos(UV.y * 110.0);
		float crescent = smoothstep(0.55, 0.7, UV.x) * (1.0 - smoothstep(0.86, 0.95, UV.x));
		c = mix(flank, fin, crescent) * (0.86 + 0.14 * ray);
		c = mix(c, fin_edge, smoothstep(0.92, 0.99, UV.x) * smoothstep(0.2, 0.0, min(UV.y, 1.0 - UV.y)) + smoothstep(0.93, 1.0, UV.x) * 0.4);
		c = mix(c, yellow, (1.0 - smoothstep(0.0, 0.15, UV.x)) * 0.6);
		rough = 0.5;
	} else if (p == 5) {
		// The pectoral fins: pale and see-through-looking sea green, an orange band along the
		// leading rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 80.0);
		c = mix(belly, vec3(0.85, 0.9, 0.7), 0.4) * (0.86 + 0.14 * ray);
		c = mix(c, fin, (1.0 - smoothstep(0.08, 0.2, UV.y)) * 0.85);
		c = mix(c, flank, (1.0 - smoothstep(0.0, 0.2, UV.x)) * 0.6);
		rough = 0.55;
		spec = 0.35;
	} else if (p == 6) {
		// The pelvic fins: rose, a blue leading edge.
		c = mix(fin, fin_edge, 1.0 - smoothstep(0.1, 0.25, UV.y));
		rough = 0.55;
	} else if (p == 8) {
		// The gills: rakers, the bar, then the filaments (fine rows of them), darker deeper in the
		// throat and towards the wall.
		float fil = 0.72 + 0.28 * sin(fract(UV.y) * 110.0);
		c = mix(gill_raker, gill_bar, smoothstep(0.08, 0.25, UV.x));
		c = mix(c, gill_red * fil, smoothstep(0.35, 0.5, UV.x));
		c *= mix(1.0, 0.7, smoothstep(THROAT.x, THROAT.y, rest.z + 0.5)) * (1.0 - 0.3 * UV.x);
		rough = 0.3;
		spec = 0.6;
	} else {
		c = eye_colour(UV.x, iris, iris_ring);
		c = eye_finish(c, UV.x);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
