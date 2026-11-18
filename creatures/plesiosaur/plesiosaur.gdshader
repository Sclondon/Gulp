shader_type spatial;
// The plesiosaur (plesiosaur.gd): every marking drawn here (no texture files), its rowing, its neck,
// its mouth and its eyes. What each point is comes from the model (tools/build_plesiosaur.py): UV2.y
// the part (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower tooth, 6 a fore flipper, 7 an eye, 8 a
// hind flipper); UV2.x, on the body and the jaw, how much it is inside the mouth. UV, on the body and
// jaw: x how far along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on
// a flipper: x root (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0)
// to rim (1).
//
// It swims by ROWING ITS FOUR FLIPPERS, each tip tracing a figure of eight (up and down once, fore
// and aft twice, in each stroke) and feathering as it goes, the hind pair half a stroke behind the
// fore; its body stays stiff, its short tail swings a little. The long neck bends where `neck` and
// `curl` say. All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 9.0;
const float HALF = 4.5;
// Where the neck meets the body and where the head ends (metres behind the tip of the snout): the
// neck bends between, the head stays stiff.
const float NECK_BASE = 4.6;
const float HEAD_END = 0.5;
// Where the hips are: behind them the tail bends with `curl`.
const float HIPS = 7.4;
// The corner of the mouth, where the lower jaw hinges (metres behind the tip, metres up).
const float CORNER = 0.42;
const float HINGE_Y = -0.0206;
const float HINGE_SPREAD = 0.03;
const float JAW_FROM = 0.006;
const vec2 EYE_AT = vec2(0.31, 0.034);
// How far the lower jaw swings down for `gape` 1 (radians); how far the neck bends for `neck` 1
// (radians from shoulders to head: to the side, up and down); how much of `curl` the neck takes
// (the rest bends the tail).
const float GAPE_MAX = 0.75;
const vec2 NECK_MAX = vec2(1.2, 0.9);
const float CURL_NECK = 0.7;
// The flippers' rowing for `sway` 1 (radians): up and down, fore and aft, feathering; how far behind
// the fore pair the hind pair is (of a stroke); how far the tail's tip swings (metres).
const float FLAP = 0.45;
const float SWEEP = 0.2;
const float FEATHER = 0.5;
const float HIND_LAG = 0.5;
const float TAIL_SWING = 0.14;
// Where the right flippers' roots are and which ways they reach and run, as the model has them (the
// build script prints them: FLIPPER_FRAME; the left ones are their mirrors).
const vec3 FORE_ROOT = vec3(0.4367, -0.3200, 0.8000);
const vec3 FORE_SPAN = vec3(0.9322, -0.2051, 0.2983);
const vec3 FORE_CHORD = vec3(-0.2933, 0.0549, 0.9544);
const vec3 HIND_ROOT = vec3(0.4339, -0.3000, 2.4500);
const vec3 HIND_SPAN = vec3(0.9036, -0.1988, 0.3795);
const vec3 HIND_CHORD = vec3(-0.3727, 0.0721, 0.9251);

// How far through a stroke of its flippers (0..1, it wraps). Set by Plesiosaur.
uniform float phase = 0.0;
// Turning: how far it is bent round to one side, in radians from head to tail, most of it in the neck
// (0 straight; more than 0 the tail comes round to +X, and the head too: a C).
uniform float curl = 0.0;
// The neck swung on its own: x to the side (+1 the head swung 1.2 radians to its right, +X), y up
// (+1 the head raised 0.9 radians), from the shoulders; the head stays straight on its end.
uniform vec2 neck = vec2(0.0);
// How widely it rows, for 1 as one cruising; 0 the flippers held still.
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape = 0.0;

// The back, the flank, the belly, the pale dapples; the flippers; the inside of the mouth; the teeth.
uniform vec3 back : source_color = vec3(0.12, 0.13, 0.15);
uniform vec3 flank : source_color = vec3(0.34, 0.36, 0.38);
uniform vec3 belly : source_color = vec3(0.86, 0.84, 0.78);
uniform vec3 dapple : source_color = vec3(0.32, 0.35, 0.37);
uniform vec3 fin : source_color = vec3(0.1, 0.11, 0.13);
uniform vec3 mouth : source_color = vec3(0.62, 0.32, 0.32);
uniform vec3 tooth : source_color = vec3(0.93, 0.9, 0.8);
// How strongly the pale dapples on its back and the faint bands on its neck show (0 none).
uniform float dapples = 0.6;

// The cartoon eye (0 the eye as in life, 1 the cartoon eye), where its eyes look (x +1 towards the
// nose, y +1 up, each in its own plane) and its lids (0 open, 1 shut). Set by the node.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// Where the right eye sits, as the model has it (the build script prints it: EYE_FRAME; the left eye
// is its mirror): its middle on the skin, the way out of the head, the way to the nose and the way up
// in the eye's own plane, how fast the skin falls away from that plane round it (metres per square
// metre), and the eye's radius.
const vec3 EYE_CENTRE = vec3(0.07922, 0.03400, -4.19000);
const vec3 EYE_OUT = vec3(0.9098, 0.3756, -0.1767);
const vec3 EYE_FWD = vec3(-0.1634, -0.0674, -0.9843);
const vec3 EYE_UP = vec3(-0.3816, 0.9243, 0.0000);
const float EYE_SAG = 2.5851;
const float EYE_RADIUS = 0.024;
// The plesiosaur's: gentle and wide-eyed. Bigger than life by 1.6; a soft white, a big warm dark
// brown iris, a big round pupil, two big highlights; the upper lid high in a soft round arch, the
// lower lid low (wide open, mild), thin lines.
const float EYE_GROW = 1.6;
const vec3 SCLERA = vec3(0.96, 0.95, 0.92);
const vec3 IRIS_LIGHT = vec3(0.5, 0.32, 0.18);
const vec3 IRIS_DARK = vec3(0.16, 0.09, 0.05);
const float IRIS = 0.6;
const vec2 IRIS_AT = vec2(0.04, -0.02);
const vec2 LOOK_REACH = vec2(0.24, 0.18);
const vec2 GLINT_AT = vec2(0.2, 0.26);
const float GLINT = 0.19;
const vec2 GLINT2_AT = vec2(-0.16, -0.16);
const vec3 OUTLINE = vec3(0.03, 0.03, 0.04);
const float LINE_UP = 0.07;
const float LINE_DOWN = 0.04;

// (inside the pupil where this is under 0; `q` from the iris's middle, in eye radii)
float pupil(vec2 q) {
	return length(q) - 0.36;
}

float lid_up(float x) {
	return 0.92 - 0.12 * x * x;
}

float lid_down(float x) {
	return -0.8 + 0.1 * x * x;
}

vec3 lid_colour() {
	return mix(back, flank, 0.4);
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

// The cartoon eye's colour at `e` (eye_at); `lit` how much of it glows a little.
vec3 cartoon_eye(vec2 e, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 q = e - IRIS_AT - clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK_REACH;
	float qi = length(q);
	vec3 c = SCLERA * (1.0 - 0.15 * smoothstep(0.5, 0.86, r));
	vec3 iris = mix(IRIS_LIGHT, IRIS_DARK, smoothstep(IRIS * 0.5, IRIS, qi));
	iris = mix(iris, IRIS_LIGHT * 1.2, (1.0 - smoothstep(0.0, IRIS * 0.7, qi)) * 0.3);
	c = mix(c, iris, 1.0 - smoothstep(IRIS - aa, IRIS + aa, qi));
	c = mix(c, vec3(0.01), 1.0 - smoothstep(-aa, aa, pupil(q)));
	float glint = max(1.0 - smoothstep(GLINT - aa, GLINT + aa, length(e - GLINT_AT)),
		1.0 - smoothstep(GLINT * 0.5 - aa, GLINT * 0.5 + aa, length(e - GLINT2_AT)));
	c = mix(c, vec3(1.0), glint);
	lit = mix(0.5, 1.0, glint);
	c = mix(c, OUTLINE, smoothstep(0.85 - aa, 0.87 + aa, r));
	// the lids, meeting a little below the middle as it blinks
	float b = clamp(blink, 0.0, 1.0);
	float meet = mix(lid_down(e.x), lid_up(e.x), 0.4);
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

// `p` turned by `a` about the unit `axis` (through the origin).
vec3 turned(vec3 p, vec3 axis, float a) {
	float c = cos(a);
	return p * c + cross(axis, p) * sin(a) + axis * dot(axis, p) * (1.0 - c);
}

// A right flipper's point (and normal) rowed about its root: feathered about its span, flapped up and
// down about its chord, swept fore and aft about the upright; `t` how far out along it the point is
// (its tip bends a little further and later).
void row(inout vec3 v, inout vec3 n, vec3 root, vec3 span, vec3 chord, float at, float t) {
	float a = TAU * at;
	float bend = 1.0 + 0.25 * t;
	float feather = FEATHER * sway * cos(a);
	float flap = FLAP * sway * sin(a - 0.25 * t) * bend;
	float sweep = SWEEP * sway * sin(2.0 * a);
	vec3 d = v - root;
	d = turned(d, span, feather);
	n = turned(n, span, feather);
	d = turned(d, chord, flap);
	n = turned(n, chord, flap);
	d = turned(d, vec3(0.0, 1.0, 0.0), sweep);
	n = turned(n, vec3(0.0, 1.0, 0.0), sweep);
	v = root + d;
}

// The neck (all ahead of NECK_BASE) bent round an arc by `bend` (radians from the shoulders to the
// head: x to the side, y up); the head beyond HEAD_END carried straight on its end.
void neck_bend(inout vec3 v, inout vec3 n, vec2 bend) {
	float th = length(bend);
	if (th < 0.001) {
		return;
	}
	vec2 dir = bend / th;
	float zb = NECK_BASE - HALF;
	float f = zb - v.z;
	if (f <= 0.0) {
		return;
	}
	float reach = NECK_BASE - HEAD_END;
	float k = th / reach;
	float r = 1.0 / k;
	float w = dot(v.xy, dir);
	vec2 across = v.xy - dir * w;
	float s = min(f, reach);
	float a = s * k;
	float c = cos(a);
	float sn = sin(a);
	float along = (r - w) * sn + (f - s) * c;
	float side = r - (r - w) * c + (f - s) * sn;
	v.xy = across + dir * side;
	v.z = zb - along;
	float nw = dot(n.xy, dir);
	vec2 n_across = n.xy - dir * nw;
	float nf = -n.z;
	n.xy = n_across + dir * (nw * c + nf * sn);
	n.z = -(-nw * sn + nf * c);
}

// The tail behind the hips laid round an arc to one side by `a` radians to its tip (more than 0, to +X).
void tail_bend(inout vec3 v, inout vec3 n, float a_all) {
	float from = HIPS - HALF;
	float d = v.z - from;
	if (abs(a_all) < 0.001 || d <= 0.0) {
		return;
	}
	float k = a_all / (LENGTH - HIPS);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
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
	if (p == 1 || p == 3) {
		// The lower jaw (and its teeth) swings down about the corner of the mouth; behind the
		// corner, inside the head, it stays.
		float a = GAPE_MAX * clamp(gape, 0.0, 1.0) * smoothstep(CORNER + 0.01, CORNER - HINGE_SPREAD, v.z + HALF);
		vec2 hinge = vec2(HINGE_Y, CORNER - HALF);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	if (p == 6 || p == 8) {
		// A flipper rows about its root (the left ones as mirrors of the right).
		vec3 m = vec3(v.x >= 0.0 ? 1.0 : -1.0, 1.0, 1.0);
		vec3 mv = v * m;
		vec3 mn = n * m;
		if (p == 6) {
			row(mv, mn, FORE_ROOT, FORE_SPAN, FORE_CHORD, phase, UV.x);
		} else {
			row(mv, mn, HIND_ROOT, HIND_SPAN, HIND_CHORD, phase - HIND_LAG, UV.x);
		}
		v = mv * m;
		n = mn * m;
	}
	// The short tail swings a little, side to side, once a stroke.
	float xm = v.z + HALF;
	float s = clamp((xm - HIPS) / (LENGTH - HIPS), 0.0, 1.0);
	float swing = TAIL_SWING * sway * s * s * sin(TAU * (phase - 0.3 * s));
	float slope = TAIL_SWING * sway * 2.0 * s * sin(TAU * (phase - 0.3 * s)) / (LENGTH - HIPS);
	float turn = atan(slope);
	v.x += swing;
	n = vec3(n.x * cos(turn) + n.z * sin(turn), n.y, -n.x * sin(turn) + n.z * cos(turn));
	neck_bend(v, n, vec2(neck.x * NECK_MAX.x + curl * CURL_NECK, neck.y * NECK_MAX.y));
	tail_bend(v, n, curl * (1.0 - CURL_NECK));
	VERTEX = v;
	NORMAL = n;
}

// The line of the mouth, as the model has it.
float mouth_y(float xm) {
	return -0.008 - 0.03 * xm;
}

// The skin at a place: `xm` behind the tip, `h` how high on its side (0..1).
vec3 skin(float xm, float h, float side) {
	float grain = noise2(vec2(xm * 50.0, h * 30.0 + side * 9.0));
	float cloud = noise2(vec2(xm * 2.5, h * 5.0) + 3.0 + side * 5.0);
	// Countershaded: the belly pale, the flank grey, the back dark, the line between wavering.
	float edge = 0.56 + (cloud - 0.5) * 0.1;
	vec3 c = mix(belly, flank, smoothstep(0.26, 0.44, h + (cloud - 0.5) * 0.06));
	c = mix(c, back, smoothstep(edge - 0.1, edge + 0.06, h));
	// Pale dapples over the back of the body, and faint dark bands round the top of the neck.
	vec2 at = vec2(xm * 2.2, h * 6.0 + side * 3.0);
	vec2 cell = floor(at);
	vec2 in_cell = fract(at) - 0.5 - (vec2(hash2(cell), hash2(cell + 5.0)) - 0.5) * 0.5;
	float spot = (1.0 - smoothstep(0.12, 0.26, length(in_cell * vec2(1.0, 1.4)))) * step(0.35, hash2(cell + 9.0));
	c = mix(c, dapple, spot * dapples * smoothstep(0.55, 0.75, h) * smoothstep(4.3, 4.9, xm) * (1.0 - smoothstep(8.2, 8.8, xm)));
	float band = smoothstep(0.55, 0.95, sin(xm * 5.5 + (cloud - 0.5) * 2.0)) * smoothstep(0.5, 0.75, h) * smoothstep(0.6, 1.0, xm) * (1.0 - smoothstep(4.0, 4.6, xm));
	c = mix(c, c * 0.6, band * dapples);
	c *= 0.93 + 0.14 * grain;
	return c;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.42;
	float spec = 0.5;
	float xm = rest.z + HALF;
	float side = rest.x >= 0.0 ? 1.0 : -1.0;
	if (p == 0 || p == 1) {
		float y = rest.y;
		c = skin(xm, UV.y, side);
		if (p == 0) {
			// The nostrils: small dark slits ahead of the eyes, high on the snout.
			vec2 nn = vec2(xm - 0.2, abs(rest.x) - 0.03);
			c = mix(c, vec3(0.02), (1.0 - smoothstep(0.6, 1.0, length(nn / vec2(0.014, 0.005)))) * step(0.0, y));
			// A darker rim of skin round the eye.
			vec2 e = vec2(xm - EYE_AT.x, y - EYE_AT.y);
			c = mix(c, back * 0.8, (1.0 - smoothstep(0.024, 0.04, length(e))) * 0.6);
			float lip = (1.0 - smoothstep(0.0, 0.004, y - mouth_y(xm))) * (1.0 - smoothstep(CORNER - 0.005, CORNER + 0.003, xm));
			c = mix(c, c * 0.5, lip * 0.7 * (1.0 - inside));
		} else {
			float lip = 1.0 - smoothstep(0.0, 0.004, mouth_y(min(xm, CORNER)) - y);
			c = mix(c, flank * 0.7, lip * 0.6 * (1.0 - inside));
		}
		// The inside of the mouth: pink, darker towards the throat (not at the very tip).
		vec3 in_mouth = mix(mouth, mouth * 0.3, smoothstep(0.1, CORNER + 0.01, xm));
		c = mix(c, in_mouth, smoothstep(0.1, 0.6, inside) * smoothstep(JAW_FROM, JAW_FROM + 0.02, xm) * (1.0 - smoothstep(CORNER + 0.006, CORNER + 0.02, xm)));
		rough = mix(rough, 0.5, inside);
	} else if (p == 2 || p == 3) {
		// A fang: ivory, darker at the gum.
		c = mix(tooth * 0.7, tooth, smoothstep(0.1, 0.5, UV.x));
		rough = 0.3;
	} else if (p == 6 || p == 8) {
		// A flipper: dark above, pale below, its leading edge paler, the dapples running onto it.
		c = mix(mix(belly, flank, 0.35), fin, smoothstep(-0.25, 0.25, rest_normal.y));
		c = mix(c, c * 1.35, (1.0 - smoothstep(0.0, 0.15, UV.y)) * 0.4);
		vec2 at = vec2(UV.x * 7.0, UV.y * 2.5);
		float spot = (1.0 - smoothstep(0.15, 0.3, length(fract(at) - 0.5))) * step(0.5, hash2(floor(at) + side * 3.0));
		c = mix(c, dapple, spot * dapples * 0.6 * smoothstep(0.0, 0.2, rest_normal.y));
	} else {
		// An eye, as in life: dark, with a warm brown iris and a dark rim.
		float r = length(eye_at);
		c = mix(vec3(0.01), vec3(0.3, 0.18, 0.08), smoothstep(0.4, 0.48, r));
		c = mix(c, vec3(0.03), smoothstep(0.8, 0.95, r));
		rough = 0.1;
		spec = 0.7;
	}
	if (p == 7 && cartoon_eyes > 0.0) {
		float lit;
		vec3 toon = cartoon_eye(eye_at, lit);
		c = mix(c, toon, cartoon_eyes);
		// (shiny where the eye shows, not on the lids)
		rough = mix(rough, lit > 0.01 ? 0.2 : 0.6, cartoon_eyes);
		EMISSION = toon * lit * 0.6 * cartoon_eyes;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
