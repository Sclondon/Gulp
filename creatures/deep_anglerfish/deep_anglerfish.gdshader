shader_type spatial;
// The humpback anglerfish (deep_anglerfish.gd): every marking drawn here (no texture files), its swimming, its
// mouth, its rod and the light of its lure. What each point is comes from the model
// (tools/build_deep_anglerfish.py): UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
// pectoral fin, 5 the rod, 6 an eye, 7 the lower jaw, 8 a tooth of the roof, 9 a tooth of the lower jaw, 10 the
// lure's bulb). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on
// its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0)
// to trailing edge (1); on an eye: x middle (0) to rim (1); on the rod and a tooth: x root (0) to tip (1); on the
// bulb: x its base (0) to its top (1).
//
// It swims as anglerfish of the deep do, slowly: the stiff round body barely bends, the small tail sweeps, the
// little pectoral fins fan. The rod sways and can be flicked; the bulb glows (EMISSION: the only part that does).
// All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 0.30;
const float HALF = 0.15;
// Where the tail fin is hinged (metres behind the jaw): behind it the tail is one plate.
const float JOINT = 0.228;
// The lower jaw: how far back it runs (metres behind its tip), where its hinge is there (on the line of the
// mouth, whose slope is SLOPE), and how far it swings down, wide open (radians).
const float JAW_TO = 0.095;
const float HINGE_Y = -0.011;
const float SLOPE = 0.6;
const float GAPE_OPEN = 1.05;
// Where the rod rises (y, z in the model).
const vec2 ROD_ROOT = vec2(0.07066, -0.13);
const vec2 EYE_AT = vec2(0.058, 0.033);

// How far through a beat of its tail (0..1, it wraps). Set by DeepAnglerfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the tail
// (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats: 1 as one drifting along (its tail's edge swings about 0.02 m either way), 0 still.
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open (as when it strikes). The lower jaw swings down about its hinge.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// The lure: how bright its bulb is (0 dark, 1 lit), how strongly every light of it glows (0..2), and how hard the
// rod is flicked once each beat of the tail (0 never: it only sways).
uniform float lure : hint_range(0.0, 1.0) = 1.0;
uniform float glow : hint_range(0.0, 2.0) = 1.0;
uniform float flick : hint_range(0.0, 1.0) = 0.0;
// How far the rod is leant forward over the mouth (radians; less than 0 back).
uniform float rod_lean = 0.0;

// The velvety black skin and the brown that shows through it.
uniform vec3 skin : source_color = vec3(0.022, 0.018, 0.02);
uniform vec3 skin_brown : source_color = vec3(0.075, 0.05, 0.045);
// The fins: dark, a little browner and clearer at their edges.
uniform vec3 fin : source_color = vec3(0.05, 0.035, 0.035);
// The inside of the mouth (black in life; a dark red-black here so that an open mouth reads).
uniform vec3 mouth_inside : source_color = vec3(0.1, 0.022, 0.03);
// The glassy teeth.
uniform vec3 tooth : source_color = vec3(0.86, 0.88, 0.9);
// The rod, towards its tip; the bulb's skin, and the light it gives.
uniform vec3 rod_tip : source_color = vec3(0.42, 0.36, 0.36);
uniform vec3 bulb : source_color = vec3(0.82, 0.88, 0.92);
uniform vec3 lure_light : source_color = vec3(0.55, 0.82, 1.0);

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

// How far to one side the middle line of the body is, `xm` metres behind the jaw: a slow wave, nearly nothing
// in the round body, growing in the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.004 - 0.012 * s + 0.055 * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * 0.8));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.04;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.6 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// Turns `v` and `n` about the X axis through `at` (y, z) by `a` (more than 0: what is above `at` goes forward).
void pitch(inout vec3 v, inout vec3 n, vec2 at, float a) {
	float c = cos(a);
	float s = sin(a);
	vec2 d = vec2(v.y - at.x, v.z - at.y);
	v.y = at.x + d.x * c + d.y * s;
	v.z = at.y + d.y * c - d.x * s;
	n = vec3(n.x, n.y * c + n.z * s, n.z * c - n.y * s);
}

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	inside = UV2.x;
	vec3 v = VERTEX;
	vec3 nn = NORMAL;
	int p = int(part + 0.5);
	float xm = v.z + HALF;
	float wave = 6.2831853 * phase;
	if (p == 7 || p == 9) {
		// The lower jaw (and its teeth) swings down about its hinge; its end inside the head stays where it is.
		float a = clamp(gape, 0.0, 1.0) * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.035, JAW_TO - 0.001, xm));
		pitch(v, nn, vec2(HINGE_Y, JAW_TO - HALF), a);
	} else if (p == 5 || p == 10) {
		// The rod: it bends more towards its tip, sways from side to side, and jerks forward when flicked.
		float t = p == 5 ? UV.x : 1.0;
		float jerk = sin(3.14159265 * clamp(phase / 0.22, 0.0, 1.0));
		float lean = rod_lean + 0.07 * sway * sin(wave + 1.3) + flick * 0.55 * jerk * jerk * (1.0 - 0.35 * smoothstep(0.1, 0.22, phase));
		pitch(v, nn, ROD_ROOT, lean * t);
		v.x += 0.007 * sway * pow(t, 1.5) * sin(wave + 0.4);
	} else if (p == 4) {
		// The pectoral fins fan back and forth.
		float t = UV.x;
		v.x += sign(rest.x) * t * 0.007 * sway * sin(wave + 1.57);
		v.z += t * 0.004 * sway * cos(wave + 1.57);
	}
	xm = v.z + HALF;
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.001) - side_at(zc - 0.001)) / 0.002;
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.85 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	nn = vec3(nn.x * c + nn.z * sn, nn.y, -nn.x * sn + nn.z * c);
	curl_bend(v, nn);
	VERTEX = v;
	NORMAL = nn;
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	vec3 e = vec3(0.0);
	float rough = 0.75;
	float spec = 0.3;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		// Velvety black: blotches of brown under it, fine wrinkles, a soft sheen where the light glances off.
		float blot = noise2(vec2(xm * 45.0 + rest.x * 38.0, rest.y * 50.0 - rest.x * 24.0));
		float fine = noise2(vec2(xm * 380.0 + rest.x * 300.0, rest.y * 300.0 - rest.x * 160.0));
		c = mix(skin, skin_brown, smoothstep(0.45, 0.85, blot) * 0.7);
		c *= 0.8 + 0.35 * fine;
		// the paler lips of the mouth
		float lip = 1.0 - smoothstep(0.0005, 0.003, abs(rest.y - (0.046 - SLOPE * xm)));
		c = mix(c, skin_brown * 1.6, lip * (1.0 - step(JAW_TO, xm)) * 0.6);
		c += skin_brown * 0.6 * glance * glance * glance;
		rough = 0.68;
		spec = 0.28;
		c = mix(c, mouth_inside, inside);
		rough = mix(rough, 0.62, inside);
		spec = mix(spec, 0.22, inside);
	} else if (p == 1 || p == 2 || p == 3 || p == 4) {
		// The fins: dark, with fine rays, browner and clearer towards their edges.
		float ray = pow(abs(cos(3.14159265 * UV.y * (p == 3 ? 9.0 : 7.0))), 8.0);
		c = mix(fin, skin_brown * 1.4, smoothstep(0.55, 1.0, UV.x) * 0.6);
		c = mix(c, skin * 0.7, ray * 0.6);
		rough = 0.6;
	} else if (p == 5) {
		// The rod: black at its root, paler and a little pink towards its tip.
		c = mix(skin, rod_tip, smoothstep(0.35, 1.0, UV.x));
		rough = 0.5;
		e = lure_light * 0.25 * smoothstep(0.85, 1.0, UV.x) * glow * lure;
	} else if (p == 6) {
		// A tiny eye: dark, with a dull silver-blue gleam.
		c = mix(vec3(0.004, 0.005, 0.008), vec3(0.22, 0.26, 0.3), smoothstep(0.55, 0.75, UV.x) * (1.0 - smoothstep(0.85, 1.0, UV.x)));
		rough = 0.12;
		spec = 0.7;
	} else if (p == 8 || p == 9) {
		// A tooth: glassy, clear towards its tip, a little dusky at its root.
		c = mix(tooth * 0.55, tooth, smoothstep(0.0, 0.5, UV.x));
		c += vec3(0.2) * glance;
		rough = 0.12;
		spec = 0.8;
	} else {
		// The lure's bulb: a dark collar at its base, then the pale bulb that glows, brightest towards its top.
		float u = UV.x;
		float window = smoothstep(0.22, 0.42, u);
		c = mix(skin_brown, bulb, window);
		rough = 0.25;
		spec = 0.6;
		e = lure_light * window * (0.55 + 0.6 * smoothstep(0.4, 1.0, u)) * 2.2 * glow * lure;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = e;
}
