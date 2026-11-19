shader_type spatial;
// The California halibut (california_halibut.gd): every marking drawn here (no texture files), its
// swimming, its lying down on the sand and its jaw. A flatfish, modelled as it lies: its upper
// (eyed) side is +Y, the edge of its back +X, the edge of its belly and its lower jaw -X, its
// nose -Z. What each point is comes from the model (tools/build_california_halibut.py): UV2.y
// the part (0 body, 1 lower jaw, 2 the dorsal and anal fins, 3 the tail, 4 the pectoral and
// pelvic fins, 5 an eye); UV2.x, on the body and jaw, 1 inside the mouth. UV inside the mouth:
// x from the nose (0) to the hinge (1), y from the under lip (0) to the upper lip (1); on a
// fin: x from its root (0) to its edge (1), y along it; on an eye: x middle (0) to rim (1).
//
// It swims as flatfish do: a wave up and down along its flat body, small at the head and large
// at the tail, and a quicker ripple along the fins that fringe it. All of it is a function of
// `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
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


// Kept in step with the model.
const float LENGTH = 1.0;
const float HALF = 0.5;
// The flat its fins lie in, and its underside (metres above the origin).
const float SEAM = -0.0145;
const float UNDER = -0.0355;
// Where the lower jaw hinges (metres behind the snout); the mouth's line is x = -MOUTH_K * xm.
const float HINGE = 0.125;
const float MOUTH_K = 0.42;

// How far through a beat of its body (0..1, it wraps). Set by CaliforniaHalibut.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, as it lies (radians from
// the gills to the tail; 0 straight; more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// How widely it beats, for 1 as a halibut cruising (its tail rises and falls about 0.05 m).
uniform float sway = 1.0;
// The mouth: 0 shut, 1 wide open as when it bites (the lower jaw swung out about its hinge, the
// snout lifted a little the other way).
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// Lying on the sand: 0 swimming, 1 flat on the ground (no wave, its fins and tail laid down to
// the level of its underside, 0.0355 m below its origin).
uniform float settle : hint_range(0.0, 1.0) = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.05;

// The upper side: its sandy ground, the darker blotches, the pale spots and flecks.
uniform vec3 sand : source_color = vec3(0.47, 0.38, 0.25);
uniform vec3 blotch : source_color = vec3(0.2, 0.15, 0.09);
uniform vec3 pale : source_color = vec3(0.78, 0.7, 0.52);
// How strongly the blotches and spots show (0 plain sand; cheaper).
uniform float mottle = 1.0;
// The under (blind) side.
uniform vec3 belly : source_color = vec3(0.93, 0.92, 0.88);
// Inside the mouth, and its teeth.
uniform vec3 mouth : source_color = vec3(0.16, 0.05, 0.05);
uniform vec3 teeth : source_color = vec3(0.92, 0.9, 0.8);
// The iris of its eyes.
uniform vec3 iris : source_color = vec3(0.62, 0.5, 0.24);

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

// How high the body's flat is lifted, `xm` metres behind the snout: a wave that runs back along
// it, small at the head, large at the tail.
float lift_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * (0.005 + 0.05 * s * s);
	return sway * (1.0 - settle) * reach * sin(TAU * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.25 * LENGTH;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.75 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// THE CARTOON EYE (`cartoon_eyes` 1; 0 is the eye as it was) and the lids that `blink` closes.
// The halibut's: a goofy, lopsided googly stare. Both eyes wide and round with plenty of white and a
// small gold iris; the upper eye's pupil sits a little off from the lower one's, so that it always looks
// a touch cross-eyed, as a flatfish should. No lids of its own at rest.
// Where the eye is on the model (its middle on the skin, the way it faces, its radius: printed by
// the builder), how much bigger the cartoon eye is, and how far its rim is sunk into the skin to
// meet it (in radii, per unit of growth).
const vec3 EYE_AT = vec3(-0.00400, 0.01903, -0.41200);
const vec3 EYE_OUT = vec3(-0.03032, 0.97704, -0.21089);
// (the second eye, the one that came round nearer the back's edge)
const vec3 EYE2_AT = vec3(0.03600, 0.01439, -0.40200);
const vec3 EYE2_OUT = vec3(0.35365, 0.90199, -0.24768);
const float EYE_RADIUS = 0.0125;
const float EYE_GROW = 1.45;
const float EYE_SINK = 0.3;
// Its shape, in the eye's own plane (x towards the nose, y up, 1 its rim): the iris's radius;
// the upper lid's edge at rest, how it slopes (lower towards the nose for more than 0) and how
// it arches; the lower lid's edge at rest; how far the iris slides for `eye_look` 1.
const float IRIS = 0.42;
const float LID = 1.4;
const float LID_SLOPE = 0.0;
const float LID_ARCH = 0.0;
const float LOWER_LID = -1.4;
const float LOOK = 0.4;

// 0 the eye as it was, 1 the cartoon eye.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where it looks (-1..1 each): x towards its nose (+) or tail, y up (+) or down.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: a lid of the skin's colour closes over the eye.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// The cartoon eye's white, its iris, and its outline.
uniform vec3 eye_white : source_color = vec3(0.96, 0.94, 0.85);
uniform vec3 eye_iris : source_color = vec3(0.85, 0.62, 0.18);
uniform vec3 eye_line : source_color = vec3(0.12, 0.08, 0.04);

// The eye a point (at rest) belongs to: its middle `c`, the way it faces `o`, and its own
// "forward" (towards the nose) `f` and "up" `u`.
void eye_frame(vec3 p, out vec3 c, out vec3 o, out vec3 f, out vec3 u) {
	bool second = p.x > 0.016;
	c = second ? EYE2_AT : EYE_AT;
	o = normalize(second ? EYE2_OUT : EYE_OUT);
	// (its eyes' "up" is the edge of its back, +X)
	vec3 up = vec3(1.0, 0.0, 0.0);
	f = vec3(0.0, 0.0, -1.0);
	f = normalize(f - o * dot(f, o));
	u = normalize(up - o * dot(up, o) - f * dot(up, f));
}

// The cartoon eye's pupil, `q` in the iris's own measure (1 its edge): 1 inside it.
float pupil_of(vec2 q) {
	return 1.0 - smoothstep(0.52, 0.58, length(q));
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
	vec2 at = clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK + (p.x > 0.016 ? vec2(0.12, 0.1) : vec2(-0.06, -0.02));
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

// THE GILLS (added 2026-11-18): four arches inside the mouth against its roof, seen when the jaw swings out.
const vec3 GILL_RED = vec3(0.55, 0.05, 0.06);

// The gills' colour (`uv`: x from an arch's root, 0, to its edge, 1; y along it): blood red filaments behind,
// pale gill rakers along its free edge on its front, a little darker towards the edge.
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
	inside = UV2.x;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (abs(part - 5.0) < 0.5) {
		v = eye_grow(v, UV.x);
	}
	float xm = v.z + HALF;
	// The mouth: the lower jaw swings out (towards -X) about its hinge; the snout lifts a little
	// the other way.
	vec2 hinge = vec2(-MOUTH_K * HINGE, HINGE - HALF);
	float a = 0.0;
	if (part > 0.5 && part < 1.5) {
		a = gape * 0.62 * smoothstep(HINGE, HINGE - 0.05, xm);
	} else {
		a = -gape * 0.1 * smoothstep(HINGE + 0.02, 0.0, xm);
	}
	if (a != 0.0) {
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = v.xz - hinge;
		v.xz = hinge + vec2(d.x * ca + d.y * sa, d.y * ca - d.x * sa);
		n.xz = vec2(n.x * ca + n.z * sa, n.z * ca - n.x * sa);
	}
	// Lying down: the thin rear of the body sinks to the ground, and the fins and tail are laid
	// down from their roots to their edges.
	float rear = smoothstep(0.55, 0.88, xm);
	v.y -= settle * 0.012 * rear;
	bool fringe = part > 1.5 && part < 3.5;
	bool flat_fin = fringe || (part > 3.5 && part < 4.5 && rest.y < SEAM + 0.005);
	if (flat_fin) {
		v.y -= settle * UV.x * (SEAM - UNDER - 0.003 - 0.012 * rear);
	}
	if (fringe) {
		// The fins' own ripple, twice as quick as the body's wave and shorter.
		float swing = sway * (1.0 - settle) * 0.013 * UV.x;
		float at = TAU * (2.0 * phase - xm / 0.2);
		v.y += swing * sin(at);
		n = normalize(n + vec3(0.0, 0.0, swing * TAU / 0.2 * cos(at)) * n.y);
	}
	// The body's wave: each slice across it is lifted and tipped to stay square to the wave.
	float h = lift_at(xm);
	float slope = (lift_at(xm + 0.004) - lift_at(xm - 0.004)) / 0.008;
	float turn = atan(slope);
	float c = cos(turn);
	float sn = sin(turn);
	v = vec3(v.x, h + v.y * c, v.z - v.y * sn);
	n = vec3(n.x, n.y * c + n.z * sn, -n.y * sn + n.z * c);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The upper side's skin at a place on it (metres across, metres along): sand, darker blotches,
// pale flecks and round pale spots, a fine grain.
vec3 skin(vec2 at) {
	vec3 c = sand;
	float grain = noise2(at * 330.0);
	if (mottle > 0.0) {
		// (the place is pushed about a little, so that the blotches are not square)
		vec2 p = at + 0.03 * (vec2(noise2(at * 22.0 + 40.0), noise2(at * 22.0 + 90.0)) - 0.5);
		float big = 0.6 * noise2(p * 13.0 + 3.0) + 0.4 * noise2(p * 41.0 + 7.3);
		c = mix(c, blotch, mottle * 0.75 * smoothstep(0.5, 0.72, big));
		c = mix(c, pale, mottle * 0.45 * smoothstep(0.6, 0.8, noise2(p * 57.0 + 21.0)));
		vec2 g = p / 0.062;
		vec2 id = floor(g);
		vec2 f = fract(g) - 0.5 - (vec2(hash2(id), hash2(id + 17.0)) - 0.5) * 0.5;
		float d = length(f);
		float on = step(0.62, hash2(id + 9.0));
		c = mix(c, blotch, mottle * 0.3 * on * (1.0 - smoothstep(0.12, 0.3, d)));
		c = mix(c, pale, mottle * 0.6 * on * (1.0 - smoothstep(0.04, 0.15, d)));
	}
	return c * (0.88 + 0.24 * grain);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

