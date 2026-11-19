shader_type spatial;
// The red rock crab (rock_crab.gd): every marking drawn here (no texture files), its walking and
// its claws. What each point is comes from the model (tools/build_rock_crab.py): UV2.y the part
// times 16 plus which one of them it is (0 the shell, 1 a walking leg, 2 a claw, 3 an eye); the
// colour's red, green and blue the joint the part turns about (a place in the box BOX_MIN to
// BOX_MAX); the colour's alpha one more number (on a leg 0 above the knee and 1 below it; on a
// finger 0 at its root to 1 at its tip; on an eye 0 its stalk and 1 the eye); UV.x, UV.y and
// UV2.x three more (on a leg the place of its knee; on a claw the hinge of its upper finger; on
// the shell how far out from its middle it is, 0 to 1 at its edge, and 1 on top or 0 beneath).
//
// It walks sideways, as crabs do, in an alternating gait (the first and third legs of one side
// step with the second and fourth of the other). Each leg is two stiff lengths, from its joint
// with the body to its knee and from the knee to its tip, worked out each frame so that a foot
// on the ground stays where it is put (no skeleton). All of it is a function of `phase` alone,
// so a picture of it loops exactly. Nothing here needs more than GL Compatibility has.
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


// Kept in step with the model: the box the joints are written in; how far out along a leg (from
// its joint to its tip, seen from above) its knee is.
const vec3 BOX_MIN = vec3(-0.1, 0.0, -0.1);
const vec3 BOX_MAX = vec3(0.1, 0.1, 0.1);
const float KNEE_AT = 0.62;
// The hinge of the left claw's upper finger: its axis (the right claw is the mirror of it).
const vec3 FINGER_AXIS = vec3(-0.361, 0.0, 0.933);
// How much of a step a foot spends on the ground (the rest it is lifted and swung back).
const float ON_GROUND = 0.6;
// How far a foot moves in one step at `walk` 1, and how high it is lifted (metres).
const float STRIDE = 0.026;
const float LIFT = 0.012;

// How far through one cycle of its steps (0..1, it wraps): in one cycle every leg steps once.
// Set by RockCrab.
uniform float phase = 0.0;
// Walking: 0 standing, 1 a walk to its left (+X), -1 to its right (-X); more is a longer stride.
uniform float walk = 0.0;
// Its claws: 0 folded in front of it, 1 raised high and spread with their fingers open (as a crab
// that is threatened, or reaching for something).
uniform float claws : hint_range(0.0, 1.0) = 0.0;

// The top of the shell, its darker middle and paler rim; beneath it; the black of the claws' tips.
uniform vec3 shell : source_color = vec3(0.36, 0.06, 0.04);
uniform vec3 shell_dark : source_color = vec3(0.2, 0.04, 0.03);
uniform vec3 shell_rim : source_color = vec3(0.52, 0.16, 0.08);
uniform vec3 under : source_color = vec3(0.86, 0.74, 0.55);
uniform vec3 tips : source_color = vec3(0.02, 0.015, 0.015);
// How strongly the shell's fine mottling shows.
uniform float mottle = 0.6;

// Cartoon eyes: 0 its eyes as they are, 1 big glossy beads with a white, an iris, a pupil, a
// highlight and a lid (the rock crab's own: a shifty little scrapper, a big yellow-green iris and a
// round pupil under lids half down and sloping up towards its middle, a sly sidelong look).
// `eye_look` slides the iris and pupil (x across the eye towards its head, which on these
// forward-looking eyes is towards its middle; y up; -1..1); `blink` brings a lid the colour of its
// shell down over each eye (0 open, 1 shut), cartoon or not.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// As the model has it: the middle of the left eye (the right one mirrored).
const vec3 EYE_MIDDLE = vec3(0.0178, 0.0412, -0.0497);
// This crab's cartoon eye: the way the left one looks; how much bigger it is; its white, its iris;
// how wide the iris and the pupil are (as the sine of the angle from where it looks); the pupil's
// shape (its width and height); where the upper lid rests (1 above the eye, -1 shut) and how it
// slopes (+ lower across towards its head: a frown); how far the iris slides at `eye_look` 1.
const vec3 EYE_GAZE = vec3(0.45, 0.4, -0.8);
const float EYE_GROW = 1.8;
const vec3 EYE_WHITE = vec3(0.96, 0.95, 0.86);
const vec3 EYE_IRIS = vec3(0.68, 0.78, 0.12);
const float IRIS_SIZE = 0.68;
const float PUPIL_SIZE = 0.36;
const vec2 PUPIL_SHAPE = vec2(1.0, 1.0);
const float LID_REST = 0.42;
const float LID_SLOPE = -0.3;
const float LOOK_REACH = 0.28;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float index;
varying float along;
varying vec3 kk;
varying vec3 joint_at;

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

// Where a foot is in its step, `cycle` through it (only the fraction counts): x how far ahead of
// its middle place it stands (0.5 as it is set down, -0.5 as it is picked up), y how high it is
// lifted (0 on the ground, 1 at the top of its swing).
vec2 foot_at(float cycle) {
	float c = fract(cycle);
	if (c < ON_GROUND) {
		return vec2(0.5 - c / ON_GROUND, 0.0);
	}
	float u = (c - ON_GROUND) / (1.0 - ON_GROUND);
	return vec2(-0.5 * cos(3.14159265 * u), sin(3.14159265 * u));
}

// One point of a leg, moved so that the leg's tip is `shift` from where it stands at rest. The leg
// is two stiff lengths in an upright plane: from its joint with the body (`joint`) to its knee
// (`knee`), and from the knee to its tip, which at rest is on the ground (y 0), the knee KNEE_AT of
// the way out to it (as the model is built). `lower` is 1 for a point below the knee. The joint
// turns the whole leg about an upright axis and lifts it; the knee opens and shuts: both worked
// out exactly (the two-length triangle), so a foot on the ground stays on it.
void leg_move(inout vec3 v, inout vec3 n, vec3 joint, vec3 knee, float lower, vec3 shift) {
	vec2 flat_way = knee.xz - joint.xz;
	float knee_out = length(flat_way);
	vec3 d = vec3(flat_way.x, 0.0, flat_way.y) / knee_out;
	vec3 up = vec3(0.0, 1.0, 0.0);
	vec3 axis = cross(d, up);
	float a = length(knee - joint);
	vec3 tip = vec3(joint.x, 0.0, joint.z) + d * (knee_out / KNEE_AT);
	float b = length(tip - knee);
	vec2 was = vec2(knee_out / KNEE_AT, -joint.y);
	vec3 to = tip + shift - joint;
	vec3 across = cross(up, d);
	float yaw = atan(dot(to, across), dot(to, d));
	vec2 now = vec2(length(to.xz), to.y);
	float l0 = length(was);
	float l1 = clamp(length(now), abs(a - b) + 0.0001, a + b - 0.0001);
	float lift = atan(now.y, now.x) + acos(clamp((a * a + l1 * l1 - b * b) / (2.0 * a * l1), -1.0, 1.0))
			- atan(was.y, was.x) - acos(clamp((a * a + l0 * l0 - b * b) / (2.0 * a * l0), -1.0, 1.0));
	float open = acos(clamp((a * a + b * b - l1 * l1) / (2.0 * a * b), -1.0, 1.0))
			- acos(clamp((a * a + b * b - l0 * l0) / (2.0 * a * b), -1.0, 1.0));
	if (lower > 0.5) {
		v = knee + turned(v - knee, axis, open);
		n = turned(n, axis, open);
	}
	v = joint + turned(turned(v - joint, axis, lift), up, yaw);
	n = turned(turned(n, axis, lift), up, yaw);
}

// How far its body is lifted at this point of the cycle (it rises a little as each set of legs
// pushes).
float bob() {
	return 0.0012 * min(abs(walk), 1.5) * (0.5 - 0.5 * cos(12.5663706 * phase));
}

// The eye on the side of `p` (at rest): its middle, the way it looks, its up and its across (towards
// the head).
void eye_frame(vec3 p, out vec3 mid, out vec3 gaze, out vec3 up, out vec3 across) {
	float side = p.x >= 0.0 ? 1.0 : -1.0;
	mid = EYE_MIDDLE * vec3(side, 1.0, 1.0);
	gaze = normalize(EYE_GAZE * vec3(side, 1.0, 1.0));
	up = normalize(vec3(0.0, 1.0, 0.0) - gaze * gaze.y);
	across = normalize(cross(up, gaze)) * side;
}

// The colour of a point `p` (at rest) of an eye: `plain` as it is, mixed to the cartoon eye by
// `cartoon_eyes`, the lid (`skin`) over it as `blink` (and, cartooned, `LID_REST`) has it; `lid` is
// set to how far the lid covers it, `glint` to where the cartoon eye's highlights are (they stay
// put, up and forward on the eye, when it looks about).
vec3 eye_colour(vec3 p, vec3 plain, vec3 skin, out float lid, out float glint) {
	vec3 mid, gaze, up, across;
	eye_frame(p, mid, gaze, up, across);
	vec3 d = normalize(p - mid);
	vec2 q = vec2(dot(d, across), dot(d, up));
	float front = smoothstep(-0.05, 0.1, dot(d, gaze));
	vec2 at = q - eye_look * LOOK_REACH;
	float r = length(at);
	vec3 c = EYE_WHITE;
	float iris = (1.0 - smoothstep(IRIS_SIZE - 0.03, IRIS_SIZE, r)) * front;
	c = mix(c, EYE_IRIS * mix(1.2, 0.6, smoothstep(0.0, IRIS_SIZE, r)), iris);
	c = mix(c, vec3(0.03, 0.02, 0.02), (1.0 - smoothstep(0.015, 0.045, abs(r - IRIS_SIZE))) * front);
	float pupil = 1.0 - smoothstep(PUPIL_SIZE - 0.03, PUPIL_SIZE, length(at / PUPIL_SHAPE));
	c = mix(c, vec3(0.01, 0.01, 0.015), pupil * front);
	c = mix(plain, c, cartoon_eyes);
	// the upper lid: its edge comes down from above the eye (or from where it rests) to below it
	float edge = mix(mix(1.08, LID_REST, cartoon_eyes), -1.08, blink) - LID_SLOPE * q.x;
	lid = smoothstep(edge - 0.02, edge + 0.02, q.y);
	glint = smoothstep(0.955, 0.97, dot(d, normalize(gaze + up * min(0.62, LID_REST - 0.28) + across * 0.3)));
	glint = max(glint, 0.7 * smoothstep(0.991, 0.995, dot(d, normalize(gaze + up * 0.18 + across * 0.52))));
	c = mix(c, skin, lid);
	c = mix(c, skin * 0.35, (1.0 - smoothstep(0.02, 0.07, abs(q.y - edge))) * step(edge, 1.0) * max(cartoon_eyes, step(0.001, blink)));
	return c;
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	float code = floor(UV2.y + 0.5);
	part = floor((code + 0.5) / 16.0);
	index = code - part * 16.0;
	along = COLOR.a;
	kk = vec3(UV.x, UV.y, UV2.x);
	vec3 joint = mix(BOX_MIN, BOX_MAX, COLOR.rgb);
	joint_at = joint;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float up_by = bob();
	if (part > 0.5 && part < 1.5) {
		// A walking leg: `index` 0 the first (the front) to 3 the last; which side, from its joint.
		float side = joint.x >= 0.0 ? 1.0 : -1.0;
		float cycle = phase + 0.5 * mod(index + (side > 0.0 ? 0.0 : 1.0), 2.0) + 0.06 * index;
		vec2 f = foot_at(cycle);
		vec3 shift = vec3(walk * STRIDE * f.x, LIFT * min(abs(walk), 1.0) * f.y - up_by, 0.0);
		leg_move(v, n, joint, kk, along, shift);
	} else if (part > 1.5 && part < 2.5) {
		// A claw, worked in the left one's frame (the right is its mirror): its upper finger opens
		// about its hinge, then the whole claw is raised and spread about its shoulder.
		float side = joint.x >= 0.0 ? 1.0 : -1.0;
		v.x *= side;
		n.x *= side;
		vec3 shoulder = vec3(joint.x * side, joint.y, joint.z);
		vec3 hinge = vec3(kk.x * side, kk.y, kk.z);
		float c = clamp(claws, 0.0, 1.0);
		if (index > 1.5) {
			v = hinge + turned(v - hinge, FINGER_AXIS, -0.75 * c);
			n = turned(n, FINGER_AXIS, -0.75 * c);
		}
		vec3 reach = hinge - shoulder;
		vec3 flat_way = normalize(vec3(reach.x, 0.0, reach.z));
		vec3 raise_axis = normalize(cross(flat_way, vec3(0.0, 1.0, 0.0)));
		v = shoulder + turned(turned(v - shoulder, raise_axis, 0.8 * c), vec3(0.0, 1.0, 0.0), -0.7 * c);
		n = turned(turned(n, raise_axis, 0.8 * c), vec3(0.0, 1.0, 0.0), -0.7 * c);
		v.x *= side;
		n.x *= side;
	}
	if (part > 2.5 && along > 0.5 && cartoon_eyes > 0.0) {
		// the cartoon eye: bigger about its own middle
		vec3 mid = EYE_MIDDLE * vec3(rest.x >= 0.0 ? 1.0 : -1.0, 1.0, 1.0);
		v = mid + (v - mid) * mix(1.0, EYE_GROW, cartoon_eyes);
	}
	v.y += up_by;
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

