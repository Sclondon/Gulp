shader_type spatial;
// The betta (betta.gd): every marking drawn here (no texture files), its swimming, the trailing,
// billowing and rippling of its long fins, its mouth, and its flare (gill covers out, the beard
// out, every fin spread stiff). What each point is comes from the model (tools/build_betta.py):
// UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 a
// pelvic fin, 6 an eye, 7 the lower jaw, 8 a gill cover, 9 the beard). UV2.x: 1 inside the mouth,
// 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its side (1 the ridge
// of the back, 0 the keel of the belly); on a fin, a gill cover or the beard: x root (0) to tip or
// free edge (1), y leading or upper edge (0) to trailing or lower edge (1); on an eye: x middle (0)
// to rim (1).
//
// Every place here is in BODY LENGTHS (the tip of the jaw 0, the end of the tail 1), as the build
// script has them: the model's metres are divided by `length_m`.
//
// The model is built with every fin spread as when it flares. With `flare` 0 the shader folds the
// tail in like a closing fan (pleated) and lets it droop, leans the dorsal and anal fins back, and
// swings the pelvic threads back; the gill covers lie shut and the beard is folded away inside the
// head. Its swimming is a slow wave down the body; behind the tail's root the long fins are carried
// partly as a plate and lag behind it as the wave runs on along them (they trail), every long fin
// billows (a slow swell out to one side and back) and ripples (smaller folds running back across it,
// like cloth), less as it flares. All of it is a function of `phase` alone, so a picture of it loops
// exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model (body lengths).
const float HALF = 0.5;
const float JOINT = 0.535;
const float BODY_TO = 0.558;
const vec2 EYE_AT = vec2(0.072, 0.016);
const float EYE_RADIUS = 0.028;
// The lower jaw: how far back it runs (its hinge is there, on the line of the mouth), and how far
// it swings down, wide open (radians).
const float JAW_TO = 0.037;
const float HINGE_Y = -0.01265;
const float GAPE_OPEN = 1.0;
// The tail fin's pivot (on the middle line); the gill covers' hinge (how far back, how far out).
const float TAIL_PIVOT = 0.525;
const vec2 COVER_HINGE = vec2(0.0485, 0.098);
// The beard: its reach, its ruffle, the way it reaches (the left side's; the right's is mirrored).
const float BEARD_LONG = 0.08;
const float BEARD_RUFFLE = 0.012;
const vec3 BEARD_WAY = vec3(0.8554, -0.2516, 0.4528);

// How long the model is, in metres.
uniform float length_m = 0.065;
// How far through one beat (0..1, it wraps). Set by Betta.
uniform float phase = 0.0;
// In one beat: how many times its tail beats, how many times its fins swell out and back, how many
// ripples run across them (whole numbers).
uniform float tail_beats = 1.0;
uniform float billows = 1.0;
uniform float ripples = 2.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left).
// The head stays as it is. (As the yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely its body beats (1 cruising), how much its fins trail, billow and ripple (1 as a betta
// drifting, 0 still).
uniform float sway = 1.0;
uniform float flow = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.1;
// How far its mouth is open: 0 shut, 1 wide open. The lower jaw swings down about its hinge.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How far it flares: 0 calm (its fins folded and trailing, gill covers shut), 1 the full display
// (gill covers swung out, the dark beard out round them, every fin spread out stiff).
uniform float flare : hint_range(0.0, 1.0) = 0.0;

// The body, and its darker back and head; the shine of its scales where light glances off them.
uniform vec3 body_main : source_color = vec3(0.08, 0.18, 0.55);
uniform vec3 body_dark : source_color = vec3(0.04, 0.05, 0.16);
uniform vec3 sheen : source_color = vec3(0.25, 0.5, 1.0);
// How strongly the sheen shows (an iridescent fish shines; it also glows a little of itself).
uniform float shine = 1.0;
// The long fins: their main colour, at the root, at the edge, and their rays.
uniform vec3 fin_main : source_color = vec3(0.1, 0.22, 0.65);
uniform vec3 fin_root : source_color = vec3(0.22, 0.06, 0.18);
uniform vec3 fin_edge : source_color = vec3(0.35, 0.6, 1.0);
uniform vec3 fin_ray : source_color = vec3(0.04, 0.08, 0.3);
// The tips of the pelvic threads.
uniform vec3 pelvic_tip : source_color = vec3(0.85, 0.88, 0.95);
// The marble: 0 none, 1 blotched over a pale ground in three colours (`pattern_seed` makes each
// one's blotches its own).
uniform float marble = 0.0;
uniform float pattern_seed = 0.0;
uniform vec3 blotch_a : source_color = vec3(0.75, 0.06, 0.06);
uniform vec3 blotch_b : source_color = vec3(0.1, 0.2, 0.6);
uniform vec3 blotch_c : source_color = vec3(0.05, 0.05, 0.06);
// The beard, and the inside of the gill covers and the mouth.
uniform vec3 beard : source_color = vec3(0.06, 0.03, 0.04);
uniform vec3 gill_inside : source_color = vec3(0.35, 0.06, 0.08);
uniform vec3 mouth_inside : source_color = vec3(0.12, 0.03, 0.04);
// The clear pectoral fins.
uniform vec3 fin_clear : source_color = vec3(0.4, 0.44, 0.5);

varying vec3 rest;
varying float part;
varying float inside;
varying float inner;

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

float fbm(vec2 p) {
	return 0.55 * noise2(p) + 0.3 * noise2(p * 2.1 + 5.3) + 0.15 * noise2(p * 4.3 + 11.7);
}

// How far to one side the middle line of the body is (body lengths), `xm` behind the jaw.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = 0.006 - 0.022 * s + 0.07 * s * s;
	return sway * reach * sin(6.2831853 * (phase * tail_beats - xm / wave));
}

// How far to one side a point of a long fin is put by its trailing, billowing and rippling
// (body lengths), at `xm` behind the jaw and `y` up, `away` how far it is from the body.
float fin_side(float xm, float y, float away, int p) {
	float loose = flow * (1.0 - 0.75 * flare);
	float tp = 6.2831853 * phase * tail_beats;
	float bp = 6.2831853 * phase * billows;
	float rp = 6.2831853 * phase * ripples;
	// (trailing: the body's wave running on along the fin behind the tail's root)
	float d = max(xm - JOINT, 0.0);
	float trail = sway * 0.3 * d * sqrt(d) * sin(tp - 6.2831853 * xm / wave - 0.5);
	// (billowing: a slow swell out to one side and back, greater towards the edge)
	float swell = 0.05 * away * away * sin(bp - away * 4.0 + (p == 2 ? 1.7 : 0.0) + (p == 1 ? 3.1 : 0.0));
	// (rippling: folds that run back across the fin)
	float fold = 0.01 * smoothstep(0.02, 0.15, away) * sin(rp - xm * 26.0 + y * 34.0);
	return trail * (1.0 - 0.5 * flare) + loose * (swell + fold);
}

// The tail folded in like a closing fan when it is calm: its pleats, how far to one side.
float pleat(float xm, float y) {
	vec2 d = vec2(xm - TAIL_PIVOT, y);
	float r = length(d);
	float a = atan(d.y, d.x);
	return (1.0 - flare) * 0.035 * r * smoothstep(0.03, 0.12, r) * sin(a * 16.0);
}

// How far from the body a point of a long fin is (body lengths).
float out_of(float xm, float y, int p) {
	if (p == 3) {
		return length(vec2(xm - TAIL_PIVOT, y));
	} else if (p == 1) {
		return max(y - 0.06, 0.0);
	} else if (p == 2) {
		return max(-0.07 - y, 0.0);
	}
	return max(-0.08 - y, 0.0) * 0.8;
}

float lateral(float xm, float y, int p) {
	float s = fin_side(xm, y, out_of(xm, y, p), p);
	if (p == 3) {
		s += pleat(xm, y);
	}
	return s;
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / 0.7;
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

void vertex() {
	part = UV2.y;
	inside = UV2.x;
	vec3 v = VERTEX / length_m;
	rest = v;
	vec3 n = NORMAL;
	inner = 0.0;
	float xm = v.z + HALF;
	int p = int(part + 0.5);
	float calm = 1.0 - clamp(flare, 0.0, 1.0);
	if (p == 7) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = clamp(gape, 0.0, 1.0) * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.016, JAW_TO - 0.002, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		n = vec3(n.x, n.y * ca + n.z * sa, n.z * ca - n.y * sa);
	} else if (p == 8) {
		// A gill cover swings out about its hinge at its front (mirrored for the right side).
		float sx = sign(v.x);
		inner = step(n.x * sx, 0.0);
		float a = clamp(flare, 0.0, 1.0) * 1.1;
		float ca = cos(a);
		float sa = sin(a);
		float dx = v.x * sx - COVER_HINGE.x;
		float dz = xm - COVER_HINGE.y;
		v.x = sx * (COVER_HINGE.x + dx * ca + dz * sa);
		v.z = COVER_HINGE.y - HALF + dz * ca - dx * sa;
		float nx = n.x * sx;
		n = vec3(sx * (nx * ca + n.z * sa), n.y, n.z * ca - nx * sa);
	} else if (p == 9) {
		// The beard: folded back onto its root inside the head when it is calm.
		float sx = sign(v.x);
		vec3 way = vec3(BEARD_WAY.x * sx, BEARD_WAY.y, BEARD_WAY.z);
		vec3 across = normalize(cross(vec3(0.0, 1.0, 0.0), way));
		float t = UV.x;
		float u = UV.y;
		float reach = BEARD_LONG * (0.6 + 0.4 * sin(3.14159265 * u));
		vec3 spread = way * (t * reach) + across * (BEARD_RUFFLE * t * sin(u * 6.0 * 3.14159265));
		float out_amt = smoothstep(0.0, 1.0, clamp(flare * 1.25 - 0.1, 0.0, 1.0));
		v -= spread * (1.0 - out_amt);
		// (and it waves a little, out)
		v += across * 0.006 * t * sin(6.2831853 * phase * ripples - u * 9.0) * out_amt * flow;
	} else if (p == 3) {
		// The tail: closed in like a fan and drooping when it is calm.
		vec2 d = vec2(xm - TAIL_PIVOT, v.y);
		float r = length(d);
		float a = atan(d.y, d.x);
		float w = smoothstep(0.03, 0.1, r);
		float a2 = mix(a, a * mix(0.42, 1.0, flare) - 0.32 * calm, w);
		float turn = a2 - a;
		v.y = r * sin(a2);
		v.z = TAIL_PIVOT - HALF + r * cos(a2);
		n = vec3(n.x, n.y * cos(turn) + n.z * sin(turn), n.z * cos(turn) - n.y * sin(turn));
	} else if (p == 1) {
		// The dorsal fin: leaned back and lowered when it is calm.
		float h = max(v.y - 0.055, 0.0);
		v.z += h * 0.95 * calm;
		v.y -= h * 0.42 * calm;
	} else if (p == 2) {
		// The anal fin: leaned back when it is calm.
		float h = max(-0.065 - v.y, 0.0);
		v.z += h * 0.75 * calm;
		v.y += h * 0.15 * calm;
	} else if (p == 5) {
		// The pelvic threads: swung back when it is calm.
		vec2 root = vec2(-0.07, 0.2 - HALF);
		vec2 d = vec2(v.y - root.x, v.z - root.y);
		float a = -0.75 * calm;
		float ca = cos(a);
		float sa = sin(a);
		v.y = root.x + d.x * ca - d.y * sa;
		v.z = root.y + d.x * sa + d.y * ca;
		n = vec3(n.x, n.y * ca - n.z * sa, n.y * sa + n.z * ca);
	}
	xm = v.z + HALF;
	if (p == 1 || p == 2 || p == 3 || p == 5) {
		// The long fins trail, billow and ripple: both of a fin's skins are moved alike.
		float e = 0.004;
		float s = lateral(xm, v.y, p);
		float dz = (lateral(xm + e, v.y, p) - lateral(xm - e, v.y, p)) / (2.0 * e);
		float dy = (lateral(xm, v.y + e, p) - lateral(xm, v.y - e, p)) / (2.0 * e);
		v.x += s;
		n = vec3(n.x, n.y - n.x * dy, n.z - n.x * dz);
	}
	// (behind its root the tail is carried partly as one plate, turned about the root)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.003) - side_at(zc - 0.003)) / 0.006;
	float turn = atan(slope) * mix(1.0, 0.5, step(JOINT, xm));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(v, n);
	VERTEX = v * length_m;
	NORMAL = normalize(n);
}

float mouth_y(float xm) {
	return 0.004 - 0.45 * xm;
}

float gill_x(float y) {
	return 0.165 - 7.0 * (y + 0.008) * (y + 0.008);
}

// The marble's blotches: a colour, and how much of it there is here (0 none).
vec4 blotches(vec2 at) {
	float a = fbm(at + pattern_seed * 1.37);
	float b = fbm(at * 1.3 + 17.1 + pattern_seed * 0.71);
	float k = fbm(at * 0.7 + 31.7 + pattern_seed * 2.13);
	vec3 colour = k < 0.45 ? blotch_a : (k < 0.6 ? blotch_b : blotch_c);
	float amount = smoothstep(0.56, 0.61, a) * 0.95;
	amount = max(amount, smoothstep(0.64, 0.69, b) * 0.9);
	return vec4(colour, amount);
}

void fragment() {
	int p = int(part + 0.5);
	vec3 nrm = normalize(NORMAL);
	float facing = clamp(dot(nrm, normalize(VIEW)), 0.0, 1.0);
	float glance = 1.0 - facing;
	vec3 c;
	vec3 glow = vec3(0.0);
	float rough = 0.4;
	float spec = 0.5;
	if (p == 0 || p == 7 || (p == 8 && inner < 0.5)) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		if (p == 8) {
			q = 0.0;
		}
		float behind = xm - gill_x(y);
		// The body: darker over the back and the head.
		c = mix(body_main, body_dark, smoothstep(0.3, 0.95, q) * 0.7);
		c = mix(c, body_dark, (1.0 - smoothstep(0.08, 0.2, xm)) * 0.55);
		// The scales: each a little brighter at its middle, its edge darker (they catch the light).
		float arc = acos(clamp(q, -1.0, 1.0)) * 0.08;
		float row = floor(arc / 0.012);
		float along = xm / 0.016 + 0.5 * mod(row, 2.0);
		vec2 f = vec2(fract(along), fract(arc / 0.012));
		float scale_r = length(vec2(f.x, (f.y - 0.5) * 1.2));
		float rim = smoothstep(0.62, 0.95, scale_r);
		float scaled = smoothstep(0.0, 0.01, behind) * (1.0 - smoothstep(BODY_TO - 0.04, BODY_TO, xm)) * (p == 8 ? 0.0 : 1.0);
		float glint = (1.0 - smoothstep(0.2, 0.7, scale_r)) * scaled;
		if (marble > 0.5) {
			vec4 b = blotches(vec2(xm * 14.0, y * 14.0));
			c = mix(c, b.rgb, b.a);
		}
		c *= 1.0 - 0.18 * rim * scaled;
		// The iridescent shine where light glances off it, strongest on each scale's middle.
		c += sheen * shine * (0.15 + 0.25 * glint) * glance * glance;
		glow = sheen * shine * 0.08 * (0.4 + glint) * (0.3 + 0.7 * glance);
		// The head: the line of the mouth, the gill cover's edge.
		float mouth_l = (1.0 - smoothstep(0.001, 0.003, abs(y - mouth_y(xm)))) * smoothstep(0.0, 0.004, xm) * (1.0 - smoothstep(JAW_TO - 0.006, JAW_TO, xm)) * (1.0 - smoothstep(0.0, 0.3, gape));
		c = mix(c, vec3(0.03, 0.02, 0.03), mouth_l * 0.7);
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.35, 0.55, q));
		float crease = (1.0 - smoothstep(0.0, 0.004, abs(behind - 0.002))) * 0.5;
		c = mix(c, c * 0.4, crease * span);
		if (p == 8) {
			// (the outside of a gill cover: the head's colour, its back edge darker)
			c = mix(c, c * 0.5, smoothstep(0.75, 1.0, UV.x));
		}
		rough = mix(0.32, 0.2, glint);
		spec = 0.6;
		c = mix(c, mouth_inside, inside);
		glow *= 1.0 - inside;
		rough = mix(rough, 0.8, inside);
		spec = mix(spec, 0.2, inside);
	} else if (p == 8) {
		// The inside of a gill cover: red, as the gills under it.
		c = gill_inside;
		rough = 0.6;
		spec = 0.3;
	} else if (p == 9) {
		// The beard: dark, ruffled, a little red at its root.
		c = mix(gill_inside * 0.6, beard, smoothstep(0.0, 0.4, UV.x));
		c *= 0.85 + 0.15 * cos(UV.y * 80.0);
		rough = 0.55;
		spec = 0.35;
	} else if (p == 6) {
		// An eye: a big black pupil, a dark iris with a thin ring of gold and the body's colour.
		float r = UV.x;
		vec3 iris = mix(body_dark * 1.5, vec3(0.75, 0.6, 0.25), smoothstep(0.55, 0.62, r) * (1.0 - smoothstep(0.66, 0.74, r)) * 0.8);
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.5, 0.56, r));
		c = mix(c, body_dark, smoothstep(0.86, 1.0, r) * 0.85);
		rough = 0.1;
		spec = 0.7;
	} else if (p == 4) {
		// A pectoral fin: clear.
		c = mix(fin_main, fin_clear, 0.5) * (0.9 + 0.1 * cos(UV.y * 40.0));
		rough = 0.5;
		spec = 0.35;
	} else {
		// The long fins: their root colour, their main colour, a paler edge, many fine rays.
		float t = UV.x;
		float u = UV.y;
		float rays = pow(abs(cos(u * (p == 3 ? 70.0 : 45.0))), 4.0);
		c = mix(fin_root, fin_main, smoothstep(0.0, 0.35, t));
		c = mix(c, fin_ray, rays * 0.45 * smoothstep(0.05, 0.3, t));
		c = mix(c, fin_edge, smoothstep(0.82, 0.98, t) * 0.75);
		if (marble > 0.5) {
			vec4 b = blotches(vec2(t * 6.0, u * (p == 3 ? 9.0 : 4.0)) + float(p) * 7.0);
			c = mix(c, b.rgb, b.a * 0.85);
		}
		if (p == 5) {
			c = mix(c, pelvic_tip, smoothstep(0.75, 0.95, t));
		}
		c += sheen * shine * 0.18 * glance * glance;
		glow = sheen * shine * 0.04 * glance;
		rough = 0.45;
		spec = 0.4;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = glow;
}
