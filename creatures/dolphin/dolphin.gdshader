shader_type spatial;
// The bottlenose dolphin (dolphin.gd): every marking drawn here (no texture files), its swimming
// and its mouth. What each point is comes from the model (tools/build_dolphin.py): UV2.y the part
// (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower tooth, 4 the flukes, 5 the dorsal fin, 6 a
// flipper, 7 an eye); UV2.x, on the body and the jaw, how much it is inside the mouth. UV, on the
// body and jaw: x how far along, y how high on its side (1 the ridge of the back, 0 the keel of
// the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye:
// x middle (0) to rim (1).
//
// It swims as whales and dolphins do: its flukes beat UP AND DOWN. A wave runs back along the
// body, all but nothing at the flippers and growing down the tail stock, and the flukes pitch
// about their root as one stiff plate. All of it is a function of `phase` alone, so a picture of
// it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 2.8;
const float HALF = 1.4;
// Where the flukes are hinged (metres behind the tip of the jaw): behind it they are one stiff plate.
const float JOINT = 2.5;
// The corner of the mouth, where the lower jaw hinges (metres behind the tip, metres up), and how
// far behind it the jaw runs on inside the body.
const float CORNER = 0.30;
const float HINGE_Y = -0.0318;
const float JAW_TAIL = 0.065;
const float BLOWHOLE = 0.41;
const vec2 EYE_AT = vec2(0.368, -0.004);
// How far the lower jaw swings down for `gape` 1 (radians), and how far the flukes' root rises and
// falls for `sway` 1 (of its length).
const float GAPE_MAX = 0.62;
const float REACH = 0.06;
// (TAU is Godot's own constant)

// How far through a beat of its flukes (0..1, it wraps). Set by Dolphin.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// flippers to the flukes (0 straight; more than 0 the tail comes round to +X, as the fish's does).
uniform float curl = 0.0;
// The same up and down, about its middle, in radians from the tip of its beak to its flukes (0
// straight; more than 0 its head and its flukes both come up; less than 0 both go down, its back
// arched: the top of a leap, the start of a dive).
uniform float arch = 0.0;
// How widely it beats, for 1 as a dolphin cruising (its fluke tips rise and fall about 0.25 m).
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.05;

// The cape (the dark back, from the blowhole to the tail), the flank, the belly.
uniform vec3 cape : source_color = vec3(0.12, 0.14, 0.17);
uniform vec3 flank : source_color = vec3(0.38, 0.42, 0.47);
uniform vec3 belly : source_color = vec3(0.9, 0.82, 0.8);
// The fins; the inside of the mouth; the teeth.
uniform vec3 fin : source_color = vec3(0.1, 0.115, 0.14);
uniform vec3 mouth : source_color = vec3(0.62, 0.3, 0.3);
uniform vec3 tooth : source_color = vec3(0.93, 0.9, 0.8);
// How strongly the pale scratches (tooth rakes from other dolphins) show on its sides.
uniform float rakes = 0.35;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float inside;

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

// How far up the middle line of the body is, `xm` metres behind the tip: a wave that runs back
// along it, least at the flippers, large only down the tail stock.
float lift_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * REACH * (0.07 - 0.3 * s + 0.33 * s * s + 0.9 * s * s * s * s);
	return sway * reach * sin(TAU * (phase - s / wave));
}

// The body behind the head laid round an arc to one side (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2 * LENGTH;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.7 * LENGTH);
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

void vertex() {
	part = UV2.y;
	inside = UV2.x;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	if (p == 1 || p == 3) {
		// The lower jaw (and its teeth) swings down about the corner of the mouth; behind the
		// corner, inside the body, it stays.
		float a = GAPE_MAX * clamp(gape, 0.0, 1.0) * smoothstep(CORNER + 0.01, CORNER - 0.035, v.z + HALF);
		vec2 hinge = vec2(HINGE_Y, CORNER - HALF);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	float xm = v.z + HALF;
	// (the flukes, behind their hinge, are one stiff plate: they turn about the hinge)
	float zc = min(xm, JOINT);
	float h = lift_at(zc);
	float slope = (lift_at(zc + 0.01) - lift_at(zc - 0.01)) / 0.02;
	// (the flukes pitch a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.35 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec2 o = vec2(v.y, xm - zc);
	v = vec3(v.x, h + o.x * c + o.y * sn, zc - HALF - o.x * sn + o.y * c);
	n = vec3(n.x, n.y * c + n.z * sn, -n.y * sn + n.z * c);
	arch_bend(v, n);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The line of the mouth, as the model has it.
float mouth_y(float xm) {
	return -0.049 - 0.06 * xm + 0.036 * smoothstep(0.19, 0.31, xm);
}

// The skin of the body at a place: `xm` behind the tip, `y` up, `h` how high on its side (0..1).
vec3 skin(float xm, float y, float h, float side) {
	float grain = noise2(vec2(xm * 90.0, h * 40.0 + side * 9.0));
	float cloud = noise2(vec2(xm * 7.0, h * 5.0) + 3.0 + side * 5.0);
	// The belly pinkish white, the flank grey, the cape dark: from the blowhole it widens to its
	// lowest under the dorsal fin and narrows again down the tail stock.
	float edge = mix(0.74, 0.5, smoothstep(0.35, 1.3, xm)) + 0.2 * smoothstep(1.5, 2.4, xm) + (cloud - 0.5) * 0.06;
	vec3 c = mix(belly, flank, smoothstep(0.2, 0.46, h + (cloud - 0.5) * 0.08));
	// (the tail stock is grey all round)
	c = mix(c, flank * 0.85, smoothstep(2.0, 2.45, xm) * (1.0 - smoothstep(0.2, 0.46, h)));
	c = mix(c, cape, smoothstep(edge - 0.1, edge + 0.07, h));
	// (the beak is dark on top, the melon a shade paler than the cape)
	c = mix(c, cape * 1.15, (1.0 - smoothstep(0.12, 0.2, xm)) * smoothstep(0.45, 0.6, h));
	c *= 0.94 + 0.12 * grain;
	// The scratches other dolphins' teeth leave: pale sets of parallel lines here and there.
	vec2 at = vec2(xm * 3.2, h * 2.6 + side * 3.7);
	vec2 cell = floor(at);
	float turn = hash2(cell) * TAU;
	vec2 in_cell = fract(at) - 0.5;
	float along = in_cell.x * cos(turn) + in_cell.y * sin(turn);
	float across = -in_cell.x * sin(turn) + in_cell.y * cos(turn);
	float lines = smoothstep(0.75, 0.95, cos(across * 150.0)) * (1.0 - smoothstep(0.02, 0.05, abs(across))) * (1.0 - smoothstep(0.1, 0.32, abs(along)));
	c = mix(c, flank * 1.5, lines * rakes * step(0.55, hash2(cell + 7.0)) * smoothstep(0.3, 0.5, h) * smoothstep(0.4, 0.6, xm));
	return c;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.34;
	float spec = 0.5;
	float xm = rest.z + HALF;
	float side = rest.x >= 0.0 ? 1.0 : -1.0;
	if (p == 0 || p == 1) {
		float y = rest.y;
		c = skin(xm, y, UV.y, side);
		if (p == 0) {
			// The crease where the melon rises from the beak.
			c = mix(c, c * 0.55, (1.0 - smoothstep(0.0, 0.012, abs(xm - 0.132))) * smoothstep(0.55, 0.75, UV.y) * 0.6);
			// The blowhole: a dark crescent on top of the head, open to the front.
			vec2 b = vec2(rest.x, xm - BLOWHOLE);
			float ring = 1.0 - smoothstep(0.003, 0.006, abs(length(b) - 0.011));
			c = mix(c, vec3(0.015, 0.016, 0.02), max(ring * smoothstep(-0.004, 0.004, b.y), 1.0 - smoothstep(0.004, 0.008, length(b - vec2(0.0, 0.004)))) * step(0.0, y));
			// The eye's dark surround, and the dark line from it towards the flipper.
			vec2 e = vec2(xm - EYE_AT.x, y - EYE_AT.y);
			c = mix(c, cape * 0.7, (1.0 - smoothstep(0.016, 0.04, length(e * vec2(0.8, 1.2)))) * 0.8);
			float stripe = (1.0 - smoothstep(0.006, 0.02, abs(e.y + 0.3 * e.x - 0.9 * e.x * e.x))) * smoothstep(0.0, 0.04, e.x) * (1.0 - smoothstep(0.12, 0.26, e.x));
			c = mix(c, cape, stripe * 0.45);
			// The upper lip: a dark line along the mouth.
			float lip = (1.0 - smoothstep(0.0, 0.006, y - mouth_y(xm))) * (1.0 - smoothstep(CORNER - 0.01, CORNER + 0.004, xm));
			c = mix(c, c * 0.5, lip * 0.7 * (1.0 - inside));
		} else {
			// The lower jaw: pale, greyer towards its tip and along its lip.
			c = mix(c, flank, 0.55 * (1.0 - smoothstep(0.0, 0.09, xm)));
			float lip = 1.0 - smoothstep(0.0, 0.007, mouth_y(min(xm, CORNER)) - y);
			c = mix(c, flank * 0.7, lip * 0.6 * (1.0 - inside));
		}
		// The inside of the mouth: pink, darker towards the throat.
		vec3 in_mouth = mix(mouth, mouth * 0.3, smoothstep(0.1, CORNER + 0.02, xm));
		// (behind the corner, where the roof falls to the belly over the back of the jaw, it is
		// skin coloured: only a hair of it ever shows, between the two, from below)
		c = mix(c, in_mouth, smoothstep(0.1, 0.6, inside) * (1.0 - smoothstep(CORNER + 0.012, CORNER + 0.03, xm)));
		rough = mix(rough, 0.5, inside);
	} else if (p == 2 || p == 3) {
		// A tooth: ivory, darker at the gum.
		c = mix(tooth * 0.7, tooth, smoothstep(0.1, 0.5, UV.x));
		rough = 0.3;
	} else if (p == 4) {
		// The flukes: dark above, grey below, a paler trailing edge.
		c = mix(flank * 0.8, fin, smoothstep(-0.2, 0.2, rest_normal.y));
		c = mix(c, c * 1.35, smoothstep(0.85, 1.0, UV.y) * 0.5);
		c *= 0.95 + 0.1 * noise2(vec2(rest.x, rest.z) * 60.0);
	} else if (p == 5) {
		// The dorsal fin: dark, a shade paler in its middle.
		c = mix(fin, cape * 1.3, 0.5 * smoothstep(0.1, 0.5, UV.y) * (1.0 - smoothstep(0.5, 0.95, UV.y)) * (1.0 - UV.x));
		c *= 0.95 + 0.1 * noise2(rest.yz * 60.0);
	} else if (p == 6) {
		// A flipper: dark above, paler below and at its root.
		c = mix(flank, fin, smoothstep(-0.2, 0.2, rest_normal.y));
		c = mix(c, flank, (1.0 - smoothstep(0.0, 0.25, UV.x)) * 0.5);
	} else {
		// An eye: dark brown, all but black, with a dark lid round it.
		float r = UV.x;
		c = mix(vec3(0.02, 0.014, 0.01), vec3(0.09, 0.055, 0.03), smoothstep(0.35, 0.7, r));
		c = mix(c, cape * 0.6, smoothstep(0.8, 1.0, r));
		rough = 0.12;
		spec = 0.7;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
