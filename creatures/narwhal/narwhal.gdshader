shader_type spatial;
// The narwhal (narwhal.gd): every marking drawn here (no texture files), its swimming, its tusk's
// length and its mouth. What each point is comes from the model (tools/build_narwhal.py): UV2.y
// the part (0 body, 1 lower jaw, 4 the flukes, 6 a flipper, 7 an eye, 8 the tusk); UV2.x, on the
// body and the jaw, how much it is inside the mouth. UV, on the body and jaw: x how far along, y
// how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to
// tip (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1); on the
// tusk: x root (0) to tip (1).
//
// It swims as whales do: its flukes beat UP AND DOWN. A wave runs back along the body, all but
// nothing at the flippers and growing down the tail stock, and the flukes pitch about their root
// as one stiff plate. All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has. The code is GameCommon's dolphin's, changed
// for this animal.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 4.5;
const float HALF = 2.25;
// Where the flukes are hinged (metres behind the front of the head): behind it they are one plate.
const float JOINT = 3.95;
// The corner of the mouth, where the lower jaw hinges (metres behind the front, metres up), and
// how far behind it the jaw runs on inside the body.
const float CORNER = 0.23;
const float HINGE_Y = -0.1148;
const float JAW_TAIL = 0.11;
const float BLOWHOLE = 0.5;
const vec2 EYE_AT = vec2(0.345, -0.085);
// The tusk: where its root is (in the head, left of the middle line), how far it reaches ahead
// of the front of the head at `tusk` 1, how many grooves wind round it and how far along it one
// goes in a whole turn (left-handed).
const vec3 TUSK_ROOT = vec3(-0.062, -0.045, -2.16);
const float TUSK_REACH = 2.5;
const float TUSK_STARTS = 4.0;
const float TUSK_PITCH = 0.3;
// How far the lower jaw swings down for `gape` 1 (radians), and how far the flukes' root rises and
// falls for `sway` 1 (of its length).
const float GAPE_MAX = 0.5;
const float REACH = 0.055;

// How far through a beat of its flukes (0..1, it wraps). Set by Narwhal.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// flippers to the flukes (0 straight; more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// The same up and down, about its middle, in radians from its head to its flukes (more than 0 its
// head and its flukes both come up; less than 0 both go down, its back arched).
uniform float arch = 0.0;
// How widely it beats, for 1 as a narwhal cruising (its fluke tips rise and fall about 0.3 m).
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape = 0.0;
// The tusk's length: 1 a grown male's (2.5 m ahead of its head), less a young one's, 0 none (a
// female or a calf).
uniform float tusk = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.05;

// The pale ground, the dark spots on it, the near-black of the back and the head; how thickly
// spotted it is (0 an old, nearly white one, 1 the usual, more a young dark one); the fins' dark;
// the inside of the mouth; the tusk's ivory.
uniform vec3 pale : source_color = vec3(0.68, 0.7, 0.69);
uniform vec3 spot : source_color = vec3(0.16, 0.17, 0.18);
uniform vec3 back : source_color = vec3(0.1, 0.11, 0.12);
uniform float spots = 1.0;
uniform vec3 fin : source_color = vec3(0.13, 0.14, 0.15);
uniform vec3 mouth : source_color = vec3(0.6, 0.32, 0.32);
uniform vec3 ivory : source_color = vec3(0.92, 0.9, 0.82);

// The cartoon eye (0 the eye as in life, 1 the cartoon eye), where its eyes look (x +1 towards the
// nose, y +1 up, each in its own plane) and its lids (0 open, 1 shut). Set by the node.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// Where the right eye sits, as the model has it (the build script prints it: EYE_FRAME; the left
// eye is its mirror): its middle on the skin, the way out of the head, the way to the nose and the
// way up in the eye's own plane, how fast the skin falls away from that plane round it (metres per
// square metre), and the eye's radius.
const vec3 EYE_CENTRE = vec3(0.28382, -0.08500, -1.90500);
const vec3 EYE_OUT = vec3(0.9275, -0.2772, -0.2507);
const vec3 EYE_FWD = vec3(-0.2402, 0.0718, -0.9681);
const vec3 EYE_UP = vec3(0.2863, 0.9581, 0.0000);
const float EYE_SAG = 0.8866;
const float EYE_RADIUS = 0.019;
// The narwhal's: small, mild and curious. Bigger than life by 1.7 (still small on so big a head);
// a soft white, a gentle dark slate-brown iris looking a little up and ahead, a round pupil, two
// highlights; the upper lid high and lifted in the middle (raised brows: curious), the lower lid
// soft and low (mild), thin lines.
const float EYE_GROW = 1.7;
const vec3 SCLERA = vec3(0.95, 0.95, 0.93);
const vec3 IRIS_LIGHT = vec3(0.42, 0.36, 0.3);
const vec3 IRIS_DARK = vec3(0.14, 0.12, 0.11);
const float IRIS = 0.5;
const vec2 IRIS_AT = vec2(0.08, 0.07);
const vec2 LOOK_REACH = vec2(0.26, 0.2);
const vec2 GLINT_AT = vec2(0.24, 0.3);
const float GLINT = 0.15;
const vec2 GLINT2_AT = vec2(-0.16, -0.12);
const vec3 OUTLINE = vec3(0.04, 0.045, 0.05);
const float LINE_UP = 0.07;
const float LINE_DOWN = 0.05;

// (inside the pupil where this is under 0; `q` from the iris's middle, in eye radii)
float pupil(vec2 q) {
	return length(q) - 0.26;
}

float lid_up(float x) {
	// (lifted in the middle: an open, wondering brow)
	return 0.92 - 0.3 * x * x;
}

float lid_down(float x) {
	return -0.72 - 0.15 * x * x;
}

vec3 lid_colour() {
	return mix(back, pale, 0.72);
}

// (where an eye's point lies in the eye's own plane, in eye radii: x towards the nose, y up)
varying vec2 eye_at;

// The eye's dome grown about its own middle for the cartoon eye, its rim laid back on the skin.
void eye_grow(inout vec3 v, out vec2 at) {
	vec3 m = vec3(v.x >= 0.0 ? 1.0 : -1.0, 1.0, 1.0);
	vec3 d = v - EYE_CENTRE * m;
	vec2 pl = vec2(dot(d, EYE_FWD * m), dot(d, EYE_UP * m));
	at = pl / EYE_RADIUS;
	if (cartoon_eyes <= 0.0) {
		return;
	}
	float g = mix(1.0, EYE_GROW, cartoon_eyes);
	float r2 = dot(pl, pl);
	float over = dot(d, EYE_OUT * m) + EYE_SAG * r2;
	float h = over * g - EYE_SAG * r2 * g * g;
	v = EYE_CENTRE * m + (EYE_FWD * m * pl.x + EYE_UP * m * pl.y) * g + EYE_OUT * m * h;
}

// The cartoon eye's colour at `e` (eye_at); `lit` how much of it glows a little (its white,
// iris and highlight read in dark water; the lids do not).
vec3 cartoon_eye(vec2 e, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 q = e - IRIS_AT - clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK_REACH;
	float qi = length(q);
	vec3 c = SCLERA * (1.0 - 0.15 * smoothstep(0.5, 0.86, r));
	vec3 iris = mix(IRIS_LIGHT, IRIS_DARK, smoothstep(IRIS * 0.5, IRIS, qi));
	c = mix(c, iris, 1.0 - smoothstep(IRIS - aa, IRIS + aa, qi));
	c = mix(c, vec3(0.01), 1.0 - smoothstep(-aa, aa, pupil(q)));
	// the highlights stay put, towards the light, wherever it looks
	float glint = max(1.0 - smoothstep(GLINT - aa, GLINT + aa, length(e - GLINT_AT)),
		1.0 - smoothstep(GLINT * 0.45 - aa, GLINT * 0.45 + aa, length(e - GLINT2_AT)));
	c = mix(c, vec3(1.0), glint);
	lit = mix(0.5, 1.0, glint);
	// a dark ring round it
	c = mix(c, OUTLINE, smoothstep(0.84 - aa, 0.86 + aa, r));
	// the lids, meeting a little below the middle as it blinks
	float b = clamp(blink, 0.0, 1.0);
	float meet = mix(lid_down(e.x), lid_up(e.x), 0.35);
	float up = mix(lid_up(e.x), meet, b);
	float down = mix(lid_down(e.x), meet, b);
	float over_up = e.y - up;
	float over_down = down - e.y;
	float lid = max(smoothstep(-aa, aa, over_up), smoothstep(-aa, aa, over_down));
	c = mix(c, lid_colour(), lid);
	lit *= 1.0 - lid;
	float line = max(smoothstep(-aa, aa, over_up) * (1.0 - smoothstep(LINE_UP - aa, LINE_UP + aa, over_up)),
		smoothstep(-aa, aa, over_down) * (1.0 - smoothstep(LINE_DOWN - aa, LINE_DOWN + aa, over_down)));
	c = mix(c, OUTLINE, line * (1.0 - smoothstep(0.92, 1.0, r)));
	return c;
}

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float inside;

vec3 hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.xxy + p.yxx) * p.zyx);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(hash3(i).x, hash3(i + vec3(1.0, 0.0, 0.0)).x, f.x);
	float b = mix(hash3(i + vec3(0.0, 1.0, 0.0)).x, hash3(i + vec3(1.0, 1.0, 0.0)).x, f.x);
	float c = mix(hash3(i + vec3(0.0, 0.0, 1.0)).x, hash3(i + vec3(1.0, 0.0, 1.0)).x, f.x);
	float d = mix(hash3(i + vec3(0.0, 1.0, 1.0)).x, hash3(i + vec3(1.0, 1.0, 1.0)).x, f.x);
	return mix(mix(a, b, f.y), mix(c, d, f.y), f.z);
}

// The nearest of a scatter of points, one to a cell: (how far, in cells; a number of its own).
vec2 scatter(vec3 p) {
	vec3 b = floor(p - 0.5);
	float best = 9.0;
	float id = 0.0;
	for (int k = 0; k < 8; k++) {
		vec3 cell = b + vec3(float(k & 1), float((k >> 1) & 1), float((k >> 2) & 1));
		vec3 h = hash3(cell);
		float d = length(p - (cell + 0.5 + (h - 0.5) * 0.7));
		if (d < best) {
			best = d;
			id = fract(h.x * 7.3 + h.y * 3.1);
		}
	}
	return vec2(best, id);
}

// How far up the middle line of the body is, `xm` metres behind the front: a wave that runs back
// along it, least at the flippers, large only down the tail stock.
float lift_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * REACH * (0.07 - 0.3 * s + 0.33 * s * s + 0.9 * s * s * s * s);
	return sway * reach * sin(TAU * (phase - s / wave));
}

// The body behind the head laid round an arc to one side (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2 * LENGTH;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.7 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// The whole body laid round an arc that goes up and down, about its middle (see `arch`).
void arch_bend(inout vec3 v, inout vec3 n) {
	if (abs(arch) < 0.001) {
		return;
	}
	float k = arch / LENGTH;
	// (ahead of the head, the tusk goes on straight from it: it does not bend)
	float z = max(v.z, -HALF);
	float ahead = v.z - z;
	float a = z * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x, n.y * c + n.z * sn, n.z * c - n.y * sn);
	v = vec3(v.x, r - (r - v.y) * c, (r - v.y) * sn) + vec3(0.0, sn, c) * ahead;
}

void vertex() {
	part = UV2.y;
	inside = UV2.x;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	eye_at = vec2(0.0);
	if (p == 7) {
		vec2 at;
		eye_grow(v, at);
		eye_at = at;
	}
	if (p == 8) {
		// The tusk: drawn out from its root to its length, and a little thinner when short; at 0
		// it is gone into the head.
		float k = clamp(tusk, 0.0, 1.5);
		float thick = k > 0.0 ? mix(0.55, 1.0, min(k, 1.0)) : 0.0;
		vec3 d = v - TUSK_ROOT;
		v = TUSK_ROOT + vec3(d.xy * thick, d.z * k);
	}
	if (p == 1) {
		// The lower jaw swings down about the corner of the mouth; behind the corner, inside the
		// body, it stays.
		float a = GAPE_MAX * clamp(gape, 0.0, 1.0) * smoothstep(CORNER + 0.01, CORNER - 0.04, v.z + HALF);
		vec2 hinge = vec2(HINGE_Y, CORNER - HALF);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	float xm = v.z + HALF;
	// (the flukes, behind their hinge, are one stiff plate: they turn about the hinge; the tusk,
	// ahead of the head, goes with the head)
	float zc = clamp(xm, 0.0, JOINT);
	float h = lift_at(zc);
	float slope = (lift_at(zc + 0.015) - lift_at(zc - 0.015)) / 0.03;
	// (the flukes pitch a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.35 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec2 o = vec2(v.y, xm - zc);
	v = vec3(v.x, h + o.x * c + o.y * sn, zc - HALF - o.x * sn + o.y * c);
	n = vec3(n.x, n.y * c + n.z * sn, -n.y * sn + n.z * c);
	arch_bend(v, n);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The line of the mouth, as the model has it.
float mouth_y(float xm) {
	return -0.152 + 0.04 * xm + 0.028 * smoothstep(0.12, 0.235, xm);
}

// The skin at a place: `p` where (at rest), `xm` behind the front, `h` how high on its side (0..1).
vec3 skin(vec3 p, float xm, float h) {
	float cloud = noise3(p * 2.2);
	float grain = noise3(p * 60.0);
	// The ground: pale on the belly, greyer up the sides.
	vec3 c = mix(pale, mix(pale, back, 0.25), smoothstep(0.25, 0.6, h + (cloud - 0.5) * 0.2));
	// The spots: dark blotches of every size, few on the belly, crowding up the sides until on the
	// back they run together into near-black; the head mottled dark all over.
	float crowd = clamp(spots, 0.0, 1.5) * (smoothstep(0.1, 0.75, h + (cloud - 0.5) * 0.25) + 0.6 * (1.0 - smoothstep(0.3, 0.8, xm)));
	float wobble = (noise3(p * 22.0) - 0.5) * 0.45 + (noise3(p * 70.0) - 0.5) * 0.2;
	vec2 big = scatter(p / 0.065 + 3.0);
	float rb = mix(0.1, 0.4, big.y) * crowd;
	float dark = 1.0 - smoothstep(rb * 0.75, rb, big.x + wobble);
	vec2 small = scatter(p / 0.026 + 11.0);
	float rs = mix(0.1, 0.38, small.y) * crowd;
	dark = max(dark, (1.0 - smoothstep(rs * 0.7, rs, small.x + wobble)) * step(0.25, small.y));
	c = mix(c, spot * (0.85 + 0.3 * cloud), clamp(dark, 0.0, 1.0) * 0.95);
	float solid = smoothstep(0.78, 0.95, h + (cloud - 0.5) * 0.15) * clamp(spots, 0.0, 1.5);
	c = mix(c, back, clamp(solid, 0.0, 1.0) * 0.9);
	c *= 0.95 + 0.1 * grain;
	return c;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.32;
	float spec = 0.5;
	float xm = rest.z + HALF;
	if (p == 0 || p == 1) {
		float y = rest.y;
		c = skin(rest, xm, UV.y);
		if (p == 0) {
			// The blowhole: a dark crescent on top of the head, open to the front.
			vec2 b = vec2(rest.x, xm - BLOWHOLE);
			float ring = 1.0 - smoothstep(0.004, 0.008, abs(length(b) - 0.016));
			c = mix(c, vec3(0.015, 0.016, 0.02), max(ring * smoothstep(-0.005, 0.005, b.y), 1.0 - smoothstep(0.005, 0.01, length(b - vec2(0.0, 0.005)))) * step(0.0, y));
			// The upper lip: a dark line along the mouth.
			float lip = (1.0 - smoothstep(0.0, 0.008, y - mouth_y(xm))) * (1.0 - smoothstep(CORNER - 0.01, CORNER + 0.005, xm));
			c = mix(c, back, lip * 0.75 * (1.0 - inside));
		} else {
			// The lower jaw: its lip dark.
			float lip = 1.0 - smoothstep(0.0, 0.009, mouth_y(min(xm, CORNER)) - y);
			c = mix(c, back, lip * 0.7 * (1.0 - inside));
		}
		// The inside of the mouth: pink, darker towards the throat.
		vec3 in_mouth = mix(mouth, mouth * 0.3, smoothstep(0.08, CORNER + 0.02, xm));
		c = mix(c, in_mouth, smoothstep(0.1, 0.6, inside) * (1.0 - smoothstep(CORNER + 0.012, CORNER + 0.03, xm)));
		rough = mix(rough, 0.5, inside);
	} else if (p == 4 || p == 6) {
		// The flukes and flippers: dark, mottled, paler towards their edges underneath.
		vec2 s = scatter(rest / 0.05 + 7.0);
		c = mix(fin, pale * 0.8, (1.0 - smoothstep(0.2, 0.35, s.x)) * 0.35 * (1.0 - smoothstep(-0.2, 0.3, rest_normal.y)));
		c = mix(c, mix(fin, pale, 0.4), smoothstep(0.8, 1.0, UV.y) * 0.35);
		c *= 0.92 + 0.16 * noise3(rest * 40.0);
	} else if (p == 8) {
		// The tusk: ivory, yellowed and dirtier towards the root, darker in its spiral grooves,
		// clean and pale towards the tip.
		vec2 d = rest.xy - TUSK_ROOT.xy;
		float s = TUSK_ROOT.z - rest.z;
		float around = atan(d.y, d.x);
		float groove = 0.5 + 0.5 * cos(TUSK_STARTS * (around - TAU * s / TUSK_PITCH));
		float t = UV.x;
		c = mix(ivory * vec3(0.78, 0.72, 0.56), ivory, smoothstep(0.0, 0.4, t));
		c = mix(c, ivory * 1.05, smoothstep(0.85, 1.0, t));
		c *= 1.0 - 0.22 * smoothstep(0.55, 0.95, groove) * smoothstep(0.03, 0.12, t);
		c *= 0.94 + 0.12 * noise3(vec3(rest.xy * 200.0, rest.z * 8.0));
		rough = 0.35;
		spec = 0.55;
	} else {
		// An eye: dark brown, all but black, with a dark lid round it.
		float r = UV.x;
		c = mix(vec3(0.02, 0.016, 0.014), vec3(0.08, 0.06, 0.045), smoothstep(0.35, 0.7, r));
		c = mix(c, back, smoothstep(0.8, 1.0, r));
		rough = 0.12;
		spec = 0.7;
	}
	if (p == 7 && cartoon_eyes > 0.0) {
		float lit;
		vec3 toon = cartoon_eye(eye_at, lit);
		c = mix(c, toon, cartoon_eyes);
		rough = mix(rough, 0.2, cartoon_eyes);
		EMISSION = toon * lit * 0.6 * cartoon_eyes;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
