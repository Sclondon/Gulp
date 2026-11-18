shader_type spatial;
// The oysters (oyster.gd): one Pacific oyster, or a clump of five grown together. Their colours and their
// opening, in one shader; Oyster sets every setting below for the model it shows.
//
// What each point is comes from the model (tools/build_oyster.py): UV2.y the part (0 the shell's outside, 1 its
// inside, 2 its lip, 3 the soft body, 4 the pearl); UV2.x which oyster of the clump it belongs to and which way it
// swings, 2 x (its number) + 1 for the upper valve. UV on the shell: x from the hinge (0) to the edge (1), y round
// it; on the body: x from its middle (0) to its edge (1).
//
// The models are built shut; `open` swings each upper valve up about its hinge (`hinge_at[i]`, `hinge_axis[i]`)
// by `upper_turn` radians at 1 (in a clump each by its own share, `opens[i]`). The body breathes a little on
// `phase`. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// How far open (0 shut, 1 as far as it opens: a little).
uniform float open : hint_range(0.0, 1.0) = 0.0;
// 1 shows the pearl lying on the body (seen when it is open), 0 hides it.
uniform float pearl : hint_range(0.0, 1.0) = 0.0;
// How far through a beat (0..1) and how strongly it moves (the body's slow breathing).
uniform float phase = 0.0;
uniform float sway = 1.0;
// Each oyster's hinge: a point on it and the way it runs; how far its upper valve turns at `open` 1 (radians),
// and each oyster's share of that (so that the five of a clump do not open alike).
uniform vec3 hinge_at[5];
uniform vec3 hinge_axis[5];
uniform float opens[5];
uniform float upper_turn = 0.16;
// Where the pearl's middle is (it is drawn shrunk to that point when hidden).
uniform vec3 pearl_at = vec3(0.0);
// How big the oyster is (metres): for the scale of its markings.
uniform float size = 0.16;

// The colours: the rough outside (grey, with brown and violet in its layers), the lip, the mother-of-pearl
// inside and its dark violet muscle scar, the body and its dark mantle edge, the pearl.
uniform vec3 shell : source_color = vec3(0.58, 0.56, 0.52);
uniform vec3 shell_dark : source_color = vec3(0.32, 0.27, 0.26);
uniform vec3 shell_tint : source_color = vec3(0.45, 0.36, 0.42);
uniform vec3 lip : source_color = vec3(0.3, 0.24, 0.3);
uniform vec3 nacre : source_color = vec3(0.9, 0.9, 0.88);
uniform vec3 scar : source_color = vec3(0.35, 0.2, 0.38);
uniform vec3 flesh : source_color = vec3(0.82, 0.76, 0.62);
uniform vec3 mantle_edge : source_color = vec3(0.12, 0.1, 0.1);
uniform vec3 pearl_colour : source_color = vec3(0.96, 0.93, 0.9);
// How strong the mother-of-pearl's colours are.
uniform float pearly = 0.75;

varying vec3 rest;
varying float part;

void turn_about(inout vec3 p, inout vec3 n, vec3 at, vec3 axis, float a) {
	float c = cos(a);
	float s = sin(a);
	vec3 d = p - at;
	p = at + d * c + cross(axis, d) * s + axis * dot(axis, d) * (1.0 - c);
	n = n * c + cross(axis, n) * s + axis * dot(axis, n) * (1.0 - c);
}

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	int which = int(floor(UV2.x * 0.5 + 0.01));
	float upper = mod(floor(UV2.x + 0.01), 2.0);
	if (p == 4) {
		v = mix(pearl_at, v, step(0.5, pearl));
	} else if (p == 3) {
		// the body swells and settles slowly as it breathes
		v.y += sway * 0.0006 * (size / 0.16) * sin(TAU * phase + UV.y * 3.0) * (1.0 - UV.x) * open;
	}
	if (upper > 0.5) {
		turn_about(v, n, hinge_at[which], hinge_axis[which], open * opens[which] * upper_turn);
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
	float round_it = UV.y;
	vec2 at = rest.xz / size;
	float n1 = noise2(at * 18.0 + rest.y / size * 7.0);
	float n2 = noise2(at * 60.0 + 3.0);
	vec3 c;
	float rough = 0.7;
	float spec = 0.3;
	float shimmer = 0.0;
	if (p == 0) {
		// THE OUTSIDE: rough grey layers, each ending in a darker frilled edge; streaks of brown and violet
		// running out from the hinge; chalky where it is worn.
		float layer = u * 8.0 + 0.35 * sin(3.0 * round_it * PI) + 0.4 * n1;
		float edge = smoothstep(0.75, 0.97, fract(layer));
		float fade = 1.0 - smoothstep(0.3, 1.0, fwidth(layer));
		c = shell * (0.85 + 0.3 * n2);
		c = mix(c, shell_tint, 0.45 * smoothstep(0.45, 0.75, noise2(vec2(round_it * 14.0, u * 2.0))));
		c = mix(c, shell_dark, 0.55 * edge * fade);
		c = mix(c, vec3(0.8, 0.78, 0.74), 0.3 * smoothstep(0.6, 0.85, n1) * (1.0 - u));
		rough = 0.85;
	} else if (p == 1) {
		// THE INSIDE: mother-of-pearl, with the dark violet scar where the muscle held
		c = nacre * (0.92 + 0.08 * n1);
		vec2 q = vec2(u - 0.62, (round_it - 0.58) * 0.8);
		c = mix(c, scar, 0.8 * (1.0 - smoothstep(0.09, 0.12, length(q))));
		c = mix(c, lip, 0.5 * smoothstep(0.9, 1.0, u));
		shimmer = pearly;
		rough = 0.15;
		spec = 0.8;
	} else if (p == 2) {
		c = lip * (0.8 + 0.4 * n2);
		rough = 0.6;
	} else if (p == 3) {
		// THE BODY: creamy grey, glistening, its gills' fine folds, and its dark frilled mantle edge
		c = flesh * (0.9 + 0.15 * n1);
		c *= 0.9 + 0.1 * sin(round_it * 140.0 + n1 * 4.0) * smoothstep(0.3, 0.6, u);
		float frill = 0.92 + 0.035 * sin(round_it * 90.0) + 0.02 * sin(round_it * 37.0);
		c = mix(c, mantle_edge, smoothstep(frill - 0.04, frill, u));
		rough = 0.25;
		spec = 0.7;
	} else {
		c = pearl_colour;
		shimmer = 0.6;
		rough = 0.08;
		spec = 0.9;
	}
	// (mother-of-pearl: colours that shift as the surface turns from the eye)
	vec3 irid = 0.5 + 0.5 * cos(TAU * (glance * 1.5 + n1 * 0.5 + vec3(0.0, 0.33, 0.67)));
	c = mix(c, c * 0.65 + irid * 0.4, shimmer * (0.35 + 0.65 * glance));
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
