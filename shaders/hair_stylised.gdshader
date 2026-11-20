shader_type spatial;
render_mode vertex_lighting, cull_disabled;
// Stylised hair drawn on plain carriers (tools/figed/hair.py makes them by rule; tools/figed/README.md, "Hair as
// locks", is the record and lists what to change for a new style). Painterly, not strands: each carrier strip is cut
// to one lock's outline (a tapered, hooked, forked tip), shaded round, with a few soft strand streaks and a light
// laid across it where it faces the sky. The same shader draws the dark cap under the locks and a moustache's full
// shape (`lock_shape` 0: no outline is cut).
//
// What the carriers give it:
//   UV    = (along the lock, 0 root .. 1 tip; across it, 0 .. 1)
//   UV2   = (metres along; a number 0..1 of the lock's own, the same all over it)
//   COLOR = rgb: the sideways direction across the lock (0.5 + 0.5 * unit vector, model space); a: how far out the
//           lock lies among its neighbours (0 deepest, 1 outermost)
// Cost: no textures, no loops; a dozen hashes a pixel. Everything painted depends only on UV, UV2.y and three
// colours, so it can be baked to one small picture of a few locks if a web build needs it cheaper still.

#include "res://shaders/ink/ink.gdshaderinc"

group_uniforms colours;
uniform vec3 base : source_color = vec3(0.36, 0.2, 0.13);
// the dark between and under locks, and at their roots
uniform vec3 deep : source_color = vec3(0.17, 0.085, 0.06);
// the painted light across a lock
uniform vec3 light : source_color = vec3(0.62, 0.38, 0.22);
// each lock a little lighter or darker than its neighbours
uniform float vary = 0.12;
// deeper locks darker (COLOR.a)
uniform float depth_shade = 0.25;
// darker toward the root, over this share of the length
uniform float root_dark = 0.5;
uniform float root_reach = 0.4;
// darker where the hair faces the ground
uniform float under_shade = 0.35;
// the underside of a carrier (its back face) darker: the shadowed inside of a lifted lock
uniform float back_dark = 0.5;

group_uniforms outline;
// 1: cut each strip to a lock's outline. 0: a plain surface (a cap, a moustache's body)
uniform float lock_shape = 1.0;
// the share of the length over which the lock narrows to its point, and how round that narrowing is
uniform float taper = 0.45;
uniform float taper_round = 1.6;
// the tip leans to one edge of the strip (a comma), 0..1; which edge: each lock its own (0), all to UV.y 1 (1) or
// all to UV.y 0 (-1)
uniform float hook = 0.7;
uniform float hook_way = 0.0;
// the tip forks into two points, 0..1
uniform float fork = 0.5;
// the lock's edges waver (a share of its width) this many times along it
uniform float waver = 0.08;
uniform float waver_count = 2.5;
// the root starts narrower, over this share of the length
uniform float root_narrow = 0.15;
// a plain surface's far edge (UV.x near 1) broken into points this share back, this many points across (0 off)
uniform float edge_points = 0.0;
uniform float edge_point_count = 6.0;

group_uniforms stubble;
// stubble on a plain surface lying on the skin (0 off): only short strokes of it are drawn, more of them the higher
// this is and the higher UV.x is there (how thick it grows); UV2 is metres over the skin. stubble_size: metres
// between hairs; stubble_length: a hair's length as a share of that; stubble_lean: how far the hairs lean sideways
uniform float stubble = 0.0;
uniform float stubble_size = 0.0022;
uniform float stubble_length = 0.55;
uniform float stubble_lean = 0.2;
// a hair's width as a share of the gap between hairs
uniform float stubble_width = 0.14;

group_uniforms ribbons;
// a carrier is drawn as this many ribbons of hair side by side (1: the carrier is one lock)
uniform float ribbons = 1.0;
// the ribbons wave across the carrier as they run: how far (a share of its half width), how many waves
uniform float ribbon_wave = 0.0;
uniform float ribbon_waves = 1.0;
// each ribbon ends in a point of its own, up to this share of the length before the carrier's end (0: none), each
// point this share long
uniform float ribbon_tips = 0.0;
uniform float ribbon_taper = 0.25;
// each ribbon a little lighter or darker than the next
uniform float ribbon_vary = 0.0;

group_uniforms paint;
// the dark line of the crease between ribbons and along the carrier's edges: how dark, how wide (a share of half a
// ribbon), and how deep the shadow is on a ribbon's lower side, under its neighbour
uniform float edge_dark = 0.75;
uniform float edge_width = 0.3;
uniform float under_edge = 0.6;
// soft strand streaks: how many across a lock, how strong, and how long they run (smaller: longer)
uniform float strands = 4.0;
uniform float strand_depth = 0.3;
uniform float strand_run = 1.6;
// the light: how strong, where along the lock (0..1), how long, how streaky; repeated every `shine_every` metres if
// that is over 0 (once on each wave of a long lock)
// a lock lighter down its middle than at its edges (a ribbon's ridge), where it faces up
uniform float ridge = 0.35;
uniform float shine = 0.7;
uniform float shine_at = 0.42;
uniform float shine_length = 0.2;
uniform float shine_streaks = 0.6;
uniform float shine_every = 0.0;
// the light only where the hair faces up (1) or everywhere (0)
uniform float shine_up = 0.7;

group_uniforms motion;
// moved in the vertex stage (metres): each lock waved sideways along its length, lifted off the head over its
// middle, its tip flicked out; `sway` rocks the wave in time (wind, a bounce), 0 still
uniform float wave = 0.0;
uniform float wave_length = 0.07;
uniform float lift = 0.0;
uniform float flick = 0.0;
uniform float sway = 0.0;
uniform float sway_speed = 2.0;

varying float number;
varying float depth;
varying float up;

void vertex() {
	number = UV2.y;
	depth = COLOR.a;
	float t = UV.x;
	if (wave != 0.0 || lift != 0.0 || flick != 0.0) {
		vec3 side = COLOR.rgb * 2.0 - 1.0;
		float hold = smoothstep(0.0, 0.3, t);
		float swing = sin(UV2.x / max(wave_length, 0.001) * 6.2832 + number * 6.2832 + sway * sin(TIME * sway_speed + number * 6.2832));
		VERTEX += side * wave * swing * hold + NORMAL * (lift * sin(3.1416 * t) + flick * t * t * t);
	}
	up = (MODEL_MATRIX * vec4(NORMAL, 0.0)).y;
}

void fragment() {
	float t = UV.x;
	float v = UV.y - 0.5;
	float n1 = ink_hash(vec2(number * 91.7, 3.1));
	float n2 = ink_hash(vec2(number * 57.3, 8.6));
	float n3 = ink_hash(vec2(number * 23.9, 5.2));
	float x = v * 2.0;
	if (stubble > 0.0) {
		// one hair to a cell of a grid over the skin, each placed and sized its own way; fewer where it grows thin
		vec2 at = UV2 / stubble_size;
		at.x += 0.5 * floor(at.y);
		vec2 cell = floor(at);
		float pick = ink_hash(cell + 3.3);
		vec2 in_cell = fract(at) - 0.5 - (ink_hash22(cell) - 0.5) * 0.4;
		float along_hair = in_cell.y / max(stubble_length, 0.01);
		float across_hair = in_cell.x - stubble_lean * sign(UV2.x) * in_cell.y;
		// (never thinner than a pixel, or far off it would flicker away)
		float wide = max(stubble_width * (1.0 - along_hair * along_hair * 4.0), fwidth(at.x) * 0.5);
		if (pick > stubble * t || abs(along_hair) > 0.5 || abs(across_hair) > wide) {
			discard;
		}
	}
	float way = hook_way != 0.0 ? sign(hook_way) : (n1 > 0.5 ? 1.0 : -1.0);
	if (lock_shape > 0.5) {
		float k = clamp((t - (1.0 - taper)) / max(taper, 0.001), 0.0, 1.0);
		float half_w = 0.5 * (1.0 - pow(k, taper_round)) * mix(1.0 - 0.45 * step(0.001, root_narrow), 1.0, smoothstep(0.0, max(root_narrow, 0.001), t));
		float mid = way * hook * 0.5 * pow(k, taper_round);
		mid += waver * sin(t * waver_count * 6.2832 + n2 * 6.2832) * (1.0 - k);
		half_w *= 1.0 - waver * (0.5 + 0.5 * sin(t * waver_count * 4.1 + n3 * 6.2832));
		float off = v - mid;
		if (abs(off) > half_w) {
			discard;
		}
		x = off / max(half_w, 0.0001);
		// the fork: a notch opening from part way down the taper, to the side away from the hook
		if (fork > 0.0 && n3 < fork) {
			float open = clamp((k - 0.15 - 0.3 * n2) / 0.5, 0.0, 1.0);
			float notch_at = -way * (0.15 + 0.3 * n2);
			if (open > 0.0 && abs(x - notch_at) < open * 0.34) {
				discard;
			}
		}
	} else if (edge_points > 0.0) {
		float cell = UV.y * edge_point_count + 0.3 * sin(t * 9.0);
		float ends = 1.0 - edge_points * ink_hash(vec2(floor(cell), 4.4));
		float in_k = clamp((t - (ends - edge_points)) / edge_points, 0.0, 1.0);
		if (t > ends || abs(fract(cell) - 0.5) * 2.0 > 1.0 - in_k) {
			discard;
		}
	}
	// the ribbons a carrier is drawn as: side by side, waving together along it, each ending in a point of its own
	// (the creases wave, the carrier's own edges do not; a count like 2.5 gives half the carriers two, half three)
	float count = max(1.0, floor(ribbons + n3));
	float rx = (clamp(x + ribbon_wave * sin(t * ribbon_waves * 6.2832 + n2 * 6.2832) * (1.0 - x * x), -0.999, 0.999) * 0.5 + 0.5) * count;
	float ribbon = floor(rx);
	float r1 = ink_hash(vec2(ribbon * 3.7 + 1.3, number * 131.0));
	float fx = fract(rx) * 2.0 - 1.0;
	if (ribbon_tips > 0.0) {
		float ends = 1.0 - ribbon_tips * r1;
		float kk = clamp((t - (ends - ribbon_taper)) / max(ribbon_taper, 0.001), 0.0, 1.0);
		float open = 1.0 - kk * kk;
		// (the point leans to the ribbon's upper side, as the lock's own does)
		float lean = fx - way * 0.6 * kk * kk;
		if (t > ends || abs(lean) > open) {
			discard;
		}
		fx = lean / max(open, 0.001);
	}
	vec3 colour = base * (1.0 + vary * (n2 - 0.5) * 2.0) * (1.0 + ribbon_vary * (r1 - 0.5) * 2.0);
	// strand streaks along the ribbon
	float streak = ink_noise(vec2(fx * strands + r1 * 37.0 + number * 37.0, t * strand_run + n1 * 9.0));
	float fine = ink_noise(vec2(fx * strands * 2.7 + number * 11.0, t * strand_run * 2.0 + n3 * 5.0));
	colour *= 1.0 + strand_depth * ((streak * 0.7 + fine * 0.3) - 0.5) * 2.0;
	// the painted light, on streaks, where the hair faces the sky
	float faces_up = mix(1.0, smoothstep(-0.2, 0.7, up), shine_up);
	// each ribbon lies over the next: light on its upper side, falling to shadow under the one above it
	float under = fx * way;
	float mid_x = 1.0 - smoothstep(0.0, 1.2, abs(under + 0.3));
	colour = mix(colour, light, ridge * mid_x * faces_up);
	float along_light = shine_every > 0.0 ? fract(UV2.x / shine_every + n3 + r1 * 0.3) : t;
	float where_light = shine_every > 0.0 ? 0.5 : shine_at + (n2 - 0.5) * 0.2;
	float band = (along_light - where_light) / max(shine_length, 0.001);
	band = exp(-band * band);
	float streaky = mix(1.0, smoothstep(0.3, 0.7, ink_noise(vec2(fx * strands * 1.6 + number * 71.0, t * strand_run * 0.7))), shine_streaks);
	float lit = shine * band * streaky * faces_up * mid_x;
	colour = mix(colour, light, clamp(lit, 0.0, 1.0));
	// the shadow under the ribbon above, and the dark line of the crease between two
	colour = mix(colour, deep, under_edge * smoothstep(0.1, 1.0, under) * 0.8);
	float crease = smoothstep(1.0 - edge_width, 1.0, abs(fx));
	colour = mix(colour, deep, edge_dark * crease);
	if (lock_shape > 0.5) {
		// and the carrier's own edges
		float rim = smoothstep(1.0 - edge_width / count, 1.0, abs(x));
		colour = mix(colour, deep, edge_dark * rim);
	}
	colour = mix(colour, deep, root_dark * (1.0 - smoothstep(0.0, max(root_reach, 0.001), t)));
	colour = mix(colour, deep, depth_shade * (1.0 - depth));
	colour = mix(colour, deep, FRONT_FACING ? 0.0 : back_dark);
	colour *= mix(1.0, 0.45 + 0.55 * smoothstep(-0.8, 0.3, up), under_shade);
	ALBEDO = colour;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}
