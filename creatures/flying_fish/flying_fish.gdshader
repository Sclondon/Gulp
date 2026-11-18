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

// Cartoon eyes (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0, the default, is the eye drawn below, as it always was; 1 is the cartoon eye:
// grown about the middle of its face, a pale white, a coloured iris, a big dark pupil, a highlight
// that stays put (up and forward, towards the light) and a dark rim. The flying fish's: a wide,
// startled, always-about-to-take-off stare, no lid, a huge pupil in a pale sky-blue iris.
uniform float cartoon_eyes = 0.0;
// Where the pupil looks, in the eye's own plane: x forward (towards the snout; -1 back towards the
// tail), y up; -1..1. Only the cartoon eye's pupil moves.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat from above and below and a lid of `lid_colour` closes over it.
uniform float blink = 0.0;
// The right eye's middle on the skin and the way it faces (metres, as the model is built: the build
// script prints them; the left eye is its mirror).
uniform vec3 eye_at = vec3(0.0126, 0.0033, -0.1275);
uniform vec3 eye_out = vec3(0.9816, 0.0554, -0.1829);
// How much bigger the cartoon eye is drawn, and how fast the head's skin falls away round it (1 / (2 x
// its radius there), per metre); its white, its iris (how wide, of the eye's face to its rim), its
// pupil (how wide, of the iris; 0 round, 1 an upright slit, 2 a level bar, 3 a keyhole), where the
// upper lid's edge rests (1 the top of the eye, no lid; 0 its middle) and how much lower it comes at
// the front (a frown).
uniform float eye_grow = 1.3;
// (eye_sink: 0, not sunk, looked cleanest on all of them: sunk, the rim dipped under the skin and came
// out again below the eye as a dark crescent)
uniform float eye_sink = 0.0;
uniform vec3 eye_white : source_color = vec3(0.98, 0.98, 0.97);
uniform vec3 iris : source_color = vec3(0.55, 0.78, 0.95);
uniform float iris_size = 0.5;
uniform float pupil_size = 0.7;
uniform int pupil_shape = 0;
uniform float lid = 1.0;
uniform float lid_slant = 0.0;
uniform vec3 lid_colour : source_color = vec3(0.6, 0.66, 0.74);

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


// The cartoon eye's dome grown about the middle of its face, and squashed from above and below as
// it blinks (nothing moves while cartoon_eyes and blink are 0).
void eye_shape(inout vec3 v) {
	if (cartoon_eyes <= 0.0 && blink <= 0.0) {
		return;
	}
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	vec3 at = vec3(eye_at.x * side_is, eye_at.yz);
	vec3 o = normalize(vec3(eye_out.x * side_is, eye_out.yz));
	vec3 up = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
	vec3 d = v - at;
	float grow = mix(1.0, eye_grow, cartoon_eyes);
	float before = dot(d - o * dot(d, o), d - o * dot(d, o));
	// (grown across, and outward; what lies behind its face, deep in the head, is not pushed further in,
	// or it would come out through the other side of a narrow head)
	float deep = min(dot(d, o), 0.0);
	d = (d - o * deep) * grow + o * deep;
	// (sunk as the head's skin falls away round it, so that the grown rim stays in the skin)
	d -= o * eye_sink * before * (grow * grow - 1.0);
	d -= up * dot(d, up) * 0.8 * blink;
	v = at + d;
}


// The cartoon eye's colour at a place on its face: `e` x up, y forward, 1 at its rim.
vec3 cartoon_eye(vec2 e) {
	float r = length(e);
	vec2 q = e - vec2(eye_look.y, eye_look.x) * (0.9 - iris_size);
	float ri = length(q) / iris_size;
	float aa = fwidth(ri) + 0.01;
	vec3 c = eye_white * mix(1.0, 0.82, smoothstep(0.4, 1.0, r));
	vec3 ring = mix(iris * 1.2, iris * 0.6, smoothstep(0.25, 0.95, ri));
	ring = mix(ring, iris * 0.25, smoothstep(0.82, 1.0, ri));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ri));
	vec2 p = q / (iris_size * pupil_size);
	float pd = length(p);
	if (pupil_shape == 1) {
		pd = length(vec2(p.x * 0.6, p.y * 2.4));
	} else if (pupil_shape == 2) {
		pd = length(vec2(p.x * 2.4, p.y * 0.6));
	} else if (pupil_shape == 3) {
		pd = min(length(p - vec2(0.22, 0.0)) * 1.15, length(vec2((p.x + 0.35) * 0.75, p.y * 2.8)));
	}
	float pa = fwidth(pd) + 0.02;
	c = mix(c, vec3(0.015), 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	float shine = 1.0 - smoothstep(0.17, 0.21, length(e - vec2(0.36, 0.3)));
	shine = max(shine, 0.85 * (1.0 - smoothstep(0.07, 0.1, length(e - vec2(-0.22, -0.3)))));
	c = mix(c, vec3(1.0), shine);
	return mix(c, vec3(0.02), smoothstep(0.83, 0.9, r));
}


void vertex() {
	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part == 2.0) {
		eye_shape(v);
	}
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
		if (cartoon_eyes > 0.0) {
			c = mix(c, cartoon_eye(on_eye), cartoon_eyes);
		}
		// (past its rim, where the grown dome runs back into the head and a sliver may show below it: the skin's colour, not the dark rim)
		c = mix(c, lid_colour, cartoon_eyes * smoothstep(0.95, 1.0, length(on_eye)));
		// (the upper lid: none on the eye as it was, until it blinks)
		float lid_edge = mix(mix(1.3, lid, cartoon_eyes) - lid_slant * cartoon_eyes * on_eye.y, -1.3, blink);
		c = mix(c, vec3(0.02), smoothstep(lid_edge - 0.16, lid_edge - 0.06, on_eye.x) * step(lid_edge, 1.2));
		c = mix(c, lid_colour, smoothstep(lid_edge - 0.05, lid_edge, on_eye.x));
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
