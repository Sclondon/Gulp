shader_type spatial;
// The mosasaur (mosasaur.gd): every marking drawn here (no texture files), its swimming, its mouth
// and its eyes. What each point is comes from the model (tools/build_mosasaur.py): UV2.y the part (0
// body, 1 lower jaw, 2 an upper tooth (along the lip or on the roof of the mouth), 3 a lower tooth, 4
// the fluke's lobes, 6 a fore paddle, 7 an eye, 8 a hind paddle); UV2.x, on the body and the jaw, how
// much it is inside the mouth (on the fluke, 1 the lower lobe). UV, on the body and jaw: x how far
// along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root
// (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1).
//
// It swims SIDE TO SIDE with the whole of its long tail: a wave that starts behind the chest and
// grows all the way back to the fluke, which turns as one stiff plate behind its hinge; the head
// swings a little against it. All of it is a function of `phase` alone, so a picture of it loops
// exactly. Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
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
const float LENGTH = 12.0;
const float HALF = 6.0;
// Where the fluke is hinged (metres behind the tip of the snout): behind it, one stiff plate.
const float JOINT = 10.4;
// The corner of the mouth, where the lower jaw hinges (metres behind the tip, metres up), and how far
// the jaw's turn is spread round it.
const float CORNER = 1.42;
const float HINGE_Y = -0.111;
const float HINGE_SPREAD = 0.2;
const vec2 EYE_AT = vec2(1.13, 0.175);
const float JAW_FROM = 0.05;
// How far the lower jaw swings down for `gape` 1 (radians: very wide), how far the skull lifts with
// it, and how far the middle line swings for `sway` 1 (of its length).
const float GAPE_MAX = 1.1;
const float LIFT_MAX = 0.14;
const float REACH = 0.075;

// How far through a beat of its tail (0..1, it wraps). Set by Mosasaur.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the fore
// paddles to the fluke (0 straight; more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// How widely it beats, for 1 as one cruising (the fluke swings about 0.8 m each way).
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open (the jaw drops 63 degrees and the skull lifts).
uniform float gape = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.85;

// The back, the flank, the belly, the dark blotches; the fins; the inside of the mouth; the teeth.
uniform vec3 back : source_color = vec3(0.1, 0.12, 0.11);
uniform vec3 flank : source_color = vec3(0.3, 0.33, 0.3);
uniform vec3 belly : source_color = vec3(0.82, 0.8, 0.72);
uniform vec3 blotch : source_color = vec3(0.04, 0.05, 0.045);
uniform vec3 fin : source_color = vec3(0.08, 0.095, 0.09);
uniform vec3 mouth : source_color = vec3(0.55, 0.26, 0.26);
uniform vec3 tooth : source_color = vec3(0.9, 0.86, 0.72);
// How strongly the dark mottling on its back and flanks shows (0 none).
uniform float mottle = 0.6;

// The cartoon eye (0 the eye as in life, 1 the cartoon eye), where its eyes look (x +1 towards the
// nose, y +1 up, each in its own plane) and its lids (0 open, 1 shut). Set by the node.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// Where the right eye sits, as the model has it (the build script prints it: EYE_FRAME; the left eye
// is its mirror): its middle on the skin, the way out of the head, the way to the nose and the way up
// in the eye's own plane, how fast the skin falls away from that plane round it (metres per square
// metre), and the eye's radius.
const vec3 EYE_CENTRE = vec3(0.23987, 0.17500, -4.87000);
const vec3 EYE_OUT = vec3(0.8469, 0.4999, -0.1815);
const vec3 EYE_FWD = vec3(-0.1563, -0.0922, -0.9834);
const vec3 EYE_UP = vec3(-0.5083, 0.8612, 0.0000);
const float EYE_SAG = 0.9645;
const float EYE_RADIUS = 0.056;
// The mosasaur's: a cold menace. Bigger than life by 2 (its eye is small for its head); a cold yellow-green iris filling nearly all
// of the eye (no white to speak of), a thin black slit of a pupil, a small hard highlight; a heavy
// brow coming down low and slanting in towards the snout, and a lower lid pushed up under it (the
// narrowed stare of a hunter), thick dark lines.
const float EYE_GROW = 2.0;
const vec3 SCLERA = vec3(0.75, 0.72, 0.42);
const vec3 IRIS_LIGHT = vec3(0.86, 0.8, 0.22);
const vec3 IRIS_DARK = vec3(0.36, 0.42, 0.08);
const float IRIS = 0.8;
const vec2 IRIS_AT = vec2(0.0, -0.02);
const vec2 LOOK_REACH = vec2(0.2, 0.12);
const vec2 GLINT_AT = vec2(0.26, 0.2);
const float GLINT = 0.09;
const vec2 GLINT2_AT = vec2(-0.2, -0.22);
const vec3 OUTLINE = vec3(0.02, 0.025, 0.02);
const float LINE_UP = 0.16;
const float LINE_DOWN = 0.07;

// (inside the pupil where this is under 0; `q` from the iris's middle, in eye radii: a tall thin slit)
float pupil(vec2 q) {
	return (length(q / vec2(0.075, 0.62)) - 1.0) * 0.075;
}

// (the brow: low, and lower still towards the snout, x +1)
float lid_up(float x) {
	return 0.34 - 0.3 * x - 0.12 * x * x;
}

float lid_down(float x) {
	return -0.55 + 0.08 * x + 0.12 * x * x;
}

vec3 lid_colour() {
	return back * 1.1;
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

// The cartoon eye's colour at `e` (eye_at); `lit` how much of it glows a little.
vec3 cartoon_eye(vec2 e, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 q = e - IRIS_AT - clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK_REACH;
	float qi = length(q);
	vec3 c = SCLERA * (1.0 - 0.25 * smoothstep(0.5, 0.86, r));
	// (the iris: rays of darker colour out from the pupil)
	float rays = 0.5 + 0.5 * sin(atan(q.y, q.x) * 23.0);
	vec3 iris = mix(IRIS_LIGHT, IRIS_DARK, smoothstep(IRIS * 0.25, IRIS, qi) * 0.8 + rays * 0.15);
	c = mix(c, iris, 1.0 - smoothstep(IRIS - aa, IRIS + aa, qi));
	c = mix(c, vec3(0.005), 1.0 - smoothstep(-aa * 0.3, aa * 0.3, pupil(q)));
	float glint = max(1.0 - smoothstep(GLINT - aa, GLINT + aa, length(e - GLINT_AT)),
		1.0 - smoothstep(GLINT * 0.4 - aa, GLINT * 0.4 + aa, length(e - GLINT2_AT)));
	c = mix(c, vec3(1.0), glint);
	lit = mix(0.45, 1.0, glint);
	c = mix(c, OUTLINE, smoothstep(0.84 - aa, 0.86 + aa, r));
	// the lids, meeting a little above the middle as it blinks
	float b = clamp(blink, 0.0, 1.0);
	float meet = mix(lid_down(e.x), lid_up(e.x), 0.55);
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

// How far to the side the middle line of the body is, `xm` metres behind the tip: a wave that runs
// back along it, least at the chest, growing all the way down the tail.
float side_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * REACH * (0.07 - 0.36 * s + 0.62 * s * s + 0.6 * s * s * s);
	return sway * reach * sin(TAU * (phase - s / wave));
}

// The body behind the head laid round an arc to one side (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.3 * LENGTH;
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

// Turns `v` and `n` by `a` about the hinge of the jaw (more than 0: the front goes down).
void about_hinge(inout vec3 v, inout vec3 n, float a) {
	vec2 hinge = vec2(HINGE_Y, CORNER - HALF);
	vec2 d = v.yz - hinge;
	float c = cos(a);
	float sn = sin(a);
	v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	inside = UV2.x;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	eye_at = vec2(0.0);
	if (p == 7) {
		vec2 at;
		eye_grow(v, at);
		eye_at = at;
	}
	float open = clamp(gape, 0.0, 1.0);
	if (p == 1 || p == 3) {
		// The lower jaw (and its teeth) swings down about the corner of the mouth; behind the
		// corner, inside the body, it stays.
		about_hinge(v, n, GAPE_MAX * open * smoothstep(CORNER + 0.04, CORNER - HINGE_SPREAD, v.z + HALF));
	} else if ((p == 0 || p == 2 || p == 7) && open > 0.0) {
		// The skull (the upper head, its teeth and eyes) lifts a little about the same hinge; the
		// throat under the hinge and the neck behind it stay.
		float w = smoothstep(CORNER + 0.5, CORNER - 0.1, v.z + HALF) * smoothstep(HINGE_Y - 0.12, HINGE_Y + 0.04, v.y);
		about_hinge(v, n, -LIFT_MAX * open * w);
	}
	float xm = v.z + HALF;
	// (the fluke, behind its hinge, is one stiff plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.03) - side_at(zc - 0.03)) / 0.06;
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.85 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The line of the mouth, as the model has it.
float mouth_y(float xm) {
	return -0.04 - 0.05 * xm;
}

// The skin at a place: `xm` behind the tip, `h` how high on its side (0..1).
vec3 skin(float xm, float h, float side) {
	float grain = noise2(vec2(xm * 30.0, h * 22.0 + side * 9.0));
	float scales = noise2(vec2(xm * 90.0, h * 70.0 + side * 3.0));
	float cloud = noise2(vec2(xm * 1.6, h * 4.0) + 3.0 + side * 5.0);
	// Countershaded: the belly pale, the flank grey-green, the back dark, the line between wavering.
	float edge = 0.55 + 0.05 * smoothstep(6.0, 10.0, xm) + (cloud - 0.5) * 0.1;
	vec3 c = mix(belly, flank, smoothstep(0.24, 0.42, h + (cloud - 0.5) * 0.08));
	c = mix(c, back, smoothstep(edge - 0.1, edge + 0.06, h));
	// Dark mottling over the back and the upper flanks, blotches of two sizes, and faint bands
	// across the tail.
	float spots = noise2(vec2(xm * 2.4, h * 7.0 + side * 11.0)) * 0.65 + noise2(vec2(xm * 6.0, h * 16.0 - side * 4.0)) * 0.35;
	float mott = smoothstep(0.56, 0.68, spots) * smoothstep(0.35, 0.6, h);
	float band = smoothstep(0.6, 0.95, sin(xm * 2.6 + (cloud - 0.5) * 2.0)) * smoothstep(5.5, 7.0, xm) * smoothstep(0.4, 0.7, h);
	c = mix(c, blotch, clamp(mott * 0.8 + band * 0.5, 0.0, 1.0) * mottle);
	// (small scales: a fine light grain)
	c *= 0.9 + 0.12 * grain + 0.08 * scales;
	return c;
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

