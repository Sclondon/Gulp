shader_type spatial;
// The Pacific red snapper (snapper.gd): every marking drawn here (no texture files), its swimming,
// its sculling pectoral fins and its working jaw. What each point is comes from the model
// (tools/build_snapper.py): UV2.y the part (0 body, 1 lower jaw, 2 dorsal fin, 3 anal fin, 4 tail,
// 5 a pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body and jaw: x how far along, y how
// high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to
// edge (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1). UV2.x,
// on the body and jaw, how much the point is inside the mouth; on the dorsal fin, how far it
// stands above the fin's root.
//
// It swims as snappers do: a wave down the rear half of the body and the tail, the pectoral
// fins rowing in turn to hold it or steer it. All of it is a function of `phase` alone, so a
// picture of it loops exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model (tools/build_snapper.py), in body lengths.
const float LENGTH = 0.7;
// Where the tail fin is hinged: behind it the tail is one plate.
const float JOINT = 0.83;
// How far the tail wrist swings to each side at `sway` 1.
const float SWING = 0.07;
// The jaw's hinge, where the line of the mouth starts and how it bows; how far the jaw swings
// down at `gape` 1 (radians); how far the snout lifts, from where, about what height.
const float HINGE_S = 0.11;
const float HINGE_Y = -0.062;
const float MOUTH_Y0 = -0.035;
const float MOUTH_BOW = 1.2;
const float GAPE_ANGLE = 0.62;
const float LIFT = 0.07;
const float LIFT_TO = 0.105;
const float LIFT_Y = 0.05;
// A pectoral fin's root (to the side, up, along); how far it rows and flaps (radians); whether
// the two row in turn (1) or together (0); how far it folds in when `scull` is 0.
const vec3 PEC_ROOT = vec3(0.0572, -0.045, 0.285);
const float PEC_SWING = 0.2;
const float PEC_FLAP = 0.1;
const float PEC_ALT = 1.0;
const float PEC_HOLD = -0.25;
const float FIN_WAVE = 0.006;
// How much of the dorsal fin is spines.
const float SPINE_SHARE = 0.55;
// The gill cover's edge (its rearmost reach, at what height, how it curves); the eye; its pupil.
const vec3 GILL = vec3(0.265, -0.01, 3.0);
const vec2 EYE_AT = vec2(0.137, 0.03);
const float PUPIL = 0.42;

// How long the wave along its body is, in body lengths.
uniform float wave = 1.0;

// The back, the flank, the belly: rosy red all over, deeper above, pale below.
uniform vec3 back : source_color = vec3(0.62, 0.07, 0.08);
uniform vec3 flank : source_color = vec3(0.9, 0.24, 0.24);
uniform vec3 belly : source_color = vec3(0.97, 0.7, 0.68);
// The silver that shines over the red where light glances off the scales, and how much.
uniform vec3 silver : source_color = vec3(0.98, 0.9, 0.9);
uniform float sheen = 0.5;
// The fins, and their darker edges.
uniform vec3 fin : source_color = vec3(0.88, 0.2, 0.2);
uniform vec3 fin_edge : source_color = vec3(0.45, 0.04, 0.06);
// The eye: its iris and the ring round its pupil.
uniform vec3 iris : source_color = vec3(0.78, 0.16, 0.12);
uniform vec3 iris_ring : source_color = vec3(0.95, 0.7, 0.3);

// ---------------------------------------------------------------------------------------------
// From here to the fragment function the shader is the same for GameCommon's snapper, rockfish,
// surfperch and garibaldi: only the numbers above differ. Mend one, mend the others.
// Inside, everything is in body lengths (the fish 1 long, `s` 0 at the tip of its snout to 1 at
// the tips of its tail), as the build script has it.
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
// How far the spines of its dorsal fin are raised (0 folded back, 1 up).
uniform float dorsal = 1.0;
// The inside of the mouth.
uniform vec3 mouth : source_color = vec3(0.16, 0.03, 0.035);

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
	float reach = SWING * (0.1 - 0.5 * k + 1.4 * k * k);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
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
	int p = int(part + 0.5);
	vec3 v = VERTEX / LENGTH;
	vec3 n = NORMAL;
	rest = v;
	rest_normal = n;
	inside = p <= 1 ? UV2.x : 0.0;
	float open = clamp(gape, 0.0, 1.0);
	if (p == 1) {
		// The lower jaw swings down about its hinge; the throat behind it stays.
		float a = open * GAPE_ANGLE * (1.0 - smoothstep(HINGE_S - CORNER_B, HINGE_S + CORNER_C, v.z + 0.5));
		vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	} else if (p == 0 && v.z + 0.5 < LIFT_TO) {
		// The snout lifts a little as the mouth opens.
		float a = -open * LIFT * (1.0 - smoothstep(0.0, LIFT_TO, v.z + 0.5));
		vec2 hinge = vec2(LIFT_Y, LIFT_TO - 0.5);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	} else if (p == 2) {
		// The spines of the dorsal fin fold back and down.
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
	if (p >= 2 && p <= 4) {
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
		// Rosy red, deeper on the back, pale pink under the belly.
		c = mix(flank, back, smoothstep(0.1, 0.9, q));
		c = mix(belly, c, smoothstep(-0.98, -0.3, q));
		// Scales on the body (the snout and jaws are smooth): each a shade deeper at its root,
		// silver where the light catches it. Above the lateral line the rows run up and back.
		float body_part = smoothstep(0.17, 0.25, s) * (1.0 - smoothstep(0.8, 0.84, s));
		float lean = smoothstep(0.2, 0.7, q) * 0.5;
		float sc = scales(vec2((s + lean * round_it) * 86.0, round_it * 30.0));
		c *= mix(1.0, 0.86 + 0.2 * sc, body_part);
		float shine = sheen * (0.25 + 0.75 * glance) * (0.35 + 0.65 * sc * body_part) * (1.0 - 0.6 * smoothstep(0.4, 0.95, q));
		c = mix(c, silver, shine * 0.55);
		// The lateral line: a faint arched line, high on the side.
		float line_y = 0.045 + 0.05 * sin(clamp((s - 0.24) / 0.6, 0.0, 1.0) * 3.14159265) - 0.05 * smoothstep(0.5, 0.82, s);
		c = mix(c, back, 0.35 * (1.0 - smoothstep(0.0, 0.004, abs(y - line_y))) * smoothstep(0.24, 0.28, s) * (1.0 - smoothstep(0.8, 0.83, s)));
		// The head: a deeper red over the snout and brow, the lips' seam, the gill cover's edge
		// and the cheek's crease before it.
		c = mix(c, mix(back, flank, 0.35), (1.0 - smoothstep(0.03, 0.2, s)) * smoothstep(-0.4, 0.5, q) * 0.7);
		c = mix(c, back * 0.45, lip_line(s, y) * 0.75);
		c = mix(c, c * 0.35, gill_crease(s, y, q));
		float cheek = s - (gill_s(y) - 0.07 - 2.5 * y * y);
		c = mix(c, c * 0.6, (1.0 - smoothstep(0.0, 0.004, abs(cheek))) * 0.4 * smoothstep(-0.85, -0.5, q) * (1.0 - smoothstep(0.0, 0.3, q)));
		c = mix(c, mouth, inside);
		rough = mix(0.34, 0.6, inside);
		spec = mix(0.6, 0.2, inside);
	} else if (p == 2) {
		// The dorsal fin: rosy, its spines a deeper red, a dark red edge.
		float spine = pow(abs(cos(3.14159265 * UV.y / SPINE_SHARE * 10.0)), 12.0) * (1.0 - step(SPINE_SHARE, UV.y));
		float ray = 0.5 + 0.5 * cos(UV.y * 190.0);
		c = fin * (0.86 + 0.14 * mix(1.0, ray, step(SPINE_SHARE, UV.y)));
		c = mix(c, back, spine * 0.6);
		c = mix(c, fin_edge, smoothstep(0.78, 0.98, UV.x) * 0.8);
		c = mix(c, back, (1.0 - smoothstep(0.0, 0.3, UV.x)) * 0.5);
		rough = 0.55;
	} else if (p == 3 || p == 4) {
		// The anal fin and the tail: red, fine rays, a dark red edge.
		float ray = 0.5 + 0.5 * cos(UV.y * (p == 4 ? 150.0 : 90.0));
		c = fin * (0.84 + 0.16 * ray);
		c = mix(c, fin_edge, smoothstep(0.8, 0.99, UV.x) * 0.85);
		c = mix(c, mix(back, flank, 0.5), (1.0 - smoothstep(0.0, 0.3, UV.x)) * 0.6);
		rough = 0.5;
	} else if (p == 5 || p == 6) {
		// The pectoral and pelvic fins: a paler rosy pink, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 70.0);
		c = mix(fin, belly, p == 5 ? 0.35 : 0.2) * (0.86 + 0.14 * ray);
		c = mix(c, flank, (1.0 - smoothstep(0.0, 0.25, UV.x)) * 0.6);
		rough = 0.55;
		spec = 0.35;
	} else {
		c = eye_colour(UV.x, iris, iris_ring);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
