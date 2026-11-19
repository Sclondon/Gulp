shader_type spatial;
// The wrasses (wrasse.gd): the bluestreak cleaner wrasse (`kind` 0) and the moon wrasse (`kind` 1).
// Every marking of both is drawn here (no texture files), with their rowing pectoral fins, their
// bobbing, their trailing tails and their working jaws. What each point is comes from the model
// (tools/build_wrasse.py): UV2.y the part (0 body, 1 lower jaw, 2 dorsal fin, 3 anal fin, 4 tail,
// 5 a pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body and jaw: x how far along, y how
// high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to
// edge (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1). UV2.x,
// on the body and jaw, how much the point is inside the mouth; on the dorsal fin, how far it
// stands above the fin's root.
//
// They swim as wrasses do (labriform): they row with their pectoral fins, both together, the body
// bobbing up and down with each stroke (the wrasse's gait), the tail trailing and only beating
// hard (`sway`) when they hurry. All of it is a function of `phase` alone, so a picture of it
// loops exactly. Nothing here needs more than GL Compatibility has.
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


// Kept in step with the models (tools/build_wrasse.py), in body lengths; the same for both kinds.
const float LENGTH = 0.25;
// How far the tail wrist swings to each side at `sway` 1 (a wrasse's tail mostly trails).
const float SWING = 0.05;
// The jaw's hinge, where the line of the mouth starts and how it bows; how far the jaw swings
// down at `gape` 1 (radians); how far the snout lifts, from where, about what height; how far
// the thick upper lip pushes forward as the mouth opens.
const float HINGE_S = 0.052;
const float HINGE_Y = -0.024;
const float MOUTH_Y0 = -0.013;
const float MOUTH_BOW = 1.2;
const float GAPE_ANGLE = 0.65;
const float LIFT = 0.12;
const float LIFT_TO = 0.06;
const float LIFT_Y = 0.02;
const float PROTRUDE = 0.008;
// How far its pectoral fins row back and forth and flap up and down (radians); whether the two
// row in turn (1) or together (0); how far they fold back when `scull` is 0.
const float PEC_SWING = 0.6;
const float PEC_FLAP = 0.45;
const float PEC_ALT = 0.0;
const float PEC_HOLD = -0.3;
// How far the body rises and falls, and pitches, with each stroke at `scull` 1: the bob.
const float BOB = 0.012;
const float BOB_PITCH = 0.04;
const float FIN_WAVE = 0.005;
// How much of the dorsal fin is spines.
const float SPINE_SHARE = 0.44;
// The gill cover's edge (its rearmost reach, at what height, how it curves); the eye; its pupil.
const vec3 GILL = vec3(0.2, -0.004, 2.6);
const vec2 EYE_AT = vec2(0.092, 0.022);
const float PUPIL = 0.42;

// Which wrasse: 0 the bluestreak cleaner wrasse, 1 the moon wrasse. Set by the node, with the
// two below and the colours (wrasse.gd's KINDS).
uniform float kind = 0.0;
// A pectoral fin's root (to the side, up, along) and the tail fin's hinge (behind it the tail is
// one plate), as each kind's model is built.
uniform vec3 pec_root = vec3(0.041, -0.006, 0.215);
uniform float joint = 0.835;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.0;

// The colours (each kind's own are set by the node). The cleaner: `back` the blue of its back,
// `flank` the pale yellow-white of its front, `belly` its white belly, `mark` its black stripe,
// `head` the top of its head. The moon: `back` and `flank` its greens, `belly` its pale throat,
// `mark` the magenta bar on every scale and the bands on its head, `head` the blue of its head.
uniform vec3 back : source_color = vec3(0.2, 0.45, 0.95);
uniform vec3 flank : source_color = vec3(0.93, 0.9, 0.66);
uniform vec3 belly : source_color = vec3(0.95, 0.96, 0.98);
uniform vec3 mark : source_color = vec3(0.02, 0.02, 0.05);
uniform vec3 head : source_color = vec3(0.85, 0.85, 0.7);
uniform vec3 lips : source_color = vec3(0.1, 0.1, 0.16);
// The fins, their edges, and the tail's own colour (the cleaner's black wedge, the moon's yellow
// crescent).
uniform vec3 fin : source_color = vec3(0.12, 0.25, 0.7);
uniform vec3 fin_edge : source_color = vec3(0.5, 0.8, 1.0);
uniform vec3 tail_main : source_color = vec3(0.02, 0.02, 0.05);
// The eye: its iris and the ring round its pupil.
uniform vec3 iris : source_color = vec3(0.12, 0.16, 0.35);
uniform vec3 iris_ring : source_color = vec3(0.5, 0.7, 1.0);

// The gills (added 2026-11-18): four arches a side in the throat behind the mouth (part 8), seen
// only through the open mouth: pale rakers on the inner edge, a pinker bar, a fringe of blood-red
// filaments, all darker deeper in the throat. The throat runs from THROAT.x to THROAT.y (how far
// along), as the model is built (the build's THROAT line).
const vec2 THROAT = vec2(0.0735, 0.165);
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
// Its character (set by the kind in wrasse.gd; these defaults are the cleaner wrasse: an eager little helper, wide open, all white round a bright blue iris): how much bigger than life, the white, the iris, the
// lid (the skin about the eye), how wide the iris is (a share of the eye), the pupil (a share
// of the iris; its shape: 0 round, 1 an upright slit, 2 a flat bar), where the upper lid's edge
// sits (1.4 out of sight, 0 half shut), how it slants (more than 0 lower towards the nose: a
// frown), and the lower lid's edge (-1.4 out of sight).
uniform float eye_grow = 1.75;
uniform vec3 sclera : source_color = vec3(1.0000, 1.0000, 1.0000);
uniform vec3 eye_iris : source_color = vec3(0.1500, 0.4500, 1.0000);
uniform vec3 lid : source_color = vec3(0.0300, 0.0300, 0.0600);
uniform float iris_size = 0.42;
uniform float pupil_size = 0.60;
uniform int pupil_shape = 0;
uniform float lid_top = 1.40;
uniform float lid_slant = 0.00;
uniform float lid_low = -1.40;
// As the model is built (the build's EYE line), in body lengths: the eye's middle on the skin of
// its left side (x, y, how far along), the way the skin faces there, how far the skin falls away
// under its rim, its radius. The eye grows about a point just out from its middle, so that its
// rim stays on the skin.
uniform vec3 eye_mid = vec3(0.0328, 0.0220, 0.0920);
uniform vec3 eye_facing = vec3(0.9317, 0.2994, -0.2059);
uniform float eye_sink = 0.0012;
uniform float eye_radius = 0.0170;

// ---------------------------------------------------------------------------------------------
// Inside, everything is in body lengths (the fish 1 long, `s` 0 at the tip of its snout to 1 at
// the tips of its tail), as the build script has it. (From GameCommon's parrotfish's shader.)
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
// How hard its pectoral fins row (1 as it cruises, 0 folded back and still: no bob).
uniform float scull = 1.0;
// The mouth: 0 shut, 1 wide open, as when it bites. The lower jaw swings down about its hinge,
// the snout lifts a little and the upper lip pushes forward.
uniform float gape = 0.0;
// How far its dorsal fin is raised (0 folded down, 1 up).
uniform float dorsal = 1.0;
// The inside of the mouth.
uniform vec3 mouth : source_color = vec3(0.2, 0.06, 0.08);

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

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float s) {
	return MOUTH_Y0 + (HINGE_Y - MOUTH_Y0) * pow(max(s, 0.0) / HINGE_S, MOUTH_BOW);
}

float gill_s(float y) {
	return GILL.x - GILL.z * (y - GILL.y) * (y - GILL.y);
}

// How far to one side the middle line of the body is at `s`: a wave that runs back along it,
// small at the head, growing to the tail.
float side_at(float s) {
	float k = s / joint;
	float reach = SWING * (0.1 - 0.5 * k + 1.4 * k * k);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.25;
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
	bake_uv = CUSTOM0.xy;

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
		// The snout lifts a little as the mouth opens, and the thick upper lip pushes forward.
		float s0 = v.z + 0.5;
		float lip = (1.0 - smoothstep(0.0, 0.012, abs(v.y - mouth_y(s0)) - 0.004)) * (1.0 - smoothstep(0.02, HINGE_S, s0));
		v.z -= open * PROTRUDE * lip;
		float a = -open * LIFT * (1.0 - smoothstep(0.0, LIFT_TO, s0));
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
		vec3 root = vec3(sg * pec_root.x, pec_root.y, pec_root.z - 0.5);
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
	float zc = min(s, joint);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.86 * joint, joint, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, s - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - 0.5 - o.x * sn + o.z * c);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(v, n);
	// Each stroke of the pectoral fins lifts the body and tips its nose (the wrasse's bob).
	float stroke = 6.2831853 * phase;
	float pitch = row * BOB_PITCH * cos(stroke);
	v.y += row * BOB * sin(stroke) + v.z * sin(pitch);
	n.yz = vec2(n.y + n.z * sin(pitch), n.z);
	VERTEX = v * LENGTH;
	NORMAL = normalize(n);
}

// Scales: rounds in rows, every other row half a scale along. Gives (how near a scale's middle,
// 1 there to 0 between scales; the place within the scale, -0.5..0.5 each way). `p` counts
// scales (x along the fish, y round it).
vec3 scales(vec2 p) {
	float column = floor(p.x);
	vec2 f = vec2(fract(p.x) - 0.5, fract(p.y + 0.5 * mod(column, 2.0)) - 0.5);
	// (far off, where the scales are smaller than the picture's dots, they fade to their average)
	float far = smoothstep(0.35, 0.9, max(fwidth(p.x), fwidth(p.y)));
	return vec3(mix(1.0 - smoothstep(0.3, 0.6, length(f)), 0.6, far), f * (1.0 - far));
}

float gill_crease(float s, float y, float q) {
	float behind = s - gill_s(y);
	float span = smoothstep(-0.97, -0.75, q) * (1.0 - smoothstep(0.35, 0.6, q));
	return ((1.0 - smoothstep(0.0, 0.003, abs(behind - 0.002))) * 0.6 + (1.0 - smoothstep(0.0, 0.025, behind)) * step(0.0, behind) * 0.25) * span;
}

// 1 on a line `wide` across from `a` to `b` (in (s, y)), round-ended.
float band(float s, float y, vec2 a, vec2 b, float wide) {
	vec2 d = b - a;
	vec2 p = vec2(s, y) - a;
	float t = clamp(dot(p, d) / dot(d, d), 0.0, 1.0);
	return 1.0 - smoothstep(wide * 0.5, wide * 0.5 + 0.003, length(p - d * t));
}

// An eye: a black pupil, an iris of `tint` ringed with `ring` round the pupil, a dark rim.
vec3 eye_colour(float r, vec3 tint, vec3 ring) {
	float grain = 0.85 + 0.15 * noise2(vec2(atan(rest.y - EYE_AT.y, rest.z + 0.5 - EYE_AT.x) * 12.0, r * 3.0));
	vec3 c = mix(ring, tint, smoothstep(0.55, 0.75, r)) * grain;
	c = mix(vec3(0.004, 0.005, 0.008), c, smoothstep(PUPIL, PUPIL + 0.06, r));
	return mix(c, tint * 0.3, smoothstep(0.86, 1.0, r) * 0.85);
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

// The cleaner's black stripe: 1 inside it. From the tip of the snout through the eye, along the
// middle of the flank, widening all the way to the tail.
float stripe_centre(float s) {
	return mix(mix(-0.008, 0.021, smoothstep(0.0, 0.092, s)), -0.004, smoothstep(0.092, 0.6, s));
}

float stripe_half(float s) {
	return mix(0.007, 0.016, smoothstep(0.0, 0.09, s)) + 0.028 * smoothstep(0.12, 0.84, s);
}

float cleaner_stripe(float s, float y) {
	float centre = stripe_centre(s);
	float half_wide = stripe_half(s);
	return 1.0 - smoothstep(half_wide - 0.003, half_wide + 0.003, abs(y - centre));
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

