shader_type spatial;
// The channel catfish (channel_catfish.gd): every marking drawn here (no texture files), its
// swimming, and its barbels laid along their ropes. What each point is comes from the model
// (tools/build_channel_catfish.py): UV2.y the part (0 body, 1 dorsal, 2 adipose, 3 anal, 4 the
// tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 a barbel, 9 the lower jaw, 10 a cheek). UV,
// on the body and the lower jaw: x how far along, y how high on its side (1 the ridge of the back,
// 0 the keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge
// (1); on an eye: x middle (0) to rim (1); on a barbel: x root (0) to tip (1), y how far round it
// (0..1); on a cheek: x how far along. UV2.x, on a barbel: which one (0 to 7, the whole part) and
// how thick it is at its root (the fraction: metres times 100); on the body and the lower jaw, how
// far inside the mouth (0 skin and lips, 1 the middle of its roof or floor); on a cheek, how far
// down it from the upper lip (0) to the lower (1).
//
// It swims as catfish do: a slow wave runs back along the whole body, small at the head, least
// just behind it, widest at the tail, and every cross-section is turned to stay square to the
// body's line (a true bend); the soft forked tail goes with it. All of that is a function of
// `phase` alone, so a picture of it loops exactly. The barbels are ropes that ChannelCatfish
// simulates: their points come here in a small picture (`ropes`) and each barbel is laid along a
// smooth curve through its own.
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


// Kept in step with the model and with channel_catfish.gd.
const float LENGTH = 0.6;
const float HALF = 0.3;
const float MOUTH_TO = 0.031;
// Where the lower jaw hinges (metres behind the snout, metres up: the corners of the mouth), where
// it ends at the belly, and how far it swings down for `gape` 1 (radians: the front of the lower
// lip drops about 0.013 m). ChannelCatfish has the same numbers, for the chin's barbels.
const vec2 HINGE = vec2(0.031, -0.02794);
const float JAW_BACK = 0.043;
const float GAPE_TURN = 0.55;
// How many points a barbel's rope has (the picture is this wide, and sixteen high: a row of
// points for each barbel, then a row for each of which way is "side" at each point).
const int POINTS = 8;

// How far through a beat of its tail (0..1, it wraps). Set by ChannelCatfish.
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of fish swimming tight rounds: "The fish need to bend more"):
// how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The
// head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How widely it swims, for 1 as a catfish cruising slowly (its tail tips swing about 0.05 m
// either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.95;
// How far its mouth is open (the user, 2026-11-17: "the fish should be able to open their
// mouths"): 0 shut, 1 wide open. Set by ChannelCatfish.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// The barbels' ropes (ChannelCatfish sends them).
// How thick the barbels are drawn, for 1 as the model has them (the user, 2026-11-17: "The catfish
// whiskers need to be thicker": the model's own are a real catfish's, hair-fine at any distance).
uniform float barbel_thick = 1.8;
uniform sampler2D ropes : filter_nearest;

// The back; the slate blue it turns to on the upper side and where light glances off it.
uniform vec3 back : source_color = vec3(0.1, 0.125, 0.12);
uniform vec3 back_blue : source_color = vec3(0.2, 0.27, 0.33);
// The side, the belly, the small dark spots scattered over the side.
uniform vec3 side : source_color = vec3(0.56, 0.6, 0.57);
uniform vec3 belly : source_color = vec3(0.93, 0.92, 0.88);
uniform vec3 spot : source_color = vec3(0.03, 0.035, 0.04);
// The lips and the inside of the mouth's line.
uniform vec3 lip : source_color = vec3(0.7, 0.62, 0.6);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.13, 0.07, 0.075);
// The fins: their dusky membrane, their dark edges, the paler roots of the lower ones.
uniform vec3 fin : source_color = vec3(0.2, 0.23, 0.24);
uniform vec3 fin_edge : source_color = vec3(0.05, 0.06, 0.065);
uniform vec3 fin_pale : source_color = vec3(0.6, 0.62, 0.6);
// The barbels: the long ones at the mouth and the short ones at the nostrils; the four on the chin.
uniform vec3 barbel : source_color = vec3(0.05, 0.055, 0.06);
uniform vec3 barbel_chin : source_color = vec3(0.36, 0.37, 0.36);
// The eye's iris.
uniform vec3 iris : source_color = vec3(0.5, 0.5, 0.42);
// How strongly the spots show (0 none: a big old slate one; 1 a young silvery one).
uniform float spots_show = 0.85;

// Cartoon eyes (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0, the default, is the eye drawn below, as it always was; 1 is the cartoon eye:
// grown about its middle, a pale white, a coloured iris, a big dark pupil, a highlight that stays
// put (up and forward, towards the light) and a dark rim, under an upper lid. The channel catfish's:
// a sleepy, unbothered old bottom-feeder, a heavy level lid half way down, a pale gold iris and a
// level bar of a pupil.
uniform float cartoon_eyes = 0.0;
// Where the pupil looks, in the eye's own plane: x forward (towards the snout; -1 back towards the
// tail), y up; -1..1. Only the cartoon eye's pupil moves.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat from above and below and a lid of `lid_colour` closes over it.
uniform float blink = 0.0;
// How much bigger the cartoon eye is drawn, and how fast the head's skin falls away round it (1 / (2 x
// its radius there), per metre); its white, its iris (`cartoon_iris`: `iris` is the eye's as it
// was; how wide, of the eye's face to its rim), its pupil (how wide, of the iris; 0 round, 1 an
// upright slit, 2 a level bar, 3 a keyhole), where the upper lid's edge rests (1 the top of the eye,
// no lid; 0 its middle) and how much lower it comes at the front (a frown).
uniform float eye_grow = 2.0;
// (eye_sink: 0, not sunk, looked cleanest on all of them: sunk, the rim dipped under the skin and came
// out again below the eye as a dark crescent)
uniform float eye_sink = 0.0;
uniform vec3 eye_white : source_color = vec3(0.95, 0.94, 0.86);
uniform vec3 cartoon_iris : source_color = vec3(0.86, 0.76, 0.42);
uniform float iris_size = 0.64;
uniform float pupil_size = 0.62;
uniform int pupil_shape = 2;
uniform float lid = 0.12;
uniform float lid_slant = 0.0;
uniform vec3 lid_colour : source_color = vec3(0.2, 0.25, 0.29);
// As the model has it (the build script prints it): the right eye's middle on the skin and the way
// it faces (metres), and its radius over the skin (`EYE_AT`, `EYE_RADIUS`: metres behind the snout,
// metres up).
const vec3 EYE_MIDDLE = vec3(0.03922, -0.0115, -0.25);
const vec3 EYE_OUT = vec3(0.9374, 0.276, -0.2123);
const vec2 EYE_AT = vec2(0.05, -0.0115);
const float EYE_RADIUS = 0.0062;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float whisker;

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
// runs back along it, small at the head, least just behind it, widest at the tail.
// (ChannelCatfish._side_at is the same: its barbels' roots go with the head.)
float side_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * (0.012 - 0.04 * s + 0.118 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// How much of the jaw's swing a point `xm` metres behind the snout takes: all of it ahead of the
// corners of the mouth, none at the belly (as the model has it: `jaw_turn`).
float jaw_turn(float xm) {
	return 1.0 - smoothstep(MOUTH_TO - 0.005, JAW_BACK, xm);
}

// `v` (and its normal `n`) swung down about the jaw's hinge by `a` radians.
void swing(inout vec3 v, inout vec3 n, float a) {
	vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
	vec2 d = v.yz - hinge;
	v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
	n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
}

vec3 rope_point(int i, int row) {
	return texelFetch(ropes, ivec2(clamp(i, 0, POINTS - 1), row), 0).xyz;
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
	vec3 ring = mix(cartoon_iris * 1.2, cartoon_iris * 0.6, smoothstep(0.25, 0.95, ri));
	ring = mix(ring, cartoon_iris * 0.25, smoothstep(0.82, 1.0, ri));
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
	rest_normal = NORMAL;
	whisker = 0.0;
	if (part > 7.5 && part < 8.5) {
		// A barbel: laid along a smooth curve through its rope's points, a tapering round tube.
		whisker = floor(UV2.x);
		float thick = fract(UV2.x) * 0.01 * barbel_thick;
		int row = int(whisker + 0.5);
		float s = clamp(UV.x, 0.0, 1.0);
		float f = s * float(POINTS - 1);
		int i = min(int(f), POINTS - 2);
		float t = f - float(i);
		vec3 p0 = rope_point(i - 1, row);
		vec3 p1 = rope_point(i, row);
		vec3 p2 = rope_point(i + 1, row);
		vec3 p3 = rope_point(i + 2, row);
		vec3 at = 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * (p1 - p2) + p3 - p0) * t * t * t);
		vec3 along = 0.5 * ((p2 - p0) + 2.0 * (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t + 3.0 * (3.0 * (p1 - p2) + p3 - p0) * t * t);
		along = normalize(along + vec3(0.0, 0.0, 1e-7));
		vec3 e1 = mix(rope_point(i, row + 8), rope_point(i + 1, row + 8), t);
		e1 = normalize(e1 - along * dot(e1, along) + vec3(1e-7, 0.0, 0.0));
		vec3 e2 = cross(along, e1);
		float a = UV.y * 6.2831853;
		// (as the model has it: how thick it is `s` along it)
		float r = thick * (1.0 - 0.72 * s) * sqrt(min(1.0, (1.0 - s) * 30.0));
		vec3 out_way = e1 * cos(a) + e2 * sin(a);
		VERTEX = at + out_way * r;
		NORMAL = out_way;
	} else {
		vec3 v = VERTEX;
		vec3 n = NORMAL;
		if (part > 6.5 && part < 7.5) {
			eye_shape(v);
		}
		if (part > 8.5 && part < 9.5) {
			// The lower jaw swings down about its hinge: all of it ahead of the corners of the
			// mouth, its back less and less, as the throat stretches.
			swing(v, n, clamp(gape, 0.0, 1.0) * GAPE_TURN * jaw_turn(v.z + HALF));
		} else if (part > 9.5) {
			// A cheek hangs between the lips: the model has it as it is with the mouth wide open;
			// it folds up along the line of the mouth as the mouth shuts (each point swung as far
			// as it is down the cheek, UV2.x).
			swing(v, n, (clamp(gape, 0.0, 1.0) - 1.0) * GAPE_TURN * jaw_turn(UV.x * LENGTH) * UV2.x);
		}
		float xm = v.z + HALF;
		float h = side_at(xm);
		float slope = (side_at(xm + 0.004) - side_at(xm - 0.004)) / 0.008;
		float turn = atan(slope);
		float c = cos(turn);
		float sn = sin(turn);
		VERTEX = vec3(h + v.x * c, v.y, v.z - v.x * sn);
		NORMAL = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
		vec3 curled = VERTEX;
		vec3 curled_normal = NORMAL;
		curl_bend(curled, curled_normal);
		VERTEX = curled;
		NORMAL = curled_normal;
	}
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return -0.0236 - 0.14 * xm;
}

float gill_x(float y) {
	return 0.138 - 13.0 * (y + 0.012) * (y + 0.012);
}

// The fine rays of a fin: `count` of them across it.
float rays(float across, float count) {
	return pow(abs(cos(3.14159265 * across * count)), 6.0);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

