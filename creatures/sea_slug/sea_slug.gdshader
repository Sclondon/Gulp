shader_type spatial;
// The sea slugs (sea_slug.gd): a sea hare, a blue dragon and a Spanish dancer. Their colours and all of
// their moving, in one shader; `kind` says which (SeaSlug sets it, and every setting below, for its kind).
//
// What each point is comes from the model (tools/build_sea_slug.py): UV2.y the part (0 body, 1 a flap: the
// sea hare's parapodia or the dancer's skirt, 2 a rhinophore, 3 an oral tentacle, 4 a ceras or the stalk of
// an arm, 5 a gill). UV, on the body: x how far along (0 head to 1 tail), y how high (0 foot to 1 back); on
// the sea hare's flap: x along it, y from its root (0) to its edge (1); on the dancer's skirt: x round it
// (0 at the head, 0.25 its left side), y from its root (0) to its edge (1); on anything else x from its
// root (0) to its tip (1). UV2.x, on those others, a number of its own (0..1). COLOR on the sea hare's
// flaps: the flap's hinge (r |x| and g y, tenths of a metre; b 1 the left flap, 0 the right).
//
// It crawls (or, the blue dragon, drifts) at `swim` 0 and swims at 1. All of it is a function of `phase`
// alone, so a film of it loops exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Which slug: 0 the sea hare, 1 the blue dragon, 2 the Spanish dancer.
uniform int kind = 0;
// Its length, and how far its middle is behind the front (metres, as built).
uniform float body_length = 0.3;
uniform float body_half = 0.15;
// How far through a beat (0..1, it wraps). Set by SeaSlug.
uniform float phase = 0.0;
// 0 crawling (the blue dragon: drifting), 1 swimming.
uniform float swim : hint_range(0.0, 1.0) = 0.0;
// How strongly it moves at all (1 as it lives, 0 still).
uniform float sway = 1.0;
// How far it bends at the height of a swimming stroke (radians from head to tail): the sea hare and the
// dancer up and down, the blue dragon from side to side.
uniform float flex = 0.6;
// How many ripples lie along its body as it crawls.
uniform float ripples = 1.5;
// The sea hare: how far its flaps open at the top of a stroke (radians).
uniform float flap_open = 1.25;
// The dancer: how many waves run along each side of its skirt as it swims, how many frills its edge has
// all round, and how deep they are (radians at the edge).
uniform float skirt_waves = 1.2;
uniform float frills = 16.0;
uniform float frill_depth = 0.32;

// The colours (SeaSlug sets them for each kind).
// The body's main colour, its second colour (the sea hare's pale spots, the blue dragon's silver back, the
// dancer's paler underside) and its darkest (the sea hare's net of dark lines, the blue dragon's deep blue).
uniform vec3 body : source_color = vec3(0.32, 0.27, 0.12);
uniform vec3 body_second : source_color = vec3(0.7, 0.66, 0.52);
uniform vec3 body_dark : source_color = vec3(0.12, 0.09, 0.05);
// The edge of a flap or the skirt, and what stands on it (rhinophores, gills, cerata).
uniform vec3 edge : source_color = vec3(0.05, 0.04, 0.03);
uniform vec3 parts : source_color = vec3(0.36, 0.26, 0.14);
uniform vec3 tips : source_color = vec3(0.16, 0.1, 0.06);
// How much of its colour shows without any light on it.
uniform float vivid = 0.06;

// The dancer's skirt root (kept in step with the build script's SKIRT_*).
const float SKIRT_W = 0.040;
const float SKIRT_L = 0.118;
const float SKIRT_Y = 0.014;
const float SKIRT_SIDE = 0.050;
const float SKIRT_END = 0.014;

varying vec3 rest;
varying float part;
varying float under;

// Bends v about its middle round an arc of curvature k: in the x-z plane (`side` true; more than 0 and
// both ends come round to +X) or the y-z plane (both ends come up).
void arc(inout vec3 v, inout vec3 n, float k, bool side) {
	if (abs(k) < 0.01) {
		return;
	}
	float a = v.z * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	if (side) {
		n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
		v = vec3(r + (v.x - r) * c, v.y, (r - v.x) * sn);
	} else {
		n = vec3(n.x, n.y * c + n.z * sn, -n.y * sn + n.z * c);
		v = vec3(v.x, r + (v.y - r) * c, (r - v.y) * sn);
	}
}

// Turns p (and n) about a line along z through `at` (x, y) by `a` radians.
void turn_z(inout vec3 p, inout vec3 n, vec2 at, float a) {
	float c = cos(a);
	float s = sin(a);
	vec2 d = p.xy - at;
	p.xy = at + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
	n.xy = vec2(n.x * c - n.y * s, n.x * s + n.y * c);
}

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	under = 0.0;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float along = clamp((v.z + body_half) / body_length, 0.0, 1.0);
	float turn = TAU * phase;
	float crawl = sway * (1.0 - swim);
	float stroke = sin(turn);
	int p = int(part + 0.5);

	if (kind == 2 && p == 1) {
		// THE DANCER'S SKIRT, built flat: where it hinges round the body, how far out and how far above
		// or below its middle sheet each point is; then laid along a curving arc that droops at its root
		// and curls up at its edge as it crawls, and runs in waves from head to tail as it swims.
		float th = UV.x * TAU;
		float r = UV.y;
		vec3 root = vec3(SKIRT_W * sin(th), SKIRT_Y, -SKIRT_L * cos(th));
		vec3 out_way = normalize(vec3(sin(th) / SKIRT_W, 0.0, -cos(th) / SKIRT_L));
		float reach = SKIRT_END + (SKIRT_SIDE - SKIRT_END) * pow(sin(th) * sin(th), 0.7);
		float rho = dot(v.xz - root.xz, out_way.xz);
		float off = v.y - SKIRT_Y;
		under = step(off, -0.0001);
		float s_side = th < PI ? th / PI : (TAU - th) / PI;
		float rr = clamp(rho / reach, 0.0, 1.2);
		float frill = frill_depth * sin(frills * th) * (0.4 + 0.6 * swim);
		float b0 = mix(-0.32 + 0.05 * crawl * sin(turn - s_side * TAU), 0.06 + 0.12 * sway * stroke, swim);
		float b1 = mix(0.95 + 0.2 * crawl * sin(turn - s_side * TAU * ripples), 1.1 * sway * sin(turn - s_side * TAU * skirt_waves), swim) + frill;
		float b_at = b0 + b1 * rr;
		vec2 flat_up;
		if (abs(b1) < 0.001) {
			flat_up = vec2(cos(b0), sin(b0)) * rho;
		} else {
			flat_up = vec2(sin(b_at) - sin(b0), cos(b0) - cos(b_at)) * reach / b1;
		}
		vec3 up = vec3(0.0, 1.0, 0.0);
		vec3 sheet_up = -sin(b_at) * out_way + cos(b_at) * up;
		v = root + out_way * flat_up.x + up * flat_up.y + sheet_up * off;
		float n_out = dot(n, out_way);
		float n_up = n.y;
		vec3 n_side = n - out_way * n_out - up * n_up;
		n = n_side + out_way * (n_out * cos(b_at) - n_up * sin(b_at)) + up * (n_out * sin(b_at) + n_up * cos(b_at));
	} else if (kind == 0 && p == 1) {
		// THE SEA HARE'S FLAP: turned out about its hinge, a little as it breathes, wide as it swims.
		float sx = COLOR.b > 0.5 ? 1.0 : -1.0;
		vec2 hinge = vec2(sx * COLOR.r * 0.1, COLOR.g * 0.1);
		float wave = 0.5 + 0.5 * sin(turn - UV.x * 1.6);
		float a = sway * mix(0.05 * (0.5 + 0.5 * sin(turn - UV.x * 2.0)), 0.2 + flap_open * wave, swim);
		turn_z(v, n, hinge, -sx * a);
	} else if (p >= 2) {
		// What stands on it waves from its root, no two quite together.
		float reach = (kind == 1 ? 0.0008 : 0.004) * (p == 5 ? 1.0 : (p == 4 ? 1.0 : 0.5));
		float w = UV.x * UV.x * reach * sway;
		float a = turn - along * 5.0 + UV2.x * 2.4;
		v.x += w * sin(a);
		v.z += w * 0.6 * cos(a + UV2.x * 1.3);
		if (kind == 1 && p == 4) {
			// the blue dragon's fans paddle, forward and back, each pair a little after the one before
			float out_from = smoothstep(0.0015, 0.008, abs(v.x));
			v.z += sway * out_from * abs(v.x) * mix(0.12, 0.55, swim) * sin(turn - along * 4.0);
			v.y += sway * out_from * 0.0006 * mix(0.6, 1.0, swim) * cos(turn - along * 4.0 + UV2.x);
		}
	}

	// Crawling: a ripple that runs back along the body (it swells and sinks a little as each passes), the
	// head and the tail swinging slowly.
	if (kind != 1) {
		float ripple = sin(turn * 1.0 - along * ripples * TAU);
		float low = 1.0 - smoothstep(0.0, 0.08 * body_length, v.y);
		v.x *= 1.0 + crawl * 0.04 * ripple * (p == 0 ? 1.0 : 0.5);
		v.y *= 1.0 - crawl * 0.03 * ripple * (1.0 - low);
		float ends = (along - 0.5) * 2.0;
		v.x += crawl * 0.025 * body_length * ends * ends * sin(turn - along * 2.2);
		// Swimming: bent up and down along its length (the dancer heaving, the sea hare rowing).
		arc(v, n, sway * swim * flex * stroke / body_length, false);
	} else {
		// The blue dragon drifting: a slow sway of its body from side to side; swimming, more.
		arc(v, n, sway * mix(0.25, 1.0, swim) * flex * stroke / body_length, true);
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

// Round spots on a jittered grid (cells `cell` across): 1 inside a spot, its radius `size` of a cell.
float spots(vec2 p, float cell, float size) {
	vec2 g = p / cell;
	vec2 i = floor(g);
	vec2 jitter = vec2(hash2(i), hash2(i + 17.0)) * 0.5 + 0.25;
	float keep = step(0.35, hash2(i + 41.0));
	float d = length(fract(g) - jitter);
	float r = size * (0.6 + 0.6 * hash2(i + 7.0));
	return keep * (1.0 - smoothstep(r * 0.8, r, d));
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c = body;
	float rough = 0.5;
	float spec = 0.4;
	// (a place on its skin that does not move as it does: for the patterns)
	vec2 at = vec2(rest.z, rest.x + rest.y) / body_length;
	if (kind == 0) {
		// THE SEA HARE: olive brown, a net of darker lines, pale grey-white spots, the flaps' edges dark.
		float n1 = noise2(at * 34.0);
		float n2 = noise2(at * 90.0 + 3.0);
		float net = 1.0 - smoothstep(0.03, 0.09, abs(noise2(at * 26.0 + 9.0) - 0.5));
		c = body * (0.8 + 0.4 * n1);
		c = mix(c, body_dark, 0.55 * net);
		// (the pale spots ragged at their edges, a few big, many small)
		float rag = 0.25 * (noise2(at * 160.0) - 0.5);
		c = mix(c, body_second, 0.75 * spots(at + vec2(0.3, 0.1) + rag * 0.02, 0.05, 0.22));
		c = mix(c, body_second * 0.8, 0.45 * spots(at + rag * 0.01, 0.018, 0.3));
		c *= 0.9 + 0.2 * n2;
		if (p == 0) {
			// (paler at the sole of its foot)
			c = mix(c, body * 0.8 + body_second * 0.15, 1.0 - smoothstep(0.0, 0.12, UV.y));
		} else if (p == 1) {
			c = mix(c, edge, smoothstep(0.9, 0.99, UV.y));
		} else {
			c = mix(parts * (0.85 + 0.3 * n1), tips, smoothstep(0.7, 1.0, UV.x));
		}
		rough = 0.55;
	} else if (kind == 1) {
		// THE BLUE DRAGON (upside down): its foot, seen from above, deep blue with a pale blue line down its
		// middle and darker edges; its back, seen from below, silver; its cerata blue, darker at the tips.
		if (p == 0) {
			float h = UV.y;
			c = mix(body, body_dark, smoothstep(0.08, 0.3, h) * (1.0 - smoothstep(0.35, 0.55, h)));
			c = mix(c, vec3(0.55, 0.78, 1.0), 0.6 * (1.0 - smoothstep(0.0003, 0.0007, abs(rest.x))) * (1.0 - smoothstep(0.0, 0.25, h)));
			c = mix(c, body_second, smoothstep(0.45, 0.75, h));
			spec = mix(0.4, 0.8, smoothstep(0.5, 0.8, h));
			rough = mix(0.35, 0.2, smoothstep(0.5, 0.8, h));
		} else if (p == 4) {
			c = mix(body, parts, smoothstep(0.1, 0.6, UV.x));
			c = mix(c, tips, smoothstep(0.65, 0.95, UV.x));
			rough = 0.3;
		} else {
			c = mix(body, parts, UV.x);
		}
		c *= 0.9 + 0.2 * noise2(rest.xz * 3000.0);
	} else {
		// THE SPANISH DANCER: scarlet, finely speckled with pale dots; the skirt's edge white above, and
		// a broad white band along it beneath; its underside paler.
		float n1 = noise2(at * 40.0);
		c = body * (0.85 + 0.3 * n1);
		float dots = spots(vec2(rest.z, rest.x) * 1.0, 0.006, 0.18);
		if (p == 0) {
			c = mix(c, body_second, 0.6 * (1.0 - smoothstep(0.0, 0.3, UV.y)));
			c = mix(c, vec3(1.0, 0.9, 0.85), 0.5 * dots * smoothstep(0.4, 0.6, UV.y));
		} else if (p == 1) {
			float r = UV.y;
			vec3 top = mix(c, vec3(1.0, 0.92, 0.88), 0.45 * dots);
			top = mix(top, edge, smoothstep(0.93, 0.99, r));
			vec3 bottom = mix(body_second, body * 0.9, 0.3 * n1);
			bottom = mix(bottom, edge, smoothstep(0.72, 0.85, r));
			c = mix(top, bottom, under);
			c = mix(c, edge, step(0.995, r));
		} else if (p == 5) {
			c = mix(parts, tips, smoothstep(0.4, 1.0, UV.x));
		} else {
			c = mix(body, parts, smoothstep(0.2, 0.8, UV.x));
			c *= 0.75 + 0.25 * step(0.5, fract(UV.x * 7.0));
		}
		rough = 0.45;
	}
	// (soft, half-clear flesh: it brightens where it is seen edge on)
	c += c * 0.45 * glance * glance;
	ALBEDO = c;
	EMISSION = c * vivid;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
