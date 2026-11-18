shader_type spatial;
// The Pacific mackerel (pacific_mackerel.gd): every marking drawn here (no texture files), its
// swimming and its jaw. What each point is comes from the model
// (tools/build_pacific_mackerel.py): UV2.y the part (0 body, 1 the first dorsal fin, 2 the
// second, 3 the anal fin, 4 the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 the inside
// of the mouth, 9 a tooth (none on this one), 10 a finlet, 11 a gill arch); UV2.x how much of the jaw's swing a
// point takes (above 0 the lower jaw, below 0 the upper head, which lifts a little). UV, on the
// body: x how far along (0 the snout's tip, 1 the tips of the tail), y how high on its side (1 the
// ridge of the back, 0 the keel of the belly); in the mouth: x how far inside (0 at the lips); on
// a fin: x root (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0)
// to rim (1).
//
// It swims as mackerels do (carangiform): the front of the body all but still, a wave that grows
// over the back half, the forked tail swung behind its wrist. All of it is a function of `phase`
// alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model (body lengths unless said).
const float LENGTH = 0.40;
const float HALF = 0.20;
// Where the tail fin is hinged (metres behind the snout): behind it the tail is one plate.
const float JOINT = 0.346;
// The jaw's hinge (how far along, how high), the gill cover's edge, the eye.
const float HINGE_S = 0.095;
const float HINGE_Y = -0.02454;
const float GILL_S = 0.245;
const float GILL_K = 10.0;
const float GILL_Y0 = -0.005;
const vec2 EYE_AT = vec2(0.088, 0.019);
// How far the lower jaw swings down wide open, and how far the upper head lifts (radians).
const float GAPE_OPEN = 0.62;
const float UPPER_LIFT = 0.1;

// How far through a beat of its tail (0..1, it wraps). Set by PacificMackerel.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is. (As the yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely it beats, for 1 as a mackerel cruising (its tail tips swing about 0.025 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.05;
// How far its mouth is open: 0 shut, 1 wide open (as when it bites, or swims open-mouthed to
// strain plankton). The lower jaw swings down about its hinge, the upper head lifts a little.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The back, and the blue it turns to where light glances off it; the dark wavy bars on it.
uniform vec3 back : source_color = vec3(0.06, 0.27, 0.25);
uniform vec3 back_blue : source_color = vec3(0.1, 0.38, 0.55);
uniform vec3 bars : source_color = vec3(0.01, 0.04, 0.05);
// The flank and the belly; the brassy sheen along the edge of the back; the dusky spots low on
// the flank.
uniform vec3 silver : source_color = vec3(0.72, 0.76, 0.76);
uniform vec3 belly : source_color = vec3(0.95, 0.95, 0.92);
uniform vec3 sheen : source_color = vec3(0.62, 0.66, 0.45);
uniform vec3 blotch : source_color = vec3(0.32, 0.38, 0.4);
// How strongly the bars and the low dusky spots show (0 none).
uniform float bars_show = 1.0;
uniform float blotches_show = 0.35;
// The fins: dusky, and the paler lower ones; the inside of the mouth.
uniform vec3 fin_dusk : source_color = vec3(0.16, 0.24, 0.24);
uniform vec3 fin : source_color = vec3(0.68, 0.7, 0.66);
uniform vec3 mouth_inside : source_color = vec3(0.16, 0.08, 0.09);
// The gills: the filaments' blood red, and the pale gill rakers.
uniform vec3 gill_red : source_color = vec3(0.62, 0.05, 0.07);
uniform vec3 gill_raker : source_color = vec3(0.72, 0.6, 0.56);
// The cartoon eye: 0 the eye as in life, 1 a bigger cartoon eye (a white, an iris, a pupil, a
// highlight, a dark outline and lids of its own character); where its pupils look (x forward,
// towards the snout, y up, -1..1, in each eye's own plane); a blink (0 open, 1 shut: lids the
// colour of the skin close over the eye, the cartoon one and the one in life alike).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The mackerel's cartoon eye: busy and a little cheeky. A brassy green-gold iris (the sheen of its
// flank), a big round pupil, and an upper lid that sits level a little way down the eye and lifts
// towards the snout, with a touch of lower lid: a knowing, sideways look. (Kept in step with the
// model: the eye's radius, and the point it grows about, a little above its middle: out, up,
// along, in body lengths.)
const float EYE_R = 0.021;
const vec3 EYE_PIVOT = vec3(0.03604, 0.0274, 0.088);
const float EYE_BIG = 1.45;
const vec3 SCLERA = vec3(0.95, 0.95, 0.9);
const vec3 IRIS_IN = vec3(0.86, 0.88, 0.42);
const vec3 IRIS_OUT = vec3(0.3, 0.46, 0.14);
const float IRIS_R = 0.6;
// The pupil's half width and half height, in eye radii.
const vec2 PUPIL = vec2(0.32, 0.32);
// The upper lid's edge (eye radii up from the middle) and its slant (up per radius forward); the
// lower lid's (below -1: none).
const float LID_TOP = 0.5;
const float LID_SLANT = 0.18;
const float LID_LOW = -0.8;
const float LID_LOW_SLANT = 0.0;

varying vec3 rest;
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
// runs back along it, small over the front half, growing large over the back.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.7 * (0.01 - 0.03 * s + 0.035 * s * s + 0.075 * s * s * s * s);
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
	vec3 v = VERTEX;
	// The cartoon eye is bigger: the eye grows about a point near its middle.
	if (abs(part - 7.0) < 0.5 && cartoon_eyes > 0.0) {
		vec3 pivot = vec3(sign(v.x) * EYE_PIVOT.x, EYE_PIVOT.y, EYE_PIVOT.z - 0.5) * LENGTH;
		v = pivot + (v - pivot) * mix(1.0, EYE_BIG, cartoon_eyes);
	}
	// The jaw: the lower jaw swings down about its hinge, the upper head lifts a little about the
	// same hinge; each point takes as much of the swing as the model says (less towards the hinge).
	float w = UV2.x;
	if (abs(w) > 0.0001) {
		float a = clamp(gape, 0.0, 1.0) * (w > 0.0 ? GAPE_OPEN * w : UPPER_LIFT * w);
		float ca = cos(a);
		float sa = sin(a);
		vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5) * LENGTH;
		vec2 d = vec2(v.y, v.z) - hinge;
		v.y = hinge.x + d.x * ca + d.y * sa;
		v.z = hinge.y + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
	}
	float xm = v.z + HALF;
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.001) - side_at(zc - 0.001)) / 0.002;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.86 * JOINT, JOINT, zc));
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

// The cartoon eye at `e`: a point of the eye in its own plane, in eye radii (x forward, towards
// the snout; y up). A white shaded towards its rim, an iris (darker at its edge) and a pupil that
// slide together as far as `eye_look` asks and the white allows, and highlights that stay put,
// up and forward, towards the light.
vec3 cartoon_eye(vec2 e) {
	vec2 d = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.86 - IRIS_R);
	float ir = length(d) / IRIS_R;
	vec3 c = SCLERA * (1.0 - 0.2 * smoothstep(0.45, 0.95, length(e)));
	vec3 iris = mix(IRIS_IN, IRIS_OUT, smoothstep(0.25, 1.0, ir));
	iris = mix(iris, iris * 0.3, smoothstep(0.8, 0.95, ir));
	c = mix(c, iris, 1.0 - smoothstep(0.96, 1.0, ir));
	c = mix(c, vec3(0.01, 0.01, 0.015), 1.0 - smoothstep(0.88, 1.0, length(d / PUPIL)));
	float shine = 1.0 - smoothstep(0.1, 0.135, length(e - vec2(0.22, 0.3)));
	shine = max(shine, 1.0 - smoothstep(0.04, 0.065, length(e - vec2(-0.14, -0.2))));
	return mix(c, vec3(1.0), shine);
}

// The lids over an eye at `e` (as above), the colour of the skin: in the cartoon eye, where its
// character puts them, with a dark line along each edge and a dark outline round the eye; in the
// eye in life, out of sight. `blink` brings them together.
vec3 eye_lids(vec3 c, vec2 e, vec3 lid) {
	float top = mix(1.3, LID_TOP + LID_SLANT * e.x, cartoon_eyes);
	float low = mix(-1.3, LID_LOW + LID_LOW_SLANT * e.x, cartoon_eyes);
	float meet = mix(top, low, 0.7);
	top = mix(top, meet, blink);
	low = mix(low, meet, blink);
	float over = max(smoothstep(-0.02, 0.02, e.y - top), smoothstep(-0.02, 0.02, low - e.y));
	c = mix(c, lid, over);
	float line = max(1.0 - smoothstep(0.035, 0.07, abs(e.y - top)), 1.0 - smoothstep(0.025, 0.05, abs(e.y - low)));
	c = mix(c, vec3(0.02, 0.02, 0.03), line * mix(0.5, 1.0, cartoon_eyes) * step(0.001, max(cartoon_eyes, blink)));
	return mix(c, vec3(0.02, 0.02, 0.03), smoothstep(0.84, 0.92, length(e)) * cartoon_eyes);
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	if (p == 0) {
		float s = rest.z / LENGTH + 0.5;
		float y = rest.y / LENGTH;
		float q = UV.y * 2.0 - 1.0;
		float cloud = noise2(vec2(s * 30.0, q * 4.0) + 3.0);
		// Where the green back ends: high on the head, near the middle line along the body.
		float edge = mix(0.42, 0.12, smoothstep(0.08, 0.3, s)) + (cloud - 0.5) * 0.05;
		c = mix(belly, silver, smoothstep(-0.75, -0.2, q));
		c = mix(c, sheen, 0.35 * smoothstep(edge - 0.3, edge - 0.03, q));
		c += silver * 0.25 * glance * glance;
		// The dusky spots low on the flank (faint, scattered).
		float spots = smoothstep(0.66, 0.76, noise2(vec2(s * 85.0, q * 13.0) + 11.0)) * smoothstep(0.26, 0.36, s) * (1.0 - smoothstep(0.78, 0.85, s));
		spots *= smoothstep(-0.7, -0.45, q) * (1.0 - smoothstep(edge - 0.2, edge - 0.08, q));
		c = mix(c, blotch, spots * blotches_show);
		float dark = smoothstep(edge - 0.04, edge + 0.05, q);
		vec3 top = mix(back, back_blue, 0.35 * glance + 0.15 * cloud);
		// The wavy bars: about thirty, slanting back and down, wavering, from the ridge to the
		// back's edge; none on the head.
		float lane = s / 0.022 + (1.0 - q) * 1.2 + 0.22 * sin(q * 9.0 + floor(s / 0.022) * 1.7);
		float stripe = smoothstep(0.27, 0.35, abs(fract(lane) - 0.5));
		float run = smoothstep(0.225, 0.275, s) * (1.0 - smoothstep(0.84, 0.865, s)) * smoothstep(edge - 0.02, edge + 0.12, q);
		top = mix(top, bars, stripe * run * bars_show * (1.0 - 0.6 * smoothstep(0.9, 1.0, q)));
		c = mix(c, top, dark);
		// The gill cover's edge: a fine dark line, a little shadow behind it.
		float behind = s - (GILL_S - GILL_K * (y - GILL_Y0) * (y - GILL_Y0));
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.55, 0.75, q));
		c = mix(c, c * 0.45, (1.0 - smoothstep(0.0, 0.0025, abs(behind))) * 0.6 * span);
		// The snout: darker over its top.
		c = mix(c, back * 0.8, (1.0 - smoothstep(0.02, 0.07, s)) * smoothstep(0.0, 0.5, q) * 0.6);
		rough = mix(0.28, 0.45, dark);
		spec = mix(0.7, 0.45, dark);
	} else if (p == 1 || p == 2 || p == 10) {
		// The dorsal fins and the finlets: dusky, the spiny first with clear skin between its spines.
		float ray = pow(abs(cos(3.14159265 * UV.y * (p == 1 ? 10.0 : 12.0))), 6.0);
		c = mix(fin_dusk, fin * 0.75, 0.2 + 0.4 * UV.y * UV.x);
		c = mix(c, fin_dusk * 0.5, ray * 0.5);
		rough = 0.5;
	} else if (p == 3) {
		// The anal fin: pale.
		c = mix(belly * 0.9, fin, 0.3 + 0.4 * UV.x) * (0.9 + 0.1 * cos(UV.y * 70.0));
		rough = 0.5;
	} else if (p == 4) {
		// The tail: dusky green-grey, darker at its edge.
		float ray = 0.5 + 0.5 * cos(UV.y * 70.0);
		c = mix(back * 0.9, fin_dusk, smoothstep(0.0, 0.3, UV.x)) * (0.85 + 0.15 * ray);
		c = mix(c, fin_dusk * 0.5, smoothstep(0.6, 1.0, UV.x) * 0.6);
		c += back_blue * 0.25 * glance * glance;
		rough = 0.45;
	} else if (p == 5) {
		// A pectoral fin: dusky above, paler below.
		float ray = 0.5 + 0.5 * cos(UV.y * 50.0);
		c = mix(fin_dusk, fin, 0.25 + 0.6 * UV.y) * (0.88 + 0.12 * ray);
		rough = 0.5;
	} else if (p == 6) {
		// A pelvic fin: pale.
		c = mix(belly * 0.95, fin, 0.5 * UV.x) * (0.9 + 0.1 * cos(UV.y * 40.0));
		rough = 0.5;
	} else if (p == 7) {
		// An eye: a big black pupil, a silver iris with a little gold, a dark rim.
		float r = UV.x;
		float round_it = atan(rest.y / LENGTH - EYE_AT.y, rest.z / LENGTH + 0.5 - EYE_AT.x);
		vec3 iris = mix(vec3(0.74, 0.76, 0.74), vec3(0.78, 0.66, 0.36), smoothstep(0.55, 0.68, r) * (1.0 - smoothstep(0.7, 0.92, r)) * 0.45);
		iris *= 0.85 + 0.15 * noise2(vec2(round_it * 9.0, r * 3.0));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.52, 0.58, r));
		c = mix(c, back * 1.2, smoothstep(0.86, 1.0, r) * 0.8);
		vec2 e = vec2(EYE_AT.x - (rest.z / LENGTH + 0.5), rest.y / LENGTH - EYE_AT.y) / EYE_R;
		c = mix(c, cartoon_eye(e), cartoon_eyes);
		c = eye_lids(c, e, mix(silver, back, 0.5));
		rough = 0.12;
		spec = 0.6;
	} else if (p == 11) {
		// A gill arch (in the roof or the floor at the back of the mouth): pale rakers along its front edge,
		// then the bar and the fringe of blood-red filaments, darker deeper in, towards the hinge.
		float strands = 0.75 + 0.25 * sin(UV.x * 70.0);
		c = mix(gill_raker, gill_red * strands, smoothstep(0.06, 0.24, UV.y));
		c *= mix(1.0, 0.55, smoothstep(HINGE_S - 0.06, HINGE_S, rest.z / LENGTH + 0.5));
		rough = 0.35;
		spec = 0.5;
	} else {
		// The inside of the mouth (and teeth, though this one has none to see): darker deeper in.
		c = mix(mouth_inside * 1.6, mouth_inside * 0.5, smoothstep(0.0, 0.8, UV.x));
		if (p == 9) {
			c = vec3(0.9, 0.88, 0.8);
		}
		rough = 0.75;
		spec = 0.25;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
