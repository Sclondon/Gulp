// The swim family's core (GameCommon `godot/motion-families`): a wave runs back along the body, side to
// side (fish, sharks, eels, seals, reptiles) or up and down (whales, dolphins, otters), carried round the
// body's line so the fins and tail follow it; behind `swim_joint` the tail is one plate; then the turning curl
// and the arch. What each animal sets (scripts/motion.gd fills them from its spec):
//
//   reach(s), body lengths either way = env_poly.x + env_poly.y s + env_poly.z s^2 + env_poly.w s^3
//                                       + env_pow.x * pow(clamp((s - env_pow.y) / (1 - env_pow.y), 0, 1), env_pow.z)
//   side(s) = input[swim_drive] (sway) * still * motion_length * reach(s) * sin(TAU * (phase * tail_beats - s / (wave * swim_wave_scale)) + swim_wave_off)
//
// s runs 0 at `motion_nose` to 1 a body length behind it, clamped to swim_from..swim_joint; the slope there turns the
// point about the line (more, by `swim_wrist`, from `swim_wrist_from` to the swim_joint). Curl: from z `swim_curl_from`, bent
// `curl` radians over `swim_curl_span` metres, the tail round to +x. Arch: from z `swim_arch_from`, `arch` radians
// over `swim_arch_span` metres, up; on both sides of swim_arch_from when `swim_arch_both`, else behind it only.

uniform int swim_axis = 0;
uniform vec4 env_poly = vec4(0.0);
uniform vec3 env_pow = vec3(0.0, 0.0, 2.0);
uniform float wave = 1.0;
uniform float swim_wave_scale = 1.0;
uniform float swim_wave_off = 0.0;
uniform float swim_from = 0.0;
uniform float swim_joint = 1.05;
uniform float swim_wrist = 0.0;
uniform float swim_wrist_from = 0.9;
uniform float swim_curl_from = 0.0;
uniform float swim_curl_span = 1.0;
uniform float swim_arch_from = 0.0;
uniform float swim_arch_span = 1.0;
uniform bool swim_arch_both = true;
// What sizes the wave (a number in the moves' table of live settings: 1 is sway), and what stills it:
// the wave (and, with swim_still_curl, the curl) times clamp(1 - swim_still_by * input[swim_still], 0, 1).
uniform int swim_drive = 1;
uniform int swim_still = 0;
uniform float swim_still_by = 0.0;
uniform bool swim_still_curl = false;

float swim_side(float s, float size) {
	float reach = env_poly.x + s * (env_poly.y + s * (env_poly.z + s * env_poly.w));
	if (env_pow.x != 0.0) {
		reach += env_pow.x * pow(clamp((s - env_pow.y) / (1.0 - env_pow.y), 0.0, 1.0), env_pow.z);
	}
	return size * motion_length * reach * sin(6.2831853 * (phase * tail_beats - s / (wave * swim_wave_scale)) + swim_wave_off);
}

void swim_core(inout vec3 v, inout vec3 n) {
	float still = clamp(1.0 - swim_still_by * motion_input(swim_still), 0.0, 1.0);
	float size = motion_input(swim_drive) * still;
	float bend = swim_still_curl ? curl * still : curl;
	float s = (v.z - motion_nose) / motion_length;
	float zc = clamp(s, swim_from, swim_joint);
	float h = swim_side(zc, size);
	float e = 0.002;
	float slope = (swim_side(zc + e, size) - swim_side(zc - e, size)) / (2.0 * e * motion_length);
	float turn = atan(slope) * (1.0 + swim_wrist * smoothstep(swim_wrist_from, swim_joint, zc));
	float c = cos(turn);
	float sn = sin(turn);
	float z0 = motion_nose + zc * motion_length;
	float along = (s - zc) * motion_length;
	if (swim_axis == 0) {
		v = vec3(h + v.x * c + along * sn, v.y, z0 - v.x * sn + along * c);
		n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	} else {
		v = vec3(v.x, h + v.y * c + along * sn, z0 - v.y * sn + along * c);
		n = vec3(n.x, n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	if (abs(bend) > 0.001) {
		float d = v.z - swim_curl_from;
		if (d > 0.0) {
			float k = bend / swim_curl_span;
			float a = d * k;
			float r = 1.0 / k;
			float cc = cos(a);
			float ss = sin(a);
			n = vec3(n.x * cc + n.z * ss, n.y, -n.x * ss + n.z * cc);
			v = vec3(r + (v.x - r) * cc, v.y, swim_curl_from + (r - v.x) * ss);
		}
	}
	if (abs(arch) > 0.001) {
		float d = v.z - swim_arch_from;
		if (swim_arch_both || d > 0.0) {
			float k = arch / swim_arch_span;
			float a = d * k;
			float r = 1.0 / k;
			float cc = cos(a);
			float ss = sin(a);
			n = vec3(n.x, n.y * cc + n.z * ss, n.z * cc - n.y * ss);
			v = vec3(v.x, r + (v.y - r) * cc, swim_arch_from + (r - v.y) * ss);
		}
	}
}
