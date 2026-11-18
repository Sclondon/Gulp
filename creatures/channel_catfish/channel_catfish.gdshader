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
render_mode cull_back;

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
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.5;
	float spec = 0.3;
	if (p == 0 || p == 9) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float h = UV.y;
		// (how far round the side, in metres, so that marks are not stretched over the back)
		float round_side = acos(clamp(1.0 - 2.0 * h, -1.0, 1.0)) / 3.14159265 * 0.15;
		float cloud = noise2(vec2(xm * 34.0, round_side * 60.0));
		float mottle = noise2(vec2(xm * 110.0 + 3.0, round_side * 150.0));
		// The white of the belly reaches from the chin to the anal fin; behind that the underside
		// is grey. The dark of the back comes down the side softly, lowest on the head.
		float behind_belly = smoothstep(0.3, 0.44, xm);
		float low_edge = mix(0.2, -0.2, behind_belly) + (cloud - 0.5) * 0.09;
		float on_head = 1.0 - smoothstep(0.1, 0.17, xm);
		float high_edge = mix(0.52, 0.44, on_head) + (cloud - 0.5) * 0.07;
		c = mix(belly, side, smoothstep(low_edge, low_edge + 0.2, h));
		// (the lower side faintly clouded, where it is neither belly nor back)
		float flank = smoothstep(low_edge + 0.12, low_edge + 0.3, h) * (1.0 - smoothstep(0.5, 0.64, h));
		c = mix(c, c * 1.1, smoothstep(0.45, 0.85, mottle) * flank * 0.5);
		c = mix(c, c * 0.88, smoothstep(0.5, 0.9, cloud) * flank * 0.6);
		vec3 top = mix(back_blue, back, smoothstep(high_edge + 0.02, high_edge + 0.34, h));
		top *= 0.97 + 0.06 * mottle;
		top += back_blue * 0.55 * glance * glance;
		float dark = smoothstep(high_edge - 0.2, high_edge + 0.14, h);
		c = mix(c, top, dark);
		// The spots: small, dark, scattered unevenly over the side from the gill cover to the tail.
		vec2 where = vec2(xm, round_side) / 0.017;
		vec2 cell = floor(where);
		float marked = 0.0;
		for (int ix = -1; ix <= 1; ix++) {
			for (int iy = -1; iy <= 1; iy++) {
				vec2 one = cell + vec2(float(ix), float(iy));
				float has = step(0.5, hash2(one + 17.0));
				vec2 middle = one + vec2(0.15) + 0.7 * vec2(hash2(one + 3.7), hash2(one + 9.1));
				float wide = 0.07 + 0.1 * hash2(one + 21.3);
				marked = max(marked, has * (1.0 - smoothstep(wide * 0.6, wide, length(where - middle))));
			}
		}
		float spotted = smoothstep(0.125, 0.16, xm) * (1.0 - smoothstep(0.47, 0.52, xm)) * smoothstep(low_edge + 0.08, low_edge + 0.2, h) * (1.0 - smoothstep(0.86, 0.97, h));
		c = mix(c, spot, marked * spotted * spots_show * mix(0.9, 0.55, dark));
		// The lateral line: a row of small pale pores from the top of the gill cover to the tail.
		float line_y = mix(0.014, 0.001, smoothstep(0.13, 0.5, xm));
		float pores = (1.0 - smoothstep(0.0003, 0.0011, abs(y - line_y))) * smoothstep(0.3, 0.75, abs(fract(xm / 0.0052) - 0.5) * 2.0);
		c = mix(c, c * 1.35 + 0.04, pores * 0.32 * smoothstep(0.138, 0.15, xm) * (1.0 - smoothstep(0.5, 0.53, xm)));
		// The head: the line of the mouth and the pale lips round it, the gill cover's edge, the
		// nostrils (the front pair near the tip of the snout, the rear pair behind the barbels).
		float mouth_fade = smoothstep(0.0, 0.002, xm) * (1.0 - smoothstep(MOUTH_TO - 0.004, MOUTH_TO + 0.001, xm));
		float from_mouth = abs(y - mouth_y(xm));
		c = mix(c, lip, (1.0 - smoothstep(0.0012, 0.0042, from_mouth)) * mouth_fade * 0.55);
		c = mix(c, vec3(0.03, 0.022, 0.025), (1.0 - smoothstep(0.0003, 0.001, from_mouth)) * mouth_fade * 0.9);
		float span = smoothstep(0.03, 0.12, h) * (1.0 - smoothstep(0.86, 0.96, h));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.002, abs(behind - 0.001))) * 0.3 + (1.0 - smoothstep(0.0, 0.016, behind)) * step(0.0, behind) * 0.2;
		c = mix(c, c * 0.5, crease * span);
		// (the body runs into the tail fin)
		c = mix(c, back, smoothstep(0.5, 0.54, xm) * 0.85);
		if (rest_normal.y > 0.2) {
			float front = length(vec2(abs(rest.x) - 0.0105, xm - 0.0075));
			float rear = length(vec2(abs(rest.x) - 0.0128, xm - 0.0298));
			c = mix(c, vec3(0.012, 0.012, 0.015), max(1.0 - smoothstep(0.0009, 0.0016, front), 1.0 - smoothstep(0.0012, 0.002, rear)));
			c = mix(c, c * 1.5, (1.0 - smoothstep(0.0016, 0.0028, front)) * smoothstep(0.0012, 0.0018, front) * 0.4);
		}
		// (scaleless, slimy skin: smooth and wet)
		rough = mix(0.26, 0.36, dark);
		spec = 0.55;
		// The inside of the mouth (its roof and floor, which the model marks: seen when it gapes).
		float lined = smoothstep(0.0, 0.12, UV2.x);
		c = mix(c, mouth_inside, lined);
		rough = mix(rough, 0.7, lined);
		spec = mix(spec, 0.3, lined);
	} else if (p == 1) {
		// The dorsal: dusky, darker towards its edge, a pale stiff spine up its front, soft rays.
		c = mix(fin, fin_edge, smoothstep(0.35, 1.0, UV.x) * 0.8);
		c = mix(c, c * 0.62, rays(UV.y, 7.0) * 0.6);
		c = mix(c, back_blue * 1.1, (1.0 - smoothstep(0.02, 0.07, UV.y)) * 0.7);
		c = mix(c, back, (1.0 - smoothstep(0.0, 0.22, UV.x)) * 0.8);
		c += back_blue * 0.3 * glance * glance;
	} else if (p == 2) {
		// The adipose fin: flesh, the colour of the back, a little paler towards its rim.
		c = mix(back, back_blue, 0.25 + 0.45 * smoothstep(0.3, 1.0, UV.x));
		c += back_blue * 0.4 * glance * glance;
		rough = 0.3;
	} else if (p == 3) {
		// The anal fin: pale grey at its root, dusky further out, a dark edge, many fine rays.
		c = mix(fin_pale, fin, smoothstep(0.05, 0.55, UV.x));
		c = mix(c, fin_edge, smoothstep(0.72, 1.0, UV.x) * 0.85);
		c = mix(c, c * 0.7, rays(UV.y, 27.0) * 0.5 * smoothstep(0.05, 0.3, UV.x));
	} else if (p == 4) {
		// The tail: dusky, darker to its edge, its rays fanning out.
		c = mix(fin, fin_edge, smoothstep(0.45, 1.0, UV.x) * 0.75 + smoothstep(0.8, 1.0, UV.y) * 0.3);
		c = mix(c, back, (1.0 - smoothstep(0.0, 0.28, UV.x)) * 0.85);
		c = mix(c, c * 0.68, rays(UV.y, 9.0) * 0.5 * smoothstep(0.15, 0.4, UV.x));
		c += back_blue * 0.3 * glance * glance;
	} else if (p == 5) {
		// A pectoral fin: a pale spine along its front, dusky above, paler below.
		float above = smoothstep(-0.15, 0.15, rest_normal.y);
		c = mix(mix(fin_pale * 0.9, fin, 0.35), mix(fin, fin_edge, smoothstep(0.4, 1.0, UV.x) * 0.6), above);
		c = mix(c, c * 0.7, rays(UV.y, 9.0) * 0.5 * smoothstep(0.1, 0.3, UV.x));
		c = mix(c, fin_pale, (1.0 - smoothstep(0.03, 0.1, UV.y)) * 0.65);
	} else if (p == 6) {
		// A pelvic fin: pale, dusky towards its tip.
		c = mix(fin_pale, fin, smoothstep(0.25, 1.0, UV.x) * 0.8);
		c = mix(c, c * 0.75, rays(UV.y, 8.0) * 0.45 * smoothstep(0.1, 0.3, UV.x));
	} else if (p == 7) {
		// An eye: small; a round dark pupil, a pale iris, a dark rim.
		float r = UV.x;
		c = mix(vec3(0.004, 0.005, 0.008), iris * (0.8 + 0.25 * noise2(vec2(atan(rest.y + 0.0115, rest.z + 0.25) * 7.0, 1.5))), smoothstep(0.54, 0.62, r));
		c = mix(c, back * 0.6, smoothstep(0.76, 0.95, r));
		// (where it is on the eye's face: x up, y forward, 1 at its rim, as the model lays it on the skin)
		vec2 e = vec2(rest.y - EYE_AT.y, EYE_AT.x - (rest.z + HALF)) / EYE_RADIUS;
		if (cartoon_eyes > 0.0) {
			c = mix(c, cartoon_eye(e), cartoon_eyes);
		}
		// (the upper lid: none on the eye as it was, until it blinks)
		float lid_edge = mix(mix(1.3, lid, cartoon_eyes) - lid_slant * cartoon_eyes * e.y, -1.3, blink);
		c = mix(c, vec3(0.02), smoothstep(lid_edge - 0.16, lid_edge - 0.06, e.x) * step(lid_edge, 1.2));
		c = mix(c, lid_colour, smoothstep(lid_edge - 0.05, lid_edge, e.x));
		rough = 0.1;
		spec = 0.7;
	} else if (p == 10) {
		// A cheek: the inside of the mouth.
		c = mouth_inside * (0.8 + 0.4 * UV2.x);
		rough = 0.7;
		spec = 0.3;
	} else {
		// A barbel: the mouth's and the nostrils' dark; the chin's four paler, dusky to their tips.
		float chin = step(1.5, whisker) * (1.0 - step(5.5, whisker));
		c = mix(barbel, mix(barbel_chin, barbel * 2.0, smoothstep(0.2, 1.0, UV.x)), chin);
		c += back_blue * 0.25 * glance;
		rough = 0.35;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
