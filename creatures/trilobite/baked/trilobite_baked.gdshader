shader_type spatial;
// The trilobites (trilobite.gd): every marking drawn here (no texture files), their walking, their
// beating gills, their antennae and their rolling up (`enroll`), and their cartoon eyes. One shader
// for every kind: what differs between them (their size, where the head shield ends and the tail
// shield begins, how many body segments, their colours, their cartoon eye) are settings that
// Trilobite sets from its KINDS. What each point is comes from the model
// (tools/build_trilobite.py): UV2.y the part times 16 plus which one of them it is (0 the shell,
// 1 a walking leg (which pair, 0 the first), 2 a gill (its leg's pair), 3 an eye, 4 an antenna,
// 5 a spine (0 a cheek spine, 1 a body segment's, 2 one up its back, 3 one behind its tail, 4 the
// third segment's long ones)); the colour's red, green and blue the place the part grows from or
// turns about (in the box BOX_MIN to BOX_MAX, times its length); the colour's alpha one more number
// (on a leg 0 above the knee and 1 below it; along a gill, an antenna or a spine 0 at its root to 1
// at its tip); on a leg or a gill UV.x, UV.y and UV2.x the place of its knee.
//
// It walks forwards on its legs in waves running from back to front (no skeleton: each leg is two
// stiff lengths worked out so that a foot on the ground stays put), its gills swing with its legs,
// its antennae feel about, and with `enroll` it rolls up into a ball, its head shield and its tail
// shield meeting beneath. All of it is a function of `phase` (and the settings) alone, so a picture
// of it loops exactly. Nothing here needs more than GL Compatibility has.
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


// Kept in step with the model, as shares of its length: the box the places are written in; how far
// out along a leg (from its joint to its tip, seen from above) its knee is.
const vec3 BOX_MIN = vec3(-0.9, -0.1, -0.9);
const vec3 BOX_MAX = vec3(0.9, 0.6, 1.0);
const float KNEE_AT = 0.45;
// How much of a step a foot spends on the ground; how far it moves in one step at `walk` 1, and how
// high it is lifted (shares of its length); how far apart (a share of a step) one pair of legs is
// from the pair behind it.
const float ON_GROUND = 0.6;
const float STRIDE = 0.05;
const float LIFT = 0.025;
const float LEG_LAG = 0.14;
// Rolled up: how far it bends (radians, all along it, at `enroll` 1), and how much less its head and
// tail shields bend than its body segments.
const float ENROLL_MAX = 5.75;
const float SHIELD_BEND = 0.5;
// Rolled up, how far the sides of its shell curl down as well (so that the ball closes at its sides).
const float SIDE_CURL = 0.9;

// The kind, as Trilobite's KINDS has it (shares of its length, but `size`): its length in metres;
// how high the bottom of its shell's rim stands; where its head shield ends and its tail shield
// begins (z); how many body segments it has; how high the top of its shell stands above the rim's
// bottom; how wide its middle lobe is (each side); how strongly its tail shield is ringed.
uniform float size = 0.15;
uniform float venter = 0.06;
uniform float head_back = -0.12;
uniform float tail_front = 0.12;
uniform float segments = 10.0;
uniform float top_height = 0.24;
uniform float lobe = 0.12;
uniform float tail_rings = 0.0;
// Its colours: the shell, its dark markings, its pale underside, its legs, gills and antennae.
uniform vec3 shell : source_color = vec3(0.62, 0.42, 0.22);
uniform vec3 dark : source_color = vec3(0.32, 0.18, 0.08);
uniform vec3 under : source_color = vec3(0.85, 0.75, 0.6);
uniform vec3 limb : source_color = vec3(0.8, 0.5, 0.4);

// How far through one cycle of its steps (0..1, it wraps). Set by Trilobite.
uniform float phase = 0.0;
// Walking: 0 standing, 1 a walk forwards, -1 backwards; more is a longer stride.
uniform float walk = 0.0;
// How far its antennae swing (radians at their tips) and its gills beat.
uniform float feel = 0.25;
// 0 spread out, 1 rolled up into a ball.
uniform float enroll : hint_range(0.0, 1.0) = 0.0;

// Cartoon eyes: 0 its eyes as they are (crescents of tiny lenses), 1 the cartoon eye, each kind its
// own (Trilobite's KINDS: the smooth one's wide, innocent stare, the spiny one's suspicious squint,
// the cheek-spined one's sleepy droop). `eye_look` slides the iris and pupil (x towards its front, y
// up, -1..1); `blink` brings a lid the colour of its shell down over each eye (0 open, 1 shut),
// cartoon or not.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// The kind's cartoon eye: the way the left one looks; how much bigger it is; its iris; how wide the
// iris and the pupil are (as the sine of the angle from where it looks); the pupil's shape (its
// width and height); where the upper lid rests (1 above the eye, -1 shut) and how it slopes (+ lower
// at the front).
uniform vec3 eye_gaze = vec3(1.0, 0.75, 0.05);
uniform float eye_grow = 1.6;
uniform vec3 iris : source_color = vec3(0.25, 0.65, 0.6);
uniform float iris_size = 0.56;
uniform float pupil_size = 0.3;
uniform vec2 pupil_shape = vec2(1.0, 1.0);
uniform float lid_rest = 1.0;
uniform float lid_slope = 0.0;
const vec3 EYE_WHITE = vec3(0.97, 0.96, 0.92);
const float LOOK_REACH = 0.3;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float index;
varying float along;
varying vec3 kk;
varying vec3 joint;

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

// `v` turned by `a` about the axis `k` (a unit vector).
vec3 turned(vec3 v, vec3 k, float a) {
	float c = cos(a);
	float s = sin(a);
	return v * c + cross(k, v) * s + k * dot(k, v) * (1.0 - c);
}

// Where a foot is in its step, `cycle` through it: x how far ahead of its middle place it stands
// (0.5 as it is set down, -0.5 as it is picked up), y how high it is lifted (0 on the ground, 1 at
// the top of its swing).
vec2 foot_at(float cycle) {
	float c = fract(cycle);
	if (c < ON_GROUND) {
		return vec2(0.5 - c / ON_GROUND, 0.0);
	}
	float u = (c - ON_GROUND) / (1.0 - ON_GROUND);
	return vec2(-0.5 * cos(3.14159265 * u), sin(3.14159265 * u));
}

// How a leg turns so that its tip is `shift` from where it stands at rest: about an upright axis
// through its joint (`yaw`), up about its joint (`lift`) and open at its knee (`open`). The leg is
// two stiff lengths in an upright plane: from its joint (`j`) to its knee (`knee`), and from the
// knee to its tip, which at rest is on the ground, the knee KNEE_AT of the way out to it (as the
// model is built). Worked out exactly (the two-length triangle), so a foot on the ground stays on
// it. `d` is set to the way the leg points, `axis` to the axis it lifts about.
void leg_turns(vec3 j, vec3 knee, vec3 shift, out vec3 d, out vec3 axis, out float yaw, out float lift, out float open) {
	vec2 flat_way = knee.xz - j.xz;
	float knee_out = length(flat_way);
	d = vec3(flat_way.x, 0.0, flat_way.y) / knee_out;
	vec3 up = vec3(0.0, 1.0, 0.0);
	axis = cross(d, up);
	float a = length(knee - j);
	vec3 tip = vec3(j.x, 0.0, j.z) + d * (knee_out / KNEE_AT);
	float b = length(tip - knee);
	vec2 was = vec2(knee_out / KNEE_AT, -j.y);
	vec3 to = tip + shift - j;
	vec3 across = cross(up, d);
	yaw = atan(dot(to, across), dot(to, d));
	vec2 now = vec2(length(to.xz), to.y);
	float l0 = length(was);
	float l1 = clamp(length(now), abs(a - b) + 0.00001, a + b - 0.00001);
	lift = atan(now.y, now.x) + acos(clamp((a * a + l1 * l1 - b * b) / (2.0 * a * l1), -1.0, 1.0))
			- atan(was.y, was.x) - acos(clamp((a * a + l0 * l0 - b * b) / (2.0 * a * l0), -1.0, 1.0));
	open = acos(clamp((a * a + b * b - l1 * l1) / (2.0 * a * b), -1.0, 1.0))
			- acos(clamp((a * a + b * b - l0 * l0) / (2.0 * a * b), -1.0, 1.0));
}

// How far along it and down a point of its bending middle line is, and how far it has turned, `s`
// metres from the middle of its body segments (one way: the segments `half` metres, then the
// shield), the segments bending by `kt` (radians a metre) and the shield by `ks`.
vec3 arc_at(float s, float half_len, float kt, float ks) {
	float s1 = min(s, half_len);
	float s2 = max(s - half_len, 0.0);
	float t1 = kt * s1;
	vec3 r = vec3(s1, 0.0, t1);
	if (kt > 1e-5) {
		r.xy = vec2(sin(t1), 1.0 - cos(t1)) / kt;
	}
	if (s2 > 0.0) {
		float t2 = t1 + ks * s2;
		if (ks > 1e-5) {
			r.xy += vec2(sin(t2) - sin(t1), cos(t1) - cos(t2)) / ks;
		} else {
			r.xy += vec2(cos(t1), sin(t1)) * s2;
		}
		r.z = t2;
	}
	return r;
}

// How far down the lowest point of it is when rolled, below the bottom of its rim, on the side
// whose length from the middle of its segments is `reach` (the shield's end): where it has turned
// half a turn, or its end if it does not get so far.
float lowest(float reach, float half_len, float kt, float ks) {
	float s = reach;
	float turn_mid = kt * half_len;
	if (turn_mid >= 3.14159265) {
		s = 3.14159265 / max(kt, 1e-5);
	} else if (turn_mid + ks * (reach - half_len) >= 3.14159265) {
		s = half_len + (3.14159265 - turn_mid) / max(ks, 1e-5);
	}
	vec3 r = arc_at(s, half_len, kt, ks);
	return r.y - top_height * size * min(cos(r.z), 0.0);
}

// Rolled up (`enroll`): the point `v` (and its normal `n`), bent along its middle line as the
// point of the middle line at `zb` (its own place along it, or for a part that is carried stiffly,
// the place it grows from) is.
void roll(inout vec3 v, inout vec3 n, float zb) {
	if (enroll < 0.001) {
		return;
	}
	float y0 = venter * size;
	float z0 = 0.5 * (head_back + tail_front) * size;
	float half_len = 0.5 * (tail_front - head_back) * size;
	float head_len = (head_back + 0.5) * size;
	float tail_len = (0.5 - tail_front) * size;
	float kt = enroll * ENROLL_MAX / (2.0 * half_len + SHIELD_BEND * (head_len + tail_len));
	float ks = kt * SHIELD_BEND;
	float d = zb - z0;
	float way = d >= 0.0 ? 1.0 : -1.0;
	vec3 r = arc_at(abs(d), half_len, kt, ks);
	float phi = way * r.z;
	vec3 o = vec3(v.x, v.y - y0, v.z - zb);
	float c = cos(r.z);
	float s = sin(phi);
	v = vec3(o.x, y0 - r.y + o.y * c - o.z * s, z0 + way * r.x + o.y * s + o.z * c);
	n = vec3(n.x, n.y * c - n.z * s, n.y * s + n.z * c);
	// lifted so that the ball rests on the ground
	float low = max(lowest(half_len + head_len, half_len, kt, ks), lowest(half_len + tail_len, half_len, kt, ks));
	v.y += max(low - y0, 0.0);
}

// The eye whose middle is `mid` (the left one if `mid`.x > 0): the way it looks, its up and its
// across (towards its front).
void eye_frame(vec3 mid, out vec3 gaze, out vec3 up, out vec3 across) {
	float side = mid.x >= 0.0 ? 1.0 : -1.0;
	gaze = normalize(eye_gaze * vec3(side, 1.0, 1.0));
	up = normalize(vec3(0.0, 1.0, 0.0) - gaze * gaze.y);
	across = normalize(cross(up, gaze)) * side;
}

// The colour of a point `p` (at rest) of the eye whose middle is `mid`: `plain` as it is, mixed to
// the cartoon eye by `cartoon_eyes`, the lid (`lid_skin`) over it as `blink` (and, cartooned,
// `lid_rest`) has it; `lid` is set to how far the lid covers it, `glint` to where the cartoon
// eye's highlights are.
vec3 eye_colour(vec3 p, vec3 mid, vec3 plain, vec3 lid_skin, out float lid, out float glint) {
	vec3 gaze, up, across;
	eye_frame(mid, gaze, up, across);
	vec3 d = normalize(p - mid);
	vec2 q = vec2(dot(d, across), dot(d, up));
	float front = smoothstep(-0.05, 0.1, dot(d, gaze));
	vec2 at = q - eye_look * LOOK_REACH;
	float r = length(at);
	vec3 c = EYE_WHITE;
	float in_iris = (1.0 - smoothstep(iris_size - 0.03, iris_size, r)) * front;
	float streaks = 0.85 + 0.15 * sin(atan(at.y, at.x) * 22.0);
	c = mix(c, iris * mix(1.25, 0.55, smoothstep(0.0, iris_size, r)) * streaks, in_iris);
	c = mix(c, vec3(0.03, 0.02, 0.02), (1.0 - smoothstep(0.015, 0.045, abs(r - iris_size))) * front);
	float pupil = 1.0 - smoothstep(pupil_size - 0.03, pupil_size, length(at / pupil_shape));
	c = mix(c, vec3(0.01, 0.01, 0.015), pupil * front);
	c = mix(plain, c, cartoon_eyes);
	// the upper lid: its edge comes down from above the eye (or from where it rests) to below it
	float edge = mix(mix(1.08, lid_rest, cartoon_eyes), -1.08, blink) - lid_slope * q.x * cartoon_eyes;
	lid = smoothstep(edge - 0.02, edge + 0.02, q.y);
	glint = smoothstep(0.955, 0.97, dot(d, normalize(gaze + up * 0.62 + across * 0.3)));
	glint = max(glint, 0.7 * smoothstep(0.991, 0.995, dot(d, normalize(gaze + up * 0.18 + across * 0.52))));
	glint *= 1.0 - lid;
	c = mix(c, lid_skin, lid);
	c = mix(c, lid_skin * 0.35, (1.0 - smoothstep(0.02, 0.07, abs(q.y - edge))) * step(edge, 1.0) * max(cartoon_eyes, step(0.001, blink)));
	return c;
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	float code = floor(UV2.y + 0.5);
	part = floor((code + 0.5) / 16.0);
	index = code - part * 16.0;
	along = COLOR.a;
	kk = vec3(UV.x, UV.y, UV2.x);
	joint = mix(BOX_MIN, BOX_MAX, COLOR.rgb) * size;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	float side = rest.x >= 0.0 ? 1.0 : -1.0;
	float zb = v.z;
	if (p == 1 || p == 2) {
		// A walking leg, or the gill on it: `index` its pair, 0 the first (the front); waves of steps
		// running from back to front, the two sides half a step apart. Rolled up, the legs fold in.
		float cycle = phase - LEG_LAG * index + (side > 0.0 ? 0.0 : 0.5);
		vec2 f = foot_at(cycle);
		float going = walk * (1.0 - enroll);
		vec3 shift = vec3(0.0, LIFT * size * min(abs(going), 1.0) * f.y, -going * STRIDE * size * f.x);
		vec3 d, axis;
		float yaw, lift, open;
		leg_turns(joint, kk, shift, d, axis, yaw, lift, open);
		if (p == 1) {
			if (along > 0.5) {
				v = kk + turned(v - kk, axis, open);
				n = turned(n, axis, open);
			}
			v = joint + turned(turned(v - joint, axis, lift), vec3(0.0, 1.0, 0.0), yaw);
			n = turned(turned(n, axis, lift), vec3(0.0, 1.0, 0.0), yaw);
		} else {
			// (a gill swings with its leg, beating a little)
			float beat = yaw + side * feel * 0.3 * sin(6.2831853 * cycle);
			v = joint + turned(v - joint, vec3(0.0, 1.0, 0.0), beat);
			n = turned(n, vec3(0.0, 1.0, 0.0), beat);
		}
		v = joint + (v - joint) * (1.0 - 0.6 * enroll);
		zb = joint.z;
	} else if (p == 4) {
		// An antenna: it feels slowly about, more towards its tip; rolled up, it draws in.
		float a = side * feel * along * sin(6.2831853 * (phase - 0.3 * along) + side);
		v = joint + turned(v - joint, vec3(0.0, 1.0, 0.0), a);
		n = turned(n, vec3(0.0, 1.0, 0.0), a);
		v = joint + (v - joint) * (1.0 - 0.55 * enroll);
		zb = joint.z;
	} else if (p == 3) {
		if (cartoon_eyes > 0.0) {
			// the cartoon eye: bigger about its own middle
			v = joint + (v - joint) * mix(1.0, eye_grow, cartoon_eyes);
		}
		zb = joint.z;
	} else if (p == 5) {
		// (a spine is carried stiffly by the part it grows from)
		zb = joint.z;
	}
	if (p == 0 || p == 3 || p == 5) {
		// rolled up, the sides of its shell (and what stands on them) curl down too
		float sx = min(abs(rest.x) / size, 0.45);
		v.y -= enroll * SIDE_CURL * sx * sx * size;
		n = normalize(n + vec3(sign(rest.x) * 2.0 * SIDE_CURL * enroll * sx * n.y, 0.0, 0.0));
	}
	roll(v, n, zb);
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

