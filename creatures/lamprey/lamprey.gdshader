shader_type spatial;
// The sea lamprey (lamprey.gd): it swims by a wave that runs the whole length of its body, as an
// eel does; its sucker folds shut into a slit and opens out round, its teeth showing; and every
// marking is drawn here (the component's README says what was used): no texture files. What each
// point is comes from the model (tools/build_lamprey.py): COLOR.r the part, as a tenth (0 body, 1
// sucker, 2 eye, 3 teeth, 4 nostril, 5 first dorsal, 6 second dorsal and tail, 7 the tail's lower
// lobe). On the body UV.x is how far along it (0 the front of the head to 1 the tail tip), UV.y how
// high (0 belly line to 1 back line), UV2.x how far round the skin from the back line (metres, +
// right, - left), UV2.y the whole way from back line to belly line. On the sucker UV.x is how far
// out from its middle (1 the rim) and UV2.x which part of it (0 throat, 1 inner face, 2 rim, 3
// outside). On a tooth UV.x is from its root (0) to its tip (1); on the nostril how far out from its
// middle. On a fin UV.x is from its root (0) to its edge (1), UV.y along it. Nothing here needs more
// than GL Compatibility has.
//
// Everything that moves runs on `phase` (0..1 through one beat, set by Lamprey): the body's waves go
// a whole number of times a beat, so a picture of it comes round again exactly.
render_mode cull_back, depth_draw_opaque;

// As the model is built: body lengths are of this many metres; the middle of the sucker's rim (how
// far along, how high, in body lengths) and the way its face looks (forward and down), and the way
// up across its face.
const float LENGTH = 0.7;
const float DISC_S = 0.024;
const float DISC_Y = -0.015;
const vec3 DISC_AXIS = vec3(0.0, -0.6, -0.8);
const vec3 DISC_V = vec3(0.0, 0.8, -0.6);
// How many body lengths one wave of the swimming bend is (a lamprey has more than one wave along it).
const float WAVE = 0.7;
// The gill openings: the first and the step between them (body lengths along), how far round the
// side (0 the back line, 1 the belly line), and how wide (metres, at scale 1).
const float PORE_FROM = 0.112;
const float PORE_STEP = 0.0158;
const float PORE_ROUND = 0.47;
const float PORE_SIZE = 0.0027;

uniform float phase = 0.0;
// How many waves run down its body in a beat (a whole number).
uniform float tail_beats = 2.0;
// How hard it swims: 1 swings its tail about a fifteenth of its length each way, its head a third
// of that.
uniform float sway = 0.8;
// The sucker: 0 folded shut into a slit, 1 open full and round, its teeth showing.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X). The head stays as it is.
uniform float curl = 0.0;

// Colours: the back, the side, the belly; the dark mottling over back and sides; the sucker's inner
// face, its rim, its throat; the teeth; the eye's ring; the fins.
uniform vec3 back : source_color = vec3(0.27, 0.24, 0.13);
uniform vec3 side : source_color = vec3(0.47, 0.41, 0.24);
uniform vec3 belly : source_color = vec3(0.8, 0.76, 0.62);
uniform vec3 mottle_colour : source_color = vec3(0.11, 0.1, 0.06);
uniform vec3 disc_face : source_color = vec3(0.82, 0.66, 0.54);
uniform vec3 disc_rim : source_color = vec3(0.86, 0.76, 0.62);
uniform vec3 throat : source_color = vec3(0.24, 0.07, 0.06);
uniform vec3 tooth : source_color = vec3(0.9, 0.72, 0.32);
uniform vec3 tooth_tip : source_color = vec3(0.5, 0.33, 0.12);
uniform vec3 eye_ring : source_color = vec3(0.5, 0.56, 0.56);
uniform vec3 fin_colour : source_color = vec3(0.5, 0.44, 0.27);
// How blotched the back and sides are, and the shine of its wet skin.
uniform float mottle = 1.0;
uniform float sheen = 0.35;
// The cartoon eye (the user, 2026-11-18: "the eyes for most of them should be more cartoony and
// personalized"): 0 the eye as the species has it, 1 the cartoon eye: much bigger, a pale glassy
// blue iris with a small pin of a pupil in plenty of white, no upper lid, and a lower lid pushed up
// into a hungry leer (a lamprey's vacant, hungry stare). `eye_look` slides the iris and pupil (x
// towards the snout, y up; -1..1); `blink` 0 open to 1 shut (the eye squashed flat, the lid down).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The right eye's middle (metres) and the way it looks out (the build prints the EYE line); the cartoon
// eye's width, how far it bulges and stands out, how far the iris slides, its size, the pupil's, its
// colour, and the lower lid's line (x towards the snout, y up, 1 the eye's rim).
const vec3 EYE_MIDDLE = vec3(0.01473, 0.00684, -0.30078);
const vec3 EYE_OUT = vec3(0.9342, 0.3532, -0.0494);
const float EYE_GROW = 1.6;
const float EYE_BULGE = 1.3;
const float EYE_PUSH = 0.003;
const float IRIS_TRAVEL = 0.3;
const float IRIS_R = 0.5;
const float PUPIL_R = 0.16;
const vec3 IRIS = vec3(0.56, 0.72, 0.8);
const float LOW_LID_Y = -0.58;
const float LOW_LID_SLANT = -0.22;

varying vec3 rest;
varying float part;


vec4 hash4(vec2 p) {
	vec4 q = fract(p.xyxy * vec4(0.1031, 0.1030, 0.0973, 0.1099));
	q += dot(q, q.wzxy + 33.33);
	return fract((q.xxyz + q.yzzw) * q.zywx);
}


float cloud(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash4(i).x, hash4(i + vec2(1.0, 0.0)).x, f.x), mix(hash4(i + vec2(0.0, 1.0)).x, hash4(i + vec2(1.0, 1.0)).x, f.x), f.y);
}


void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.3 * LENGTH;
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


void vertex() {
	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float open = clamp(gape, 0.0, 1.0);
	float tail = phase * TAU * tail_beats;
	if (part == 2.0 && (cartoon_eyes > 0.0 || blink > 0.0)) {
		// The eye: bigger and prouder as a cartoon eye, squashed flat to blink.
		vec3 mid = EYE_MIDDLE;
		vec3 o = EYE_OUT;
		if (v.x < 0.0) {
			mid.x = -mid.x;
			o.x = -o.x;
		}
		vec3 up = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
		float wide = mix(1.0, EYE_GROW, cartoon_eyes);
		float proud = mix(1.0, EYE_BULGE, cartoon_eyes);
		float shut = 1.0 - 0.8 * clamp(blink, 0.0, 1.0);
		vec3 d = v - mid;
		float d_out = dot(d, o);
		vec3 flat_d = d - o * d_out;
		float d_up = dot(flat_d, up);
		v = mid + o * (d_out * proud + EYE_PUSH * cartoon_eyes) + (flat_d - up * d_up) * wide + up * (d_up * wide * shut);
		float n_out = dot(n, o);
		vec3 n_flat = n - o * n_out;
		float n_up = dot(n_flat, up);
		n = o * (n_out / proud) + (n_flat - up * n_up) / wide + up * (n_up / (wide * shut));
	}
	if (part == 1.0 || part == 3.0) {
		// The sucker (and its teeth) fold shut: narrowed from side to side to a slit, a little
		// shorter up and down, and drawn back into the head.
		vec3 axis = normalize(DISC_AXIS);
		vec3 up = normalize(DISC_V);
		vec3 centre = vec3(0.0, DISC_Y, DISC_S - 0.5) * LENGTH;
		float kx = mix(0.1, 1.0, open);
		float kv = mix(0.72, 1.0, open);
		vec3 d = v - centre;
		float dv = dot(d, up);
		float da = dot(d, axis);
		v = centre + vec3(d.x * kx, 0.0, 0.0) + up * (dv * kv) + axis * (da - (1.0 - open) * 0.009 * LENGTH);
		n = vec3(n.x / kx, 0.0, 0.0) + up * (dot(n, up) / kv) + axis * dot(n, axis);
	} else if (part >= 5.0) {
		// The fins ripple a little behind the bend that carries them.
		float s = v.z / LENGTH + 0.5;
		v.x += LENGTH * 0.006 * sway * UV.x * UV.x * sin(tail - TAU * s / WAVE - 0.8);
	}
	// The swimming bend: a wave that runs from head to tail along the whole body, small at the head
	// and growing to the tail; each place carried sideways and turned to lie along the bent body.
	float sb = clamp(v.z / LENGTH + 0.5, 0.0, 1.02);
	float reach = 0.022 + 0.048 * sb;
	float w = tail - TAU * sb / WAVE;
	float off = LENGTH * sway * reach * sin(w);
	float slope = sway * (0.048 * sin(w) - reach * TAU / WAVE * cos(w));
	vec3 along = normalize(vec3(slope, 0.0, 1.0));
	vec3 across = vec3(along.z, 0.0, -along.x);
	v = vec3(off, v.y, v.z) + across * v.x;
	n = across * n.x + vec3(0.0, n.y, 0.0) + along * n.z;
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = normalize(n);
}


// The cartoon eye's colour at `e` on its face (x towards the snout, y up, 1 at its rim), `nv` the
// way it faces (view space): white round a pale glassy iris, a small pin of a pupil, a highlight that
// stays towards the light (where the dome faces it), a dark outline.
vec3 cartoon_eye(vec2 e, vec3 nv) {
	float r = length(e);
	vec2 q = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * IRIS_TRAVEL;
	float ri = length(q);
	vec3 c = vec3(0.95, 0.95, 0.9);
	vec3 iris = mix(IRIS * 1.15, IRIS * 0.62, smoothstep(0.05, IRIS_R, ri));
	iris = mix(iris, vec3(0.1, 0.16, 0.2), smoothstep(IRIS_R - 0.08, IRIS_R - 0.01, ri));
	c = mix(c, iris, 1.0 - smoothstep(IRIS_R - 0.02, IRIS_R + 0.02, ri));
	c = mix(c, vec3(0.01), 1.0 - smoothstep(PUPIL_R - 0.02, PUPIL_R + 0.02, ri));
	vec3 light = normalize(vec3(-0.3, 0.35, 0.9));
	c = mix(c, vec3(1.0), smoothstep(0.986, 0.99, dot(nv, light)));
	return mix(c, vec3(0.03, 0.03, 0.025), smoothstep(0.68, 0.73, r));
}


// The lids over an eye (`c` its colour, at `e` on its face): the cartoon eye's lower lid pushed up, with
// a dark line along its edge (none on the eye as the species has it); the upper lid comes down to blink.
vec3 eye_lid(vec2 e, vec3 c, vec3 lid_c) {
	float shut = clamp(blink, 0.0, 1.0);
	float low_line = mix(-1.1, LOW_LID_Y + LOW_LID_SLANT * e.x, cartoon_eyes);
	float line = mix(1.1, low_line - 0.02, shut);
	float on = max(cartoon_eyes, step(0.001, shut));
	c = mix(c, vec3(0.03, 0.03, 0.025), (1.0 - smoothstep(0.0, 0.1, line - e.y)) * smoothstep(-1.0, -0.6, line) * step(0.001, shut));
	c = mix(c, vec3(0.03, 0.03, 0.025), (1.0 - smoothstep(0.0, 0.1, e.y - low_line)) * smoothstep(-1.0, -0.6, low_line) * on);
	c = mix(c, lid_c, smoothstep(line - 0.01, line + 0.01, e.y));
	return mix(c, lid_c, 1.0 - smoothstep(low_line - 0.01, low_line + 0.01, e.y));
}


// The colour of the skin at a place: `h` up (0 belly line to 1 back line), `p` where (metres).
vec3 skin(float h, vec2 p) {
	vec3 c = mix(belly, side, smoothstep(0.1, 0.42, h));
	c = mix(c, back, smoothstep(0.55, 0.92, h));
	if (mottle > 0.0) {
		// dark blotches over the back and sides, broken and uneven
		// (the patches' edges wander, so that they are marbled rather than blocky)
		vec2 q = p / 0.022 + 3.1 + 0.6 * vec2(cloud(p / 0.009), cloud(p / 0.009 + 5.3));
		float m = 0.65 * cloud(q) + 0.35 * cloud(p / 0.008 + 11.7);
		c = mix(c, mottle_colour, mottle * 0.75 * smoothstep(0.5, 0.66, m) * smoothstep(0.25, 0.55, h));
	}
	// (a fine grain; laid by height, not by the way round, which jumps where the two sides meet
	// along the belly)
	c *= 0.93 + 0.14 * cloud(vec2(rest.z, rest.y) / 0.004);
	return c;
}


void fragment() {
	vec3 c = side;
	float rough = 0.32;
	float glint = sheen;
	float seen = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	if (part < 0.5) {
		float s = UV.x;
		float h = UV.y;
		vec2 p = vec2(rest.z, UV2.x);
		c = skin(h, p);
		// The seven gill openings in a row behind each eye: dark round holes, each in a pale rim.
		float round_it = abs(UV2.x) / max(UV2.y, 0.001);
		float k = clamp(floor((s - PORE_FROM) / PORE_STEP + 0.5), 0.0, 6.0);
		vec2 d = vec2((s - PORE_FROM - k * PORE_STEP) * LENGTH, (round_it - PORE_ROUND) * UV2.y);
		float r = length(d) / PORE_SIZE;
		c = mix(c, mix(c, belly, 0.55), 1.0 - smoothstep(0.85, 1.15, r));
		c = mix(c, vec3(0.04, 0.03, 0.03), 1.0 - smoothstep(0.5, 0.68, r));
		glint *= smoothstep(0.5, 0.8, r);
		// (the head's skin behind the sucker's throat is seen down the throat while the sucker
		// draws back into the head as it shuts: it is the throat's colour there)
		vec3 axis = normalize(DISC_AXIS);
		vec3 from_disc = rest - vec3(0.0, DISC_Y, DISC_S - 0.5) * LENGTH;
		float down_axis = dot(from_disc, axis);
		float off_axis = length(from_disc - axis * down_axis);
		c = mix(c, throat, (1.0 - smoothstep(0.006, 0.008, off_axis / LENGTH)) * step(-0.04, down_axis / LENGTH));
	} else if (part < 1.5) {
		// The sucker: the throat dark, the inner face pale flesh with faint lines out to the rim, the
		// fringed rim paler, the outside the colour of the head.
		float region = UV2.x;
		vec3 outside = mix(belly, side, 0.6);
		c = mix(throat, disc_face, smoothstep(0.3, 0.9, region));
		c *= 1.0 - 0.12 * smoothstep(0.5, 1.0, region) * (1.0 - smoothstep(1.0, 1.5, region)) * smoothstep(0.6, 1.0, abs(sin(UV.y * TAU * 36.0)));
		c = mix(c, disc_rim, smoothstep(1.4, 2.0, region));
		c = mix(c, outside, smoothstep(2.3, 3.0, region));
		rough = 0.5;
		glint *= 0.5;
	} else if (part < 2.5) {
		// An eye: a dark pupil in a silvery ring.
		vec2 on_eye = UV * 2.0 - 1.0;
		float r = length(on_eye);
		c = mix(eye_ring, eye_ring * 0.4, smoothstep(0.45, 0.62, r));
		c = mix(c, vec3(0.03), smoothstep(0.62, 0.72, r));
		c = mix(c, vec3(0.01), 1.0 - smoothstep(0.34, 0.4, r));
		if (cartoon_eyes > 0.0 || blink > 0.0) {
			vec2 e = vec2(on_eye.y, on_eye.x);
			c = mix(c, cartoon_eye(e, normalize(NORMAL)), cartoon_eyes);
			c = eye_lid(e, c, mix(side, back, 0.4));
		}
		rough = 0.06;
		glint = 0.0;
	} else if (part < 3.5) {
		// A tooth: horny yellow, browner to its tip.
		c = mix(tooth, tooth_tip, smoothstep(0.4, 1.0, UV.x));
		rough = 0.25;
		glint *= 0.3;
	} else if (part < 4.5) {
		// The nostril: a short tube the colour of the head, open dark at its tip.
		c = mix(vec3(0.03), side * 0.85, smoothstep(0.38, 0.6, UV.x));
		glint *= 0.5;
	} else {
		// A fin: thin, the body's colour, darker towards its edge, with faint lines.
		float r = UV.x;
		float lines = smoothstep(0.6, 1.0, abs(fract(UV.y) - 0.5) * 2.0) * smoothstep(0.1, 0.4, r);
		c = mix(side, fin_colour, smoothstep(0.0, 0.3, r));
		c = mix(c, mottle_colour, 0.35 * smoothstep(0.65, 1.0, r));
		c *= 1.0 - 0.12 * lines;
		rough = 0.45;
		glint *= 0.5;
	}
	float aslant = pow(1.0 - seen, 3.0);
	c += vec3(0.9, 0.95, 0.85) * glint * aslant;
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.5;
}
