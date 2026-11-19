shader_type spatial;
// The red lionfish (lionfish.gd): every marking drawn here (no texture files), the fanning and
// folding of its fins and spines (`spread`), the slow waving of its fins, its gentle swimming and
// its working jaw. What each point is comes from the model (tools/build_lionfish.py): UV2.y the
// part (0 body, 1 lower jaw, 2 a dorsal spine with its flag, 3 the soft dorsal and anal fins,
// 4 tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 a tab over an eye, 9 a tab on the lower
// jaw). UV, on the body and jaw: x how far along, y how high on its side (1 the ridge of the
// back, 0 the keel of the belly); on a fin or tab: x root (0) to edge or tip (1), y leading edge
// (0) to trailing edge (1); on a dorsal spine: x root (0) to tip (1), y its number plus 0.9 times
// how far across its flag; on an eye: x middle (0) to rim (1). UV2.x, on the body and jaw, how
// much the point is inside the mouth.
//
// A lionfish mostly hovers, fins spread: its pectoral fins and its soft fins wave slowly, its
// tail beats gently (`sway`). All of it is a function of `phase` alone, so a picture of it loops
// exactly. Nothing here needs more than GL Compatibility has.
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


// Kept in step with the model (tools/build_lionfish.py prints them), in body lengths.
const float LENGTH = 0.35;
// Where the tail fin is hinged: behind it the tail is one plate.
const float JOINT = 0.78;
// How far the tail wrist swings to each side at `sway` 1.
const float SWING = 0.05;
// The jaw's hinge, where the line of the mouth starts and how it bows; how far the jaw swings
// down at `gape` 1 (radians); how far the snout lifts, from where, about what height.
const float HINGE_S = 0.1;
const float HINGE_Y = -0.062;
const float MOUTH_Y0 = -0.02;
const float MOUTH_BOW = 1.0;
const float GAPE_ANGLE = 0.7;
const float LIFT = 0.08;
const float LIFT_TO = 0.11;
const float LIFT_Y = 0.06;
// A pectoral fin's root (to the side, up, along); the way its flat faces and its middle ray
// points (the fish's left fin; the right is its mirror); how wide its fan is (radians).
const vec3 PEC_ROOT = vec3(0.0619, -0.035, 0.285);
const vec3 PEC_FACING = vec3(0.7912, -0.0907, -0.6048);
const float PEC_FAN = 1.9199;
const float PEC_RAYS = 15.0;
// With `spread` 0: how much of its fan a pectoral fin closes, how far it folds back along the
// body, how far the dorsal spines lie back (radians).
const float PEC_CLOSE = 0.8;
const float PEC_FOLD = 0.55;
const float SPINE_FOLD = 1.05;
// How far a pectoral fin waves (body lengths at its edge) at `scull` 1, and the soft fins.
const float PEC_WAVE = 0.03;
const float FIN_WAVE = 0.012;
// The roots of the thirteen dorsal spines (how far along, how high).
const vec2 SPINE_ROOT[13] = {
	vec2(0.2000, 0.1130), vec2(0.2296, 0.1203), vec2(0.2592, 0.1260), vec2(0.2887, 0.1283),
	vec2(0.3183, 0.1293), vec2(0.3479, 0.1299), vec2(0.3775, 0.1299), vec2(0.4071, 0.1272),
	vec2(0.4367, 0.1222), vec2(0.4662, 0.1167), vec2(0.4958, 0.1109), vec2(0.5254, 0.1039),
	vec2(0.5550, 0.0961)
};
// The gill cover's edge (its rearmost reach, at what height, how it curves); the eye; its pupil.
const vec3 GILL = vec3(0.29, 0.0, 2.2);
const vec2 EYE_AT = vec2(0.122, 0.05);
const float PUPIL = 0.36;
// How far apart its body's bars are, and its head's (body lengths).
const float BARS = 0.072;
const float RINGS = 0.05;

// How long the wave along its body is, in body lengths.
uniform float wave = 1.1;

// The dark of its bars (red-brown) and the pale between them (cream-white); its belly.
uniform vec3 bar : source_color = vec3(0.5, 0.1, 0.07);
uniform vec3 pale : source_color = vec3(0.97, 0.9, 0.82);
uniform vec3 belly : source_color = vec3(0.98, 0.86, 0.8);
// Its fins: the pale of the membranes and the dark of their spots and bands.
uniform vec3 fin_clear : source_color = vec3(0.93, 0.86, 0.82);
uniform vec3 fin_spot : source_color = vec3(0.38, 0.08, 0.06);
// The eye: its iris and the ring round its pupil.
uniform vec3 iris : source_color = vec3(0.62, 0.22, 0.12);
uniform vec3 iris_ring : source_color = vec3(0.95, 0.7, 0.35);

// The gills (added 2026-11-18): four arches a side in the throat behind the mouth (part 10), seen
// only through the open mouth: pale rakers on the inner edge, a pinker bar, a fringe of blood-red
// filaments, all darker deeper in the throat. The throat runs from THROAT.x to THROAT.y (how far
// along), as the model is built (the build's THROAT line).
const vec2 THROAT = vec2(0.1215, 0.255);
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
// Its character (a haughty, scheming hunter: a heavy red-brown lid slanting down to the front in a scowl over a red iris with a cat slit): how much bigger than life, the white, the iris, the
// lid (the skin about the eye), how wide the iris is (a share of the eye), the pupil (a share
// of the iris; its shape: 0 round, 1 an upright slit, 2 a flat bar), where the upper lid's edge
// sits (1.4 out of sight, 0 half shut), how it slants (more than 0 lower towards the nose: a
// frown), and the lower lid's edge (-1.4 out of sight).
uniform float eye_grow = 1.35;
uniform vec3 sclera : source_color = vec3(0.9600, 0.9000, 0.7800);
uniform vec3 eye_iris : source_color = vec3(0.9000, 0.2800, 0.1200);
uniform vec3 lid : source_color = vec3(0.5000, 0.1000, 0.0700);
uniform float iris_size = 0.58;
uniform float pupil_size = 0.80;
uniform int pupil_shape = 1;
uniform float lid_top = 0.30;
uniform float lid_slant = 0.45;
uniform float lid_low = -1.40;
// As the model is built (the build's EYE line), in body lengths: the eye's middle on the skin of
// its left side (x, y, how far along), the way the skin faces there, how far the skin falls away
// under its rim, its radius. The eye grows about a point just out from its middle, so that its
// rim stays on the skin.
uniform vec3 eye_mid = vec3(0.0505, 0.0500, 0.1220);
uniform vec3 eye_facing = vec3(0.9056, 0.3560, -0.2304);
uniform float eye_sink = 0.0027;
uniform float eye_radius = 0.0270;

// ---------------------------------------------------------------------------------------------
// Inside, everything is in body lengths (the fish 1 long, `s` 0 at the tip of its snout to 1 at
// the edge of its tail), as the build script has it.
// ---------------------------------------------------------------------------------------------

// How far before and behind the jaw's hinge the corner of the mouth runs (as the model has it).
const float CORNER_B = 0.012;
const float CORNER_C = 0.035;

// How far through a beat of its tail (0..1, it wraps). Set by the node.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left).
uniform float curl = 0.0;
// How widely its body and tail beat (a lionfish hovering: a little; 1 swimming; 0 still).
uniform float sway = 0.3;
// How much its pectoral fins and soft fins wave (1 as it hovers, 0 held still).
uniform float scull = 1.0;
// Its fins and spines: 1 fanned out and raised (as it hovers, or threatens), 0 folded: the
// pectoral fans closed and laid back along the body, the spines laid back.
uniform float spread = 1.0;
// The mouth: 0 shut, 1 wide open, as when it gulps its prey. The lower jaw (with its tabs)
// swings down about its hinge and the snout lifts a little.
uniform float gape = 0.0;
// The inside of the mouth.
uniform vec3 mouth : source_color = vec3(0.2, 0.05, 0.05);

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

// `v` turned about the unit axis `k` by `a` radians.
vec3 turned(vec3 v, vec3 k, float a) {
	return v * cos(a) + cross(k, v) * sin(a) + k * dot(k, v) * (1.0 - cos(a));
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
	float from = -0.15;
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
	float fold = 1.0 - clamp(spread, 0.0, 1.0);
	float wave_by = clamp(scull, 0.0, 2.0);
	if (p == 1 || p == 9) {
		// The lower jaw (and the tabs on it) swings down about its hinge; the throat stays.
		float a = open * GAPE_ANGLE * (1.0 - smoothstep(HINGE_S - CORNER_B, HINGE_S + CORNER_C, v.z + 0.5));
		vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	} else if (p == 0 && v.z + 0.5 < LIFT_TO) {
		// The snout lifts a little as the mouth opens.
		float a = -open * LIFT * (1.0 - smoothstep(0.0, LIFT_TO, v.z + 0.5));
		vec2 hinge = vec2(LIFT_Y, LIFT_TO - 0.5);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	} else if (p == 2) {
		// A dorsal spine and its flag lie back about the spine's root.
		int i = clamp(int(floor(UV.y + 0.04)), 0, 12);
		vec2 root = SPINE_ROOT[i];
		float a = fold * SPINE_FOLD * (0.75 + 0.25 * float(i) / 12.0);
		vec2 d = vec2(v.y - root.y, v.z - (root.x - 0.5));
		float c = cos(a);
		float sn = sin(a);
		v.yz = vec2(root.y, root.x - 0.5) + vec2(d.x * c - d.y * sn, d.x * sn + d.y * c);
		n.yz = vec2(n.y * c - n.z * sn, n.y * sn + n.z * c);
	} else if (p == 5) {
		// A pectoral fin: its fan closes and it folds back along the body as `spread` falls;
		// spread, it waves slowly, a ripple running out along its rays.
		float sg = sign(v.x);
		vec3 root = vec3(sg * PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z - 0.5);
		vec3 axis = vec3(PEC_FACING.x, sg * PEC_FACING.y, sg * PEC_FACING.z);
		vec3 out_way = vec3(sg * PEC_FACING.x, PEC_FACING.y, PEC_FACING.z);
		vec3 d = v - root;
		d += out_way * wave_by * PEC_WAVE * UV.x * UV.x * sin(6.2831853 * phase - 3.0 * UV.y - 2.5 * UV.x) * (1.0 - 0.6 * fold);
		float close = -(UV.y - 0.5) * PEC_FAN * PEC_CLOSE * fold;
		d = turned(d, axis, close);
		n = turned(n, axis, close);
		float a = -sg * fold * PEC_FOLD;
		d = vec3(d.x * cos(a) + d.z * sin(a), d.y, -d.x * sin(a) + d.z * cos(a));
		n = vec3(n.x * cos(a) + n.z * sin(a), n.y, -n.x * sin(a) + n.z * cos(a));
		v = root + d;
	} else if (p == 6) {
		// The pelvic fins lie back a little as `spread` falls, and sway.
		v.z += fold * 0.06 * UV.x;
		v.y += fold * 0.04 * UV.x;
		v.x += sign(v.x) * wave_by * 0.008 * UV.x * sin(6.2831853 * phase - 1.0);
	}
	if (p == 3 || p == 4) {
		// The soft fins and the tail ripple, a wave running back along them.
		v.x += FIN_WAVE * (0.4 * wave_by + 0.6 * sway) * UV.x * UV.x * sin(6.2831853 * phase - 6.0 * UV.y - 1.5);
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

// The lionfish's banding along a line `x` counted in bands: a broad dark bar, a pale gap with a
// thin dark line in it. 1 dark, 0 pale.
float banding(float x) {
	float f = fract(x);
	float w = max(fwidth(x), 0.001) * 1.2;
	float broad = smoothstep(0.0, w, f) * (1.0 - smoothstep(0.48 - w, 0.48 + w, f));
	float thin = smoothstep(0.66 - w, 0.66 + w, f) * (1.0 - smoothstep(0.73 - w, 0.73 + w, f));
	return max(broad, thin * 0.85);
}

// An eye: a black pupil, an iris of `tint` ringed with `ring` round the pupil, a dark rim.
vec3 eye_colour(float r, vec3 tint, vec3 ring) {
	float grain = 0.85 + 0.15 * noise2(vec2(atan(rest.y - EYE_AT.y, rest.z + 0.5 - EYE_AT.x) * 12.0, r * 3.0));
	vec3 c = mix(ring, tint, smoothstep(0.5, 0.72, r)) * grain;
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

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

