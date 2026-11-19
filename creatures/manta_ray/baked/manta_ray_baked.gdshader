shader_type spatial;
// The giant oceanic manta ray (manta_ray.gd): every marking drawn here (no texture files), and
// everything that moves. What each point is comes from the model (tools/build_manta_ray.py): UV2.y
// the part (0 skin, 1 inside the mouth, 2 a cephalic fin, 3 the tail, 4 the dorsal fin, 5 a tail
// spine, 6 an eye). On the skin and in the mouth: UV.x the lower jaw's weight, UV.y from the
// leading edge (0) to the trailing edge (1), UV2.x +1 on top, -1 beneath, 0 along the edges. On a
// cephalic fin: UV.x root (0) to tip (1), UV.y metres across from its top edge, UV2.x metres off
// the middle of its sheet (+ its inner skin). On the tail: UV.x root to tip. On an eye: UV.x
// middle (0) to rim (1).
//
// It flies: each wing is bent upward and downward as a wave that runs out from its root to its
// tip, the tip lagging and curling; the back edge lags the front; the body pitches and rides up
// and down a little against the wings; the tail trails with a late wave of its own. All of it is
// a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
// (The vertex half below is the same in GameCommon's manta-ray, devil-ray and spotted-eagle-ray
// but for these numbers: improve one, copy it to the others.)
render_mode cull_back, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// Kept in step with the model (the builder prints them: its SHADER line).
const float HALF = 2.5;
const float DISC = 2.2;
const float TAIL_LENGTH = 1.5;
// The lower jaw's hinge (y, z) and how far it turns at `gape` 1 (radians).
const vec2 HINGE = vec2(-0.2012, -0.6);
const float JAW_TURN = 0.55;
// The cephalic fins (the one on +X; the other is its mirror).
const vec3 CEPH_ROOT = vec3(0.5, 0.035, -0.96);
const vec3 CEPH_ALONG = vec3(0.04969, -0.09938, -0.99381);
const vec3 CEPH_DOWN = vec3(-0.12429, -0.98792, 0.09258);
const vec3 CEPH_IN = vec3(-0.99100, 0.11892, -0.06144);
const float CEPH_LENGTH = 0.58;
const float CEPH_WIDTH = 0.30;
const float CEPH_ROLL0 = 11.0;
const float CEPH_ROLL1 = 18.0;
const float CEPH_CUP = 2.6;
// How far out along a wing (0 the middle line, 1 the tip) the wing starts to bend.
const float ROOT = 0.13;
// How far the wing is bent at its tip at the top of a stroke (radians), how much higher it goes
// than it comes down, how far the tip lags the root and the back edge the front (parts of a beat).
const float FLAP = 0.62;
const float LIFT = 0.1;
const float TIP_LAG = 0.24;
const float BACK_LAG = 0.1;
// How far the body pitches (radians) and rides up and down (metres) at `sway` 1.
const float PITCH = 0.045;
const float HEAVE = 0.07;

// How far through a beat of its wings (0..1, it wraps). Set by MantaRay.
uniform float phase = 0.0;
// How widely it beats: 1 cruising, 0 gliding with its wings held still.
uniform float sway = 1.0;
// Turning: more than 0 it banks into a turn towards +X (as the fish's `curl`, whose tails come
// round to +X). At `curl` c: the whole animal is rolled 0.6 c radians about its long axis, its +X
// side down; the +X wing (inside the turn) droops a further 0.35 c radians by its tip and the
// other lifts 0.35 c; the tail trails round to +X, c radians by its tip.
uniform float curl = 0.0;
// The mouth: 0 shut, 1 wide open, as it is held when it feeds.
uniform float gape = 0.0;
// The cephalic fins: 0 rolled up into horns, 1 unrolled into scoops beside the mouth.
uniform float scoops = 0.0;

// The back; the blue-grey it glances; the pale shoulder marks; the belly; its dark spots and
// the grey of its rear edge; the inside of the mouth.
uniform vec3 back : source_color = vec3(0.022, 0.024, 0.03);
uniform vec3 back_sheen : source_color = vec3(0.1, 0.13, 0.18);
uniform vec3 shoulder : source_color = vec3(0.74, 0.76, 0.78);
uniform vec3 belly : source_color = vec3(0.93, 0.93, 0.91);
uniform vec3 belly_dark : source_color = vec3(0.07, 0.07, 0.085);
uniform vec3 mouth_inside : source_color = vec3(0.06, 0.03, 0.04);
// How strongly the shoulder marks and the belly's spots show.
uniform float shoulder_show = 1.0;
uniform float spots_show = 1.0;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float topness;

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

// A point of a cephalic fin and the way its skin faces: `t` along it, `h` metres across from its
// top edge, `off` metres off the middle of its sheet; `sx` which side. The sheet is curled across
// its width: tightly, more so towards its free edge, when rolled (a spiral, the horn); gently
// when spread (the scoop).
void ceph_point(float t, float h, float off, float sx, out vec3 p, out vec3 n) {
	float open = clamp(scoops, 0.0, 1.0);
	float k0 = mix(CEPH_ROLL0, CEPH_CUP, open);
	float k1 = CEPH_ROLL1 * (1.0 - open) / (2.0 * CEPH_WIDTH);
	vec2 q = vec2(0.0);
	float dh = h / 12.0;
	for (int i = 0; i < 12; i++) {
		float hm = (float(i) + 0.5) * dh;
		float th = k0 * hm + k1 * hm * hm;
		q += vec2(cos(th), sin(th)) * dh;
	}
	float th = k0 * h + k1 * h * h;
	vec3 flip = vec3(sx, 1.0, 1.0);
	vec3 normal = (CEPH_IN * cos(th) - CEPH_DOWN * sin(th)) * flip;
	p = (CEPH_ROOT + CEPH_ALONG * (t * CEPH_LENGTH) + CEPH_DOWN * q.x + CEPH_IN * q.y) * flip + normal * off;
	n = normal * (off >= 0.0 ? 1.0 : -1.0);
}

// How far a wing is bent upward (radians) `e` of the way from where it starts to bend (0) to its
// tip (1), for a point `back_part` of a beat behind the front edge; `side` +1 the +X wing.
float wing_angle(float e, float back_part, float side) {
	float beat = 6.2831853 * (phase - TIP_LAG * e - back_part);
	float bend = pow(e, 1.15);
	// (the tip curls on past the rest of the wing, later still)
	float tip = 0.45 * pow(e, 4.0) * sin(beat - 0.9);
	return sway * (FLAP * (bend * sin(beat) + tip) + LIFT * bend) - side * 0.35 * curl * bend;
}

// THE CARTOON EYE (`cartoon_eyes` 1; 0 is the eye as it was) and the lids that `blink` closes.
// The manta's: a gentle giant. A big soft dark eye with little white and a large round pupil, a calm
// lid above and the lower lid raised a little, as in a smile.
// Where the eye is on the model (its middle on the skin, the way it faces, its radius: printed by
// the builder), how much bigger the cartoon eye is, and how far its rim is sunk into the skin to
// meet it (in radii, per unit of growth).
const vec3 EYE_AT = vec3(0.50000, 0.03500, -1.02500);
const vec3 EYE_OUT = vec3(0.84122, 0.12618, -0.52576);
const float EYE_RADIUS = 0.034;
const float EYE_GROW = 1.5;
const float EYE_SINK = 0.0;
// Its shape, in the eye's own plane (x towards the nose, y up, 1 its rim): the iris's radius;
// the upper lid's edge at rest, how it slopes (lower towards the nose for more than 0) and how
// it arches; the lower lid's edge at rest; how far the iris slides for `eye_look` 1.
const float IRIS = 0.72;
const float LID = 0.72;
const float LID_SLOPE = 0.0;
const float LID_ARCH = 0.08;
const float LOWER_LID = -0.55;
const float LOOK = 0.22;

// 0 the eye as it was, 1 the cartoon eye.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where it looks (-1..1 each): x towards its nose (+) or tail, y up (+) or down.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: a lid of the skin's colour closes over the eye.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// The cartoon eye's white, its iris, and its outline.
uniform vec3 eye_white : source_color = vec3(0.92, 0.92, 0.9);
uniform vec3 eye_iris : source_color = vec3(0.3, 0.19, 0.12);
uniform vec3 eye_line : source_color = vec3(0.02, 0.02, 0.03);

// The eye a point (at rest) belongs to: its middle `c`, the way it faces `o`, and its own
// "forward" (towards the nose) `f` and "up" `u`.
void eye_frame(vec3 p, out vec3 c, out vec3 o, out vec3 f, out vec3 u) {
	float sx = p.x >= 0.0 ? 1.0 : -1.0;
	c = vec3(EYE_AT.x * sx, EYE_AT.yz);
	o = normalize(vec3(EYE_OUT.x * sx, EYE_OUT.yz));
	vec3 up = vec3(0.0, 1.0, 0.0);
	f = vec3(0.0, 0.0, -1.0);
	f = normalize(f - o * dot(f, o));
	u = normalize(up - o * dot(up, o) - f * dot(up, f));
}

// The cartoon eye's pupil, `q` in the iris's own measure (1 its edge): 1 inside it.
float pupil_of(vec2 q) {
	return 1.0 - smoothstep(0.58, 0.64, length(q));
}

// The colour of the eye at rest point `p` (`r` from its middle, 0, to its rim, 1), the old eye's
// colour `plain` and the skin's colour round it `lid`; `glint` comes back for EMISSION and `shut`
// for how much of it a lid covers. (Its coordinates go by `r` and the way round from its middle, so
// that the eye is drawn round on the round cartoon eye: see eye_grow.)
vec3 eye_colour(vec3 p, float r, vec3 plain, vec3 lid, out float glint, out float shut) {
	vec3 c0;
	vec3 o;
	vec3 f;
	vec3 u;
	eye_frame(p, c0, o, f, u);
	vec2 e = vec2(dot(p - c0, f), dot(p - c0, u));
	e = length(e) > 1e-7 ? normalize(e) * r : vec2(0.0);
	float t = cartoon_eyes;
	glint = 0.0;
	// The cartoon eye: a white, an iris that slides with `eye_look`, its pupil, a highlight that
	// stays put (towards the light above and ahead), a dark outline.
	vec2 at = clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK;
	vec2 q = (e - at) / IRIS;
	float iq = length(q);
	vec3 toon = eye_white * (1.0 - 0.18 * smoothstep(0.35, 0.95, r));
	vec3 ring = eye_iris * (0.55 + 0.6 * (1.0 - iq)) * (0.9 + 0.2 * noise2(q * 9.0));
	ring = mix(ring, eye_line, smoothstep(0.8, 1.0, iq) * 0.7);
	toon = mix(toon, ring, 1.0 - smoothstep(0.96, 1.04, iq));
	toon = mix(toon, vec3(0.012, 0.01, 0.014), pupil_of(q));
	float shine = 1.0 - smoothstep(0.13, 0.17, length(e - vec2(0.3, 0.36)));
	shine = max(shine, 1.0 - smoothstep(0.05, 0.08, length(e - vec2(-0.12, -0.3))));
	toon = mix(toon, vec3(1.0), shine);
	toon = mix(toon, eye_line, smoothstep(0.8, 0.88, r));
	vec3 c = mix(plain, toon, t);
	glint = shine * t;
	// The lids: at rest only the cartoon eye's; `blink` brings the upper one down to the lower.
	float top = mix(1.4, LID - LID_SLOPE * e.x + LID_ARCH * (1.0 - e.x * e.x), t);
	float bottom = mix(-1.4, LOWER_LID, t);
	top = mix(top, bottom, blink);
	float edge = 0.06 + 0.04 * t;
	float covered = max(smoothstep(top - 0.02, top + 0.02, e.y), 1.0 - smoothstep(bottom - 0.02, bottom + 0.02, e.y));
	float rim = max(1.0 - smoothstep(edge * 0.5, edge, abs(e.y - top)), (1.0 - smoothstep(edge * 0.5, edge, abs(e.y - bottom))) * t);
	rim *= step(-0.2, top - bottom) * max(t, blink) * (1.0 - smoothstep(0.86, 0.98, r));
	c = mix(c, lid, covered);
	c = mix(c, eye_line, rim);
	glint *= 1.0 - covered;
	shut = covered;
	return c;
}

// The cartoon eye: made round (each point `r` of the way from its middle to its rim, on a circle in
// the eye's own plane, however the dome was laid on the skin), grown about its middle, its rim
// sunk into the skin round it.
vec3 eye_grow(vec3 v, float r) {
	if (cartoon_eyes <= 0.0) {
		return v;
	}
	vec3 c;
	vec3 o;
	vec3 f;
	vec3 u;
	eye_frame(v, c, o, f, u);
	float k = mix(1.0, EYE_GROW, cartoon_eyes);
	vec3 d = v - c;
	float dn = dot(d, o);
	vec3 flat_part = d - o * dn;
	vec3 way = length(flat_part) > 1e-7 ? normalize(flat_part) : vec3(0.0);
	flat_part = mix(flat_part, way * r * EYE_RADIUS * EYE_GROW, cartoon_eyes);
	return c + flat_part + o * (dn * k - EYE_RADIUS * EYE_SINK * (k - 1.0));
}

// THE GILLS (added 2026-11-18). How far a gill flap reaches back from its slit (metres, as the builder has it).
const float FLAP_W = 0.04576;
// The red of the gills (filaments), and how far a flap's back edge drops when they are wide open (radians).
const vec3 GILL_RED = vec3(0.55, 0.05, 0.06);
const float FLAP_OPEN = 0.6;
// How far the gills open for breathing (0 shut, the default; 1 wide). They open with `gape` too.
uniform float gills : hint_range(0.0, 1.0) = 0.0;

float gills_open() {
	return clamp(max(gape, gills), 0.0, 1.0);
}

// The gills' colour (`uv`: x from an arch's root, or a flap's slit, 0, to its edge, 1; y along it): blood red
// filaments, pale gill rakers along an arch's free edge on its front, a little darker towards the edge.
vec3 gill_colour(vec2 uv, bool rakers) {
	float comb = 0.5 + 0.5 * cos(uv.y * 6.2831853 * 14.0);
	vec3 red = GILL_RED * (0.7 + 0.45 * comb);
	vec3 c = red;
	if (rakers) {
		// (pale gill rakers: short teeth along the arch's free edge)
		c = mix(red, vec3(0.82, 0.74, 0.66), smoothstep(0.75, 0.9, uv.x) * step(0.55, comb));
	}
	return c * mix(1.0, 0.75, uv.x);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	topness = UV2.x;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (abs(part - 6.0) < 0.5) {
		v = eye_grow(v, UV.x);
	}
	if (abs(part - 8.0) < 0.5) {
		// A gill flap: its back edge drops as the gills open (see gills_open).
		v.y -= UV.x * FLAP_W * tan(FLAP_OPEN * gills_open());
	}
	if (part > 1.5 && part < 2.5) {
		ceph_point(UV.x, UV.y, UV2.x, v.x >= 0.0 ? 1.0 : -1.0, v, n);
	} else if (part < 1.5 && UV.x > 0.0) {
		// The lower jaw turns down about its hinge.
		float a = clamp(gape, 0.0, 1.0) * JAW_TURN * UV.x;
		vec2 d = v.yz - HINGE;
		v.yz = HINGE + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	}
	// The wings: from where they start to bend, each line across a wing is laid along a curve
	// whose slope is `wing_angle`, its length kept.
	float side = v.x >= 0.0 ? 1.0 : -1.0;
	float out_x = abs(v.x) / HALF;
	if (out_x > ROOT) {
		float e1 = (out_x - ROOT) / (1.0 - ROOT);
		float back_part = BACK_LAG * (v.z / DISC + 0.5);
		vec2 q = vec2(0.0);
		float de = e1 / 8.0;
		for (int i = 0; i < 8; i++) {
			float a = wing_angle((float(i) + 0.5) * de, back_part, side);
			q += vec2(cos(a), sin(a)) * de;
		}
		q *= (1.0 - ROOT) * HALF;
		float a = wing_angle(e1, back_part, side);
		float c = cos(a);
		float s = sin(a);
		float nx = n.x * side;
		v = vec3(side * (ROOT * HALF + q.x - s * v.y), q.y + c * v.y, v.z);
		n = vec3(side * (nx * c - n.y * s), nx * s + n.y * c, n.z);
	}
	// The tail: a wave that runs back along it, late, and grows towards its tip; round to +X
	// with `curl`.
	float behind = max(v.z - (DISC * 0.5 - 0.08 * DISC), 0.0);
	float f = behind / TAIL_LENGTH;
	v.y += sway * 0.05 * TAIL_LENGTH * pow(f, 1.5) * sin(6.2831853 * (phase - 0.2 - 0.9 * f));
	v.x += curl * behind * behind / (2.0 * TAIL_LENGTH);
	// The body pitches, and rides down as the wings go up.
	float pitch = sway * PITCH * cos(6.2831853 * phase);
	float pc = cos(pitch);
	float ps = sin(pitch);
	v = vec3(v.x, v.y * pc - v.z * ps, v.z * pc + v.y * ps);
	n = vec3(n.x, n.y * pc - n.z * ps, n.z * pc + n.y * ps);
	v.y -= sway * HEAVE * sin(6.2831853 * (phase - 0.08));
	// Banked into a turn: rolled about its long axis, its +X side down.
	float bank = 0.6 * curl;
	float bc = cos(bank);
	float bs = sin(bank);
	v = vec3(v.x * bc + v.y * bs, v.y * bc - v.x * bs, v.z);
	n = vec3(n.x * bc + n.y * bs, n.y * bc - n.x * bs, n.z);
	VERTEX = v;
	NORMAL = n;
}

// How much of a soft-edged ellipse at `at`, turned by `turn`, of half sizes `size`, covers `p`.
float patch_of(vec2 p, vec2 at, vec2 size, float turn, float edge) {
	vec2 d = p - at;
	d = vec2(d.x * cos(turn) + d.y * sin(turn), d.y * cos(turn) - d.x * sin(turn)) / size;
	return 1.0 - smoothstep(1.0 - edge, 1.0 + edge, length(d));
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

