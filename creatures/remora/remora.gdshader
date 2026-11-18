shader_type spatial;
// The remora (remora.gd): every marking drawn here (no texture files), its swimming, its jaw and
// the stillness of a remora riding on a host.
// What each point is comes from the model (tools/build_remora.py): UV2.y the part (0 body, 1 the
// dorsal fin, 3 the anal fin, 4 the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 the inside
// of the mouth, 9 a tooth, 11 a gill arch, 12 the sucker disc); UV2.x how much of the jaw's swing a
// point takes (above 0 the lower jaw, below 0 the upper head, which lifts a little). UV, on the
// body: x how far along (0 the jaw's tip, 1 the tips of the tail), y how high on its side (1 the
// ridge of the back, 0 the keel of the belly); in the mouth: x how far inside (0 at the lips); on
// a tooth: x root (0) to point (1); on a fin: x root (0) to tip (1), y leading edge (0) to
// trailing edge (1); on an eye: x middle (0) to rim (1); on the disc: x how far out from its middle
// to its edge (0 to 1, round the oval), y how high on a slat (1 its crest, 0 the groove).
//
// It swims with more of its body than a tuna does (a long slender fish): a wave that grows along
// it from behind the head, largest at the tail. `riding` lays it straight and still, as when its
// disc holds it to a host, with only the tip of its tail and its fins trembling. All of it is a
// function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model (body lengths unless said).
const float LENGTH = 0.6;
const float HALF = 0.3;
// Where the tail fin is hinged (metres behind the jaw's tip): behind it the tail is one plate.
const float JOINT = 0.543;
// The jaw's hinge (how far along, how high), the gill cover's edge, the eye.
const float HINGE_S = 0.072;
const float HINGE_Y = -0.00423;
const float GILL_S = 0.185;
const float GILL_K = 12.0;
const float GILL_Y0 = -0.004;
const vec2 EYE_AT = vec2(0.098, 0.006);
// The disc: where it begins and ends along the head, and its half width at its widest.
const vec3 DISC = vec3(0.038, 0.272, 0.028);
// How far the lower jaw swings down wide open, and how far the upper head lifts (radians).
const float GAPE_OPEN = 0.55;
const float UPPER_LIFT = 0.1;
// Riding: how far the tip of the tail trembles either way (metres at scale 1), and the fins.
const float TREMBLE = 0.006;
const float FIN_TREMBLE = 0.004;

// How far through a beat of its tail (0..1, it wraps). Set by Remora.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is. (As the yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely it beats, for 1 as a remora cruising (its tail tips swing about 0.05 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;
// How far its mouth is open: 0 shut, 1 wide open. The lower jaw swings down about its hinge, the
// upper head lifts a little.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// Riding on a host: 0 swimming, 1 stuck by its disc, straight and still (sway and curl are let go
// of), only the tip of its tail and its fins trembling.
uniform float riding : hint_range(0.0, 1.0) = 0.0;

// The body: a dark grey-brown all over (it rides upside down as often as not, so its belly is as
// dark as its back), and along each side a black band from the jaw through the eye to the tail,
// edged above and below with a pale stripe.
uniform vec3 body : source_color = vec3(0.24, 0.225, 0.21);
uniform vec3 band : source_color = vec3(0.025, 0.025, 0.03);
uniform vec3 stripe : source_color = vec3(0.78, 0.78, 0.74);
// How strongly the band and its stripes show (0 none: a plain grey remora).
uniform float stripes_show = 1.0;
// The fins (dark, the dorsal, anal and tail fins edged pale); the disc's slats and its grooves;
// the teeth; the inside of the mouth.
uniform vec3 fin_dark : source_color = vec3(0.05, 0.05, 0.055);
uniform vec3 fin_edge : source_color = vec3(0.72, 0.72, 0.68);
uniform vec3 slat : source_color = vec3(0.56, 0.5, 0.5);
uniform vec3 groove : source_color = vec3(0.06, 0.045, 0.05);
uniform vec3 teeth : source_color = vec3(0.85, 0.82, 0.74);
uniform vec3 mouth_inside : source_color = vec3(0.3, 0.17, 0.18);
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

// The remora's cartoon eye: a hitchhiker's, half-lidded, lazy and pleased with itself. An amber
// iris, a round pupil, a heavy upper lid lying low and level and a lower lid pushed up a little.
// (Kept in step with the model: the eye's radius, and the point it grows about, a little above
// its middle: out, up, along, in body lengths.)
const float EYE_R = 0.0085;
const vec3 EYE_PIVOT = vec3(0.037046, 0.0094, 0.098);
const float EYE_BIG = 1.6;
const vec3 SCLERA = vec3(0.95, 0.95, 0.93);
const vec3 IRIS_IN = vec3(1.0, 0.82, 0.35);
const vec3 IRIS_OUT = vec3(0.62, 0.32, 0.06);
const float IRIS_R = 0.56;
// The pupil's half width and half height, in eye radii.
const vec2 PUPIL = vec2(0.27, 0.27);
// The upper lid's edge (eye radii up from the middle) and its slant (up per radius forward); the
// lower lid's (below -1: none).
const float LID_TOP = 0.16;
const float LID_SLANT = 0.06;
const float LID_LOW = -0.66;
const float LID_LOW_SLANT = -0.05;

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
// that runs back along it, small at the head and growing to the tail; riding, only the tip of the
// tail trembles, quicker (three times a beat).
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.75 * (0.018 - 0.04 * s + 0.045 * s * s + 0.07 * s * s * s * s);
	float swim = sway * (1.0 - riding) * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
	float shiver = riding * TREMBLE * smoothstep(0.7, 1.0, s) * sin(6.2831853 * (3.0 * phase - 1.5 * s));
	return swim + shiver;
}

// The body behind the head laid round an arc (see `curl`); riding, it lies straight.
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2 * LENGTH;
	float d = v.z - from;
	float bend = curl * (1.0 - riding);
	if (abs(bend) < 0.001 || d <= 0.0) {
		return;
	}
	float k = bend / (0.7 * LENGTH);
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
	int p = int(part + 0.5);
	// The cartoon eye is bigger: the eye grows about a point near its middle.
	if (p == 7 && cartoon_eyes > 0.0) {
		vec3 pivot = vec3(sign(v.x) * EYE_PIVOT.x, EYE_PIVOT.y, EYE_PIVOT.z - 0.5) * LENGTH;
		v = pivot + (v - pivot) * mix(1.0, EYE_BIG, cartoon_eyes);
	}
	// Riding, its fins tremble: the paired fins' tips in and out, a ripple along the dorsal and
	// anal fins' edges (four times a beat).
	if (riding > 0.0) {
		if (p == 5 || p == 6) {
			v.x += sign(v.x) * riding * FIN_TREMBLE * UV.x * sin(6.2831853 * (4.0 * phase + 0.3 * UV.y));
		} else if (p == 1 || p == 3) {
			v.x += riding * FIN_TREMBLE * 0.7 * UV.x * sin(6.2831853 * (4.0 * phase - 1.5 * UV.y));
		}
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
	float slope = (side_at(zc + 0.003) - side_at(zc - 0.003)) / 0.006;
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
	float shine = 1.0 - smoothstep(0.1, 0.135, length(e - vec2(0.22, 0.02)));
	shine = max(shine, 1.0 - smoothstep(0.04, 0.065, length(e - vec2(-0.14, -0.3))));
	return mix(c, vec3(1.0), shine);
}

// The lids over an eye at `e` (as above), the colour of the skin: in the cartoon eye, where its
// character puts them, with a dark line along each edge and a dark outline round the eye; in the
// eye in life, out of sight. `blink` brings them together.
vec3 eye_lids(vec3 c, vec2 e, vec3 lid) {
	float top = mix(1.3, LID_TOP + LID_SLANT * e.x, cartoon_eyes);
	float low = mix(-1.3, LID_LOW + LID_LOW_SLANT * e.x, cartoon_eyes);
	float meet = mix(top, low, 0.6);
	top = mix(top, meet, blink);
	low = mix(low, meet, blink);
	float over = max(smoothstep(-0.02, 0.02, e.y - top), smoothstep(-0.02, 0.02, low - e.y));
	c = mix(c, lid, over);
	float line = max(1.0 - smoothstep(0.035, 0.07, abs(e.y - top)), 1.0 - smoothstep(0.025, 0.05, abs(e.y - low)));
	c = mix(c, vec3(0.02, 0.02, 0.03), line * mix(0.5, 1.0, cartoon_eyes) * step(0.001, max(cartoon_eyes, blink)));
	return mix(c, vec3(0.02, 0.02, 0.03), smoothstep(0.84, 0.92, length(e)) * cartoon_eyes);
}

// The band and its pale edges at height `q` on the side (-1 the keel, 0 the middle line, 1 the
// ridge), `s` along: over the head it runs from the lower jaw through the eye.
vec3 banded(vec3 c, float s, float q, float cloud) {
	float mid = mix(0.02, 0.0, smoothstep(0.05, 0.3, s));
	float wide = mix(0.08, 0.13, smoothstep(0.04, 0.35, s)) * (1.0 - 0.45 * smoothstep(0.72, 0.9, s));
	float d = abs(q - mid);
	float edge = 0.1 * (1.0 - 0.3 * smoothstep(0.7, 0.9, s));
	float run = smoothstep(0.004, 0.03, s) * (1.0 - smoothstep(0.88, 0.91, s));
	float pale = (1.0 - smoothstep(wide + edge - 0.012, wide + edge + 0.012, d)) * smoothstep(wide - 0.012, wide + 0.012, d);
	float dark = 1.0 - smoothstep(wide - 0.012, wide + 0.012, d);
	c = mix(c, stripe * (0.85 + 0.15 * cloud), pale * run * stripes_show);
	return mix(c, band, dark * run * stripes_show);
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.5;
	float spec = 0.45;
	float s = rest.z / LENGTH + 0.5;
	if (p == 0) {
		float y = rest.y / LENGTH;
		float q = UV.y * 2.0 - 1.0;
		float cloud = noise2(vec2(s * 30.0, q * 4.0) + 3.0);
		c = body * (0.85 + 0.25 * cloud);
		c = mix(c, body * 1.25, 0.2 * smoothstep(-0.2, -0.9, q));
		c = banded(c, s, q, cloud);
		c += vec3(0.05) * glance * glance;
		// The gill cover's edge: a fine dark line.
		float behind = s - (GILL_S - GILL_K * (y - GILL_Y0) * (y - GILL_Y0));
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.6, 0.8, q));
		c = mix(c, c * 0.4, (1.0 - smoothstep(0.0, 0.0015, abs(behind))) * 0.6 * span);
		// The skin round the disc: a little paler, soft.
		c = mix(c, slat * 0.55, 0.35 * smoothstep(0.8, 0.98, q) * smoothstep(DISC.x - 0.02, DISC.x, s) * (1.0 - smoothstep(DISC.y, DISC.y + 0.03, s)));
	} else if (p == 12) {
		// The sucker disc: pale slats with dark grooves between them, the middle ridge a little
		// darker, a soft fleshy rim.
		float e = UV.x;
		float crest = UV.y;
		c = mix(groove, slat, smoothstep(0.05, 0.85, crest));
		c *= 0.88 + 0.12 * noise2(vec2(s * 200.0, rest.x * 300.0));
		float ridge = 1.0 - smoothstep(0.002, 0.005, abs(rest.x / LENGTH));
		c = mix(c, slat * 0.42, ridge * 0.7);
		float rim = smoothstep(0.78, 0.86, e);
		c = mix(c, mix(slat * 0.75, body * 1.1, smoothstep(0.92, 1.0, e)), rim);
		rough = 0.65;
		spec = 0.4;
	} else if (p == 1 || p == 3) {
		// The dorsal and anal fins: dark, their front lobes' edges pale.
		float ray = 0.85 + 0.15 * cos(UV.y * 90.0);
		c = fin_dark * ray * 1.3;
		float lip = smoothstep(0.78, 0.95, UV.x) * (1.0 - smoothstep(0.1, 0.35, UV.y));
		c = mix(c, fin_edge, lip * 0.85);
		rough = 0.5;
	} else if (p == 4) {
		// The tail: black, its upper and lower corners white.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		c = fin_dark * (0.85 + 0.15 * ray);
		c = mix(c, fin_edge, smoothstep(0.75, 0.92, UV.x) * 0.9);
		rough = 0.45;
	} else if (p == 5 || p == 6) {
		// The pectoral and pelvic fins: dusky, paler towards their trailing edges.
		float ray = 0.5 + 0.5 * cos(UV.y * 40.0);
		c = mix(fin_dark * 1.6, body * 1.4, 0.4 * UV.y) * (0.88 + 0.12 * ray);
		rough = 0.5;
	} else if (p == 7) {
		// An eye: a black pupil, a dull gold iris, a dark rim.
		float r = UV.x;
		float round_it = atan(rest.y / LENGTH - EYE_AT.y, s - EYE_AT.x);
		vec3 iris = vec3(0.55, 0.45, 0.28) * (0.85 + 0.15 * noise2(vec2(round_it * 9.0, r * 3.0)));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.5, 0.56, r));
		c = mix(c, band * 1.4, smoothstep(0.84, 1.0, r) * 0.85);
		vec2 e = vec2(EYE_AT.x - s, rest.y / LENGTH - EYE_AT.y) / EYE_R;
		c = mix(c, cartoon_eye(e), cartoon_eyes);
		c = eye_lids(c, e, body * 1.3);
		rough = 0.12;
		spec = 0.6;
	} else if (p == 9) {
		// A tooth: ivory.
		c = mix(teeth, teeth * 0.8, UV.x * 0.5);
		rough = 0.3;
		spec = 0.5;
	} else if (p == 11) {
		// A gill arch (in the roof or the floor at the back of the mouth): pale rakers along its front
		// edge, then the bar and the fringe of blood-red filaments, darker deeper in, towards the hinge.
		float strands = 0.75 + 0.25 * sin(UV.x * 70.0);
		c = mix(gill_raker, gill_red * strands, smoothstep(0.06, 0.24, UV.y));
		c *= mix(1.0, 0.55, smoothstep(HINGE_S - 0.04, HINGE_S, s));
		rough = 0.35;
		spec = 0.5;
	} else {
		// The inside of the mouth: darker deeper in (and skin where the lower jaw juts past the
		// upper: the top of its tip).
		c = mix(mouth_inside * 1.6, mouth_inside * 0.4, smoothstep(0.0, 0.8, UV.x));
		c = mix(body * 1.1, c, smoothstep(0.0, 0.12, UV.x));
		rough = 0.75;
		spec = 0.25;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
