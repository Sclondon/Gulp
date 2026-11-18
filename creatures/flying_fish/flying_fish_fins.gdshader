shader_type spatial;
// The flying fish's see-through fins (flying_fish.gd): the wings (the pectoral and pelvic fins)
// and the dorsal and anal fins, a thin film between darker rays. How they move is in
// flying_fish_motion.gdshaderinc (shared with the body's shader). What each point is comes from
// the model (tools/build_flying_fish.py): COLOR.r the part, as a tenth (4 dorsal, 7 anal,
// 8 pelvic, 9 pectoral); UV.x along its rays (0 root to 1 edge), UV.y across it counted in rays
// (0 its leading ray).
//
// See-through, and it writes its depth as it is drawn: what is behind a fin shows through it
// (the body, the water, the floor), except another of the fish's own fins drawn after it, which
// is hidden there instead of painted over the nearer one. See the README's decision.
render_mode blend_mix, cull_back, depth_draw_always;

#include "res://creatures/flying_fish/flying_fish_motion.gdshaderinc"

// The rays; the film of the wings (the pectoral fins), dusky blue-grey with a paler band across
// it and a pale trailing edge; the film of the pelvic fins, nearly clear; of the dorsal and of the
// anal fin.
uniform vec3 ray : source_color = vec3(0.05, 0.07, 0.12);
uniform vec3 ray_pale : source_color = vec3(0.72, 0.78, 0.86);
uniform vec3 wing : source_color = vec3(0.13, 0.2, 0.34);
uniform vec3 wing_band : source_color = vec3(0.62, 0.74, 0.88);
uniform vec3 pelvic : source_color = vec3(0.86, 0.9, 0.95);
uniform vec3 dorsal : source_color = vec3(0.16, 0.22, 0.32);
uniform vec3 anal : source_color = vec3(0.9, 0.93, 0.96);
// How much of what is behind each film is hidden (0 clear glass, 1 solid), and the rays.
uniform float wing_alpha : hint_range(0.0, 1.0) = 0.55;
uniform float pelvic_alpha : hint_range(0.0, 1.0) = 0.38;
uniform float dorsal_alpha : hint_range(0.0, 1.0) = 0.5;
uniform float anal_alpha : hint_range(0.0, 1.0) = 0.3;
uniform float ray_alpha : hint_range(0.0, 1.0) = 0.95;
uniform float folded_alpha : hint_range(0.0, 1.0) = 0.88;
// How strong the pale band across the wing is.
uniform float band_amount : hint_range(0.0, 1.0) = 0.6;

varying float part;


void vertex() {
	part = floor(COLOR.r * 10.0 + 0.5);
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	fish_move(v, n, part, UV, COLOR);
	VERTEX = v;
	NORMAL = n;
}


void fragment() {
	// A fin: its rays as lines that fork towards the edge (a wing's first ray does not).
	float r = UV.x;
	float ty = UV.y;
	float between = abs(fract(ty) - 0.5) * 2.0;
	float between_fine = abs(fract(ty * 2.0) - 0.5) * 2.0;
	float forked = smoothstep(0.5, 0.72, r) * smoothstep(0.9, 1.4, ty);
	float lines = mix(smoothstep(0.6, 0.96, between), smoothstep(0.55, 0.96, between_fine), forked);
	// (none at the very root)
	lines *= smoothstep(0.02, 0.1, r);
	// (where the rays are too close to be told apart, folded or seen aslant, they are an even dusk)
	lines = mix(lines, 0.4, smoothstep(0.3, 0.8, fwidth(ty) * (1.0 + forked)));
	vec3 film = wing;
	vec3 line_colour = ray;
	float alpha = wing_alpha;
	if (part > 8.5) {
		float t = ty / 15.0;
		// The pale band: across the middle of the wing, from behind the leading rays to the trailing edge.
		float band = exp(-pow((r - 0.5 - 0.12 * t) / 0.13, 2.0)) * smoothstep(0.12, 0.4, t);
		film = mix(wing, wing_band, band_amount * band);
		alpha = mix(wing_alpha, wing_alpha * 0.7, band_amount * band);
		// (a pale clear margin along the trailing edge, and a pale leading ray)
		float margin = smoothstep(0.93, 1.0, r);
		film = mix(film, wing_band, 0.7 * margin);
		line_colour = mix(ray, ray_pale, 1.0 - smoothstep(0.3, 0.9, ty));
		// (darker and denser at the root)
		alpha = mix(alpha, 0.9, 1.0 - smoothstep(0.0, 0.14, r));
	} else if (part > 7.5) {
		film = pelvic;
		alpha = pelvic_alpha;
		line_colour = mix(ray_pale, ray, 0.25);
	} else if (part > 5.5) {
		film = anal;
		alpha = anal_alpha;
		line_colour = mix(ray_pale, ray, 0.3);
	} else {
		film = mix(dorsal, dorsal * 1.6, smoothstep(0.5, 1.0, r));
		alpha = dorsal_alpha;
	}
	// (a folded wing is its whole film laid many times over itself: nearly solid)
	if (part > 7.5) {
		float shut = 1.0 - clamp(wings, 0.0, 1.0);
		alpha = mix(alpha, max(alpha, folded_alpha), shut * shut);
	}
	ALBEDO = mix(film, line_colour, lines);
	ALPHA = mix(alpha, max(alpha, ray_alpha), lines);
	ROUGHNESS = 0.35;
	SPECULAR = 0.25;
	// (light from behind a fin shows through it)
	BACKLIGHT = vec3(0.45);
}
