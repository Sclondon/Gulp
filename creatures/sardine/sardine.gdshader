shader_type spatial;
// The Pacific sardine (sardine.gd): every marking drawn here (no texture files), and its
// swimming. What each point is comes from the model (tools/build_sardine.py): UV2.y the part
// (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an
// eye, 7 the lower jaw). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x
// how far along, y how high on its side (1 the ridge of the back, 0 the
// keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge (1);
// on an eye: x middle (0) to rim (1).
//
// It swims as sardines and herrings do (between subcarangiform and carangiform): a wave runs
// back along the body, small at the head (which swings a little, as it does in life), growing
// through the whole back half, the forked tail swung behind the wrist. All of it is a function
// of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 0.22;
const float HALF = 0.11;
// Where the tail fin is hinged (metres behind the jaw): behind it the tail is one plate.
const float JOINT = 0.183;
const float MOUTH_TO = 0.018;
const vec2 EYE_AT = vec2(0.021, 0.0042);
// The lower jaw: how far back it runs (metres behind its tip), where its hinge is there (on the
// line of the mouth), and how far it swings down, wide open (radians).
const float JAW_TO = 0.019;
const float HINGE_Y = -0.0049;
const float GAPE_OPEN = 0.8;
// The row of spots: where the first is (metres behind the jaw), how far apart, how many.
const float SPOT_FROM = 0.058;
const float SPOT_STEP = 0.0132;
const float SPOT_COUNT = 8.0;

// How far through a beat of its tail (0..1, it wraps). Set by Sardine.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is; set it from how tightly the fish is turning. (As the
// yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely it beats, for 1 as a sardine cruising (its tail tips swing about 0.02 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.95;
// How far its mouth is open: 0 shut, 1 wide open (as when it bites, or swims open-mouthed to
// strain its food from the water). The lower jaw swings down about its hinge.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The back, and the blue-green it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.02, 0.09, 0.19);
uniform vec3 back_green : source_color = vec3(0.03, 0.36, 0.44);
// The flank and the belly; the faint brassy green under the back's edge.
uniform vec3 silver : source_color = vec3(0.74, 0.78, 0.81);
uniform vec3 belly : source_color = vec3(0.95, 0.95, 0.93);
uniform vec3 sheen : source_color = vec3(0.55, 0.72, 0.55);
// The spots; how strongly the row shows, and the fainter second row above it (0 none).
uniform vec3 spot : source_color = vec3(0.02, 0.04, 0.07);
uniform float spots_show = 0.92;
uniform float second_row = 0.3;
// How strongly the scales' edges show.
uniform float scales_show = 0.6;
// The pale fins; the dusky tail and dorsal fin.
uniform vec3 fin : source_color = vec3(0.7, 0.75, 0.74);
uniform vec3 fin_dusk : source_color = vec3(0.2, 0.28, 0.29);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.1, 0.035, 0.04);

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

// How far to one side the middle line of the body is, `xm` metres behind the jaw: a wave that
// runs back along it, smallest a little behind the head, growing all the way to the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.008 - 0.03 * s + 0.082 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
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
	inside = UV2.x;
	vec3 v = VERTEX;
	float xm = v.z + HALF;
	if (part > 6.5) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = clamp(gape, 0.0, 1.0) * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.008, JAW_TO - 0.0005, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0006) - side_at(zc - 0.0006)) / 0.0012;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.2 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(NORMAL.x * c + NORMAL.z * sn, NORMAL.y, -NORMAL.x * sn + NORMAL.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return 0.0008 - 0.30 * xm;
}

float gill_x(float y) {
	return 0.050 - 26.0 * (y + 0.002) * (y + 0.002);
}

// One spot of a row: `lane` counts along the row (a whole number at each spot's middle).
float spot_of(float xm, float q, float lane, float last, float high, float radius, float seed) {
	float k = clamp(floor(lane + 0.5), 0.0, last);
	float r = radius * (1.0 - 0.04 * k) * (0.85 + 0.3 * hash2(vec2(k, seed)));
	vec2 d = vec2((lane - k) * SPOT_STEP + (hash2(vec2(k, seed + 1.0)) - 0.5) * 0.0016,(q - high - (hash2(vec2(k, seed + 2.0)) - 0.5) * 0.04) * (0.0195 - 0.0125 * smoothstep(0.085, 0.185, xm)));
	return 1.0 - smoothstep(r * 0.62, r, length(d));
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.42;
	float spec = 0.5;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		float cloud = noise2(vec2(xm * 60.0, q * 3.0) + 4.0);
		float behind = xm - gill_x(y);
		// The scales: large, in rows that step half a scale from one to the next; each a little
		// brighter or duller than its neighbours, its rear edge a faint dark arc.
		float arc = acos(clamp(q, -1.0, 1.0)) * 0.017;
		float row = floor(arc / 0.0032);
		float along = xm / 0.0037 + 0.5 * mod(row, 2.0);
		vec2 f = vec2(fract(along), fract(arc / 0.0032));
		float rim = smoothstep(0.76, 0.97, length(vec2(f.x, (f.y - 0.5) * 1.15)));
		float foil = hash2(vec2(floor(along), row));
		float scaled = smoothstep(0.0, 0.004, behind) * (1.0 - smoothstep(0.172, 0.186, xm)) * scales_show;
		// Where the dark back ends: at the top of the eye on the head, lower on the body.
		float edge = mix(0.74, 0.5, smoothstep(0.018, 0.06, xm)) + (cloud - 0.5) * 0.05;
		// The belly white, the flank bright silver, a brassy green under the back's edge.
		c = mix(belly, silver, smoothstep(-0.8, -0.3, q));
		c = mix(c, sheen, 0.3 * smoothstep(edge - 0.34, edge - 0.04, q));
		c *= 1.0 + scaled * (0.08 * (foil - 0.5) - 0.15 * rim);
		// (silver lights up where the light glances off it)
		c += silver * 0.25 * glance * glance;
		float dark = smoothstep(edge - 0.05, edge + 0.06, q);
		vec3 top = mix(back_green, back, smoothstep(edge - 0.02, edge + 0.32, q));
		top *= 1.0 + scaled * (0.12 * (foil - 0.5) - 0.22 * rim);
		top += back_green * 0.7 * glance * glance;
		c = mix(c, top, dark);
		// The spots: a row of eight along the top of the silver, and a fainter row above it.
		float lane = (xm - SPOT_FROM) / SPOT_STEP;
		float spots = spot_of(xm, q, lane, SPOT_COUNT - 1.0, 0.3, 0.0027, 2.0) * spots_show;
		spots = max(spots, spot_of(xm, q, lane - 0.5, SPOT_COUNT - 3.0, edge + 0.04, 0.0015, 9.0) * second_row);
		c = mix(c, spot, spots);
		// The head: no scales; darker over the snout; the line of the mouth, the gill cover's edge,
		// the cheek's crease before it and the fine grooves that fan down and back over the cover.
		float mouth = (1.0 - smoothstep(0.00012, 0.0004, abs(y - mouth_y(xm)))) * smoothstep(0.0, 0.0006, xm) * (1.0 - smoothstep(MOUTH_TO - 0.002, MOUTH_TO, xm));
		c = mix(c, vec3(0.03, 0.04, 0.05), mouth * 0.75);
		float span = smoothstep(-0.97, -0.82, q) * (1.0 - smoothstep(0.45, 0.65, q));
		float crease = (1.0 - smoothstep(0.0, 0.0007, abs(behind - 0.0004))) * 0.6 + (1.0 - smoothstep(0.0, 0.005, behind)) * step(0.0, behind) * 0.2;
		c = mix(c, c * 0.3, crease * span);
		float cheek = xm - (gill_x(y) - 0.0125 - 16.0 * y * y);
		c = mix(c, c * 0.5, (1.0 - smoothstep(0.0, 0.0007, abs(cheek))) * 0.4 * smoothstep(-0.85, -0.6, q) * (1.0 - smoothstep(0.1, 0.35, q)));
		float fan = atan(0.004 - y, xm - 0.034);
		float grooves = 1.0 - smoothstep(0.0, 0.5, abs(sin(fan * 15.0)));
		float cover = smoothstep(0.0, 0.002, cheek) * (1.0 - smoothstep(-0.0025, -0.0005, behind)) * (1.0 - smoothstep(-0.002, 0.001, y)) * smoothstep(-0.92, -0.75, q);
		c = mix(c, c * 0.62, grooves * cover * 0.5);
		rough = mix(0.26, 0.5, dark);
		spec = mix(0.7, 0.4, dark);
		// The inside of the mouth.
		c = mix(c, mouth_inside, inside);
		rough = mix(rough, 0.8, inside);
		spec = mix(spec, 0.2, inside);
	} else if (p == 1) {
		// The dorsal fin: dusky, clearer towards its rear, about seventeen rays.
		float ray = pow(abs(cos(3.14159265 * UV.y * 17.0)), 6.0);
		c = mix(fin_dusk, fin * 0.8, 0.25 + 0.5 * UV.y);
		c = mix(c, fin_dusk * 0.6, ray * 0.45);
		c = mix(c, back_green * 0.5, (1.0 - smoothstep(0.0, 0.3, UV.x)) * 0.6);
		c = mix(c, fin_dusk * 0.5, smoothstep(0.75, 1.0, UV.x) * 0.5);
	} else if (p == 2) {
		// The anal fin: pale, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 110.0);
		c = mix(belly * 0.92, fin, 0.3 + 0.5 * UV.x) * (0.9 + 0.1 * ray);
	} else if (p == 3) {
		// The tail: silver at its root, dusky green-grey beyond, darker along its edges and tips.
		float ray = 0.5 + 0.5 * cos(UV.y * 75.0);
		c = mix(silver * 0.8, fin_dusk * 1.5, smoothstep(0.02, 0.3, UV.x)) * (0.85 + 0.15 * ray);
		float rim = max(smoothstep(0.55, 1.0, UV.x), max(1.0 - smoothstep(0.0, 0.12, UV.y), smoothstep(0.86, 1.0, UV.y)) * smoothstep(0.1, 0.4, UV.x));
		c = mix(c, fin_dusk * 0.45, rim * 0.75);
		c += back_green * 0.3 * glance * glance;
		rough = 0.45;
	} else if (p == 4) {
		// A pectoral fin: pale, a little dusky along its upper edge.
		float ray = 0.5 + 0.5 * cos(UV.y * 55.0);
		c = mix(fin, belly, 0.4 * UV.y) * (0.88 + 0.12 * ray);
		c = mix(c, fin_dusk, (1.0 - smoothstep(0.0, 0.3, UV.y)) * 0.45);
		rough = 0.5;
		spec = 0.35;
	} else if (p == 5) {
		// A pelvic fin: pale.
		c = mix(belly * 0.95, fin, 0.5 * UV.x) * (0.9 + 0.1 * cos(UV.y * 40.0));
	} else {
		// An eye: a big black pupil, a silver iris with a little gold, a dark rim.
		float r = UV.x;
		float round_it = atan(rest.y - EYE_AT.y, rest.z + HALF - EYE_AT.x);
		vec3 iris = mix(vec3(0.72, 0.75, 0.74), vec3(0.8, 0.7, 0.4), smoothstep(0.55, 0.7, r) * (1.0 - smoothstep(0.7, 0.95, r)) * 0.4) * (0.85 + 0.15 * noise2(vec2(round_it * 9.0, r * 3.0)));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.5, 0.56, r));
		c = mix(c, back * 1.5, smoothstep(0.86, 1.0, r) * 0.85);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
