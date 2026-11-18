shader_type spatial;
// The leopard shark (leopard_shark.gd): every marking drawn here (no texture files), its swimming
// and its jaws. What each point is comes from the model (tools/build_leopard_shark.py): COLOR.r the
// part, as a twentieth (0 body, 1 lower jaw, 2 eye, 3 upper tooth, 4 lower tooth, 5 first dorsal,
// 6 second dorsal, 7 tail, 8 anal fin, 9 pelvic fin, 10 pectoral fin, 11 cheek, 12 gill arch, 13 gill slit's flap: see
// the build script); COLOR.g how much
// a point goes with the upper jaw when it pushes out; COLOR.b how much it is inside the mouth. On
// the body and the jaw UV.x is how far along the fish (0 snout, 1 tail tip) and UV.y how high on
// it (0 the line under the belly and chin, 1 the back line). On a fin UV.x is root (0) to edge (1)
// and UV.y along its outline; on an eye UV is where on its round face; on a cheek UV.x is 0 at its
// top edge and 1 at its lower edge (which goes with the jaw).
//
// It swims as sharks do: a wave down the whole rear of the body that grows towards the tail, the
// head swinging a little, the tail sweeping wide. All of it is a function of `phase` alone, so a
// picture of it loops exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model (tools/build_leopard_shark.py).
const float LENGTH = 1.5;
const float HINGE_S = 0.09;
const float HINGE_Y = -0.029;
const float MOUTH_S = 0.045;
// How far the lower jaw drops at gape 1 (radians), and how far the upper jaw pushes out then (body
// lengths forward, and down).
const float JAW_TURN = 0.62;
const float PUSH = 0.008;
const float PUSH_DOWN = 0.005;

// The gills (added 2026-11-18): how far the arches spread apart as the mouth opens and how far a slit's
// flap lifts at its front edge, wide open (body lengths), and the gills' red.
const float GILL_SPREAD = 0.004;
const float SLIT_LIFT = 0.0068;
const vec3 GILL_RED = vec3(0.62, 0.05, 0.07);

// How far through a beat of its tail (0..1, it wraps). Set by LeopardShark.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X). The head stays as it is.
uniform float curl = 0.0;
// How widely it beats: 1 a leopard shark cruising (its tail tip swings about 0.12 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;
// The mouth: 0 shut, 1 wide open as when it bites (the lower jaw drops, the upper jaw pushes out).
uniform float gape = 0.0;

// The silver-bronze back and flanks, the black saddles and spots, the pale belly, the eye.
uniform vec3 back : source_color = vec3(0.5, 0.46, 0.39);
uniform vec3 saddle : source_color = vec3(0.025, 0.022, 0.02);
uniform vec3 belly : source_color = vec3(0.86, 0.84, 0.79);
uniform vec3 iris : source_color = vec3(0.45, 0.5, 0.36);
uniform vec3 mouth : source_color = vec3(0.32, 0.08, 0.09);
uniform vec3 tooth : source_color = vec3(0.93, 0.91, 0.84);

// The cartoon eye (added 2026-11-18): 0 the eye as it is, 1 the cartoon eye below.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the cartoon eye looks, -1..1: x towards the nose, y up.
uniform vec2 eye_look = vec2(0.0);
// The lids: 0 open, 1 shut.
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The cartoon eye's character, this animal's own: a leopard shark's, a cat's eye, a green-gold
// iris filling it with an upright slit of a pupil, narrowed by both lids into a sly, lazy squint.
// Where the eye's dome meets the skin (the right eye's, metres: the build script prints it as
// EYE_MID) and how much bigger the cartoon eye is; the white; the iris (its colour, its rim's, its
// radius on the eye's face, 1 the rim); the pupil's half width and half height; where the
// highlight is; the upper lid's line at the front and the back of the eye and how much it arches;
// the lower lid's line and how much it curves down (on the eye's face: x towards the nose, y up,
// -1..1).
const vec3 EYE_MID = vec3(0.0673, 0.0255, -0.6660);
const float EYE_GROW = 1.9;
const vec3 SCLERA = vec3(0.9, 0.88, 0.8);
const vec3 IRIS = vec3(0.55, 0.6, 0.27);
const vec3 IRIS_RIM = vec3(0.22, 0.26, 0.1);
const float IRIS_R = 0.8;
const vec2 PUPIL = vec2(0.1, 0.6);
const vec2 HIGHLIGHT = vec2(0.3, 0.12);
const vec2 BROW = vec2(0.5, 0.56);
const float BROW_ARCH = 0.1;
const vec2 LOWER_LID = vec2(-0.6, -0.04);

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying vec2 extra;

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

// How far to one side the middle line is at `s` (body lengths): a wave running back along it,
// small at the head, least behind the gills, growing to the tail.
float side_at(float s) {
	float rear = max(s - 0.18, 0.0) / 0.82;
	float reach = 0.016 * (1.0 - smoothstep(0.0, 0.3, s)) + 0.006 + 0.075 * pow(rear, 1.4);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

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

// Turns a point and its normal about the jaw's hinge (in the fish's middle plane) by `a`.
void hinge_turn(inout vec3 v, inout vec3 n, float a) {
	vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5) * LENGTH;
	vec2 d = v.yz - hinge;
	float c = cos(a);
	float sn = sin(a);
	v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
}

void vertex() {
	part = floor(COLOR.r * 20.0 + 0.5);
	extra = COLOR.gb;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	// The cartoon eye: the eye's dome grown about where it meets the skin.
	if (part > 1.5 && part < 2.5) {
		vec3 mid = vec3(sign(v.x) * EYE_MID.x, EYE_MID.y, EYE_MID.z);
		v = mid + (v - mid) * mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
	}
	float open = clamp(gape, 0.0, 1.0);
	float s = v.z / LENGTH + 0.5;
	// The jaws: the lower jaw (and its teeth) swings down about its hinge, the throat behind it
	// staying; the cheeks' lower edges go with it; the upper jaw pushes out and down.
	if (part > 0.5 && part < 1.5) {
		hinge_turn(v, n, open * JAW_TURN * smoothstep(HINGE_S + 0.045, HINGE_S - 0.02, s));
	} else if (part > 3.5 && part < 4.5) {
		hinge_turn(v, n, open * JAW_TURN);
	} else if (part > 10.5 && part < 12.5) {
		// (a cheek; or a gill arch, which spreads from the next a little as it opens)
		if (part > 11.5) {
			v.z += open * GILL_SPREAD * LENGTH * (UV.y - 0.5);
		}
		hinge_turn(v, n, open * JAW_TURN * UV.x);
	} else if (part > 12.5) {
		// (a gill slit's flap: its front edge lifts out through the skin as the mouth opens)
		vec3 outward = normalize(vec3(v.x, 0.6 * v.y, 0.0));
		v += outward * smoothstep(0.1, 1.0, open) * SLIT_LIFT * LENGTH * COLOR.b;
	}
	v.z -= COLOR.g * open * PUSH * LENGTH;
	v.y -= COLOR.g * open * PUSH_DOWN * LENGTH;
	// The swimming: each cross-section moved to the wave's line and turned square to it.
	float h = side_at(s) * LENGTH;
	float slope = (side_at(s + 0.002) - side_at(s - 0.002)) / 0.004;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.8, 0.95, s));
	float c = cos(turn);
	float sn = sin(turn);
	v = vec3(h + v.x * c, v.y, v.z - v.x * sn);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The leopard's markings on the body: 1 on a black saddle or spot. Narrow saddles with rounded
// ends cross the back about every 0.06 of its length from behind the eyes to the tail (the wider
// ones at the front paler in the middle); round spots scatter over the upper flanks and between.
float marks(float s, float h) {
	float k = (s - 0.1) / 0.06;
	float cell = floor(k + 0.5);
	float d = (k - cell) * 0.06;
	float wob = 0.004 * (noise2(vec2(s * 90.0, h * 7.0 + cell * 3.1)) - 0.5);
	float half_w = mix(0.0085, 0.005, smoothstep(0.2, 0.85, s)) * (0.75 + 0.5 * hash2(vec2(cell, 1.0)));
	float reach = 0.6 + 0.12 * hash2(vec2(cell, 2.0));
	// (rounded at its lower end)
	float wide = half_w * sqrt(clamp((h - reach) / 0.07, 0.0, 1.0));
	float across = abs(d + wob);
	float band = (1.0 - smoothstep(wide - 0.0012, wide + 0.0012, across)) * smoothstep(reach + 0.004, reach + 0.02, h);
	float pale = step(0.0075, half_w) * (1.0 - smoothstep(0.3, 0.45, across / max(half_w, 1e-4))) * smoothstep(reach + 0.06, reach + 0.12, h) * (1.0 - smoothstep(0.88, 0.95, h));
	band *= 1.0 - 0.6 * pale;
	band *= smoothstep(0.085, 0.1, s) * (1.0 - smoothstep(0.93, 0.97, s));
	// the spots: one or none in each small cell, off-centre
	vec2 g = vec2(s * 55.0, h * 8.0);
	vec2 id = floor(g);
	vec2 at = id + 0.3 + 0.4 * vec2(hash2(id + 7.0), hash2(id + 13.0));
	float r = 0.17 + 0.1 * hash2(id + 21.0);
	float spot = (1.0 - smoothstep(r - 0.05, r + 0.05, length((g - at) * vec2(1.0, 1.25)))) * step(0.45, hash2(id + 31.0));
	spot *= smoothstep(0.3, 0.36, h) * smoothstep(0.08, 0.11, s) * (1.0 - smoothstep(0.85, 0.9, s));
	return max(band, spot);
}
// The five gill slits: where each is along the fish; from how high to how high (as the model's
// GILLS); 1 on a slit's dark line.
float gills(float s, float h) {
	float on = 0.0;
	for (int i = 0; i < 5; i++) {
		float at = 0.135 + 0.0085 * float(i);
		float top = 0.64 - 0.03 * float(i) * float(i) / 4.0;
		float lean = at + 0.008 * (h - 0.5) - 0.012 * (h - 0.48) * (h - 0.48);
		float line = 1.0 - smoothstep(0.0005, 0.0012, abs(s - lean));
		on = max(on, line * smoothstep(0.35, 0.38, h) * (1.0 - smoothstep(top - 0.03, top, h)));
	}
	return on;
}

// The eye's face, `real` the eye as it is: with cartoon_eyes the cartoon eye (a white, the iris
// and pupil slid by eye_look, a highlight that stays put, a dark outline, the lids of its
// character), and with blink the lids closing over it.
vec4 eye_face(vec3 real, vec2 uv) {
	// (on the eye's face: x towards the nose, y up, 1 out at its rim)
	vec2 e = vec2(uv.y - 0.5, uv.x - 0.5) * 2.0;
	float r = length(e);
	float k = clamp(cartoon_eyes, 0.0, 1.0);
	vec2 q = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.9 - IRIS_R);
	float qi = length(q) / IRIS_R;
	vec3 toon = SCLERA * mix(1.0, 0.78, smoothstep(0.4, 0.95, r));
	vec3 iris_c = mix(IRIS * (1.0 + 0.4 * noise2(q * 7.0 + 3.0)), IRIS_RIM, smoothstep(0.55, 1.0, qi));
	toon = mix(toon, iris_c, 1.0 - smoothstep(0.95, 1.05, qi));
	float qp = length(q / PUPIL);
	toon = mix(toon, vec3(0.008), 1.0 - smoothstep(0.9, 1.1, qp));
	// (the highlight stays put, up towards the light, whichever way the eye looks)
	toon = mix(toon, vec3(1.0), 1.0 - smoothstep(0.1, 0.15, length(e - HIGHLIGHT)));
	toon = mix(toon, vec3(1.0), 0.75 * (1.0 - smoothstep(0.035, 0.06, length(e - HIGHLIGHT * vec2(-0.6, -1.0)))));
	toon = mix(toon, vec3(0.01), smoothstep(0.83, 0.9, r));
	vec3 c = mix(real, toon, k);
	// The lids, the colour of its skin: for the cartoon eye the upper one along its brow (slanting
	// and arched) and the lower one curved; both close to meet a little under the middle as it
	// blinks, a dark line along each edge.
	float b = clamp(blink, 0.0, 1.0);
	float arch = 1.0 - e.x * e.x;
	float top = mix(mix(1.2, mix(BROW.y, BROW.x, e.x * 0.5 + 0.5) + BROW_ARCH * arch, k), -0.15, b);
	float bottom = mix(mix(-1.2, LOWER_LID.x - LOWER_LID.y * arch, k), -0.15, b);
	float lid_line = max(e.y - top, bottom - e.y);
	float on = step(0.001, max(k, b));
	c = mix(c, vec3(0.01), (1.0 - smoothstep(0.05, 0.1, abs(lid_line))) * on * (1.0 - smoothstep(0.85, 1.0, r)));
	float lid = smoothstep(0.05, 0.1, lid_line) * on;
	c = mix(c, back, lid);
	return vec4(c, lid);
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.6;
	float spec = 0.35;
	float up = rest_normal.y;
	if (p == 0 || p == 1 || p == 13) {
		float s = UV.x;
		float h = UV.y;
		float grain = noise2(vec2(s * 150.0, h * 24.0));
		// Silver-bronze above, fading to the pale belly low on the flank.
		vec3 top = back * (0.9 + 0.2 * noise2(vec2(s * 30.0, h * 5.0)));
		top = mix(top, top * vec3(1.05, 1.06, 1.1), smoothstep(0.6, 0.35, h));
		c = mix(belly, top, smoothstep(0.24, 0.36, h + 0.02 * (noise2(vec2(s * 50.0, 3.0)) - 0.5)));
		c *= 0.975 + 0.035 * grain;
		// Black saddles across the back (the wider ones at the front split by a paler middle) and
		// black spots on the flanks between them.
		c = mix(c, saddle, marks(s, h) * 0.92);
		if (p == 0) {
			c = mix(c, c * 0.3, gills(s, h) * 0.85);
			// (the pores on the snout)
			float pore = 1.0 - smoothstep(0.25, 0.45, length(fract(vec2(s * 900.0, h * 70.0)) - 0.5));
			c = mix(c, c * 0.75, pore * step(0.7, hash2(floor(vec2(s * 900.0, h * 70.0)))) * (1.0 - smoothstep(0.04, 0.065, s)) * smoothstep(0.35, 0.55, h) * 0.6);
		}
		// Inside the mouth.
		float inside = smoothstep(0.3, 0.7, extra.y) * float(p != 13);
		c = mix(c, mouth * mix(1.0, 0.45, smoothstep(MOUTH_S, HINGE_S + 0.01, s)), inside);
		rough = mix(0.62, 0.4, inside);
	} else if (p == 2) {
		// The eye: a green-gold iris, an upright slit of a pupil, a dark ring.
		float r = length(UV - vec2(0.5)) * 2.0;
		c = iris * (0.8 + 0.3 * noise2(UV * 30.0));
		float slit = 1.0 - smoothstep(0.1, 0.16, abs(UV.y - 0.5) * 2.0 / max(1.0 - pow(abs(UV.x - 0.5) * 2.0, 2.0), 0.05));
		c = mix(c, vec3(0.01), slit);
		c = mix(c, back * 0.25, smoothstep(0.8, 1.0, r));
		rough = 0.12;
		spec = 0.7;
	} else if (p == 3 || p == 4) {
		c = mix(tooth * 0.75, tooth, smoothstep(0.0, 0.5, UV.x));
		rough = 0.3;
		spec = 0.55;
	} else if (p == 11) {
		// A cheek: skin outside, the mouth inside.
		float outward = rest_normal.x * sign(rest.x);
		c = mix(mouth * 0.6, belly, smoothstep(-0.2, 0.2, outward));
	} else {
		// A fin: bronze, with black bars on the dorsal fins and bands across the tail, a few spots
		// on the pectorals; pale beneath the paired fins and on the anal fin.
		c = back * (0.92 + 0.14 * noise2(UV * vec2(8.0, 30.0)));
		float dark = 0.0;
		if (p == 5 || p == 6) {
			dark = (1.0 - smoothstep(0.08, 0.12, abs(UV.y - 0.45 + 0.1 * UV.x))) * smoothstep(0.1, 0.25, UV.x);
			dark = max(dark, smoothstep(0.82, 0.95, UV.x) * 0.6);
		} else if (p == 7) {
			float lane = fract(rest.z / LENGTH * 16.0 + 0.3);
			dark = (1.0 - smoothstep(0.12, 0.18, abs(lane - 0.5))) * smoothstep(0.05, 0.2, UV.x);
		} else if (p == 10) {
			vec2 g = UV * vec2(6.0, 12.0);
			vec2 id = floor(g);
			dark = (1.0 - smoothstep(0.14, 0.2, length(fract(g) - 0.5))) * step(0.6, hash2(id + 3.0)) * smoothstep(0.15, 0.3, UV.x);
		}
		c = mix(c, saddle, dark * 0.9);
		if (p == 10 || p == 9) {
			c = mix(c, belly * 0.95, smoothstep(0.1, -0.1, up));
		}
		if (p == 8) {
			c = mix(c, belly, 0.6);
		}
	}
	// The gills: a slit's flap is skin, red at its lifted front edge; an arch is a pinkish bar, a fringe of
	// deep red filaments behind it and pale rakers in front, darker the further back in the throat it is.
	if (p == 13) {
		c = mix(c, GILL_RED * 0.75, smoothstep(0.55, 0.75, extra.y));
	} else if (p == 12) {
		float stripe = 0.72 + 0.28 * step(0.5, fract(abs(UV2.x) * 22.0));
		c = mix(vec3(0.86, 0.8, 0.74), vec3(0.7, 0.24, 0.26), smoothstep(0.25, 0.4, extra.y));
		c = mix(c, GILL_RED * stripe, smoothstep(0.6, 0.8, extra.y));
		c *= mix(1.0, 0.45, UV.y);
		rough = 0.35;
		spec = 0.5;
	}
	if (p == 2) {
		vec4 eye = eye_face(c, UV);
		c = eye.rgb;
		rough = mix(rough, 0.6, eye.a);
		spec = mix(spec, 0.35, eye.a);
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
