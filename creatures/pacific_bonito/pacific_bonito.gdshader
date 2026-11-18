shader_type spatial;
// The Pacific bonito (pacific_bonito.gd): every marking drawn here (no texture files), its
// swimming and its jaw. It began as GameCommon's yellowfin tuna's shader, by way of the bluefin's. What each point is
// comes from the model (tools/build_pacific_bonito.py): UV2.y the part (0 body, 1 first dorsal,
// 2 the second dorsal and the anal fin, 3 a finlet, 4 the tail, 5 a pectoral fin, 6 a pelvic fin,
// 7 an eye). UV, on the body: x how far along, y how high on its side (1 the ridge of the back,
// 0 the keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge
// (1); on an eye: x middle (0) to rim (1). UV2.x, on the first dorsal, how far the point stands
// above the fin's root (metres); on the body, what it is of the mouth (0 skin, 1 the lower jaw's
// skin, 2 the roof of the mouth, 3 its floor, 4 a tooth above, 5 a tooth below: the odd ones
// swing with the jaw).
//
// The model is drawn 1.5 long ("units", the yellowfin's numbers) and scaled to LENGTH: every
// measure below is in units but where it says metres.
//
// It swims as tunas and bonitos do (thunniform): the body all but rigid, a wave that only grows large in the
// last third, the tail wrist flexing and the stiff crescent tail swung as one plate. All of it is
// a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model (its SHAPE line).
const float LENGTH = 0.75;
const float U = LENGTH / 1.5;
const float HALF = 0.75;
// Where the tail fin is hinged (units behind the snout): behind it the tail is one stiff plate.
const float JOINT = 1.335;
// Where the lower jaw hinges (units behind the snout, units above the middle line); how much of
// the jaw's length, ahead of the hinge, bends rather than swings; how far the jaw drops and the
// snout lifts with the mouth wide open (radians).
const float HINGE = 0.165;
const float HINGE_Y = -0.026;
const float SOFT = 0.3;
const float JAW_DROP = 0.6;
const float SNOUT_LIFT = 0.07;
const float GILL = 0.33;
const vec2 EYE_AT = vec2(0.118, 0.03);

// How far through a beat of its tail (0..1, it wraps). Set by PacificBonito.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left).
// The head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// The mouth: 0 shut, 1 wide open, as when it bites.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How widely it beats, for 1 as a bonito cruising (its tail tips swing about 0.06 m either way).
uniform float sway = 1.0;
// How far the first dorsal fin is raised (0 folded down into its groove, 1 up).
uniform float first_dorsal = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;

// The back, and the metallic blue it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.04, 0.1, 0.15);
uniform vec3 back_blue : source_color = vec3(0.1, 0.21, 0.3);
// The slanting stripes on its upper back and sides, and how strongly they show.
uniform vec3 stripe : source_color = vec3(0.006, 0.012, 0.025);
uniform float stripes_show = 0.92;
// How many stripes there are, along its length.
uniform float stripe_count = 9.0;
// The flank and the belly (plain: no marks).
uniform vec3 silver : source_color = vec3(0.6, 0.64, 0.68);
uniform vec3 belly : source_color = vec3(0.9, 0.91, 0.92);
// The fins: dusky grey (the finlets with darker edges); the tail.
uniform vec3 fin_dusk : source_color = vec3(0.17, 0.2, 0.22);
uniform vec3 fin_edge : source_color = vec3(0.03, 0.035, 0.045);
uniform vec3 tail_dark : source_color = vec3(0.05, 0.08, 0.11);
// The inside of the mouth, and the teeth.
uniform vec3 mouth : source_color = vec3(0.2, 0.06, 0.07);
uniform vec3 teeth : source_color = vec3(0.9, 0.88, 0.8);

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
	if (p == 0 && in_mouth == 1) {
		// The inside of the mouth: dark, darker towards the throat.
		c = mouth * mix(1.0, 0.3, smoothstep(0.0, HINGE, rest.z + HALF));
		rough = 0.6;
		spec = 0.25;
	} else if (p == 0 && in_mouth == 2) {
		// A tooth.
		c = teeth;
		rough = 0.3;
	} else if (p == 0) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		// (a fine grain, like small scales)
		float grain = 0.6 * noise2(vec2(xm * 700.0, q * 120.0)) + 0.4 * noise2(vec2(xm * 1500.0 + 7.0, q * 260.0));
		float cloud = noise2(vec2(xm * 9.0, q * 3.0) + 4.0);
		// Where the steel-blue back ends: over the eye on the head, a little above its middle line
		// on the body, a little waved.
		float edge = mix(0.62, 0.36, smoothstep(0.12, 0.4, xm)) + 0.02 * sin(xm * 9.0) + (cloud - 0.5) * 0.04;
		// The belly white, the flank silver.
		c = mix(belly, silver, smoothstep(-0.75, 0.0, q));
		c *= 0.96 + 0.08 * grain;
		// The back: a steel blue-green, shading into the silver.
		float dark = smoothstep(edge - 0.22, edge + 0.08, q);
		vec3 top = mix(back_blue, back, smoothstep(edge - 0.1, edge + 0.3, q));
		top += back_blue * (0.7 * glance * glance + 0.12 * (grain - 0.5));
		c = mix(c, top, dark);
		// The stripes: dark lines slanting down and forward from the ridge of the back to a little
		// above its middle line, from behind the head to the tail wrist (from above they meet at the
		// ridge as chevrons pointing forward).
		float lane = (xm - 0.28 * q) * stripe_count / 0.85 + 0.15 * (noise2(vec2(xm * 6.0, q * 4.0)) - 0.5);
		float stripe_here = 1.0 - smoothstep(0.13, 0.2, abs(fract(lane) - 0.5));
		float stripes_where = smoothstep(0.3, 0.4, xm) * (1.0 - smoothstep(1.12, 1.22, xm)) * smoothstep(0.08, 0.24, q);
		c = mix(c, stripe, stripe_here * stripes_where * stripes_show);
		// The head: the lips, the gill cover's edge and the cheek's crease before it.
		float lip = (1.0 - smoothstep(HINGE - 0.02, HINGE + 0.005, xm)) * (1.0 - smoothstep(0.0, 0.005, abs(y - HINGE_Y * (0.25 + 0.75 * xm / HINGE))));
		c = mix(c, c * 0.45, lip * 0.5);
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.4, 0.6, q));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.003, abs(behind - 0.002))) * 0.6 + (1.0 - smoothstep(0.0, 0.025, behind)) * step(0.0, behind) * 0.22;
		c = mix(c, c * 0.25, crease * span);
		float cheek = xm - (gill_x(y) - 0.09 - 2.0 * y * y);
		c = mix(c, c * 0.55, (1.0 - smoothstep(0.0, 0.004, abs(cheek))) * 0.35 * smoothstep(-0.8, -0.5, q) * (1.0 - smoothstep(0.1, 0.35, q)));
		// The tail wrist: dark along its keels.
		float wrist = smoothstep(1.17, 1.28, xm) * (1.0 - smoothstep(0.3, 0.7, abs(q)));
		c = mix(c, back * 0.7, wrist * 0.85);
		rough = mix(0.3, 0.5, max(dark, wrist));
		spec = mix(0.65, 0.4, max(dark, wrist));
	} else if (p == 1) {
		// The first dorsal: long, low and blackish, its many spines darker still.
		float spine = pow(abs(cos(3.14159265 * UV.y * 19.0)), 10.0);
		c = mix(stripe * 2.0, fin_dusk * 0.7, 0.2 + 0.3 * UV.x);
		c = mix(c, stripe, spine * 0.6);
		c = mix(c, back, (1.0 - smoothstep(0.0, 0.3, UV.x)) * 0.7);
	} else if (p == 2) {
		// The second dorsal and the anal fin: dusky (the anal fin paler). Fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 70.0 + UV.x * 9.0);
		vec3 own = rest.y > 0.0 ? fin_dusk * 0.8 : mix(fin_dusk, silver, 0.45);
		c = own * (0.88 + 0.12 * ray);
		c = mix(c, rest.y > 0.0 ? back : silver * 0.8, (1.0 - smoothstep(0.02, 0.25, UV.x)) * 0.75);
		rough = 0.5;
	} else if (p == 3) {
		// A finlet: dusky, its edge darker.
		float rim = max(smoothstep(0.55, 0.82, UV.y), smoothstep(0.66, 0.92, UV.x));
		rim *= smoothstep(0.0, 0.25, UV.x);
		c = mix(rest.y > 0.0 ? fin_dusk : mix(fin_dusk, silver, 0.35), fin_edge, rim * 0.7);
		rough = 0.5;
	} else if (p == 4) {
		// The tail: dark blue-grey, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 90.0);
		c = tail_dark * (0.8 + 0.4 * ray);
		c += back_blue * 0.5 * glance * glance;
		rough = 0.45;
	} else if (p == 5) {
		// A pectoral fin: dusky above, paler below.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		vec3 above = mix(back, fin_dusk, 0.3 + 0.25 * UV.y) + back_blue * 0.4 * glance;
		vec3 below = mix(fin_dusk, silver, 0.5);
		c = mix(below, above, smoothstep(-0.15, 0.15, rest_normal.x * sign(rest.x))) * (0.88 + 0.12 * ray);
		rough = 0.55;
		spec = 0.3;
	} else if (p == 6) {
		// A pelvic fin: pale, dusky towards its tip.
		c = mix(belly * 0.85, fin_dusk * 1.6, smoothstep(0.1, 0.9, UV.x) * 0.7);
		c = mix(c, fin_dusk, 0.25 * (0.5 + 0.5 * cos(UV.y * 40.0)));
	} else {
		// An eye: a big black pupil, a silver iris, a dark rim.
		float r = UV.x;
		vec3 iris = vec3(0.42, 0.45, 0.46) * (0.85 + 0.15 * noise2(vec2(atan(rest.y - EYE_AT.y, rest.z + HALF - EYE_AT.x) * 14.0, r * 3.0)));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.6, 0.66, r));
		c = mix(c, back * 2.0, smoothstep(0.84, 1.0, r) * 0.9);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
