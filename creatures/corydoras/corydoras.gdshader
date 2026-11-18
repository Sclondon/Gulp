shader_type spatial;
// The cory catfish (corydoras.gd): every marking drawn here (no texture files), for the bronze cory and the
// panda (corydoras.gd sets the colours of each), and its swimming. What each point is comes from the model
// (tools/build_corydoras.py): UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
// pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a barbel, 9 the adipose fin). UV2.x: 1 inside
// the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its side (1 the ridge of
// the back, 0 the middle of the belly); on a fin: x root (0) to edge (1), y leading edge (0) to trailing edge
// (1); on an eye: x middle (0) to rim (1); on a barbel: x root to tip.
//
// It swims by a wave down the back half of its body (subcarangiform), its stiff armoured front nearly still,
// the forked tail carried round behind its wrist. All of it is a function of `phase` alone, so a picture of it
// loops exactly. The mouth (under the snout) opens: `gape`. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model (the build script prints them).
const float LENGTH = 0.06;
const float HALF = 0.03;
const float JOINT = 0.0462;
const float JAW_TO = 0.0036;
const float HINGE_Y = -0.0048;
const vec2 EYE_AT = vec2(0.0064, 0.0036);
const float GILL_AT = 0.0108;
const float GAPE_OPEN = 0.9;
const float PROTRUDE = 0.0003;
// The plates (as the build script has them): where they begin and end, how long each is.
const float PLATE_FROM = 0.0115;
const float PLATE_TO = 0.0465;
const float PLATE_LONG = 0.00155;
// Where the dorsal fin stands on the back (for the panda's dark saddle under it).
const vec2 DORSAL_AT = vec2(0.0145, 0.023);

uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats, for 1 as a cory swimming along.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The colours (corydoras.gd's KINDS sets them for each kind). The body; its back and head; the belly; the
// sheen where light glances off the plates (green on a bronze cory); the dark marks (the panda's eye mask,
// saddle and tail spot: 0 none); the plates' edges; the fins.
uniform vec3 body : source_color = vec3(0.58, 0.43, 0.22);
uniform vec3 back : source_color = vec3(0.4, 0.31, 0.15);
uniform vec3 belly : source_color = vec3(0.88, 0.8, 0.66);
uniform vec3 sheen : source_color = vec3(0.2, 0.5, 0.36);
uniform float sheen_amount = 0.9;
uniform vec3 mark : source_color = vec3(0.03, 0.03, 0.035);
uniform float mask_amount = 0.0;
uniform float saddle_amount = 0.0;
uniform float tail_spot_amount = 0.0;
uniform float plates_show = 0.6;
uniform vec3 fin : source_color = vec3(0.68, 0.64, 0.54);
uniform vec3 fin_edge : source_color = vec3(0.86, 0.84, 0.78);
uniform vec3 barbel_colour : source_color = vec3(0.8, 0.72, 0.58);
uniform vec3 iris : source_color = vec3(0.7, 0.55, 0.25);
uniform vec3 mouth_inside : source_color = vec3(0.35, 0.12, 0.12);

varying vec3 rest;
varying float part;
varying float inside;

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.006 - 0.03 * s + 0.09 * s * s);
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
	// The mouth pushes forward and down a little as it opens (the barbels go with the upper lip).
	if ((part < 0.5 || (part > 6.5 && part < 8.5)) && xm < JAW_TO + 0.003 * step(7.5, part)) {
		float w = 1.0 - smoothstep(0.3 * JAW_TO, JAW_TO, xm);
		w = part > 7.5 ? 1.0 - smoothstep(0.5 * JAW_TO, 1.4 * JAW_TO, xm) : w;
		v.z -= g * PROTRUDE * w;
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
	float slope = (side_at(zc + 0.0002) - side_at(zc - 0.0002)) / 0.0004;
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

// The panda's dark marks at a place on the body (0 none, 1 dark).
float marks_at(float xm, float y, float q) {
	// the mask: a band down over the eye, from the top of the head to the cheek
	float across = xm - (EYE_AT.x + 0.32 * (y - EYE_AT.y));
	float m = (1.0 - smoothstep(0.0022, 0.0028, abs(across))) * smoothstep(-0.0045, -0.0028, y) * mask_amount;
	// the saddle under the dorsal fin
	float saddle = smoothstep(DORSAL_AT.x - 0.0008, DORSAL_AT.x + 0.0008, xm) * (1.0 - smoothstep(DORSAL_AT.y - 0.002, DORSAL_AT.y, xm));
	m = max(m, saddle * smoothstep(0.5, 0.65, q) * saddle_amount);
	// the round spot on the root of the tail
	float spot = length(vec2((xm - 0.0425) / 1.0, (q - 0.25) * 0.004));
	m = max(m, (1.0 - smoothstep(0.0028, 0.0034, spot)) * tail_spot_amount);
	return m;
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		// The body, darker on the back and the head, the flat belly pale.
		c = mix(belly, body, smoothstep(-0.92, -0.7, q));
		c = mix(c, back, smoothstep(0.35, 0.9, q) * 0.8);
		c = mix(c, back, (1.0 - smoothstep(GILL_AT - 0.002, GILL_AT + 0.001, xm)) * smoothstep(-0.4, 0.2, q) * 0.5);
		// The plates' edges: each plate's rear edge a fine dark line, the two rows half a plate apart and
		// meeting along the middle line, a little brighter just in front of each edge.
		float f = (xm - PLATE_FROM) / PLATE_LONG + (q >= 0.0 ? 0.0 : 0.5) + 0.35 * abs(q);
		float in_plates = smoothstep(PLATE_FROM, PLATE_FROM + 0.001, xm) * (1.0 - smoothstep(PLATE_TO - 0.001, PLATE_TO, xm)) * (1.0 - smoothstep(0.8, 0.9, abs(q)));
		float fr = fract(f);
		float edge = (1.0 - smoothstep(0.0, 0.1, fr)) + smoothstep(0.96, 1.0, fr);
		float seam = 1.0 - smoothstep(0.0, 0.035, abs(q));
		float shade = hash3(vec3(floor(f), sign(q), 3.0));
		c *= 1.0 + in_plates * plates_show * (0.12 * smoothstep(0.5, 0.95, fr) + 0.08 * (shade - 0.5) - 0.45 * max(edge, seam));
		// The sheen: green-gold where light glances off the plates.
		c = mix(c, sheen, sheen_amount * glance * glance * smoothstep(-0.7, -0.3, q) * 0.8);
		// The gill cover's edge.
		float behind = xm - (GILL_AT - 40.0 * (y + 0.001) * (y + 0.001));
		c = mix(c, c * 0.55, (1.0 - smoothstep(0.0, 0.00025, abs(behind))) * smoothstep(-0.85, -0.5, q) * (1.0 - smoothstep(0.6, 0.8, q)));
		c = mix(c, mark, marks_at(xm, y, q));
		c = mix(c, mouth_inside, inside);
		rough = mix(0.38, 0.85, inside);
		spec = mix(0.55, 0.2, inside);
	} else if (p == 8) {
		c = mix(barbel_colour, fin_edge, UV.x * 0.5);
		rough = 0.6;
	} else if (p == 6) {
		// An eye: a black pupil, a gold ring, on the panda inside its dark mask.
		float r = UV.x;
		c = mix(vec3(0.004, 0.004, 0.006), iris, smoothstep(0.5, 0.58, r) * (1.0 - smoothstep(0.75, 0.9, r)));
		c = mix(c, mix(back, mark, mask_amount), smoothstep(0.86, 1.0, r));
		rough = 0.12;
		spec = 0.65;
	} else {
		// The fins: pale and clear-looking, with fine rays; the dorsal's and pectorals' spines (their leading
		// edges) darker; on the panda a dark patch on the dorsal fin.
		float rays = p == 3 ? 22.0 : 9.0;
		c = mix(fin, fin_edge, smoothstep(0.1, 0.9, UV.x));
		c *= 0.88 + 0.12 * pow(abs(cos(3.14159265 * UV.y * rays)), 4.0);
		if (p == 1 || p == 4 || p == 9) {
			c = mix(c, back * 0.8, (1.0 - smoothstep(0.0, 0.14, UV.y)) * 0.75);
		}
		if (p == 1) {
			c = mix(c, mark, saddle_amount * (1.0 - smoothstep(0.55, 0.7, UV.x)) * smoothstep(0.0, 0.05, UV.y));
		}
		if (p == 3) {
			// faint rows of dots across the tail (on the bronze; the panda's is clear)
			float dots = (1.0 - smoothstep(0.3, 0.45, fract(UV.x * 6.0))) * (1.0 - smoothstep(0.3, 0.45, fract(UV.y * 10.0)));
			c = mix(c, back, dots * (1.0 - tail_spot_amount) * 0.35 * smoothstep(0.15, 0.3, UV.x));
		}
		rough = 0.5;
		spec = 0.35;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
