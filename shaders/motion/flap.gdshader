shader_type spatial;
// The flap family (GameCommon `godot/motion-families`): rays, whose wings (the sides of the disc) beat
// up and down, bending along the span, the beat running out to the tips and back along the chord. The
// shared moves (motion.gdshaderinc) run before the wings (jaw, eyes, gills) and after them (the tail's
// wave, the pitch, heave and bank of the whole body: flag 64). What each animal sets:
//
//   e: 0 at the wing's root (|x| = wing_root) to 1 at its tip (|x| = wing_tip); zf = (z - wing_chord_from) / wing_chord_span
//   slope(e) = sway * (wing_lift.x + wing_lift.y * e^wing_lift.z + (wing_beat.x + wing_beat.y * e^wing_lift.z) * sin(b)
//              + wing_beat.z * e^wing_beat.w * sin(b - wing_tip_lag)) - side * wing_curl_bank * curl * e^wing_lift.z
//   b = TAU * (phase - wing_lag.x * e - wing_lag.y * zf)
//
// The wing is the slope summed out along the span (WING_STEPS steps), about the plane y = wing_plane;
// only the parts in `wing_parts` (bits) bend.
render_mode cull_back, vertex_lighting;

#include "res://shaders/motion/motion.gdshaderinc"

#define WING_STEPS 8

uniform float wing_root = 0.1;
uniform float wing_tip = 1.0;
uniform float wing_plane = 0.0;
uniform int wing_parts = 1;
uniform vec3 wing_lift = vec3(0.0, 0.0, 1.0);
uniform vec4 wing_beat = vec4(0.0, 0.5, 0.0, 4.0);
uniform float wing_tip_lag = 0.0;
uniform vec2 wing_lag = vec2(0.0);
uniform float wing_chord_from = 0.0;
uniform float wing_chord_span = 1.0;
uniform float wing_curl_bank = 0.0;

float wing_slope(float e, float zf, float side) {
	float b = 6.2831853 * (phase - wing_lag.x * e - wing_lag.y * zf);
	float bend = pow(max(e, 0.0), wing_lift.z);
	float tip = wing_beat.z != 0.0 ? wing_beat.z * pow(max(e, 0.0), wing_beat.w) * sin(b - wing_tip_lag) : 0.0;
	return sway * (wing_lift.x + wing_lift.y * bend + (wing_beat.x + wing_beat.y * bend) * sin(b) + tip) - side * wing_curl_bank * curl * bend;
}

void vertex() {
	bake_uv = CUSTOM0.xy;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float side = VERTEX.x >= 0.0 ? 1.0 : -1.0;
	motion_ops(v, n, NORMAL, side, CUSTOM0, CUSTOM1, CUSTOM2, CUSTOM3, false);
	int part = int(CUSTOM0.z + 0.5);
	float r = abs(v.x);
	if (((wing_parts >> part) & 1) != 0 && r > wing_root) {
		float sx = v.x >= 0.0 ? 1.0 : -1.0;
		float span = r - wing_root;
		float e1 = span / (wing_tip - wing_root);
		float zf = (v.z - wing_chord_from) / wing_chord_span;
		float along = 0.0;
		float up = 0.0;
		for (int i = 0; i < WING_STEPS; i++) {
			float b = wing_slope(e1 * (float(i) + 0.5) / float(WING_STEPS), zf, sx);
			along += cos(b);
			up += sin(b);
		}
		along *= span / float(WING_STEPS);
		up *= span / float(WING_STEPS);
		float b = wing_slope(e1, zf, sx);
		float cb = cos(b);
		float sb = sin(b);
		float high = v.y - wing_plane;
		v.x = sx * (wing_root + along - high * sb);
		v.y = wing_plane + up + high * cb;
		n = vec3(n.x * cb - sx * n.y * sb, sx * n.x * sb + n.y * cb, n.z);
	}
	motion_ops(v, n, NORMAL, side, CUSTOM0, CUSTOM1, CUSTOM2, CUSTOM3, true);
	VERTEX = v;
	NORMAL = normalize(n);
}

#include "res://shaders/motion/motion_paint.gdshaderinc"
