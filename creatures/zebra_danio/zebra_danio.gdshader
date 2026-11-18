shader_type spatial;
// The zebra danio (zebra_danio.gd): every marking drawn here (no texture files), and its swimming. What each
// point is comes from the model (tools/build_zebra_danio.py): UV2.y the part (0 body, 1 the dorsal fin, 2 the
// anal fin, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a barbel). UV2.x: 1
// inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its side (1 the
// ridge of the back, 0 the keel of the belly); on a fin: x root (0) to edge (1), y leading edge (0) to
// trailing edge (1); on an eye: x middle (0) to rim (1); on a barbel: x root to tip.
//
// It swims as small minnows do (subcarangiform): a quick wave down the back half of the body, the head
// swinging a little, the forked tail carried round behind its wrist. All of it is a function of `phase`
// alone, so a picture of it loops exactly. The mouth opens (`gape`): the lower jaw swings down about its
// hinge and the mouth pushes forward a hair. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model (the build script prints them).
const float LENGTH = 0.045;
const float HALF = 0.0225;
const float JOINT = 0.0342;
const float JAW_TO = 0.0023;
const float HINGE_Y = -0.00026;
const float BODY_TO = 0.0362;
const vec2 EYE_AT = vec2(0.0041, 0.0009);
const float GILL_AT = 0.0082;
const float GAPE_OPEN = 1.0;
const float PROTRUDE = 0.00022;
// The five stripes, as the school model has them too: their middles, how high on its side (1 the ridge of
// the back, -1 the keel), and their half width.
const float STRIPE_HALF = 0.075;

uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats, for 1 as a danio cruising.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The olive back; the gold-silver between the stripes and on the head; the steel-blue stripes and the
// brighter blue they turn where light glances off them; the silver-white belly.
uniform vec3 back : source_color = vec3(0.36, 0.33, 0.19);
uniform vec3 gold : source_color = vec3(0.86, 0.8, 0.56);
uniform vec3 stripe : source_color = vec3(0.1, 0.16, 0.4);
uniform vec3 stripe_glint : source_color = vec3(0.32, 0.46, 0.8);
uniform vec3 belly : source_color = vec3(0.92, 0.91, 0.86);
// The fins: clear-pale, and the white edges of the anal fin and the tail.
uniform vec3 fin : source_color = vec3(0.78, 0.76, 0.66);
uniform vec3 fin_white : source_color = vec3(0.95, 0.94, 0.88);
uniform vec3 mouth_inside : source_color = vec3(0.3, 0.08, 0.08);

varying vec3 rest;
varying float part;
varying float inside;

float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.012 - 0.035 * s + 0.085 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
}

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
	inside = UV2.x;
	vec3 v = VERTEX;
	float xm = v.z + HALF;
	float g = clamp(gape, 0.0, 1.0);
	if ((part < 0.5 || part > 6.5) && xm < JAW_TO) {
		v.z -= g * PROTRUDE * (1.0 - smoothstep(0.3 * JAW_TO, JAW_TO, xm));
		xm = v.z + HALF;
	}
	if (part > 6.5 && part < 7.5) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = g * GAPE_OPEN * (1.0 - smoothstep(0.55 * JAW_TO, 0.97 * JAW_TO, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.00015) - side_at(zc - 0.00015)) / 0.0003;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.85 * JOINT, JOINT, zc));
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

// How much of a stripe is at height `q` on the side (the five of them).
float stripes_at(float q, float soft) {
	float s = 0.0;
	s = max(s, 1.0 - smoothstep(STRIPE_HALF - soft, STRIPE_HALF + soft, abs(q - 0.44)));
	s = max(s, 1.0 - smoothstep(STRIPE_HALF - soft, STRIPE_HALF + soft, abs(q - 0.19)));
	s = max(s, 1.0 - smoothstep(STRIPE_HALF - soft, STRIPE_HALF + soft, abs(q + 0.06)));
	s = max(s, 1.0 - smoothstep(STRIPE_HALF - soft, STRIPE_HALF + soft, abs(q + 0.31)));
	s = max(s, 1.0 - smoothstep(STRIPE_HALF - soft, STRIPE_HALF + soft, abs(q + 0.55)));
	return s;
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.35;
	float spec = 0.55;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float q = UV.y * 2.0 - 1.0;
		// Gold-silver all over, an olive back, a silver-white belly.
		c = mix(belly, gold, smoothstep(-0.85, -0.55, q));
		c = mix(c, back, smoothstep(0.58, 0.8, q));
		// The stripes, from behind the gill cover to the tail (they run on into the tail fin); on the head a
		// faint blue wash over the gill cover only.
		float behind = xm - (GILL_AT - 60.0 * (rest.y - 0.0004) * (rest.y - 0.0004));
		float on = smoothstep(0.0005, 0.0016, behind) * stripes_at(q, 0.02);
		vec3 blue = mix(stripe, stripe_glint, 0.55 * glance * glance);
		c = mix(c, blue, on);
		c += gold * 0.25 * glance * glance * (1.0 - on);
		// The gill cover's edge; the line of the mouth darker.
		float cover = (1.0 - smoothstep(0.0, 0.00018, abs(behind))) * smoothstep(-0.9, -0.6, q) * (1.0 - smoothstep(0.45, 0.7, q));
		c = mix(c, c * 0.5, cover * 0.6);
		rough = mix(0.3, 0.45, on);
		c = mix(c, mouth_inside, inside);
		rough = mix(rough, 0.8, inside);
		spec = mix(spec, 0.2, inside);
	} else if (p == 3) {
		// The tail: the stripes run on along its middle rays; its lobes clear and pale, white towards their
		// edges.
		float u = UV.y * 2.0 - 1.0;
		float on = 0.0;
		on = max(on, 1.0 - smoothstep(0.08, 0.13, abs(u)));
		on = max(on, 1.0 - smoothstep(0.07, 0.11, abs(abs(u) - 0.3)));
		on *= 1.0 - smoothstep(0.55, 0.85, UV.x);
		c = mix(fin, fin_white, smoothstep(0.4, 1.0, UV.x));
		c = mix(c, stripe, on);
		c *= 0.9 + 0.1 * cos(UV.y * 90.0);
	} else if (p == 2) {
		// The anal fin: blue and gold bands along its base, a white edge.
		float t = UV.x;
		float on = max(1.0 - smoothstep(0.08, 0.12, abs(t - 0.28)), 1.0 - smoothstep(0.08, 0.12, abs(t - 0.62)));
		c = mix(gold, stripe, on);
		c = mix(c, fin_white, smoothstep(0.8, 0.92, t));
	} else if (p == 1) {
		// The dorsal fin: olive at its root, a blue band, a pale edge.
		float t = UV.x;
		c = mix(back * 1.3, fin, smoothstep(0.1, 0.5, t));
		c = mix(c, stripe, (1.0 - smoothstep(0.08, 0.12, abs(t - 0.42))) * 0.7);
		c = mix(c, fin_white, smoothstep(0.75, 0.95, t));
	} else if (p == 4 || p == 5) {
		c = mix(gold, fin, smoothstep(0.0, 0.4, UV.x));
		c = mix(c, fin_white, 0.4 * UV.x);
		rough = 0.5;
	} else if (p == 8) {
		// A barbel: pale.
		c = mix(gold, fin_white, UV.x);
		rough = 0.6;
	} else {
		// An eye: a black pupil, a silver-gold iris darker over its top.
		float r = UV.x;
		vec3 iris = mix(vec3(0.82, 0.78, 0.6), back, smoothstep(0.3, 0.9, (rest.y - EYE_AT.y) / 0.0013) * 0.7);
		c = mix(vec3(0.004, 0.004, 0.006), iris, smoothstep(0.52, 0.6, r));
		c = mix(c, back * 0.6, smoothstep(0.88, 1.0, r) * 0.7);
		rough = 0.12;
		spec = 0.65;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
