shader_type spatial;
// The fin whale (fin_whale.gd): it swims by beating its flukes up and down, its flippers scull, its
// lower jaw drops (its pleated throat ballooning), and every marking is drawn here: no texture files. What each
// point is comes from the model (tools/build_fin_whale.py): COLOR.r the part, as a tenth (0 body, 1
// lower jaw, 2 eye, 3 baleen, 4 the mouth's wall, 5 dorsal, 6 flukes, 7 flipper, 8 a knob on the upper
// skin, 9 a knob on the lower jaw). On the body and jaw UV.x is how far along (0 the snout's tip to 1
// the flukes' notch), UV.y how high (0 the belly or keel line, 1 the back line or the middle of the
// floor of the mouth), UV2.x how far round the skin from the top line (metres, + its left side, -
// its right), UV2.y the whole way round from top line to bottom line (metres); COLOR.g how much of
// the throat (it balloons), COLOR.b how much inside the mouth. On a fin UV.x is root (0) to tip (1)
// (on the flukes, middle to tip), UV.y leading (0) to trailing (1) edge; UV2 and COLOR.b the way
// its flat side faces. On the mouth's wall COLOR.g is how far it unfolds. On an eye or a knob UV is
// where a point is on its round face (its middle at 0.5, 0.5).
//
// Everything that moves runs on `phase` (0..1 through one beat, set by FinWhale): the flukes beat
// `tail_beats` times and the flippers scull `sculls` times a beat (whole numbers), so a picture of
// it comes round again exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back, depth_draw_opaque;

// As the model is built: snout to the flukes' notch (metres), where the lower jaw hinges (how far
// along, how high, in body lengths), how far back the pleated throat runs, how far open the mouth's
// wall was built (radians), where the flukes are hinged (how far along).
const float LENGTH = 20.0;
const float HINGE_S = 0.212;
const float HINGE_Y = -0.028;
const float NAVEL_S = 0.5;
const float FAN_OPEN = 0.03;
const float JOINT = 0.935;
// How far the lower jaw drops at `gape` 1 (radians), and how far the throat balloons down then
// (body lengths).
const float GAPE_MAX = 1.05;
const float BALLOON = 0.065;
// The throat's pleats: how many each side, how far up the side they reach (0 the belly line, 1
// the back line), from and to where along (body lengths), how deep (metres).
const float PLEATS = 45.0;
const float PLEAT_TOP = 0.42;
const float PLEAT_FROM = -0.01;
const float PLEAT_TO = 0.5;
const float PLEAT_DEPTH = 0.02;
// The two blowholes: how far along (body lengths), how far apart at the back (metres from the
// middle line), how long (metres).
const float BLOW_S = 0.199;
const float BLOW_APART = 0.07;
const float BLOW_LONG = 0.45;
// The eye (the one on +X; the other is its mirror): the middle of its rim, where it meets the skin
// (metres), the way it faces, and how far the skin round it curves away (metres: the radius of the
// head there), for the cartoon eye, which swells it about the middle of its rim.
const vec3 EYE_AT = vec3(1.0712, -0.24, -5.7);
const vec3 EYE_OUT = vec3(0.9151, -0.0507, -0.4001);
const float EYE_BEND = 1.1;
// The cartoon eye, this whale's own (keen and quick, the greyhound of the sea: a sea-green iris, a narrow bar of a pupil, the upper lid slanting down towards the snout in a focused look, the lower lid raised): how much bigger than life; the
// white, the iris (its colour, how big: 1 the whole eye) and the pupil (its half width and half
// height, as a share of the eye, and how square it is: 2 round or oval, more a rounded bar); the
// lids: where the upper and lower lids' edges cross the middle (1 the top of the eye, -1 the
// bottom), how far the upper lid's edge drops towards the snout (+) or the tail (-), how much it
// bows up in the middle, where the lids meet as it blinks; the lid's colour.
const float EYE_GROW = 1.6;
const vec3 EYE_WHITE = vec3(0.92, 0.92, 0.9);
const vec3 EYE_IRIS = vec3(0.25, 0.5, 0.42);
const float IRIS_SIZE = 0.5;
const vec2 PUPIL = vec2(0.25, 0.08);
const float PUPIL_SQUARE = 4.0;
const float LID_TOP = 0.5;
const float LID_BOTTOM = -0.5;
const float LID_SLANT = 0.3;
const float LID_BOW = 0.15;
const float LID_MEET = -0.05;

// How far through a beat it is (0..1), and how many times in a beat its flukes beat and its
// flippers scull (whole numbers).
uniform float phase = 0.0;
uniform float tail_beats = 1.0;
uniform float sculls = 1.0;
// How hard it swims: 1 cruising (the flukes' notch rises and falls about 1.2 m either way), 0 still.
uniform float sway = 1.0;
// How far its flippers scull (1 as it cruises).
uniform float scull = 1.0;
// How long the wave down its body is, in body lengths.
uniform float wave = 1.3;
// How far its mouth is open: 0 shut, 1 its lower jaw dropped wide (as it gulps a swarm of krill).
uniform float gape = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the head to
// the flukes (0 straight; more than 0 the flukes come round to +X, its left, as it turns left).
uniform float curl = 0.0;
// The same up and down: how far the whole body is bent about its middle, in radians from snout to
// flukes (0 straight; more than 0 its head and its flukes both come up, as it rounds out of a
// dive; less than 0 both go down, as it arches its back to dive).
uniform float arch = 0.0;

// The skin: its dark grey-brown back, its white underside; the pale chevron on its back behind
// the head and the pale blaze sweeping up its right side; the fins' white undersides; the pale
// baleen at the front of its right side.
uniform vec3 back : source_color = vec3(0.14, 0.14, 0.15);
uniform vec3 belly : source_color = vec3(0.86, 0.86, 0.84);
uniform vec3 chevron : source_color = vec3(0.42, 0.43, 0.44);
uniform vec3 fin_under : source_color = vec3(0.84, 0.84, 0.82);
uniform vec3 baleen_pale : source_color = vec3(0.82, 0.78, 0.62);
// How strongly the chevron and the blaze show (0 none).
uniform float chevron_show = 1.0;
// Inside the mouth: the roof, the floor and tongue, the walls; the baleen plates and their fringe.
uniform vec3 mouth_roof : source_color = vec3(0.07, 0.06, 0.065);
uniform vec3 tongue : source_color = vec3(0.45, 0.26, 0.26);
uniform vec3 mouth_wall : source_color = vec3(0.36, 0.17, 0.17);
uniform vec3 baleen : source_color = vec3(0.13, 0.13, 0.15);
uniform vec3 fringe : source_color = vec3(0.62, 0.6, 0.55);
// The eye.
uniform vec3 eye_dark : source_color = vec3(0.02, 0.018, 0.016);
uniform vec3 eye_iris : source_color = vec3(0.16, 0.1, 0.06);
// The cartoon eye: 0 the eye as it is (above), 1 a big cartoon eye of its own (a pale white, a
// coloured iris, a dark pupil, a highlight, a dark rim, lids that give it its look); between, a blend.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the cartoon eye looks: -1..1 each way, right and up as seen by someone looking at that eye
// (so both eyes turn the same way: x more than 0 turns its gaze towards its -X side).
uniform vec2 eye_look = vec2(0.0);
// A blink: 0 open, 1 shut (its lids, the colour of its skin, close over the eye).
uniform float blink : hint_range(0.0, 1.0) = 0.0;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying vec2 extra;

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yzx + 33.33);
	return fract((p.x + p.y) * p.z);
}

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

// Soft value noise, 0..1, a lump to each 1 of `p`.
float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(hash3(i), hash3(i + vec3(1.0, 0.0, 0.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 0.0)), hash3(i + vec3(1.0, 1.0, 0.0)), f.x), f.y);
	float b = mix(mix(hash3(i + vec3(0.0, 0.0, 1.0)), hash3(i + vec3(1.0, 0.0, 1.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 1.0)), hash3(i + vec3(1.0, 1.0, 1.0)), f.x), f.y);
	return mix(a, b, f.z);
}

float fbm3(vec3 p) {
	return 0.55 * noise3(p) + 0.3 * noise3(p * 2.03 + 11.0) + 0.15 * noise3(p * 4.1 + 23.0);
}

// The nearest of a scatter of points, one to each square of `p`: (how far, a number for which).
vec2 cells(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	float best = 9.0;
	float which = 0.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 o = vec2(float(x), float(y));
			float h = hash2(i + o);
			vec2 at = o + vec2(h, hash2(i + o + 17.0)) * 0.8 + 0.1;
			float d = length(at - f);
			if (d < best) {
				best = d;
				which = h;
			}
		}
	}
	return vec2(best, which);
}

// Barnacles: a crust of small pale cones, each with a dark hole in its middle, `size` metres apart,
// on the skin place `at` (metres) where `px` metres show in one pixel (finer, they fade out).
// Returns how much of a barnacle is here (0..1); `hole` how much of its dark middle; `bump` the
// height it gives the skin (metres).
float barnacles(vec2 at, float size, float px, out float hole, out float bump) {
	vec2 b = cells(at / size + 13.0);
	float shown = 1.0 - smoothstep(0.2, 0.5, px / size);
	float disc = (1.0 - smoothstep(0.3, 0.42, b.x)) * step(b.y, 0.85);
	hole = (1.0 - smoothstep(0.07, 0.13, b.x)) * disc * shown;
	bump = size * shown * (0.35 * disc * (1.0 - smoothstep(0.1, 0.42, b.x)) - 0.25 * hole);
	return disc * shown;
}

// How far up the middle line of the body is, `s` body lengths behind the snout: a
// wave that runs back along it, all but nothing at the head, growing down the tail stock.
float lift_at(float s) {
	float grow = 0.035 + 0.965 * pow(clamp((s - 0.22) / 0.78, 0.0, 1.0), 2.1);
	return sway * LENGTH * 0.06 * grow * sin(TAU * (phase * tail_beats - s / wave));
}

// The body behind the head laid round an arc to one side (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.22 * LENGTH;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.72 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// The whole body laid round an arc that goes up and down, about its middle (see `arch`).
void arch_bend(inout vec3 v, inout vec3 n) {
	if (abs(arch) < 0.001) {
		return;
	}
	float k = arch / LENGTH;
	float a = v.z * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x, n.y * c + n.z * sn, n.z * c - n.y * sn);
	v = vec3(v.x, r - (r - v.y) * c, (r - v.y) * sn);
}

// Turns a point (and its normal) about the jaw's hinge: more than 0 swings what is ahead of it down.
void about_hinge(inout vec3 v, inout vec3 n, float a) {
	vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5) * LENGTH;
	vec2 d = v.yz - hinge;
	float c = cos(a);
	float sn = sin(a);
	v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
}

void vertex() {
	rest = VERTEX;
	rest_normal = NORMAL;
	part = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float s = v.z / LENGTH + 0.5;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float open = clamp(gape, 0.0, 1.0) * GAPE_MAX;
	if (part == 1.0 || part == 9.0) {
		// The lower jaw swings down about its hinge under the eye; the throat behind it stays.
		about_hinge(v, n, open * smoothstep(HINGE_S + 0.03, HINGE_S - 0.012, s));
	} else if (part == 4.0) {
		// The mouth's wall unfolds from the roof of the mouth down to the lower jaw.
		about_hinge(v, n, COLOR.g * (open - FAN_OPEN));
	} else if (part == 0.0) {
		// The throat balloons down and out as the mouth opens.
		float b = clamp(gape, 0.0, 1.0) * COLOR.g;
		v.y -= b * BALLOON * LENGTH;
		v.x *= 1.0 + b * BALLOON * 3.0;
	} else if (part == 2.0 && cartoon_eyes > 0.0) {
		// The cartoon eye: the eye swollen about the middle of its rim, sunk a little at its edge
		// where the skin round it curves away.
		vec3 at = EYE_AT * vec3(side_is, 1.0, 1.0);
		vec3 ax = EYE_OUT * vec3(side_is, 1.0, 1.0);
		float k = mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
		vec3 d = v - at;
		vec3 flat_d = d - ax * dot(d, ax);
		v = at + d * k - ax * (dot(flat_d, flat_d) * (k * k - 1.0)) / (2.0 * EYE_BEND);
	} else if (part == 7.0) {
		// The flippers scull slowly, the stroke growing out to the tip, one a little after the other.
		vec3 flat_way = normalize(vec3(UV2.x, UV2.y, COLOR.b * 2.0 - 1.0));
		float a = phase * TAU * sculls + (side_is > 0.0 ? 0.0 : 0.5);
		v += flat_way * LENGTH * 0.008 * scull * UV.x * UV.x * sin(a - UV.x * 0.6);
	}
	// The beat: the middle line rises and falls in a wave down the body, each cross-section turned
	// to stay square to it; behind their hinge the flukes are one stiff plate, pitched a little
	// further than the stock's own line.
	float zc = min(s, JOINT);
	float h = lift_at(zc);
	float slope = (lift_at(zc + 0.002) - lift_at(zc - 0.002)) / (0.004 * LENGTH);
	float turn = atan(slope) * (1.0 + 0.55 * smoothstep(JOINT - 0.06, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, (s - zc) * LENGTH);
	v = vec3(o.x, h + o.y * c + o.z * sn, (zc - 0.5) * LENGTH - o.y * sn + o.z * c);
	n = vec3(n.x, n.y * c + n.z * sn, n.z * c - n.y * sn);
	curl_bend(v, n);
	arch_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// A height (metres) the surface seems to have, turned into a tilt of its normal (bump mapping
// without a texture or tangents: Mikkelsen's surface gradient, from screen-space derivatives).
vec3 bumped(vec3 n, vec3 pos, float height) {
	vec3 dpdx = dFdx(pos);
	vec3 dpdy = dFdy(pos);
	vec3 r1 = cross(dpdy, n);
	vec3 r2 = cross(n, dpdx);
	float det = dot(dpdx, r1);
	vec3 grad = sign(det) * (dFdx(height) * r1 + dFdy(height) * r2);
	return normalize(abs(det) * n - grad);
}

void fragment() {
	int p = int(part + 0.5);
	float s = rest.z / LENGTH + 0.5;
	// how high on the body (0 the belly line, 1 the back line); on a fin, root (0) to tip (1)
	float hh = UV.y;
	float girth = max(UV2.y, 0.001);
	float arc = UV2.x;
	// how far from the belly line round towards the back line (0..1)
	float fb = clamp((girth - abs(arc)) / girth, 0.0, 1.0);
	// +1 its left side, -1 its right
	float side_is = rest.x >= 0.0 ? 1.0 : -1.0;
	vec3 m = rest;
	float inside = (p <= 1) ? extra.y : 0.0;
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	// A flat place on the skin for patterns (metres): along the body and round it from the top
	// line; on a fin, across its faces. `px`: how many metres of it one pixel covers (patterns
	// finer than that fade out).
	vec2 q = (p <= 1) ? vec2(s * LENGTH, arc) : vec2(m.z + 0.7 * m.y, m.x + 0.4 * m.y);
	float px = length(fwidth(q));
	// (the pleats' grooves: how many grooves up from the belly line, and how many one pixel covers)
	float pleat_k = fb * PLEATS / PLEAT_TOP;
	float pleat_fw = fwidth(pleat_k);
	float plate_k = m.z / 0.02;
	float plate_fw = fwidth(plate_k);
	vec3 c = vec3(0.5);
	float height = 0.0;
	float rough = 0.5;
	float spec = 0.4;
	if (p == 2) {
		// An eye: a dark round middle in a dark brown iris, in folds of skin.
		float r = length(UV - 0.5) * 2.0;
		c = mix(eye_dark, eye_iris, smoothstep(0.25, 0.45, r) * 0.7);
		c = mix(c, eye_dark * 2.0, smoothstep(0.62, 0.8, r));
		c *= 0.85 + 0.3 * noise3(m * 40.0);
		rough = 0.12;
		spec = 0.7;
		// Where on its round face (1 its rim): forward (towards the snout) and up, and right as seen
		// by someone looking at it.
		float fwd = (0.5 - UV.y) * 2.0;
		float upw = (UV.x - 0.5) * 2.0;
		vec2 e = vec2(side_is * fwd, upw);
		float aa = max(fwidth(r), 0.002);
		// its lids, an edge above and below, closing as it blinks
		float b = clamp(blink, 0.0, 1.0);
		float top_edge = mix(LID_TOP, LID_MEET, b) - LID_SLANT * fwd * (1.0 - b) - LID_BOW * fwd * fwd * (1.0 - 0.6 * b);
		float bottom_edge = mix(LID_BOTTOM, LID_MEET, b) + 0.25 * fwd * fwd * (1.0 - b);
		float lid = max(smoothstep(top_edge - aa, top_edge + aa, upw), smoothstep(bottom_edge + aa, bottom_edge - aa, upw));
		if (cartoon_eyes > 0.0) {
			vec2 look = clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.92 - IRIS_SIZE) ;
			vec2 ir = e - look;
			float ri = length(ir) / IRIS_SIZE;
			vec3 toon = EYE_WHITE * (1.0 - 0.18 * smoothstep(0.5, 1.0, r));
			// the iris: darker round its edge, a ring of paler flecks
			vec3 iris_c = mix(EYE_IRIS * 1.25, EYE_IRIS * 0.55, smoothstep(0.35, 1.0, ri));
			iris_c *= 0.9 + 0.2 * noise3(vec3(atan(ir.y, ir.x) * 3.0, ri * 4.0, 0.0));
			toon = mix(toon, iris_c, smoothstep(1.0 + aa / IRIS_SIZE, 1.0 - aa / IRIS_SIZE, ri));
			toon = mix(toon, EYE_IRIS * 0.3, smoothstep(0.8, 1.0, ri) * step(ri, 1.0) * 0.6);
			// the pupil
			vec2 pp = abs(ir / PUPIL);
			float rp = pow(pow(pp.x, PUPIL_SQUARE) + pow(pp.y, PUPIL_SQUARE), 1.0 / PUPIL_SQUARE);
			toon = mix(toon, vec3(0.012), smoothstep(1.0 + aa * 3.0, 1.0 - aa * 3.0, rp));
			// a bright highlight that stays put (up and towards the front), and a small one below it
			float hl = 1.0 - smoothstep(0.13 - aa, 0.13 + aa, length(vec2(fwd, upw) - vec2(0.28, 0.34)));
			hl = max(hl, 1.0 - smoothstep(0.06 - aa, 0.06 + aa, length(vec2(fwd, upw) - vec2(0.42, 0.12))));
			toon = mix(toon, vec3(1.0), hl);
			// a dark rim, so it reads from far off
			toon = mix(toon, vec3(0.02), smoothstep(0.84 - aa, 0.88 + aa, r));
			// the lids, the colour of its skin, a dark line along their edges
			float edge = max(1.0 - smoothstep(0.0, 0.07 + aa, abs(upw - top_edge)), 1.0 - smoothstep(0.0, 0.05 + aa, abs(upw - bottom_edge)));
			vec3 lid_c = back * 1.3;
			toon = mix(toon, lid_c * (0.9 + 0.2 * smoothstep(-1.0, 1.0, upw)), lid);
			toon = mix(toon, vec3(0.02), edge * step(0.0, 1.0 - r));
			c = mix(c, toon, clamp(cartoon_eyes, 0.0, 1.0));
			rough = mix(rough, 0.25, lid * cartoon_eyes);
		} else if (b > 0.0) {
			// (the eye as it is: no lids showing until it blinks)
			float top_r = mix(1.1, LID_MEET, b);
			float bottom_r = mix(-1.1, LID_MEET, b);
			float shut = max(smoothstep(top_r - aa, top_r + aa, upw), smoothstep(bottom_r + aa, bottom_r - aa, upw));
			c = mix(c, back * 1.3, shut);
			rough = mix(rough, 0.45, shut);
		}
	} else if (p == 3) {
		// The baleen: close-set plates hanging in a row, their inner edges frayed into a fringe of
		// bristles towards the bottom.
		float plate = 1.0 - smoothstep(0.15, 0.45 + plate_fw, abs(fract(plate_k) - 0.5)) * (1.0 - smoothstep(0.6, 1.2, plate_fw));
		float down = 1.0 - UV.y;
		vec3 bc = mix(baleen * mix(0.85, 1.25, noise3(vec3(m.z * 12.0, 0.0, 0.0))), baleen_pale, step(m.x, 0.0) * (1.0 - smoothstep(0.085, 0.1, s)));
		c = mix(bc * 0.6, bc, plate * 0.6 + 0.4);
		float hair = noise3(vec3(m.z * 60.0, m.y * 6.0, m.x * 60.0));
		c = mix(c, fringe * (0.8 + 0.3 * hair), smoothstep(0.55, 0.95, down) * (0.6 + 0.4 * hair));
		height = 0.004 * plate;
		rough = 0.6;
		spec = 0.25;
	} else if (p == 4) {
		// The mouth's wall: dark flesh, in soft folds, darker deep inside.
		float fold = noise3(m * vec3(1.2, 3.0, 1.2));
		c = mouth_wall * (0.7 + 0.5 * fold) * mix(0.5, 1.0, smoothstep(0.0, 0.6, extra.x));
		height = 0.03 * fold;
		rough = 0.45;
	} else {
		// The skin: dark grey-brown above, white beneath, the line between them waved; lopsided at
		// the head: the lower jaw white on its right side (-x) and dark on its left, the white
		// coming up higher on the right; a pale chevron on the back behind the head and a pale
		// blaze up the right side; close up, faint scars, fine flecks and wrinkles.
		float big = fbm3(m * 0.3);
		vec3 top = back * (0.85 + 0.3 * big);
		float edge = 0.43 + 0.08 * (noise3(m * 0.7) - 0.5);
		if (side_is < 0.0) {
			edge += 0.16 * smoothstep(0.27, 0.16, s);
		}
		float white = smoothstep(edge + 0.025, edge - 0.025, fb);
		if (p == 1 || p == 9) {
			// the lower jaw: all white on its right side; on its left dark but for its keel
			white = side_is < 0.0 ? 1.0 : smoothstep(0.22, 0.12, fb + 0.04 * (big - 0.5));
		} else if (p == 0 && side_is > 0.0) {
			// (on the left the upper jaw is dark down to its lip)
			white *= smoothstep(0.2, 0.235, s);
		}
		c = mix(top, belly * (0.95 + 0.08 * big), white);
		if (p == 0) {
			float a = abs(arc);
			float sm = s * LENGTH;
			// the right upper lip white at the front
			if (side_is < 0.0) {
				c = mix(c, belly * 0.92, smoothstep(0.42, 0.3, hh) * smoothstep(0.205, 0.18, s));
			}
			// the chevron: a pale V on the back, its point on the middle line behind the blowholes,
			// its arms sweeping back and down the sides (brighter on the right)
			float centre = 0.262 * LENGTH + 0.9 * a;
			float vee = exp(-pow((sm - centre) / (0.5 + 0.25 * a), 2.0)) * (1.0 - smoothstep(1.4, 2.6, a));
			vee *= (side_is < 0.0 ? 0.75 : 0.45) * (0.75 + 0.5 * noise3(m * 1.5));
			// the blaze: a pale swath sweeping up and back from behind the eye, on the right only
			float rise = 0.5 + 2.2 * (s - 0.22);
			float blaze = (side_is < 0.0 ? 1.0 : 0.0) * exp(-pow((fb - rise) / 0.05, 2.0)) * smoothstep(0.21, 0.24, s) * (1.0 - smoothstep(0.3, 0.36, s));
			c = mix(c, chevron * (0.9 + 0.2 * big), clamp(vee + 0.7 * blaze, 0.0, 1.0) * chevron_show * (1.0 - white));
		} else if (p == 7) {
			// a flipper: dark above, white beneath and along its leading edge
			vec3 flat_way = normalize(vec3(UV2.x, UV2.y, extra.y * 2.0 - 1.0));
			float under = smoothstep(0.15, -0.15, dot(rest_normal, flat_way));
			c = mix(top, fin_under, max(under, smoothstep(0.12, 0.0, UV.y) * 0.7));
		} else if (p == 6) {
			// the flukes: dark above, white beneath with a dark grey margin
			float under = smoothstep(0.15, -0.15, rest_normal.y);
			float margin = max(smoothstep(0.82, 0.97, UV.y), smoothstep(0.85, 1.0, UV.x));
			c = mix(top, mix(fin_under, top * 1.6, margin), under);
		} else if (p == 5) {
			c = top;
		}
		// scars: a few thin pale scratches; flecks and wrinkles to be seen close up
		float scratch = smoothstep(0.985, 1.0, 1.0 - abs(2.0 * noise3(m * vec3(0.6, 3.0, 0.9) + 5.0) - 1.0)) * smoothstep(0.62, 0.75, noise3(m * 0.4 + 9.0));
		c = mix(c, mix(c, belly, 0.45), scratch * (1.0 - smoothstep(0.01, 0.03, px)));
		vec2 fleck = cells(q / 0.06 + 77.0);
		c = mix(c, c * 1.25, (1.0 - smoothstep(0.1, 0.22, fleck.x)) * step(fleck.y, 0.25) * (1.0 - smoothstep(0.015, 0.03, px)) * 0.4);
		// (close up: the skin's soft wrinkles, running round the body, and a fine grain)
		float wrinkle = noise3(m * vec3(1.5, 1.5, 9.0)) * (1.0 - smoothstep(0.006, 0.02, px));
		height += 0.003 * (wrinkle - 0.5) + 0.0012 * (noise3(m * 35.0) - 0.5) * (1.0 - smoothstep(0.002, 0.006, px));
		rough = 0.4 + 0.12 * big;
		spec = 0.38;
		if (p <= 1 && PLEATS > 0.0) {
			// The pleats of the throat: grooves running along it from the chin back to the navel,
			// stretched open as it balloons.
			float zone = smoothstep(PLEAT_FROM, PLEAT_FROM + 0.025, s) * (1.0 - smoothstep(PLEAT_TO - 0.06, PLEAT_TO, s));
			zone *= (1.0 - smoothstep(PLEAT_TOP * 0.8, PLEAT_TOP, fb)) * (1.0 - inside);
			float d = abs(fract(pleat_k) - 0.5);
			float groove = smoothstep(0.32 - pleat_fw, 0.5, d);
			float show = zone * (1.0 - smoothstep(0.2, 0.45, pleat_fw));
			float stretched = clamp(gape, 0.0, 1.0) * (p == 1 ? 0.6 : extra.x);
			height -= groove * show * PLEAT_DEPTH * (1.0 - 0.7 * stretched);
			c = mix(c, mix(c * 0.55, vec3(0.78, 0.66, 0.64), stretched), groove * show);
		}
		if (p == 0) {
			// The two blowholes, side by side behind the splash guard, closing towards the front.
			float along = (s - BLOW_S) * LENGTH;
			float apart = abs(m.x) - BLOW_APART * (0.6 + 0.4 * clamp(along / BLOW_LONG + 0.5, 0.0, 1.0));
			float slit = 1.0 - smoothstep(0.75, 1.0, length(vec2(along / (0.5 * BLOW_LONG), apart / (0.09 * BLOW_LONG))));
			float lip_of = 1.0 - smoothstep(0.9, 1.6, length(vec2(along / (0.5 * BLOW_LONG), apart / (0.2 * BLOW_LONG))));
			c = mix(c, c * 0.8, lip_of * 0.5);
			c = mix(c, vec3(0.02), slit);
			height += (0.012 * lip_of - 0.05 * slit) * BLOW_LONG;
		}
		if (p <= 1) {
			// Inside the mouth: the roof (dark) and the floor and tongue.
			c = mix(c, (p == 0 ? mouth_roof : tongue) * (0.85 + 0.3 * noise3(m * 3.0)), inside);
			rough = mix(rough, 0.35, inside);
		}
	}
	NORMAL = bumped(NORMAL, VERTEX, height);
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
