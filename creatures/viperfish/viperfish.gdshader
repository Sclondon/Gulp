shader_type spatial;
// The viperfish (viperfish.gd): every marking drawn here (no texture files), its swimming, its mouth, its long
// dorsal ray and its lights. What each point is comes from the model (tools/build_viperfish.py): UV2.y the part
// (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 the long dorsal ray, 6 an eye, 7 the
// lower jaw, 8 a tooth of the upper jaw, 9 a tooth of the lower jaw, 10 the light at the ray's tip, 11 a
// photophore, 12 a pelvic fin, 13 the adipose fin). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the
// jaw: x how far along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root
// (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye or a photophore: x middle (0) to rim (1); on
// the ray and a tooth: x root (0) to tip (1); on the ray's light: x its base (0) to its top (1).
//
// It swims with a slow wave down the long body (more of it bends than in a tuna or a sardine). When it opens its
// mouth the lower jaw swings down and the head lifts back, as a viperfish's does. The photophores and the light on
// the ray glow (EMISSION). All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 0.30;
const float HALF = 0.15;
const float JOINT = 0.268;
// The lower jaw: how far back it runs, where its hinge is (on the line of the mouth, whose slope is SLOPE), how
// far it swings down and how far the head lifts back, wide open (radians).
const float JAW_TO = 0.04;
const float HINGE_Y = -0.0029;
const float SLOPE = 0.11;
const float GAPE_OPEN = 1.05;
const float HEAD_LIFT = 0.32;
// The root of the long dorsal ray (y, z in the model).
const vec2 RAY_ROOT = vec2(0.01581, -0.09);
const vec2 EYE_AT = vec2(0.0145, 0.0042);

// How far through a beat of its tail (0..1, it wraps). Set by Viperfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the tail
// (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats: 1 as one cruising (its tail tips swing about 0.025 m either way), 0 still.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.75;
// How far its mouth is open: 0 shut, 1 wide open (the jaw swings down, the head lifts back).
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How strongly its lights glow (0 none, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;
// How far the long dorsal ray is leant forward (radians; less than 0 further back).
uniform float ray_lean = 0.0;

// The dark skin, the iridescence on it (blue-green, turning violet where light glances off), the black lines of
// its net of hexagonal marks.
uniform vec3 skin : source_color = vec3(0.025, 0.032, 0.045);
uniform vec3 sheen : source_color = vec3(0.12, 0.34, 0.38);
uniform vec3 sheen_glance : source_color = vec3(0.3, 0.16, 0.42);
uniform vec3 net : source_color = vec3(0.004, 0.005, 0.008);
// How strongly the net shows.
uniform float net_show = 0.8;
// The fins: dark, clearer at their edges.
uniform vec3 fin : source_color = vec3(0.05, 0.06, 0.07);
uniform vec3 mouth_inside : source_color = vec3(0.07, 0.02, 0.03);
uniform vec3 tooth : source_color = vec3(0.86, 0.88, 0.9);
// The photophores' and the ray light's colour.
uniform vec3 light_colour : source_color = vec3(0.3, 0.6, 1.0);

varying vec3 rest;
varying float part;
varying float inside;

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.006 - 0.022 * s + 0.075 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.09;
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
	vec3 v = VERTEX;
	vec3 nn = NORMAL;
	int p = int(part + 0.5);
	float xm = v.z + HALF;
	float g = clamp(gape, 0.0, 1.0);
	vec2 hinge = vec2(HINGE_Y, JAW_TO - HALF);
	if (p == 7 || p == 9) {
		// The lower jaw (and its teeth) swings down about its hinge; its end inside the head stays where it is.
		pitch(v, nn, hinge, g * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.016, JAW_TO - 0.0005, xm)));
	} else if (p == 5 || p == 10) {
		// The long ray sways, bent more towards its tip.
		float t = p == 5 ? UV.x : 1.0;
		pitch(v, nn, RAY_ROOT, (ray_lean + 0.1 * sway * sin(6.2831853 * phase + 1.0)) * t);
		v.x += 0.006 * sway * pow(t, 1.5) * sin(6.2831853 * phase + 2.2);
	} else if (p == 4) {
		v.x += sign(rest.x) * UV.x * 0.0025 * sway * sin(6.2831853 * phase);
	}
	// The head (and everything on it, the jaw too) lifts back about the hinge as the mouth opens, the neck bending.
	pitch(v, nn, hinge, -g * HEAD_LIFT * (1.0 - smoothstep(JAW_TO - 0.012, JAW_TO + 0.03, xm)));
	xm = v.z + HALF;
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0008) - side_at(zc - 0.0008)) / 0.0016;
	float turn = atan(slope) * (1.0 + 0.2 * smoothstep(0.9 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	nn = vec3(nn.x * c + nn.z * sn, nn.y, -nn.x * sn + nn.z * c);
	curl_bend(v, nn);
	VERTEX = v;
	NORMAL = nn;
}

// How near a point is to the edge of its cell in a grid of hexagons (0 at the edge, 0.5 in the middle), and which
// cell it is in.
vec3 hexes(vec2 p) {
	vec2 r = vec2(1.0, 1.7320508);
	vec2 h = r * 0.5;
	vec2 a = mod(p, r) - h;
	vec2 b = mod(p - h, r) - h;
	vec2 g = dot(a, a) < dot(b, b) ? a : b;
	vec2 id = p - g;
	vec2 q = abs(g);
	float edge = 0.5 - max(dot(q, normalize(vec2(1.0, 1.7320508))), q.x);
	return vec3(edge, id);
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	vec3 e = vec3(0.0);
	float rough = 0.4;
	float spec = 0.5;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float q = UV.y;
		// The net of hexagonal marks over the body (none on the head), each cell a little brighter or duller.
		vec3 hx = hexes(vec2(xm / 0.0042, q * 9.0));
		float body_net = smoothstep(0.032, 0.08, xm) * (1.0 - smoothstep(0.255, 0.268, xm));
		float cell = hash2(hx.yz);
		// Darkest along the back; the iridescence strongest low on the flanks.
		c = skin * (0.75 + 0.5 * cell * body_net);
		float flank = smoothstep(0.85, 0.35, q) * (1.0 - smoothstep(0.12, 0.0, q) * 0.5);
		vec3 tint = mix(sheen, sheen_glance, glance);
		c += tint * (0.25 + 0.75 * glance * glance) * (0.25 + 0.75 * flank) * (0.5 + 0.7 * cell * body_net);
		c = mix(c, net, (1.0 - smoothstep(0.02, 0.07, hx.x)) * body_net * net_show);
		// the line of the mouth
		float mouth = (1.0 - smoothstep(0.0001, 0.0004, abs(rest.y - (0.0015 - SLOPE * xm)))) * (1.0 - smoothstep(JAW_TO - 0.002, JAW_TO, xm));
		c = mix(c, net, mouth * 0.8);
		rough = 0.3;
		spec = 0.6;
		c = mix(c, mouth_inside, inside);
		rough = mix(rough, 0.6, inside);
		spec = mix(spec, 0.25, inside);
	} else if (p == 1 || p == 2 || p == 3 || p == 4 || p == 12 || p == 13) {
		float ray = pow(abs(cos(3.14159265 * UV.y * 6.0)), 8.0);
		c = mix(fin, fin * 2.2, smoothstep(0.5, 1.0, UV.x) * 0.6);
		c = mix(c, net, ray * 0.5 * (p == 13 ? 0.0 : 1.0));
		rough = 0.5;
	} else if (p == 5) {
		// The long ray: dark, paler and glowing faintly near its tip.
		c = mix(fin, vec3(0.3, 0.32, 0.36), smoothstep(0.5, 1.0, UV.x));
		e = light_colour * 0.3 * smoothstep(0.9, 1.0, UV.x) * glow;
	} else if (p == 6) {
		// The big eye: black, with a blue-green gleam round its pupil.
		float r = UV.x;
		c = mix(vec3(0.003, 0.004, 0.006), vec3(0.14, 0.28, 0.3), smoothstep(0.5, 0.6, r) * (1.0 - smoothstep(0.8, 1.0, r)));
		rough = 0.08;
		spec = 0.8;
	} else if (p == 8 || p == 9) {
		c = mix(tooth * 0.55, tooth, smoothstep(0.0, 0.4, UV.x));
		c += vec3(0.2) * glance;
		rough = 0.12;
		spec = 0.8;
	} else if (p == 10) {
		// The light on the ray's tip.
		c = vec3(0.8, 0.88, 0.95);
		e = light_colour * 2.2 * glow * (0.6 + 0.4 * smoothstep(0.2, 1.0, UV.x));
		rough = 0.3;
	} else {
		// A photophore: a bright middle, a dark rim.
		float r = UV.x;
		float lit = 1.0 - smoothstep(0.45, 0.85, r);
		c = mix(vec3(0.6, 0.75, 0.85), net, smoothstep(0.7, 1.0, r));
		e = light_colour * 1.8 * glow * lit;
		rough = 0.2;
		spec = 0.7;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = e;
}
