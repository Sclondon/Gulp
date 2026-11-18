shader_type spatial;
// The California halibut (california_halibut.gd): every marking drawn here (no texture files), its
// swimming, its lying down on the sand and its jaw. A flatfish, modelled as it lies: its upper
// (eyed) side is +Y, the edge of its back +X, the edge of its belly and its lower jaw -X, its
// nose -Z. What each point is comes from the model (tools/build_california_halibut.py): UV2.y
// the part (0 body, 1 lower jaw, 2 the dorsal and anal fins, 3 the tail, 4 the pectoral and
// pelvic fins, 5 an eye); UV2.x, on the body and jaw, 1 inside the mouth. UV inside the mouth:
// x from the nose (0) to the hinge (1), y from the under lip (0) to the upper lip (1); on a
// fin: x from its root (0) to its edge (1), y along it; on an eye: x middle (0) to rim (1).
//
// It swims as flatfish do: a wave up and down along its flat body, small at the head and large
// at the tail, and a quicker ripple along the fins that fringe it. All of it is a function of
// `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 1.0;
const float HALF = 0.5;
// The flat its fins lie in, and its underside (metres above the origin).
const float SEAM = -0.0145;
const float UNDER = -0.0355;
// Where the lower jaw hinges (metres behind the snout); the mouth's line is x = -MOUTH_K * xm.
const float HINGE = 0.125;
const float MOUTH_K = 0.42;

// How far through a beat of its body (0..1, it wraps). Set by CaliforniaHalibut.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, as it lies (radians from
// the gills to the tail; 0 straight; more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// How widely it beats, for 1 as a halibut cruising (its tail rises and falls about 0.05 m).
uniform float sway = 1.0;
// The mouth: 0 shut, 1 wide open as when it bites (the lower jaw swung out about its hinge, the
// snout lifted a little the other way).
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// Lying on the sand: 0 swimming, 1 flat on the ground (no wave, its fins and tail laid down to
// the level of its underside, 0.0355 m below its origin).
uniform float settle : hint_range(0.0, 1.0) = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.05;

// The upper side: its sandy ground, the darker blotches, the pale spots and flecks.
uniform vec3 sand : source_color = vec3(0.47, 0.38, 0.25);
uniform vec3 blotch : source_color = vec3(0.2, 0.15, 0.09);
uniform vec3 pale : source_color = vec3(0.78, 0.7, 0.52);
// How strongly the blotches and spots show (0 plain sand; cheaper).
uniform float mottle = 1.0;
// The under (blind) side.
uniform vec3 belly : source_color = vec3(0.93, 0.92, 0.88);
// Inside the mouth, and its teeth.
uniform vec3 mouth : source_color = vec3(0.16, 0.05, 0.05);
uniform vec3 teeth : source_color = vec3(0.92, 0.9, 0.8);
// The iris of its eyes.
uniform vec3 iris : source_color = vec3(0.62, 0.5, 0.24);

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

// How high the body's flat is lifted, `xm` metres behind the snout: a wave that runs back along
// it, small at the head, large at the tail.
float lift_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * (0.005 + 0.05 * s * s);
	return sway * (1.0 - settle) * reach * sin(TAU * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.25 * LENGTH;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.75 * LENGTH);
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
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float xm = v.z + HALF;
	// The mouth: the lower jaw swings out (towards -X) about its hinge; the snout lifts a little
	// the other way.
	vec2 hinge = vec2(-MOUTH_K * HINGE, HINGE - HALF);
	float a = 0.0;
	if (part > 0.5 && part < 1.5) {
		a = gape * 0.62 * smoothstep(HINGE, HINGE - 0.05, xm);
	} else {
		a = -gape * 0.1 * smoothstep(HINGE + 0.02, 0.0, xm);
	}
	if (a != 0.0) {
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = v.xz - hinge;
		v.xz = hinge + vec2(d.x * ca + d.y * sa, d.y * ca - d.x * sa);
		n.xz = vec2(n.x * ca + n.z * sa, n.z * ca - n.x * sa);
	}
	// Lying down: the thin rear of the body sinks to the ground, and the fins and tail are laid
	// down from their roots to their edges.
	float rear = smoothstep(0.55, 0.88, xm);
	v.y -= settle * 0.012 * rear;
	bool fringe = part > 1.5 && part < 3.5;
	bool flat_fin = fringe || (part > 3.5 && part < 4.5 && rest.y < SEAM + 0.005);
	if (flat_fin) {
		v.y -= settle * UV.x * (SEAM - UNDER - 0.003 - 0.012 * rear);
	}
	if (fringe) {
		// The fins' own ripple, twice as quick as the body's wave and shorter.
		float swing = sway * (1.0 - settle) * 0.013 * UV.x;
		float at = TAU * (2.0 * phase - xm / 0.2);
		v.y += swing * sin(at);
		n = normalize(n + vec3(0.0, 0.0, swing * TAU / 0.2 * cos(at)) * n.y);
	}
	// The body's wave: each slice across it is lifted and tipped to stay square to the wave.
	float h = lift_at(xm);
	float slope = (lift_at(xm + 0.004) - lift_at(xm - 0.004)) / 0.008;
	float turn = atan(slope);
	float c = cos(turn);
	float sn = sin(turn);
	v = vec3(v.x, h + v.y * c, v.z - v.y * sn);
	n = vec3(n.x, n.y * c + n.z * sn, -n.y * sn + n.z * c);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The upper side's skin at a place on it (metres across, metres along): sand, darker blotches,
// pale flecks and round pale spots, a fine grain.
vec3 skin(vec2 at) {
	vec3 c = sand;
	float grain = noise2(at * 330.0);
	if (mottle > 0.0) {
		// (the place is pushed about a little, so that the blotches are not square)
		vec2 p = at + 0.03 * (vec2(noise2(at * 22.0 + 40.0), noise2(at * 22.0 + 90.0)) - 0.5);
		float big = 0.6 * noise2(p * 13.0 + 3.0) + 0.4 * noise2(p * 41.0 + 7.3);
		c = mix(c, blotch, mottle * 0.75 * smoothstep(0.5, 0.72, big));
		c = mix(c, pale, mottle * 0.45 * smoothstep(0.6, 0.8, noise2(p * 57.0 + 21.0)));
		vec2 g = p / 0.062;
		vec2 id = floor(g);
		vec2 f = fract(g) - 0.5 - (vec2(hash2(id), hash2(id + 17.0)) - 0.5) * 0.5;
		float d = length(f);
		float on = step(0.62, hash2(id + 9.0));
		c = mix(c, blotch, mottle * 0.3 * on * (1.0 - smoothstep(0.12, 0.3, d)));
		c = mix(c, pale, mottle * 0.6 * on * (1.0 - smoothstep(0.04, 0.15, d)));
	}
	return c * (0.88 + 0.24 * grain);
}

void fragment() {
	int p = int(part + 0.5);
	float upper = smoothstep(-0.3, 0.05, rest_normal.y);
	float xm = rest.z + HALF;
	vec3 c;
	float rough = 0.5;
	float spec = 0.4;
	if (p <= 1 && inside > 0.5) {
		// Inside the mouth: dark, a row of pointed teeth along each lip.
		float lip = min(UV.y, 1.0 - UV.y);
		float tri = abs(fract(UV.x * 24.0) - 0.5) * 2.0;
		float tooth = (1.0 - step(0.24 * (1.0 - tri), lip)) * smoothstep(0.03, 0.1, UV.x) * (1.0 - smoothstep(0.82, 0.95, UV.x));
		c = mix(mouth, teeth, tooth);
		rough = mix(0.95, 0.35, tooth);
		spec = mix(0.05, 0.5, tooth);
	} else if (p <= 1) {
		c = skin(rest.xz);
		// The lateral line: a high arch over the pectoral fin, then straight to the tail.
		float line_x = 0.008 + 0.055 * exp(-pow((xm - 0.27) / 0.065, 2.0));
		float line = (1.0 - smoothstep(0.0012, 0.003, abs(rest.x - line_x))) * smoothstep(0.17, 0.2, xm) * (1.0 - smoothstep(0.84, 0.87, xm));
		c = mix(c, blotch, line * 0.55);
		// The gill cover's edge.
		float gill = xm - (0.245 - 5.0 * (rest.x + 0.01) * (rest.x + 0.01));
		float crease = (1.0 - smoothstep(0.0, 0.003, abs(gill))) * step(-0.1, rest.x) * (1.0 - step(0.09, rest.x));
		c = mix(c, c * 0.45, crease * 0.6);
		// The lips: paler along the mouth's line, the line itself dark.
		float m = rest.x + MOUTH_K * xm;
		float along = 1.0 - smoothstep(HINGE - 0.004, HINGE + 0.003, xm);
		c = mix(c, pale * 0.9, 0.45 * (1.0 - smoothstep(0.003, 0.009, abs(m))) * along);
		c = mix(c, mouth, (1.0 - smoothstep(0.0006, 0.0018, abs(m))) * along);
		c = mix(belly, c, upper);
	} else if (p == 5) {
		// An eye: a dark pupil, a gold-brown iris, the skin's colour at its rim.
		float r = UV.x;
		c = mix(vec3(0.01, 0.01, 0.012), iris * (0.8 + 0.4 * noise2(rest.xz * 900.0)), smoothstep(0.4, 0.47, r));
		c = mix(c, sand * 0.7, smoothstep(0.74, 0.86, r));
		rough = 0.12;
		spec = 0.6;
	} else {
		// A fin: the skin's markings carried out onto it, its rays as fine lines, pale at its edge.
		float rays = p == 2 ? 75.0 : (p == 3 ? 17.0 : 9.0);
		float ray = 0.5 + 0.5 * cos(UV.y * TAU * rays);
		c = skin(rest.xz) * (0.8 + 0.2 * ray);
		c = mix(c, pale, 0.3 * smoothstep(0.75, 1.0, UV.x));
		c = mix(belly * (0.9 + 0.1 * ray), c, upper);
		rough = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
