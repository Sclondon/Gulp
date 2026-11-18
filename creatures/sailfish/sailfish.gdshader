shader_type spatial;
// The sailfish (sailfish.gd): every marking drawn here (no texture files), its sail folded and
// rippled, and its swimming. What each point is comes from the model (tools/build_sailfish.py):
// UV2.y the part (0 body, 1 the sail, 2 the small middle fins, 3 the lower jaw, 4 the tail, 5 a
// pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body: x how far along, y how high on its
// side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y
// leading edge (0) to trailing edge (1); on the lower jaw: x tip (0) to hinge (1), y the line of
// the mouth (0) to the chin (1); on an eye: x middle (0) to rim (1). UV2.x, on the sail, how far
// the point stands above the fin's root (metres).
//
// It swims as tunas and billfish do (thunniform): the head and bill one stiff piece, the body all
// but rigid, a wave that only grows large in the last third, the tail wrist flexing and the stiff
// crescent tail swung as one plate. All of it is a function of `phase` alone, so a picture of it
// loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 2.6;
const float HALF = 1.3;
// Ahead of this (metres behind the bill's tip) the head and bill are one stiff piece.
const float HEAD = 0.82;
// Where the tail fin is hinged: behind it the tail is one stiff plate.
const float JOINT = 2.29;
const float SAIL_RAYS = 46.0;
const float SAIL_HIGH = 0.54;
// The lower jaw: where its tip and its sunk end are, its hinge (metres behind the bill's tip, metres
// up), and how far it swings down when the mouth is wide open (radians).
const float JAW_FROM = 0.30;
const float JAW_TO = 0.64;
const vec2 JAW_HINGE = vec2(0.63, -0.06);
const float JAW_SWING = 0.36;

// How far through a beat of its tail (0..1, it wraps). Set by Sailfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left).
// The bill and head stay as they are; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How widely it beats, for 1 as a sailfish cruising (its tail tips swing about 0.2 m either way).
uniform float sway = 1.0;
// How far the sail is raised (0 folded down into its groove along the back, 1 up).
uniform float sail = 1.0;
// How far the top of the raised sail ripples to each side (metres).
uniform float ripple = 0.022;
// How far its mouth is open (0 shut, 1 wide open, as when it bites): the lower jaw swings down
// about its hinge under the eye.
uniform float gape = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;

// The back, and the cobalt it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.012, 0.022, 0.075);
uniform vec3 back_blue : source_color = vec3(0.03, 0.11, 0.42);
// The flank (brownish blue), the lower flank and the belly.
uniform vec3 flank : source_color = vec3(0.2, 0.22, 0.31);
uniform vec3 silver : source_color = vec3(0.62, 0.66, 0.72);
uniform vec3 belly : source_color = vec3(0.93, 0.94, 0.94);
// The upright rows of pale dots down the flanks, and how strongly they show.
uniform vec3 bars : source_color = vec3(0.5, 0.7, 0.95);
uniform float bars_show = 0.8;
// The sail: its membrane, its rays and root, its spots.
uniform vec3 sail_blue : source_color = vec3(0.07, 0.17, 0.5);
uniform vec3 sail_dark : source_color = vec3(0.02, 0.04, 0.14);
uniform vec3 sail_spots : source_color = vec3(0.006, 0.008, 0.025);
// The other fins and the bill.
uniform vec3 fin_dark : source_color = vec3(0.02, 0.03, 0.075);
uniform vec3 bill : source_color = vec3(0.03, 0.04, 0.08);
// The inside of the mouth (seen only when it is open).
uniform vec3 mouth : source_color = vec3(0.05, 0.016, 0.022);

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

// How far to one side the middle line of the body is, `xm` metres behind the bill's tip: a wave
// that runs back along it, all but nothing as far as the middle, large only near the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.42 * (0.006 - 0.02 * s + 0.02 * s * s + 0.09 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 0.85 - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - 0.85);
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
	if (part > 0.5 && part < 1.5) {
		// The sail folds back and down into its groove; raised, a wave runs back along its top.
		float up = clamp(sail, 0.0, 1.0);
		float down = UV2.x * (1.0 - up);
		v.y -= down * 0.97;
		v.z += down * 0.3;
		float high = UV2.x / SAIL_HIGH;
		v.x += up * ripple * high * high * sin(6.2831853 * (phase - rest.z * 1.4));
	}
	vec3 nn = NORMAL;
	if (part > 2.5 && part < 3.5) {
		// The lower jaw swings down about its hinge.
		float a = clamp(gape, 0.0, 1.0) * JAW_SWING;
		float ca = cos(a);
		float sa = sin(a);
		float dy = v.y - JAW_HINGE.y;
		float dz = v.z - (JAW_HINGE.x - HALF);
		v.y = JAW_HINGE.y + dy * ca + dz * sa;
		v.z = JAW_HINGE.x - HALF + dz * ca - dy * sa;
		nn = vec3(nn.x, nn.y * ca + nn.z * sa, nn.z * ca - nn.y * sa);
	}
	float xm = v.z + HALF;
	// (the head and bill ahead, and the tail behind its hinge, are stiff: they turn as one piece)
	float zc = clamp(xm, HEAD, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(nn.x * c + nn.z * sn, nn.y, -nn.x * sn + nn.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The edge of the gill cover, as the model has it.
float gill_x(float y) {
	return 0.83 - 2.5 * (y + 0.02) * (y + 0.02);
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.42;
	float spec = 0.5;
	if (p == 0) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		// (a fine grain, like small scales)
		float grain = 0.6 * noise2(vec2(xm * 500.0, q * 90.0)) + 0.4 * noise2(vec2(xm * 1100.0 + 7.0, q * 200.0));
		float cloud = noise2(vec2(xm * 6.0, q * 3.0) + 4.0);
		// The belly white, the lower flank silver, the flank brownish blue, the back dark cobalt.
		c = mix(belly, silver, smoothstep(-0.95, -0.5, q));
		c = mix(c, flank, smoothstep(-0.42, 0.18, q + (cloud - 0.5) * 0.12));
		c *= 0.95 + 0.1 * grain;
		float dark = smoothstep(0.12, 0.55, q + (cloud - 0.5) * 0.1);
		vec3 top = mix(back_blue, back, smoothstep(0.45, 0.92, q));
		top += back_blue * (0.9 * glance * glance + 0.12 * (grain - 0.5));
		c = mix(c, top, dark);
		// The bars: upright rows of pale blue-grey dots down the flanks, from behind the gill cover to
		// the tail wrist.
		float lane = (xm - 0.9) / 0.068;
		float row = floor(lane);
		float across = (fract(lane) - 0.5) * 0.068;
		float down = y / 0.024 + hash2(vec2(row, 5.0));
		float spot = (fract(down) - 0.5) * 0.024;
		float which = hash2(vec2(row, floor(down)));
		// (no two dots quite alike, nor quite in line)
		float size = 0.0052 + 0.0034 * which;
		float pale = 1.0 - smoothstep(size * 0.6, size, length(vec2(across + (fract(which * 7.3) - 0.5) * 0.009, spot * 0.8)));
		float where = smoothstep(0.9, 0.96, xm) * (1.0 - smoothstep(2.05, 2.14, xm)) * (1.0 - smoothstep(0.62, 0.82, q)) * smoothstep(-0.72, -0.4, q);
		c = mix(c, bars, pale * where * bars_show);
		// The bill and the top of the head: blue-black, paler underneath.
		float beak = (1.0 - smoothstep(0.42, 0.66, xm)) * smoothstep(-0.75, -0.1, q);
		c = mix(c, bill * (0.9 + 0.2 * grain), beak);
		// The roof of the mouth: the underside of the bill and head where the shut lower jaw lies
		// against it (hidden inside the jaw until the mouth opens).
		float open = smoothstep(0.0, 0.06, gape);
		if (open > 0.0 && q < -0.3 && xm > JAW_FROM - 0.01 && xm < JAW_TO) {
			float js = max(0.0, (xm - JAW_FROM) / (JAW_TO - JAW_FROM));
			float jaw_up = -abs(y / q) + 0.004;
			float chin = min(-(0.0165 + 0.056 * pow(js, 1.1)), jaw_up - 0.002);
			float across_jaw = max(pow(1.0 - q * q, 0.46) / 0.92, abs(rest.x) / (0.006 + 0.085 * max(xm - JAW_FROM, 0.0)));
			float up_jaw = (y - 0.5 * (jaw_up + chin)) / (0.5 * (jaw_up - chin));
			float inside = 1.0 - smoothstep(0.75, 1.0, across_jaw * across_jaw + up_jaw * up_jaw);
			// (not at the sunk end of the jaw, where its skin and the head's all but meet)
			c = mix(c, mouth, inside * open * (1.0 - smoothstep(0.55, 0.6, xm)));
		}
		// The gill cover's edge.
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.4, 0.6, q));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.004, abs(behind - 0.002))) * 0.6 + (1.0 - smoothstep(0.0, 0.035, behind)) * step(0.0, behind) * 0.22;
		c = mix(c, c * 0.3, crease * span);
		// The tail wrist: dark along its keels.
		float wrist = smoothstep(2.12, 2.22, xm) * (1.0 - smoothstep(0.35, 0.75, abs(q)));
		c = mix(c, back, wrist * 0.85);
		rough = mix(0.3, 0.5, max(dark, wrist));
		spec = mix(0.65, 0.4, max(dark, wrist));
	} else if (p == 1) {
		// The sail: slate and cobalt blue, darker at its root and along its rays, scattered with
		// small dark round spots.
		float ray = pow(abs(cos(3.14159265 * UV.y * SAIL_RAYS)), 14.0);
		float cloud = noise2(vec2(rest.z * 7.0, rest.y * 7.0) + 11.0);
		c = mix(sail_dark, sail_blue, smoothstep(0.0, 0.45, UV.x)) * (0.75 + 0.5 * cloud);
		c = mix(c, sail_dark, ray * 0.6);
		vec2 g = vec2(rest.z, rest.y) / 0.062;
		vec2 cell = floor(g);
		vec2 f = fract(g) - 0.5;
		vec2 at = (vec2(hash2(cell), hash2(cell + 17.0)) - 0.5) * 0.5;
		float r = 0.12 + 0.11 * hash2(cell + 5.0);
		float dot_here = (1.0 - smoothstep(r * 0.7, r, length(f - at))) * step(0.42, hash2(cell + 9.0));
		dot_here *= smoothstep(0.06, 0.2, UV.x) * (1.0 - smoothstep(0.82, 0.96, UV.x));
		c = mix(c, sail_spots, dot_here * 0.92);
		c += sail_blue * 0.5 * glance * glance;
		rough = 0.5;
		spec = 0.4;
	} else if (p == 2) {
		// The second dorsal and the anal fins: blue-black, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 50.0);
		c = fin_dark * (0.8 + 0.4 * ray) + back_blue * 0.4 * glance * glance;
		rough = 0.5;
	} else if (p == 3) {
		// The lower jaw: pale, dark along the line of the mouth and towards its tip.
		c = mix(silver * 0.8, belly * 0.95, smoothstep(0.3, 0.9, UV.y));
		c = mix(c, bill, (1.0 - smoothstep(0.2, 0.75, UV.x)) * 0.55);
		c = mix(c, vec3(0.02, 0.02, 0.03), (1.0 - smoothstep(0.14, 0.3, UV.y)) * 0.85);
		// (its top is the floor of the mouth, seen when it is open)
		c = mix(c, mouth, (1.0 - smoothstep(0.3, 0.42, UV.y)) * smoothstep(0.0, 0.06, gape));
	} else if (p == 4) {
		// The tail: blue-black, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 90.0);
		c = fin_dark * (0.8 + 0.4 * ray);
		c += back_blue * 0.5 * glance * glance;
		rough = 0.45;
	} else if (p == 5) {
		// A pectoral fin: blue-black, a little paler towards its root.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		c = mix(fin_dark * 2.2 + silver * 0.06, fin_dark, smoothstep(0.0, 0.5, UV.x)) * (0.85 + 0.3 * ray);
		c += back_blue * 0.4 * glance * glance;
		rough = 0.5;
		spec = 0.35;
	} else if (p == 6) {
		// A pelvic fin: a blue-black rod.
		c = fin_dark * 1.2 + back_blue * 0.3 * glance * glance;
		rough = 0.5;
	} else {
		// An eye: a big black pupil, a silver-blue iris, a dark rim.
		float r = UV.x;
		vec3 iris = mix(vec3(0.4, 0.45, 0.5), vec3(0.55, 0.6, 0.55), smoothstep(0.7, 0.95, r) * 0.4) * (0.85 + 0.15 * noise2(vec2(atan(rest.y - 0.022, rest.z + 0.665) * 14.0, r * 3.0)));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.58, 0.64, r));
		c = mix(c, back * 2.0, smoothstep(0.84, 1.0, r) * 0.9);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
