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
const vec3 EYE_CENTRE = vec3(0.52138, -0.04000, -2.70000);
const vec3 EYE_OUT = vec3(0.9801, -0.0098, -0.1984);
const vec3 EYE_FWD = vec3(-0.1984, 0.0020, -0.9801);
const vec3 EYE_UP = vec3(0.0100, 0.9999, 0.0000);
const float EYE_SAG = 0.5021;
const float EYE_RADIUS = 0.032;
// The orca's: a hunter's cool, knowing look. Bigger than life by 2; a white eye, a warm amber
// iris, a round pupil; a heavy straight upper lid slanting down to the front (a level, sure gaze),
// with a thick dark line along it, and a low lower lid.
const float EYE_GROW = 2.0;
const vec3 SCLERA = vec3(0.96, 0.95, 0.92);
const vec3 IRIS_LIGHT = vec3(0.78, 0.5, 0.18);
const vec3 IRIS_DARK = vec3(0.32, 0.15, 0.04);
const float IRIS = 0.44;
const vec2 IRIS_AT = vec2(0.06, -0.04);
const vec2 LOOK_REACH = vec2(0.3, 0.22);
const vec2 GLINT_AT = vec2(0.2, 0.22);
const float GLINT = 0.13;
const vec2 GLINT2_AT = vec2(-0.16, -0.2);
const vec3 OUTLINE = vec3(0.01, 0.01, 0.012);
const float LINE_UP = 0.16;
// (how far under the lower lid a fold of skin is drawn: 0 none)
const float BAG = 0.0;
const float LINE_DOWN = 0.07;

// (inside the pupil where this is under 0; `q` from the iris's middle, in eye radii)
float pupil(vec2 q) {
	return length(q) - 0.23;
}

float lid_up(float x) {
	return 0.5 - 0.2 * x;
}

float lid_down(float x) {
	return -0.8 + 0.06 * x * x;
}

vec3 lid_colour() {
	return black;
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
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	inside = UV2.x;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	eye_at = vec2(0.0);
	if (p == 7) {
		vec2 at;
		eye_grow(v, at);
		eye_at = at;
	}
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
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

