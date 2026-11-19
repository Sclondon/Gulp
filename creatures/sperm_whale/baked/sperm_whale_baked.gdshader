shader_type spatial;
// The sperm whale (sperm_whale.gd): every marking drawn here (no texture files), the wrinkles of
// its skin, its swimming and its mouth. What each point is comes from the model
// (tools/build_sperm_whale.py): UV2.y the part (0 body, 1 lower jaw, 3 a tooth, 4 the flukes,
// 6 a flipper, 7 an eye); UV2.x, on the jaw, how much it is on the jaw's top (the floor of the
// mouth). UV, on the body and jaw: x how far along, y how high on its side (1 the ridge of the
// back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing
// edge (1); on an eye: x middle (0) to rim (1); on a tooth: x root (0) to tip (1).
//
// It swims as whales do: its flukes beat UP AND DOWN. A wave runs back along the body, nothing at
// the head and growing down the tail stock, and the flukes pitch about their root as one stiff
// plate. All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has (the wrinkles are a bump made from screen-space
// derivatives, which GLES 3 and WebGL 2 have); it runs the same under Forward+.
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


// Kept in step with the model.
const float LENGTH = 15.0;
const float HALF = 7.5;
// Where the flukes are hinged (metres behind the front of the head).
const float JOINT = 13.5;
// Where the head's box ends; the corner of the mouth, where the jaw hinges (metres behind the
// front, metres up); the eye; the blowhole (metres behind the front, metres to the side).
const float HEAD_END = 5.0;
const float JAW_FROM = 0.75;
const float CORNER = 4.1;
const float HINGE_Y = -1.3262;
const vec2 EYE_AT = vec2(4.55, -0.74);
const vec2 BLOWHOLE = vec2(0.42, -0.34);
// How far the lower jaw swings down for `gape` 1 (radians), and how far the flukes' root rises and
// falls for `sway` 1 (of its length).
const float GAPE_MAX = 0.8;
const float REACH = 0.045;

// How far through a beat of its flukes (0..1, it wraps). Set by SpermWhale.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the head
// to the flukes (0 straight; more than 0 the tail comes round to +X, as the fish's does).
uniform float curl = 0.0;
// The same up and down, about its middle, in radians from its head to its flukes (0 straight;
// more than 0 its head and its flukes both come up; less than 0 both go down, its back arched:
// the start of a deep dive, its flukes about to lift).
uniform float arch = 0.0;
// How widely it beats, for 1 a sperm whale cruising (its fluke tips rise and fall about 0.9 m).
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open (the narrow jaw hangs down).
uniform float gape = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.0;

// Its dark grey-brown skin, a little paler on the belly and the head's front; the white round the
// mouth and inside it; the teeth.
uniform vec3 skin : source_color = vec3(0.2, 0.18, 0.17);
uniform vec3 pale : source_color = vec3(0.36, 0.34, 0.33);
uniform vec3 white : source_color = vec3(0.86, 0.85, 0.82);
uniform vec3 mouth : source_color = vec3(0.8, 0.72, 0.72);
uniform vec3 tooth : source_color = vec3(0.92, 0.88, 0.76);
// How deep the wrinkles of the skin behind the head look (0 smooth), and how strongly the pale
// scars (squid suckers and scratches) show on the head.
uniform float wrinkles = 1.0;
uniform float scars = 0.6;

// The cartoon eye (added 2026-11-18; 0 the eye as in life, as it always was, 1 the cartoon eye),
// where its eyes look (x +1 towards the nose, y +1 up, each in its own plane) and its lids (0 open,
// 1 shut). Set by the node.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// Where the right eye sits, as the model has it (the build script prints it: EYE_FRAME; the left
// eye is its mirror): its middle on the skin, the way out of the head, the way to the nose and the
// way up in the eye's own plane, how fast the skin falls away from that plane round it (metres per
// square metre), and the eye's radius.
const vec3 EYE_CENTRE = vec3(1.14778, -0.74000, -2.95000);
const vec3 EYE_OUT = vec3(0.9829, -0.1800, -0.0382);
const vec3 EYE_FWD = vec3(-0.0375, 0.0069, -0.9993);
const vec3 EYE_UP = vec3(0.1801, 0.9836, -0.0000);
const float EYE_SAG = 0.0663;
const float EYE_RADIUS = 0.055;
// The sperm whale's: old, slow, weary and wise. Bigger than life by 2.2 (its own is tiny on that
// head); an old yellowed white, a pale grey-blue iris, a flat bar of a pupil (a deep diver's); a
// heavy upper lid half down and drooping towards the back (sad, patient), a lower lid with a bag
// of skin under it.
const float EYE_GROW = 2.2;
const vec3 SCLERA = vec3(0.9, 0.88, 0.8);
const vec3 IRIS_LIGHT = vec3(0.6, 0.7, 0.74);
const vec3 IRIS_DARK = vec3(0.2, 0.27, 0.32);
const float IRIS = 0.5;
const vec2 IRIS_AT = vec2(0.05, -0.08);
const vec2 LOOK_REACH = vec2(0.3, 0.18);
const vec2 GLINT_AT = vec2(0.22, 0.1);
const float GLINT = 0.1;
const vec2 GLINT2_AT = vec2(-0.2, -0.3);
const vec3 OUTLINE = vec3(0.04, 0.035, 0.03);
const float LINE_UP = 0.11;
// (how far under the lower lid a fold of skin is drawn: 0 none)
const float BAG = 0.2;
const float LINE_DOWN = 0.08;

// (inside the pupil where this is under 0; `q` from the iris's middle, in eye radii)
float pupil(vec2 q) {
	return length(vec2(max(abs(q.x) - 0.17, 0.0), q.y)) - 0.11;
}

float lid_up(float x) {
	return 0.28 + 0.2 * x;
}

float lid_down(float x) {
	return -0.62 + 0.06 * x;
}

vec3 lid_colour() {
	return skin;
}

// (where an eye's point lies in the eye's own plane, in eye radii: x towards the nose, y up)
varying vec2 eye_at;

// The eye's dome grown about its own middle for the cartoon eye, its rim laid back on the skin.
void eye_grow(inout vec3 v, out vec2 at) {
	vec3 m = vec3(v.x >= 0.0 ? 1.0 : -1.0, 1.0, 1.0);
	vec3 d = v - EYE_CENTRE * m;
	vec2 pl = vec2(dot(d, EYE_FWD * m), dot(d, EYE_UP * m));
	at = pl / EYE_RADIUS;
	if (cartoon_eyes <= 0.0) {
		return;
	}
	float g = mix(1.0, EYE_GROW, cartoon_eyes);
	float r2 = dot(pl, pl);
	float over = dot(d, EYE_OUT * m) + EYE_SAG * r2;
	float h = over * g - EYE_SAG * r2 * g * g;
	v = EYE_CENTRE * m + (EYE_FWD * m * pl.x + EYE_UP * m * pl.y) * g + EYE_OUT * m * h;
}

// The cartoon eye's colour at `e` (eye_at); `lit` how much of it glows a little (its white,
// iris and highlight read in dark water; the lids do not).
vec3 cartoon_eye(vec2 e, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 q = e - IRIS_AT - clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK_REACH;
	float qi = length(q);
	vec3 c = SCLERA * (1.0 - 0.18 * smoothstep(0.5, 0.86, r));
	vec3 iris = mix(IRIS_LIGHT, IRIS_DARK, smoothstep(IRIS * 0.55, IRIS, qi));
	iris = mix(iris, IRIS_LIGHT * 1.15, (1.0 - smoothstep(0.0, IRIS * 0.6, qi)) * 0.3);
	c = mix(c, iris, 1.0 - smoothstep(IRIS - aa, IRIS + aa, qi));
	c = mix(c, vec3(0.01), 1.0 - smoothstep(-aa, aa, pupil(q)));
	// the highlights stay put, towards the light, wherever it looks
	float glint = max(1.0 - smoothstep(GLINT - aa, GLINT + aa, length(e - GLINT_AT)),
		1.0 - smoothstep(GLINT * 0.45 - aa, GLINT * 0.45 + aa, length(e - GLINT2_AT)));
	c = mix(c, vec3(1.0), glint);
	lit = mix(0.5, 1.0, glint);
	// a dark ring round it
	c = mix(c, OUTLINE, smoothstep(0.84 - aa, 0.86 + aa, r));
	// the lids, meeting a little below the middle as it blinks
	float b = clamp(blink, 0.0, 1.0);
	float meet = mix(lid_down(e.x), lid_up(e.x), 0.35);
	float up = mix(lid_up(e.x), meet, b);
	float down = mix(lid_down(e.x), meet, b);
	float over_up = e.y - up;
	float over_down = down - e.y;
	float lid = max(smoothstep(-aa, aa, over_up), smoothstep(-aa, aa, over_down));
	c = mix(c, lid_colour(), lid);
	lit *= 1.0 - lid;
	float line = max(smoothstep(-aa, aa, over_up) * (1.0 - smoothstep(LINE_UP - aa, LINE_UP + aa, over_up)),
		smoothstep(-aa, aa, over_down) * (1.0 - smoothstep(LINE_DOWN - aa, LINE_DOWN + aa, over_down)));
	c = mix(c, OUTLINE, line * (1.0 - smoothstep(0.92, 1.0, r)));
	if (BAG > 0.0) {
		float fold = smoothstep(BAG - aa, BAG + aa, over_down) * (1.0 - smoothstep(BAG + 0.05 - aa, BAG + 0.05 + aa, over_down));
		c = mix(c, lid_colour() * 0.5, fold * (1.0 - smoothstep(0.85, 0.97, r)) * (1.0 - b));
	}
	return c;
}

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

// How far up the middle line of the body is, `xm` metres behind the front: a wave that runs back
// along it, nothing at the head, large only down the tail stock.
float lift_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * REACH * (0.05 - 0.28 * s + 0.3 * s * s + 0.93 * s * s * s * s);
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
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	inside = UV2.x;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	eye_at = vec2(0.0);
	if (p == 7) {
		vec2 at;
		eye_grow(v, at);
		eye_at = at;
	}
	if (p == 1 || p == 3) {
		// The lower jaw (and its teeth) swings down about the corner of the mouth; behind the
		// corner, up in the throat, it stays.
		float a = GAPE_MAX * clamp(gape, 0.0, 1.0) * smoothstep(CORNER + 0.45, CORNER - 0.15, v.z + HALF);
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
	float slope = (lift_at(zc + 0.04) - lift_at(zc - 0.04)) / 0.08;
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

// The wrinkles behind the head: long creases running mostly along the body, broken and wavering
// (a height, in metres).
float wrinkle(float xm, float h, float side) {
	float bend = noise2(vec2(xm * 0.9, h * 3.0 + side * 7.0)) * 6.0;
	float lines = sin(h * 95.0 + bend + noise2(vec2(xm * 4.0, h * 30.0)) * 2.5);
	float broken = smoothstep(0.25, 0.6, noise2(vec2(xm * 2.2 + side * 4.0, h * 14.0)));
	float cross_lines = sin(xm * 26.0 + noise2(vec2(xm * 3.0, h * 20.0 + side)) * 4.0) * 0.35;
	return (lines * broken + cross_lines * (1.0 - broken)) * 0.006;
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

