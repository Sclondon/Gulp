shader_type spatial;
// The pufferfish (pufferfish.gd): it sculls with its dorsal and anal fins, which buzz, and fans
// with its pectoral fins; its body is stiff and its tail steers. `puff` blows it up into a ball
// with every spine standing straight out; `gape` opens its beak. Every marking is drawn here: no
// texture files. Nothing here needs more than GL Compatibility has.
//
// What each point is comes from the model (tools/build_pufferfish.py): COLOR.r the part, as a
// tenth (0 body, 1 lower jaw, 2 eye, 3 upper beak, 4 lower beak, 5 spine, 6 dorsal, 7 anal,
// 8 tail, 9 pectoral). On the body: UV.x how far along (0 snout to 1 tail tip), UV.y how high
// (0 belly line to 1 back line), UV2.x how far round from the back line (metres, + right);
// COLOR.g 1 on the upper lip (it lifts as the mouth opens); COLOR.b the inside of the mouth (on
// the lip and jaw). On a fin: UV.x along its rays (0 root to 1 edge), UV.y across it counted in
// rays; UV2 and COLOR.b the way its flat side faces. On a spine: UV.x along it (0 root, 1 tip);
// UV2 its root's x and y, COLOR.g its root's s (body lengths); UV.y and COLOR.b the way it lies.
//
// Everything that moves runs on `phase` (0..1 through one beat, set by Pufferfish): the tail
// beats, the fins' strokes and buzzes each go a whole number of times a beat, so it comes round
// exactly.
render_mode cull_back, depth_draw_opaque;

// As the model is built (the build script's SHAPE lines): its length; where its lower jaw hinges
// (how far along, how high; body lengths) and the line of its mouth; where its eye sits on the
// skin and the middle of its pectoral fin's root (x out, y up, how far along); where the roots of
// its dorsal and anal fins run (y, s at their front and back ends) and their rays; the ball it
// blows up into (its middle's height and how far along, its radius).
const float LENGTH = 0.3;
const vec2 HINGE = vec2(0.04, -0.028);
const float MOUTH_Y = -0.012;
const vec3 EYE_SKIN = vec3(0.1117, 0.104, 0.17);
const vec3 EYE_OUT = vec3(0.7829, 0.5802, -0.2244);
const vec3 PEC_ROOT = vec3(0.1393, 0.005, 0.303);
const vec4 DORSAL_ROOT = vec4(0.0904, 0.6, 0.0592, 0.675);
const float DORSAL_RAYS = 10.0;
const vec4 ANAL_ROOT = vec4(-0.071, 0.625, -0.0454, 0.7);
const float ANAL_RAYS = 9.0;
const vec2 PUFF_AT = vec2(0.0, 0.38);
const float PUFF_RADIUS = 0.35;
// How far the lower jaw swings down when `gape` is 1 (radians), and how far the upper lip lifts.
const float GAPE_ANGLE = 0.75;
const float GAPE_LIFT = 0.22;

// How far through a beat it is (0..1); how many times in a beat its tail beats, its pectoral
// fins fan and its dorsal and anal fins buzz (whole numbers).
uniform float phase = 0.0;
uniform float tail_beats = 1.0;
uniform float strokes = 4.0;
uniform float buzzes = 8.0;
// How widely its tail swings (1: a tenth of its length each way), and how hard its fins work
// (1 as it potters about; 0 held still).
uniform float sway = 0.25;
uniform float row = 1.0;
// The mouth: 0 shut, 1 wide open (the lower jaw and its beak swing down, the upper lip lifts).
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// Blown up: 0 as it swims, 1 a ball with every spine standing straight out.
uniform float puff : hint_range(0.0, 1.0) = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// For a game: `flash` adds white light to the whole fish (a hit); `rim` lights its edges with
// its own colour; `tint` multiplies its colours.
uniform float flash = 0.0;
uniform float rim = 0.0;
uniform vec3 tint : source_color = vec3(1.0);
// Its colours: the back and sides, the spots, the belly, the fins, the beak, the inside of the
// mouth; how many spots (0 none, 1 as built), how strong the skin's sheen is.
uniform vec3 back : source_color = vec3(0.66, 0.56, 0.36);
uniform vec3 spot_colour : source_color = vec3(0.2, 0.13, 0.07);
uniform vec3 belly : source_color = vec3(0.95, 0.93, 0.85);
uniform vec3 fin_colour : source_color = vec3(0.8, 0.72, 0.52);
uniform vec3 beak_colour : source_color = vec3(0.94, 0.91, 0.8);
uniform vec3 mouth : source_color = vec3(0.2, 0.06, 0.06);
uniform float spots = 1.0;
uniform float sheen = 0.15;

// The cartoon eye: 0 the eye as it is built, 1 bigger, a white with a coloured iris, a pupil, a
// highlight that stays put and a dark outline. `eye_look`: where both eyes look (-1..1: x towards
// the nose, y up). `blink`: 0 open, 1 shut (the lids meet and the eye squashes). The pufferfish's
// is huge, round and alarmed: white all round a small green-gold iris and a pinprick pupil, no lid.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform float eye_size = 1.9;
uniform vec3 iris : source_color = vec3(0.62, 0.78, 0.2);
uniform float iris_size = 0.4;
uniform float pupil_size = 0.42;
uniform float lid = 1.4;
uniform float lower_lid = -1.4;

varying vec3 rest;
varying float part;
varying float inside;


vec3 ball_middle() {
	return vec3(0.0, PUFF_AT.x, PUFF_AT.y - 0.5) * LENGTH;
}


// Where a point of the still fish goes when it is blown up by `amount`: the body about its
// middle onto the ball, the mouth carried with it, the tail left as it is.
vec3 puffed(vec3 p, float amount) {
	if (amount <= 0.0) {
		return p;
	}
	vec3 c = ball_middle();
	float r = PUFF_RADIUS * LENGTH;
	vec3 m = vec3(0.0, MOUTH_Y, -0.505) * LENGTH;
	vec3 dm = c + normalize(m - c) * r - m;
	vec3 d = p - c;
	vec3 dp = c + d / max(length(d), 1e-6) * r - p;
	float s = p.z / LENGTH + 0.5;
	float a = smoothstep(0.02, 0.09, s);
	float b = smoothstep(0.7, 0.8, s);
	return p + amount * mix(dm, dp, a) * (1.0 - b);
}


// How much of the way round onto the ball a point's normal turns.
float puff_turn(vec3 p, float amount) {
	float s = p.z / LENGTH + 0.5;
	return amount * smoothstep(0.02, 0.09, s) * (1.0 - smoothstep(0.7, 0.8, s));
}


// Turns v by `angle` about the unit `axis`.
vec3 turned(vec3 v, vec3 axis, float angle) {
	float c = cos(angle);
	float sn = sin(angle);
	return v * c + cross(axis, v) * sn + axis * dot(axis, v) * (1.0 - c);
}


// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.15 * LENGTH;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.65 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}


void vertex() {
	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	inside = (part < 1.5) ? COLOR.b : 0.0;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float tail = phase * TAU * tail_beats;
	float stroke = phase * TAU * strokes;
	float buzz = phase * TAU * buzzes;
	float amount = clamp(puff, 0.0, 1.0);
	// (the mouth's pieces ride with the front of the face as it puffs)
	vec3 mouth_at = vec3(0.0, MOUTH_Y, -0.505) * LENGTH;
	vec3 mouth_moves = puffed(mouth_at, amount) - mouth_at;
	if (part == 1.0 || part == 4.0 || part == 3.0 || (part == 0.0 && COLOR.g > 0.5)) {
		// The lower jaw and its beak swing down about the hinge; the upper lip and its beak lift.
		bool lower = part == 1.0 || part == 4.0;
		float a = lower ? gape * GAPE_ANGLE : -gape * GAPE_LIFT;
		vec2 hinge = lower ? vec2(HINGE.y, HINGE.x - 0.5) * LENGTH : vec2(MOUTH_Y + 0.014, HINGE.x - 0.5) * LENGTH;
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
		v += mouth_moves;
	} else if (part == 0.0) {
		vec3 was = v;
		v = puffed(v, amount);
		n = normalize(mix(n, normalize(was - ball_middle()), puff_turn(was, amount)));
	} else if (part == 2.0) {
		// The eye: grown about where it sits on the skin (the cartoon eye), squashed as it blinks,
		// and carried with the skin.
		vec3 at = vec3(EYE_SKIN.x * side_is, EYE_SKIN.y, EYE_SKIN.z - 0.5) * LENGTH;
		if (cartoon_eyes > 0.0) {
			vec3 d = v - at;
			d.y *= 1.0 - 0.45 * blink * cartoon_eyes;
			v = at + d * mix(1.0, eye_size, cartoon_eyes);
		}
		// (puffed, it turns with the skin it sits in, to face out of the ball)
		vec3 at_now = puffed(at, amount);
		vec3 was_out = vec3(EYE_OUT.x * side_is, EYE_OUT.y, EYE_OUT.z);
		vec3 now_out = normalize(at_now - ball_middle());
		vec3 axis = cross(was_out, now_out);
		float sn = length(axis);
		float angle = atan(sn, dot(was_out, now_out)) * amount;
		axis = sn > 1e-5 ? axis / sn : vec3(1.0, 0.0, 0.0);
		v = at_now + turned(v - at, axis, angle);
		n = turned(n, axis, angle);
	} else if (part == 5.0) {
		// A spine: carried with the skin at its root, and turned from lying back along the skin to
		// standing straight out of the ball.
		vec3 root = vec3(UV2.x, UV2.y, COLOR.g - 0.5) * LENGTH;
		vec3 way = vec3(UV.y, COLOR.b * 2.0 - 1.0, 0.0);
		way.z = sqrt(max(1.0 - dot(way.xy, way.xy), 0.0));
		vec3 root_now = puffed(root, amount);
		vec3 out_way = normalize(root_now - ball_middle());
		vec3 axis = cross(way, out_way);
		float sn = length(axis);
		float angle = atan(sn, dot(way, out_way)) * smoothstep(0.1, 0.9, amount);
		axis = sn > 1e-5 ? axis / sn : vec3(1.0, 0.0, 0.0);
		v = root_now + turned(v - root, axis, angle);
		n = turned(n, axis, angle);
	} else {
		// A fin waves the way its flat side faces, more towards its edge.
		vec3 flat_way = normalize(vec3(UV2.x, UV2.y, COLOR.b * 2.0 - 1.0));
		float r = UV.x;
		if (part == 9.0) {
			// The pectoral fins fan: each turns out from the body and back about the upright line
			// through its root, the left half a stroke after the right, its edge trailing.
			float a = stroke + (side_is > 0.0 ? 0.0 : PI);
			float spin = side_is * row * (0.45 * sin(a) + 0.05);
			vec3 root = vec3(PEC_ROOT.x * side_is, PEC_ROOT.y, PEC_ROOT.z - 0.5) * LENGTH;
			float c = cos(spin);
			float sn = sin(spin);
			vec3 d = v - root;
			v = root + vec3(d.x * c + d.z * sn, d.y, d.z * c - d.x * sn);
			n = vec3(n.x * c + n.z * sn, n.y, n.z * c - n.x * sn);
			flat_way = vec3(flat_way.x * c + flat_way.z * sn, flat_way.y, flat_way.z * c - flat_way.x * sn);
			v += flat_way * LENGTH * 0.02 * row * r * r * sin(a - 1.3);
			v += puffed(root, amount) - root;
		} else if (part == 6.0 || part == 7.0) {
			// The dorsal and anal fins buzz from side to side, a wave running back along them, and
			// ride with the skin along their roots.
			vec4 line = part == 6.0 ? DORSAL_ROOT : ANAL_ROOT;
			float t = clamp(UV.y / (part == 6.0 ? DORSAL_RAYS : ANAL_RAYS), 0.0, 1.0);
			v.x += LENGTH * 0.03 * row * pow(r, 1.4) * sin(buzz - t * 2.2 + (part == 7.0 ? PI : 0.0));
			vec3 root = vec3(0.0, mix(line.x, line.z, t), mix(line.y, line.w, t) - 0.5) * LENGTH;
			v += puffed(root, amount) - root;
		} else {
			// (the tail's edge lags behind the bend that carries it)
			v.x += LENGTH * 0.03 * sway * r * r * sin(tail - TAU * 0.5 - 1.1);
		}
	}
	// The swimming bend: little of it, only the wrist and tail; its tail steers. Each place is
	// carried sideways and turned to lie along the bent body, so the fins and tail follow it.
	float sb = clamp(rest.z / LENGTH + 0.5, 0.0, 1.05);
	float behind = max(sb - 0.55, 0.0);
	float reach = 0.6 * behind * behind;
	float reach_slope = 1.2 * behind;
	float w = tail - TAU * sb * 0.5;
	float off = LENGTH * sway * reach * sin(w);
	float slope = sway * (reach_slope * sin(w) - reach * TAU * 0.5 * cos(w));
	vec3 along = normalize(vec3(slope, 0.0, 1.0));
	vec3 across = vec3(along.z, 0.0, -along.x);
	v = vec3(off, v.y, v.z) + across * v.x;
	n = across * n.x + vec3(0.0, n.y, 0.0) + along * n.z;
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = normalize(n);
}


// A hash of a cell, 0..1 each.
vec2 hash2(vec2 p) {
	p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
	return fract(sin(p) * 43758.5453);
}


// How much of a dark spot covers a place on the skin (`q`: how far along, how far round; body
// lengths): one spot to a cell of a grid, each a little off its middle and of its own size.
float spotted(vec2 q) {
	float cell = 0.042;
	vec2 g = q / cell;
	vec2 base = floor(g);
	float best = 0.0;
	// (the soft edge from how fast the grid runs across the screen, the same for every cell)
	float aa = max(length(fwidth(g)) * 0.7, 0.02);
	for (int i = -1; i <= 1; i++) {
		for (int j = -1; j <= 1; j++) {
			vec2 c = base + vec2(float(i), float(j));
			vec2 h = hash2(c);
			vec2 at = c + 0.2 + 0.6 * h;
			float radius = 0.2 + 0.13 * h.y;
			float d = length(g - at);
			best = max(best, 1.0 - smoothstep(radius - aa, radius + aa, d));
		}
	}
	return best;
}


// The cartoon eye at a point of the eye's dome (`uv` its UV), in skin of colour `skin`. On the
// dome, e is (towards the nose, up) in seen radii of the eye: 1 where the eye meets the skin.
vec3 cartoon_eye(vec2 uv, vec3 skin) {
	vec2 on_eye = uv * 2.0 - 1.0;
	vec2 e = vec2(on_eye.y, on_eye.x) / 0.644;
	float er = length(e);
	vec3 white = vec3(0.97, 0.96, 0.92);
	vec3 ink = vec3(0.02, 0.02, 0.025);
	vec2 ic = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.92 - iris_size) * 0.75;
	float ir = length(ic) / iris_size;
	float aa = max(fwidth(ir), 0.02);
	vec3 c = mix(white * 0.86, white, smoothstep(1.0, 0.4, er));
	vec3 ring = mix(iris * 1.2, iris * 0.6, smoothstep(0.3, 1.0, ir));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ir));
	c = mix(c, iris * 0.3, smoothstep(0.82, 0.95, ir) * (1.0 - smoothstep(1.0 - aa, 1.0 + aa, ir)));
	float pd = length(ic / (iris_size * pupil_size));
	float pa = max(fwidth(pd), 0.02);
	c = mix(c, ink, 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	float ea = max(fwidth(er), 0.01);
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.15 - ea, 0.15 + ea, length(e - vec2(0.26, 0.38))));
	c = mix(c, vec3(1.0), 0.8 * (1.0 - smoothstep(0.06 - ea, 0.06 + ea, length(e - vec2(-0.22, -0.3)))));
	// the lids (none show while it is open: an alarmed stare); they meet as it blinks
	float shut = -0.12;
	float upper = mix(lid, shut, blink);
	float lower = mix(lower_lid - 0.12 * e.x * e.x, shut + 0.03, blink);
	float la = max(fwidth(e.y), 0.01);
	float on_lid = max(smoothstep(upper - la, upper + la, e.y), 1.0 - smoothstep(lower - la, lower + la, e.y));
	float lid_edge = max(1.0 - smoothstep(0.06, 0.06 + 2.0 * la, abs(e.y - upper)),
		0.6 * (1.0 - smoothstep(0.04, 0.04 + 2.0 * la, abs(e.y - lower))));
	c = mix(c, skin * 0.92, on_lid);
	c = mix(c, ink, lid_edge * step(er, 1.0) * step(upper, 1.0));
	c = mix(c, ink, smoothstep(0.86 - ea, 0.88 + ea, er));
	c = mix(c, skin, smoothstep(1.0 - ea, 1.0 + ea, er));
	return c;
}


void fragment() {
	float s = rest.z / LENGTH + 0.5;
	float y = rest.y / LENGTH;
	float x = rest.x / LENGTH;
	vec3 c = back;
	float rough = 0.45;
	float glint = sheen;
	float seen = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	float in_mouth = inside;
	if (part < 0.5) {
		// The body: sandy above with dark spots, a pale belly; the line between wavers.
		float h = UV.y;
		float line = 0.36 + 0.03 * sin(s * 40.0) - 0.08 * smoothstep(0.55, 0.8, s);
		float pale = 1.0 - smoothstep(line - 0.04, line + 0.04, h);
		c = mix(back, belly, pale);
		// (darker along the top of the back, paler towards the belly line)
		c *= mix(1.0, 0.82, smoothstep(0.75, 1.0, h));
		float dark = spotted(vec2(s, UV2.x / LENGTH)) * spots;
		dark *= smoothstep(line + 0.02, line + 0.1, h) * smoothstep(0.05, 0.1, s) * (1.0 - smoothstep(0.86, 0.9, s));
		c = mix(c, spot_colour, 0.88 * dark);
		if (COLOR.g < 0.5) {
			// (the face behind the lips: the inside of the mouth, seen when they part)
			float m = length(vec2(x / 0.02, (y - MOUTH_Y) / 0.011));
			in_mouth = max(in_mouth, (1.0 - smoothstep(0.8, 1.0, m)) * (1.0 - smoothstep(0.02, 0.03, s)));
		}
	} else if (part < 1.5) {
		c = belly * 0.95;
	} else if (part > 2.5 && part < 4.5) {
		// The beak: four teeth fused into two plates, a groove down the middle of each.
		c = beak_colour * mix(0.85, 1.0, smoothstep(0.0, 0.6, abs(UV.y - 0.5) * 2.0));
		c = mix(c, beak_colour * 0.45, 1.0 - smoothstep(0.0012, 0.0024, abs(x)));
		rough = 0.25;
		glint = 0.35;
	} else if (part > 4.5 && part < 5.5) {
		// A spine: sandy at its root, dark at its tip.
		c = mix(back * 1.12, spot_colour, smoothstep(0.45, 0.95, UV.x));
		rough = 0.35;
	} else if (part > 5.5) {
		float r = UV.x;
		c = fin_colour;
		if (part > 7.5 && part < 8.5) {
			// (the tail: dusky towards its edge, a pale rim)
			c = mix(fin_colour * 0.9, spot_colour * 1.6, 0.6 * smoothstep(0.45, 0.85, r));
			c = mix(c, fin_colour * 1.1, smoothstep(0.9, 0.97, r));
		} else if (part > 8.5) {
			c = mix(back, fin_colour * 1.05, smoothstep(0.0, 0.3, r));
		}
		// (its rays as fine lines)
		float between = abs(fract(UV.y) - 0.5) * 2.0;
		float lines = smoothstep(0.55, 1.0, between) * smoothstep(0.05, 0.3, r) * (1.0 - smoothstep(0.3, 0.8, fwidth(UV.y)));
		c *= 1.0 - 0.18 * lines;
		rough = 0.5;
		glint *= 0.4;
	}
	if (part > 1.5 && part < 2.5) {
		// An eye: a dark pupil in a green-gold ring, dark at the rim; the skin round it.
		vec2 on_eye = UV * 2.0 - 1.0;
		float er = length(on_eye);
		vec3 around = mix(back, belly, 0.15);
		c = mix(vec3(0.5, 0.55, 0.15), around * 0.6, smoothstep(0.52, 0.64, er));
		c = mix(c, vec3(0.8, 0.75, 0.25), 0.5 * (1.0 - smoothstep(0.36, 0.44, er)));
		c = mix(c, vec3(0.01), 1.0 - smoothstep(0.28, 0.32, er));
		if (cartoon_eyes > 0.0) {
			c = mix(c, cartoon_eye(UV, around), cartoon_eyes);
		}
		rough = 0.08;
		glint = 0.0;
	}
	c = mix(c, mouth, in_mouth);
	glint *= 1.0 - in_mouth;
	c *= tint;
	float aslant = pow(1.0 - seen, 3.0);
	c += vec3(1.0, 0.97, 0.9) * glint * aslant;
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.4;
	EMISSION = c * (rim * 0.8 * aslant) + vec3(flash);
}
