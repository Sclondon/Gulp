shader_type spatial;
// The river beast (river_beast.gd): every marking drawn here (no texture files), its swimming, its
// mouth, its eyes, and its standing up (`stand`). What each point is comes from the model
// (tools/build_river_beast.py): UV2.y the part (0 body and tail, 1 lower jaw, 2 an upper tooth, 3 a
// lower tooth, 5 an arm, 6 a hind leg, 7 an eye); UV2.x, on the body and the jaw, how much it is
// inside the mouth; on a limb, how far along it from its root (metres, as built). UV, on the body and
// jaw: x how far along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a
// limb: x along it, y 1 on a claw; on an eye: x middle (0) to rim (1). On a clump of fur, UV.y is 2 +
// how far from its root to its tip.
//
// The model is built SWIMMING, as a beaver swims at the surface: its arms tucked under its chest, its
// hind legs trailing beside its tail. Swimming, its broad tail sculls side to side and its hind feet
// kick by turns. `stand` stands it up on its hind legs, each move a turn about a hinge (Pivot Painter
// style: the hinges are constants here and each point knows what it belongs to): the hind legs swing
// down under it (hip, knee, ankle, the far joint first), the body turns up about the hips, the head
// comes back to level, the arms hang bent in front of the chest, the tail drops to the ground behind
// and lies along it. All of it is a function of `phase` and the settings, so a picture of it loops
// exactly. Nothing here needs more than GL Compatibility.
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
const float LENGTH = 3.93;
const float HALF = 1.965;
const float CORNER = 0.58;
const float HINGE_Y = -0.012;
const float HINGE_SPREAD = 0.1;
const vec2 EYE_AT = vec2(0.49, 0.112);
const float JAW_FROM = 0.04;
const float FUR_FROM = 0.76;
const float FUR_TO = 2.68;
const vec2 SHOULDER = vec2(1.26, -0.26);
const vec2 ELBOW = vec2(1.58, -0.44);
const vec2 WRIST = vec2(1.9, -0.46);
const float AT_ELBOW = 0.3758;
const float AT_WRIST = 0.6965;
const vec2 HIP = vec2(2.28, -0.13);
const vec2 KNEE = vec2(2.73, -0.31);
const vec2 ANKLE = vec2(3.13, -0.29);
const float AT_KNEE = 0.5383;
const float AT_ANKLE = 0.939;
// Standing: how far each joint turns (radians; more than 0 swings what lies behind it down): the arm's
// shoulder, elbow, wrist; the leg's hip, knee, ankle; the body up about the hips; the head back to
// level about the neck; the tail down about its root and flat again further along.
const vec3 STAND_ARM = vec3(-0.05, 1.22, -0.87);
const vec3 STAND_LEG = vec3(1.31, 0.1, 1.8);
const float STAND_BODY = 1.36;
const vec2 NECK = vec2(0.8, 0.0);
const float STAND_HEAD = -1.42;
const vec2 TAIL_ROOT = vec2(2.42, -0.05);
const float STAND_TAIL = 1.15;
const vec2 TAIL_MID = vec2(2.85, -0.02);
const float STAND_TAIL_MID = -0.62;
// How far the lower jaw swings down for `gape` 1, how far the skull lifts with it.
const float GAPE_MAX = 0.85;
const float LIFT_MAX = 0.14;

// How far through a beat (0..1, it wraps). Set by RiverBeast.
uniform float phase = 0.0;
// How many times its tail sculls and its feet kick in one beat (a whole number).
uniform float tail_beats = 1.0;
// Turning: how far the body is bent round behind the neck, radians from the neck to the tip of the
// tail (more than 0 the tail comes round to +X). It fades out as it stands.
uniform float curl = 0.0;
// How hard it swims: 1 cruising (the tail's tip swings about 0.22 m each way, the feet kick).
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape = 0.0;
// 0 swimming along the surface, 1 standing on its hind legs.
uniform float stand = 0.0;
// How long the wave down its tail is, in body lengths.
uniform float wave = 0.7;

// Its coat (the root of a clump, its middle, its tip), its scales (above, below), its claws, the
// inside of its mouth, its teeth.
uniform vec3 fur_root : source_color = vec3(0.1, 0.06, 0.03);
uniform vec3 fur : source_color = vec3(0.33, 0.21, 0.1);
uniform vec3 fur_tip : source_color = vec3(0.52, 0.38, 0.2);
uniform vec3 scale_top : source_color = vec3(0.24, 0.25, 0.16);
uniform vec3 scale_under : source_color = vec3(0.6, 0.56, 0.4);
uniform vec3 claw : source_color = vec3(0.06, 0.05, 0.04);
uniform vec3 mouth : source_color = vec3(0.6, 0.38, 0.3);
uniform vec3 tooth : source_color = vec3(0.88, 0.84, 0.7);
// How wet its coat looks (0 dry and dull, 1 slick with water).
uniform float wet = 0.7;

uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// Where the right eye sits, as the model has it (the build script prints it: EYE_FRAME).
const vec3 EYE_CENTRE = vec3(0.14900, 0.11200, -1.47500);
const vec3 EYE_OUT = vec3(0.6413, 0.7464, -0.1778);
const vec3 EYE_FWD = vec3(-0.1158, -0.1348, -0.9841);
const vec3 EYE_UP = vec3(-0.7585, 0.6517, 0.0000);
const float EYE_SAG = 2.5903;
const float EYE_RADIUS = 0.03;
// The river beast's: a wary old grouch. Bigger than life by 2.2; a green-gold iris and a fat
// crocodile's slit, the lids heavy and low (a suspicious squint): the upper lid drawn down across the
// top third and slanting in towards the snout, the lower lid pushed up from beneath.
const float EYE_GROW = 2.2;
const vec3 SCLERA = vec3(0.84, 0.82, 0.62);
const vec3 IRIS_LIGHT = vec3(0.82, 0.8, 0.3);
const vec3 IRIS_DARK = vec3(0.36, 0.42, 0.1);
const float IRIS = 0.72;
const vec2 IRIS_AT = vec2(0.03, -0.06);
const vec2 LOOK_REACH = vec2(0.22, 0.12);
const vec2 GLINT_AT = vec2(0.22, 0.12);
const float GLINT = 0.1;
const vec2 GLINT2_AT = vec2(-0.2, -0.26);
const vec3 OUTLINE = vec3(0.03, 0.02, 0.01);
const float LINE_UP = 0.17;
const float LINE_DOWN = 0.07;

float pupil(vec2 q) {
	return (length(q / vec2(0.16, 0.52)) - 1.0) * 0.16;
}

float lid_up(float x) {
	return 0.3 - 0.22 * x - 0.1 * x * x;
}

float lid_down(float x) {
	return -0.5 + 0.06 * x + 0.14 * x * x;
}

vec3 lid_colour() {
	return scale_top * 0.85;
}

varying vec2 eye_at;

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

vec3 cartoon_eye(vec2 e, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 q = e - IRIS_AT - clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK_REACH;
	float qi = length(q);
	vec3 c = SCLERA * (1.0 - 0.25 * smoothstep(0.5, 0.86, r));
	float rays = 0.5 + 0.5 * sin(atan(q.y, q.x) * 21.0);
	vec3 iris = mix(IRIS_LIGHT, IRIS_DARK, smoothstep(IRIS * 0.2, IRIS, qi) * 0.85 + rays * 0.14);
	c = mix(c, iris, 1.0 - smoothstep(IRIS - aa, IRIS + aa, qi));
	c = mix(c, vec3(0.005), 1.0 - smoothstep(-aa * 0.3, aa * 0.3, pupil(q)));
	float glint = max(1.0 - smoothstep(GLINT - aa, GLINT + aa, length(e - GLINT_AT)),
		1.0 - smoothstep(GLINT * 0.4 - aa, GLINT * 0.4 + aa, length(e - GLINT2_AT)));
	c = mix(c, vec3(1.0), glint);
	lit = mix(0.45, 1.0, glint);
	c = mix(c, OUTLINE, smoothstep(0.84 - aa, 0.86 + aa, r));
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
varying float clump;

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

// Turns `v` and `n` by `a` about a line across the body (along X) through `pivot` (xm, y): more than
// 0 turns what lies behind the pivot down (and what lies ahead of it up).
void hinge(inout vec3 v, inout vec3 n, vec2 pivot, float a) {
	vec2 p = vec2(pivot.y, pivot.x - HALF);
	vec2 d = v.yz - p;
	float c = cos(a);
	float s = sin(a);
	v.yz = p + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
	n.yz = vec2(n.y * c - n.z * s, n.y * s + n.z * c);
}

// How far to the side the tail is, `xm` behind the tip of the snout: a sculling wave growing to its tip.
float side_at(float xm) {
	float s = clamp((xm - 2.1) / (LENGTH - 2.1), 0.0, 1.0);
	return sway * 0.22 * s * s * sin(TAU * (tail_beats * phase - xm / (LENGTH * wave)));
}

void curl_bend(inout vec3 v, inout vec3 n, float bend) {
	float from = 0.8 - HALF;
	float d = v.z - from;
	if (abs(bend) < 0.001 || d <= 0.0) {
		return;
	}
	float k = bend / (LENGTH - 0.8);
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
	inside = UV2.x;
	clump = UV.y > 1.5 ? UV.y - 2.0 : -1.0;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	eye_at = vec2(0.0);
	if (p == 0 && clump >= -0.5) {
		// (a clump of fur on the body is shaded much as the coat under it is: its normal leans to the
		// body's, out from the middle line, as fur cards take the normals of the skin they grow on)
		n = normalize(mix(n, normalize(vec3(v.x, v.y + 0.05, 0.0)), 0.85));
	}
	if (p == 7) {
		vec2 at;
		eye_grow(v, at);
		eye_at = at;
	}
	float open = clamp(gape, 0.0, 1.0);
	if (p == 1 || p == 3) {
		hinge(v, n, vec2(CORNER, HINGE_Y), -GAPE_MAX * open * smoothstep(CORNER + 0.03, CORNER - HINGE_SPREAD, v.z + HALF));
	} else if ((p == 0 || p == 2 || p == 7) && open > 0.0) {
		float w = smoothstep(CORNER + 0.2, CORNER - 0.04, v.z + HALF) * smoothstep(HINGE_Y - 0.06, HINGE_Y + 0.02, v.y);
		hinge(v, n, vec2(CORNER, HINGE_Y), LIFT_MAX * open * w);
	}
	float st = clamp(stand, 0.0, 1.0);
	float swim = 1.0 - st;
	float beat = TAU * tail_beats * phase;
	float along = UV2.x;
	float xm0 = v.z + HALF;
	if (p == 6) {
		// A hind leg: kicking by turns as it swims (the foot flexing after the thigh), swung down
		// under it as it stands; the foot, then the shin, then the whole leg, each about its joint.
		float side = rest.x >= 0.0 ? 0.0 : PI;
		float kick = sway * swim * 0.38 * sin(beat + side);
		float flex = sway * swim * 0.5 * sin(beat + side - 1.2);
		hinge(v, n, ANKLE, (STAND_LEG.z * st + flex) * smoothstep(AT_ANKLE - 0.03, AT_ANKLE + 0.05, along));
		hinge(v, n, KNEE, STAND_LEG.y * st * smoothstep(AT_KNEE - 0.05, AT_KNEE + 0.05, along));
		hinge(v, n, HIP, STAND_LEG.x * st + kick);
	} else {
		if (p == 5) {
			// An arm: the hand, then the forearm, then the whole arm about the shoulder; then, as
			// part of the body, up with it.
			hinge(v, n, WRIST, STAND_ARM.z * st * smoothstep(AT_WRIST - 0.03, AT_WRIST + 0.04, along));
			hinge(v, n, ELBOW, STAND_ARM.y * st * smoothstep(AT_ELBOW - 0.05, AT_ELBOW + 0.05, along));
			hinge(v, n, SHOULDER, STAND_ARM.x * st);
		} else {
			// The head back towards level about the neck; the tail down to the ground and flat along it.
			hinge(v, n, NECK, STAND_HEAD * st * smoothstep(NECK.x + 0.12, NECK.x - 0.12, xm0));
			float tail = smoothstep(TAIL_ROOT.x - 0.15, TAIL_ROOT.x + 0.1, xm0);
			hinge(v, n, TAIL_MID, STAND_TAIL_MID * st * smoothstep(TAIL_MID.x - 0.1, TAIL_MID.x + 0.15, xm0));
			hinge(v, n, TAIL_ROOT, STAND_TAIL * st * tail);
		}
		// The body (and the arms on it) up about the hips, breathing a little as it stands.
		float body = p == 5 ? 1.0 : smoothstep(HIP.x + 0.12, HIP.x - 0.18, xm0);
		hinge(v, n, HIP, (STAND_BODY + 0.025 * sin(beat)) * st * body);
	}
	// The tail sculls side to side (by where it lies as built: it swishes along the ground as it stands).
	float h = side_at(xm0);
	float slope = (side_at(xm0 + 0.02) - side_at(xm0 - 0.02)) / 0.04;
	float turn = atan(slope);
	if (p != 6) {
		v.x += h;
		n = vec3(n.x * cos(turn) + n.z * sin(turn), n.y, -n.x * sin(turn) + n.z * cos(turn));
	}
	curl_bend(v, n, curl * swim);
	VERTEX = v;
	NORMAL = n;
}

float mouth_y(float xm) {
	return -0.035 - 0.012 * xm + 0.03 * smoothstep(0.34, 0.58, xm);
}

// Scales: a grid of rounded plates `size` metres across in the plane (a, b), dark in the seams.
float plates(vec2 q) {
	vec2 cell = q;
	cell.x += 0.5 * floor(cell.y) + 0.35 * noise2(vec2(floor(cell.y) * 3.1, cell.x * 0.3));
	vec2 f = fract(cell) - 0.5;
	float jag = 0.06 * noise2(floor(cell) * 1.7);
	float d = max(abs(f.x), abs(f.y)) + jag;
	return smoothstep(0.52, 0.4, d);
}

// The scaly hide at a place, `h` how high on the side (0 belly .. 1 back).
vec3 scaly(vec2 q, float h, float spots) {
	vec3 c = mix(scale_under, scale_top, smoothstep(0.25, 0.55, h));
	c = mix(c, c * 0.45, smoothstep(0.55, 0.75, spots) * smoothstep(0.35, 0.6, h));
	float pl = plates(q);
	return c * mix(0.7, 1.04, pl) * (0.9 + 0.12 * noise2(q * 0.37));
}

// The coat under and between the clumps: dark, streaked lengthways in wet clumps.
vec3 coat(float xm, float across) {
	float streak = noise2(vec2(xm * 6.0, across * 40.0)) * 0.7 + noise2(vec2(xm * 14.0, across * 90.0)) * 0.3;
	return mix(mix(fur_root, fur, 0.4), fur * 0.9, smoothstep(0.3, 0.8, streak) * 0.8);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

