shader_type spatial;
// The flying fish's body, lower jaw, eyes and tail (flying_fish.gd): how they move is in
// flying_fish_motion.gdshaderinc (shared with the fins' shader); every marking is drawn here, from
// the species (the component's README names the references): no texture files. What each point
// is comes from the model (tools/build_flying_fish.py): COLOR.r the part, as a tenth (0 body,
// 1 lower jaw, 2 eye, 6 tail). On the body UV.x is how far along the fish (0 snout to 1 tail
// tip), UV.y how high (0 belly line to 1 back line), UV2.x how far round the skin from the back
// line (metres, + right, - left), UV2.y the whole way from back line to belly line; COLOR.g the
// gill cover's moving edge, COLOR.b the inside of the mouth. On the tail UV.x is along its rays
// (0 root to 1 edge), UV.y across it counted in rays. Nothing here needs more than GL
// Compatibility has.
render_mode cull_back, depth_draw_opaque, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// (from res://creatures/flying_fish/flying_fish_motion.gdshaderinc)
// How the flying fish (flying_fish.gd) moves: shared by its two shaders (flying_fish.gdshader, the
// body, and flying_fish_fins.gdshader, the see-through fins), so that both surfaces of the one
// model move as one. It swims by a wave down its body, its jaw and gill covers work, its tail and
// fins trail the bend, and its wings (the pectoral and pelvic fins) fold back along the body or
// spread, each turned about its root. What each point is comes from the model
// (tools/build_flying_fish.py): COLOR.r the part, as a tenth (0 body, 1 lower jaw, 2 eye,
// 4 dorsal, 6 tail, 7 anal, 8 pelvic, 9 pectoral); on the body COLOR.g the gill cover's moving
// edge; on a fin UV.x along its rays (0 root to 1 edge), UV.y across it counted in rays, COLOR.g
// 1 on a left wing. Nothing here needs more than GL Compatibility has.
//
// Everything that moves by itself runs on `phase` (0..1 through one beat, set by FlyingFish): the
// tail beats and the breaths each go a whole number of times a beat, so a picture of it comes
// round again exactly.

// Kept in step with the model and the script.
const float LENGTH = 0.3;
const float HINGE_S = 0.045;
const float HINGE_Y = -0.015;
// How many body lengths one wave of the swimming bend is.
const float WAVE = 0.95;
// The wings, as tools/build_flying_fish.py prints them (its SHADER lines; metres and radians,
// the right wing of each pair): the root of the leading ray; how long the root is; the angle
// between the leading and the trailing ray, spread; how many rays; how much of that angle is left
// folded; how far the folded rays bow in to lie along the body (per metre squared); and how the
// fin is held spread and folded, as three angles (how far its leading ray is swept back from
// straight out to the side, how far that ray is lifted above level, how far the fin is rolled
// about that ray: 0 flat with its trailing edge behind, a quarter turn its trailing edge down).
const vec3 PECTORAL_AT = vec3(0.01360, 0.01061, -0.08580);
const float PECTORAL_BASE = 0.00750;
const float PECTORAL_FAN = 1.08210;
const float PECTORAL_RAYS = 15.0;
const float PECTORAL_SHUT = 0.020;
const float PECTORAL_HUG = 0.40000;
const vec3 PECTORAL_SPREAD = vec3(0.24435, 0.15708, 0.06981);
const vec3 PECTORAL_FOLDED = vec3(1.53589, -0.02618, 1.78024);
const vec3 PELVIC_AT = vec3(0.00935, -0.01626, -0.02250);
const float PELVIC_BASE = 0.00480;
const float PELVIC_FAN = 0.95993;
const float PELVIC_RAYS = 6.0;
const float PELVIC_SHUT = 0.030;
const float PELVIC_HUG = 0.66667;
const vec3 PELVIC_SPREAD = vec3(0.52360, -0.12217, 0.00000);
const vec3 PELVIC_FOLDED = vec3(1.53240, 0.08727, 1.08210);

// How far through a beat it is (0..1), and how many times in a beat its tail beats and it
// breathes (whole numbers).
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of fish swimming tight rounds: "The fish need to bend more"):
// how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The
// head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
uniform float tail_beats = 3.0;
uniform float breaths = 2.0;
// How hard it is swimming: how far its tail swings (1 is a tenth of its length each way).
uniform float swim = 0.5;
// The wings: 0 the pectoral and pelvic fins folded back flat along the body (as it swims under
// water), 1 spread wide and held stiff (as it glides), and every place between.
uniform float wings : hint_range(0.0, 1.0) = 0.0;
// The mouth: how far open it is held (radians) and how much further each breath opens it. The
// gill covers: how far their edges lift with each breath (metres).
uniform float gape = 0.03;
uniform float gape_breath = 0.07;
uniform float gill_flare = 0.002;


float gill_edge(float h) {
	return 0.19 - 0.2 * (h - 0.45) * (h - 0.45);
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


// A wing's own directions from its three angles: the way its leading ray goes, the way across
// it towards its trailing edge, and the way its flat side faces.
mat3 wing_frame(vec3 held) {
	vec3 a = vec3(cos(held.x) * cos(held.y), sin(held.y), sin(held.x) * cos(held.y));
	vec3 b = normalize(cross(a, vec3(0.0, 1.0, 0.0)));
	vec3 n = cross(b, a);
	return mat3(a, b * cos(held.z) - n * sin(held.z), n * cos(held.z) + b * sin(held.z));
}


// Folds a right wing: `v` and `n` are a point of the spread model and its normal, `t` how far
// across the fin its ray is (0 the leading ray to 1 the trailing), `open` 0 folded to 1 spread.
// Each ray is found from where the point is (how far along its ray, how far off the fin's middle
// sheet), then laid out again with the fin held as `open` says: the whole fin turned about its
// root, its fan of rays closed, and the rays bowed in to lie along the body. The same sums as
// `wing_where` in tools/build_flying_fish.py.
void wing_pose(inout vec3 v, inout vec3 n, float t, float open, vec3 at, float base, float fan, float shut, float hug, vec3 spread, vec3 folded) {
	mat3 was = wing_frame(spread);
	vec3 d = v - at;
	float angle = t * fan;
	float off = dot(d, was[2]);
	float along = dot(d, was[0]) * cos(angle) + (dot(d, was[1]) - base * t) * sin(angle);
	mat3 now = wing_frame(mix(folded, spread, open));
	float angle_now = angle * mix(shut, 1.0, open);
	float bow = hug * (1.0 - open) * along * along;
	v = at + now[1] * (base * t) + (now[0] * cos(angle_now) + now[1] * sin(angle_now)) * along + now[2] * (off + bow);
	vec3 m = vec3(dot(n, was[0]), dot(n, was[1]), dot(n, was[2]));
	float turned = angle_now - angle;
	m.xy = vec2(m.x * cos(turned) - m.y * sin(turned), m.x * sin(turned) + m.y * cos(turned));
	n = now[0] * m.x + now[1] * m.y + now[2] * m.z;
}


// Moves a point of the model and its normal. `part` is what it is (0 to 9), `uv` and `colour`
// the point's own.
void fish_move(inout vec3 v, inout vec3 n, float part, vec2 uv, vec4 colour) {
	float s = v.z / LENGTH + 0.5;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float breath = phase * TAU * breaths;
	float tail = phase * TAU * tail_beats;
	float wave = tail - TAU * clamp(s, 0.0, 1.05) / WAVE;
	// (a spread wing is held stiff: it is carried and turned as its root is, not bent along its
	// length with the body beside it; a folded one lies along the body and bends with it)
	float held = 0.0;
	float root_z = v.z;
	if (part == 1.0) {
		// The lower jaw swings about its hinge; the chin behind it stays.
		float a = (gape + gape_breath * (0.5 - 0.5 * cos(breath))) * smoothstep(0.06, 0.035, s);
		vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5) * LENGTH;
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	} else if (part == 0.0) {
		// The gill covers lift at their rear edges, a little after the mouth opens.
		v.x += side_is * colour.g * gill_flare * (0.5 - 0.5 * cos(breath - 1.3));
	} else if (part >= 8.0) {
		// A wing: folded or spread about its root (the left one as the right one's mirror picture).
		float mirror = colour.g > 0.5 ? -1.0 : 1.0;
		float open = clamp(wings, 0.0, 1.0);
		v.x *= mirror;
		n.x *= mirror;
		if (part == 9.0) {
			wing_pose(v, n, uv.y / PECTORAL_RAYS, open, PECTORAL_AT, PECTORAL_BASE, PECTORAL_FAN, PECTORAL_SHUT, PECTORAL_HUG, PECTORAL_SPREAD, PECTORAL_FOLDED);
			root_z = PECTORAL_AT.z;
		} else {
			wing_pose(v, n, uv.y / PELVIC_RAYS, open, PELVIC_AT, PELVIC_BASE, PELVIC_FAN, PELVIC_SHUT, PELVIC_HUG, PELVIC_SPREAD, PELVIC_FOLDED);
			root_z = PELVIC_AT.z;
		}
		v.x *= mirror;
		n.x *= mirror;
		held = open;
	} else if (part == 6.0) {
		// (the tail's edge lags behind the bend that carries it)
		v.x += LENGTH * 0.02 * swim * uv.x * uv.x * sin(wave - 1.1);
	} else if (part >= 4.0) {
		// The dorsal and anal fins trail the bend too.
		v.x += LENGTH * 0.012 * swim * uv.x * uv.x * sin(wave - 1.0 - uv.y * 0.2);
	}
	// The swimming bend: a wave that runs from head to tail, the head nearly still and the tail
	// swinging widest. Each place is carried sideways and turned to lie along the bent body, so
	// that the fins and the tail follow it.
	float zb = mix(v.z, root_z, held);
	float sb = clamp(zb / LENGTH + 0.5, 0.0, 1.05);
	float reach = 0.012 - 0.05 * sb + 0.14 * sb * sb;
	float reach_slope = -0.05 + 0.28 * sb;
	float w = tail - TAU * sb / WAVE;
	float off = LENGTH * swim * reach * sin(w);
	float slope = swim * (reach_slope * sin(w) - reach * TAU / WAVE * cos(w));
	vec3 along = normalize(vec3(slope, 0.0, 1.0));
	vec3 across = vec3(along.z, 0.0, -along.x);
	v = vec3(off, v.y, zb) + across * v.x + along * (v.z - zb);
	n = normalize(across * n.x + vec3(0.0, n.y, 0.0) + along * n.z);
	// The turn (`curl`), the same way: a stiff wing goes round with its root.
	float zc = mix(v.z, root_z, held);
	vec3 carried = vec3(v.x, v.y, zc);
	vec3 ahead = vec3(0.0, 0.0, 1.0);
	vec3 carried_too = carried;
	curl_bend(carried, ahead);
	curl_bend(carried_too, n);
	v = carried + ahead * (v.z - zc);
}


// The colours: the dark blue back, the bright line where it meets the silver side, the silver
// side, the white belly.
uniform vec3 back : source_color = vec3(0.03, 0.08, 0.2);
uniform vec3 back_line : source_color = vec3(0.16, 0.42, 0.78);
uniform vec3 side : source_color = vec3(0.74, 0.79, 0.85);
uniform vec3 belly : source_color = vec3(0.96, 0.97, 0.98);
uniform vec3 cheek : source_color = vec3(0.88, 0.9, 0.93);
uniform vec3 lip : source_color = vec3(0.8, 0.76, 0.76);
uniform vec3 mouth : source_color = vec3(0.8, 0.62, 0.62);
uniform vec3 tail_colour : source_color = vec3(0.1, 0.14, 0.22);
uniform vec3 eye_silver : source_color = vec3(0.82, 0.86, 0.9);
uniform vec3 sheen_colour : source_color = vec3(0.6, 0.78, 1.0);
// How high up the side the blue back begins (0 the belly line, 1 the back line), how strong the
// bright line along its lower edge is, and how strong the sheen and the scales are.
uniform float back_from = 0.6;
uniform float line_amount = 0.55;
uniform float sheen = 0.4;
uniform float scales = 1.0;
// How big a scale is (metres): a flying fish's are large.
uniform float scale_size = 0.0042;

// Cartoon eyes (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0, the default, is the eye drawn below, as it always was; 1 is the cartoon eye:
// grown about the middle of its face, a pale white, a coloured iris, a big dark pupil, a highlight
// that stays put (up and forward, towards the light) and a dark rim. The flying fish's: a wide,
// startled, always-about-to-take-off stare, no lid, a huge pupil in a pale sky-blue iris.
uniform float cartoon_eyes = 0.0;
// Where the pupil looks, in the eye's own plane: x forward (towards the snout; -1 back towards the
// tail), y up; -1..1. Only the cartoon eye's pupil moves.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat from above and below and a lid of `lid_colour` closes over it.
uniform float blink = 0.0;
// The right eye's middle on the skin and the way it faces (metres, as the model is built: the build
// script prints them; the left eye is its mirror).
uniform vec3 eye_at = vec3(0.0126, 0.0033, -0.1275);
uniform vec3 eye_out = vec3(0.9816, 0.0554, -0.1829);
// How much bigger the cartoon eye is drawn, and how fast the head's skin falls away round it (1 / (2 x
// its radius there), per metre); its white, its iris (how wide, of the eye's face to its rim), its
// pupil (how wide, of the iris; 0 round, 1 an upright slit, 2 a level bar, 3 a keyhole), where the
// upper lid's edge rests (1 the top of the eye, no lid; 0 its middle) and how much lower it comes at
// the front (a frown).
uniform float eye_grow = 1.3;
// (eye_sink: 0, not sunk, looked cleanest on all of them: sunk, the rim dipped under the skin and came
// out again below the eye as a dark crescent)
uniform float eye_sink = 0.0;
uniform vec3 eye_white : source_color = vec3(0.98, 0.98, 0.97);
uniform vec3 iris : source_color = vec3(0.55, 0.78, 0.95);
uniform float iris_size = 0.5;
uniform float pupil_size = 0.7;
uniform int pupil_shape = 0;
uniform float lid = 1.0;
uniform float lid_slant = 0.0;
uniform vec3 lid_colour : source_color = vec3(0.6, 0.66, 0.74);

varying vec3 rest;
varying float part;
varying vec2 extra;


vec4 hash4(vec2 p) {
	vec4 q = fract(p.xyxy * vec4(0.1031, 0.1030, 0.0973, 0.1099));
	q += dot(q, q.wzxy + 33.33);
	return fract((q.xxyz + q.yzzw) * q.zywx);
}


// Soft patches, 0..1, a patch to each 1 of `p`: the skin is not one flat colour.
float cloud(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash4(i).x, hash4(i + vec2(1.0, 0.0)).x, f.x), mix(hash4(i + vec2(0.0, 1.0)).x, hash4(i + vec2(1.0, 1.0)).x, f.x), f.y);
}


// The cartoon eye's dome grown about the middle of its face, and squashed from above and below as
// it blinks (nothing moves while cartoon_eyes and blink are 0).
void eye_shape(inout vec3 v) {
	if (cartoon_eyes <= 0.0 && blink <= 0.0) {
		return;
	}
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	vec3 at = vec3(eye_at.x * side_is, eye_at.yz);
	vec3 o = normalize(vec3(eye_out.x * side_is, eye_out.yz));
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


void vertex() {
	bake_uv = CUSTOM0.xy;

	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part == 2.0) {
		eye_shape(v);
	}
	fish_move(v, n, part, UV, COLOR);
	VERTEX = v;
	NORMAL = n;
}


// The colour of the body's skin at a place: `h` up it (0 belly line to 1 back line). Dark blue
// above and silver-white below, as fish of the open sea are, with a bright blue line between.
vec3 skin(float h) {
	vec3 c = mix(belly, side, smoothstep(0.03, 0.3, h));
	c = mix(c, back_line, line_amount * exp(-pow((h - back_from + 0.035) / 0.04, 2.0)));
	c = mix(c, back, smoothstep(back_from - 0.03, back_from + 0.06, h));
	return c;
}


void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

