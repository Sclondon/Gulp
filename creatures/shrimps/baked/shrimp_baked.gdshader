shader_type spatial;
// The shrimps (shrimp.gd): every marking drawn here (no texture files), their walking, their swimmerets, their tail
// flick, the mantis shrimp's punch and swivelling eyes, the pistol shrimp's snap, the waving antennae and the cartoon
// eyes. What each point is comes from the model (tools/build_shrimps.py): UV2.y the part times 16 plus which one of
// them it is (0 the body, 1 a walking leg, 2 a swimmeret, 3 an eye, 4 an antenna or antennule, 5 an antennal scale,
// 6 the tail fan, 7 the rostrum, 8 a mouthpart, 9 a claw's arm, 10 a claw's moving part); the colour's red, green and
// blue the joint the part turns about (a place in the box box_min to box_max); the colour's alpha one more number (on
// a leg 0 above the knee and 1 below it; along an antenna, a swimmeret or a paddle 0 at its root to 1 at its tip; on
// an eye 0 its stalk and 1 the eye; on the mantis shrimp's forearm 1 the club, 0.5 the hook); UV.x, UV.y and UV2.x a
// second place (on a leg its knee, on the mantis shrimp's arms the elbow).
//
// Everything that moves is a function of `phase` (and the amounts below) alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has. One opaque draw, back faces culled.
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


// Which shrimp (set by Shrimp with its model): 0 the scarlet cleaner, 1 the peacock mantis, 2 the pistol shrimp.
uniform int kind = 0;
// Set per kind by Shrimp, as its model is built: the box its joints are written in; how many legs a side (the wave
// of steps runs over them in a beat); a step's length at `walk` 1 and how high a foot lifts; the tail flick's start
// (z), the middle line's height there, the length that bends and how far it curls at 1 (radians); where the abdomen's
// segments start and how long each is.
uniform vec3 box_min = vec3(-0.012, 0.0, -0.032);
uniform vec3 box_max = vec3(0.012, 0.024, 0.032);
uniform float legs_a_side = 5.0;
uniform float stride = 0.003;
uniform float lift = 0.0016;
uniform float curl_from = -0.0018;
uniform float curl_y = 0.0103;
uniform float curl_length = 0.022;
uniform float curl_max = 2.7;
uniform float seg0 = -0.0018;
uniform float seg_step = 0.0039;

// How far through one cycle of its steps and beats (0..1, it wraps). Set by Shrimp.
uniform float phase = 0.0;
// Walking: 0 standing, 1 a walk forwards, -1 backwards.
uniform float walk = 0.0;
// How widely its swimmerets beat: 0 still, 1 swimming.
uniform float paddle = 0.0;
// Its tail flick: 0 straight, 1 the abdomen and tail fan curled right down and under.
uniform float flick : hint_range(0.0, 1.0) = 0.0;
// How far its long antennae swing side to side (radians at their tips), and up and down (the cleaner waves them).
uniform float feel = 0.12;
uniform float wave_up = 0.0;
// The mantis shrimp: 0 its arms folded, 1 punched right out. How far its eyes swivel on their own (0 still).
uniform float strike : hint_range(0.0, 1.0) = 0.0;
uniform float swivel = 0.0;
// The pistol shrimp: 0 its big claw shut, 1 its finger cocked wide open (a snap is 1 to 0 at once).
uniform float snap : hint_range(0.0, 1.0) = 0.0;

// Its colours: the shell; a second shell colour (the cleaner's yellow sides, the mantis shrimp's pale sides, the
// pistol shrimp's mottling); white; and three accents (the cleaner's legs, -, -; the mantis shrimp's red arms and
// legs, its orange scales and tail, its blue paddles; the pistol shrimp's finger tips, -, -).
uniform vec3 shell : source_color = vec3(0.8, 0.08, 0.06);
uniform vec3 shell2 : source_color = vec3(0.96, 0.72, 0.32);
uniform vec3 white : source_color = vec3(0.97, 0.96, 0.93);
uniform vec3 accent1 : source_color = vec3(0.9, 0.55, 0.5);
uniform vec3 accent2 : source_color = vec3(0.98, 0.55, 0.12);
uniform vec3 accent3 : source_color = vec3(0.12, 0.42, 0.9);

// Cartoon eyes: 0 its eyes as they are, 1 the cartoon eye (each kind its own: Shrimp's EYES). `eye_look` slides the
// iris and pupil (x towards its head, y up, -1..1); `blink` brings a lid the colour of its shell down (0 open, 1 shut).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// Set per kind by Shrimp: the left eye's middle, the way it looks, its stalk's foot; how much bigger the cartoon eye
// grows; its white and iris; how wide the iris and the pupil are (as the sine of the angle from where it looks); the
// pupil's shape (width, height); where the upper lid rests (1 above the eye, -1 shut) and how it slopes; how far
// the iris slides at `eye_look` 1; 1 for the mantis shrimp's hexagon-faceted eye with its band of colours.
uniform vec3 eye_middle = vec3(0.00286, 0.01251, -0.01908);
uniform vec3 eye_gaze = vec3(0.6, 0.15, -0.78);
uniform float eye_grow = 1.6;
uniform vec3 eye_white : source_color = vec3(0.97, 0.96, 0.92);
uniform vec3 eye_iris : source_color = vec3(0.85, 0.32, 0.12);
uniform float iris_size = 0.56;
uniform float pupil_size = 0.34;
uniform vec2 pupil_shape = vec2(1.0, 1.0);
uniform float lid_rest = 1.08;
uniform float lid_slope = 0.0;
uniform float look_reach = 0.36;
uniform float eye_hex = 0.0;
uniform vec3 lid_colour : source_color = vec3(0.8, 0.12, 0.08);

// The mantis shrimp's punch: how far the merus turns up about its shoulder and the forearm about its elbow at 1; the
// pistol shrimp's finger's widest cock (radians).
const float STRIKE_SHOULDER = 0.6;
const float STRIKE_ELBOW = 1.9;
const float SNAP_OPEN = 1.25;
const float ON_GROUND = 0.65;
const float KNEE_AT = 0.45;

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

// Where a foot is in its step: x how far ahead of its middle place (0.5 set down, -0.5 picked up), y how high.
vec2 foot_at(float cycle) {
	float c = fract(cycle);
	if (c < ON_GROUND) {
		return vec2(0.5 - c / ON_GROUND, 0.0);
	}
	float u = (c - ON_GROUND) / (1.0 - ON_GROUND);
	return vec2(-0.5 * cos(3.14159265 * u), sin(3.14159265 * u));
}

// One point of a leg, moved so that the leg's tip is `shift` from where it stands at rest: two stiff lengths in an
// upright plane, from its joint to its knee and from its knee to its tip on the ground, worked out exactly (the
// spot prawn's: GameCommon spot-prawn).
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
	float l1 = clamp(length(now), abs(a - b) + 0.00001, a + b - 0.00001);
	float lift_by = atan(now.y, now.x) + acos(clamp((a * a + l1 * l1 - b * b) / (2.0 * a * l1), -1.0, 1.0))
			- atan(was.y, was.x) - acos(clamp((a * a + l0 * l0 - b * b) / (2.0 * a * l0), -1.0, 1.0));
	float open = acos(clamp((a * a + b * b - l1 * l1) / (2.0 * a * b), -1.0, 1.0))
			- acos(clamp((a * a + b * b - l0 * l0) / (2.0 * a * b), -1.0, 1.0));
	if (lower > 0.5) {
		v = knee + turned(v - knee, axis, open);
		n = turned(n, axis, open);
	}
	v = joint + turned(turned(v - joint, axis, lift_by), up, yaw);
	n = turned(turned(n, axis, lift_by), up, yaw);
}

// The abdomen and the tail fan curled down and under (see `flick`).
void curl_under(inout vec3 v, inout vec3 n) {
	float d = v.z - curl_from;
	if (flick < 0.001 || d <= 0.0) {
		return;
	}
	float k = flick * curl_max / curl_length;
	float r = 1.0 / k;
	float dc = min(d, curl_length);
	float extra = d - dc;
	float a = dc * k;
	float h = v.y - curl_y;
	float ca = cos(a);
	float sa = sin(a);
	v = vec3(v.x, curl_y - r + (r + h) * ca - extra * sa, curl_from + (r + h) * sa + extra * ca);
	n = vec3(n.x, n.y * ca - n.z * sa, n.y * sa + n.z * ca);
}

// The eye on the side of `p` (at rest): its middle, the way it looks, its up and its across (towards the head).
void eye_frame(vec3 p, out vec3 mid, out vec3 gaze, out vec3 up, out vec3 across) {
	float side = p.x >= 0.0 ? 1.0 : -1.0;
	mid = eye_middle * vec3(side, 1.0, 1.0);
	gaze = normalize(eye_gaze * vec3(side, 1.0, 1.0));
	up = normalize(vec3(0.0, 1.0, 0.0) - gaze * gaze.y);
	across = normalize(cross(up, gaze)) * side;
}

// How far `p` is inside a hexagon of a honeycomb of cells a unit across (0 on an edge, 0.5 at a middle).
float hex_inside(vec2 p) {
	vec2 r = vec2(1.0, 1.7320508);
	vec2 h = r * 0.5;
	vec2 a = mod(p, r) - h;
	vec2 b = mod(p - h, r) - h;
	vec2 g = dot(a, a) < dot(b, b) ? a : b;
	vec2 q = abs(g);
	return 0.5 - max(dot(q, normalize(r)), q.x);
}

// The colour of a point `p` (at rest) of an eye: `plain` as it is, mixed to the cartoon eye by `cartoon_eyes`, the
// lid over it as `blink` (and, cartooned, `lid_rest`) has it; `lid` is set to how far the lid covers it, `glint` to
// where the cartoon eye's highlights are.
vec3 eye_colour(vec3 p, vec3 plain, out float lid, out float glint) {
	vec3 mid, gaze, up, across;
	eye_frame(p, mid, gaze, up, across);
	vec3 d = normalize(p - mid);
	vec2 q = vec2(dot(d, across), dot(d, up));
	float front = smoothstep(-0.05, 0.1, dot(d, gaze));
	vec2 at = q - eye_look * look_reach;
	float r = length(at);
	vec3 c;
	if (eye_hex > 0.5) {
		// the mantis shrimp's: a bright faceted eye all over (no white), a band of colours across its middle, its
		// dark pseudopupil looking about over the facets
		c = eye_iris * (0.85 + 0.3 * smoothstep(0.9, 0.0, length(q)));
		float band = 1.0 - smoothstep(0.17, 0.2, abs(q.y));
		vec3 rows = q.y > 0.06 ? vec3(0.62, 0.3, 0.85) : (q.y < -0.06 ? vec3(1.0, 0.42, 0.62) : vec3(1.0, 0.86, 0.25));
		c = mix(c, rows, band * front);
		float facets = hex_inside(q * 9.0);
		c *= mix(1.0, 0.55, (1.0 - smoothstep(0.03, 0.1, facets)) * front);
		c = mix(c, c * 0.45, (1.0 - smoothstep(0.01, 0.03, abs(q.y) - 0.185)) * step(abs(q.y), 0.215) * front);
		float pupil = 1.0 - smoothstep(pupil_size - 0.04, pupil_size, length(at / pupil_shape));
		c = mix(c, vec3(0.02, 0.02, 0.04), pupil * front);
	} else {
		c = eye_white;
		float iris = (1.0 - smoothstep(iris_size - 0.03, iris_size, r)) * front;
		c = mix(c, eye_iris * mix(1.25, 0.6, smoothstep(0.0, iris_size, r)), iris);
		c = mix(c, vec3(0.03, 0.02, 0.02), (1.0 - smoothstep(0.015, 0.045, abs(r - iris_size))) * front);
		float pupil = 1.0 - smoothstep(pupil_size - 0.03, pupil_size, length(at / pupil_shape));
		c = mix(c, vec3(0.01, 0.01, 0.015), pupil * front);
	}
	c = mix(plain, c, cartoon_eyes);
	// the upper lid: its edge comes down from above the eye (or from where it rests) to below it
	float edge = mix(mix(1.08, lid_rest, cartoon_eyes), -1.08, blink) - lid_slope * q.x;
	lid = smoothstep(edge - 0.02, edge + 0.02, q.y);
	glint = smoothstep(0.955, 0.97, dot(d, normalize(gaze + up * 0.62 + across * 0.3)));
	glint = max(glint, 0.7 * smoothstep(0.991, 0.995, dot(d, normalize(gaze + up * 0.18 + across * 0.52))));
	c = mix(c, lid_colour, lid);
	c = mix(c, lid_colour * 0.35, (1.0 - smoothstep(0.02, 0.07, abs(q.y - edge))) * step(edge, 1.0) * max(cartoon_eyes, step(0.001, blink)));
	return c;
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	float code = floor(UV2.y + 0.5);
	part = floor((code + 0.5) / 16.0);
	index = code - part * 16.0;
	along = COLOR.a;
	kk = vec3(UV.x, UV.y, UV2.x);
	vec3 joint = mix(box_min, box_max, COLOR.rgb);
	joint_at = joint;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	vec3 x_axis = vec3(1.0, 0.0, 0.0);
	int p = int(part + 0.5);
	float side = joint.x >= 0.0 ? 1.0 : -1.0;
	if (p == 1) {
		// A walking leg: a wave of steps from back to front, the two sides half a step apart.
		float cycle = phase - index / legs_a_side + (side > 0.0 ? 0.0 : 0.5);
		vec2 f = foot_at(cycle);
		vec3 shift = vec3(0.0, lift * min(abs(walk), 1.0) * f.y, -walk * stride * f.x);
		leg_move(v, n, joint, kk, along, shift);
	} else if (p == 2) {
		// A swimmeret: it swings forwards and back about where it hangs, each pair a fifth of a beat ahead of the one
		// in front of it.
		float a = paddle * (0.15 + 0.55 * sin(6.2831853 * (phase + 0.2 * index)));
		v = joint + turned(v - joint, x_axis, a);
		n = turned(n, x_axis, a);
	} else if (p == 3) {
		if (along > 0.5 && cartoon_eyes > 0.0) {
			// the cartoon eye: bigger about its own middle
			vec3 mid = eye_middle * vec3(sign(rest.x), 1.0, 1.0);
			v = mid + (v - mid) * mix(1.0, eye_grow, cartoon_eyes);
		}
		if (swivel > 0.0) {
			// each eye turns on its stalk on its own, the two never in step
			float yaw = side > 0.0 ? sin(6.2831853 * 2.0 * phase) : sin(6.2831853 * 3.0 * phase + 2.0);
			float pitch = side > 0.0 ? sin(6.2831853 * 3.0 * phase + 1.0) : cos(6.2831853 * 2.0 * phase);
			yaw *= 0.55 * swivel * side;
			pitch *= 0.35 * swivel;
			v = joint + turned(turned(v - joint, x_axis, pitch), vec3(0.0, 1.0, 0.0), yaw);
			n = turned(turned(n, x_axis, pitch), vec3(0.0, 1.0, 0.0), yaw);
		}
	} else if (p == 4) {
		// An antenna (index 0) swings slowly out and in, more towards its tip, and (the cleaner's) waves up and down;
		// an antennule (index 1) a little.
		float k = index < 0.5 ? 1.0 : 0.35;
		float a = side * feel * k * along * sin(6.2831853 * (phase - 0.3 * along));
		float b = wave_up * k * along * sin(6.2831853 * (2.0 * phase - 0.5 * along) + (side > 0.0 ? 0.0 : 1.4));
		v = joint + turned(turned(v - joint, x_axis, b), vec3(0.0, 1.0, 0.0), a);
		n = turned(turned(n, x_axis, b), vec3(0.0, 1.0, 0.0), a);
	} else if (p == 9 && kind == 1) {
		// The mantis shrimp's merus: it turns up about its shoulder as it punches.
		float a1 = STRIKE_SHOULDER * smoothstep(0.0, 0.4, strike);
		v = joint + turned(v - joint, x_axis, a1);
		n = turned(n, x_axis, a1);
	} else if (p == 10 && kind == 1) {
		// Its forearm and club: swung forward about its elbow, carried with the merus.
		float a1 = STRIKE_SHOULDER * smoothstep(0.0, 0.4, strike);
		float a2 = STRIKE_ELBOW * smoothstep(0.2, 1.0, strike);
		v = joint + turned(kk + turned(v - kk, x_axis, a2) - joint, x_axis, a1);
		n = turned(turned(n, x_axis, a2), x_axis, a1);
	} else if (p == 10 && kind == 2) {
		// The pistol shrimp's big finger: cocked open about its hinge.
		float a = SNAP_OPEN * snap;
		v = joint + turned(v - joint, x_axis, a);
		n = turned(n, x_axis, a);
	}
	if (p == 0 || p == 2 || p == 6) {
		curl_under(v, n);
	}
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

