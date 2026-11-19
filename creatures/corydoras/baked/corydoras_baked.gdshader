shader_type spatial;
// The cory catfish (corydoras.gd): every marking drawn here (no texture files), for the bronze cory and the
// panda (corydoras.gd sets the colours of each), and its swimming. What each point is comes from the model
// (tools/build_corydoras.py): UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
// pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a barbel, 9 the adipose fin). UV2.x: 1 inside
// the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its side (1 the ridge of
// the back, 0 the middle of the belly); on a fin: x root (0) to edge (1), y leading edge (0) to trailing edge
// (1); on an eye: x middle (0) to rim (1); on a barbel: x root to tip.
//
// It swims by a wave down the back half of its body (subcarangiform), its stiff armoured front nearly still,
// the forked tail carried round behind its wrist. All of it is a function of `phase` alone, so a picture of it
// loops exactly. The mouth (under the snout) opens: `gape`. Nothing here needs more than GL Compatibility has.
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


// Kept in step with the model (the build script prints them).
const float LENGTH = 0.06;
const float HALF = 0.03;
const float JOINT = 0.0462;
const float JAW_TO = 0.0036;
const float HINGE_Y = -0.0048;
const vec2 EYE_AT = vec2(0.0064, 0.0036);
const float GILL_AT = 0.0108;
const float GAPE_OPEN = 0.9;
const float PROTRUDE = 0.0003;
// The plates (as the build script has them): where they begin and end, how long each is.
const float PLATE_FROM = 0.0115;
const float PLATE_TO = 0.0465;
const float PLATE_LONG = 0.00155;
// Where the dorsal fin stands on the back (for the panda's dark saddle under it).
const vec2 DORSAL_AT = vec2(0.0145, 0.023);

uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats, for 1 as a cory swimming along.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The colours (corydoras.gd's KINDS sets them for each kind). The body; its back and head; the belly; the
// sheen where light glances off the plates (green on a bronze cory); the dark marks (the panda's eye mask,
// saddle and tail spot: 0 none); the plates' edges; the fins.
uniform vec3 body : source_color = vec3(0.58, 0.43, 0.22);
uniform vec3 back : source_color = vec3(0.4, 0.31, 0.15);
uniform vec3 belly : source_color = vec3(0.88, 0.8, 0.66);
uniform vec3 sheen : source_color = vec3(0.2, 0.5, 0.36);
uniform float sheen_amount = 0.9;
uniform vec3 mark : source_color = vec3(0.03, 0.03, 0.035);
uniform float mask_amount = 0.0;
uniform float saddle_amount = 0.0;
uniform float tail_spot_amount = 0.0;
uniform float plates_show = 0.6;
uniform vec3 fin : source_color = vec3(0.68, 0.64, 0.54);
uniform vec3 fin_edge : source_color = vec3(0.86, 0.84, 0.78);
uniform vec3 barbel_colour : source_color = vec3(0.8, 0.72, 0.58);
uniform vec3 iris : source_color = vec3(0.7, 0.55, 0.25);
uniform vec3 mouth_inside : source_color = vec3(0.35, 0.12, 0.12);

// Cartoon eyes (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0, the default, is the eye drawn below, as it always was; 1 the cartoon eye: grown about
// its middle, a white, an iris, a round pupil, a highlight that stays put (up and forward, towards the light)
// and a dark rim, under an upper lid the colour of its head. The cory's: friendly, contented and a little
// sleepy: a big soft dark pupil in its own bronze iris (`iris`, set by its kind), the lid half down and
// drooping a little towards the back, as if it were about to give its famous wink.
uniform float cartoon_eyes = 0.0;
// Where the cartoon eye looks, -1..1 each way: x towards the nose (+) or the tail, y up (+) or down.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat from above and below (a fish has no lids) and the lid comes down.
uniform float blink = 0.0;
// How much bigger the cartoon eye is; how far its grown rim sinks back towards the skin (up and down, along);
// its white; how wide its iris is (of the eye's face) and its pupil (of the iris); where the upper lid's edge
// rests (1 the top of the eye: no lid) and how much lower it comes at the front (less than 0 raises it there).
uniform float eye_grow = 1.5;
uniform vec2 eye_sink = vec2(75.0, 15.0);
uniform vec3 eye_white : source_color = vec3(0.97, 0.96, 0.92);
uniform float iris_size = 0.66;
uniform float pupil_size = 0.7;
uniform float lid = 0.5;
uniform float lid_slant = -0.15;
// As the model has it (the build script's EYE line): the left eye's middle on the skin and the way it faces
// (the right eye is its mirror), and its radius over the skin.
const vec3 EYE_MIDDLE = vec3(0.00499, 0.0036, -0.0236);
const vec3 EYE_OUT = vec3(0.8194, 0.4205, -0.3896);
const float EYE_RADIUS = 0.0016;

// The gills (added 2026-11-18; the user: "The fish need modeled gills as well, ... so like when it opens its
// mouth wide you can see them"): four arches a side in the throat behind the mouth, seen through it when it is
// open (closed in, they are not seen at all). As the model has them (the build script's GILLS line): the gap
// between two arches and where the throat ends. Their red, and their rakers' pale.
const float GILL_GAP = 0.00125;
const float THROAT_END = 0.0119;
uniform vec3 gill_red : source_color = vec3(0.66, 0.05, 0.07);
uniform vec3 gill_raker : source_color = vec3(0.9, 0.66, 0.62);

varying vec3 rest;
varying float part;
varying float inside;

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.006 - 0.03 * s + 0.09 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
}

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

// The cartoon eye grown about its middle, and squashed from above and below as it blinks (nothing moves
// while cartoon_eyes and blink are 0).
void eye_shape(inout vec3 v) {
	if (cartoon_eyes <= 0.0 && blink <= 0.0) {
		return;
	}
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	vec3 at = vec3(EYE_MIDDLE.x * side_is, EYE_MIDDLE.yz);
	vec3 o = normalize(vec3(EYE_OUT.x * side_is, EYE_OUT.yz));
	vec3 up = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
	vec3 d = v - at;
	float grow = mix(1.0, eye_grow, cartoon_eyes);
	// (grown across and outward; what lies behind its face is not pushed further in; the grown rim sinks
	// back as the head's skin falls away round it)
	float deep = min(dot(d, o), 0.0);
	vec3 across = d - o * dot(d, o);
	vec3 up_d = up * dot(across, up);
	float before = eye_sink.x * dot(up_d, up_d) + eye_sink.y * dot(across - up_d, across - up_d);
	d = (d - o * deep) * grow + o * deep;
	d -= o * before * (grow * grow - 1.0);
	d -= up * dot(d, up) * 0.85 * blink;
	v = at + d;
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	inside = UV2.x;
	vec3 v = VERTEX;
	float xm = v.z + HALF;
	float g = clamp(gape, 0.0, 1.0);
	if (part > 5.5 && part < 6.5) {
		eye_shape(v);
		xm = v.z + HALF;
	}
	// The gill arches spread a little apart as the mouth opens.
	if (part > 9.5) {
		v.z += g * 0.14 * GILL_GAP * (floor(UV.y) - 1.5);
		xm = v.z + HALF;
	}
	// The mouth pushes forward and down a little as it opens (the barbels go with the upper lip).
	if ((part < 0.5 || (part > 6.5 && part < 8.5)) && xm < JAW_TO + 0.003 * step(7.5, part)) {
		float w = 1.0 - smoothstep(0.3 * JAW_TO, JAW_TO, xm);
		w = part > 7.5 ? 1.0 - smoothstep(0.5 * JAW_TO, 1.4 * JAW_TO, xm) : w;
		v.z -= g * PROTRUDE * w;
		xm = v.z + HALF;
	}
	if (part > 6.5 && part < 7.5) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = g * GAPE_OPEN * (1.0 - smoothstep(0.55 * JAW_TO, 0.97 * JAW_TO, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0002) - side_at(zc - 0.0002)) / 0.0004;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.85 * JOINT, JOINT, zc));
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

// The panda's dark marks at a place on the body (0 none, 1 dark).
float marks_at(float xm, float y, float q) {
	// the mask: a band down over the eye, from the top of the head to the cheek
	float across = xm - (EYE_AT.x + 0.32 * (y - EYE_AT.y));
	float m = (1.0 - smoothstep(0.0022, 0.0028, abs(across))) * smoothstep(-0.0045, -0.0028, y) * mask_amount;
	// the saddle under the dorsal fin
	float saddle = smoothstep(DORSAL_AT.x - 0.0008, DORSAL_AT.x + 0.0008, xm) * (1.0 - smoothstep(DORSAL_AT.y - 0.002, DORSAL_AT.y, xm));
	m = max(m, saddle * smoothstep(0.5, 0.65, q) * saddle_amount);
	// the round spot on the root of the tail
	float spot = length(vec2((xm - 0.0425) / 1.0, (q - 0.25) * 0.004));
	m = max(m, (1.0 - smoothstep(0.0028, 0.0034, spot)) * tail_spot_amount);
	return m;
}

// The cartoon eye's colour at a place on its face: `e` x up, y forward, 1 at its rim. A round pupil.
vec3 cartoon_eye(vec2 e) {
	float r = length(e);
	vec2 q = e - vec2(eye_look.y, eye_look.x) * (0.92 - iris_size);
	float ri = length(q) / iris_size;
	float aa = fwidth(ri) + 0.01;
	vec3 c = eye_white * mix(1.0, 0.8, smoothstep(0.45, 1.0, r));
	vec3 ring = mix(iris * 1.2, iris * 0.6, smoothstep(0.3, 0.95, ri));
	ring = mix(ring, iris * 0.2, smoothstep(0.84, 1.0, ri));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ri));
	float pd = length(q) / (iris_size * pupil_size);
	float pa = fwidth(pd) + 0.02;
	c = mix(c, vec3(0.012), 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	// (the highlights: up and forward, where the light comes from, and a second one below behind)
	float glint = 1.0 - smoothstep(0.15, 0.19, length(e - vec2(0.32, 0.28)));
	glint = max(glint, 0.8 * (1.0 - smoothstep(0.06, 0.09, length(e - vec2(-0.22, -0.26)))));
	c = mix(c, vec3(1.0), glint);
	// (the dark outline, so that it reads from far off)
	return mix(c, vec3(0.03, 0.025, 0.015), smoothstep(0.84, 0.91, r));
}

// The gills' colour: `uv` as the model gives it (x 0 the rakers' side, about 0.35 the bar, 1 the filaments;
// y the arch's number plus how far along it), `xm` how far back: blood red, the filaments darker with fine
// lines across, the rakers pale, all darker deeper in the throat.
vec3 gills(vec2 uv, float xm) {
	float along = fract(uv.y);
	vec3 fringe = gill_red * 0.62 * (0.72 + 0.28 * cos(along * 160.0));
	vec3 c = mix(gill_red * 1.15, fringe, smoothstep(0.45, 0.9, uv.x));
	float teeth = 0.6 + 0.4 * step(0.45, fract(along * 11.0));
	c = mix(c, gill_raker, (1.0 - smoothstep(0.06, 0.24, uv.x)) * teeth);
	return c * (1.0 - 0.5 * smoothstep(JAW_TO, THROAT_END, xm));
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

