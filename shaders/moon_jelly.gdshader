shader_type spatial;
// The moon jelly (scripts/moon_jelly.gd). The model (tools/build_moon_jelly.py) is still: here the
// bell beats, the fringe of fine tentacles sways and trails, and each of the four oral arms is laid
// along a chain of points that the script simulates like a rope (after GameCommon's rope, which
// sends its chain to the vertex shader in the same way).
//
// What a point is comes from the model: COLOR.r the part (0 the top of the bell, 0.25 its underside
// and stalk, 0.5 a gonad, 0.75 an oral arm, 1 a fringe tentacle), COLOR.g which arm, UV.x across,
// UV.y along (the bell: crown to rim; a strand: root to tip), UV2.x a tentacle's length, UV2.y its
// phase.
//
// Drawn as light added to the picture: jelly is clear, and what is seen of it is the light it
// scatters, more where the line of sight runs through more of it (its edges, its folds).
render_mode blend_add, unshaded, cull_disabled, depth_draw_never, fog_disabled;

// Kept in step with the model and the script.
const int ARM_POINTS = 10;
const float ARM_ROOT = 0.07;
const float ARM_Y = 0.08;
const float ARM_LONG = 0.85;

// Set by MoonJelly each frame.
uniform float clock = 0.0;
// How far through a beat of its bell (0..1).
uniform float beat = 0.0;
// How the fringe is swung back (its own space, a share of each tentacle's length).
uniform vec3 trail = vec3(0.0);
// The four arms' chains, in its own space: arm k's points are arm_pts[k * ARM_POINTS ...].
uniform vec3 arm_pts[40];

// The colour of its light, and of its gonads and the eight sense organs on its rim.
uniform vec3 light : source_color = vec3(0.62, 0.76, 1.0);
uniform vec3 gonad : source_color = vec3(1.0, 0.74, 0.42);
uniform vec3 organ : source_color = vec3(1.0, 0.55, 0.15);
uniform float brightness = 1.0;
// How long this jelly's fringe is, for one as the model has it (they vary: the user, 2026-11-17).
uniform float fringe = 1.0;
// How much of its light the water takes in each metre between it and the eye (fog would add
// its own colour to light that is added to the picture, so the jelly dims itself instead).
uniform float murk = 0.06;

varying float part;
varying vec2 at;

// The beat of the bell (the user, 2026-11-17: "They need to deform their bodies more than just
// jiggle- actualy linke sin wave based full pulses"). MoonJelly has the same sums (`squeeze`,
// `bend`), to hold the arms to the bell as it beats: change one, change the other.
// How far the rim swings down and in at the top of a beat (radians), how much later the beat
// reaches the rim than the middle (a share of a beat), and the share of a beat spent closing.
const float SWING = 0.9;
const float LAG = 0.3;
// How far open the bell is between beats, as a share of the swing: it unfolds past its resting
// saucer, its rim lifting and spreading, before it closes again (the user, 2026-11-17: "the dont
// unfold their bell enough in the pulse, they should move in big wave like motions").
// Set by MoonJelly, beat by beat: most beats about 0.3, now and then over 1, when the bell
// opens right out and its rim turns up past flat, all but inside out (the user, 2026-11-17:
// "they still need to unfold even more in the pulse somtiemes, like totally inside out").
uniform float open = 0.3;
const float CLOSING = 0.36;

// How far the bell is drawn in, through a beat (0..1): one whole sine wave with no rest in it,
// quicker closing than opening.
float squeeze(float x) {
	x = fract(x);
	float through = x < CLOSING ? 0.5 * x / CLOSING : 0.5 + 0.5 * (x - CLOSING) / (1.0 - CLOSING);
	return 0.5 - 0.5 * cos(through * 6.2831853);
}

// A point of the bell as the beat has bent it: the saucer folds down into a deep cup about a
// ring a quarter of the way out, the rim swinging down and in, the crown lifting; the fold
// runs out from the middle to the rim as a wave.
vec3 bend(vec3 p) {
	float reach = length(p.xz);
	float rim = smoothstep(0.12, 1.0, reach);
	float q = squeeze(beat - LAG * rim);
	// Lumpy (the user, 2026-11-17: "the vertex distortion more lumpy and extreme"): the fold is
	// deeper in some places round the bell than in others, in three lobes that go round with
	// the beat and five that drift, and a swell runs out through the jelly as it closes.
	float round_it = atan(p.z, p.x);
	// (only a little: the user, 2026-11-17, "too lumpya on the wobble")
	float lump = 1.0 + 0.07 * sin(round_it * 3.0 + beat * 6.2831853) + 0.04 * sin(round_it * 5.0 - clock * 0.9);
	float turn = SWING * (q * (1.0 + open) - open) * rim * lump;
	vec2 arm = vec2(reach - 0.25, p.y - 0.15);
	vec2 swung = vec2(arm.x * cos(turn) + arm.y * sin(turn), arm.y * cos(turn) - arm.x * sin(turn));
	p.xz *= (0.25 + swung.x) / max(reach, 0.0001);
	p.y = 0.15 + swung.y + 0.07 * squeeze(beat) + 0.012 * sin(reach * 9.0 - beat * 12.5663706) * rim * (0.4 + 0.6 * q);
	return p;
}

// The veins of the bell (its canals), after the user's picture of them and as Aurelia has them:
// sixteen trees leave the middle, each forking three times on its way to the rim into eight fine
// twigs, and between each pair of trees one thin canal runs straight out unforked. Nothing in it
// is regular: every tree stands a little off its place, every fork comes at its own distance
// out, is lopsided in its own way and wavers its own way, and the canals thin towards the rim
// (the user, 2026-11-17: "the veins need a higher quality less repetitive look").
// `where` is (round the bell 0..1, crown to rim 0..1), `soft` how much of the bell a pixel
// covers there (so that the lines stay smooth far off); the answer is how bright, 0..1.
float vein_hash(float n) {
	return fract(sin(n * 91.345) * 47453.5453);
}

// (smooth noise along a line: -1..1)
float vein_waver(float x) {
	float i = floor(x);
	float f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(vein_hash(i), vein_hash(i + 1.0), f) * 2.0 - 1.0;
}

float veins(vec2 where, float soft) {
	float r = where.y;
	// (the trees are not evenly spaced round the bell)
	float round_it = where.x * 6.2831853;
	float lane = where.x * 16.0 + 0.14 * sin(round_it * 3.0 + 1.7) + 0.1 * sin(round_it * 7.0 + 0.4);
	float tree = floor(lane + 0.5);
	float x = lane - tree;
	// (the eighth tree is the first again, round the bell)
	tree = mod(tree, 16.0);
	// how wide a lane is here, in bell radii
	float wide = r * 0.3927;
	float thick = mix(0.005, 0.0018, smoothstep(0.3, 1.0, r));
	// The straight canal between two trees.
	float between = mod(floor(lane), 16.0);
	float straight = abs(fract(lane) - 0.5 + vein_waver(r * 9.0 + between * 31.0) * 0.012 / max(wide, 0.05));
	float line = (1.0 - smoothstep(thick * 0.6, thick * 0.6 + soft, straight * wide)) * 0.55;
	// The tree: fold the lane about each fork in turn; what is left is how far the nearest
	// twig is. Each fold has its own distance out, its own spread and its own lean.
	float id = tree * 7.31;
	float own = vein_hash(id);
	x += vein_waver(r * 7.0 + id) * 0.02 * smoothstep(0.35, 0.6, r);
	float fork1 = 0.42 + 0.09 * own;
	float side1 = x < 0.0 ? -1.0 : 1.0;
	x = abs(x + 0.02 * (own - 0.5)) - (0.2 + 0.05 * (own - 0.5)) * smoothstep(fork1, fork1 + 0.3, r);
	id += side1 * 1.93;
	own = vein_hash(id);
	x += vein_waver(r * 11.0 + id * 3.0) * 0.016 * smoothstep(fork1, fork1 + 0.2, r);
	float fork2 = 0.58 + 0.12 * own;
	float side2 = x < 0.0 ? -1.0 : 1.0;
	x = abs(x + 0.015 * (own - 0.5)) - (0.1 + 0.035 * (own - 0.5)) * smoothstep(fork2, fork2 + 0.22, r);
	id += side2 * 4.27;
	own = vein_hash(id);
	x += vein_waver(r * 15.0 + id * 5.0) * 0.011 * smoothstep(fork2, fork2 + 0.15, r);
	float fork3 = 0.74 + 0.12 * own;
	// (some twigs never fork again)
	float last = own > 0.25 ? 1.0 : 0.0;
	x = abs(x) - (0.048 + 0.02 * (own - 0.5)) * smoothstep(fork3, fork3 + 0.16, r) * last;
	float twig = abs(x) * wide;
	float bright = 0.75 + 0.25 * vein_waver(r * 13.0 + id * 9.0);
	line = max(line, (1.0 - smoothstep(thick, thick + soft, twig)) * bright);
	// (they reach all the way in to the four rings, fainter the nearer the middle: the user,
	// 2026-11-17, "they should reach all the way to the 4 rings (thought get softer)")
	return line * smoothstep(0.08, 0.2, r) * mix(0.3, 1.0, smoothstep(0.15, 0.55, r)) * (1.0 - smoothstep(0.95, 0.99, r));
}

void vertex() {
	part = COLOR.r;
	at = UV;
	if (part > 0.875) {
		// A fringe tentacle: it goes with the rim, sweeps in as the bell closes, sways, and
		// trails behind.
		float s = UV.y;
		float ph = UV2.y * 6.2831853;
		vec3 root = VERTEX + vec3(0.0, s * UV2.x, 0.0);
		float long = UV2.x * fringe;
		vec2 out_way = normalize(root.xz);
		vec3 across = VERTEX - (root - vec3(0.0, s * long, 0.0));
		// Its root goes with the rim. The swing of the rim then runs down it like a wave down
		// a rope: each part of it hangs the way the rim pointed a little while before, the
		// further down the later (worked out as the sum of short pieces, so that it curves).
		vec3 at_rope = bend(root);
		const int PIECES = 6;
		for (int i = 0; i < PIECES; i++) {
			float from = float(i) / float(PIECES);
			float piece = clamp(s - from, 0.0, 1.0 / float(PIECES));
			// (loose: the swing takes most of a beat to reach its tip, and overshoots)
			float swung = squeeze(beat - LAG - 0.05 - 0.7 * (from + 0.5 / float(PIECES)));
			float turn = SWING * 1.1 * (swung * (1.0 + open) - open);
			// (and it is thrown out a little as the rim snaps back)
			turn -= 0.25 * squeeze(beat - LAG - 0.45 - 0.5 * from) * from;
			at_rope += vec3(-out_way.x * sin(turn), -cos(turn), -out_way.y * sin(turn)) * piece * long;
		}
		vec3 sway = vec3(sin(clock * 1.3 + ph - s * 5.0), 0.0, cos(clock * 1.1 + ph * 1.7 - s * 4.0)) * 0.42 * s * s;
		vec3 off = (trail * pow(s, 1.5) + sway) * long;
		off.y += dot(trail, trail) * 0.45 * s * s * long;
		VERTEX = at_rope + across + off;
	} else if (part > 0.625) {
		// An oral arm: where this point is along the chain, and its offset from the arm's
		// middle line turned to lie the way the chain runs there.
		int k = int(floor(COLOR.g * 4.0));
		float a = 0.7853982 + float(k) * 1.5707963;
		float s = UV.y;
		vec3 offset = VERTEX - vec3(cos(a) * ARM_ROOT, ARM_Y - s * ARM_LONG, sin(a) * ARM_ROOT);
		float f = s * float(ARM_POINTS - 1);
		int i = min(int(f), ARM_POINTS - 2);
		float t = f - float(i);
		int base = k * ARM_POINTS;
		vec3 p0 = arm_pts[base + max(i - 1, 0)];
		vec3 p1 = arm_pts[base + i];
		vec3 p2 = arm_pts[base + i + 1];
		vec3 p3 = arm_pts[base + min(i + 2, ARM_POINTS - 1)];
		// (a smooth curve through the points)
		vec3 c1 = p2 - p0;
		vec3 c2 = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3;
		vec3 c3 = 3.0 * (p1 - p2) + p3 - p0;
		vec3 on_line = 0.5 * (2.0 * p1 + c1 * t + c2 * t * t + c3 * t * t * t);
		vec3 way = normalize(0.5 * (c1 + 2.0 * c2 * t + 3.0 * c3 * t * t) + vec3(0.0, -0.0001, 0.0));
		// (the smallest turn that takes straight down to the way the chain runs)
		vec3 w = cross(vec3(0.0, -1.0, 0.0), way);
		float c = max(-way.y, -0.98);
		offset += cross(w, offset) + cross(w, cross(w, offset)) / (1.0 + c);
		NORMAL += cross(w, NORMAL) + cross(w, cross(w, NORMAL)) / (1.0 + c);
		// its frills ripple
		offset *= 1.0 + 0.12 * sin(clock * 2.2 + s * 26.0 + float(k)) * abs(UV.x - 0.5) * 2.0;
		VERTEX = on_line + offset;
	} else {
		// The bell (and the gonads in it): the rim is drawn in and down, the crown lifts, and
		// the beat reaches the rim a little after the middle.
		VERTEX = bend(VERTEX);
	}
}

void fragment() {
	// Seen edge on, there is more jelly in the way.
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	vec3 c;
	if (part < 0.125) {
		// The top of the bell: a faint film, bright where it turns away; canals running out to
		// the rim, forking as they go; a bright line at the rim; an orange speck in each notch.
		float glow = 0.05 + 0.5 * pow(edge, 2.2);
		float soft = max(fwidth(at.x) * 6.2831853 * at.y, fwidth(at.y)) * 1.0 + 0.001;
		// (the veins catch the light only where the bell is seen aslant: not looked straight
		// down on, and not at its very edge: the user, 2026-11-17, "smaller and more numerous,
		// and sort of only veiwable at certain angles")
		float catches = smoothstep(0.12, 0.5, edge) * (1.0 - 0.7 * smoothstep(0.78, 1.0, edge));
		glow += veins(at, soft) * 0.4 * catches;
		glow += smoothstep(0.955, 0.99, at.y) * 0.55;
		c = light * glow;
		vec2 to_organ = vec2((fract(at.x * 8.0 + 0.5) - 0.5) * 0.8, at.y - 0.975);
		c += organ * (1.0 - smoothstep(0.008, 0.022, length(to_organ))) * 1.4;
	} else if (part < 0.375) {
		c = light * (0.03 + 0.3 * pow(edge, 2.0));
	} else if (part < 0.625) {
		// A gonad: warm, lumpy, the brightest thing in it (the user, 2026-11-17: "the 4 rings
		// should glow the most").
		float lumps = 0.75 + 0.25 * sin(at.y * 90.0) * sin(at.x * 12.566);
		c = gonad * (1.0 + 0.7 * edge) * lumps;
	} else if (part < 0.875) {
		// An oral arm: a thin veil, brighter along its frilled edges and its fold.
		float across = abs(at.x - 0.5) * 2.0;
		float glow = 0.07 + 0.22 * edge + 0.3 * smoothstep(0.72, 1.0, across) + 0.3 * (1.0 - smoothstep(0.0, 0.14, across));
		c = light * glow * (1.0 - 0.35 * at.y);
	} else {
		c = light * 0.2 * (1.0 - 0.75 * at.y);
	}
	ALBEDO = c * brightness * exp(-murk * length(VERTEX));
}
