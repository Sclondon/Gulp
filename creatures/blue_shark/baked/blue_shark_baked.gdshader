shader_type spatial;
// The blue shark (blue_shark.gd): every marking drawn here (no texture files), its swimming
// and its jaws. What each point is comes from the model (tools/build_blue_shark.py): COLOR.r the
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
render_mode cull_back, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// Kept in step with the model (tools/build_blue_shark.py).
const float LENGTH = 3.0;
const float HINGE_S = 0.135;
const float HINGE_Y = -0.033;
const float MOUTH_S = 0.085;
// How far the lower jaw drops at gape 1 (radians), and how far the upper jaw pushes out then (body
// lengths forward, and down).
const float JAW_TURN = 0.72;
const float PUSH = 0.012;
const float PUSH_DOWN = 0.006;

// The gills (added 2026-11-18): how far the arches spread apart as the mouth opens and how far a slit's
// flap lifts at its front edge, wide open (body lengths), and the gills' red.
const float GILL_SPREAD = 0.004;
const float SLIT_LIFT = 0.0068;
const vec3 GILL_RED = vec3(0.62, 0.05, 0.07);

// How far through a beat of its tail (0..1, it wraps). Set by BlueShark.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X). The head stays as it is.
uniform float curl = 0.0;
// How widely it beats: 1 a blue shark cruising (its tail tip swings about 0.3 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;
// The mouth: 0 shut, 1 wide open as when it bites (the lower jaw drops, the upper jaw pushes out).
uniform float gape = 0.0;

// The deep indigo back, the bright blue flanks, the white belly.
uniform vec3 back : source_color = vec3(0.04, 0.07, 0.24);
uniform vec3 flank : source_color = vec3(0.13, 0.36, 0.8);
uniform vec3 belly : source_color = vec3(0.92, 0.93, 0.94);
// The dusky tips of the pectoral fins.
uniform vec3 tip : source_color = vec3(0.05, 0.08, 0.2);
uniform vec3 mouth : source_color = vec3(0.34, 0.1, 0.12);
uniform vec3 tooth : source_color = vec3(0.93, 0.91, 0.84);

// The cartoon eye (added 2026-11-18): 0 the eye as it is, 1 the cartoon eye below.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the cartoon eye looks, -1..1: x towards the nose, y up.
uniform vec2 eye_look = vec2(0.0);
// The lids: 0 open, 1 shut.
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The cartoon eye's character, this animal's own: a blue shark's, big, round and wide open, a
// bright cobalt iris with plenty of white round it and the lids well back, a curious, alert stare.
// Where the eye's dome meets the skin (the right eye's, metres: the build script prints it as
// EYE_MID) and how much bigger the cartoon eye is; the white; the iris (its colour, its rim's, its
// radius on the eye's face, 1 the rim); the pupil's half width and half height; where the
// highlight is; the upper lid's line at the front and the back of the eye and how much it arches;
// the lower lid's line and how much it curves down (on the eye's face: x towards the nose, y up,
// -1..1).
const vec3 EYE_MID = vec3(0.0946, 0.0270, -1.2780);
const float EYE_GROW = 1.6;
const vec3 SCLERA = vec3(0.95, 0.96, 0.97);
const vec3 IRIS = vec3(0.12, 0.34, 0.85);
const vec3 IRIS_RIM = vec3(0.03, 0.07, 0.3);
const float IRIS_R = 0.58;
const vec2 PUPIL = vec2(0.3, 0.3);
const vec2 HIGHLIGHT = vec2(0.26, 0.3);
const vec2 BROW = vec2(0.84, 0.76);
const float BROW_ARCH = 0.12;
const vec2 LOWER_LID = vec2(-0.86, 0.0);

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
	float reach = 0.014 * (1.0 - smoothstep(0.0, 0.3, s)) + 0.005 + 0.09 * pow(rear, 1.5);
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
	bake_uv = CUSTOM0.xy;

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

// The five gill slits: where each is along the fish; from how high to how high (as the model's
// GILLS); 1 on a slit's dark line.
float gills(float s, float h) {
	float on = 0.0;
	for (int i = 0; i < 5; i++) {
		float at = 0.205 + 0.01075 * float(i);
		float top = 0.62 - 0.03 * float(i) * float(i) / 4.0;
		float lean = at + 0.012 * (h - 0.5) - 0.02 * (h - 0.48) * (h - 0.48);
		float line = 1.0 - smoothstep(0.0004, 0.0011, abs(s - lean));
		on = max(on, line * smoothstep(0.31, 0.34, h) * (1.0 - smoothstep(top - 0.03, top, h)));
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
	c = mix(c, flank, lid);
	return vec4(c, lid);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

