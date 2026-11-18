shader_type spatial;
// The whale shark (whale_shark.gd): every marking drawn here (no texture files), its swimming
// and its jaws. What each point is comes from the model (tools/build_whale_shark.py): COLOR.r the
// part, as a twentieth (0 body, 1 lower jaw, 2 eye, (3 and 4, teeth, not on this model), 5 first dorsal,
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

// Kept in step with the model (tools/build_whale_shark.py).
const float LENGTH = 10.0;
const float HINGE_S = 0.058;
const float HINGE_Y = -0.03;
const float MOUTH_S = 0.0;
// How far the lower jaw drops at gape 1 (radians); how far the upper lip moves then, in its middle
// (body lengths forward, and down: less than 0, so it lifts); how far the lower lip bows down in its
// middle. Together they open the mouth into a great oval.
const float JAW_TURN = 0.6;
const float PUSH = 0.003;
const float PUSH_DOWN = -0.03;
const float BOW = 0.02;
// How wide the lower jaw is at its widest (half, body lengths), as the model has it.
const float JAW_HALF = 0.066;

// The gills (added 2026-11-18): how far the arches spread apart as the mouth opens and how far a slit's
// flap lifts at its front edge, wide open (body lengths), and the gills' red.
const float GILL_SPREAD = 0.004;
const float SLIT_LIFT = 0.0085;
const vec3 GILL_RED = vec3(0.62, 0.05, 0.07);

// How far through a beat of its tail (0..1, it wraps). Set by WhaleShark.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X). The head stays as it is.
uniform float curl = 0.0;
// How widely it beats: 1 a whale shark cruising, slow and wide (its tail tip swings about 0.9 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.1;
// The mouth: 0 shut, 1 wide open as when it feeds, straining the water (a great oval).
uniform float gape = 0.0;

// The grey-blue back, its pale spots and bars, the white belly.
uniform vec3 back : source_color = vec3(0.19, 0.26, 0.33);
uniform vec3 spots : source_color = vec3(0.82, 0.85, 0.84);
// How strongly the spots and bars show.
uniform float spots_show = 0.85;
uniform vec3 belly : source_color = vec3(0.88, 0.89, 0.87);
uniform vec3 mouth : source_color = vec3(0.3, 0.2, 0.22);

// The cartoon eye (added 2026-11-18): 0 the eye as it is, 1 the cartoon eye below.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the cartoon eye looks, -1..1: x towards the nose, y up.
uniform vec2 eye_look = vec2(0.0);
// The lids: 0 open, 1 shut.
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The cartoon eye's character, this animal's own: a whale shark's, a gentle giant's, a small soft
// eye made big, a warm grey-brown iris and a round pupil under a heavy, drooping upper lid, sleepy
// and kind. Where the eye's dome meets the skin (the right eye's, metres: the build script prints it
// as EYE_MID) and how much bigger the cartoon eye is; the white; the iris (its colour, its rim's, its
// radius on the eye's face, 1 the rim); the pupil's half width and half height; where the
// highlight is; the upper lid's line at the front and the back of the eye and how much it arches;
// the lower lid's line and how much it curves down (on the eye's face: x towards the nose, y up,
// -1..1).
const vec3 EYE_MID = vec3(0.7629, 0.0600, -4.3800);
const float EYE_GROW = 2.4;
const vec3 SCLERA = vec3(0.92, 0.9, 0.86);
const vec3 IRIS = vec3(0.36, 0.3, 0.24);
const vec3 IRIS_RIM = vec3(0.1, 0.08, 0.07);
const float IRIS_R = 0.62;
const vec2 PUPIL = vec2(0.33, 0.33);
const vec2 HIGHLIGHT = vec2(0.28, -0.05);
const vec2 BROW = vec2(0.16, 0.2);
const float BROW_ARCH = 0.16;
const vec2 LOWER_LID = vec2(-0.62, -0.1);

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
	float reach = 0.012 * (1.0 - smoothstep(0.0, 0.3, s)) + 0.004 + 0.085 * pow(rear, 1.6);
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
		v.y -= open * BOW * LENGTH * max(0.0, 1.0 - pow(v.x / (JAW_HALF * LENGTH), 2.0)) * smoothstep(HINGE_S, HINGE_S - 0.03, s);
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

// Pale spots on a grid of cells `size` metres across, one in each cell, a little off its middle;
// with `bars`, thin pale bars between the columns of spots too.
float spotted(vec2 at, float size, float bars) {
	vec2 g = at / size;
	g.x += 0.06 * sin(g.y * 1.3 + floor(g.x) * 2.1);
	vec2 id = floor(g);
	vec2 f = fract(g) - 0.5 - (vec2(hash2(id + 1.0), hash2(id + 5.0)) - 0.5) * 0.22;
	float r = mix(0.17, 0.25, hash2(id + 9.0));
	float spot = 1.0 - smoothstep(r - 0.05, r + 0.05, length(f));
	float edge = 0.5 - abs(fract(g.x) - 0.5);
	float bar = (1.0 - smoothstep(0.03, 0.065, edge)) * (0.5 + 0.5 * step(0.12, hash2(vec2(id.x, floor(g.y / 3.0)))));
	return max(spot, bar * bars * 0.8);
}

// The whale shark's pale markings on the body, 1 on a spot, a bar or a ridge's line: `s` along it,
// `h` how high, `girth` metres round the skin from the back line. Small close spots on the head,
// bigger ones between bars behind it (two grids, so that neither is stretched where they meet).
float pattern(float s, float h, float girth) {
	vec2 at = vec2(s * LENGTH, girth);
	float head = 1.0 - smoothstep(0.11, 0.16, s);
	float pale = mix(spotted(at, 0.26, 1.0), spotted(at + 3.0, 0.1, 0.0), head);
	float lines = 0.0;
	for (int i = 0; i < 3; i++) {
		float on = i == 0 ? 0.84 : (i == 1 ? 0.67 : 0.51);
		lines = max(lines, 1.0 - smoothstep(0.005, 0.012, abs(h - on)));
	}
	lines *= smoothstep(0.16, 0.24, s) * (1.0 - smoothstep(0.7, 0.8, s)) * 0.7;
	float fade = 1.0 - smoothstep(0.86, 0.95, s);
	return max(pale, lines) * fade * smoothstep(0.004, 0.012, s);
}
// The five gill slits: where each is along the fish; from how high to how high (as the model's
// GILLS); 1 on a slit's dark line.
float gills(float s, float h) {
	float on = 0.0;
	for (int i = 0; i < 5; i++) {
		float at = 0.135 + 0.017 * float(i);
		float top = 0.82 - 0.03 * float(i) * float(i) / 4.0;
		float lean = at + 0.01 * (h - 0.5) - 0.02 * (h - 0.48) * (h - 0.48);
		float line = 1.0 - smoothstep(0.0005, 0.0012, abs(s - lean));
		on = max(on, line * smoothstep(0.15 + 0.02 * float(i), 0.18 + 0.02 * float(i), h) * (1.0 - smoothstep(top - 0.03, top, h)));
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
		// Grey-blue above, white beneath, a soft line between low on the flank.
		vec3 top = back * (0.9 + 0.2 * noise2(vec2(s * 20.0, h * 4.0)));
		c = mix(belly, top, smoothstep(0.24, 0.34, h + 0.03 * (noise2(vec2(s * 40.0, 2.0)) - 0.5)));
		c *= 0.975 + 0.035 * grain;
		// The checkerboard: pale spots in columns between thin pale bars across the back and flanks,
		// smaller spots and no bars on the head; pale lines along the ridges.
		float pale = pattern(s, h, abs(UV2.x));
		c = mix(c, spots, pale * spots_show * smoothstep(0.22, 0.34, h));
		if (p == 0) {
			c = mix(c, back * 0.3, gills(s, h) * 0.8);
		}
		// Inside the mouth.
		float inside = smoothstep(0.3, 0.7, extra.y) * float(p != 13);
		vec3 in_mouth = mouth * mix(1.0, 0.4, smoothstep(MOUTH_S, HINGE_S + 0.01, s));
		// (the grey filter pads at the back of the mouth, ridged across)
		float pads = smoothstep(HINGE_S - 0.035, HINGE_S - 0.015, s) * (0.5 + 0.5 * cos(rest.x / LENGTH * 900.0));
		in_mouth = mix(in_mouth, vec3(0.16, 0.16, 0.17), pads * 0.8);
		c = mix(c, in_mouth, inside);
		rough = mix(0.62, 0.4, inside);
	} else if (p == 2) {
		// The eye: small and dark, a pale ring round it.
		float r = length(UV - vec2(0.5)) * 2.0;
		c = mix(vec3(0.006, 0.007, 0.009), vec3(0.45, 0.47, 0.46), smoothstep(0.62, 0.72, r));
		c = mix(c, back, smoothstep(0.85, 1.0, r));
		rough = 0.12;
		spec = 0.7;

	} else if (p == 11) {
		// A cheek: the lining of the mouth on both faces, a little darker inside.
		float outward = rest_normal.x * sign(rest.x);
		c = mix(mouth * 0.6, mix(mouth * 1.3, back, 0.35), smoothstep(-0.2, 0.2, outward));
	} else {
		// A fin: grey-blue, spotted pale; white beneath the paired fins.
		c = back * (0.92 + 0.14 * noise2(UV * vec2(8.0, 30.0)));
		vec2 g = vec2(rest.z, length(rest.xy)) / 0.2;
		vec2 id = floor(g);
		float spot = (1.0 - smoothstep(0.16, 0.24, length(fract(g) - 0.5 - (vec2(hash2(id + 2.0), hash2(id + 6.0)) - 0.5) * 0.3))) * step(0.3, hash2(id + 11.0));
		c = mix(c, spots, spot * spots_show * 0.8 * smoothstep(0.05, 0.2, UV.x));
		c *= mix(1.0, 0.85, smoothstep(0.8, 1.0, UV.x));
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
