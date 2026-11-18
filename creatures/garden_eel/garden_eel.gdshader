shader_type spatial;
// One garden eel (garden_eel.gd): its pose out of its burrow, its swaying and its colours. The pose
// and the colours are in garden_eel.gdshaderinc, shared with the colony's shader. All of its motion
// is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

#include "res://creatures/garden_eel/garden_eel.gdshaderinc"

// How far through a beat (0..1, it wraps). Set by GardenEel.
uniform float phase = 0.0;
// How much of it is out of its burrow: 0 all in, 1 all out (0.3 m of it stands up at scale 1).
uniform float out_of_sand : hint_range(0.0, 1.0) = 1.0;
// How strongly it sways (1 as it lives, 0 still).
uniform float sway = 1.0;
// Radians its top is curled over (2.0: its head a little below level, facing -Z), and its stalk leans back.
uniform float hook = 2.0;
uniform float lean = 0.12;

varying vec3 rest;
varying float part;

void vertex() {
	rest = VERTEX;
	part = UV2.y;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	eel_pose(v, n, out_of_sand, TAU * phase, sway, hook, lean);
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	vec3 c = eel_colour(rest, part, UV, false);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	ALBEDO = c * (1.0 + 0.25 * glance * glance);
	ROUGHNESS = part > 0.5 && part < 1.5 ? 0.15 : 0.45;
	SPECULAR = part > 0.5 && part < 1.5 ? 0.8 : 0.4;
}
