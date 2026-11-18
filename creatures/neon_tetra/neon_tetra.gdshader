shader_type spatial;
// The neon tetra and the cardinal tetra (neon_tetra.gd): every marking drawn here (no texture
// files), and their swimming. What each point is comes from the model
// (tools/build_neon_tetra.py): UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the
// tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 the adipose fin, 9 a gill arch). UV2.x: 1
// inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its
// side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y
// leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1).
//
// Every place here is in BODY LENGTHS (the tip of the jaw 0, the tips of the tail 1), as the
// build script has them: the model's metres are divided by `length_m`.
//
// It swims as small characins do (subcarangiform): a wave runs back along the body, small at the
// head, growing through the back half, the forked tail swung behind the wrist. All of it is a
// function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model (body lengths).
const float HALF = 0.5;
// Where the tail fin is hinged: behind it the tail is one plate.
const float JOINT = 0.812;
const float MOUTH_TO = 0.05;
const vec2 EYE_AT = vec2(0.085, 0.016);
// The lower jaw: how far back it runs (its hinge is there, on the line of the mouth), and how far
// it swings down, wide open (radians).
const float JAW_TO = 0.052;
const float HINGE_Y = -0.01744;
const float GAPE_OPEN = 1.0;

// How long the model is, in metres (0.035 the neon, 0.042 the cardinal). Set by NeonTetra.
uniform float length_m = 0.035;
// How far through one beat (0..1, it wraps). Set by NeonTetra.
uniform float phase = 0.0;
// How many times its tail beats in one beat (a whole number).
uniform float tail_beats = 3.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is. (As the yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely it beats, 1 cruising (its tail tips swing about a tenth of its length either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.95;
// How far its mouth is open: 0 shut, 1 wide open (as when it bites). The lower jaw swings down
// about its hinge.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The olive back and the dark line along its lower edge.
uniform vec3 back : source_color = vec3(0.30, 0.27, 0.15);
uniform vec3 back_dark : source_color = vec3(0.06, 0.06, 0.05);
// The stripe: blue seen face on, green where it is seen glancing; how brightly it glows (it
// shines in dark water of itself), how far back it runs (body lengths).
uniform vec3 stripe_blue : source_color = vec3(0.10, 0.55, 1.0);
uniform vec3 stripe_green : source_color = vec3(0.15, 0.95, 0.75);
uniform float glow = 0.9;
uniform float stripe_to = 0.68;
// The red band under the stripe, and where it begins (body lengths: 0.43 the neon, 0.04 the
// cardinal, whose red runs the whole length).
uniform vec3 red : source_color = vec3(0.82, 0.07, 0.05);
uniform float red_from = 0.43;
// The silver of the head and flank, the white belly.
uniform vec3 silver : source_color = vec3(0.78, 0.80, 0.83);
uniform vec3 belly : source_color = vec3(0.94, 0.94, 0.92);
// The clear fins (an opaque draw: the colour of a clear fin seen in water).
uniform vec3 fin : source_color = vec3(0.62, 0.66, 0.70);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.12, 0.03, 0.04);

// THE GILLS (part 9): four arches a side standing in the throat, a short tunnel from the back of the
// mouth to GILL_TO (as the model has them: body lengths). Seen only through the open mouth; as it
// opens they spread a little. Their filaments blood red, darker deeper in the throat.
const float GILL_FROM = 0.105;
const float GILL_TO = 0.186;
// Where the full model's old wall across the back of the mouth is lifted to as it opens (inside the
// head, above the roof of the mouth).
const float WALL_UP = 0.025;
uniform vec3 gill_red : source_color = vec3(0.55, 0.04, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.74, 0.70);

// THE CARTOON EYE (`cartoon_eyes`), the tetra's own: a wide, round, bright little stare (a small
// shoaling fish, all eyes): a big clean white, a huge round pupil, the iris a ring lit along its
// top by the same blue-green as the stripe (it shines a little of itself, as the stripe does) and
// below it the type's own colour (`iris_low`: the neon's silver, the cardinal's red); no lid
// resting on it, a bright highlight that stays put up and forward, a dark outline. The eye is
// drawn EYE_BIG times its size (its dome scaled about its middle).
const float EYE_BIG = 1.3;
const float IRIS_R = 0.66;
const float PUPIL_R = 0.43;
// 0 the eye as it is in life, 1 the cartoon eye.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the cartoon eyes look: x towards the snout (+) or back (-), y up (+) or down (-), -1..1.
uniform vec2 eye_look = vec2(0.0);
// A blink: 0 open, 1 shut (a lid the colour of the skin comes down over the eye).
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 iris_low : source_color = vec3(0.72, 0.74, 0.74);

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

// How far to one side the middle line of the body is (body lengths), `xm` behind the jaw: a wave
// that runs back along it, smallest a little behind the head, growing to the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = 0.008 - 0.03 * s + 0.082 * s * s;
	return sway * reach * sin(6.2831853 * (phase * tail_beats - s * JOINT / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / 0.7;
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
	vec3 v = VERTEX / length_m;
	rest = v;
	float xm = v.z + HALF;
	if (cartoon_eyes > 0.0 && part > 5.5 && part < 6.5) {
		// The cartoon eye: its dome drawn bigger about its middle, a little further out of the head.
		float big = mix(1.0, EYE_BIG, cartoon_eyes);
		vec2 middle = vec2(EYE_AT.y, EYE_AT.x - HALF);
		v.yz = middle + (v.yz - middle) * big;
		v.x += sign(v.x) * (big - 1.0) * 0.042 * 0.3;
		// (grown backwards, onto the wider head behind it: its front edge stays about where it was)
		v.z += (big - 1.0) * 0.042 * 0.8;
		xm = v.z + HALF;
	}
	if (gape > 0.0 && part < 0.5 && inside > 0.999 && UV.y > 0.45 && UV.y < 0.55 && abs(xm - JAW_TO) < 0.0005) {
		// The full model's old wall across the back of the mouth (the foot of it): as the mouth
		// opens it is lifted up out of the way, above the roof of the mouth, so that the throat and
		// the gills behind it show. (The throat's own points are told apart by their UV's y, 0.)
		v = vec3(v.x * 0.55, WALL_UP, v.z + 0.004);
	}
	if (part > 8.5 && part < 9.5) {
		// The gill arches spread a little as the mouth opens.
		float open = clamp(gape, 0.0, 1.0);
		v.x *= 1.0 + 0.1 * open;
		v.z += (xm - 0.5 * (GILL_FROM + GILL_TO)) * 0.15 * open;
		xm = v.z + HALF;
	}
	if (part > 6.5 && part < 7.5) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = clamp(gape, 0.0, 1.0) * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.02, JAW_TO - 0.002, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.003) - side_at(zc - 0.003)) / 0.006;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	vec3 n = vec3(NORMAL.x * c + NORMAL.z * sn, NORMAL.y, -NORMAL.x * sn + NORMAL.z * c);
	curl_bend(v, n);
	VERTEX = v * length_m;
	NORMAL = n;
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return -0.006 - 0.22 * xm;
}

float gill_x(float y) {
	return 0.2 - 9.0 * (y + 0.01) * (y + 0.01);
}

// The middle of the stripe (body lengths up from the middle line) and half its height, `xm` back.
float stripe_y(float xm) {
	return mix(0.03, 0.016, smoothstep(0.1, 0.7, xm));
}

float stripe_half(float xm) {
	return mix(0.019, 0.011, smoothstep(0.15, 0.7, xm));
}

// The cartoon eye at a place on it `e` (x towards the snout, y up; its rim at 1): the white, the
// iris and pupil slid by `eye_look`, a highlight that stays put, a dark outline. `shine` is how
// much of it shines of itself.
vec3 cartoon_eye(vec2 e, vec3 stripe_c, out vec3 shine) {
	float d = length(e);
	vec2 at = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * vec2(0.24, 0.2);
	float r = length(at);
	vec3 c = vec3(0.95, 0.96, 0.94) * mix(1.0, 0.8, smoothstep(0.35, 0.85, d));
	float lit = smoothstep(-0.3, 0.35, at.y);
	vec3 iris = mix(iris_low, stripe_c, lit) * mix(1.15, 0.75, smoothstep(0.1, IRIS_R, r));
	float in_iris = 1.0 - smoothstep(IRIS_R - 0.03, IRIS_R, r);
	c = mix(c, iris, in_iris);
	c = mix(c, iris * 0.3, smoothstep(IRIS_R - 0.11, IRIS_R - 0.03, r) * in_iris);
	c = mix(c, vec3(0.008, 0.01, 0.016), 1.0 - smoothstep(PUPIL_R - 0.03, PUPIL_R, r));
	float spark = max(1.0 - smoothstep(0.12, 0.15, length(e - vec2(0.2, 0.3))), 0.8 * (1.0 - smoothstep(0.05, 0.07, length(e - vec2(-0.14, -0.2)))));
	c = mix(c, vec3(1.0), spark);
	shine = stripe_c * glow * 0.35 * lit * in_iris * smoothstep(PUPIL_R - 0.03, PUPIL_R, r) + vec3(0.5) * spark;
	return mix(c, vec3(0.02, 0.03, 0.03), smoothstep(0.83, 0.9, d));
}

void fragment() {
	int p = int(part + 0.5);
	vec3 n = normalize(NORMAL);
	float facing = clamp(dot(n, normalize(VIEW)), 0.0, 1.0);
	float glance = 1.0 - facing;
	vec3 c;
	vec3 glow_c = vec3(0.0);
	float rough = 0.45;
	float spec = 0.5;
	// (the stripe's colour turns from blue seen face on to green seen glancing)
	vec3 stripe_c = mix(stripe_green, stripe_blue, smoothstep(0.15, 0.85, facing));
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		float behind = xm - gill_x(y);
		float cloud = noise2(vec2(xm * 40.0, y * 60.0));
		// The silver flank, the white belly, the olive back.
		c = mix(belly, silver, smoothstep(-0.75, -0.2, q));
		c += silver * 0.18 * glance * glance;
		float sy = stripe_y(xm);
		float sh = stripe_half(xm);
		float above = smoothstep(sy + sh - 0.002, sy + sh + 0.012, y);
		vec3 top = back * (0.85 + 0.3 * cloud) * mix(1.0, 0.75, smoothstep(0.6, 1.0, q));
		c = mix(c, top, above);
		// (a dark line where the back meets the stripe, and a thin one along the ridge)
		float line_edge = 1.0 - smoothstep(0.0, 0.007, abs(y - (sy + sh + 0.008)));
		c = mix(c, back_dark, line_edge * 0.75 * smoothstep(0.04, 0.1, xm) * (1.0 - smoothstep(stripe_to, stripe_to + 0.08, xm)));
		c = mix(c, back_dark, smoothstep(0.88, 1.0, q) * 0.6);
		// The red: under the stripe from `red_from` back to the tail, down to the belly (only
		// the lowest part of the belly stays pale, and behind the vent it is red to the keel).
		float red_along = smoothstep(red_from - 0.03, red_from + 0.03, xm - (sy - y) * 0.5) * (1.0 - smoothstep(0.80, 0.835, xm));
		float red_top = sy - sh + 0.002;
		float red_low = mix(-0.62, -1.2, smoothstep(0.5, 0.62, xm));
		float reds = red_along * (1.0 - smoothstep(red_top - 0.01, red_top, y)) * smoothstep(red_low - 0.08, red_low + 0.08, q);
		c = mix(c, red * (0.9 + 0.2 * cloud), reds);
		// The stripe: from the snout, through the top of the eye, back to the adipose fin.
		float stripe = (1.0 - smoothstep(sh - 0.004, sh + 0.004, abs(y - sy))) * smoothstep(0.012, 0.04, xm) * (1.0 - smoothstep(stripe_to - 0.04, stripe_to + 0.04, xm));
		c = mix(c, stripe_c * 0.85, stripe);
		glow_c = stripe_c * stripe * glow * (0.35 + 0.65 * facing * facing);
		// The head: the line of the mouth, the gill cover's edge.
		float mouth = (1.0 - smoothstep(0.001, 0.003, abs(y - mouth_y(xm)))) * smoothstep(0.0, 0.004, xm) * (1.0 - smoothstep(MOUTH_TO - 0.006, MOUTH_TO, xm)) * (1.0 - smoothstep(0.0, 0.3, gape));
		c = mix(c, vec3(0.06, 0.05, 0.05), mouth * 0.75);
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.35, 0.55, q));
		float crease = (1.0 - smoothstep(0.0, 0.004, abs(behind - 0.002))) * 0.5;
		c = mix(c, c * 0.45, crease * span);
		rough = mix(0.3, 0.5, above);
		spec = mix(0.6, 0.35, above);
		rough = mix(rough, 0.12, stripe);
		spec = mix(spec, 0.9, stripe);
		// The inside of the mouth.
		c = mix(c, mouth_inside, inside);
		glow_c *= 1.0 - inside;
		rough = mix(rough, 0.8, inside);
		spec = mix(spec, 0.2, inside);
	} else if (p == 6) {
		// An eye: a big black pupil, a silver iris whose top is lit blue-green by the stripe.
		// (the game model's eye, UV y 1, has few points: its rings are drawn round from where it is)
		float r = UV.y > 0.5 ? length(vec2(EYE_AT.x - (rest.z + HALF), rest.y - EYE_AT.y)) / 0.042 : UV.x;
		float up = (rest.y - EYE_AT.y) / 0.042;
		vec3 iris = mix(vec3(0.72, 0.74, 0.74), stripe_c, smoothstep(0.1, 0.5, up) * 0.85);
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.5, 0.57, r));
		c = mix(c, back_dark, smoothstep(0.88, 1.0, r) * 0.8);
		glow_c = stripe_c * glow * 0.5 * smoothstep(0.1, 0.5, up) * smoothstep(0.55, 0.65, r) * (1.0 - smoothstep(0.85, 0.95, r));
		rough = 0.12;
		spec = 0.7;
		if (cartoon_eyes > 0.0 || blink > 0.0) {
			// (on the eye's own face: x towards the snout, y up, its rim at 1)
			vec2 e = vec2(EYE_AT.x - (rest.z + HALF), rest.y - EYE_AT.y) / 0.042;
			if (cartoon_eyes > 0.0) {
				vec3 shine;
				c = mix(c, cartoon_eye(e, stripe_c, shine), cartoon_eyes);
				glow_c = mix(glow_c, shine, cartoon_eyes);
			}
			// The lid: the cartoon eye has none resting on it; `blink` brings it down over the eye.
			float lid = mix(1.3, -1.08, blink);
			float shut = smoothstep(lid - 0.015, lid + 0.015, e.y);
			vec3 skin_c = mix(back, silver, 0.45);
			c = mix(c, skin_c, shut);
			c = mix(c, back_dark, (1.0 - smoothstep(0.02, 0.08, abs(e.y - lid))) * (1.0 - smoothstep(0.95, 1.05, lid)) * 0.8);
			glow_c *= 1.0 - shut;
			rough = mix(rough, 0.45, shut);
			spec = mix(spec, 0.4, shut);
		}
	} else if (p == 9) {
		// A gill arch: its pale rakers at the inner front edge, the red bar, then the fringe of
		// blood-red filaments (fine lines along it), darker deeper in the shadow of the throat.
		float t = UV.x;
		float u = UV.y;
		c = mix(gill_raker, gill_red * 1.3, smoothstep(0.08, 0.22, u));
		c = mix(c, gill_red * 0.8, smoothstep(0.3, 0.45, u));
		c *= mix(1.0, 0.7 + 0.3 * (0.5 + 0.5 * cos(t * 150.0)), smoothstep(0.35, 0.5, u));
		c = mix(c, c * 0.7, (1.0 - smoothstep(0.06, 0.12, u)) * step(0.5, fract(t * 16.0)));
		c *= mix(1.0, 0.45, smoothstep(GILL_FROM - 0.02, GILL_TO, rest.z + HALF));
		rough = 0.35;
		spec = 0.45;
	} else {
		// The fins: clear, with faint rays; the tail a little red at its root.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		c = fin * (0.9 + 0.1 * ray);
		if (p == 3) {
			c = mix(c, red * 0.9, (1.0 - smoothstep(0.0, 0.25, UV.x)) * 0.55);
		} else if (p == 1 || p == 2) {
			// (a pale tip to the dorsal and the front of the anal fin)
			c = mix(c, belly, smoothstep(0.7, 1.0, UV.x) * (1.0 - smoothstep(0.0, 0.4, UV.y)) * 0.6);
		} else if (p == 8) {
			c = mix(back, fin, 0.5);
		}
		rough = 0.5;
		spec = 0.35;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = glow_c;
}
