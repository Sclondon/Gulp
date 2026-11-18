shader_type spatial;
// The Atlantic horseshoe crab (horseshoe_crab.gd): every marking drawn here (no texture files),
// its walking, its flapping book gills, its swinging tail spike and its rear shell bent on its
// hinge. What each point is comes from the model (tools/build_horseshoe_crab.py): UV2.y the part
// times 16 plus which one of them it is (0 the front shell, 1 the rear shell, 2 the tail spike, 3
// a walking leg, 4 a book gill, 5 an eye, 6 a spine of the rear shell); the colour's red, green
// and blue the joint the part turns about (a place in the box BOX_MIN to BOX_MAX); the colour's
// alpha one more number (on a leg 0 above the knee and 1 below it; along the tail spike or a gill
// 0 at its root to 1 at its end); on a leg UV.x, UV.y and UV2.x the place of its knee; on a shell
// UV.x how far out from its middle (0 to 1, the rim) and UV2.x 1 on its underside.
//
// It walks forwards on five pairs of legs in a wave from back to front (no skeleton: each leg is
// two stiff lengths worked out so that a foot on the ground stays put), mostly hidden under its
// shell. All of it is a function of `phase` alone, so a picture of it loops exactly. Nothing here
// needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model: the box the joints are written in; how far out along a leg (from
// its joint to its tip, seen from above) its knee is; the hinge between the two shells.
const vec3 BOX_MIN = vec3(-0.2, 0.0, -0.3);
const vec3 BOX_MAX = vec3(0.2, 0.15, 0.3);
const float KNEE_AT = 0.45;
const vec3 HINGE = vec3(0.0, 0.03, -0.092);
// How much of a step a foot spends on the ground; how far it moves in one step at `walk` 1, and
// how high it is lifted (metres).
const float ON_GROUND = 0.65;
const float STRIDE = 0.016;
const float LIFT = 0.005;

// How far through one cycle of its steps (0..1, it wraps). Set by HorseshoeCrab.
uniform float phase = 0.0;
// Walking: 0 standing, 1 a walk forwards, -1 backwards; more is a longer stride.
uniform float walk = 0.0;
// How widely its book gills flap: 0 still, 1 breathing hard (as when it swims).
uniform float gills = 0.4;
// How far its tail spike swings from side to side and lifts.
uniform float swing = 0.5;
// The rear shell bent on its hinge (radians): more than 0 down, less than 0 up (as when it
// rights itself or digs in).
uniform float hinge = 0.0;

// The olive-brown of its shell, the darker mottling, the paler colour of its underside and its
// legs, the dark of its eyes.
uniform vec3 olive : source_color = vec3(0.3, 0.26, 0.14);
uniform vec3 mottle : source_color = vec3(0.17, 0.14, 0.08);
uniform vec3 underside : source_color = vec3(0.64, 0.51, 0.32);
uniform vec3 legs : source_color = vec3(0.52, 0.34, 0.19);
uniform vec3 eye : source_color = vec3(0.05, 0.04, 0.03);

varying vec3 rest;
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

// Where a foot is in its step, `cycle` through it: x how far ahead of its middle place it stands
// (0.5 as it is set down, -0.5 as it is picked up), y how high it is lifted (0 on the ground).
vec2 foot_at(float cycle) {
	float c = fract(cycle);
	if (c < ON_GROUND) {
		return vec2(0.5 - c / ON_GROUND, 0.0);
	}
	float u = (c - ON_GROUND) / (1.0 - ON_GROUND);
	return vec2(-0.5 * cos(3.14159265 * u), sin(3.14159265 * u));
}

// One point of a leg, moved so that the leg's tip is `shift` from where it stands at rest (as
// GameCommon's spot prawn and rock crab do it: the joint turns the leg about an upright axis and
// lifts it, the knee opens and shuts, both worked out exactly so a foot on the ground stays put).
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

void vertex() {
	float code = floor(UV2.y + 0.5);
	part = floor((code + 0.5) / 16.0);
	index = code - part * 16.0;
	along = COLOR.a;
	kk = vec3(UV.x, UV.y, UV2.x);
	vec3 joint = mix(BOX_MIN, BOX_MAX, COLOR.rgb);
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	float wave = 6.2831853 * phase;
	if (p == 3) {
		// A walking leg: `index` 0 the first (the front) to 4 the last; a wave of steps from back
		// to front, the two sides half a step apart.
		float side = joint.x >= 0.0 ? 1.0 : -1.0;
		vec2 f = foot_at(phase - 0.2 * index + (side > 0.0 ? 0.0 : 0.5));
		vec3 shift = vec3(0.0, LIFT * min(abs(walk), 1.0) * f.y, -walk * STRIDE * f.x);
		leg_move(v, n, joint, kk, along, shift);
	} else if (p == 4) {
		// A book gill: it flaps down and back up about its hinge, the front one first.
		float a = gills * (0.1 + 0.28 * (0.5 + 0.5 * sin(wave - 0.9 * index)));
		v = joint + turned(v - joint, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	} else if (p == 2) {
		// The tail spike: it swings from side to side and lifts a little, about its root.
		float yaw = swing * 0.14 * sin(wave);
		float pitch = -swing * 0.05 * (0.5 + 0.5 * sin(2.0 * wave));
		v = joint + turned(turned(v - joint, vec3(1.0, 0.0, 0.0), pitch), vec3(0.0, 1.0, 0.0), yaw);
		n = turned(turned(n, vec3(1.0, 0.0, 0.0), pitch), vec3(0.0, 1.0, 0.0), yaw);
	}
	if (p == 1 || p == 2 || p == 4 || p == 6) {
		// The rear shell and all that hangs from it, bent on the hinge.
		v = HINGE + turned(v - HINGE, vec3(1.0, 0.0, 0.0), hinge);
		n = turned(n, vec3(1.0, 0.0, 0.0), hinge);
	}
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 nn = normalize(NORMAL);
	vec3 c;
	float rough = 0.4;
	float spec = 0.45;
	float grain = noise2(rest.xz * 600.0);
	if (p == 0 || p == 1) {
		if (kk.z > 0.5) {
			// The underside: pale tan, a little darker towards the middle.
			c = underside * (0.85 + 0.15 * kk.x) * (0.9 + 0.15 * grain);
			rough = 0.6;
		} else {
			// The top: olive-brown, darker blotches, the rim's flange paler and greener, the
			// ridges' crests worn lighter, fine pits all over; two small dark eyes (the median
			// ocelli) on the middle ridge near the front.
			float blot = noise2(rest.xz * 28.0 + 3.0) * 0.65 + noise2(rest.xz * 70.0) * 0.35;
			c = mix(olive, mottle, smoothstep(0.45, 0.75, blot) * 0.75);
			c = mix(c, olive * vec3(1.2, 1.25, 1.05), smoothstep(0.78, 0.97, kk.x) * 0.55);
			float crest = smoothstep(0.92, 0.99, nn.y) * (1.0 - smoothstep(0.6, 0.8, kk.x));
			c *= 0.9 + 0.12 * grain + 0.12 * crest;
			if (p == 0) {
				float ocelli = 1.0 - smoothstep(0.0008, 0.0013, length(vec2(abs(rest.x) - 0.0022, rest.z + 0.226)));
				c = mix(c, eye, ocelli * 0.6);
			}
			// the rim itself, a dark line
			c = mix(c, mottle * 0.7, smoothstep(0.985, 1.0, kk.x) * 0.6);
			rough = 0.5;
			spec = 0.4;
		}
	} else if (p == 2) {
		// The tail spike: olive-brown above, paler beneath, a row of small dark teeth along its keel.
		c = mix(underside * 0.9, olive, smoothstep(-0.3, 0.4, nn.y));
		c = mix(c, mottle, smoothstep(0.85, 1.0, nn.y) * smoothstep(0.6, 0.95, sin(along * 60.0)) * (1.0 - along) * 0.4);
		rough = 0.35;
		spec = 0.5;
	} else if (p == 3) {
		// A leg: brown, banded at its joints, darker towards its claw.
		c = legs * (0.85 + 0.2 * grain);
		c = mix(c, legs * 0.55, along * 0.6 * smoothstep(0.0, 0.02, kk.y - rest.y));
		c = mix(c, underside, (1.0 - smoothstep(0.002, 0.006, length(rest - kk))) * 0.5);
		rough = 0.5;
	} else if (p == 4) {
		// A book gill: pale, its many fine leaves showing as lines across it.
		c = mix(underside, legs, 0.35) * (0.85 + 0.15 * sin(rest.z * 1800.0 + rest.x * 60.0));
		rough = 0.6;
	} else if (p == 5) {
		// A compound eye: dark and glossy, faintly faceted.
		c = mix(eye, mottle, 0.4) * (0.8 + 0.4 * step(0.5, hash2(floor(rest.xz * 1500.0))));
		rough = 0.35;
		spec = 0.5;
	} else {
		// A spine: olive-brown, darker at its point.
		c = mix(olive, mottle, 0.5) * (0.9 + 0.15 * grain);
		rough = 0.35;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
