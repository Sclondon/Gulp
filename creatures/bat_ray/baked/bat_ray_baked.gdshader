shader_type spatial;
// The bat ray (bat_ray.gd): every marking drawn here (no texture files), the flap of its wings,
// its trailing tail and its mouth. What each point is comes from the model
// (tools/build_bat_ray.py), which holds its wings out flat: UV2.y the part (0 body, 1 the
// mouth's plate underneath, 2 a pelvic fin or the dorsal fin, 5 an eye, 6 the tail, 7 the
// spine). UV on a fin or the plate: x from its root (0) to its edge (1); on an eye: x middle (0)
// to rim (1); on the tail and spine: x along (0 to 1).
//
// It flies as eagle rays do: its wings beat up and down like a bird's, each bent along its
// length, the tips following the roots a little late; the body rides down as they rise. All of
// it is a function of `phase` alone, so a picture of it loops exactly.
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
const float LENGTH = 1.4;
const float HALF = 0.7;
// The flat the wings lie in (metres above the origin), where a wing begins to bend (metres from
// the middle line) and where its tip is.
const float PLANE = -0.0235;
const float ROOT = 0.09;
const float HALF_SPAN = 0.6;
// The mouth's plate: where its hinge is (metres behind the nose, metres above the origin).
const float MOUTH_HINGE = 0.106;
const float MOUTH_Y = -0.0674;
const float MOUTH_LONG = 0.03;
const float MOUTH_WIDE = 0.08;

// How far through a beat of its wings (0..1, it wraps). Set by BatRay.
uniform float phase = 0.0;
// Turning: how far its rear and tail are bent round to one side (radians from the middle of the
// disc to the tail's tip; 0 straight; more than 0 the tail comes round to +X). The wings are
// not bent by it: a ray turns by banking, which is the game's to do.
uniform float curl = 0.0;
// How widely it beats, for 1 as a bat ray cruising (its wing tips rise about 0.3 m and fall
// about 0.23 m), 0 gliding with its wings held flat.
uniform float sway = 1.0;
// The mouth, underneath: 0 shut, 1 wide open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How late the wing tips follow the roots, as a part of a beat.
uniform float lag = 0.22;

// The upper side, and the darker shade it turns to towards the wings' edges.
uniform vec3 back : source_color = vec3(0.2, 0.165, 0.1);
uniform vec3 back_dark : source_color = vec3(0.075, 0.065, 0.045);
// The under side, and the dusk at the wings' edges beneath.
uniform vec3 belly : source_color = vec3(0.93, 0.93, 0.9);
uniform vec3 belly_dusk : source_color = vec3(0.42, 0.38, 0.33);
// Inside the mouth; the iris of its eyes; the spine.
uniform vec3 mouth : source_color = vec3(0.13, 0.05, 0.05);
uniform vec3 iris : source_color = vec3(0.5, 0.42, 0.24);
uniform vec3 spine : source_color = vec3(0.74, 0.69, 0.58);

varying vec3 rest;
varying vec3 rest_normal;
varying float part;

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

// How steeply a wing rises (radians), `q` of the way from its root (0) to its tip (1): the
// roots lead, the tips follow, and the trailing edge (`chord` 1) a little after the leading.
float slope_at(float q, float chord) {
	return sway * (0.08 + (0.2 + 0.8 * q) * sin(TAU * (phase - lag * q - 0.06 * chord)));
}

// The rear of the disc and the tail laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 0.5 - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - 0.5);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// THE CARTOON EYE (`cartoon_eyes` 1; 0 is the eye as it was) and the lids that `blink` closes.
// The bat ray's: sly and knowing. A heavy lid slanting down towards its nose over an amber iris,
// a level bar of a pupil (a ray's), a lower lid just showing.
// Where the eye is on the model (its middle on the skin, the way it faces, its radius: printed by
// the builder), how much bigger the cartoon eye is, and how far its rim is sunk into the skin to
// meet it (in radii, per unit of growth).
const vec3 EYE_AT = vec3(0.07000, 0.01562, -0.64000);
const vec3 EYE_OUT = vec3(0.87060, 0.42425, -0.24915);
const float EYE_RADIUS = 0.011;
const float EYE_GROW = 2.3;
const float EYE_SINK = 0.3;
// Its shape, in the eye's own plane (x towards the nose, y up, 1 its rim): the iris's radius;
// the upper lid's edge at rest, how it slopes (lower towards the nose for more than 0) and how
// it arches; the lower lid's edge at rest; how far the iris slides for `eye_look` 1.
const float IRIS = 0.6;
const float LID = 0.3;
const float LID_SLOPE = 0.25;
const float LID_ARCH = 0.0;
const float LOWER_LID = -0.8;
const float LOOK = 0.3;

// 0 the eye as it was, 1 the cartoon eye.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where it looks (-1..1 each): x towards its nose (+) or tail, y up (+) or down.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: a lid of the skin's colour closes over the eye.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// The cartoon eye's white, its iris, and its outline.
uniform vec3 eye_white : source_color = vec3(0.93, 0.9, 0.82);
uniform vec3 eye_iris : source_color = vec3(0.86, 0.52, 0.14);
uniform vec3 eye_line : source_color = vec3(0.06, 0.045, 0.03);

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
	return 1.0 - smoothstep(0.2, 0.26, length(vec2(max(abs(q.x) - 0.38, 0.0), q.y)));
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
const float FLAP_W = 0.0084;
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
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (abs(part - 5.0) < 0.5) {
		v = eye_grow(v, UV.x);
	}
	if (abs(part - 8.0) < 0.5) {
		// A gill flap: its back edge drops as the gills open (see gills_open).
		v.y -= UV.x * FLAP_W * tan(FLAP_OPEN * gills_open());
	}
	float xm = v.z + HALF;
	if (part > 0.5 && part < 1.5) {
		// The mouth's plate swings down about its rear edge.
		float a = gape * 0.75;
		float ca = cos(a);
		float sa = sin(a);
		vec2 hinge = vec2(MOUTH_Y, MOUTH_HINGE - HALF);
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * ca + d.y * sa, d.y * ca - d.x * sa);
		n.yz = vec2(n.y * ca + n.z * sa, n.z * ca - n.y * sa);
	}
	float r = abs(v.x);
	if (part < 0.5 && r > ROOT) {
		// A wing: bent upward (or downward) along its length, its own length kept.
		float sx = sign(v.x);
		float span = r - ROOT;
		float q = span / (HALF_SPAN - ROOT);
		float chord = clamp((xm - 0.1) / 0.5, 0.0, 1.0);
		float along = 0.0;
		float up = 0.0;
		for (int i = 0; i < 6; i++) {
			float b = slope_at(q * (float(i) + 0.5) / 6.0, chord);
			along += cos(b);
			up += sin(b);
		}
		along *= span / 6.0;
		up *= span / 6.0;
		float b = slope_at(q, chord);
		float cb = cos(b);
		float sb = sin(b);
		float high = v.y - PLANE;
		v.x = sx * (ROOT + along - high * sb);
		v.y = PLANE + up + high * cb;
		n = vec3(n.x * cb - sx * n.y * sb, sx * n.x * sb + n.y * cb, n.z);
	}
	// The body rides down as the wings rise, and up as they fall.
	v.y -= sway * 0.02 * sin(TAU * phase);
	// The tail trails: a slow wave down it, larger towards its tip.
	float t = max(0.0, (xm - 0.66) / (LENGTH - 0.66));
	v.y += sway * 0.05 * t * t * sin(TAU * (phase - 0.3 - 0.6 * t));
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

