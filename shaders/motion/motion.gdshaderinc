// Motion families (GameCommon `godot/motion-families`): what every family shader shares. The user,
// 2026-11-19: "each animal should not need its own shader for swimming or motion"; they chose a few
// motion families, each animal setting numbers as uniforms. A family shader (swim, flap, jointed,
// radial) is this file plus its own core; an animal is that shader plus its numbers (scripts/motion.gd,
// set by BakedLook from the animal's `baked/<shader>_motion.gd`) plus what each point of its model is,
// written into the baked meshes by tools/motion_labels.gd:
//
//   CUSTOM0.xy  where its paint is (the bake's atlas)
//   CUSTOM0.z   its part (0..23: which of the animal's moves take it)
//   CUSTOM0.w   weight 1; CUSTOM1.xyzw weights 2..5; CUSTOM2.w weight 6; CUSTOM3.w weight 7
//   CUSTOM2.xyz a point of its own (a hinge, a joint); CUSTOM3.xyz a way of its own (a fin's flat side, an axis)
//
// The moves ("ops", up to MOTION_OPS) are run in order on each point at rest, before the family's core
// (the swimming wave, the wings). Each op:
//   amount = (drive * drive2 * (c + a * shape(angle)) + plus * drive3) * weight[w] * weight[w2]
//   angle  = TAU * phase * beats * input[beat] + off + (the -x side ? side_off : 0) + per_s * s + per_lag * weight[lag]
// and then, by its type: 1 turn about a point and an axis by `amount` radians; 2 move along a way by
// `amount` metres; 3 scale about a point (1 + amount * k1 across the axis, 1 + amount * k2 along it);
// 4 draw towards a point along a way, or straight to it with no way (by `amount`, 0..1); 5 bend along a way beyond `k1` metres from a
// point, `amount` radians over `k2` metres (an arm curling). Flags: 1 mirrored (the -x side does the
// mirror image: worked out on the +x side), 2 amount times the side (+1 / -1), 4 the point is the
// vertex's own, 8 the way is the vertex's own, 16 the way is the normal at rest, 32 a bend's second
// axis is up (else sideways, across the way and up), 64 run after the family's core (in the swum pose), 128 the point is the vertex's own way (a second
// point of its own), 256 the drive's size only (its sign dropped), 512 a bend ends after its k2 metres
// (beyond, the rest is carried straight on). Type 6 (the jointed family, MOTION_LEGS): a leg's stride: the vertex's own point is
// its joint, its own way its knee, weight[w] over 0.5 the lower leg; the foot moves along the op's way by
// drive * k1 * stride(angle) and up by k2 * min(|drive|, 1) * lift(angle); f.w is the knee's share of
// the reach (see motion_leg). Shapes: 0 sine, 1 sine's upper half only, 2 a
// foot's stride (back along the ground, then forward through the air: `ground` of the cycle on it),
// 3 a foot's lift (0 on the ground, a bump in the air), 4 on (c while the drive is above 0).
//
// `input` is the table below: 0 is 1.0, the rest are this family's live settings by name, which the
// animals' scripts set each frame as they did on their own shaders (scripts/motion.gd keeps the same
// list: change both).

#define MOTION_OPS 24

uniform float phase = 0.0;
uniform float sway = 1.0;
uniform float gape = 0.0;
uniform float cartoon_eyes = 0.0;
uniform float blink = 0.0;
uniform float curl = 0.0;
uniform float arch = 0.0;
uniform float tail_beats = 1.0;
uniform float scull = 0.0;
uniform float sculls = 1.0;
uniform float swim = 0.0;
uniform float dorsal = 0.0;
uniform float strokes = 1.0;
uniform float row = 0.0;
uniform float breaths = 1.0;
uniform float gills = 0.0;
uniform float walk = 0.0;
uniform float gape_breath = 0.0;
uniform float gill_flare = 0.0;
uniform float first_dorsal = 0.0;
uniform float ripples = 1.0;
uniform float open = 0.0;
uniform float withdraw = 0.0;
uniform float spread = 0.0;
uniform float strike = 0.0;
uniform float scoops = 0.0;
uniform float wings = 0.0;
uniform float snap = 0.0;
uniform float buzzes = 1.0;
uniform float paddle = 0.0;
uniform float flick = 0.0;
uniform float feel = 0.0;
uniform float flap = 0.0;
uniform float grasp = 0.0;
uniform float billows = 1.0;
uniform float flow = 0.0;
uniform float flare = 0.0;
uniform float settle = 0.0;
uniform float dig = 0.0;
uniform float waggle = 0.0;
uniform float fans = 1.0;
uniform float twitches = 1.0;
uniform float fan = 0.0;
uniform float twitch = 0.0;
uniform float furl = 0.0;
uniform float fin_ripples = 1.0;
uniform float flaps = 1.0;
uniform float breathe = 0.0;
uniform float sit = 0.0;
uniform float billow = 0.0;
uniform float ripple = 0.0;
uniform float swing = 0.0;
uniform float jaw = 0.0;
uniform float tusk = 0.0;
uniform float pearl = 0.0;
uniform float puff = 0.0;
uniform float riding = 0.0;
uniform float stand = 0.0;
uniform float claws = 0.0;
uniform float sail = 0.0;
uniform float bobs = 1.0;
uniform float bob = 0.0;
uniform float grip = 0.0;
uniform float fold = 0.0;
uniform float crest = 0.0;
uniform float afloat = 0.0;
uniform float flex = 0.0;
uniform float tuck = 0.0;
uniform float enroll = 0.0;
uniform float curl_up = 0.0;
uniform float retract = 0.0;
uniform float fin_waves = 1.0;
uniform float fin_lift = 0.0;
uniform float arm_sway = 0.0;
uniform float wade = 0.0;
uniform float lean = 0.0;
uniform float sink = 0.0;
uniform float fin_tall = 0.0;
uniform float tusks = 0.0;
uniform float humps = 0.0;
uniform float rear = 0.0;
uniform float coil = 0.0;
uniform float sway_speed = 1.0;
uniform float limb_beats = 1.0;
uniform float strand_beats = 1.0;
uniform float fin_beats = 1.0;
uniform float kelpie = 0.0;
uniform float flaps_open = 0.0;
// (fixed numbers an animal's ops read as a drive or a beat; set from its spec)
uniform float aux0 = 0.0;
uniform float aux1 = 0.0;
uniform float aux2 = 0.0;
uniform float aux3 = 0.0;

// The moves (see above), packed by scripts/motion.gd.
uniform int op_count = 0;
uniform vec4 op_a[MOTION_OPS]; // type, parts (bits), flags, drive + 128 * drive2 + 16384 * drive3
uniform vec4 op_b[MOTION_OPS]; // c, a, beats, off
uniform vec4 op_c[MOTION_OPS]; // side_off, per_s, per_lag, w + 8 * w2 + 64 * lag
uniform vec4 op_d[MOTION_OPS]; // point, k1
uniform vec4 op_e[MOTION_OPS]; // way, k2
uniform vec4 op_f[MOTION_OPS]; // beat input, shape, ground, plus (or a leg's knee_at)

// Where along the body a point is (s: 0 at `motion_nose`, 1 a body length behind it).
uniform float motion_length = 1.0;
uniform float motion_nose = -0.5;

varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : hint_default_black, filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;

vec3 motion_turned(vec3 p, vec3 k, float a) {
	float c = cos(a);
	float s = sin(a);
	return p * c + cross(k, p) * s + k * dot(k, p) * (1.0 - c);
}

float motion_shape(int shape, float angle, float ground) {
	if (shape == 1) {
		return max(sin(angle), 0.0);
	}
	if (shape == 2 || shape == 3) {
		float c = fract(angle / 6.2831853);
		if (c < ground) {
			return shape == 2 ? 0.5 - c / ground : 0.0;
		}
		float u = (c - ground) / (1.0 - ground);
		return shape == 2 ? -0.5 * cos(3.14159265 * u) : sin(3.14159265 * u);
	}
	return sin(angle);
}

// Bends (a, b) round an arc beyond `from` along a, curving by k a metre (the curl_bend of the old shaders).
// Beyond `to` the rest goes on straight, along the arc's end (to: 1e9 for no end).
void motion_arc(inout float a, inout float b, inout float na, inout float nb, float from, float k, float to) {
	if (a <= from || abs(k) < 0.0001) {
		return;
	}
	float over = max(a - to, 0.0);
	a -= over;
	float f = k * (a - from);
	float c = cos(f);
	float s = sin(f);
	float a2 = from + s / k - b * s + over * c;
	b = (1.0 - c) / k + b * c + over * s;
	a = a2;
	float n2 = na * c - nb * s;
	nb = na * s + nb * c;
	na = n2;
}

#ifdef MOTION_LEGS
// A leg from its joint (on the body) through its knee to its foot on the ground (the old crustacean
// shaders' leg_move): the foot moved by `shift`, the upper leg turned at the joint (lifted and swung) and
// the lower opened at the knee (`lower`) so it reaches there. `knee_at`: the knee's share of the way out.
void motion_leg(inout vec3 v, inout vec3 n, vec3 joint, vec3 knee, bool lower, vec3 shift, float knee_at) {
	vec2 flat_way = knee.xz - joint.xz;
	float knee_out = length(flat_way);
	if (knee_out < 0.000001) {
		return;
	}
	vec3 d = vec3(flat_way.x, 0.0, flat_way.y) / knee_out;
	vec3 up = vec3(0.0, 1.0, 0.0);
	vec3 axis = cross(d, up);
	float a = length(knee - joint);
	vec3 tip = vec3(joint.x, 0.0, joint.z) + d * (knee_out / knee_at);
	float b = length(tip - knee);
	vec2 was = vec2(knee_out / knee_at, -joint.y);
	vec3 to = tip + shift - joint;
	vec3 across = cross(up, d);
	float yaw = atan(dot(to, across), dot(to, d));
	vec2 now = vec2(length(to.xz), to.y);
	float l0 = length(was);
	float l1 = clamp(length(now), abs(a - b) + 0.0001, a + b - 0.0001);
	float lift = atan(now.y, now.x) + acos(clamp((a * a + l1 * l1 - b * b) / (2.0 * a * l1), -1.0, 1.0))
			- atan(was.y, was.x) - acos(clamp((a * a + l0 * l0 - b * b) / (2.0 * a * l0), -1.0, 1.0));
	float knee_open = acos(clamp((a * a + b * b - l1 * l1) / (2.0 * a * b), -1.0, 1.0))
			- acos(clamp((a * a + b * b - l0 * l0) / (2.0 * a * b), -1.0, 1.0));
	if (lower) {
		v = knee + motion_turned(v - knee, axis, knee_open);
		n = motion_turned(n, axis, knee_open);
	}
	v = joint + motion_turned(motion_turned(v - joint, axis, lift), up, yaw);
	n = motion_turned(motion_turned(n, axis, lift), up, yaw);
}
#endif

// One live setting by its number in the table (for the families' cores).
float motion_input(int i) {
	float inputs[96] = float[96](1.0, sway, gape, cartoon_eyes, blink, curl, arch, tail_beats, scull, sculls,
			swim, dorsal, strokes, row, breaths, gills, walk, gape_breath, gill_flare, first_dorsal,
			ripples, open, withdraw, spread, strike, scoops, wings, snap, buzzes, paddle,
			flick, feel, flap, grasp, billows, flow, flare, settle, dig, waggle,
			fans, twitches, fan, twitch, furl, fin_ripples, flaps, breathe, sit, billow,
			ripple, swing, jaw, tusk, pearl, puff, riding, stand, claws, sail,
			bobs, bob, grip, fold, crest, afloat, flex, tuck, enroll, curl_up,
			retract, fin_waves, fin_lift, arm_sway, wade, lean, sink, fin_tall, tusks, humps,
			rear, coil, sway_speed, limb_beats, strand_beats, fin_beats, kelpie, flaps_open, aux0, aux1,
			aux2, aux3, phase, 0.0, 0.0, 0.0);
	return inputs[i];
}

// Runs the animal's moves on a point at rest (v, n; its normal at rest; its side, +1 or -1 by x at rest;
// CUSTOM0..3, which only vertex() can read).
void motion_ops(inout vec3 v, inout vec3 n, vec3 rest_n, float side, vec4 c0, vec4 c1, vec4 c2, vec4 c3, bool post) {
	float inputs[96] = float[96](1.0, sway, gape, cartoon_eyes, blink, curl, arch, tail_beats, scull, sculls,
			swim, dorsal, strokes, row, breaths, gills, walk, gape_breath, gill_flare, first_dorsal,
			ripples, open, withdraw, spread, strike, scoops, wings, snap, buzzes, paddle,
			flick, feel, flap, grasp, billows, flow, flare, settle, dig, waggle,
			fans, twitches, fan, twitch, furl, fin_ripples, flaps, breathe, sit, billow,
			ripple, swing, jaw, tusk, pearl, puff, riding, stand, claws, sail,
			bobs, bob, grip, fold, crest, afloat, flex, tuck, enroll, curl_up,
			retract, fin_waves, fin_lift, arm_sway, wade, lean, sink, fin_tall, tusks, humps,
			rear, coil, sway_speed, limb_beats, strand_beats, fin_beats, kelpie, flaps_open, aux0, aux1,
			aux2, aux3, phase, 0.0, 0.0, 0.0);
	float weights[8] = float[8](1.0, c0.w, c1.x, c1.y, c1.z, c1.w, c2.w, c3.w);
	int part = int(c0.z + 0.5);
	for (int i = 0; i < op_count; i++) {
		vec4 a = op_a[i];
		int flags = int(a.z);
		if (((flags & 64) != 0) != post || ((int(a.y) >> part) & 1) == 0) {
			continue;
		}
		vec4 b = op_b[i];
		vec4 c = op_c[i];
		vec4 f = op_f[i];
		int drives = int(a.w);
		int slots = int(c.w);
		float drive = inputs[drives & 127] * inputs[(drives >> 7) & 127];
		if ((flags & 256) != 0) {
			drive = abs(drive);
		}
		float w = weights[slots & 7] * weights[(slots >> 3) & 7];
		int shape = int(f.y);
		float angle = 6.2831853 * phase * b.z * inputs[int(f.x)] + b.w + (side < 0.0 ? c.x : 0.0)
				+ c.y * (v.z - motion_nose) / motion_length + c.z * weights[(slots >> 6) & 7];
		int type = int(a.x);
#ifdef MOTION_LEGS
		if (type == 6) {
			motion_leg(v, n, c2.xyz, c3.xyz, w > 0.5, op_e[i].xyz * (drive * op_d[i].w * motion_shape(2, angle, f.z))
					+ vec3(0.0, op_e[i].w * min(abs(drive), 1.0) * motion_shape(3, angle, f.z), 0.0), f.w);
			continue;
		}
#endif
		float amount;
		if (shape == 4) {
			amount = inputs[(drives >> 7) & 127] * b.x * step(0.00001, inputs[drives & 127]) * w;
		} else {
			amount = drive * (b.x + b.y * motion_shape(shape, angle, f.z)) * w;
		}
		// (plus a second, steady part: f.w times a third drive)
		amount += f.w * inputs[drives >> 14] * w;
		if ((flags & 2) != 0) {
			amount *= side;
		}
		if (abs(amount) < 0.0000001) {
			continue;
		}
		bool mirrored = (flags & 1) != 0 && side < 0.0;
		vec3 at = (flags & 4) != 0 ? c2.xyz : ((flags & 128) != 0 ? c3.xyz : op_d[i].xyz);
		vec3 way = (flags & 8) != 0 ? c3.xyz : ((flags & 16) != 0 ? rest_n : op_e[i].xyz);
		if (mirrored) {
			v.x = -v.x;
			n.x = -n.x;
			if ((flags & 132) != 0) {
				at.x = -at.x;
			}
			if ((flags & 24) != 0) {
				way.x = -way.x;
			}
		}
		if (type == 1) {
			vec3 k = normalize(way);
			v = at + motion_turned(v - at, k, amount);
			n = motion_turned(n, k, amount);
		} else if (type == 2) {
			v += way * amount;
		} else if (type == 3) {
			vec3 k = normalize(way);
			vec3 d = v - at;
			vec3 along = k * dot(d, k);
			v = at + (d - along) * (1.0 + amount * op_d[i].w) + along * (1.0 + amount * op_e[i].w);
		} else if (type == 4) {
			v += (dot(way, way) > 0.0 ? way * dot(at - v, way) : at - v) * amount;
		} else if (type == 5) {
			vec3 u = normalize(way);
			vec3 up = vec3(0.0, 1.0, 0.0);
			vec3 bw = (flags & 32) != 0 ? up : normalize(cross(up, u));
			vec3 d = v - at;
			float pa = dot(d, u);
			float pb = dot(d, bw);
			vec3 rest_of = d - u * pa - bw * pb;
			float na = dot(n, u);
			float nb = dot(n, bw);
			vec3 n_rest = n - u * na - bw * nb;
			motion_arc(pa, pb, na, nb, op_d[i].w, amount / max(op_e[i].w, 0.0001), (flags & 512) != 0 ? op_d[i].w + op_e[i].w : 1.0e9);
			v = at + u * pa + bw * pb + rest_of;
			n = u * na + bw * nb + n_rest;
		}
		if (mirrored) {
			v.x = -v.x;
			n.x = -n.x;
		}
	}
}

