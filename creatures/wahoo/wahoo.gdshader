shader_type spatial;
// The wahoo (wahoo.gd): every marking drawn here (no texture files), its swimming and its jaw.
// What each point is comes from the model (tools/build_wahoo.py): UV2.y the part (0 body, 1 the
// first dorsal fin, 2 the second, 3 the anal fin, 4 the tail, 5 a pectoral fin, 6 a pelvic fin, 7
// an eye, 8 the inside of the mouth, 9 a tooth, 10 a finlet, 11 a gill arch); UV2.x how much of the jaw's swing a
// point takes (above 0 the lower jaw, below 0 the upper head, which lifts a little). UV, on the
// body: x how far along (0 the jaw's tip, 1 the tips of the tail), y how high on its side (1 the
// ridge of the back, 0 the keel of the belly); in the mouth: x how far inside (0 at the lips); on
// a tooth: x root (0) to point (1); on a fin: x root (0) to tip (1), y leading edge (0) to
// trailing edge (1); on an eye: x middle (0) to rim (1).
//
// It swims as the fast mackerels and tunas do (between carangiform and thunniform): the long
// front of the body all but still, a wave that grows large only over the last third, the stiff
// crescent tail swung behind its wrist. All of it is a function of `phase` alone, so a picture
// of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model (body lengths unless said).
const float LENGTH = 1.8;
const float HALF = 0.9;
// Where the tail fin is hinged (metres behind the jaw's tip): behind it the tail is one plate.
const float JOINT = 1.638;
// The jaw's hinge (how far along, how high), the gill cover's edge, the eye.
const float HINGE_S = 0.118;
const float HINGE_Y = -0.01063;
const float GILL_S = 0.228;
const float GILL_K = 10.0;
const float GILL_Y0 = -0.004;
const vec2 EYE_AT = vec2(0.13, 0.014);
// How far the lower jaw swings down wide open, and how far the upper head lifts (radians).
const float GAPE_OPEN = 0.5;
const float UPPER_LIFT = 0.08;

// How far through a beat of its tail (0..1, it wraps). Set by Wahoo.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is. (As the yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely it beats, for 1 as a wahoo cruising (its tail tips swing about 0.13 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;
// How far its mouth is open: 0 shut, 1 wide open (as when it strikes). The lower jaw swings
// down about its hinge, the upper head lifts a little, and the teeth show.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The back, and the electric blue it turns to where light glances off it; the cobalt bars.
uniform vec3 back : source_color = vec3(0.015, 0.08, 0.3);
uniform vec3 back_blue : source_color = vec3(0.08, 0.42, 0.95);
uniform vec3 bars : source_color = vec3(0.03, 0.1, 0.42);
// The flank and the belly.
uniform vec3 silver : source_color = vec3(0.7, 0.74, 0.79);
uniform vec3 belly : source_color = vec3(0.94, 0.95, 0.95);
// How strongly the bars show (0 none: a wahoo's bars fade when it is excited or dead).
uniform float bars_show = 1.0;
// The dark blue fins; the teeth; the inside of the mouth.
uniform vec3 fin_dark : source_color = vec3(0.02, 0.05, 0.14);
uniform vec3 fin : source_color = vec3(0.55, 0.6, 0.68);
uniform vec3 teeth : source_color = vec3(0.92, 0.9, 0.82);
uniform vec3 mouth_inside : source_color = vec3(0.22, 0.12, 0.13);
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

// The wahoo's cartoon eye: a racer's, intent on what is ahead. An electric blue iris (the blue of
// its back), a round pupil, a clean white, and an upper lid slanting down towards the snout in a
// determined frown; no lower lid. Its eye is small for its size, so it grows the most. (Kept in
// step with the model: the eye's radius, and the point it grows about, a little above its middle:
// out, up, along, in body lengths.)
const float EYE_R = 0.012;
const vec3 EYE_PIVOT = vec3(0.021386, 0.0188, 0.13);
const float EYE_BIG = 1.7;
const vec3 SCLERA = vec3(0.95, 0.96, 0.97);
const vec3 IRIS_IN = vec3(0.4, 0.88, 1.0);
const vec3 IRIS_OUT = vec3(0.04, 0.26, 0.85);
const float IRIS_R = 0.54;
// The pupil's half width and half height, in eye radii.
const vec2 PUPIL = vec2(0.25, 0.25);
// The upper lid's edge (eye radii up from the middle) and its slant (up per radius forward); the
// lower lid's (below -1: none).
const float LID_TOP = 0.52;
const float LID_SLANT = -0.3;
const float LID_LOW = -1.3;
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

// How far to one side the middle line of the body is, `xm` metres behind the jaw's tip: a wave
// that runs back along it, all but nothing over the front half, large only near the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.7 * (0.012 - 0.03 * s + 0.03 * s * s + 0.085 * s * s * s * s);
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
		float cloud = noise2(vec2(s * 40.0, q * 4.0) + 3.0);
		// Where the blue back ends: over the eye on the head, a third of the way down the side
		// along the body.
		float edge = mix(0.5, 0.3, smoothstep(0.1, 0.3, s)) + (cloud - 0.5) * 0.04;
		c = mix(belly, silver, smoothstep(-0.8, -0.25, q));
		c += silver * 0.25 * glance * glance;
		// The bars: about twenty-five cobalt bars standing up the side, from the back down
		// below the middle line, some forked low down; none on the head.
		float lane = s / 0.027 + 0.15 * (1.0 - q) + 0.05 * sin(q * 7.0);
		float k = floor(lane + 0.5);
		float d = abs(lane - k);
		float stripe = 1.0 - smoothstep(0.15, 0.21, d);
		// (every third bar forks into two thinner ones below the middle line)
		float fork = step(1.5, mod(k, 3.0)) * (1.0 - smoothstep(-0.15, 0.1, q));
		stripe = mix(stripe, 1.0 - smoothstep(0.06, 0.1, abs(d - 0.17)), fork);
		float reach = -0.42 + 0.12 * hash2(vec2(k, 4.0));
		float run = smoothstep(0.22, 0.26, s) * (1.0 - smoothstep(0.86, 0.9, s)) * smoothstep(reach - 0.08, reach + 0.04, q);
		vec3 bar = mix(bars, back_blue * 0.45, 0.3 * glance);
		c = mix(c, bar, stripe * run * bars_show * (0.75 + 0.25 * cloud));
		float dark = smoothstep(edge - 0.05, edge + 0.08, q);
		vec3 top = mix(back, back_blue, 0.25 + 0.45 * glance + 0.15 * cloud);
		c = mix(c, top, dark);
		// The gill cover's edge: a fine dark line.
		float behind = s - (GILL_S - GILL_K * (y - GILL_Y0) * (y - GILL_Y0));
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.6, 0.8, q));
		c = mix(c, c * 0.45, (1.0 - smoothstep(0.0, 0.0012, abs(behind))) * 0.6 * span);
		// The beak: dark above, its lower jaw dusky below.
		c = mix(c, back * 0.8, (1.0 - smoothstep(0.03, 0.1, s)) * smoothstep(-0.1, 0.4, q) * 0.7);
		rough = mix(0.26, 0.4, dark);
		spec = mix(0.7, 0.55, dark);
	} else if (p == 1 || p == 2 || p == 10) {
		// The dorsal fins and the finlets: dark blue, the long first with clear skin between its
		// many spines.
		float ray = pow(abs(cos(3.14159265 * UV.y * (p == 1 ? 24.0 : 12.0))), 6.0);
		c = mix(fin_dark, back_blue * 0.4, 0.25 * UV.x);
		c = mix(c, fin_dark * 0.5, ray * 0.5);
		c += back_blue * 0.2 * glance * glance;
		rough = 0.45;
	} else if (p == 3) {
		// The anal fin: dusky silver-blue.
		c = mix(silver * 0.75, fin_dark * 2.0, 0.3 + 0.5 * UV.x) * (0.9 + 0.1 * cos(UV.y * 70.0));
		rough = 0.5;
	} else if (p == 4) {
		// The tail: dark blue-black.
		float ray = 0.5 + 0.5 * cos(UV.y * 70.0);
		c = mix(back * 1.2, fin_dark, smoothstep(0.0, 0.25, UV.x)) * (0.85 + 0.15 * ray);
		c += back_blue * 0.25 * glance * glance;
		rough = 0.4;
	} else if (p == 5) {
		// A pectoral fin: dark.
		float ray = 0.5 + 0.5 * cos(UV.y * 50.0);
		c = mix(fin_dark, fin * 0.6, 0.2 * UV.y) * (0.88 + 0.12 * ray);
		rough = 0.5;
	} else if (p == 6) {
		// A pelvic fin: pale below, dusky.
		c = mix(belly * 0.85, fin, 0.5 * UV.x) * (0.9 + 0.1 * cos(UV.y * 40.0));
		rough = 0.5;
	} else if (p == 7) {
		// An eye: a black pupil, a silver iris with a little gold, a dark rim.
		float r = UV.x;
		float round_it = atan(rest.y / LENGTH - EYE_AT.y, rest.z / LENGTH + 0.5 - EYE_AT.x);
		vec3 iris = mix(vec3(0.72, 0.74, 0.74), vec3(0.78, 0.66, 0.36), smoothstep(0.55, 0.68, r) * (1.0 - smoothstep(0.7, 0.92, r)) * 0.4);
		iris *= 0.85 + 0.15 * noise2(vec2(round_it * 9.0, r * 3.0));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.5, 0.56, r));
		c = mix(c, back * 1.4, smoothstep(0.84, 1.0, r) * 0.85);
		vec2 e = vec2(EYE_AT.x - (rest.z / LENGTH + 0.5), rest.y / LENGTH - EYE_AT.y) / EYE_R;
		c = mix(c, cartoon_eye(e), cartoon_eyes);
		c = eye_lids(c, e, mix(silver, back_blue, 0.55));
		rough = 0.12;
		spec = 0.6;
	} else if (p == 9) {
		// A tooth: ivory, clearer at its point.
		c = mix(teeth, teeth * 0.75 + vec3(0.1), UV.x * 0.5);
		rough = 0.25;
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
		// The inside of the mouth: darker deeper in (and skin where the lower jaw juts past the
		// upper: the top of its tip).
		c = mix(mouth_inside * 1.6, mouth_inside * 0.4, smoothstep(0.0, 0.8, UV.x));
		c = mix(back * 1.1, c, smoothstep(0.0, 0.12, UV.x));
		rough = 0.75;
		spec = 0.25;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
