shader_type spatial;
// The Pacific bluefin tuna (bluefin_tuna.gd): every marking drawn here (no texture files), its
// swimming and its jaw. It began as GameCommon's yellowfin tuna's shader. What each point is
// comes from the model (tools/build_bluefin_tuna.py): UV2.y the part (0 body, 1 first dorsal,
// 2 the second dorsal and the anal fin, 3 a finlet, 4 the tail, 5 a pectoral fin, 6 a pelvic fin,
// 7 an eye, 8 a gill: see `throat` in the build script). UV, on the body: x how far along, y how high on its side (1 the ridge of the back,
// 0 the keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge
// (1); on an eye: x middle (0) to rim (1). UV2.x, on the first dorsal, how far the point stands
// above the fin's root (metres); on the body, what it is of the mouth (0 skin, 1 the lower jaw's
// skin, 2 the roof of the mouth, 3 its floor, 4 a tooth above, 5 a tooth below: the odd ones
// swing with the jaw).
//
// The model is drawn 1.5 long ("units", the yellowfin's numbers) and scaled to LENGTH: every
// measure below is in units but where it says metres.
//
// It swims as tunas do (thunniform): the body all but rigid, a wave that only grows large in the
// last third, the tail wrist flexing and the stiff crescent tail swung as one plate. All of it is
// a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model (its SHAPE line).
const float LENGTH = 2.5;
const float U = LENGTH / 1.5;
const float HALF = 0.75;
// Where the tail fin is hinged (units behind the snout): behind it the tail is one stiff plate.
const float JOINT = 1.335;
// Where the lower jaw hinges (units behind the snout, units above the middle line); how much of
// the jaw's length, ahead of the hinge, bends rather than swings; how far the jaw drops and the
// snout lifts with the mouth wide open (radians).
const float HINGE = 0.14;
const float HINGE_Y = -0.0536;
const float SOFT = 0.4;
const float JAW_DROP = 0.62;
const float SNOUT_LIFT = 0.06;
const float GILL = 0.385;
const vec2 EYE_AT = vec2(0.152, 0.026);

// How far through a beat of its tail (0..1, it wraps). Set by BluefinTuna.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left).
// The head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// The mouth: 0 shut, 1 wide open, as when it bites.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How widely it beats, for 1 as a tuna cruising (its tail tips swing about 0.2 m either way).
uniform float sway = 1.0;
// How far the first dorsal fin is raised (0 folded down into its groove, 1 up).
uniform float first_dorsal = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;

// The back, and the metallic blue it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.006, 0.012, 0.035);
uniform vec3 back_blue : source_color = vec3(0.02, 0.075, 0.26);
// The flank and the belly; the pale lines and dots low on them.
uniform vec3 silver : source_color = vec3(0.56, 0.6, 0.66);
uniform vec3 belly : source_color = vec3(0.9, 0.91, 0.92);
uniform vec3 marks : source_color = vec3(0.97, 0.98, 1.0);
// The second dorsal (reddish brown); the anal fin and the finlets (a dusky yellow), the finlets'
// black edges; the tail and the pectoral fins; the first dorsal.
uniform vec3 fin_red : source_color = vec3(0.36, 0.13, 0.07);
uniform vec3 fin_yellow : source_color = vec3(0.78, 0.62, 0.12);
uniform vec3 fin_edge : source_color = vec3(0.02, 0.02, 0.025);
uniform vec3 tail_dark : source_color = vec3(0.03, 0.04, 0.065);
uniform vec3 fin_dusk : source_color = vec3(0.16, 0.19, 0.2);
// The inside of the mouth.
uniform vec3 mouth : source_color = vec3(0.16, 0.035, 0.04);
// How strongly the pale marks on the belly show.
uniform float marks_show = 0.3;

// The cartoon eye (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0 the eye as it always was, 1 the cartoon eye: bigger, a white, a coloured iris, a big
// pupil, a highlight and a dark outline, under a lid that gives it its character. The bluefin's: the
// heavy, unbothered old boss: a small steel-blue iris filling most of the eye, a round pupil, a heavy
// flat lid down over its top third.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the pupil and iris look, in the eye's own flat: x towards the snout (+) or the tail (-), y up
// (+) or down (-), each -1 to 1.
uniform vec2 eye_look = vec2(0.0);
// A lid the colour of the skin closing over the cartoon eye: 0 open, 1 shut.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.32, 0.46, 0.62);
// The gills (added 2026-11-18): the red of the gill arches and their filaments, seen through the open mouth.
uniform vec3 gill_red : source_color = vec3(0.6, 0.05, 0.07);
// As the model has it (its EYE line): the middle of the left eye on the skin, the way the skin faces
// there (units), the eye's radius.
const vec3 EYE_MID = vec3(0.08427, 0.02600, -0.59800);
const vec3 EYE_OUT = vec3(0.91521, 0.17230, -0.36428);
const float EYE_RADIUS = 0.023;
// The cartoon eye's character: how much bigger it is drawn; the iris's radius and the pupil's (shares
// of the eye's); the pupil's shape (0 round, 1 a teardrop pointing forward); how far the iris roams
// for `eye_look`; the lid's edge (how high at the middle, how much higher towards the snout); where
// the highlight is.
const float EYE_GROW = 1.5;
const float IRIS = 0.7;
const float PUPIL = 0.3;
const int PUPIL_SHAPE = 0;
const float EYE_ROAM = 0.22;
const float LID = 0.3;
const float LID_TILT = 0.06;
const vec2 SHINE = vec2(0.3, 0.05);

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
// (0 skin, 1 the inside of the mouth, 2 a tooth)
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

// How far to one side the middle line of the body is, `xm` units behind the snout: a wave that
// runs back along it, all but nothing as far as the middle, large only near the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = 1.05 * (0.012 - 0.03 * s + 0.03 * s * s + 0.085 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.3;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / 1.05;
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// The cartoon eye: the dome grown about its middle (`cartoon_eyes`), along the skin, its rim following
// the skin as the head curves away from it.
void eye_grow(inout vec3 v) {
	if (cartoon_eyes <= 0.0) {
		return;
	}
	float sx = v.x < 0.0 ? -1.0 : 1.0;
	vec3 mid = vec3(EYE_MID.x * sx, EYE_MID.y, EYE_MID.z);
	vec3 o = normalize(vec3(EYE_OUT.x * sx, EYE_OUT.y, EYE_OUT.z));
	vec3 d = v - mid;
	float dn = dot(d, o);
	vec3 dt = d - dn * o;
	float k = mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
	dn = dn < 0.0 ? dn * k * k : dn * k;
	v = mid + dt * k + o * dn;
}

// The cartoon eye's colour at `e`, a place in the eye's own flat (x towards the snout, y up, 1 its rim),
// under a lid of `skin`.
vec3 cartoon_eye(vec2 e, vec3 skin) {
	float r = length(e);
	vec2 look = eye_look;
	if (length(look) > 1.0) {
		look = normalize(look);
	}
	vec2 at = e - look * EYE_ROAM;
	// the white, a little grey towards its rim so that it reads as a ball
	vec3 c = vec3(0.95, 0.95, 0.92) * (1.0 - 0.22 * smoothstep(0.45, 0.95, r));
	// the iris: lighter in its middle, fine fibres, a dark ring round it
	float ri = length(at) / IRIS;
	vec3 iris = mix(eye_iris * 1.3, eye_iris * 0.6, smoothstep(0.25, 1.0, ri)) * (0.9 + 0.1 * sin(atan(at.y, at.x) * 22.0));
	c = mix(c, iris, 1.0 - smoothstep(0.97, 1.02, ri));
	c = mix(c, eye_iris * 0.25, smoothstep(0.86, 0.96, ri) * (1.0 - smoothstep(0.98, 1.03, ri)));
	// the pupil
	vec2 p = at / PUPIL;
	if (PUPIL_SHAPE == 1) {
		// (a teardrop that points forward, as a tuna's gap ahead of its lens)
		float ahead = max(p.x, 0.0);
		p = vec2(p.x > 0.0 ? p.x * 0.62 : p.x, p.y * (1.0 + 0.55 * ahead));
	}
	c = mix(c, vec3(0.008, 0.009, 0.012), 1.0 - smoothstep(0.94, 1.04, length(p)));
	// the highlight, which stays put towards the light, and a small glint below it
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.85, 1.0, length(e - SHINE) / 0.16));
	c = mix(c, vec3(1.0), 0.8 * (1.0 - smoothstep(0.8, 1.0, length(e - vec2(-0.6 * SHINE.x, SHINE.y - 0.42)) / 0.065)));
	// the lid, closing down over it for `blink`, its edge a dark line
	float lid_y = mix(LID + LID_TILT * e.x, -1.25, clamp(blink, 0.0, 1.0));
	c = mix(c, skin, smoothstep(-0.015, 0.015, e.y - lid_y));
	c = mix(c, vec3(0.01, 0.012, 0.02), (1.0 - smoothstep(0.035, 0.08, abs(e.y - lid_y))) * (1.0 - smoothstep(0.9, 1.0, r)));
	// the outline
	return mix(c, vec3(0.01, 0.012, 0.02), smoothstep(0.82, 0.9, r));
}

void vertex() {
	part = UV2.y;
	vec3 v = VERTEX / U;
	vec3 n = NORMAL;
	rest = v;
	rest_normal = n;
	float what = part < 0.5 ? UV2.x : 0.0;
	inside = floor(what * 0.5 + 0.2);
	float jaw = what - 2.0 * inside;
	if (part > 0.5 && part < 1.5) {
		// The first dorsal folds back and down into its groove.
		float down = UV2.x / U * (1.0 - clamp(first_dorsal, 0.0, 1.0));
		v.y -= down * 0.93;
		v.z += down * 0.45;
	} else if (part > 6.5 && part < 7.5) {
		// The cartoon eye: grown about its middle.
		eye_grow(v);
	} else if (part > 7.5 && part < 8.5) {
		// The gill arches spread a little as the mouth opens.
		v.x *= 1.0 + 0.1 * clamp(gape, 0.0, 1.0);
	}
	float xm = v.z + HALF;
	if (xm < HINGE) {
		// The lower jaw swings down about its hinge (the skin just ahead of the hinge bends), and
		// the snout lifts a little.
		float a = clamp(gape, 0.0, 1.0) * (1.0 - smoothstep(HINGE * (1.0 - SOFT), HINGE, xm));
		a *= jaw > 0.5 ? JAW_DROP : -SNOUT_LIFT;
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = v.yz - vec2(HINGE_Y, HINGE - HALF);
		v.yz = vec2(HINGE_Y, HINGE - HALF) + vec2(d.x * ca + d.y * sa, d.y * ca - d.x * sa);
		n.yz = vec2(n.y * ca + n.z * sa, n.z * ca - n.y * sa);
		xm = v.z + HALF;
	}
	// (the tail, behind its hinge, is one stiff plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	vec3 bent = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	vec3 bent_normal = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(bent, bent_normal);
	VERTEX = bent * U;
	NORMAL = bent_normal;
}

// The edge of the gill cover, as the model has it.
float gill_x(float y) {
	return GILL - 3.0 * (y + 0.015) * (y + 0.015);
}

void fragment() {
	int p = int(part + 0.5);
	int in_mouth = int(inside + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.42;
	float spec = 0.5;
	if (p == 0 && in_mouth == 1 && gape > 0.0 && abs(rest.z + HALF - HINGE) < 0.00002) {
		// (the wall that closed the back of the mouth at the hinge, until it opened onto the throat and its gills
		// on 2026-11-18: still in the model, so that the body's surface stays as it was, and left out here once
		// the mouth opens; shut, it is still the dark seen through the line of the lips)
		discard;
	}
	if (p == 0 && in_mouth == 1) {
		// The inside of the mouth: dark, darker towards the throat.
		c = mouth * mix(1.0, 0.3, smoothstep(0.0, HINGE, rest.z + HALF));
		rough = 0.6;
		spec = 0.25;
	} else if (p == 0 && in_mouth == 2) {
		c = vec3(0.9, 0.88, 0.8);
		rough = 0.3;
	} else if (p == 0) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		// (a fine grain, like small scales)
		float grain = 0.6 * noise2(vec2(xm * 700.0, q * 120.0)) + 0.4 * noise2(vec2(xm * 1500.0 + 7.0, q * 260.0));
		float cloud = noise2(vec2(xm * 9.0, q * 3.0) + 4.0);
		// Where the dark back ends: over the eye on the head, lower on the body, a little waved.
		float edge = mix(0.62, 0.3, smoothstep(0.12, 0.45, xm)) + 0.02 * sin(xm * 9.0) + (cloud - 0.5) * 0.04;
		// The belly white, the flank silver.
		c = mix(belly, silver, smoothstep(-0.75, 0.0, q));
		c *= 0.96 + 0.08 * grain;
		// The belly's marks: faint near-upright pale lines, and rows of pale dots between them.
		float lane = (xm + 0.05 * q) / 0.04;
		float row = floor(lane);
		float across = (fract(lane) - 0.5) * 0.04;
		float down = (q + 1.0) * 0.21;
		float pale;
		if (mod(row, 2.0) < 0.5) {
			pale = (1.0 - smoothstep(0.0018, 0.0045, abs(across))) * (0.6 + 0.4 * noise2(vec2(row, down * 30.0)));
		} else {
			float spot = (fract(down / 0.024 + hash2(vec2(row, 5.0))) - 0.5) * 0.024;
			pale = 1.0 - smoothstep(0.003, 0.006, length(vec2(across, spot)));
		}
		float where = smoothstep(0.42, 0.55, xm) * (1.0 - smoothstep(1.0, 1.18, xm)) * smoothstep(-0.97, -0.82, q) * (1.0 - smoothstep(-0.35, -0.12, q));
		c = mix(c, c * 0.88, where * 0.6);
		c = mix(c, marks, pale * where * marks_show);
		// The back: blue-black, shading through a dark steel blue into the silver.
		float dark = smoothstep(edge - 0.3, edge + 0.08, q);
		vec3 top = mix(back_blue, back, smoothstep(edge - 0.1, edge + 0.3, q));
		top += back_blue * (0.9 * glance * glance + 0.12 * (grain - 0.5));
		c = mix(c, top, dark);
		// The head: the lips, the gill cover's edge and the cheek's crease before it.
		float lip = (1.0 - smoothstep(HINGE - 0.02, HINGE + 0.005, xm)) * (1.0 - smoothstep(0.0, 0.006, abs(y - HINGE_Y * (0.25 + 0.75 * xm / HINGE))));
		c = mix(c, c * 0.45, lip * 0.5);
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.4, 0.6, q));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.0035, abs(behind - 0.002))) * 0.6 + (1.0 - smoothstep(0.0, 0.03, behind)) * step(0.0, behind) * 0.22;
		c = mix(c, c * 0.25, crease * span);
		float cheek = xm - (gill_x(y) - 0.1 - 2.0 * y * y);
		c = mix(c, c * 0.55, (1.0 - smoothstep(0.0, 0.004, abs(cheek))) * 0.35 * smoothstep(-0.8, -0.5, q) * (1.0 - smoothstep(0.1, 0.35, q)));
		// The tail wrist: black along its keels.
		float wrist = smoothstep(1.17, 1.28, xm) * (1.0 - smoothstep(0.3, 0.7, abs(q)));
		c = mix(c, back * 0.6, wrist * 0.92);
		rough = mix(0.3, 0.55, max(dark, wrist));
		spec = mix(0.65, 0.35, max(dark, wrist));
	} else if (p == 1) {
		// The first dorsal: a dusky blue-grey membrane, a little yellow in it, darker spines.
		float spine = pow(abs(cos(3.14159265 * UV.y * 14.0)), 10.0);
		c = mix(fin_dusk, fin_yellow * 0.45, 0.15 + 0.3 * UV.x);
		c = mix(c, back_blue * 0.5 + back, spine * 0.7);
		c = mix(c, back, (1.0 - smoothstep(0.0, 0.3, UV.x)) * 0.7);
	} else if (p == 2) {
		// The second dorsal: reddish brown. The anal fin: a dusky silvery yellow. Fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 70.0 + UV.x * 9.0);
		vec3 own = rest.y > 0.0 ? fin_red : mix(fin_yellow, silver, 0.55);
		c = own * (0.88 + 0.12 * ray);
		c = mix(c, own * 0.5, (1.0 - smoothstep(0.0, 0.16, UV.y)) * 0.5);
		c = mix(c, rest.y > 0.0 ? back + fin_red * 0.3 : silver * 0.8, (1.0 - smoothstep(0.02, 0.25, UV.x)) * 0.75);
		rough = 0.5;
	} else if (p == 3) {
		// A finlet: dusky yellow, edged with black.
		float rim = max(smoothstep(0.55, 0.82, UV.y), smoothstep(0.66, 0.92, UV.x));
		rim *= smoothstep(0.0, 0.25, UV.x);
		c = mix(fin_yellow, fin_edge, rim * 0.95);
		rough = 0.5;
	} else if (p == 4) {
		// The tail: blue-black, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 90.0);
		c = tail_dark * (0.8 + 0.4 * ray);
		c += back_blue * 0.6 * glance * glance;
		rough = 0.45;
	} else if (p == 5) {
		// A pectoral fin: blue-black above, silver-grey below.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		vec3 above = mix(back, fin_dusk, 0.15 + 0.25 * UV.y) + back_blue * 0.5 * glance;
		vec3 below = mix(fin_dusk, silver, 0.5);
		c = mix(below, above, smoothstep(-0.15, 0.15, rest_normal.x * sign(rest.x))) * (0.88 + 0.12 * ray);
		rough = 0.55;
		spec = 0.3;
	} else if (p == 6) {
		// A pelvic fin: pale, dusky towards its tip.
		c = mix(belly * 0.85, fin_dusk * 1.6, smoothstep(0.1, 0.9, UV.x) * 0.7);
		c = mix(c, fin_dusk, 0.25 * (0.5 + 0.5 * cos(UV.y * 40.0)));
	} else if (p == 8) {
		// A gill arch (added 2026-11-18): the bar red, the filaments behind it a deep blood red in a fine comb,
		// darker to their tips, the rakers before it pale; all darker deeper in the throat.
		float deep = smoothstep(HINGE, HINGE + 0.13, rest.z + HALF);
		if (UV.y < 0.2) {
			c = gill_red * 0.85;
		} else if (UV.y < 0.8) {
			float comb = 0.5 + 0.5 * cos(UV.x * 180.0);
			c = mix(gill_red, gill_red * 0.4, comb * 0.6) * mix(1.0, 0.65, smoothstep(0.4, 0.6, UV.y));
		} else {
			c = vec3(0.74, 0.56, 0.52);
		}
		c *= mix(1.0, 0.4, deep);
		rough = 0.45;
		spec = 0.45;
	} else {
		// An eye: a big black pupil, a silver iris, a dark rim.
		float r = UV.x;
		vec3 iris = vec3(0.42, 0.45, 0.46) * (0.85 + 0.15 * noise2(vec2(atan(rest.y - EYE_AT.y, rest.z + HALF - EYE_AT.x) * 14.0, r * 3.0)));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.6, 0.66, r));
		c = mix(c, back * 2.0, smoothstep(0.84, 1.0, r) * 0.9);
		rough = 0.14;
		spec = 0.6;
		if (cartoon_eyes > 0.0) {
			// (the cartoon eye, in its own flat: as the model has the eye, x towards the snout, y up)
			vec2 e = vec2(EYE_MID.z - rest.z, rest.y - EYE_MID.y) / EYE_RADIUS;
			float cartoon = clamp(cartoon_eyes, 0.0, 1.0);
			c = mix(c, cartoon_eye(e, mix(silver, back_blue, 0.25)), cartoon);
			rough = mix(rough, 0.25, cartoon);
			spec = mix(spec, 0.5, cartoon);
		}
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
