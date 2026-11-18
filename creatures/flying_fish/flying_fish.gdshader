shader_type spatial;
// The flying fish's body, lower jaw, eyes and tail (flying_fish.gd): how they move is in
// flying_fish_motion.gdshaderinc (shared with the fins' shader); every marking is drawn here, from
// the species (the component's README names the references): no texture files. What each point
// is comes from the model (tools/build_flying_fish.py): COLOR.r the part, as a tenth (0 body,
// 1 lower jaw, 2 eye, 6 tail). On the body UV.x is how far along the fish (0 snout to 1 tail
// tip), UV.y how high (0 belly line to 1 back line), UV2.x how far round the skin from the back
// line (metres, + right, - left), UV2.y the whole way from back line to belly line; COLOR.g the
// gill cover's moving edge, COLOR.b the inside of the mouth. On the tail UV.x is along its rays
// (0 root to 1 edge), UV.y across it counted in rays. Nothing here needs more than GL
// Compatibility has.
render_mode cull_back, depth_draw_opaque;

#include "res://creatures/flying_fish/flying_fish_motion.gdshaderinc"

// The colours: the dark blue back, the bright line where it meets the silver side, the silver
// side, the white belly.
uniform vec3 back : source_color = vec3(0.03, 0.08, 0.2);
uniform vec3 back_line : source_color = vec3(0.16, 0.42, 0.78);
uniform vec3 side : source_color = vec3(0.74, 0.79, 0.85);
uniform vec3 belly : source_color = vec3(0.96, 0.97, 0.98);
uniform vec3 cheek : source_color = vec3(0.88, 0.9, 0.93);
uniform vec3 lip : source_color = vec3(0.8, 0.76, 0.76);
uniform vec3 mouth : source_color = vec3(0.8, 0.62, 0.62);
uniform vec3 tail_colour : source_color = vec3(0.1, 0.14, 0.22);
uniform vec3 eye_silver : source_color = vec3(0.82, 0.86, 0.9);
uniform vec3 sheen_colour : source_color = vec3(0.6, 0.78, 1.0);
// How high up the side the blue back begins (0 the belly line, 1 the back line), how strong the
// bright line along its lower edge is, and how strong the sheen and the scales are.
uniform float back_from = 0.6;
uniform float line_amount = 0.55;
uniform float sheen = 0.4;
uniform float scales = 1.0;
// How big a scale is (metres): a flying fish's are large.
uniform float scale_size = 0.0042;

varying vec3 rest;
varying float part;
varying vec2 extra;


vec4 hash4(vec2 p) {
	vec4 q = fract(p.xyxy * vec4(0.1031, 0.1030, 0.0973, 0.1099));
	q += dot(q, q.wzxy + 33.33);
	return fract((q.xxyz + q.yzzw) * q.zywx);
}


// Soft patches, 0..1, a patch to each 1 of `p`: the skin is not one flat colour.
float cloud(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash4(i).x, hash4(i + vec2(1.0, 0.0)).x, f.x), mix(hash4(i + vec2(0.0, 1.0)).x, hash4(i + vec2(1.0, 1.0)).x, f.x), f.y);
}


void vertex() {
	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	fish_move(v, n, part, UV, COLOR);
	VERTEX = v;
	NORMAL = n;
}


// The colour of the body's skin at a place: `h` up it (0 belly line to 1 back line). Dark blue
// above and silver-white below, as fish of the open sea are, with a bright blue line between.
vec3 skin(float h) {
	vec3 c = mix(belly, side, smoothstep(0.03, 0.3, h));
	c = mix(c, back_line, line_amount * exp(-pow((h - back_from + 0.035) / 0.04, 2.0)));
	c = mix(c, back, smoothstep(back_from - 0.03, back_from + 0.06, h));
	return c;
}


void fragment() {
	vec3 c = side;
	float rough = 0.3;
	float glint = sheen;
	float seen = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	if (part < 0.5) {
		float s = UV.x;
		float h = UV.y;
		float girth = max(UV2.y, 0.001);
		float round_it = abs(UV2.x) / girth;
		vec2 p = vec2(rest.z, UV2.x);
		c = skin(h);
		// The head: dark on top, the cheek and gill cover bright silver, pale round the mouth; the
		// gill cover's edge a dark crescent, and the line of the cheek plate ahead of it.
		float edge = gill_edge(h);
		float head = 1.0 - smoothstep(edge - 0.01, edge + 0.004, s);
		float plate = head * smoothstep(0.08, 0.2, h) * (1.0 - smoothstep(back_from - 0.1, back_from + 0.02, h));
		c = mix(c, cheek, 0.85 * plate);
		c *= 1.0 - 0.45 * exp(-pow((s - edge - 0.002) / 0.0028, 2.0)) * smoothstep(0.08, 0.2, h) * (1.0 - smoothstep(0.74, 0.88, h));
		c *= 1.0 - 0.16 * exp(-pow((s - edge + 0.05 + 0.03 * (h - 0.45)) / 0.0026, 2.0)) * smoothstep(0.14, 0.24, h) * (1.0 - smoothstep(0.5, 0.62, h));
		// (the snout and the upper lip: dusky above, pale along the lip)
		float snout = 1.0 - smoothstep(0.02, 0.06, s);
		c = mix(c, lip, snout * (1.0 - smoothstep(0.1, 0.4, h)));
		c = mix(c, mix(back, side, 0.35), 0.6 * snout * smoothstep(0.45, 0.8, h));
		// The lateral line, which in a flying fish runs low, along the edge of the belly.
		float along_body = smoothstep(0.2, 0.25, s) * (1.0 - smoothstep(0.7, 0.76, s));
		c *= 1.0 - 0.1 * along_body * (1.0 - smoothstep(0.006, 0.014, abs(h - 0.13)));
		// The scales: large, in rows, each a crescent (its free rear edge) and none quite the same
		// silver as the next.
		vec2 sc = p / scale_size;
		sc.x += 0.5 * mod(floor(sc.y), 2.0);
		vec2 in_scale = fract(sc) - 0.5;
		float scale_edge = smoothstep(0.28, 0.5, length(in_scale)) * smoothstep(-0.25, 0.25, in_scale.x);
		float fine = 1.0 - smoothstep(0.25, 0.7, fwidth(sc.x) + fwidth(sc.y));
		float scaled = scales * (1.0 - head) * (1.0 - smoothstep(0.86, 0.97, round_it)) * fine * (1.0 - smoothstep(0.75, 0.775, s));
		c *= 1.0 - 0.1 * scale_edge * scaled;
		c *= 1.0 + 0.1 * (hash4(floor(sc)).x - 0.5) * scaled;
		rough += 0.1 * scale_edge * scaled;
		// (mottled a little, in big soft patches)
		c *= mix(1.0, 0.94 + 0.1 * cloud(p / 0.025), 1.0 - smoothstep(0.8, 0.95, round_it));
		// (where the skin runs out over the root of the tail it takes the tail's colour, as the tail does there)
		c = mix(c, tail_colour, smoothstep(0.765, 0.8, s));
		// The inside of the mouth.
		c = mix(c, mouth, extra.y);
		glint *= smoothstep(0.05, 0.25, h) * (1.0 - extra.y);
	} else if (part < 1.5) {
		// The lower jaw: pale, a little darker along the lip.
		float h = UV.y;
		c = mix(belly, lip, smoothstep(0.3, 0.85, h));
		c = mix(c, mix(side, back, 0.3), 0.5 * smoothstep(0.82, 0.98, h));
		c = mix(c, mouth, extra.y);
		glint *= 0.3;
	} else if (part < 2.5) {
		// An eye: very large, a wide black pupil in a silver ring, dusky above and dark at the rim.
		vec2 on_eye = UV * 2.0 - 1.0;
		float r = length(on_eye);
		float above = smoothstep(-0.2, 0.9, on_eye.x / max(r, 0.001));
		c = mix(eye_silver, mix(back, eye_silver, 0.3), 0.75 * above * smoothstep(0.5, 0.75, r));
		c = mix(c, vec3(0.03, 0.04, 0.06), smoothstep(0.84, 0.96, r));
		c = mix(c, vec3(0.01), 1.0 - smoothstep(0.5, 0.54, r));
		rough = 0.06;
		glint = 0.0;
	} else {
		// The tail: dusky, the body's colours running out over its root, its rays as fine lines
		// that fork towards the edge.
		float r = UV.x;
		float ty = UV.y;
		float t = ty / 22.0;
		float between = abs(fract(ty) - 0.5) * 2.0;
		float between_fine = abs(fract(ty * 2.0) - 0.5) * 2.0;
		float lines = mix(smoothstep(0.55, 1.0, between), smoothstep(0.5, 1.0, between_fine), smoothstep(0.45, 0.7, r));
		lines *= smoothstep(0.12, 0.4, r);
		c = mix(skin(1.0 - t), tail_colour, smoothstep(0.02, 0.22, r));
		// (paler and greyer between the rays towards the fork, darkest along the two lobes)
		c = mix(c, mix(tail_colour, side, 0.45), 0.5 * (1.0 - smoothstep(0.1, 0.7, abs(t * 2.0 - 1.0))) * smoothstep(0.2, 0.6, r));
		c *= 1.0 - 0.3 * lines;
		rough = 0.42;
		glint *= 0.35;
	}
	// The sheen: the skin's cold silver-blue shine where it is seen aslant.
	c += sheen_colour * glint * pow(1.0 - seen, 3.0);
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.5;
}
