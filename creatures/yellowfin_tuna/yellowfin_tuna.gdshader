shader_type spatial;
// The yellowfin tuna (yellowfin_tuna.gd): every marking drawn here (no texture files), and its
// swimming. What each point is comes from the model (tools/build_yellowfin_tuna.py): UV2.y the
// part (0 body, 1 first dorsal, 2 the sickle fins, 3 a finlet, 4 the tail, 5 a pectoral fin, 6 a
// pelvic fin, 7 an eye, 8 the lower jaw, 9 a cheek). UV, on the body and the lower jaw: x how far
// along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x
// root (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim
// (1); on a cheek: x how far along. UV2.x, on the first dorsal, how far the point stands above the
// fin's root (metres); on the body and the lower jaw, how far inside the mouth (0 skin and lips, 1
// the middle of its roof or floor); on a cheek, how far down it from the upper lip (0) to the
// lower (1).
//
// It swims as tunas do (thunniform): the body all but rigid, a wave that only grows large in the
// last third, the tail wrist flexing and the stiff crescent tail swung as one plate. All of it is
// a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 1.5;
const float HALF = 0.75;
// Where the tail fin is hinged (metres behind the snout): behind it the tail is one stiff plate.
const float JOINT = 1.335;
const float MOUTH_TO = 0.132;
// Where the lower jaw hinges (metres behind the snout, metres up: the corner of the mouth), as the
// model has it, and how far it swings down for `gape` 1 (radians: its tip drops about 0.07 m).
const vec2 HINGE = vec2(0.132, -0.0393);
const float GAPE_TURN = 0.55;
// Where the lower jaw ends at the throat (metres behind the snout).
const float JAW_BACK = 0.172;

// How far through a beat of its tail (0..1, it wraps). Set by YellowfinTuna.
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of fish swimming tight rounds: "The fish need to bend more"):
// how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The
// head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How widely it beats, for 1 as a tuna cruising (its tail tips swing about 0.12 m either way).
uniform float sway = 1.0;
// How far its mouth is open (the user, 2026-11-17: "the fish should be able to open their
// mouths"): 0 shut, 1 wide open, as when it bites. Set by YellowfinTuna.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How far the first dorsal fin is raised (0 folded down into its groove, 1 up).
uniform float first_dorsal = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;

// The back, and the metallic blue it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.012, 0.022, 0.05);
uniform vec3 back_blue : source_color = vec3(0.03, 0.13, 0.36);
// The thin bright line over the gold band, and the band.
uniform vec3 line_blue : source_color = vec3(0.1, 0.5, 0.9);
uniform vec3 gold : source_color = vec3(0.95, 0.72, 0.1);
// The flank and the belly; the pale dots and broken lines on them.
uniform vec3 silver : source_color = vec3(0.62, 0.66, 0.71);
uniform vec3 belly : source_color = vec3(0.93, 0.94, 0.93);
uniform vec3 marks : source_color = vec3(0.97, 0.98, 1.0);
// The sickle fins and the finlets; the finlets' dark edges; the tail; the first dorsal.
uniform vec3 fin_yellow : source_color = vec3(1.0, 0.8, 0.06);
uniform vec3 fin_edge : source_color = vec3(0.03, 0.03, 0.035);
uniform vec3 tail_dark : source_color = vec3(0.05, 0.065, 0.085);
uniform vec3 fin_dusk : source_color = vec3(0.3, 0.29, 0.14);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.07, 0.03, 0.035);
// How strongly the pale marks on the belly show.
uniform float marks_show = 0.55;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;

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

// How far to one side the middle line of the body is, `xm` metres behind the snout: a wave that
// runs back along it, all but nothing as far as the middle, large only near the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.7 * (0.012 - 0.03 * s + 0.03 * s * s + 0.085 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// How much of the jaw's swing a point `xm` metres behind the snout takes: all of it ahead of the
// corner of the mouth, none at the throat (as the model has it: `jaw_turn`).
float jaw_turn(float xm) {
	return 1.0 - smoothstep(MOUTH_TO - 0.02, JAW_BACK, xm);
}

// The body behind the head laid round an arc (see `curl`).
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

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part > 0.5 && part < 1.5) {
		// The first dorsal folds back and down into its groove.
		float down = UV2.x * (1.0 - clamp(first_dorsal, 0.0, 1.0));
		v.y -= down * 0.93;
		v.z += down * 0.45;
	} else if (part > 7.5) {
		// The lower jaw swings down about its hinge: all of it ahead of the corner of the mouth, its
		// back less and less, as the throat stretches. A cheek (part 9) hangs between the lips: the
		// model has it as it is with the mouth wide open; it folds up along the line of the mouth as
		// the mouth shuts (each point swung as far as it is down the cheek, UV2.x).
		float a = clamp(gape, 0.0, 1.0) * GAPE_TURN * jaw_turn(v.z + HALF);
		if (part > 8.5) {
			a = (clamp(gape, 0.0, 1.0) - 1.0) * GAPE_TURN * jaw_turn(UV.x * LENGTH) * UV2.x;
		}
		vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	}
	float xm = v.z + HALF;
	// (the tail, behind its hinge, is one stiff plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return -0.004 - 0.34 * xm + 0.55 * xm * xm;
}

float gill_x(float y) {
	return 0.36 - 3.0 * (y + 0.015) * (y + 0.015);
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.42;
	float spec = 0.5;
	if (p == 0 || p == 8) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		// (a fine grain, like small scales)
		float grain = 0.6 * noise2(vec2(xm * 700.0, q * 120.0)) + 0.4 * noise2(vec2(xm * 1500.0 + 7.0, q * 260.0));
		float cloud = noise2(vec2(xm * 9.0, q * 3.0) + 4.0);
		// Where the dark back ends: over the eye on the head, lower on the body, a little waved.
		float edge = mix(0.66, 0.4, smoothstep(0.12, 0.42, xm)) + 0.02 * sin(xm * 9.0) + (cloud - 0.5) * 0.03;
		float fade_in = smoothstep(0.2, 0.42, xm);
		float fade_out = 1.0 - 0.75 * smoothstep(1.12, 1.3, xm);
		// The belly white, the flank silver, a wash of gold under the band.
		c = mix(belly, silver, smoothstep(-0.8, -0.2, q));
		c *= 0.96 + 0.08 * grain;
		// The belly's marks: near-upright rows, leaning back a little; every other row a broken
		// line, the rows between them dots.
		float lane = (xm + 0.05 * q) / 0.033;
		float row = floor(lane);
		float across = (fract(lane) - 0.5) * 0.033;
		float down = (q + 1.0) * 0.19;
		float pale;
		if (mod(row, 2.0) < 0.5) {
			float piece = floor(down / 0.034 + hash2(vec2(row, 3.0)));
			pale = (1.0 - smoothstep(0.0018, 0.0042, abs(across))) * step(0.38, hash2(vec2(row, piece)));
			pale *= smoothstep(0.0, 0.25, abs(fract(down / 0.034 + hash2(vec2(row, 3.0))) - 0.5) * -2.0 + 1.0);
		} else {
			float spot = (fract(down / 0.02 + hash2(vec2(row, 5.0))) - 0.5) * 0.02;
			pale = 1.0 - smoothstep(0.0028, 0.0055, length(vec2(across, spot)));
		}
		float where = smoothstep(0.4, 0.52, xm) * (1.0 - smoothstep(1.02, 1.2, xm)) * smoothstep(-0.97, -0.8, q) * (1.0 - smoothstep(edge - 0.52, edge - 0.34, q));
		// (the flank is a shade darker where they are, so that they show)
		c = mix(c, c * 0.84, where * 0.7);
		c = mix(c, marks, pale * where * marks_show);
		c = mix(c, gold, 0.22 * smoothstep(edge - 0.6, edge - 0.3, q) * fade_in * fade_out);
		// The gold band from behind the eye to the tail, the thin blue line over it, the back.
		float band = smoothstep(edge - 0.37, edge - 0.23, q) * fade_in * fade_out;
		c = mix(c, gold * (0.95 + 0.1 * grain), band);
		float line = smoothstep(edge - 0.06, edge - 0.035, q) * smoothstep(0.14, 0.3, xm) * fade_out;
		c = mix(c, line_blue, line * 0.9);
		float dark = smoothstep(edge - 0.02, edge + 0.035, q);
		vec3 top = mix(back_blue, back, smoothstep(edge, edge + 0.4, q));
		top += back_blue * (0.9 * glance * glance + 0.1 * (grain - 0.5));
		c = mix(c, top, dark);
		// The head: the line of the mouth, the gill cover's edge and the cheek's crease before it.
		float mouth = (1.0 - smoothstep(0.0012, 0.0032, abs(y - mouth_y(xm)))) * smoothstep(0.0, 0.002, xm) * (1.0 - smoothstep(MOUTH_TO - 0.01, MOUTH_TO, xm));
		c = mix(c, vec3(0.02, 0.02, 0.03), mouth * 0.9);
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.4, 0.6, q));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.0035, abs(behind - 0.002))) * 0.6 + (1.0 - smoothstep(0.0, 0.03, behind)) * step(0.0, behind) * 0.22;
		c = mix(c, c * 0.25, crease * span);
		float cheek = xm - (gill_x(y) - 0.095 - 2.0 * y * y);
		c = mix(c, c * 0.55, (1.0 - smoothstep(0.0, 0.004, abs(cheek))) * 0.35 * smoothstep(-0.8, -0.5, q) * (1.0 - smoothstep(0.1, 0.35, q)));
		// (a gleam of gold on the gill cover)
		c = mix(c, gold, 0.14 * smoothstep(0.2, 0.3, xm) * (1.0 - smoothstep(0.0, 0.01, behind)) * (1.0 - dark) * (1.0 - smoothstep(-0.2, -0.7, q)));
		// The tail wrist: dark along its keels.
		float wrist = smoothstep(1.2, 1.29, xm) * (1.0 - smoothstep(0.25, 0.6, abs(q)));
		c = mix(c, back, wrist * 0.85);
		rough = mix(0.3, 0.55, max(dark, wrist));
		spec = mix(0.65, 0.35, max(dark, wrist));
		// The inside of the mouth (its roof and floor, which the model marks: seen when it gapes).
		float lined = smoothstep(0.0, 0.12, UV2.x);
		c = mix(c, mouth_inside, lined);
		rough = mix(rough, 0.7, lined);
		spec = mix(spec, 0.3, lined);
	} else if (p == 1) {
		// The first dorsal: a dusky yellow membrane, thirteen darker spines.
		float spine = pow(abs(cos(3.14159265 * UV.y * 13.0)), 10.0);
		c = mix(fin_dusk, fin_yellow * 0.62, 0.25 + 0.5 * UV.x);
		c = mix(c, back_blue * 0.6 + fin_dusk * 0.3, spine * 0.7);
		c = mix(c, back, (1.0 - smoothstep(0.0, 0.3, UV.x)) * 0.6);
	} else if (p == 2) {
		// The sickle fins: yellow, a little deeper at the leading edge and the root, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 70.0 + UV.x * 9.0);
		c = fin_yellow * (0.9 + 0.1 * ray);
		c = mix(c, fin_yellow * vec3(0.7, 0.55, 0.3), (1.0 - smoothstep(0.0, 0.16, UV.y)) * 0.55);
		c = mix(c, fin_dusk, (1.0 - smoothstep(0.02, 0.2, UV.x)) * 0.75);
		rough = 0.5;
	} else if (p == 3) {
		// A finlet: bright yellow, edged with black.
		float rim = max(smoothstep(0.62, 0.86, UV.y), smoothstep(0.72, 0.95, UV.x));
		rim *= smoothstep(0.0, 0.25, UV.x);
		c = mix(fin_yellow, fin_edge, rim * 0.95);
		rough = 0.5;
	} else if (p == 4) {
		// The tail: dark, fine rays, a faint dusky yellow down the middle of each lobe.
		float ray = 0.5 + 0.5 * cos(UV.y * 90.0);
		c = tail_dark * (0.8 + 0.4 * ray);
		c = mix(c, fin_dusk, 0.3 * (1.0 - abs(UV.y * 2.0 - 1.0)) * smoothstep(0.05, 0.4, UV.x));
		c += back_blue * 0.5 * glance * glance;
		rough = 0.45;
	} else if (p == 5) {
		// A pectoral fin: dark above, dusky yellow and silver below.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		vec3 above = mix(back, fin_dusk, 0.25 + 0.3 * UV.y) + back_blue * 0.5 * glance;
		vec3 below = mix(fin_dusk * 1.5, silver, 0.45);
		c = mix(below, above, smoothstep(-0.15, 0.15, rest_normal.x * sign(rest.x))) * (0.88 + 0.12 * ray);
		rough = 0.55;
		spec = 0.3;
	} else if (p == 6) {
		// A pelvic fin: pale, dusky yellow towards its tip.
		c = mix(belly * 0.9, fin_yellow * 0.75, smoothstep(0.1, 0.9, UV.x) * 0.6);
		c = mix(c, fin_dusk, 0.25 * (0.5 + 0.5 * cos(UV.y * 40.0)));
	} else if (p == 9) {
		// A cheek: the inside of the mouth.
		c = mouth_inside * (0.8 + 0.4 * UV2.x);
		rough = 0.7;
		spec = 0.3;
	} else {
		// An eye: a big black pupil, a silver and gold iris, a dark rim.
		float r = UV.x;
		vec3 iris = mix(vec3(0.42, 0.45, 0.44), gold * vec3(0.8, 0.85, 0.9), smoothstep(0.7, 0.95, r) * 0.35) * (0.85 + 0.15 * noise2(vec2(atan(rest.y - 0.024, rest.z + 0.605) * 14.0, r * 3.0)));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.62, 0.68, r));
		c = mix(c, back * 2.0, smoothstep(0.84, 1.0, r) * 0.9);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
