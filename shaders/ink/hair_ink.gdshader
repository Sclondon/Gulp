shader_type spatial;
// Hair as the inked prints draw it: each lock a flat shape in two tones,
// black ink in the gaps between locks and at the roots, strand lines running
// down the lock (sparse and broken in the light, packed close in the shadow),
// and the light caught in a band of white flicks lying across the lock, ragged
// at both edges, rather than a smooth sheen.
//
// Which way a lock runs comes from its texture coordinates: UV is (along the
// lock from root 0 to tip 1, round it 0..1), as GameCommon's models give it
// (build_character.py) and HairShape's locks do; UV2, where the model has it,
// is the same in metres, which keeps the strand lines the same width on a
// short lock and a long one (`metres`). TANGENT runs along the lock.

#include "res://shaders/ink/ink.gdshaderinc"

uniform vec3 albedo : source_color = vec3(0.13, 0.09, 0.08);
uniform vec3 ink : source_color = vec3(0.03, 0.02, 0.025);
// Dark hair is drawn lighter than it is where lit, as the prints draw black hair
// (dark brown-violet, with the ink for its shadows): how far towards pale.
uniform vec3 pale : source_color = vec3(0.62, 0.5, 0.52);
uniform float lighten = 0.22;
uniform float wrap = 0.1;
uniform float flatness = 0.65;
// UV2 is in metres (1), or only UV (0).
uniform float metres = 0.0;
// Strands: how far apart (metres with UV2, else lines round a lock), how much
// of the gap a line covers in the light and in the shadow.
uniform float strand_gap = 0.0035;
uniform float strands_round = 9.0;
uniform float lit_lines = 0.12;
uniform float shadow_lines = 0.6;
uniform float shadow_fill = 0.16;
// Ink at the roots and between the locks (where a lock turns away).
uniform float root_ink = 0.22;
uniform float gap_ink = 0.3;
// The band of flicks: colour, how strong, how tight, how ragged.
uniform vec3 flicks : source_color = vec3(0.86, 0.78, 0.7);
uniform float flick_gain = 0.55;
uniform float flick_gloss = 26.0;
uniform float flick_ragged = 0.45;
uniform float print_grain = 0.06;

varying float strand_phase;
varying float strand;
varying float along;
varying vec3 lie;

void fragment() {
	along = UV.x;
	strand_phase = metres > 0.5 ? UV2.y / strand_gap : UV.y * strands_round;
	strand = ink_hash(vec2(floor(strand_phase), 1.0));
	// Lines in the light: thin, and broken into dashes along the strand.
	float run = metres > 0.5 ? UV2.x * 55.0 : UV.x * 6.0;
	float dash = step(0.45, ink_noise(vec2(floor(strand_phase) * 3.1, run + strand * 5.0)));
	float lines = mix(1.0, hatch(strand_phase, lit_lines * (0.6 + strand)), dash);
	vec3 colour = mix(albedo, pale, lighten) * (0.92 + 0.16 * strand);
	colour = mix(colour, ink, (1.0 - lines) * 0.75);
	// (the root is inked: a jagged dark tongue up each strand)
	float root = 1.0 - smoothstep(0.0, root_ink * (0.4 + strand), UV.x);
	colour = mix(colour, ink, root * 0.85);
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	colour = mix(colour, ink, (1.0 - cut(facing, gap_ink)) * 0.9);
	ALBEDO = colour * grain(vec3(UV * 0.05, strand), print_grain);
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
	lie = TANGENT;
}

void light() {
	float reach = clamp(ATTENUATION, 0.0, 1.0);
	float facing = (dot(NORMAL, LIGHT) + wrap) / (1.0 + wrap);
	float amount = facing * smoothstep(0.15, 0.6, reach);
	float lit = cut(amount, 0.04);
	float strength = mix(reach, 1.0, flatness);
	// In the shadow the strand lines close up.
	float deep = clamp(-amount * 1.5 + 0.35, 0.0, 1.0);
	float lines = hatch(strand_phase + 0.5, deep * shadow_lines);
	float fill = LIGHT_IS_DIRECTIONAL ? shadow_fill * lines : 0.0;
	DIFFUSE_LIGHT += (lit + (1.0 - lit) * fill) * strength * LIGHT_COLOR / PI;
	// Kajiya-Kay across the lock, each strand tipped its own way, cut hard into flicks.
	vec3 tip = normalize(normalize(lie) + NORMAL * (strand - 0.5) * flick_ragged);
	float across = dot(tip, normalize(LIGHT + VIEW));
	float band = pow(sqrt(max(1.0 - across * across, 0.0)), flick_gloss);
	// (and broken along its length too: flicks, not a stripe)
	float broken = ink_noise(vec2(strand_phase * 1.7, along * 9.0 + strand * 3.0));
	float flick = cut(band * (0.55 + 0.9 * broken), 0.55) * lit;
	SPECULAR_LIGHT += flick * flick_gain * flicks * strength * LIGHT_COLOR / PI;
}
