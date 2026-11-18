shader_type spatial;
// The sea nettle (sea_nettle.gd): the bell folds shut and open in one wave; its oral arms and
// tentacles are ropes, simulated by SeaNettle, and each is laid here along its rope. What each point is comes from the model
// (tools/build_sea_nettle.py): COLOR.r the part (0 the top of the bell, 0.25 its underside, 0.5
// an oral arm, 1 a tentacle); COLOR.g, on the top of the bell, 1 for the copy drawn only where
// it is seen from inside, and on an arm 1 for a long sheet; COLOR.b which strand ((n + 0.5) / 32: arms 0 to 3, tentacles 4 to
// 27); UV.x across it, UV.y along a strand (on the bell, crown to rim), UV2.x a strand's length,
// UV2.y its phase. How the bell folds is worked out the same way in SeaNettle (_fold), which
// hangs the ropes from it: keep them in step.
//
// The bell's markings are drawn here, after the user's photographs (the component's README):
// no texture files. Nothing here needs more than GL Compatibility has.
render_mode blend_mix, depth_draw_opaque, cull_disabled, depth_prepass_alpha;

// Kept in step with the model and the script.
const float RADIUS = 0.9;
// How far the rim swings in and down at the beat (radians; SeaNettle.swing).
uniform float swing = 0.35;
const float LAG = 0.15;
const vec2 HINGE = vec2(0.18, 0.66);
const int ARMS = 4;
const int ARM_POINTS = 12;
const int TENTACLE_POINTS = 9;

// Set by SeaNettle each frame.
// The ropes: a picture ARM_POINTS wide, a row a strand (as `SeaNettle.strands()` lists them), each
// point of it a point of that strand's rope from its root to its tip, in the nettle's own space.
// (A picture, not a list of numbers: 264 points are more than some phones' GL allows a shader.)
uniform sampler2D ropes : filter_nearest, repeat_disable;
// How far through a beat of its bell (0..1).
uniform float beat = 0.0;
// How far out past its resting shape the bell opens between beats, as a share of its swing in
// (0.3 a dome that eases a little; 1.5 and it opens right out into a shallow saucer).
uniform float open = 0.3;
// How the bell leans into the way it goes (its own space).
uniform vec3 trail = vec3(0.0);
// Its faint glow (0 by day, 1 at night).
uniform float glow = 0.0;
// The bell: amber where the jelly is thick, peach where it is thin; its rust markings; the
// hollow under it. The oral arms' ruffles and their pale edges and membranes. The tentacles.
uniform vec3 amber : source_color = vec3(0.93, 0.55, 0.27);
uniform vec3 peach : source_color = vec3(0.98, 0.76, 0.66);
uniform vec3 rust : source_color = vec3(0.4, 0.11, 0.05);
uniform vec3 under : source_color = vec3(0.98, 0.82, 0.76);
uniform vec3 frill : source_color = vec3(0.98, 0.6, 0.4);
uniform vec3 frill_pale : source_color = vec3(1.0, 0.88, 0.8);
uniform vec3 maroon : source_color = vec3(0.42, 0.07, 0.08);
// How much of what is behind it the jelly hides: the bell's wall, the underside, an arm's
// membrane and its ruffles (its markings and tentacles hide nearly all).
uniform float bell_alpha = 0.62;
uniform float under_alpha = 0.3;
uniform float membrane_alpha = 0.42;
uniform float ruffle_alpha = 0.86;
// How thick the tentacles are, for 1 as the model has them (they are made a little thicker than
// life, to be seen from far off: a close picture wants them finer).
uniform float tentacle_width = 1.0;

varying float part;
varying float flag;
varying vec2 at;
varying float long_is;
varying vec3 rest;

// How far the bell is drawn in, through a beat (0..1): quickly in, slowly let go.
float squeeze(float x) {
	x = fract(x);
	return smoothstep(0.0, 0.22, x) * (1.0 - smoothstep(0.28, 1.0, x));
}

// How far a point of the bell `reach` from its axis is turned in and down about the hinge (a
// ring near its crown) now: the beat reaches the rim a little after the middle, and between
// beats the bell opens out past its resting shape.
float fold_turn(float reach) {
	float rim = smoothstep(HINGE.x, RADIUS, reach);
	return swing * (squeeze(beat - LAG * rim) * (1.0 + open) - open) * rim;
}

vec3 fold(vec3 p) {
	float reach = length(p.xz);
	float turn = fold_turn(reach);
	vec2 arm = vec2(reach, p.y) - HINGE;
	vec2 swung = vec2(arm.x * cos(turn) + arm.y * sin(turn), arm.y * cos(turn) - arm.x * sin(turn));
	p.xz *= (HINGE.x + swung.x) / max(reach, 0.0001);
	p.y = HINGE.y + swung.y;
	return p;
}

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

// Smooth noise, 0..1.
float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(
			mix(mix(hash3(i), hash3(i + vec3(1.0, 0.0, 0.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 0.0)), hash3(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
			mix(mix(hash3(i + vec3(0.0, 0.0, 1.0)), hash3(i + vec3(1.0, 0.0, 1.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 1.0)), hash3(i + vec3(1.0, 1.0, 1.0)), f.x), f.y),
			f.z);
}

// The markings on the top of the bell: how dark (0..1) at `where` (round it 0..1, crown to rim
// 0..1) and `p`, the point of the bell at rest.
//  - a rust arch on each of the thirty-two lappets of the rim, pale gaps between them where
//    the tentacles leave;
//  - a second ring of sixteen rust dabs, a wavering garland about two fifths of the way up from
//    the rim, a streak running from each towards the crown;
//  - fine dark veins like cracks, branching, mostly between that ring and the crown;
//  - a few rust blotches at the crown.
float markings(vec2 where, vec3 p) {
	float v = where.y;
	float rough = noise3(p * 9.0);
	float blotch = noise3(p * 3.7 + 11.0);
	// the rim's arches: a dark crescent on each lappet, a thin wash of rust from it to the lip
	float x = fract(where.x * 32.0) - 0.5;
	float ragged = noise3(p * 21.0 + 2.0);
	float top = 0.905 + 0.05 * (2.0 * x) * (2.0 * x) + (rough - 0.5) * 0.03 + (ragged - 0.5) * 0.012;
	float gap = 1.0 - smoothstep(0.33, 0.48, abs(x) + (blotch - 0.5) * 0.08);
	float rim = smoothstep(top - 0.006, top + 0.01, v) * (1.0 - 0.75 * smoothstep(top + 0.012, top + 0.045, v)) * gap * (0.7 + 0.3 * blotch);
	// the second ring: sixteen dabs, each an arc with its middle towards the crown, no two alike
	float lane = where.x * 16.0 + 0.5;
	float x16 = fract(lane) - 0.5;
	float own = hash3(vec3(mod(floor(lane), 16.0), 3.0, 7.0));
	float line = 0.575 + (own - 0.5) * 0.05 + 0.05 * (2.0 * x16) * (2.0 * x16) + (rough - 0.5) * 0.05 + (ragged - 0.5) * 0.02;
	float thick = 0.046 * (0.35 + 1.3 * rough) * (1.0 - 0.5 * abs(2.0 * x16));
	float dab = (1.0 - smoothstep(thick * 0.3, thick, abs(v - line))) * (1.0 - smoothstep(0.24, 0.46 + 0.08 * own, abs(x16))) * smoothstep(0.12, 0.4, ragged + 0.5 * blotch) * (0.65 + 0.35 * blotch);
	// the streaks under the dabs, towards the crown
	float streak = (1.0 - smoothstep(0.02, 0.1, abs(x16 + (rough - 0.5) * 0.12))) * smoothstep(0.2, 0.45, v) * (1.0 - smoothstep(0.5, 0.6, v)) * 0.45 * blotch;
	// the veins: the ridges of a noise, two sizes of them, in patches
	float n1 = noise3(p * vec3(6.5, 2.4, 6.5) + 3.0) + 0.3 * noise3(p * vec3(14.0, 6.0, 14.0));
	float n2 = noise3(p * vec3(12.0, 4.5, 12.0) + 7.0) + 0.3 * noise3(p * vec3(26.0, 11.0, 26.0));
	float crack = max(1.0 - smoothstep(0.004, 0.02, abs(n1 - 0.68)), 0.75 * (1.0 - smoothstep(0.004, 0.026, abs(n2 - 0.66))));
	crack *= smoothstep(0.35, 0.6, blotch + 0.25 * rough) * (0.3 + 0.7 * (1.0 - smoothstep(0.5, 0.66, v))) * smoothstep(0.03, 0.12, v) * (1.0 - smoothstep(0.8, 0.86, v));
	// the crown's blotches
	float crown = smoothstep(0.58, 0.75, blotch + 0.3 * rough) * (1.0 - smoothstep(0.08, 0.24, v)) * 0.7;
	return clamp(max(max(rim, dab), max(streak, max(crack * 0.9, crown))), 0.0, 1.0);
}

void vertex() {
	part = COLOR.r;
	flag = COLOR.g;
	at = UV;
	long_is = UV2.x;
	rest = VERTEX;
	if (part < 0.375) {
		// The bell: its rim swung in and down as it beats, and out again past its rest.
		float reach = length(VERTEX.xz);
		float turn = fold_turn(reach);
		vec2 way = VERTEX.xz / max(reach, 0.0001);
		vec2 n = vec2(dot(NORMAL.xz, way), NORMAL.y);
		n = vec2(n.x * cos(turn) + n.y * sin(turn), n.y * cos(turn) - n.x * sin(turn));
		NORMAL = vec3(NORMAL.x + way.x * (n.x - dot(NORMAL.xz, way)), n.y, NORMAL.z + way.y * (n.x - dot(NORMAL.xz, way)));
		VERTEX = fold(VERTEX);
		// (leaning a little into the way it goes)
		VERTEX.xz -= trail.xz * max(VERTEX.y, 0.0) * 0.35;
	} else {
		// A strand: where this point is along its rope, and its offset from the strand's own
		// middle line (straight down from its root, as the model has it) turned to lie the
		// way the rope runs there.
		float s = UV.y;
		float long = UV2.x;
		float ph = UV2.y * 6.2831853;
		int row = int(floor(COLOR.b * 32.0));
		bool arm = part < 0.75;
		int count = arm ? ARM_POINTS : TENTACLE_POINTS;
		vec3 root;
		if (arm) {
			float a = 0.7853982 + float(row) * 1.5707963;
			root = vec3(cos(a) * 0.12, -0.05, sin(a) * 0.12);
			// its ruffles ripple, most at their edges, twice a beat
			float e = abs(UV.x * 2.0 - 1.0);
			VERTEX += NORMAL * sin(beat * 12.5663706 + s * long * 7.0 + ph) * 0.03 * e * smoothstep(0.0, 0.04, s);
		} else {
			int i = row - ARMS;
			float a = float(i / 3) * 0.7853982 + 0.3926991 + float(i % 3 - 1) * 0.1963495;
			root = vec3(cos(a), 0.0, sin(a)) * RADIUS * 0.96 + vec3(0.0, 0.02, 0.0);
			VERTEX -= NORMAL * (0.0045 + 0.011 * exp(-s * 30.0) + 0.0015 * (1.0 - s)) * (1.0 - tentacle_width);
		}
		vec3 offset = VERTEX - (root - vec3(0.0, s * long, 0.0));
		float f = clamp(s, 0.0, 1.0) * float(count - 1);
		int i1 = min(int(f), count - 2);
		float t = f - float(i1);
		vec3 p0 = texelFetch(ropes, ivec2(max(i1 - 1, 0), row), 0).xyz;
		vec3 p1 = texelFetch(ropes, ivec2(i1, row), 0).xyz;
		vec3 p2 = texelFetch(ropes, ivec2(i1 + 1, row), 0).xyz;
		vec3 p3 = texelFetch(ropes, ivec2(min(i1 + 2, count - 1), row), 0).xyz;
		// (a smooth curve through the points)
		vec3 c1 = p2 - p0;
		vec3 c2 = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3;
		vec3 c3 = 3.0 * (p1 - p2) + p3 - p0;
		vec3 on_line = 0.5 * (2.0 * p1 + c1 * t + c2 * t * t + c3 * t * t * t);
		vec3 way = normalize(0.5 * (c1 + 2.0 * c2 * t + 3.0 * c3 * t * t) + vec3(0.0, -0.0001, 0.0));
		// (the smallest turn that takes straight down to the way the rope runs; an arm's stalk,
		// above its root, stays as the bell has it)
		vec3 w = cross(vec3(0.0, -1.0, 0.0), way);
		float c = max(-way.y, -0.98);
		float follows = arm ? smoothstep(0.0, 0.04, s) : 1.0;
		offset += (cross(w, offset) + cross(w, cross(w, offset)) / (1.0 + c)) * follows;
		NORMAL = normalize(NORMAL + (cross(w, NORMAL) + cross(w, cross(w, NORMAL)) / (1.0 + c)) * follows);
		VERTEX = on_line + offset;
	}
}

void fragment() {
	// Seen edge on, jelly is denser.
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	vec3 c;
	float a;
	if (part < 0.125) {
		// The top of the bell. (Drawn twice: its far wall, seen from inside, before everything
		// else, and its near wall after.)
		if ((flag > 0.5) == FRONT_FACING) {
			discard;
		}
		float dark = markings(at, rest);
		// amber at the crown, where the jelly is thick; a paler peach band towards the rim, its
		// lobes paler still down their middles
		float lobe = 0.5 + 0.5 * cos(at.x * 16.0 * 6.2831853);
		c = mix(amber, peach, smoothstep(0.5, 0.75, at.y) * (0.55 + 0.3 * lobe));
		c = mix(c, amber * 0.9, 0.35 * noise3(rest * 2.3 + 5.0) * (1.0 - smoothstep(0.4, 0.7, at.y)));
		c = mix(c, rust, dark);
		a = mix(bell_alpha, 0.97, dark);
	} else if (part < 0.375) {
		// The underside: pale and clear, fine lines running out to the rim in its outer band,
		// a soft ring where that band begins, a dark dash on each lappet.
		float band = smoothstep(0.52, 0.62, at.y);
		float lines = pow(0.5 + 0.5 * cos(at.x * 96.0 * 6.2831853), 3.0);
		c = mix(under, peach, 0.35 * band);
		c = mix(c, amber, 0.4 * lines * band * (1.0 - smoothstep(0.9, 0.97, at.y)));
		float ring = 1.0 - smoothstep(0.0, 0.035, abs(at.y - 0.57));
		c = mix(c, frill_pale, ring * 0.3);
		float x = fract(at.x * 32.0) - 0.5;
		float dash = smoothstep(0.955, 0.985, at.y) * (1.0 - smoothstep(0.26, 0.42, abs(x)));
		c = mix(c, rust * 1.15, dash);
		a = mix(under_alpha + 0.2 * lines * band + 0.14 * ring, 0.96, dash);
	} else if (part < 0.75) {
		// An oral arm: a clear pale membrane down its middle, a dark line along it; orange
		// ruffles towards its edges, finely pleated, their very edge pale and scalloped like lace.
		float e = abs(at.x * 2.0 - 1.0);
		float along = at.y * long_is;
		float ruffled = smoothstep(0.12, 0.7, e);
		c = mix(frill_pale, frill, ruffled);
		float pleat = 0.5 + 0.5 * sin(along * 210.0 + 2.5 * sin(e * 7.0 + along * 3.0));
		c *= mix(1.0, 0.82 + 0.26 * pleat, smoothstep(0.25, 0.7, e) * (1.0 - 0.7 * smoothstep(0.2, 0.6, at.y)));
		c = mix(c, frill_pale, smoothstep(0.84, 0.97, e) * 0.75);
		// (paler the further down the plume)
		c = mix(c, frill_pale, 0.45 * smoothstep(0.25, 1.0, at.y));
		float mid = (1.0 - smoothstep(0.012, 0.05, e)) * flag * smoothstep(0.0, 0.03, at.y);
		c = mix(c, maroon * 1.5, mid * 0.75);
		a = mix(membrane_alpha, ruffle_alpha, max(ruffled, mid));
		// the lace: the edge is cut in small scallops, with a few holes just inside it
		float cut = 0.965 + 0.035 * sin(along * 130.0 + 1.3 * sin(along * 17.0));
		a *= 1.0 - smoothstep(cut - 0.04, cut, e);
	} else {
		// A tentacle: pale where it leaves the rim, then dark and fine.
		c = mix(peach, maroon, smoothstep(0.0, 0.035, at.y));
		a = 1.0;
	}
	// (only a tentacle is quite solid: what is solid is drawn before the rest, hard-edged)
	a = part > 0.75 ? 1.0 : clamp(a + edge * 0.18, 0.0, 0.96);
	ALBEDO = c;
	ALPHA = a;
	ROUGHNESS = 0.5;
	SPECULAR = 0.2;
	EMISSION = c * glow * (0.35 + edge * 0.5);
}

void light() {
	// Soft bands: a jelly lets light through, so even its far side is lit.
	float n_dot_l = dot(NORMAL, LIGHT);
	float wrap = clamp((n_dot_l + 0.6) / 1.6, 0.0, 1.0);
	float band = floor(wrap * 3.0 + 0.5) / 3.0;
	DIFFUSE_LIGHT += mix(wrap, band, 0.25) * ATTENUATION * LIGHT_COLOR / 3.14159;
	vec3 half_way = normalize(LIGHT + VIEW);
	SPECULAR_LIGHT += pow(max(dot(NORMAL, half_way), 0.0), 60.0) * 0.2 * ATTENUATION * LIGHT_COLOR;
}
