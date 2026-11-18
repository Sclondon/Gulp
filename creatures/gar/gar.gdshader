shader_type spatial;
// The longnose gar (gar.gd): every marking drawn here (no texture files), its swimming, its
// sideways snap and its opening beak. What each point is comes from the model
// (tools/build_gar.py): UV2.y the part (0 body, 1 lower jaw, 2 dorsal fin, 3 anal fin, 4 tail,
// 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 9 a tooth; 8 is not used). UV, on the body and jaw:
// x how far along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a
// fin: x root (0) to edge (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to
// rim (1). UV2.x, on the body and jaw, how much the point is inside the mouth; on a tooth, 1 on
// the lower jaw.
//
// It swims as gars do: slowly, a long wave down the back half of its body to the rounded tail,
// the fins far back rippling; much of the time it hangs nearly still (`sway` low), and it strikes
// by swinging its head and beak sideways (`snap`) as it opens the beak (`gape`). All of it is a
// function of `phase` and those settings alone, so a picture of it loops exactly. Nothing here
// needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model (tools/build_gar.py), in body lengths.
const float LENGTH = 1.3;
// Where the tail fin is hinged: behind it the tail is one plate.
const float JOINT = 0.885;
// How far the tail wrist swings to each side at `sway` 1.
const float SWING = 0.05;
// The jaw's hinge, where the line of the mouth starts and how it bows; how far the jaw swings
// down at `gape` 1 (radians); how far the upper beak lifts, from where, about what height.
const float HINGE_S = 0.215;
const float HINGE_Y = -0.007;
const float MOUTH_Y0 = -0.002;
const float MOUTH_BOW = 1.6;
const float GAPE_ANGLE = 0.5;
const float LIFT = 0.04;
const float LIFT_TO = 0.21;
const float LIFT_Y = 0.012;
// A pectoral fin's root (to the side, up, along); how far it rows and flaps (radians); whether
// the two row in turn (1) or together (0); how far it folds in when `scull` is 0.
const vec3 PEC_ROOT = vec3(0.0206, -0.03, 0.31);
const float PEC_SWING = 0.22;
const float PEC_FLAP = 0.12;
const float PEC_ALT = 1.0;
const float PEC_HOLD = -0.3;
const float FIN_WAVE = 0.008;
// (it has no spines: the whole dorsal fin is soft)
const float SPINE_SHARE = 0.0;
// The gill cover's edge (its rearmost reach, at what height, how it curves); the eye; its pupil.
const vec3 GILL = vec3(0.3, 0.0, 2.0);
const vec2 EYE_AT = vec2(0.218, 0.011);
const float PUPIL = 0.42;
// How the curve of the body behind the head is laid (see `curl`): from where, how long.
const float CURL_FROM = -0.15;
const float CURL_SPAN = 0.6;
// The snap: the body bends from here forward over this much of its length, and at `snap` 1 the
// head and beak end up turned this far (radians); ahead of the bend they stay straight.
const float SNAP_FROM = -0.15;
const float SNAP_SPAN = 0.22;
const float SNAP_ANGLE = 0.7;

// How long the wave along its body is, in body lengths.
uniform float wave = 0.85;
// The strike: the head and beak swung sideways (-1 to 1; more than 0 to its left, +X).
uniform float snap = 0.0;

// The back, the flank, the belly: olive-brown above, a paler olive on the sides, cream below.
uniform vec3 back : source_color = vec3(0.26, 0.24, 0.12);
uniform vec3 flank : source_color = vec3(0.58, 0.54, 0.34);
uniform vec3 belly : source_color = vec3(0.9, 0.88, 0.76);
// The edges of its diamond scales, and the round dark spots towards its tail and on its fins.
uniform vec3 scale_edge : source_color = vec3(0.14, 0.13, 0.07);
uniform vec3 spots : source_color = vec3(0.09, 0.08, 0.05);
// The fins: olive-amber.
uniform vec3 fin : source_color = vec3(0.6, 0.5, 0.28);
// The eye: its iris and the ring round its pupil.
uniform vec3 iris : source_color = vec3(0.72, 0.58, 0.2);
uniform vec3 iris_ring : source_color = vec3(0.9, 0.78, 0.4);

// ---------------------------------------------------------------------------------------------
// From here to the fragment function the shader is the same for GameCommon's yellow perch,
// walleye and gar (the gar adds its sideways snap): only the numbers above differ. Mend one,
// mend the others. It began as the snapper's (godot/snapper). Inside, everything is in body
// lengths (the fish 1 long, `s` 0 at the tip of its snout to 1 at the tips of its tail), as the
// build script has it.
// ---------------------------------------------------------------------------------------------

// How far before and behind the jaw's hinge the corner of the mouth runs (as the model has it).
const float CORNER_B = 0.012;
const float CORNER_C = 0.035;

// How far through a beat of its tail (0..1, it wraps). Set by the node.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left).
uniform float curl = 0.0;
// How widely its body and tail beat (1 as it cruises, 0 still: hovering on its pectoral fins).
uniform float sway = 1.0;
// How hard its pectoral fins scull (1 as it hovers or cruises, 0 held still).
uniform float scull = 1.0;
// The mouth: 0 shut, 1 wide open, as when it bites. The lower jaw swings down about its hinge
// and the snout lifts a little.
uniform float gape = 0.0;
// How far the spines of its first dorsal fin are raised (0 folded back, 1 up).
uniform float dorsal = 1.0;
// The inside of the mouth, and the teeth.
uniform vec3 mouth : source_color = vec3(0.3, 0.1, 0.08);
uniform vec3 teeth : source_color = vec3(0.93, 0.91, 0.84);

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

// Scales: rounds in rows, every other row half a scale along. 1 at a scale's middle, falling
// to 0 between scales. `p` counts scales (x along the fish, y round it).
float scales(vec2 p) {
	float column = floor(p.x);
	vec2 f = vec2(fract(p.x) - 0.5, fract(p.y + 0.5 * mod(column, 2.0)) - 0.5);
	// (far off, where the scales are smaller than the picture's dots, they fade to their average)
	float far = smoothstep(0.35, 0.9, max(fwidth(p.x), fwidth(p.y)));
	return mix(1.0 - smoothstep(0.28, 0.62, length(f)), 0.55, far);
}

// How far to one side the middle line of the body is at `s`: a wave that runs back along it,
// small at the head, growing to the tail.
float side_at(float s) {
	float k = s / JOINT;
	// (a gar's wave reaches further forward than a perch's: its body is long and bends along)
	float reach = SWING * (0.15 - 0.25 * k + 1.1 * k * k);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float d = v.z - CURL_FROM;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / CURL_SPAN;
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, CURL_FROM + (r - v.x) * sn);
}

// The snap (the gar's own): the body ahead of SNAP_FROM bent round an arc over SNAP_SPAN, and
// the head and beak ahead of that carried round straight, turned by `snap` * SNAP_ANGLE.
void snap_bend(inout vec3 v, inout vec3 n) {
	float d = SNAP_FROM - v.z;
	if (abs(snap) < 0.001 || d <= 0.0) {
		return;
	}
	float k = clamp(snap, -1.0, 1.0) * SNAP_ANGLE / SNAP_SPAN;
	float bent = min(d, SNAP_SPAN);
	float a = bent * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	// (along the arc to `bent`, then straight on along its last direction; `v.x` across it)
	vec2 at = vec2(r * (1.0 - c), SNAP_FROM - r * sn) + vec2(sn, -c) * (d - bent) + vec2(c, sn) * v.x;
	v = vec3(at.x, v.y, at.y);
	n = vec3(n.x * c - n.z * sn, n.y, n.x * sn + n.z * c);
}

// Turns `v` (and `n`) by `a` about the line across the head at (y, z) `hinge`.
void hinge_turn(inout vec3 v, inout vec3 n, vec2 hinge, float a) {
	vec2 d = v.yz - hinge;
	float c = cos(a);
	float sn = sin(a);
	v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
}

void vertex() {
	part = UV2.y;
	int p = int(part + 0.5);
	vec3 v = VERTEX / LENGTH;
	vec3 n = NORMAL;
	rest = v;
	rest_normal = n;
	inside = p <= 1 ? UV2.x : 0.0;
	float open = clamp(gape, 0.0, 1.0);
	bool lower = p == 1 || (p == 9 && UV2.x > 0.5);
	if (lower) {
		// The lower jaw (and its teeth) swings down about its hinge; the throat behind it stays.
		float a = open * GAPE_ANGLE * (1.0 - smoothstep(HINGE_S - CORNER_B, HINGE_S + CORNER_C, v.z + 0.5));
		hinge_turn(v, n, vec2(HINGE_Y, HINGE_S - 0.5), a);
	} else if ((p == 0 || p == 9) && v.z + 0.5 < LIFT_TO) {
		// The snout (and the upper teeth) lifts a little as the mouth opens.
		float a = -open * LIFT * (1.0 - smoothstep(0.0, LIFT_TO, v.z + 0.5));
		hinge_turn(v, n, vec2(LIFT_Y, LIFT_TO - 0.5), a);
	} else if (p == 2) {
		// The spines of the first dorsal fin fold back and down.
		float down = UV2.x * (1.0 - clamp(dorsal, 0.0, 1.0));
		v.y -= down * 0.9;
		v.z += down * 0.5;
	} else if (p == 5) {
		// A pectoral fin sculls: it rows out and back about its root, its tip trailing, and
		// flaps a little up and down.
		float sg = sign(v.x);
		vec3 root = vec3(sg * PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z - 0.5);
		float ph = 6.2831853 * (phase + (sg > 0.0 ? 0.0 : 0.5 * PEC_ALT)) - 1.3 * UV.x;
		float a = sg * (PEC_HOLD * (1.0 - clamp(scull, 0.0, 1.0)) + scull * PEC_SWING * sin(ph));
		float b = sg * scull * PEC_FLAP * cos(ph);
		vec3 d = v - root;
		d = vec3(d.x * cos(a) + d.z * sin(a), d.y, -d.x * sin(a) + d.z * cos(a));
		d = vec3(d.x * cos(b) - d.y * sin(b), d.x * sin(b) + d.y * cos(b), d.z);
		n = vec3(n.x * cos(a) + n.z * sin(a), n.y, -n.x * sin(a) + n.z * cos(a));
		v = root + d;
	}
	if ((p >= 2 && p <= 4) || p == 8) {
		// The soft rays of the middle fins ripple.
		float soft = p == 2 ? smoothstep(SPINE_SHARE - 0.1, SPINE_SHARE + 0.1, UV.y) : 1.0;
		v.x += FIN_WAVE * (0.3 + 0.7 * sway) * soft * UV.x * UV.x * sin(6.2831853 * phase - 5.0 * UV.y - 1.0);
	}
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float s = v.z + 0.5;
	float zc = min(s, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, s - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - 0.5 - o.x * sn + o.z * c);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(v, n);
	snap_bend(v, n);
	VERTEX = v * LENGTH;
	NORMAL = n;
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float s) {
	return MOUTH_Y0 + (HINGE_Y - MOUTH_Y0) * pow(max(s, 0.0) / HINGE_S, MOUTH_BOW);
}

float gill_s(float y) {
	return GILL.x - GILL.z * (y - GILL.y) * (y - GILL.y);
}

// The lips' seam (1 on the line of the mouth) and the gill cover's crease, for a point of the
// head `s` along and `y` high; `q` is how high on its side (-1 keel to 1 ridge).
float lip_line(float s, float y) {
	return (1.0 - smoothstep(0.0012, 0.0045, abs(y - mouth_y(s)))) * smoothstep(0.0, 0.006, s) * (1.0 - smoothstep(HINGE_S - 0.004, HINGE_S + 0.012, s));
}

float gill_crease(float s, float y, float q) {
	float behind = s - gill_s(y);
	float span = smoothstep(-0.97, -0.75, q) * (1.0 - smoothstep(0.35, 0.6, q));
	return ((1.0 - smoothstep(0.0, 0.004, abs(behind - 0.002))) * 0.6 + (1.0 - smoothstep(0.0, 0.03, behind)) * step(0.0, behind) * 0.25) * span;
}

// An eye: a black pupil, an iris of `tint` ringed with `ring` round the pupil, a dark rim.
vec3 eye_colour(float r, vec3 tint, vec3 ring) {
	float grain = 0.85 + 0.15 * noise2(vec2(atan(rest.y - EYE_AT.y, rest.z + 0.5 - EYE_AT.x) * 12.0, r * 3.0));
	vec3 c = mix(ring, tint, smoothstep(0.5, 0.72, r)) * grain;
	c = mix(vec3(0.004, 0.005, 0.008), c, smoothstep(PUPIL, PUPIL + 0.06, r));
	return mix(c, tint * 0.25, smoothstep(0.86, 1.0, r) * 0.85);
}

// The head's seams and the inside of the mouth over a colour `c` of the body or jaw.
vec3 head_marks(vec3 c, float s, float y, float q) {
	c = mix(c, c * 0.45, lip_line(s, y) * 0.75);
	c = mix(c, c * 0.35, gill_crease(s, y, q));
	float cheek = s - (gill_s(y) - 0.07 - 2.5 * y * y);
	c = mix(c, c * 0.6, (1.0 - smoothstep(0.0, 0.004, abs(cheek))) * 0.4 * smoothstep(-0.85, -0.5, q) * (1.0 - smoothstep(0.0, 0.3, q)));
	return mix(c, mouth, inside);
}

// Round spots scattered over a grid of `p` (one or none to a cell): 1 inside a spot.
float spotted(vec2 p, float many, float size) {
	vec2 cell = floor(p);
	float found = 0.0;
	for (int i = -1; i <= 1; i++) {
		for (int j = -1; j <= 1; j++) {
			vec2 c = cell + vec2(float(i), float(j));
			float h = hash2(c);
			if (h < many) {
				vec2 at = c + vec2(hash2(c + 7.1), hash2(c + 3.3));
				float r = size * (0.6 + 0.6 * hash2(c + 1.7));
				found = max(found, 1.0 - smoothstep(r * 0.75, r, length(p - at)));
			}
		}
	}
	return found;
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	if (p <= 1) {
		float s = rest.z + 0.5;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		float round_it = acos(clamp(q, -1.0, 1.0)) / 3.14159265;
		// Olive-brown on the back, paler olive on the sides, cream under the belly; the beak
		// dark above and pale below.
		c = mix(flank, back, smoothstep(0.1, 0.8, q));
		c = mix(belly, c, smoothstep(-0.8, -0.25, q));
		// The armour: diamond-shaped scales in rows that run diagonally round the body, their
		// edges dark, each scale a little glossy. (The beak and head are bony plates, smooth.)
		vec2 g = vec2(s * 105.0, round_it * 26.0);
		vec2 d = vec2(g.x + g.y, g.x - g.y);
		vec2 f = min(fract(d), 1.0 - fract(d));
		float edge = min(f.x, f.y);
		float far = smoothstep(0.3, 0.9, max(fwidth(d.x), fwidth(d.y)));
		float body_part = smoothstep(0.29, 0.32, s);
		float lines = mix(1.0 - smoothstep(0.02, 0.09, edge), 0.25, far) * body_part;
		c = mix(c, scale_edge, lines * 0.55);
		c *= 1.0 + 0.1 * body_part * (1.0 - far) * smoothstep(0.1, 0.4, edge);
		// Round dark spots, few on the front half, many towards the tail; a few on the head.
		float spot = spotted(vec2(s * 60.0, round_it * 16.0), 0.55, 0.32);
		spot *= max(smoothstep(0.45, 0.8, s), 0.25 * smoothstep(0.18, 0.28, s) * (1.0 - smoothstep(0.32, 0.4, s)));
		spot *= smoothstep(-0.7, -0.3, q);
		c = mix(c, spots, spot * 0.85);
		// The head: the bony plates of the skull and gill cover darker, the gill cover's edge.
		c = mix(c, back, (1.0 - smoothstep(0.2, 0.3, s)) * smoothstep(-0.2, 0.6, q) * 0.45);
		c = head_marks(c, s, y, q);
		rough = mix(mix(0.45, 0.36, body_part), 0.6, inside);
		spec = mix(0.45, 0.2, inside);
	} else if (p == 2 || p == 3 || p == 4) {
		// The dorsal fin, anal fin and tail: olive-amber, fine rays, round dark spots.
		float ray = 0.5 + 0.5 * cos(UV.y * (p == 4 ? 110.0 : 70.0));
		c = fin * (0.85 + 0.15 * ray);
		float spot = spotted(vec2(UV.x * 7.0, UV.y * (p == 4 ? 12.0 : 6.0)), 0.6, 0.3);
		c = mix(c, spots, spot * 0.85);
		c = mix(c, flank, (1.0 - smoothstep(0.0, 0.2, UV.x)) * 0.4);
		rough = 0.5;
	} else if (p == 5 || p == 6) {
		// The pectoral and pelvic fins: olive-amber, fine rays, a few faint spots.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		c = mix(fin, belly, 0.15) * (0.86 + 0.14 * ray);
		c = mix(c, spots, spotted(vec2(UV.x * 5.0, UV.y * 4.0), 0.4, 0.3) * 0.5);
		rough = 0.55;
		spec = 0.35;
	} else if (p == 9) {
		// A tooth: ivory, clearer at its point.
		c = mix(teeth, teeth * 0.75 + vec3(0.1), UV.x * 0.5);
		rough = 0.3;
	} else {
		c = eye_colour(UV.x, iris, iris_ring);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
