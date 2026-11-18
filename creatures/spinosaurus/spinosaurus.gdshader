shader_type spatial;
// The spinosaurus (spinosaurus.gd): every marking drawn here (no texture files), its swimming, its
// mouth, its eyes, and its stance in the shallows (`wade`). What each point is comes from the model
// (tools/build_spinosaurus.py): UV2.y the part (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower
// tooth, 4 the sail, 5 an arm, 6 a hind leg, 7 an eye, 8 the tail fins); UV2.x, on the body and the
// jaw, how much it is inside the mouth; on a limb, how far along it from its root (metres, as built).
// UV, on the body and jaw: x how far along, y how high on its side (1 the ridge of the back, 0 the
// keel of the belly); on the sail and the tail fins: x along, y up (from the root to the edge); on a
// limb: x along it, y 1 on a claw, 0.5 on a foot's web; on an eye: x middle (0) to rim (1).
//
// The model is built SWIMMING: its arms tucked back under its chest, its hind legs back along its
// tail. It swims SIDE TO SIDE, as a crocodile does: a wave that starts behind the chest and grows to
// the tip of its tall paddle of a tail, the head all but still. `wade` turns the limbs about their
// joints (each limb a chain of three hinges, the far one first) so that it stands on its hind legs
// in the shallows, its arms reaching down, its neck lifted. All of it is a function of `phase` and
// the settings, so a picture of it loops exactly. Nothing here needs more than GL Compatibility.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 14.0;
const float HALF = 7.0;
const float CORNER = 1.45;
const float HINGE_Y = -0.066;
const float HINGE_SPREAD = 0.22;
const vec2 EYE_AT = vec2(1.2, 0.17);
const float JAW_FROM = 0.04;
// The sail's spines: from where to where along the back, how many.
const float SAIL_FROM = 2.95;
const float SAIL_TO = 7.7;
const float SPINES = 17.0;
// The limbs' joints as built (metres behind the tip of the snout, metres up) and how far along the
// limb each joint is (metres): the arm's shoulder, elbow and wrist, the leg's hip, knee and ankle.
const vec2 SHOULDER = vec2(3.72, -0.55);
const vec2 ELBOW = vec2(4.18, -0.86);
const vec2 WRIST = vec2(4.62, -0.9);
const float AT_ELBOW = 0.558;
const float AT_WRIST = 1.0;
const vec2 HIP = vec2(5.85, -0.38);
const vec2 KNEE = vec2(6.58, -0.64);
const vec2 ANKLE = vec2(7.22, -0.58);
const float AT_KNEE = 0.873;
const float AT_ANKLE = 1.516;
// Wading: how far each joint turns (radians; more than 0 swings what lies behind it down), and how
// far the neck lifts and the head dips back to level.
const vec3 WADE_ARM = vec3(1.15, 1.03, 0.35);
const vec3 WADE_LEG = vec3(1.45, -0.14, 1.95);
const float WADE_NECK = 0.42;
const float WADE_HEAD = -0.3;
// How far the lower jaw swings down for `gape` 1, how far the skull lifts with it, and how far the
// middle line swings for `sway` 1 (of its length).
const float GAPE_MAX = 0.95;
const float LIFT_MAX = 0.12;
const float REACH = 0.07;

// How far through a beat of its tail (0..1, it wraps). Set by Spinosaurus.
uniform float phase = 0.0;
// How many times its tail beats in one beat (a whole number).
uniform float tail_beats = 1.0;
// Turning: how far the body is bent round to one side behind the neck, radians from the neck to the
// tip of the tail (more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// How widely it swims, for 1 as one cruising (the tail's tip swings about 1 m each way).
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape = 0.0;
// 0 swimming (its limbs tucked), 1 standing in the shallows on its hind legs, neck up, arms down.
uniform float wade = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;

// The back, the flank, the belly, the dark bands; the sail and its stripes; the claws; the inside of
// the mouth; the teeth.
uniform vec3 back : source_color = vec3(0.16, 0.18, 0.14);
uniform vec3 flank : source_color = vec3(0.36, 0.38, 0.3);
uniform vec3 belly : source_color = vec3(0.74, 0.7, 0.58);
uniform vec3 band : source_color = vec3(0.05, 0.06, 0.045);
uniform vec3 sail_colour : source_color = vec3(0.52, 0.4, 0.26);
uniform vec3 sail_stripe : source_color = vec3(0.13, 0.09, 0.06);
uniform vec3 claw : source_color = vec3(0.1, 0.08, 0.06);
uniform vec3 mouth : source_color = vec3(0.52, 0.24, 0.24);
uniform vec3 tooth : source_color = vec3(0.9, 0.86, 0.72);
// How strongly the bands across its back, flanks and tail show (0 none).
uniform float bands = 0.75;

// The cartoon eye (0 the eye as in life, 1 the cartoon eye), where its eyes look (x +1 towards the
// nose, y +1 up) and its lids (0 open, 1 shut). Set by the node.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// Where the right eye sits, as the model has it (the build script prints it: EYE_FRAME).
const vec3 EYE_CENTRE = vec3(0.09325, 0.17000, -5.80000);
const vec3 EYE_OUT = vec3(0.8195, 0.5197, -0.2417);
const vec3 EYE_FWD = vec3(-0.2041, -0.1295, -0.9703);
const vec3 EYE_UP = vec3(-0.5356, 0.8445, 0.0000);
const float EYE_SAG = 1.8675;
const float EYE_RADIUS = 0.045;
// The spinosaurus's: a sly, patient fisher. Bigger than life by 2.4; an amber iris with a tall
// crocodile's pupil, a knowing sideways look; a heavy brow of a crest over it, level then hooding
// down towards the snout, a lower lid that rises a little at the back (a crafty half-smile).
const float EYE_GROW = 2.4;
const vec3 SCLERA = vec3(0.86, 0.82, 0.6);
const vec3 IRIS_LIGHT = vec3(0.98, 0.72, 0.16);
const vec3 IRIS_DARK = vec3(0.58, 0.28, 0.04);
const float IRIS = 0.7;
const vec2 IRIS_AT = vec2(0.06, -0.03);
const vec2 LOOK_REACH = vec2(0.22, 0.14);
const vec2 GLINT_AT = vec2(0.24, 0.22);
const float GLINT = 0.1;
const vec2 GLINT2_AT = vec2(-0.18, -0.2);
const vec3 OUTLINE = vec3(0.02, 0.022, 0.015);
const float LINE_UP = 0.15;
const float LINE_DOWN = 0.06;

float pupil(vec2 q) {
	return (length(q / vec2(0.13, 0.55)) - 1.0) * 0.13;
}

float lid_up(float x) {
	return 0.42 - 0.18 * x - 0.14 * x * x;
}

float lid_down(float x) {
	return -0.62 - 0.12 * x + 0.16 * x * x;
}

vec3 lid_colour() {
	return mix(back, flank, 0.4);
}

varying vec2 eye_at;

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

vec3 cartoon_eye(vec2 e, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 q = e - IRIS_AT - clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK_REACH;
	float qi = length(q);
	vec3 c = SCLERA * (1.0 - 0.25 * smoothstep(0.5, 0.86, r));
	float rays = 0.5 + 0.5 * sin(atan(q.y, q.x) * 19.0);
	vec3 iris = mix(IRIS_LIGHT, IRIS_DARK, smoothstep(IRIS * 0.2, IRIS, qi) * 0.85 + rays * 0.12);
	c = mix(c, iris, 1.0 - smoothstep(IRIS - aa, IRIS + aa, qi));
	c = mix(c, vec3(0.005), 1.0 - smoothstep(-aa * 0.3, aa * 0.3, pupil(q)));
	float glint = max(1.0 - smoothstep(GLINT - aa, GLINT + aa, length(e - GLINT_AT)),
		1.0 - smoothstep(GLINT * 0.4 - aa, GLINT * 0.4 + aa, length(e - GLINT2_AT)));
	c = mix(c, vec3(1.0), glint);
	lit = mix(0.45, 1.0, glint);
	c = mix(c, OUTLINE, smoothstep(0.84 - aa, 0.86 + aa, r));
	float b = clamp(blink, 0.0, 1.0);
	float meet = mix(lid_down(e.x), lid_up(e.x), 0.55);
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

// How far to the side the middle line is `xm` metres behind the tip: a wave running back, least
// at the chest, growing all the way down the tail.
float side_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * REACH * (0.06 - 0.34 * s + 0.6 * s * s + 0.62 * s * s * s);
	return sway * (1.0 - 0.6 * clamp(wade, 0.0, 1.0)) * reach * sin(TAU * (tail_beats * phase - s / wave));
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 2.5 - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - 2.5);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// Turns `v` and `n` by `a` about a line across the body (along X) through `pivot` (xm, y): more than
// 0 turns what lies behind the pivot down (and what lies ahead of it up).
void hinge(inout vec3 v, inout vec3 n, vec2 pivot, float a) {
	vec2 p = vec2(pivot.y, pivot.x - HALF);
	vec2 d = v.yz - p;
	float c = cos(a);
	float s = sin(a);
	v.yz = p + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
	n.yz = vec2(n.y * c - n.z * s, n.y * s + n.z * c);
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
	float open = clamp(gape, 0.0, 1.0);
	if (p == 1 || p == 3) {
		// The lower jaw swings down about the corner of the mouth (with the skull's lift against it,
		// below); behind the corner, inside the throat, it stays.
		hinge(v, n, vec2(CORNER, HINGE_Y), -GAPE_MAX * open * smoothstep(CORNER + 0.04, CORNER - HINGE_SPREAD, v.z + HALF));
	} else if ((p == 0 || p == 2 || p == 7) && open > 0.0) {
		float w = smoothstep(CORNER + 0.45, CORNER - 0.1, v.z + HALF) * smoothstep(HINGE_Y - 0.1, HINGE_Y + 0.04, v.y);
		hinge(v, n, vec2(CORNER, HINGE_Y), LIFT_MAX * open * w);
	}
	float st = clamp(wade, 0.0, 1.0);
	if (st > 0.0) {
		float along = UV2.x;
		if (p == 5) {
			// An arm: the hand, then the forearm, then the whole arm, each about its joint.
			hinge(v, n, WRIST, WADE_ARM.z * st * smoothstep(AT_WRIST - 0.04, AT_WRIST + 0.04, along));
			hinge(v, n, ELBOW, WADE_ARM.y * st * smoothstep(AT_ELBOW - 0.05, AT_ELBOW + 0.05, along));
			hinge(v, n, SHOULDER, WADE_ARM.x * st);
		} else if (p == 6) {
			hinge(v, n, ANKLE, WADE_LEG.z * st * smoothstep(AT_ANKLE - 0.04, AT_ANKLE + 0.06, along));
			hinge(v, n, KNEE, WADE_LEG.y * st * smoothstep(AT_KNEE - 0.06, AT_KNEE + 0.06, along));
			hinge(v, n, HIP, WADE_LEG.x * st);
		} else {
			// The head dips back towards level, then the neck lifts it (the jaw, teeth and eyes with it).
			float xm = v.z + HALF;
			hinge(v, n, vec2(1.7, 0.0), WADE_HEAD * st * smoothstep(1.95, 1.45, xm));
			hinge(v, n, vec2(3.0, 0.05), WADE_NECK * st * smoothstep(3.3, 2.3, xm));
		}
	}
	float xm = v.z + HALF;
	float h = side_at(xm);
	float slope = (side_at(xm + 0.03) - side_at(xm - 0.03)) / 0.06;
	float turn = atan(slope);
	float c = cos(turn);
	float sn = sin(turn);
	v = vec3(h + v.x * c, v.y, v.z - v.x * sn);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

float mouth_y(float xm) {
	return -0.03 - 0.025 * xm;
}

// The scaly hide at a place: `xm` behind the tip, `h` how high on its side (0..1).
vec3 skin(float xm, float h, float side) {
	float grain = noise2(vec2(xm * 34.0, h * 26.0 + side * 9.0));
	float scales = noise2(vec2(xm * 110.0, h * 80.0 + side * 3.0));
	float cloud = noise2(vec2(xm * 1.4, h * 4.0) + 3.0 + side * 5.0);
	// Countershaded: a pale belly, grey-green flanks, a dark back; the line between wavering.
	vec3 c = mix(belly, flank, smoothstep(0.2, 0.36, h + (cloud - 0.5) * 0.1));
	c = mix(c, back, smoothstep(0.6, 0.85, h + (cloud - 0.5) * 0.1));
	// Dark bands across the back and flanks from the neck to the tip of the tail, wavering and
	// forking a little, wider apart down the tail.
	float wob = noise2(vec2(xm * 2.0, h * 3.0 + side * 7.0));
	float k = mix(11.0, 6.5, smoothstep(5.0, 12.0, xm));
	float b = smoothstep(0.35, 0.8, sin(xm * k + wob * 2.6 + h * 1.4));
	b *= smoothstep(0.3, 0.55, h) * smoothstep(1.7, 2.4, xm);
	c = mix(c, band, b * bands * 0.85);
	// (fine scales: a light grain, darker in the crevices)
	c *= 0.86 + 0.14 * grain + 0.1 * scales;
	return c;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.6;
	float spec = 0.4;
	float xm = rest.z + HALF;
	float side = rest.x >= 0.0 ? 1.0 : -1.0;
	if (p == 0 || p == 1) {
		float y = rest.y;
		c = skin(xm, UV.y, side);
		if (p == 0) {
			// The nostrils: two slits set far back on top of the snout.
			vec2 nn = vec2(xm - 0.82, abs(rest.x) - 0.045);
			c = mix(c, vec3(0.01), (1.0 - smoothstep(0.7, 1.0, length(nn / vec2(0.09, 0.012)))) * step(0.0, y));
			// The brow over the eye, a little darker; the rosette's tip darker still.
			vec2 e = vec2(xm - EYE_AT.x, y - EYE_AT.y - 0.03);
			c = mix(c, back * 0.7, (1.0 - smoothstep(0.05, 0.1, length(e * vec2(0.55, 1.0)))) * 0.7);
			float lip = (1.0 - smoothstep(0.0, 0.028, y - mouth_y(xm))) * (1.0 - smoothstep(CORNER - 0.02, CORNER + 0.02, xm));
			c = mix(c, mix(flank, belly, 0.55), lip * 0.6 * (1.0 - inside));
		} else {
			float lip = 1.0 - smoothstep(0.0, 0.028, mouth_y(min(xm, CORNER)) - y);
			c = mix(c, mix(flank, belly, 0.55), lip * 0.5 * (1.0 - inside));
		}
		vec3 in_mouth = mix(mouth, mouth * 0.25, smoothstep(0.4, CORNER + 0.05, xm));
		c = mix(c, in_mouth, smoothstep(0.1, 0.6, inside) * smoothstep(JAW_FROM, JAW_FROM + 0.05, xm) * (1.0 - smoothstep(CORNER + 0.04, CORNER + 0.12, xm)));
		rough = mix(rough, 0.45, inside);
	} else if (p == 2 || p == 3) {
		c = mix(tooth * 0.55, tooth, smoothstep(0.1, 0.55, UV.x));
		rough = 0.3;
		spec = 0.5;
	} else if (p == 4 || p == 8) {
		// The sail (and the fins of the tail): ochre skin over the spines, a dark stripe up each spine,
		// darker at its root where it meets the back, paler towards the edge.
		float pitch = (SAIL_TO - SAIL_FROM) / SPINES;
		float f = (xm - SAIL_FROM) / pitch;
		float k = p == 4 ? f : xm / 0.32;
		float stripe = 1.0 - smoothstep(0.1, 0.32, abs(fract(k) - 0.5));
		float grain = noise2(vec2(xm * 20.0, rest.y * 14.0));
		vec3 base = p == 4 ? sail_colour : mix(back, sail_colour, 0.35);
		c = mix(base, base * 1.2, smoothstep(0.4, 1.0, UV.y));
		c = mix(c, sail_stripe, stripe * mix(0.75, 0.45, UV.y));
		c = mix(c, back, (1.0 - smoothstep(0.0, 0.18, UV.y)) * 0.8);
		c *= 0.88 + 0.22 * grain;
	} else if (p == 5 || p == 6) {
		// A limb: the flank's colour, darker on top; banded on the legs; dark horn claws; a dark web.
		float lit_up = smoothstep(-0.4, 0.6, rest_normal.y);
		c = mix(mix(belly, flank, 0.6), mix(flank, back, 0.5), lit_up);
		c *= 0.86 + 0.24 * noise2(rest.xz * 30.0 + rest.y * 9.0);
		if (UV.y > 0.75) {
			c = mix(claw, claw * 3.0, smoothstep(0.6, 1.0, UV.x) * 0.0 + 0.15);
			rough = 0.35;
			spec = 0.5;
		} else if (UV.y > 0.25) {
			c = mix(back, flank, 0.3) * 0.8;
		}
	} else {
		// An eye, as in life: amber with a dark slit, a dark rim.
		float r = length(eye_at);
		c = mix(vec3(0.75, 0.5, 0.1), vec3(0.03), smoothstep(0.78, 0.92, r));
		c = mix(c, vec3(0.01), 1.0 - smoothstep(0.1, 0.16, abs(eye_at.x) + max(abs(eye_at.y) - 0.45, 0.0)));
		rough = 0.1;
		spec = 0.7;
	}
	if (p == 7 && cartoon_eyes > 0.0) {
		float lit;
		vec3 toon = cartoon_eye(eye_at, lit);
		c = mix(c, toon, cartoon_eyes);
		rough = mix(rough, lit > 0.01 ? 0.2 : 0.6, cartoon_eyes);
		EMISSION = toon * lit * 0.6 * cartoon_eyes;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
