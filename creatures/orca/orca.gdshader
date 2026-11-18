shader_type spatial;
// The orca (orca.gd): every marking drawn here (no texture files), its swimming, its mouth and the
// shape of its dorsal fin. What each point is comes from the model (tools/build_orca.py): UV2.y the
// part (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower tooth, 4 the flukes, 5 the dorsal fin, 6 a
// flipper, 7 an eye); UV2.x, on the body and the jaw, how much it is inside the mouth. UV, on the
// body and jaw: x how far along, y how high on its side (1 the ridge of the back, 0 the keel of the
// belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye: x
// middle (0) to rim (1).
//
// It swims as whales and dolphins do: its flukes beat UP AND DOWN. A wave runs back along the
// body, all but nothing at the flippers and growing down the tail stock, and the flukes pitch
// about their root as one stiff plate. All of it is a function of `phase` alone, so a picture of
// it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 7.0;
const float HALF = 3.5;
// Where the flukes are hinged (metres behind the tip of the jaw): behind it they are one stiff plate.
const float JOINT = 6.2;
// The corner of the mouth, where the lower jaw hinges (metres behind the tip, metres up).
const float CORNER = 0.62;
const float HINGE_Y = -0.1212;
const float BLOWHOLE = 1.2;
const vec2 EYE_AT = vec2(0.80, -0.04);
// The dorsal fin's edges, as the model has them (metres behind the tip, metres up), root to tip:
// the roots both shapes share, then the bull's middle points and tip, then the female's.
const vec2 DORSAL_LEAD_ROOT = vec2(2.42, 0.69);
const vec2 DORSAL_TRAIL_ROOT = vec2(3.38, 0.675);
const vec2 BULL_LEAD = vec2(2.66, 1.65);
const vec2 BULL_TRAIL = vec2(3.05, 1.42);
const vec2 BULL_TIP = vec2(2.88, 2.56);
const vec2 COW_LEAD = vec2(2.92, 1.55);
const vec2 COW_TRAIL = vec2(3.28, 0.95);
const vec2 COW_TIP = vec2(3.52, 1.66);
const float DORSAL_REACH = 0.985;
// How far the lower jaw swings down for `gape` 1 (radians), and how far the flukes' root rises and
// falls for `sway` 1 (of its length).
const float GAPE_MAX = 0.55;
const float REACH = 0.055;

// How far through a beat of its flukes (0..1, it wraps). Set by Orca.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// flippers to the flukes (0 straight; more than 0 the tail comes round to +X, as the fish's does).
uniform float curl = 0.0;
// The same up and down, about its middle, in radians from its head to its flukes (0 straight;
// more than 0 its head and its flukes both come up; less than 0 both go down, its back arched:
// the top of a leap, the start of a dive).
uniform float arch = 0.0;
// How widely it beats, for 1 an orca cruising (its fluke tips rise and fall about 0.6 m).
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape = 0.0;
// Its dorsal fin: 0 a female's or a young one's, shorter (0.9 m) and curved back; 1 a grown bull's
// tall straight blade (1.8 m).
uniform float fin_tall = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.05;

// The black, the white, the grey saddle behind the dorsal fin.
uniform vec3 black : source_color = vec3(0.025, 0.027, 0.032);
uniform vec3 white : source_color = vec3(0.93, 0.93, 0.9);
uniform vec3 saddle : source_color = vec3(0.42, 0.43, 0.45);
// The inside of the mouth; the teeth.
uniform vec3 mouth : source_color = vec3(0.6, 0.3, 0.32);
uniform vec3 tooth : source_color = vec3(0.92, 0.88, 0.76);
// How strongly the eye patch is tinted yellow, as on some (0 white).
uniform float patch_tint = 0.0;

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

vec2 bezier(vec2 a, vec2 b, vec2 c, float t) {
	float s = 1.0 - t;
	return s * s * a + 2.0 * s * t * b + t * t * c;
}

// A point of the dorsal fin's flat (metres behind the tip, metres up) for one shape.
vec2 dorsal_at(float t, float u, vec2 lead, vec2 trail, vec2 tip) {
	vec2 a = bezier(DORSAL_LEAD_ROOT, lead, tip, t * DORSAL_REACH);
	vec2 b = bezier(DORSAL_TRAIL_ROOT, trail, tip, t * DORSAL_REACH);
	return mix(a, b, u);
}

// How far up the middle line of the body is, `xm` metres behind the tip: a wave that runs back
// along it, least at the flippers, large only down the tail stock.
float lift_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * REACH * (0.07 - 0.3 * s + 0.33 * s * s + 0.9 * s * s * s * s);
	return sway * reach * sin(TAU * (phase - s / wave));
}

// The body behind the head laid round an arc to one side (see `curl`).
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

// The whole body laid round an arc that goes up and down, about its middle (see `arch`).
void arch_bend(inout vec3 v, inout vec3 n) {
	if (abs(arch) < 0.001) {
		return;
	}
	float k = arch / LENGTH;
	float a = v.z * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x, n.y * c + n.z * sn, n.z * c - n.y * sn);
	v = vec3(v.x, r - (r - v.y) * c, (r - v.y) * sn);
}

void vertex() {
	part = UV2.y;
	inside = UV2.x;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	if (p == 5) {
		// The dorsal fin: its flat drawn again between the female's shape and the bull's, from the
		// same edges the model was built with (it was built as the bull's); its thickness kept.
		vec2 bull = dorsal_at(UV.x, UV.y, BULL_LEAD, BULL_TRAIL, BULL_TIP);
		vec2 cow = dorsal_at(UV.x, UV.y, COW_LEAD, COW_TRAIL, COW_TIP);
		vec2 here = mix(cow, bull, clamp(fin_tall, 0.0, 1.0));
		v.y += here.y - bull.y;
		v.z += here.x - bull.x;
	}
	rest = v;
	rest_normal = n;
	if (p == 1 || p == 3) {
		// The lower jaw (and its teeth) swings down about the corner of the mouth; behind the
		// corner, inside the body, it stays.
		float a = GAPE_MAX * clamp(gape, 0.0, 1.0) * smoothstep(CORNER + 0.02, CORNER - 0.08, v.z + HALF);
		vec2 hinge = vec2(HINGE_Y, CORNER - HALF);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	float xm = v.z + HALF;
	// (the flukes, behind their hinge, are one stiff plate: they turn about the hinge)
	float zc = min(xm, JOINT);
	float h = lift_at(zc);
	float slope = (lift_at(zc + 0.02) - lift_at(zc - 0.02)) / 0.04;
	// (the flukes pitch a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.35 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec2 o = vec2(v.y, xm - zc);
	v = vec3(v.x, h + o.x * c + o.y * sn, zc - HALF - o.x * sn + o.y * c);
	n = vec3(n.x, n.y * c + n.z * sn, -n.y * sn + n.z * c);
	arch_bend(v, n);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The line of the mouth, as the model has it.
float mouth_y(float xm) {
	return -0.125 - 0.05 * xm + 0.035 * smoothstep(0.42, 0.63, xm);
}

// How white the skin is at a place: `xm` behind the tip, `y` up, `h` how high on its side (0..1),
// `ax` how far out to the side (metres).
float whiteness(float xm, float y, float h, float ax, float side) {
	float wob = (noise2(vec2(xm * 2.0, side * 3.0)) - 0.5) * 0.03;
	// The chin and throat white, back to the flippers; a narrow white band down the middle of the
	// belly between them; wider again behind, at the navel and the vent.
	float band = 0.36 - 0.05 * smoothstep(0.7, 1.4, xm);
	band = mix(band, 0.045, smoothstep(1.35, 2.0, xm));
	band = mix(band, 0.16, smoothstep(2.9, 3.5, xm));
	band = mix(band, 0.0, smoothstep(4.3, 4.75, xm));
	float w = 1.0 - smoothstep(band - 0.012, band + 0.012, h + wob);
	// The flank patch: a white lobe that sweeps up the side behind the dorsal fin and ends in a
	// point towards the tail.
	float s = clamp((xm - 3.3) / 1.95, 0.0, 1.0);
	float middle = 0.17 + 0.42 * pow(s, 0.75);
	float wide = 0.19 * pow(1.0 - s, 0.65) * smoothstep(3.2, 3.55, xm);
	w = max(w, 1.0 - smoothstep(wide - 0.015, wide + 0.015, abs(h + wob - middle)));
	// The eye patch: an oval above and behind the eye, its long axis tilted a little up towards
	// the back, its front end the narrower.
	vec2 e = vec2(xm - 1.12, y - 0.13);
	float tilt = 0.18;
	vec2 r = vec2(e.x * cos(tilt) + e.y * sin(tilt), -e.x * sin(tilt) + e.y * cos(tilt));
	float tall = mix(0.075, 0.115, smoothstep(-0.3, 0.25, r.x));
	float oval = length(vec2(r.x / 0.36, r.y / tall));
	w = max(w, 1.0 - smoothstep(0.94, 1.06, oval));
	return w;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.28;
	float spec = 0.55;
	float xm = rest.z + HALF;
	float side = rest.x >= 0.0 ? 1.0 : -1.0;
	if (p == 0 || p == 1) {
		float y = rest.y;
		float h = UV.y;
		float w = whiteness(xm, y, h, abs(rest.x), side);
		if (p == 1) {
			// The lower jaw: white under the chin, black along its lip.
			w = min(w, smoothstep(0.03, 0.06, mouth_y(min(xm, CORNER)) - y));
		}
		vec3 white_here = mix(white, vec3(0.95, 0.85, 0.55), patch_tint * smoothstep(0.7, 0.9, xm) * (1.0 - smoothstep(1.5, 1.6, xm)) * step(0.0, y));
		c = mix(black, white_here, w);
		// The saddle: a grey patch over the back behind the dorsal fin.
		vec2 sd = vec2((xm - 3.75) / 0.62, (h - 1.0) / 0.2);
		float sw = 1.0 - smoothstep(0.7, 1.15, length(sd) + (noise2(vec2(xm * 4.0, h * 6.0 + side * 2.0)) - 0.5) * 0.25);
		c = mix(c, saddle, sw * (1.0 - w));
		c *= 0.95 + 0.1 * noise2(vec2(xm * 30.0, h * 40.0 + side * 9.0));
		// The blowhole: a dark crescent on top of the head.
		vec2 b = vec2(rest.x, xm - BLOWHOLE);
		float ring = 1.0 - smoothstep(0.006, 0.014, abs(length(b) - 0.03));
		c = mix(c, vec3(0.0), max(ring * smoothstep(-0.01, 0.01, b.y), 1.0 - smoothstep(0.01, 0.02, length(b - vec2(0.0, 0.01)))) * step(0.0, y) * float(p == 0));
		// The inside of the mouth: pink, darker towards the throat; behind the corner, where the
		// roof falls to the belly over the back of the jaw, it is skin coloured.
		vec3 in_mouth = mix(mouth, mouth * 0.3, smoothstep(0.2, CORNER + 0.05, xm));
		c = mix(c, in_mouth, smoothstep(0.1, 0.6, inside) * (1.0 - smoothstep(CORNER + 0.03, CORNER + 0.07, xm)));
		rough = mix(rough, 0.5, inside);
	} else if (p == 2 || p == 3) {
		// A tooth: ivory, darker at the gum.
		c = mix(tooth * 0.65, tooth, smoothstep(0.1, 0.5, UV.x));
		rough = 0.3;
	} else if (p == 4) {
		// The flukes: black above; white below with a black edge all round.
		float under = 1.0 - smoothstep(-0.2, 0.2, rest_normal.y);
		float edge = smoothstep(0.62, 0.8, UV.y) + smoothstep(0.6, 0.85, UV.x) + 1.0 - smoothstep(0.12, 0.3, UV.y);
		c = mix(black, white * 0.9, under * (1.0 - clamp(edge, 0.0, 1.0)));
		c *= 0.95 + 0.1 * noise2(vec2(rest.x, rest.z) * 20.0);
	} else if (p == 5) {
		// The dorsal fin: black.
		c = black * (0.95 + 0.15 * noise2(rest.yz * 18.0));
	} else if (p == 6) {
		// A flipper: black.
		c = black * (0.95 + 0.15 * noise2(rest.xz * 18.0));
	} else {
		// An eye: dark brown, all but black.
		float r = UV.x;
		c = mix(vec3(0.02, 0.014, 0.01), vec3(0.1, 0.06, 0.03), smoothstep(0.35, 0.7, r));
		c = mix(c, black, smoothstep(0.8, 1.0, r));
		rough = 0.12;
		spec = 0.7;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
