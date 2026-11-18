shader_type spatial;
// A colony of garden eels (garden_eel_colony.gd): every eel one instance of one MultiMesh of the
// light colony model (about 230 triangles). Each instance's custom data: r how much of it is out of
// its burrow (0..1), g its own phase offset (0..1), b how far its top is curled (times `hook`),
// a how much it sways (times `sway`). The pose and the colours are in garden_eel.gdshaderinc, shared
// with the single eel's shader; the eye is drawn on the skin.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

#include "res://creatures/garden_eel/garden_eel.gdshaderinc"

// How far through a beat the colony's clock is (0..1, it wraps). Set by GardenEelColony.
uniform float phase = 0.0;
uniform float sway = 1.0;
uniform float hook = 2.0;
uniform float lean = 0.12;

varying vec3 rest;

void vertex() {
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	vec4 own = INSTANCE_CUSTOM;
	eel_pose(v, n, own.r, TAU * fract(phase + own.g), sway * own.a, hook * own.b, lean);
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	vec3 c = eel_colour(rest, 0.0, UV, true);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	ALBEDO = c * (1.0 + 0.25 * glance * glance);
	ROUGHNESS = 0.45;
	SPECULAR = 0.4;
}
