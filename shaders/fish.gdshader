// A fish: its tail wags in a wave that runs back along it, and it bends into a turn, with a rim
// light so it stands out in dark water.
//
// Gulp: this is Salmon Run 2's shaders/fish.gdshader (as of its 37b2825) made to fit a fish of
// any length. There the wag was worked out for the salmon's own mesh (nose at -0.5, 1.8 long);
// here Fish tells it where the mesh's nose and tail are (`nose_z`, `tail_z`). The charge and
// grab poses (`curl`) and the whale's `heave` are left out; `bend` is the body bending into a turn;
// `lit` is new.
shader_type spatial;
render_mode cull_disabled, specular_disabled;

#include "res://shaders/psx_common.gdshaderinc"

uniform float wag_phase = 0.0;
uniform float wag_amp = 0.12;
uniform float bend = 0.0;
uniform float flash = 0.0;
// Where the mesh's nose and tail are along z (the nose is at -z).
uniform float nose_z = -0.5;
uniform float tail_z = 1.3;
// Gulp: how much of its own colour it shows however little light falls on it, so that a fish
// can be told from its shadow in dim water.
uniform float lit = 0.45;

void vertex() {
	float span = tail_z - nose_z;
	float t = clamp((VERTEX.z - nose_z) / span, 0.0, 1.0);
	VERTEX.x += sin(wag_phase - t * 4.5) * wag_amp * t * t * span * 0.9;
	VERTEX.x += bend * t * t * span * 0.25;
	POSITION = psx_snap(PROJECTION_MATRIX * MODELVIEW_MATRIX * vec4(VERTEX, 1.0), VIEWPORT_SIZE);
}

void fragment() {
	vec3 col = srgb_to_linear(COLOR.rgb);
	ALBEDO = col;
	ROUGHNESS = 0.7;
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	EMISSION = col * (lit + rim * 0.8) + vec3(1.0) * flash;
}
