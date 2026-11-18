shader_type spatial;
// The gulper eel (gulper_eel.gd): every marking drawn here (no texture files), its swimming, its mouth and pouch,
// and the light of its tail. What each point is comes from the model (tools/build_gulper_eel.py): UV2.y the part
// (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail organ, 4 a pectoral fin, 6 an eye, 7 the lower jaw and
// pouch). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its
// side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to edge (1), y front (0) to back
// (1); on an eye: x middle (0) to rim (1); on the tail organ: x its bulb's base (0) to
// its end (0.6), then each filament's root (0.6) to its tip (1).
//
// It swims as eels do (anguilliform): a wave of more than a body's length runs back along the whole body, small at
// the head and growing to the tip of the whip. When it opens its mouth the lower jaw swings down and the pouch
// balloons out, deeper and wider, like a net; the head lifts a little. The tail organ glows (EMISSION: the only
// part that does). All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 0.80;
const float HALF = 0.40;
// Where the whip ends and the tail organ begins (metres behind the snout).
const float BODY_TO = 0.778;
// The jaws: how far back they run, where the hinge is (on the line of the mouth, whose slope is SLOPE), how far the
// lower jaw swings down and how far the head lifts back, wide open (radians), and how much deeper and wider the
// pouch balloons at its fullest.
const float JAW_TO = 0.16;
const float HINGE_Y = -0.0027;
const float SLOPE = 0.02;
const float GAPE_OPEN = 0.8;
const float HEAD_LIFT = 0.16;
const float POUCH_DEEP = 1.9;
const float POUCH_WIDE = 1.5;

// How far through a beat (0..1, it wraps): one wave down its body each beat. Set by GulperEel.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the head to the tail
// (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats: 1 as one swimming slowly (the tip of its whip swings about 0.06 m either way), 0 still.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.7;
// How far its mouth is open: 0 shut, 1 wide open, the pouch ballooned like a net.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How strongly its tail organ glows (0 none, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;

// The smooth black skin, and the grey the pouch's skin turns as it is stretched thin.
uniform vec3 skin : source_color = vec3(0.02, 0.02, 0.026);
uniform vec3 stretched : source_color = vec3(0.16, 0.14, 0.16);
uniform vec3 fin : source_color = vec3(0.045, 0.045, 0.055);
uniform vec3 mouth_inside : source_color = vec3(0.07, 0.025, 0.035);
// The tail organ's skin, and the light it gives.
uniform vec3 organ : source_color = vec3(0.9, 0.42, 0.5);
uniform vec3 organ_light : source_color = vec3(1.0, 0.3, 0.42);

varying vec3 rest;
varying float part;
varying float inside;
varying float stretch;

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

// How far to one side the middle line of the body is, `xm` metres behind the snout.
float side_at(float xm) {
	float s = xm / BODY_TO;
	float reach = LENGTH * (0.005 + 0.072 * pow(s, 1.4));
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2;
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

// Turns `v` and `n` about the X axis through `at` (y, z) by `a` (more than 0: what is above `at` goes forward,
// what is ahead of it goes down).
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
	stretch = 0.0;
	vec3 v = VERTEX;
	vec3 nn = NORMAL;
	int p = int(part + 0.5);
	float xm = v.z + HALF;
	float g = clamp(gape, 0.0, 1.0);
	vec2 hinge = vec2(HINGE_Y, JAW_TO - HALF);
	if (p == 7) {
		// The pouch balloons: deeper and wider about the line of the mouth, most in the middle of the jaws.
		float bump = pow(sin(3.14159265 * clamp(xm / JAW_TO, 0.0, 1.0)), 0.8);
		float lip = 0.0005 - SLOPE * xm;
		float sy = 1.0 + g * POUCH_DEEP * bump;
		float sx = 1.0 + g * POUCH_WIDE * bump;
		v.y = lip - (lip - v.y) * sy;
		v.x *= sx;
		nn = normalize(vec3(nn.x / sx, nn.y / sy, nn.z));
		stretch = g * bump * smoothstep(0.0, 0.006, lip - rest.y);
		// and the jaw swings down about its hinge; its end inside the head stays where it is
		pitch(v, nn, hinge, g * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.05, JAW_TO - 0.002, xm)));
	} else if (p == 3) {
		// the tail organ's filaments trail a little behind the whip's swing
		v.x += smoothstep(0.6, 1.0, UV.x) * 0.004 * sway * sin(6.2831853 * phase - 1.2);
	}
	// The head (and the jaw) lifts back a little about the hinge as the mouth opens.
	pitch(v, nn, hinge, -g * HEAD_LIFT * (1.0 - smoothstep(JAW_TO - 0.02, JAW_TO + 0.05, xm)));
	xm = v.z + HALF;
	float zc = min(xm, BODY_TO);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.001) - side_at(zc - 0.001)) / 0.002;
	float turn = atan(slope);
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
	float rough = 0.4;
	float spec = 0.45;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		// Smooth black skin, faintly mottled, a soft sheen where light glances off it.
		float blot = noise2(vec2(xm * 70.0 + rest.x * 90.0, rest.y * 120.0));
		c = skin * (0.85 + 0.35 * blot);
		c += vec3(0.05, 0.05, 0.07) * glance * glance;
		// the line of the mouth, and the pouch's skin greying as it is stretched thin
		float mouth = (1.0 - smoothstep(0.0002, 0.0006, abs(rest.y - (0.0005 - SLOPE * xm)))) * (1.0 - smoothstep(JAW_TO - 0.003, JAW_TO, xm)) * (1.0 - inside);
		c = mix(c, vec3(0.0), mouth * 0.8);
		c = mix(c, stretched * (0.8 + 0.4 * blot), clamp(stretch, 0.0, 1.0) * 0.7);
		c = mix(c, mouth_inside, inside);
		rough = mix(0.35, 0.6, inside);
		spec = mix(0.45, 0.25, inside);
	} else if (p == 1 || p == 2 || p == 4) {
		float ray = pow(abs(cos(3.14159265 * UV.y * (p == 4 ? 6.0 : 140.0))), 6.0);
		c = mix(fin, fin * 2.0, smoothstep(0.4, 1.0, UV.x) * 0.5);
		c = mix(c, skin, ray * 0.4);
		rough = 0.5;
	} else if (p == 6) {
		// A tiny eye: dark, with a dull gleam.
		c = mix(vec3(0.004, 0.005, 0.008), vec3(0.2, 0.22, 0.26), smoothstep(0.5, 0.75, UV.x) * (1.0 - smoothstep(0.85, 1.0, UV.x)));
		rough = 0.12;
		spec = 0.7;
	} else {
		// The tail organ: a pink-red bulb, brightest at its middle, its filaments fading towards their tips.
		float u = UV.x;
		float bulb = 1.0 - smoothstep(0.55, 0.62, u);
		float lit = bulb * (0.7 + 0.5 * sin(3.14159265 * clamp(u / 0.6, 0.0, 1.0))) + (1.0 - bulb) * (1.0 - smoothstep(0.6, 1.05, u)) * 0.8;
		c = organ;
		e = organ_light * 2.0 * glow * lit;
		rough = 0.3;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = e;
}
