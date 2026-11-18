shader_type spatial;
// The spot prawn (spot_prawn.gd): every marking drawn here (no texture files), its walking, its
// swimmerets and its tail flick. What each point is comes from the model
// (tools/build_spot_prawn.py): UV2.y the part times 16 plus which one of them it is (0 the body,
// 1 a walking leg, 2 a swimmeret, 3 an eye, 4 an antenna or antennule, 5 an antennal scale, 6 the
// tail fan, 7 the rostrum, 8 a mouthpart); the colour's red, green and blue the joint the part
// turns about (a place in the box BOX_MIN to BOX_MAX); the colour's alpha one more number (on a
// leg 0 above the knee and 1 below it; along an antenna, a swimmeret, the rostrum or a paddle of
// the tail fan 0 at its root to 1 at its tip; on an eye 0 its stalk and 1 the eye); on a leg UV.x,
// UV.y and UV2.x the place of its knee.
//
// It walks forwards on its ten thin legs in a wave from back to front (no skeleton: each leg is
// two stiff lengths worked out so that a foot on the ground stays put), beats its swimmerets in a
// wave from back to front, and with `flick` curls its abdomen and tail fan down and under (its
// backwards dart). All of it is a function of `phase` (and `flick`) alone, so a picture of it
// loops exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model: the box the joints are written in; how far out along a leg (from
// its joint to its tip, seen from above) its knee is.
const vec3 BOX_MIN = vec3(-0.03, 0.0, -0.1);
const vec3 BOX_MAX = vec3(0.03, 0.06, 0.1);
const float KNEE_AT = 0.45;
// How much of a step a foot spends on the ground; how far it moves in one step at `walk` 1, and
// how high it is lifted (metres).
const float ON_GROUND = 0.65;
const float STRIDE = 0.009;
const float LIFT = 0.005;
// The tail flick: where the abdomen starts bending (z), the height of its middle line there, how
// long the part that bends is (behind it the tail fan is carried round stiffly), and how far it
// curls at `flick` 1 (radians).
const float CURL_FROM = -0.004;
const float CURL_Y = 0.0318;
const float CURL_LENGTH = 0.072;
const float CURL_MAX = 2.7;
// Where the carapace ends and each segment of the abdomen begins (z), as the model has them.
const float SEG0 = -0.006;
const float SEG_STEP = 0.013;

// How far through one cycle of its steps and swimmeret beats (0..1, it wraps). Set by SpotPrawn.
uniform float phase = 0.0;
// Walking: 0 standing, 1 a walk forwards, -1 backwards; more is a longer stride.
uniform float walk = 0.0;
// How widely its swimmerets beat: 0 still, 1 swimming.
uniform float paddle = 0.0;
// Its tail flick: 0 straight, 1 the abdomen and tail fan curled right down and under.
uniform float flick : hint_range(0.0, 1.0) = 0.0;
// How far its long antennae swing (radians at their tips).
uniform float feel = 0.12;

// The red-orange of its back, the paler orange of its sides and underside; the white of its
// stripes and spots.
uniform vec3 red : source_color = vec3(0.66, 0.13, 0.06);
uniform vec3 pale : source_color = vec3(0.9, 0.5, 0.33);
uniform vec3 white : source_color = vec3(0.95, 0.93, 0.88);

// Cartoon eyes: 0 its eyes as they are, 1 big glossy beads with a white, an iris, a pupil, a
// highlight and a lid (the spot prawn's own: wide open and startled, a golden iris round a small
// round pupil). `eye_look` slides the iris and pupil (x towards its head, y up, -1..1); `blink`
// brings a lid the colour of its shell down over each eye (0 open, 1 shut), cartoon or not.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// As the model has it: the middle of the left eye (the right one mirrored) and its radius.
const vec3 EYE_MIDDLE = vec3(0.0093, 0.0375, -0.0623);
// This prawn's cartoon eye: the way the left one looks; how much bigger it is; its white, its iris;
// how wide the iris and the pupil are (as the sine of the angle from where it looks); the pupil's
// shape (its width and height); where the upper lid rests (1 above the eye, -1 shut) and how it
// slopes (+ lower at the front: a frown); how far the iris slides at `eye_look` 1.
const vec3 EYE_GAZE = vec3(0.55, 0.2, -0.8);
const float EYE_GROW = 1.7;
const vec3 EYE_WHITE = vec3(0.97, 0.96, 0.92);
const vec3 EYE_IRIS = vec3(0.95, 0.62, 0.08);
const float IRIS_SIZE = 0.52;
const float PUPIL_SIZE = 0.27;
const vec2 PUPIL_SHAPE = vec2(1.0, 1.0);
const float LID_REST = 1.08;
const float LID_SLOPE = 0.0;
const float LOOK_REACH = 0.38;

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


// The abdomen and the tail fan curled down and under about the back of the carapace (see `flick`).
void curl_under(inout vec3 v, inout vec3 n) {
	float d = v.z - CURL_FROM;
	if (flick < 0.001 || d <= 0.0) {
		return;
	}
	float k = flick * CURL_MAX / CURL_LENGTH;
	float r = 1.0 / k;
	float dc = min(d, CURL_LENGTH);
	float extra = d - dc;
	float a = dc * k;
	float h = v.y - CURL_Y;
	float ca = cos(a);
	float sa = sin(a);
	v = vec3(v.x, CURL_Y - r + (r + h) * ca - extra * sa, CURL_FROM + (r + h) * sa + extra * ca);
	n = vec3(n.x, n.y * ca - n.z * sa, n.y * sa + n.z * ca);
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
	} else if (p == 2) {
		// A swimmeret: it swings forwards and back about where it hangs, the last pair a fifth of a
		// beat ahead of the one in front of it.
		float a = paddle * (0.15 + 0.55 * sin(6.2831853 * (phase + 0.2 * index)));
		v = joint + turned(v - joint, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	} else if (p == 4 && index < 0.5) {
		// A long antenna: it swings slowly out and in, more towards its tip.
		float side = joint.x >= 0.0 ? 1.0 : -1.0;
		float a = side * feel * along * sin(6.2831853 * (phase - 0.3 * along));
		v = joint + turned(v - joint, vec3(0.0, 1.0, 0.0), a);
		n = turned(n, vec3(0.0, 1.0, 0.0), a);
	}
	if (p == 3 && along > 0.5 && cartoon_eyes > 0.0) {
		// the cartoon eye: bigger about its own middle
		float side = rest.x >= 0.0 ? 1.0 : -1.0;
		vec3 mid = EYE_MIDDLE * vec3(side, 1.0, 1.0);
		v = mid + (v - mid) * mix(1.0, EYE_GROW, cartoon_eyes);
	}
	if (p == 0 || p == 2 || p == 6) {
		curl_under(v, n);
	}
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	vec3 emit = vec3(0.0);
	float grain = noise2(rest.xz * 1400.0 + rest.y * 300.0);
	if (p == 0) {
		// The body: red-orange above, paler down its sides and beneath.
		float high = clamp((rest.y - 0.031) / 0.014, -1.0, 1.0);
		c = mix(pale, red, smoothstep(-0.7, 0.4, high));
		c *= 0.92 + 0.12 * grain;
		float z = rest.z;
		float side = abs(rest.x);
		if (z < SEG0) {
			// The carapace: white stripes running down and back across its sides, a white line
			// along the ridge at the front.
			float s1 = abs(rest.y - (0.036 - 0.16 * (z + 0.05)));
			float s2 = abs(rest.y - (0.027 - 0.16 * (z + 0.035)));
			float s3 = abs(rest.y - (0.040 - 0.05 * (z + 0.03)));
			float stripes = max(max(1.0 - smoothstep(0.0006, 0.0011, s1), 1.0 - smoothstep(0.0006, 0.0011, s2) ), 1.0 - smoothstep(0.0005, 0.0009, s3));
			stripes *= smoothstep(0.004, 0.007, side) * smoothstep(-0.056, -0.05, z) * (1.0 - smoothstep(-0.012, -0.007, z));
			c = mix(c, white, stripes * 0.9);
			c = mix(c, c * 0.7, 1.0 - smoothstep(0.0, 0.0012, abs(z - SEG0 + 0.0015)));
		} else {
			// The abdomen: each segment's rear edge a darker groove, a white spot each side of the
			// first and the fifth segments.
			float s = (z - SEG0) / SEG_STEP;
			float edge = 1.0 - smoothstep(0.0, 0.0011, abs(fract(s + 0.5) - 0.5) * SEG_STEP);
			c = mix(c, c * 0.62, edge * step(z, 0.071));
			vec2 d1 = vec2(z - 0.0005, rest.y - 0.0325);
			vec2 d5 = vec2(z - 0.0515, rest.y - 0.0300);
			float spots = 1.0 - smoothstep(0.0024, 0.0031, min(length(d1), length(d5)));
			c = mix(c, white, spots * smoothstep(0.004, 0.006, side));
		}
	} else if (p == 1 || p == 8) {
		// A leg or a mouthpart: red-orange, white bands at the knee and on its lower length.
		c = mix(pale, red, 0.55) * (0.9 + 0.15 * grain);
		if (p == 1) {
			float knee = length(rest - kk);
			c = mix(c, white, (1.0 - smoothstep(0.0012, 0.0022, knee)) * 0.8);
			float low_down = 1.0 - rest.y / max(kk.y, 0.001);
			c = mix(c, white, along * (1.0 - smoothstep(0.0, 0.06, abs(low_down - 0.45))) * 0.75);
		}
	} else if (p == 2) {
		// A swimmeret: pale, see-through orange.
		c = pale * (0.85 + 0.2 * grain);
		rough = 0.5;
	} else if (p == 3) {
		// An eye on its stalk: the stalk orange, the eye black with a dull sheen.
		c = mix(pale * 0.9, vec3(0.03, 0.025, 0.03), step(0.5, along));
		rough = mix(0.45, 0.2, along);
		spec = mix(0.4, 0.7, along);
		if (along > 0.5) {
			float lid;
			float shine;
			c = eye_colour(rest, c, mix(pale, red, 0.5), lid, shine);
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
	} else if (p == 4) {
		// An antenna: red, banded paler along its length.
		float bands = smoothstep(0.3, 0.7, sin(along * 260.0));
		c = mix(red, pale, 0.25 + 0.2 * bands);
	} else if (p == 5) {
		// An antennal scale: pale with a red edge.
		c = mix(pale, red, 0.3);
	} else if (p == 6) {
		// The tail fan: red, paler towards its tips, white at its edge tips.
		c = mix(red, pale, 0.2 + 0.35 * along);
		c = mix(c, white, smoothstep(0.85, 1.0, along) * 0.6);
	} else {
		// The rostrum: red, its teeth paler.
		c = mix(red, pale, 0.2 + 0.3 * along);
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = emit;
}
