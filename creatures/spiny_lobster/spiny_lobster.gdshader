shader_type spatial;
// The California spiny lobster (spiny_lobster.gd): every marking drawn here (no texture files),
// its walking and the slow swing of its antennae. What each point is comes from the model
// (tools/build_spiny_lobster.py): UV2.y the part times 16 plus which one of them it is (0 the
// body, 1 a walking leg, 2 an eye, 3 an antenna or antennule with its spines, 4 the tail fan, 5 a
// spine or horn on the body, 6 a mouthpart); the colour's red, green and blue the joint the part
// turns about (a place in the box BOX_MIN to BOX_MAX); the colour's alpha one more number (on a
// leg 0 above the knee and 1 below it; along an antenna, a spine or a paddle of the tail fan 0 at
// its root to 1 at its tip; on an eye 0 its stalk and 1 the eye); on a leg UV.x, UV.y and UV2.x
// the place of its knee.
//
// It walks forwards on its ten legs in a wave from back to front (no skeleton: each leg is two
// stiff lengths worked out so that a foot on the ground stays put), and swings its antennae
// slowly. All of it is a function of `phase` alone, so a picture of it loops exactly. Nothing
// here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model: the box the joints are written in; how far out along a leg (from
// its joint to its tip, seen from above) its knee is.
const vec3 BOX_MIN = vec3(-0.1, 0.0, -0.3);
const vec3 BOX_MAX = vec3(0.1, 0.2, 0.3);
const float KNEE_AT = 0.42;
// How much of a step a foot spends on the ground; how far it moves in one step at `walk` 1, and
// how high it is lifted (metres).
const float ON_GROUND = 0.65;
const float STRIDE = 0.05;
const float LIFT = 0.025;
// Where the carapace ends and each plate of the abdomen begins (z), as the model has them; the
// groove across the carapace.
const float SEG0 = -0.035;
const float GROOVE = -0.15;

// How far through one cycle of its steps (0..1, it wraps). Set by SpinyLobster.
uniform float phase = 0.0;
// Walking: 0 standing, 1 a walk forwards, -1 backwards; more is a longer stride.
uniform float walk = 0.0;
// How far its antennae swing to and fro (radians at their tips).
uniform float feel = 0.1;

// The reddish brown of its shell, its darker shading, the paler orange of its underside and its
// legs' stripes, the pale tips of its spines.
uniform vec3 shell : source_color = vec3(0.46, 0.12, 0.06);
uniform vec3 shell_dark : source_color = vec3(0.22, 0.06, 0.04);
uniform vec3 pale : source_color = vec3(0.85, 0.55, 0.25);
uniform vec3 spine_tip : source_color = vec3(0.9, 0.82, 0.62);
// How strongly the fine pale speckles show on its shell.
uniform float speckle = 0.6;

// Cartoon eyes: 0 its eyes as they are, 1 big glossy beads with a white, an iris, a pupil, a
// highlight and a lid (the spiny lobster's own: a gruff old sentry, heavy lids down over the top of
// each eye and sloping in to a frown, a dark amber iris round a pupil like a bar). `eye_look` slides
// the iris and pupil (x across the eye towards its head, which on these forward-looking eyes is
// towards its middle; y up; -1..1); `blink` brings a lid the colour of its shell down over each eye
// (0 open, 1 shut), cartoon or not.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// As the model has it: the middle of the left eye (the right one mirrored).
const vec3 EYE_MIDDLE = vec3(0.030, 0.136, -0.289);
// This lobster's cartoon eye: the way the left one looks; how much bigger it is; its white, its
// iris; how wide the iris and the pupil are (as the sine of the angle from where it looks); the
// pupil's shape (its width and height); where the upper lid rests (1 above the eye, -1 shut) and how
// it slopes (+ lower across towards its head: a frown); how far the iris slides at `eye_look` 1.
const vec3 EYE_GAZE = vec3(0.5, 0.3, -0.8);
const float EYE_GROW = 1.45;
const vec3 EYE_WHITE = vec3(0.93, 0.9, 0.8);
const vec3 EYE_IRIS = vec3(0.6, 0.32, 0.08);
const float IRIS_SIZE = 0.6;
const float PUPIL_SIZE = 0.3;
const vec2 PUPIL_SHAPE = vec2(1.35, 0.42);
const float LID_REST = 0.32;
const float LID_SLOPE = 0.38;
const float LOOK_REACH = 0.3;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float index;
varying float along;
varying vec3 kk;

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
	float code = floor(UV2.y + 0.5);
	part = floor((code + 0.5) / 16.0);
	index = code - part * 16.0;
	along = COLOR.a;
	kk = vec3(UV.x, UV.y, UV2.x);
	vec3 joint = mix(BOX_MIN, BOX_MAX, COLOR.rgb);
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	if (p == 1) {
		// A walking leg: `index` 0 the first (the front) to 4 the last; a wave of steps from back
		// to front, the two sides half a step apart.
		float side = joint.x >= 0.0 ? 1.0 : -1.0;
		float cycle = phase - 0.2 * index + (side > 0.0 ? 0.0 : 0.5);
		vec2 f = foot_at(cycle);
		vec3 shift = vec3(0.0, LIFT * min(abs(walk), 1.0) * f.y, -walk * STRIDE * f.x);
		leg_move(v, n, joint, kk, along, shift);
	} else if (p == 3) {
		// An antenna: it swings slowly out and in and a little up and down, more towards its tip
		// (the antennules less).
		float side = joint.x >= 0.0 ? 1.0 : -1.0;
		float amount = feel * along * (index < 0.5 ? 1.0 : 0.5);
		float a = side * amount * sin(6.2831853 * (phase - 0.25 * along));
		float b = 0.4 * amount * sin(6.2831853 * (phase + 0.2));
		v = joint + turned(turned(v - joint, vec3(1.0, 0.0, 0.0), b), vec3(0.0, 1.0, 0.0), a);
		n = turned(turned(n, vec3(1.0, 0.0, 0.0), b), vec3(0.0, 1.0, 0.0), a);
	}
	if (p == 2 && along > 0.5 && cartoon_eyes > 0.0) {
		// the cartoon eye: bigger about its own middle
		vec3 mid = EYE_MIDDLE * vec3(rest.x >= 0.0 ? 1.0 : -1.0, 1.0, 1.0);
		v = mid + (v - mid) * mix(1.0, EYE_GROW, cartoon_eyes);
	}
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.45;
	float spec = 0.45;
	vec3 emit = vec3(0.0);
	float grain = noise2(rest.xz * 260.0 + rest.y * 90.0);
	float blot = noise2(rest.xz * 30.0 + 3.0);
	float dots = smoothstep(0.78, 0.9, noise2(rest.xz * 330.0 + rest.yy * 170.0));
	if (p == 0) {
		// The shell: reddish brown, darker over the back and in blots, orange beneath, finely
		// speckled paler.
		float high = clamp((rest.y - 0.1) / 0.055, -1.0, 1.0);
		c = mix(pale * 0.85, shell, smoothstep(-0.85, -0.2, high));
		c = mix(c, shell_dark, smoothstep(0.2, 0.95, high) * 0.45 + (blot - 0.5) * 0.4);
		c *= 0.88 + 0.2 * grain;
		c = mix(c, spine_tip, dots * speckle * 0.5 * smoothstep(-0.6, 0.0, high));
		float z = rest.z;
		if (z < SEG0) {
			// the groove across the carapace
			c = mix(c, shell_dark * 0.6, (1.0 - smoothstep(0.0, 0.004, abs(z - GROOVE))) * 0.7);
			c = mix(c, shell_dark * 0.6, (1.0 - smoothstep(0.0, 0.003, abs(z - SEG0 + 0.003))) * 0.6);
		} else {
			// The abdomen: each plate's rear edge a dark groove with a paler band before it, and
			// across the middle of each plate a groove broken in the middle (as the species has).
			float s = (z - SEG0) / 0.0405;
			float f = fract(s);
			float edge = 1.0 - smoothstep(0.0, 0.07, min(f, 1.0 - f));
			c = mix(c, shell_dark * 0.55, edge * 0.8 * step(z, 0.2));
			c = mix(c, pale, smoothstep(0.78, 0.92, f) * (1.0 - smoothstep(0.93, 0.97, f)) * 0.35 * step(z, 0.2));
			float groove = (1.0 - smoothstep(0.0, 0.05, abs(f - 0.45))) * smoothstep(0.006, 0.012, abs(rest.x)) * smoothstep(-0.2, 0.3, high);
			c = mix(c, shell_dark * 0.6, groove * 0.7 * step(z, 0.19));
		}
	} else if (p == 1 || p == 6) {
		// A leg or a mouthpart: reddish brown with pale stripes along it, paler towards its tip.
		float around = atan(rest_normal.y, rest_normal.x + rest_normal.z);
		float stripes = smoothstep(0.55, 0.8, sin(around * 3.0));
		c = mix(shell, pale, stripes * 0.75);
		c *= 0.9 + 0.15 * grain;
		if (p == 1) {
			float low_down = 1.0 - rest.y / max(kk.y, 0.001);
			c = mix(c, pale, along * smoothstep(0.75, 1.0, low_down) * 0.6);
			c = mix(c, shell_dark, (1.0 - smoothstep(0.004, 0.012, length(rest - kk))) * 0.5);
		}
	} else if (p == 2) {
		// An eye on its stalk: the stalk orange, the eye black with a dull sheen.
		c = mix(pale * 0.8, vec3(0.025, 0.02, 0.025), step(0.5, along));
		rough = mix(0.45, 0.2, along);
		spec = mix(0.4, 0.7, along);
		if (along > 0.5) {
			float lid;
			float shine;
			c = eye_colour(rest, c, shell, lid, shine);
			// cartooned: glossy, two bright highlights up and forward on it, and a dark rim so it
			// reads from far off
			float open = (1.0 - lid) * cartoon_eyes;
			c = mix(c, c * 0.15, open * (1.0 - smoothstep(0.12, 0.38, dot(normalize(NORMAL), VIEW))));
			c = mix(c, vec3(1.0), shine * open);
			emit = vec3(0.6) * shine * open;
			rough = mix(rough, 0.12, open);
			// (a shut lid is shell, not glassy eye)
			rough = mix(rough, 0.55, lid);
			spec = mix(spec, 0.35, lid);
		}
	} else if (p == 3) {
		// An antenna: dark reddish brown, banded faintly, its spines' tips pale.
		float bands = smoothstep(0.2, 0.9, sin(along * 120.0));
		c = mix(shell_dark * 1.3, shell, 0.4 + 0.3 * bands) * (0.9 + 0.15 * grain);
	} else if (p == 4) {
		// The tail fan: reddish brown, softer and paler towards its rounded end.
		c = mix(shell, pale, 0.15 + 0.4 * smoothstep(0.55, 1.0, along)) * (0.9 + 0.15 * grain);
		c = mix(c, shell_dark, (1.0 - smoothstep(0.0, 0.15, along)) * 0.4);
		rough = 0.55;
	} else {
		// A spine or a horn: red at its foot, pale at its tip.
		c = mix(shell, spine_tip, smoothstep(0.4, 0.95, along));
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = emit;
}
