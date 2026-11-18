shader_type spatial;
// The anomalocaris (anomalocaris.gd): every marking drawn here (no texture files), its swimming
// (a wave down its body, its lobes rippling in a wave from front to back, its tail fan swaying),
// its grasping arms reaching out and curling (`grasp`) and its cartoon eyes. What each point is
// comes from the model (tools/build_anomalocaris.py): UV2.y the part times 16 plus which one of
// them it is (0 the body, 1 a lobe (0 the first to 10), 2 a tail blade (0 the inner pair to 2),
// 3 an eye or its stalk, 4 an arm (which segment, 0 the first), 5 a spine of an arm (the segment
// it stands on), 6 the mouth); the colour's red, green and blue a place (in the box BOX_MIN to
// BOX_MAX: a lobe's hinge, a tail blade's root, an eye's middle); the colour's alpha how far
// along (a lobe or a blade from root to tip, an eye's stalk 0 and the eye 1, the arm from its root
// to its tip, a spine from its foot to its point, the mouth from its rim to its opening).
//
// All of the motion is a function of `phase` (and the settings) alone, so a picture of it loops
// exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model (build_anomalocaris.py): the box the places are written in; the neck
// and where each segment begins; each arm joint's place (y, z) at rest, and how far it turns about
// +X from rest to reaching out (radians: the ARM_P and ARM_D lines the build script prints).
const vec3 BOX_MIN = vec3(-0.25, -0.2, -0.45);
const vec3 BOX_MAX = vec3(0.25, 0.2, 0.45);
const float NECK = -0.228;
const float SEG0 = -0.215;
const float SEG_STEP = 0.043;
const vec2 ARM_P[13] = vec2[13](vec2(-0.02000, -0.35200), vec2(-0.04825, -0.36702), vec2(-0.07020, -0.36549), vec2(-0.08786, -0.35610), vec2(-0.09925, -0.34152), vec2(-0.10336, -0.32503), vec2(-0.10058, -0.30927), vec2(-0.09220, -0.29683), vec2(-0.08032, -0.28941), vec2(-0.06745, -0.28761), vec2(-0.05591, -0.29091), vec2(-0.04749, -0.29798), vec2(-0.04310, -0.30697));
const float ARM_D[13] = float[13](0.97738, 0.48869, 0.38397, 0.38397, 0.38397, 0.38397, 0.38397, 0.36652, 0.34907, 0.31416, 0.24435, 0.13963, 0.03491);

// How far through one beat (0..1, it wraps): one stroke of its lobes, one wave down its body. Set
// by Anomalocaris.
uniform float phase = 0.0;
// How strongly its body waves and its tail fan sways: 1 swimming, 0 still.
uniform float sway = 1.0;
// How widely its lobes beat: 0 still, 1 swimming.
uniform float flap = 1.0;
// Its arms: 0 curled down and back under its head, 1 reaching straight out ahead, spines open.
uniform float grasp : hint_range(0.0, 1.0) = 0.0;

// Its reddish-brown, the paler pink-tan of its lobes and tail blades, the dark of its markings, the
// pale of its spines and mouth plates.
uniform vec3 body_colour : source_color = vec3(0.52, 0.2, 0.12);
uniform vec3 lobe_colour : source_color = vec3(0.82, 0.52, 0.4);
uniform vec3 dark : source_color = vec3(0.22, 0.08, 0.06);
uniform vec3 pale : source_color = vec3(0.93, 0.82, 0.66);

// Cartoon eyes: 0 its eyes as they are (big dark compound eyes, faceted), 1 the cartoon eye (the
// anomalocaris's own: big, glossy and hungry: a hot amber iris round a big round pupil, wide open
// under a brow that slants down towards its front, a predator's frown). `eye_look` slides the iris
// and pupil (x towards its front, y up, -1..1); `blink` brings a lid the colour of its skin down
// over each eye (0 open, 1 shut), cartoon or not.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// As the model has it: the middle of the left eye (the right one mirrored).
const vec3 EYE_MIDDLE = vec3(0.098, 0.04, -0.282);
// This one's cartoon eye: the way the left one looks; how much bigger it is; its white, its iris;
// how wide the iris and the pupil are (as the sine of the angle from where it looks); the pupil's
// shape (its width and height); where the upper lid rests (1 above the eye, -1 shut) and how it
// slopes (+ lower at the front: a frown); how far the iris slides at `eye_look` 1.
const vec3 EYE_GAZE = vec3(1.0, 0.3, -0.55);
const float EYE_GROW = 1.5;
const vec3 EYE_WHITE = vec3(0.97, 0.95, 0.9);
const vec3 EYE_IRIS = vec3(1.0, 0.55, 0.05);
const float IRIS_SIZE = 0.62;
const float PUPIL_SIZE = 0.38;
const vec2 PUPIL_SHAPE = vec2(1.0, 1.0);
const float LID_REST = 0.6;
const float LID_SLOPE = 0.62;
const float LOOK_REACH = 0.3;

varying vec3 rest;
varying float part;
varying float index;
varying float along;
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

// The eye on the side of `p` (at rest): its middle, the way it looks, its up and its across
// (towards its front).
void eye_frame(vec3 p, out vec3 mid, out vec3 gaze, out vec3 up, out vec3 across) {
	float side = p.x >= 0.0 ? 1.0 : -1.0;
	mid = EYE_MIDDLE * vec3(side, 1.0, 1.0);
	gaze = normalize(EYE_GAZE * vec3(side, 1.0, 1.0));
	up = normalize(vec3(0.0, 1.0, 0.0) - gaze * gaze.y);
	across = normalize(cross(up, gaze)) * side;
}

// The colour of a point `p` (at rest) of an eye: `plain` as it is, mixed to the cartoon eye by
// `cartoon_eyes`, the lid (`lid_skin`) over it as `blink` (and, cartooned, `LID_REST`) has it;
// `lid` is set to how far the lid covers it, `glint` to where the cartoon eye's highlights are.
vec3 eye_colour(vec3 p, vec3 plain, vec3 lid_skin, out float lid, out float glint) {
	vec3 mid, gaze, up, across;
	eye_frame(p, mid, gaze, up, across);
	vec3 d = normalize(p - mid);
	vec2 q = vec2(dot(d, across), dot(d, up));
	float front = smoothstep(-0.05, 0.1, dot(d, gaze));
	vec2 at = q - eye_look * LOOK_REACH;
	float r = length(at);
	vec3 c = EYE_WHITE;
	float iris = (1.0 - smoothstep(IRIS_SIZE - 0.03, IRIS_SIZE, r)) * front;
	float streaks = 0.85 + 0.15 * sin(atan(at.y, at.x) * 22.0);
	c = mix(c, EYE_IRIS * mix(1.2, 0.55, smoothstep(0.0, IRIS_SIZE, r)) * streaks, iris);
	c = mix(c, vec3(0.03, 0.02, 0.02), (1.0 - smoothstep(0.015, 0.045, abs(r - IRIS_SIZE))) * front);
	float pupil = 1.0 - smoothstep(PUPIL_SIZE - 0.03, PUPIL_SIZE, length(at / PUPIL_SHAPE));
	c = mix(c, vec3(0.01, 0.01, 0.015), pupil * front);
	c = mix(plain, c, cartoon_eyes);
	// the upper lid: its edge comes down from above the eye (or from where it rests) to below it
	float edge = mix(mix(1.08, LID_REST, cartoon_eyes), -1.08, blink) - LID_SLOPE * q.x * cartoon_eyes;
	lid = smoothstep(edge - 0.02, edge + 0.02, q.y);
	glint = smoothstep(0.955, 0.97, dot(d, normalize(gaze + up * 0.62 + across * 0.3)));
	glint = max(glint, 0.7 * smoothstep(0.991, 0.995, dot(d, normalize(gaze + up * 0.18 + across * 0.52))));
	glint *= 1.0 - lid;
	c = mix(c, lid_skin, lid);
	c = mix(c, lid_skin * 0.35, (1.0 - smoothstep(0.02, 0.07, abs(q.y - edge))) * step(edge, 1.0) * max(cartoon_eyes, step(0.001, blink)));
	return c;
}

void vertex() {
	float code = floor(UV2.y + 0.5);
	part = floor((code + 0.5) / 16.0);
	index = code - part * 16.0;
	along = COLOR.a;
	joint = mix(BOX_MIN, BOX_MAX, COLOR.rgb);
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	float wave = 6.2831853 * phase;
	float side = rest.x >= 0.0 ? 1.0 : -1.0;
	if (p == 1) {
		// A lobe: it beats up and down about its hinge, each a little behind the one in front of
		// it, so that a wave runs back along each side.
		float a = side * flap * (0.08 + 0.42 * sin(wave - 0.58 * index));
		v = joint + turned(v - joint, vec3(0.0, 0.0, 1.0), a);
		n = turned(n, vec3(0.0, 0.0, 1.0), a);
	} else if (p == 2) {
		// A tail blade: it lifts and dips a little with the stroke.
		float a = sway * 0.1 * sin(wave - 2.2 - 0.3 * index);
		v = joint + turned(v - joint, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	} else if (p == 4 || p == 5) {
		// An arm and its spines: each joint from its root out turns from the curled rest towards
		// reaching out (the outermost first, each about its own place at rest), a little breathing
		// in it as it swims.
		float g = clamp(grasp + 0.04 * sway * sin(wave + 1.0) * (1.0 - grasp), -0.1, 1.0);
		int seg = int(index + 0.5);
		for (int i = 12; i >= 0; i--) {
			if (i <= seg) {
				float a = g * ARM_D[i];
				vec2 d = v.yz - ARM_P[i];
				float c = cos(a);
				float s = sin(a);
				v.yz = ARM_P[i] + vec2(d.x * c - d.y * s, d.y * c + d.x * s);
				n.yz = vec2(n.y * c - n.z * s, n.z * c + n.y * s);
			}
		}
	}
	if (p == 3 && along > 0.5 && cartoon_eyes > 0.0) {
		// the cartoon eye: bigger about its own middle
		v = joint + (v - joint) * mix(1.0, EYE_GROW, cartoon_eyes);
	}
	// The wave down its body (up and down), growing towards its tail.
	float bend = sway * 0.007 * sin(wave - 13.0 * rest.z) * smoothstep(-0.3, 0.35, rest.z);
	float slope = sway * 0.007 * 13.0 * cos(wave - 13.0 * rest.z) * smoothstep(-0.3, 0.35, rest.z);
	v.y += bend;
	n = normalize(n + vec3(0.0, 0.0, -slope * n.y));
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 nn = normalize(NORMAL);
	vec3 c;
	float rough = 0.5;
	float spec = 0.45;
	vec3 emit = vec3(0.0);
	float grain = noise2(rest.xz * 180.0 + rest.y * 60.0);
	if (p == 0) {
		// The body: reddish-brown, darker along the back, paler beneath; on the head an oval plate
		// with a dark rim; each segment's groove dark, a pale band behind it and a row of dark
		// spots along each side.
		float top = smoothstep(-0.01, 0.025, rest.y);
		c = mix(lobe_colour * 0.85, body_colour, smoothstep(-0.02, 0.01, rest.y));
		c = mix(c, body_colour * 0.75, top * (1.0 - smoothstep(0.02, 0.05, abs(rest.x))));
		c *= 0.9 + 0.18 * grain;
		if (rest.z < NECK) {
			vec2 q = vec2(rest.x / 0.042, (rest.z + 0.31) / 0.06);
			float r = length(q);
			float rim = 1.0 - smoothstep(0.03, 0.09, abs(r - 1.0));
			c = mix(c, c * 1.15, (1.0 - smoothstep(0.9, 1.0, r)) * top);
			c = mix(c, dark, rim * top * 0.8);
		} else {
			float s = (rest.z - SEG0) / SEG_STEP;
			float groove = 1.0 - smoothstep(0.0, 0.004, abs(fract(s + 0.5) - 0.5) * SEG_STEP);
			c = mix(c, dark, groove * 0.75 * step(rest.z, 0.25));
			c = mix(c, pale, smoothstep(0.05, 0.12, fract(s)) * (1.0 - smoothstep(0.12, 0.2, fract(s))) * top * 0.35);
			vec2 spot = vec2(abs(rest.x) - 0.034, (fract(s) - 0.55) * SEG_STEP);
			c = mix(c, dark, (1.0 - smoothstep(0.004, 0.006, length(spot))) * top * smoothstep(-0.2, -0.1, rest.z) * 0.7);
		}
		float neck = 1.0 - smoothstep(0.0, 0.004, abs(rest.z - NECK));
		c = mix(c, dark, neck * 0.7);
	} else if (p == 1) {
		// A lobe: pale pink-tan, darker at its root, fine dark veins running out along it, a
		// darker trailing edge.
		c = mix(body_colour, lobe_colour, smoothstep(0.0, 0.35, along));
		float veins = smoothstep(0.75, 1.0, sin((rest.z - rest.x * 0.55) * 900.0));
		c = mix(c, c * 0.72, veins * along * 0.6);
		c *= 0.92 + 0.12 * grain;
		rough = 0.45;
	} else if (p == 2) {
		// A tail blade: red, paler towards its tip, its edge dark.
		c = mix(body_colour, lobe_colour, 0.25 + 0.4 * along);
		c = mix(c, dark, smoothstep(0.85, 1.0, along) * 0.6);
		c *= 0.92 + 0.12 * grain;
	} else if (p == 3) {
		if (along < 0.5) {
			// a stalk
			c = body_colour * (0.9 + 0.15 * grain);
		} else {
			// The eye: dark and glossy, packed with tiny facets.
			vec3 d = normalize(rest - joint);
			vec2 f = vec2(atan(d.z, d.x) * 34.0, asin(clamp(d.y, -1.0, 1.0)) * 34.0);
			vec2 cell = fract(f) - 0.5;
			c = mix(vec3(0.06, 0.05, 0.05), vec3(0.16, 0.12, 0.1), 1.0 - smoothstep(0.25, 0.45, length(cell)));
			rough = 0.18;
			spec = 0.8;
			float lid;
			float shine;
			c = eye_colour(rest, c, body_colour, lid, shine);
			// cartooned: glossy, two bright highlights up and forward on it, and a dark rim so it
			// reads from far off
			float open = (1.0 - lid) * cartoon_eyes;
			c = mix(c, c * 0.15, open * (1.0 - smoothstep(0.12, 0.38, dot(nn, VIEW))));
			c = mix(c, vec3(1.0), shine * open);
			emit = vec3(0.6) * shine * open;
			rough = mix(rough, 0.1, open);
			rough = mix(rough, 0.6, lid);
		}
	} else if (p == 4) {
		// An arm: reddish-brown, each segment paler in its middle and dark at its joints.
		float seg = fract(index * 0.5);
		c = mix(body_colour, lobe_colour, 0.25 + 0.15 * seg) * (0.9 + 0.15 * grain);
		c = mix(c, dark, 0.15 * along);
	} else if (p == 5) {
		// A spine: pale, darker at its point.
		c = mix(pale, dark, smoothstep(0.6, 1.0, along) * 0.7);
		rough = 0.35;
	} else {
		// The mouth: pale radial plates round a dark opening.
		float a = atan(rest.x, rest.z - (-0.3));
		float plates = smoothstep(0.6, 0.95, abs(sin(a * 16.0)));
		c = mix(pale, pale * 0.65, plates);
		c = mix(c, vec3(0.05, 0.02, 0.02), smoothstep(0.8, 0.95, along));
		rough = 0.4;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = emit;
}
