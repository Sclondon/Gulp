shader_type spatial;
// The round stingray (round_stingray.gd): every marking drawn here (no texture files), the
// ripple of its disc, the swing of its tail and its mouth. What each point is comes from the
// model (tools/build_round_stingray.py), which lies flat: UV2.y the part (0 body, 1 the mouth's
// plate underneath, 2 a pelvic fin, 3 the tail fin, 5 an eye, 6 the tail, 7 the spine). UV on a
// fin or the plate: x from its root (0) to its edge (1); on an eye: x middle (0) to rim (1);
// on the tail and spine: x along (0 to 1).
//
// It swims as round rays do: a ripple that runs round the edge of its disc from the nose back
// along each side, the middle of the disc still. All of it is a function of `phase` alone, so a
// picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 0.5;
const float HALF = 0.25;
// The disc: its middle (metres behind the nose), its half length and its half width.
const float DISC_MID = 0.145;
const float DISC_LONG = 0.145;
const float DISC_WIDE = 0.14;
// Where the eyes are (metres behind the nose, metres to each side).
const vec2 EYE_AT = vec2(0.088, 0.029);
// The mouth's plate: where its hinge is (metres behind the nose, metres above the origin).
const float MOUTH_HINGE = 0.072;
const float MOUTH_Y = -0.0274;
const float MOUTH_LONG = 0.014;
const float MOUTH_WIDE = 0.034;

// How far through a beat of its ripple (0..1, it wraps). Set by RoundStingray.
uniform float phase = 0.0;
// Turning: how far its tail is bent round to one side (radians from the rear of the disc to the
// tail's end; 0 straight; more than 0 the tail comes round to +X). The disc is not bent by it.
uniform float curl = 0.0;
// How high the ripple is, for 1 as a round stingray swimming (the disc's edge rises and falls
// about 0.02 m), 0 lying still and flat.
uniform float sway = 1.0;
// The mouth, underneath: 0 shut, 1 wide open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How many waves there are along each side of the disc at once.
uniform float waves = 1.4;

// The upper side: its tan-brown ground, the pale spots and the darker net between them.
uniform vec3 back : source_color = vec3(0.4, 0.31, 0.19);
uniform vec3 net : source_color = vec3(0.2, 0.15, 0.09);
uniform vec3 spot : source_color = vec3(0.74, 0.64, 0.4);
// How strongly the spots and the net show (0 plain; cheaper).
uniform float spots = 1.0;
// The under side.
uniform vec3 belly : source_color = vec3(0.95, 0.93, 0.83);
// Inside the mouth; the iris of its eyes; the spine.
uniform vec3 mouth : source_color = vec3(0.13, 0.05, 0.05);
uniform vec3 iris : source_color = vec3(0.6, 0.5, 0.28);
uniform vec3 spine : source_color = vec3(0.78, 0.72, 0.58);

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

// How high the disc is lifted at a place on it (metres to the side, metres behind the nose): a
// wave running round its edge from the nose back along each side; nothing at its middle and
// nothing at the root of the tail.
float ripple(float x, float xm) {
	vec2 d = vec2(x / DISC_WIDE, (xm - DISC_MID) / DISC_LONG);
	float rim = smoothstep(0.4, 1.0, length(d));
	float round_it = atan(abs(d.x), -d.y);
	float reach = 0.02 * rim * sqrt(rim) * (0.4 + 0.6 * smoothstep(0.0, 0.9, round_it)) * (1.0 - smoothstep(2.3, 2.95, round_it));
	return sway * reach * sin(TAU * (phase - waves * round_it / PI));
}

// The tail laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 0.25 - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - 0.25);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// THE CARTOON EYE (`cartoon_eyes` 1; 0 is the eye as it was) and the lids that `blink` closes.
// The round stingray's: shy and wary, peeking from the sand. A big brown eye with little white under
// a worried lid (higher towards its nose), its pupil the W of a real stingray's: two lobes hang into it
// from above.
// Where the eye is on the model (its middle on the skin, the way it faces, its radius: printed by
// the builder), how much bigger the cartoon eye is, and how far its rim is sunk into the skin to
// meet it (in radii, per unit of growth).
const vec3 EYE_MIDDLE = vec3(0.02900, 0.01851, -0.16200);
const vec3 EYE_OUT = vec3(0.63186, 0.77290, -0.05818);
const float EYE_RADIUS = 0.007;
const float EYE_GROW = 2.0;
const float EYE_SINK = 0.3;
// Its shape, in the eye's own plane (x towards the nose, y up, 1 its rim): the iris's radius;
// the upper lid's edge at rest, how it slopes (lower towards the nose for more than 0) and how
// it arches; the lower lid's edge at rest; how far the iris slides for `eye_look` 1.
const float IRIS = 0.66;
const float LID = 0.5;
const float LID_SLOPE = -0.2;
const float LID_ARCH = 0.0;
const float LOWER_LID = -0.85;
const float LOOK = 0.25;

// 0 the eye as it was, 1 the cartoon eye.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where it looks (-1..1 each): x towards its nose (+) or tail, y up (+) or down.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: a lid of the skin's colour closes over the eye.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// The cartoon eye's white, its iris, and its outline.
uniform vec3 eye_white : source_color = vec3(0.95, 0.93, 0.86);
uniform vec3 eye_iris : source_color = vec3(0.55, 0.42, 0.22);
uniform vec3 eye_line : source_color = vec3(0.08, 0.06, 0.03);

// The eye a point (at rest) belongs to: its middle `c`, the way it faces `o`, and its own
// "forward" (towards the nose) `f` and "up" `u`.
void eye_frame(vec3 p, out vec3 c, out vec3 o, out vec3 f, out vec3 u) {
	float sx = p.x >= 0.0 ? 1.0 : -1.0;
	c = vec3(EYE_MIDDLE.x * sx, EYE_MIDDLE.yz);
	o = normalize(vec3(EYE_OUT.x * sx, EYE_OUT.yz));
	vec3 up = vec3(0.0, 1.0, 0.0);
	f = vec3(0.0, 0.0, -1.0);
	f = normalize(f - o * dot(f, o));
	u = normalize(up - o * dot(up, o) - f * dot(up, f));
}

// The cartoon eye's pupil, `q` in the iris's own measure (1 its edge): 1 inside it.
float pupil_of(vec2 q) {
	float whole = 1.0 - smoothstep(0.58, 0.64, length(q));
	float lobes = max(1.0 - smoothstep(0.26, 0.31, length(q - vec2(-0.2, 0.55))), 1.0 - smoothstep(0.26, 0.31, length(q - vec2(0.2, 0.55))));
	return whole * (1.0 - lobes);
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
const float FLAP_W = 0.0044;
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
	// The ripple, and the skin tipped to follow it.
	float lift = ripple(rest.x, xm);
	float e = 0.003;
	vec2 fall = vec2(ripple(rest.x + e, xm) - lift, ripple(rest.x, xm + e) - lift) / e;
	v.y += lift;
	n = normalize(n - vec3(fall.x, 0.0, fall.y) * n.y);
	// The tail swings a little from side to side as it goes.
	float t = max(0.0, (xm - 0.27) / (LENGTH - 0.27));
	v.x += sway * 0.014 * t * t * sin(TAU * (phase - 0.4 * t));
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The upper side's skin at a place on it: tan-brown, covered with pale spots of uneven size,
// the ground between them darker, like a net.
vec3 skin(vec2 at) {
	vec3 c = back * (0.9 + 0.2 * noise2(at * 420.0));
	if (spots > 0.0) {
		vec2 g = at / 0.019 + 0.6 * (vec2(noise2(at * 30.0), noise2(at * 30.0 + 60.0)) - 0.5);
		vec2 cell = floor(g);
		float nearest = 9.0;
		float size = 0.0;
		for (int j = -1; j <= 1; j++) {
			for (int i = -1; i <= 1; i++) {
				vec2 other = cell + vec2(float(i), float(j));
				vec2 centre = other + 0.5 + (vec2(hash2(other), hash2(other + 31.0)) - 0.5) * 0.5;
				float d = length(g - centre);
				if (d < nearest) {
					nearest = d;
					size = hash2(other + 7.0);
				}
			}
		}
		float wide = 0.15 + 0.17 * size;
		c = mix(c, net, spots * 0.55 * smoothstep(0.3, 0.6, nearest));
		c = mix(c, spot, spots * 0.7 * (1.0 - smoothstep(wide - 0.1, wide + 0.04, nearest)));
	}
	return c;
}

void fragment() {
	int p = int(part + 0.5);
	// (a gill flap's outside is drawn as the skin there, its inside as the gills)
	bool flap = p == 8;
	if (flap) {
		p = rest_normal.y < 0.0 ? 0 : 9;
	}
	float opened = gills_open();
	float upper = smoothstep(-0.25, 0.1, rest_normal.y);
	float xm = rest.z + HALF;
	float side = abs(rest.x);
	vec3 c;
	float rough = 0.45;
	float spec = 0.45;
	if (p == 0) {
		vec3 above = skin(rest.xz);
		// (a paler rim to the disc)
		vec2 d = vec2(rest.x / DISC_WIDE, (xm - DISC_MID) / DISC_LONG);
		above = mix(above, spot, 0.35 * smoothstep(0.9, 1.0, length(d)));
		// The spiracles: a dark opening close behind each eye.
		vec2 hole = vec2((side - EYE_AT.y - 0.001) / 0.006, (xm - EYE_AT.x - 0.013) / 0.005);
		above = mix(above, net * 0.3, 1.0 - smoothstep(0.7, 1.0, length(hole)));
		// The under side: pale, yellower towards the rim; five gill slits each side; the mouth,
		// dark under its plate; the nostrils ahead of it.
		vec3 below = mix(belly, belly * vec3(1.0, 0.9, 0.62), 0.6 * smoothstep(0.55, 1.0, length(d)));
		for (int k = 0; k < 5; k++) {
			float at = 0.092 + 0.011 * float(k);
			float slit = (1.0 - smoothstep(0.0006, 0.0014, abs(xm - at - 0.2 * (side - 0.03))));
			slit *= smoothstep(0.02, 0.023, side) * (1.0 - smoothstep(0.035, 0.038, side));
			below = mix(below, mix(mouth * 1.5, GILL_RED * 0.6, opened), slit * 0.8);
			// (behind the slit, under its flap: the red of the gills as the flap lifts)
			float behind = xm - (at + 0.2 * (side - 0.03));
			float under = step(0.0, behind) * (1.0 - smoothstep(FLAP_W * 0.7, FLAP_W, behind)) * smoothstep(0.02, 0.023, side) * (1.0 - smoothstep(0.035, 0.038, side));
			below = mix(below, GILL_RED * 0.7, under * smoothstep(0.0, 0.3, opened) * (flap ? 0.0 : 1.0));
		}
		float in_mouth = (1.0 - smoothstep(MOUTH_WIDE * 0.5 - 0.0045, MOUTH_WIDE * 0.5 - 0.003, side));
		in_mouth *= smoothstep(MOUTH_HINGE - MOUTH_LONG + 0.0015, MOUTH_HINGE - MOUTH_LONG + 0.003, xm) * (1.0 - smoothstep(MOUTH_HINGE - 0.001, MOUTH_HINGE + 0.0005, xm));
		below = mix(below, mouth, in_mouth);
		vec2 nostril = vec2((side - 0.011) / 0.004, (xm - 0.045) / 0.0028);
		below = mix(below, mouth * 1.5, 1.0 - smoothstep(0.7, 1.0, length(nostril)));
		c = mix(below, above, upper);
	} else if (p == 1) {
		// The mouth's plate: the belly's colour, a shade greyer.
		c = belly * vec3(0.92, 0.89, 0.88);
	} else if (p == 2) {
		c = mix(belly, skin(rest.xz), upper);
	} else if (p == 3) {
		// The tail fin: the back's colour, darker at its edge, fine rays.
		c = mix(back, net, 0.7 * smoothstep(0.5, 1.0, UV.x)) * (0.85 + 0.15 * cos(UV.y * TAU * 22.0));
		rough = 0.55;
	} else if (p == 9) {
		// The gills: an arch (pale rakers on its front, red filaments behind) or the inside of a flap.
		c = gill_colour(UV, !flap && rest_normal.z < 0.0);
		rough = 0.6;
		spec = 0.3;
	} else if (p == 5) {
		// An eye: a dark pupil, a gold iris, the skin's colour at its rim.
		float r = UV.x;
		c = mix(vec3(0.01, 0.01, 0.012), iris, smoothstep(0.42, 0.5, r));
		c = mix(c, back * 0.7, smoothstep(0.76, 0.9, r));
		rough = 0.12;
		spec = 0.6;
	} else if (p == 6) {
		// The tail: the back's markings above, the belly's colour beneath.
		c = mix(belly, skin(rest.xz), smoothstep(-0.5, 0.1, rest_normal.y));
	} else {
		c = spine;
		rough = 0.5;
	}
	if (p == 5) {
		// (the cartoon eye and the lids: see eye_colour)
		float glint;
		float shut;
		c = eye_colour(rest, UV.x, c, back, glint, shut);
		EMISSION = vec3(glint * 0.35);
		rough = mix(mix(rough, 0.15, cartoon_eyes), 0.55, shut);
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
