shader_type spatial;
// The clown loach (clown_loach.gd): every marking drawn here (no texture files), and all of its
// moving. What each point is comes from the model (tools/build_clown_loach.py): UV2.y the part
// (0 body, 1 dorsal, 2 anal, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 a barbel,
// 8 the lower jaw, 9 a cheek). UV, on the body and the lower jaw: x how far along, y how high on
// its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y
// leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1); on a barbel: x root
// (0) to tip (1), y which barbel (over 8); on a cheek: x how far along. UV2.x, on the body and
// the lower jaw, how far inside the mouth (0 skin and lips, 1 the middle of its roof or floor); on
// a cheek, how far down it from the upper lip (0) to the lower (1).
//
// It swims with a quick wriggle: a wave that runs back along the whole body and grows towards
// the tail, which swings wide; its pectoral fins fan about their roots; its barbels twitch. All of
// it is a function of `phase` alone (0 to 1 through one beat, with whole numbers of tail beats,
// fannings and twitches in a beat), so a picture of it loops exactly.
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


// Kept in step with the model (the build script prints the pectoral numbers: SHADER).
const float LENGTH = 0.2;
const float HALF = 0.1;
const vec3 PECTORAL_ROOT = vec3(0.00985, -0.00657, -0.05100);
const vec3 PECTORAL_AXIS = vec3(-0.4633, -0.8623, -0.2043);
// Where the lower jaw hinges (metres behind the snout, metres up: the corners of the mouth), where
// it ends at the belly, and how far it swings down for `gape` 1 (radians: the front lip drops about
// 3 mm, the mouth opening downwards).
const float MOUTH_TO = 0.0085;
const vec2 HINGE = vec2(0.0085, -0.00463);
const float JAW_BACK = 0.0125;
const float GAPE_TURN = 0.75;

// How far through a beat it is (0..1, it wraps), and how many times in a beat its tail beats, its
// pectoral fins fan and its barbels twitch (whole numbers). Set by ClownLoach.
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of fish swimming tight rounds: "The fish need to bend more"):
// how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The
// head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
uniform float tail_beats = 4.0;
uniform float fans = 3.0;
uniform float twitches = 2.0;
// How widely it wriggles, for 1 as a loach on its way somewhere (its tail tips swing about a
// tenth of its length either way); 0 still.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.85;
// How far its pectoral fins fan (1: about a quarter of a right angle either way), and how far its
// barbels twitch (1: their tips about 2 mm).
uniform float fan = 1.0;
uniform float twitch = 1.0;
// How far its mouth is open (the user, 2026-11-17: "the fish should be able to open their
// mouths"): 0 shut, 1 wide open. Set by ClownLoach.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The body: orange above, paler and yellower underneath, browner along the ridge of the back.
uniform vec3 orange : source_color = vec3(0.93, 0.45, 0.07);
uniform vec3 pale : source_color = vec3(0.98, 0.74, 0.34);
uniform vec3 ridge : source_color = vec3(0.62, 0.3, 0.08);
// The three bands, and the blue they glance with.
uniform vec3 band : source_color = vec3(0.03, 0.03, 0.045);
uniform vec3 band_glance : source_color = vec3(0.1, 0.13, 0.24);
// The fins: the red of the tail and the pelvic fins, the red-orange of the others, the dark of the
// dorsal and anal fins' roots and of the streaks on the pelvic fins.
uniform vec3 fin_red : source_color = vec3(0.86, 0.13, 0.03);
uniform vec3 fin_orange : source_color = vec3(0.95, 0.36, 0.06);
uniform vec3 fin_dark : source_color = vec3(0.045, 0.035, 0.045);
// The lips and the barbels.
uniform vec3 barbel : source_color = vec3(0.93, 0.66, 0.56);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.16, 0.04, 0.04);
// How much of each band shows (1 all of it; a loach "greys out" when it squabbles).
uniform float bands_show = 1.0;

// Cartoon eyes (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0, the default, is the eye drawn below, as it always was; 1 is the cartoon eye:
// grown about its middle, a pale white, a coloured iris, a big dark pupil, a highlight that stays
// put (up and forward, towards the light) and a dark rim, under an upper lid. The clown loach's: a
// cheeky, mischievous look, a bright orange iris, a keyhole pupil, its lid (the black of the band it
// sits in) slanting up towards the snout as if it had one brow raised.
uniform float cartoon_eyes = 0.0;
// Where the pupil looks, in the eye's own plane: x forward (towards the snout; -1 back towards the
// tail), y up; -1..1. Only the cartoon eye's pupil moves.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat from above and below and a lid of `lid_colour` closes over it.
uniform float blink = 0.0;
// How much bigger the cartoon eye is drawn, and how fast the head's skin falls away round it (1 / (2 x
// its radius there), per metre); its white, its iris (how wide, of the eye's face to its rim), its
// pupil (how wide, of the iris; 0 round, 1 an upright slit, 2 a level bar, 3 a keyhole), where the
// upper lid's edge rests (1 the top of the eye, no lid; 0 its middle) and how much lower it comes at
// the front (a frown; less than 0 raises it there).
uniform float eye_grow = 1.9;
// (eye_sink: 0, not sunk, looked cleanest on all of them: sunk, the rim dipped under the skin and came
// out again below the eye as a dark crescent)
uniform float eye_sink = 0.0;
uniform vec3 eye_white : source_color = vec3(0.98, 0.95, 0.88);
uniform vec3 iris : source_color = vec3(1.0, 0.5, 0.08);
uniform float iris_size = 0.62;
uniform float pupil_size = 0.6;
uniform int pupil_shape = 3;
uniform float lid = 0.55;
uniform float lid_slant = -0.3;
uniform vec3 lid_colour : source_color = vec3(0.03, 0.03, 0.045);
// As the model has it (the build script prints it): the right eye's middle on the skin and the way
// it faces (metres), and its radius over the skin (`EYE_AT`, `EYE_RADIUS`: metres behind the snout,
// metres up).
const vec3 EYE_MIDDLE = vec3(0.00909, 0.0092, -0.071);
const vec3 EYE_OUT = vec3(0.9676, 0.1536, -0.2004);
const vec2 EYE_AT = vec2(0.029, 0.0092);
const float EYE_RADIUS = 0.0038;

varying vec3 rest;
varying float part;

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

// How far to one side the middle line of the body is, `xm` metres behind the snout: a wave that
// runs back along it, smallest behind the head, growing all the way to the tips of the tail.
float side_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * (0.016 - 0.062 * s + 0.146 * s * s);
	return sway * reach * sin(TAU * (tail_beats * phase - s / wave));
}

// How much of the jaw's swing a point `xm` metres behind the snout takes: all of it ahead of the
// corners of the mouth, none at the belly (as the model has it: `jaw_turn`).
float jaw_turn(float xm) {
	return 1.0 - smoothstep(MOUTH_TO - 0.0015, JAW_BACK, xm);
}

// `v` (and its normal `n`) swung down about the jaw's hinge by `a` radians.
void swing(inout vec3 v, inout vec3 n, float a) {
	vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
	vec2 d = v.yz - hinge;
	v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
	n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
}

// The cartoon eye grown about its middle, and squashed from above and below as it blinks (nothing
// moves while cartoon_eyes and blink are 0).
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
	float before = dot(d - o * dot(d, o), d - o * dot(d, o));
	// (grown across, and outward; what lies behind its face, deep in the head, is not pushed further in,
	// or it would come out through the other side of a narrow head)
	float deep = min(dot(d, o), 0.0);
	d = (d - o * deep) * grow + o * deep;
	// (sunk as the head's skin falls away round it, so that the grown rim stays in the skin)
	d -= o * eye_sink * before * (grow * grow - 1.0);
	d -= up * dot(d, up) * 0.8 * blink;
	v = at + d;
}


// The cartoon eye's colour at a place on its face: `e` x up, y forward, 1 at its rim.
vec3 cartoon_eye(vec2 e) {
	float r = length(e);
	vec2 q = e - vec2(eye_look.y, eye_look.x) * (0.9 - iris_size);
	float ri = length(q) / iris_size;
	float aa = fwidth(ri) + 0.01;
	vec3 c = eye_white * mix(1.0, 0.82, smoothstep(0.4, 1.0, r));
	vec3 ring = mix(iris * 1.2, iris * 0.6, smoothstep(0.25, 0.95, ri));
	ring = mix(ring, iris * 0.25, smoothstep(0.82, 1.0, ri));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ri));
	vec2 p = q / (iris_size * pupil_size);
	float pd = length(p);
	if (pupil_shape == 1) {
		pd = length(vec2(p.x * 0.6, p.y * 2.4));
	} else if (pupil_shape == 2) {
		pd = length(vec2(p.x * 2.4, p.y * 0.6));
	} else if (pupil_shape == 3) {
		pd = min(length(p - vec2(0.22, 0.0)) * 1.15, length(vec2((p.x + 0.35) * 0.75, p.y * 2.8)));
	}
	float pa = fwidth(pd) + 0.02;
	c = mix(c, vec3(0.015), 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	float shine = 1.0 - smoothstep(0.17, 0.21, length(e - vec2(0.36, 0.3)));
	shine = max(shine, 0.85 * (1.0 - smoothstep(0.07, 0.1, length(e - vec2(-0.22, -0.3)))));
	c = mix(c, vec3(1.0), shine);
	return mix(c, vec3(0.02), smoothstep(0.83, 0.9, r));
}


// The body behind the head laid round an arc (see `curl`).
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

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part > 5.5 && part < 6.5) {
		eye_shape(v);
	}
	if (part > 3.5 && part < 4.5) {
		// A pectoral fin fans about the line of its root, the fanning running out along it.
		float side = v.x < 0.0 ? -1.0 : 1.0;
		v.x *= side;
		n.x *= side;
		float a = -fan * (0.18 + 0.32 * sin(TAU * fans * phase - 1.3 * UV.x));
		float ca = cos(a);
		float sa = sin(a);
		vec3 r = v - PECTORAL_ROOT;
		v = PECTORAL_ROOT + r * ca + cross(PECTORAL_AXIS, r) * sa + PECTORAL_AXIS * dot(PECTORAL_AXIS, r) * (1.0 - ca);
		n = n * ca + cross(PECTORAL_AXIS, n) * sa + PECTORAL_AXIS * dot(PECTORAL_AXIS, n) * (1.0 - ca);
		v.x *= side;
		n.x *= side;
	} else if (part > 6.5 && part < 7.5) {
		// A barbel twitches, each in its own time, most at its tip; the chin's two (6 and 7) go
		// with the lower jaw.
		float id = UV.y * 8.0;
		float a = sin(TAU * twitches * phase + id * 2.4) + 0.5 * sin(TAU * (2.0 * twitches + 1.0) * phase + id * 4.1);
		float b = sin(TAU * (twitches + 1.0) * phase + id * 1.7);
		v += vec3(a, 0.3 * b, 0.6 * b) * (UV.x * UV.x * 0.0013 * twitch);
		if (id > 5.5) {
			swing(v, n, clamp(gape, 0.0, 1.0) * GAPE_TURN);
		}
	} else if (part > 7.5 && part < 8.5) {
		// The lower jaw swings down about its hinge: all of it ahead of the corners of the mouth,
		// its back less and less, as the throat stretches.
		swing(v, n, clamp(gape, 0.0, 1.0) * GAPE_TURN * jaw_turn(v.z + HALF));
	} else if (part > 8.5) {
		// A cheek hangs between the lips: the model has it as it is with the mouth wide open; it
		// folds up along the line of the mouth as the mouth shuts (each point swung as far as it is
		// down the cheek, UV2.x).
		swing(v, n, (clamp(gape, 0.0, 1.0) - 1.0) * GAPE_TURN * jaw_turn(UV.x * LENGTH) * UV2.x);
	}
	float xm = v.z + HALF;
	float zc = clamp(xm, 0.0, LENGTH);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0006) - side_at(zc - 0.0006)) / 0.0012;
	// (each slice of the body is turned to stay square to its middle line: a bend, not a shear)
	float turn = atan(slope);
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The edge of the gill cover, as the model has it (metres behind the snout, at a height).
float gill_x(float y) {
	return 0.047 - 14.0 * (y + 0.002) * (y + 0.002);
}

// The colour of the tail and of the plate it grows from, `s` along the fish: the orange of the
// body at the wrist, red by the fork.
vec3 tail_colour(float s) {
	return mix(mix(orange, fin_orange, smoothstep(0.73, 0.79, s)), fin_red, smoothstep(0.77, 0.9, s));
}

// How much of a band there is at `s` along the body, for a band whose middle is at `middle` and
// which is `half` wide either way (its edge a little soft).
float band_at(float s, float middle, float half) {
	return 1.0 - smoothstep(half - 0.005, half + 0.004, abs(s - middle));
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

