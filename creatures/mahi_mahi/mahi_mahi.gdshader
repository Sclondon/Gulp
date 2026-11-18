shader_type spatial;
// The mahi-mahi (mahi_mahi.gd): every marking drawn here (no texture files), its mouth opened and its
// swimming. What each point is comes from the model (tools/build_mahi_mahi.py): UV2.y the part (0 body,
// 1 the dorsal fin, 2 the anal fin, 3 the lower jaw, 4 the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an
// eye). UV, on the body: x how far along, y how high on its side (1 the ridge of the back, 0 the keel of
// the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge (1) (on the dorsal and
// the anal fin, front to back along the fin); on the lower jaw: x tip (0) to rear end (1), y the middle
// of the mouth's floor (0) round to the chin (1); on an eye: x middle (0) to rim (1). UV2.x, on the body
// and the lower jaw: how much the point is inside the mouth (the roof and the floor).
//
// It swims as jacks and dorados do (carangiform): the head one stiff piece, a wave that runs back along
// the body and grows through its rear half, the tail wrist flexing and the forked tail swung as one plate.
// All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 1.2;
const float HALF = 0.6;
// Ahead of this (metres behind the lip) the head is one stiff piece.
const float HEAD = 0.18;
// Where the tail fin is hinged: behind it the tail is one stiff plate.
const float JOINT = 1.04;
// The lower jaw's hinge (metres behind the lip, metres above the middle line) and how far it swings
// down at `gape` 1 (radians).
const vec2 HINGE = vec2(0.085, -0.024);
const float GAPE_MAX = 0.62;
const float DORSAL_RAYS = 60.0;
const float ANAL_RAYS = 27.0;
const vec2 EYE_AT = vec2(0.068, 0.024);

// How far through a beat of its tail (0..1, it wraps). Set by MahiMahi.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to
// the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The head
// stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How widely it beats, for 1 as a mahi-mahi cruising (its tail tips swing about 0.08 m either way).
uniform float sway = 1.0;
// The mouth: 0 shut, 1 wide open, as when it bites (the lower jaw swings down about its hinge).
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.0;

// The back and the dorsal fin: electric blue-green, bluer where light glances off it.
uniform vec3 back : source_color = vec3(0.0, 0.42, 0.42);
uniform vec3 back_blue : source_color = vec3(0.05, 0.3, 0.85);
// Where the back turns to the flank: green-gold.
uniform vec3 green : source_color = vec3(0.35, 0.62, 0.12);
// The flanks, and the belly.
uniform vec3 gold : source_color = vec3(1.0, 0.78, 0.06);
uniform vec3 belly : source_color = vec3(1.0, 0.93, 0.55);
// The small dark spots scattered over the flanks, and how many show (0 none, 1 all).
uniform vec3 spots : source_color = vec3(0.02, 0.06, 0.16);
uniform float spots_show = 1.0;
// The dorsal fin, the other fins, the inside of the mouth.
uniform vec3 fin_blue : source_color = vec3(0.04, 0.22, 0.62);
uniform vec3 fin_gold : source_color = vec3(0.92, 0.75, 0.2);
uniform vec3 mouth : source_color = vec3(0.12, 0.04, 0.04);

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

// How far to one side the middle line of the body is, `xm` metres behind the lip: a wave that runs
// back along it, small at the head, growing through the rear half.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.4 * (0.01 - 0.035 * s + 0.07 * s * s + 0.06 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 0.2 - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - 0.2);
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
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part > 2.5 && part < 3.5) {
		// The lower jaw swings down about its hinge; its rear end, in the throat, stays.
		float a = clamp(gape, 0.0, 1.0) * GAPE_MAX * smoothstep(HINGE.x + 0.03, HINGE.x - 0.002, v.z + HALF);
		vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	float xm = v.z + HALF;
	// (the head ahead, and the tail behind its hinge, are stiff: they turn as one piece)
	float zc = clamp(xm, HEAD, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.002) - side_at(zc - 0.002)) / 0.004;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.4 * smoothstep(0.86 * JOINT, JOINT, zc));
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

// The edge of the gill cover, as the model has it.
float gill_x(float y) {
	return 0.168 - 2.2 * (y - 0.02) * (y - 0.02);
}

// The dark spots: a few in each cell of a grid laid on the flank, each a small round dot.
float spot_at(vec2 p) {
	vec2 cell = floor(p);
	float best = 0.0;
	for (int i = -1; i <= 1; i++) {
		for (int j = -1; j <= 1; j++) {
			vec2 k = cell + vec2(float(i), float(j));
			float here = hash2(k * 1.7 + 3.1);
			vec2 at = k + vec2(hash2(k + 11.3), hash2(k + 27.9));
			float r = 0.12 + 0.12 * hash2(k + 5.5);
			float dot_ = 1.0 - smoothstep(r * 0.7, r, length(p - at));
			best = max(best, dot_ * step(here, 0.55 * spots_show));
		}
	}
	return best;
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.35;
	float spec = 0.55;
	if (p == 0) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		// (a fine grain, like small scales)
		float grain = 0.6 * noise2(vec2(xm * 900.0, q * 120.0)) + 0.4 * noise2(vec2(xm * 2000.0 + 7.0, q * 260.0));
		float cloud = noise2(vec2(xm * 9.0, q * 3.0) + 4.0);
		// The belly pale yellow, the flanks gold, green-gold higher up, the back electric blue-green.
		c = mix(belly, gold, smoothstep(-0.85, -0.3, q));
		c *= 0.93 + 0.12 * grain;
		// (on the forehead the green-gold climbs higher: the blue only along its crest)
		float line = q - 0.35 + (cloud - 0.5) * 0.25 - 0.25 * smoothstep(0.3, 0.06, xm);
		c = mix(c, green, smoothstep(-0.25, 0.05, line));
		vec3 top = mix(back, back_blue, 0.25 + 0.6 * glance * glance) * (0.85 + 0.25 * grain);
		c = mix(c, top, smoothstep(0.0, 0.3, line));
		// The spots: small, blue-black, scattered over the flanks and the back, fewer low down.
		float s = spot_at(vec2(xm * 70.0, y * 70.0));
		float where = smoothstep(0.17, 0.22, xm) * (1.0 - smoothstep(0.95, 1.0, xm)) * smoothstep(-0.7, -0.2, q);
		c = mix(c, spots, s * where * 0.9);
		// The gill cover's edge.
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.5, 0.7, q));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.002, abs(behind - 0.001))) * 0.5 + (1.0 - smoothstep(0.0, 0.02, behind)) * step(0.0, behind) * 0.15;
		c = mix(c, c * 0.45, crease * span);
		// The lips: a little darker.
		c = mix(c, c * 0.6, (1.0 - smoothstep(0.0, 0.012, xm)));
		rough = mix(0.28, 0.4, smoothstep(0.0, 0.3, line));
		spec = 0.6;
		// The roof of the mouth.
		float in_mouth = smoothstep(0.3, 0.7, inside);
		c = mix(c, mouth, in_mouth);
		rough = mix(rough, 0.6, in_mouth);
		spec = mix(spec, 0.2, in_mouth);
	} else if (p == 1) {
		// The dorsal fin: electric blue, darker along its rays, bluer where light glances.
		float ray = pow(abs(cos(3.14159265 * UV.y * DORSAL_RAYS)), 8.0);
		float cloud = noise2(vec2(rest.z * 30.0, rest.y * 30.0) + 11.0);
		c = mix(fin_blue * 0.8, fin_blue * 1.25, smoothstep(0.0, 0.8, UV.x)) * (0.85 + 0.3 * cloud);
		c = mix(c, fin_blue * 0.4, ray * 0.5);
		c += back_blue * 0.35 * glance * glance;
		rough = 0.45;
		spec = 0.45;
	} else if (p == 2) {
		// The anal fin: pale gold at its root, its edge dusky blue.
		float ray = pow(abs(cos(3.14159265 * UV.y * ANAL_RAYS)), 8.0);
		c = mix(fin_gold, fin_blue * 0.9, smoothstep(0.45, 1.0, UV.x));
		c = mix(c, c * 0.6, ray * 0.5);
		rough = 0.45;
	} else if (p == 3) {
		// The lower jaw: pale gold-white; its top is the floor of the mouth.
		c = mix(belly * 0.9, belly, smoothstep(0.55, 0.95, UV.y));
		c = mix(c, c * 0.6, (1.0 - smoothstep(0.0, 0.15, UV.x)));
		float in_mouth = smoothstep(0.3, 0.7, inside);
		c = mix(c, mouth, in_mouth);
		rough = mix(0.35, 0.6, in_mouth);
		spec = mix(0.5, 0.2, in_mouth);
	} else if (p == 4) {
		// The tail: gold, greener towards its tips, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		c = mix(fin_gold, mix(fin_gold, green, 0.6), smoothstep(0.2, 1.0, UV.x)) * (0.85 + 0.2 * ray);
		rough = 0.42;
	} else if (p == 5) {
		// A pectoral fin: pale gold, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 40.0);
		c = mix(fin_gold * 1.05, fin_gold * 0.8, smoothstep(0.0, 1.0, UV.x)) * (0.88 + 0.2 * ray);
		rough = 0.45;
		spec = 0.4;
	} else if (p == 6) {
		// A pelvic fin: gold, dark towards its tip.
		c = mix(fin_gold, spots * 2.0, smoothstep(0.4, 1.0, UV.x));
		rough = 0.45;
	} else {
		// An eye: a big black pupil, a gold-brown iris, a dark rim.
		float r = UV.x;
		vec3 iris = mix(vec3(0.6, 0.45, 0.15), vec3(0.35, 0.3, 0.12), smoothstep(0.7, 0.95, r)) * (0.85 + 0.15 * noise2(vec2(atan(rest.y - EYE_AT.y, rest.z + HALF - EYE_AT.x) * 14.0, r * 3.0)));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.55, 0.62, r));
		c = mix(c, vec3(0.05, 0.08, 0.04), smoothstep(0.86, 1.0, r) * 0.9);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
