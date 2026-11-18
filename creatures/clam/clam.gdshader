shader_type spatial;
// The clams (clam.gd): a giant clam, a scallop and a razor clam. Their colours and all their moving, in one
// shader; `kind` says which (Clam sets it, and every setting below, for its kind).
//
// What each point is comes from the model (tools/build_clam.py): UV2.y the part (0 the shell's outside, 1 its
// inside, 2 its lip, 3 a mantle, 4 a tentacle, 6 the razor clam's foot, 7 a siphon). UV2.x which way it swings
// as the shell opens (0 with the lower or right valve, 1 with the upper or left; across the giant clam's mantle,
// 0 its right edge to 1 its left). UV on the shell: x from the hinge (0) to the edge (1), y round it (0..1; the
// razor clam's: x along it from the front, y across from its hinged edge); on the giant clam's mantle: x along
// it, y across; on a scallop's mantle edge: x round it, y from its root (0) to its edge (1); on anything else x
// from its root (0) to its tip (1). COLOR.r on the giant clam's mantle: 1 its upper face.
//
// The models are built shut (the giant clam's mantle, open); `open` swings the valves about the hinge
// (`hinge_at`, `hinge_axis`; the lower or right valve by `lower_turn` radians at 1, the upper or left by
// `upper_turn`). All the moving is a function of `phase` alone, so a film of it loops exactly. Nothing here
// needs more than GL Compatibility has.
render_mode cull_back;

// Which clam: 0 the giant clam, 1 the scallop, 2 the razor clam.
uniform int kind = 0;
uniform float body_length = 1.0;
// How far through a beat (0..1, it wraps). Set by Clam.
uniform float phase = 0.0;
// How strongly it moves at all (1 as it lives, 0 still).
uniform float sway = 1.0;
// How far open its shell is (0 shut, 1 as wide as it opens).
uniform float open : hint_range(0.0, 1.0) = 0.0;
// The scallop: 0 lying still, 1 swimming, clapping its shell shut once a beat (`open` is then ignored).
uniform float swim : hint_range(0.0, 1.0) = 0.0;
// The razor clam: 0 lying on its side, 1 digging: stood up on its front end, its foot pumping down.
uniform float dig : hint_range(0.0, 1.0) = 0.0;
// The hinge: a point on it, the way it runs, and how far each valve turns about it at `open` 1.
uniform vec3 hinge_at = vec3(0.0);
uniform vec3 hinge_axis = vec3(0.0, 0.0, 1.0);
uniform float upper_turn = -0.2;
uniform float lower_turn = 0.2;

// The colours (Clam sets them for each kind): the outside of the shell (its upper or left valve, and its
// lower or right one), the inside, the lip; the mantle and its markings; the foot, tentacles or siphons.
uniform vec3 shell : source_color = vec3(0.82, 0.8, 0.74);
uniform vec3 shell_lower : source_color = vec3(0.82, 0.8, 0.74);
uniform vec3 shell_dark : source_color = vec3(0.45, 0.42, 0.34);
uniform vec3 inside : source_color = vec3(0.95, 0.94, 0.9);
uniform vec3 lip : source_color = vec3(0.85, 0.8, 0.66);
uniform vec3 mantle : source_color = vec3(0.04, 0.3, 0.4);
uniform vec3 mantle_mark : source_color = vec3(0.2, 0.75, 0.8);
uniform vec3 mantle_edge : source_color = vec3(0.15, 0.35, 0.95);
uniform vec3 flesh : source_color = vec3(0.9, 0.75, 0.6);
uniform vec3 flesh_dark : source_color = vec3(0.4, 0.25, 0.15);
// How much of its colour shows without any light on it (the giant clam's mantle glows a little).
uniform float vivid = 0.05;

// The razor clam's size and its foot's root (kept in step with the build script).
const float RAZOR_HALF = 0.075;
const float RAZOR_FOOT = -0.061;

varying vec3 rest;
varying float part;
varying float mark;

// Turns p (and n) about the line through `at` along `axis` (a unit vector) by `a` radians.
void turn_about(inout vec3 p, inout vec3 n, vec3 at, vec3 axis, float a) {
	float c = cos(a);
	float s = sin(a);
	vec3 d = p - at;
	p = at + d * c + cross(axis, d) * s + axis * dot(axis, d) * (1.0 - c);
	n = n * c + cross(axis, n) * s + axis * dot(axis, n) * (1.0 - c);
}

// A scallop's clap through a beat: open, snapped shut quickly, then opening slowly again.
float clap(float p) {
	return p < 0.16 ? 1.0 - smoothstep(0.0, 0.16, p) : smoothstep(0.16, 0.92, p);
}

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	mark = COLOR.r;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	float turn = TAU * phase;
	float opened = open;
	if (kind == 1) {
		opened = mix(open, clap(phase), swim);
	}
	if (kind == 0 && p == 3) {
		// THE GIANT CLAM'S MANTLE, built as it is wide open: as the clam shuts it is drawn in narrow and
		// down, out of sight inside the shell; open, it heaves slowly.
		float m = smoothstep(0.25, 1.0, opened);
		vec3 shut = vec3(v.x * 0.15, v.y * 0.5, v.z * 0.7);
		v = mix(shut, v, m);
		v.y += m * sway * 0.008 * sin(turn - v.z * 6.0) * smoothstep(0.0, 0.3, UV.y) * smoothstep(1.0, 0.7, UV.y);
	} else {
		if (kind == 1 && p == 4) {
			// a scallop's tentacles draw in as it shuts, and wave a little
			vec3 out_way = normalize(vec3(v.x - hinge_at.x, 0.0, v.z - hinge_at.z));
			v -= out_way * UV.x * 0.0065 * (1.0 - smoothstep(0.1, 0.7, opened));
			v.y += UV.x * UV.x * 0.0012 * sway * sin(turn * 2.0 + UV.y * 6.0);
		}
		if (kind == 2 && p == 6) {
			// THE RAZOR CLAM'S FOOT: it pushes out long and thin, swells at its tip to grip, and draws back
			// (harder as it digs).
			float pump = sway * mix(0.35, 1.0, dig);
			float e = 1.0 + pump * 0.45 * sin(turn);
			float grip = pump * max(0.0, -sin(turn - 0.6)) * smoothstep(0.55, 0.95, UV.x);
			vec2 across = v.xy - vec2(0.0, hinge_at.y);
			across *= (1.0 + 0.5 * grip) / sqrt(e);
			v.xy = vec2(0.0, hinge_at.y) + across;
			v.z = RAZOR_FOOT + (v.z - RAZOR_FOOT) * e;
		}
		if (kind == 2 && p == 7) {
			v.z += sway * 0.0015 * UV.x * sin(turn + UV.y * 3.0);
		}
		float w = UV2.x;
		turn_about(v, n, hinge_at, hinge_axis, opened * mix(lower_turn, upper_turn, w));
	}
	if (kind == 2 && dig > 0.0) {
		// Digging: stood up on its front end (which goes into the sand: the game sinks it).
		vec3 at = vec3(0.0, 0.0, -RAZOR_HALF);
		turn_about(v, n, at, vec3(1.0, 0.0, 0.0), -dig * 1.25);
	}
	VERTEX = v;
	NORMAL = n;
}

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

float noise2(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash2(i), hash2(i + vec2(1.0, 0.0)), f.x), mix(hash2(i + vec2(0.0, 1.0)), hash2(i + vec2(1.0, 1.0)), f.x), f.y);
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	float u = UV.x;
	float around = UV.y;
	float upper = step(0.5, UV2.x);
	vec3 c = shell;
	float rough = 0.5;
	float spec = 0.5;
	float pearly = 0.0;
	float n1 = noise2(rest.xz / body_length * 40.0 + rest.y / body_length * 13.0);
	if (p == 0) {
		// THE OUTSIDE OF THE SHELL
		c = mix(shell_lower, shell, upper);
		if (kind == 0) {
			// greyish white, growth lines across it and fine ribs out from the hinge, older and greener near it
			// (each line fades out where it would be finer than a pixel)
			float gx = u * 34.0 + n1 * 2.0;
			float growth = 0.5 + 0.5 * sin(gx);
			c *= 1.0 - 0.1 * growth * (1.0 - smoothstep(0.3, 1.2, fwidth(gx)));
			float rx = around * TAU * 24.0;
			c *= 1.0 - 0.06 * (0.5 + 0.5 * sin(rx)) * (1.0 - smoothstep(0.3, 1.2, fwidth(rx)));
			c = mix(c, shell_dark, 0.55 * (1.0 - smoothstep(0.05, 0.45, u)) * (0.6 + 0.4 * n1));
		} else if (kind == 1) {
			// coral pink, paler bands where it grew, light on its ribs, darker between them
			float rib = 0.5 + 0.5 * cos(19.0 * (around * PI - 0.62) / (PI - 1.24) * TAU);
			float band = smoothstep(0.4, 0.6, 0.5 + 0.5 * sin(u * 26.0 + n1 * 2.0));
			c = mix(c, mix(c, vec3(1.0, 0.92, 0.88), 0.45), band * 0.6);
			c *= 0.78 + 0.32 * rib;
			c = mix(c, shell_dark, 0.35 * (1.0 - smoothstep(0.0, 0.25, u)));
		} else {
			// glossy olive brown, cut across by a slanting line from the hinge to the back of the belly,
			// below it paler and violet-grey; fine growth lines along its length
			float line = around - 0.85 * u;
			c = mix(c, shell_dark, smoothstep(-0.03, 0.03, -line));
			float lx = u * 160.0 + around * 6.0 + n1 * 2.0;
			c *= 1.0 - 0.1 * (0.5 + 0.5 * sin(lx)) * (1.0 - smoothstep(0.3, 1.2, fwidth(lx)));
			c *= 0.85 + 0.15 * smoothstep(0.0, 0.2, min(around, 1.0 - around));
			rough = 0.25;
			spec = 0.7;
		}
	} else if (p == 1) {
		// THE INSIDE: white and smooth; the scallop's pinker towards its edge, the razor clam's violet
		c = inside;
		c = mix(c, lip, 0.4 * smoothstep(0.6, 1.0, u));
		rough = 0.18;
		spec = 0.7;
		pearly = 0.3;
	} else if (p == 2) {
		c = lip;
		rough = 0.35;
	} else if (p == 3) {
		if (kind == 0) {
			// THE GIANT CLAM'S MANTLE: on top, deep blue-green with wavy streaks and spots of bright
			// turquoise, a band of blue spots along each edge, and its siphon, a dark slit with a pale lip;
			// beneath, olive brown.
			float s = UV.y;
			float t = UV.x;
			vec2 q = vec2(t * 9.0, s * 3.0);
			float streak = smoothstep(0.55, 0.75, noise2(q * vec2(1.0, 3.0) + vec2(sin(s * 12.0) * 0.6, 0.0)));
			float spots = smoothstep(0.72, 0.8, noise2(vec2(t * 60.0, s * 22.0)));
			vec3 top = mantle * (0.8 + 0.4 * noise2(q * 4.0));
			top = mix(top, mantle_mark, 0.5 * streak);
			top = mix(top, mantle_mark, 0.55 * spots);
			float edge = 1.0 - smoothstep(0.07, 0.14, min(s, 1.0 - s));
			float dots = 1.0 - smoothstep(0.25, 0.4, length(vec2(fract(t * 40.0) - 0.5, (fract(s * 18.0) - 0.5) * 0.8)));
			top = mix(top, mix(mantle * 0.6, mantle_edge, dots), edge);
			vec2 siphon = vec2((t - 0.62) * 9.0, (s - 0.5) * 22.0);
			float slit = length(siphon);
			top = mix(top, mantle * 1.6 + vec3(0.1), 1.0 - smoothstep(0.9, 1.25, slit));
			top = mix(top, vec3(0.02, 0.03, 0.04), 1.0 - smoothstep(0.55, 0.75, slit));
			c = mix(mix(flesh_dark, mantle * 0.5, 0.5), top, step(0.5, mark));
			rough = 0.4;
			spec = 0.6;
			pearly = 0.35 * step(0.5, mark);
		} else {
			// THE SCALLOP'S MANTLE EDGE: orange tan, darker at its edge, and along it a row of tiny eyes,
			// iridescent blue, each with a bright glint
			c = mix(flesh, flesh_dark, smoothstep(0.5, 1.0, UV.y));
			vec2 e = vec2((fract(UV.x * 30.0) - 0.5) * 1.0, (UV.y - 0.82) * 3.2);
			float eye = 1.0 - smoothstep(0.2, 0.27, length(e));
			c = mix(c, mantle_edge * (0.7 + 0.6 * glance), eye);
			float glint = 1.0 - smoothstep(0.03, 0.08, length(e - vec2(0.06, 0.08)));
			c = mix(c, vec3(1.0), glint * eye);
			rough = mix(0.5, 0.1, eye);
			spec = mix(0.3, 0.9, eye);
		}
	} else if (p == 4) {
		c = mix(flesh * 1.05, flesh_dark * 1.4, smoothstep(0.6, 1.0, u));
		rough = 0.5;
	} else if (p == 6) {
		// the razor clam's foot: pale tan, pinker at its tip
		c = mix(flesh, flesh * vec3(1.05, 0.85, 0.85), smoothstep(0.5, 1.0, u));
		c *= 0.92 + 0.08 * n1;
		rough = 0.45;
	} else {
		// a siphon: cream with brown rings, a dark tip
		c = mix(flesh, flesh_dark, 0.6 * step(0.5, fract(u * 4.0)) * smoothstep(0.2, 0.3, u));
		c = mix(c, flesh_dark * 0.5, smoothstep(0.85, 1.0, u));
		rough = 0.5;
	}
	// (mother-of-pearl: colours that shift as the surface turns from the eye)
	vec3 irid = 0.5 + 0.5 * cos(TAU * (glance * 1.4 + n1 * 0.4 + vec3(0.0, 0.33, 0.67)));
	c = mix(c, c * 0.7 + irid * 0.4, pearly * glance);
	ALBEDO = c;
	EMISSION = c * vivid;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
