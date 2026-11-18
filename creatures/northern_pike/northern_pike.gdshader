shader_type spatial;
// The northern pike (northern_pike.gd): every marking drawn here (no texture files), and its
// swimming. What each point is comes from the model (tools/build_northern_pike.py): UV2.y the
// part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 a pelvic fin,
// 6 an eye, 7 the lower jaw, 8 a tooth of the upper jaw or the roof of the mouth, 9 a tooth of the
// lower jaw). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far
// along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x
// root (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim
// (1); on a tooth: x root to point.
//
// It swims as pike do (subcarangiform, body and tail): the long front of the body stays nearly
// straight, a wave grows through the back half, and the tail with the dorsal and anal fins close
// before it drives it. All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 1.0;
const float HALF = 0.5;
// Where the tail fin is hinged (metres behind the jaw): behind it the tail is one plate.
const float JOINT = 0.866;
const float MOUTH_TO = 0.136;
const vec2 EYE_AT = vec2(0.153, 0.0265);
// The lower jaw: how far back it runs (metres behind its tip), where its hinge is there (on the
// line of the mouth), and how far it swings down, wide open (radians).
const float JAW_TO = 0.135;
const float HINGE_Y = -0.009075;
const float GAPE_OPEN = 0.55;
// The snout tips up a little as the mouth opens (radians, wide open), less and less back to the
// hinge.
const float SNOUT_LIFT = 0.07;

// How far through a beat of its tail (0..1, it wraps). Set by NorthernPike.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is. (As the yellowfin tuna's `curl`.) A pike striking from an
// S-bend: set `curl` and let it straighten.
uniform float curl = 0.0;
// How widely it beats, for 1 a pike cruising (its tail tips swing about 0.08 m either way), 0 a
// pike hanging still.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.0;
// How far its mouth is open: 0 shut, 1 wide open (as when it strikes). The lower jaw swings down
// about its hinge, the snout tips up a little, and the teeth show.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The back, the olive-green flank, the cream belly.
uniform vec3 back : source_color = vec3(0.10, 0.15, 0.06);
uniform vec3 olive : source_color = vec3(0.30, 0.38, 0.15);
uniform vec3 belly : source_color = vec3(0.90, 0.88, 0.76);
// The pale bean-shaped spots in rows along the flank; how strongly they show.
uniform vec3 spot : source_color = vec3(0.80, 0.80, 0.50);
uniform float spots_show = 1.0;
// The fins: their olive-orange ground and the dark blotches on the dorsal, anal and tail fins.
uniform vec3 fin : source_color = vec3(0.50, 0.42, 0.18);
uniform vec3 fin_dark : source_color = vec3(0.08, 0.08, 0.04);
uniform vec3 fin_low : source_color = vec3(0.72, 0.55, 0.30);
// The teeth, and the inside of the mouth.
uniform vec3 tooth : source_color = vec3(0.92, 0.90, 0.84);
uniform vec3 mouth_inside : source_color = vec3(0.55, 0.42, 0.38);
// The gills (seen through the wide-open mouth): the red of their filaments and the pale of their rakers.
uniform vec3 gill_red : source_color = vec3(0.62, 0.05, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.80, 0.72);
// As the model has it (tools/build_northern_pike.py, its THROAT_Q line): the point at the back of the throat, where the
// old wall across the back of the mouth is drawn to so that it becomes the throat's floor; and the gills' part.
const vec3 THROAT_Q = vec3(0.0, -0.01961, -0.29303);
const float GILL_PART = 10.0;

// The cartoon eye: 0 the eye as it is in life (the default), 1 the cartoon eye: bigger, a pale white round
// a coloured iris, a big dark pupil, a highlight that stays put up and forward (towards the light from the
// surface) and a dark outline, so that it reads from far off. Its character: a cold, patient ambusher's stare: a bright golden-yellow iris, a keyhole pupil drawn out into a
// point towards the snout (as a pike's is, to sight along its jaw), the lid low and nearly level, so
// that it seems to be sizing up whatever is in front of it.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where it looks: x towards its snout (less than 0 back towards its tail), y up; -1..1. Both eyes look the
// same way. (The cartoon eye's iris and pupil slide.)
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashed flat and a lid of its skin's colour drawn down over it (a fish has
// no lids; this is the cartoon's blink).
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.98, 0.84, 0.22);
uniform vec3 eye_iris_dark : source_color = vec3(0.62, 0.42, 0.06);
uniform vec3 eye_white : source_color = vec3(0.95, 0.94, 0.84);
uniform vec3 eye_lid : source_color = vec3(0.24, 0.30, 0.12);

// As the model has it (the build script prints them: its EYE line): the left eye's middle on the skin, the
// way it faces, how the skin falls away from it going up and going along (along its normal, per metre
// squared), and the eye's radius.
const vec3 EYE_MID = vec3(0.03328, 0.02650, -0.34700);
const vec3 EYE_OUT = vec3(0.8077, 0.5776, -0.1185);
const vec2 EYE_SAG = vec2(-27.381, -1.054);
const float EYE_RADIUS = 0.0125;
// The cartoon eye: how much bigger it is, the iris's size (of the eye's), the pupil's (of the iris's),
// where it looks when `eye_look` is 0 (in the eye's flat, 1 its rim), and its lid's line: how high it
// comes down (1 the top of the eye) and how it slants (more than 0 higher towards the snout).
const float EYE_GROW = 1.6;
const float IRIS = 0.66;
const float PUPIL = 0.42;
const vec2 LOOK_REST = vec2(0.12, 0.0);
const float LID_AT = 0.38;
const float LID_SLOPE = 0.08;

varying vec3 rest;
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

// How far to one side the middle line of the body is, `xm` metres behind the jaw.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.006 - 0.026 * s + 0.08 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
}

// The body behind the head laid round an arc (see `curl`).
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

// Turns a point and its normal about the hinge (the line across the head through both corners of
// the mouth) by `a` radians: more than 0 the front goes down.
void hinge_turn(inout vec3 v, inout vec3 n, float a) {
	float ca = cos(a);
	float sa = sin(a);
	vec2 d = vec2(v.y - HINGE_Y, v.z + HALF - JAW_TO);
	v.y = HINGE_Y + d.x * ca + d.y * sa;
	v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
	n = vec3(n.x, n.y * ca + n.z * sa, n.z * ca - n.y * sa);
}

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	inside = UV2.x;
	vec3 v = VERTEX;
	if (part < 0.5 && UV2.x > 0.99 && abs(UV.x - JAW_TO / LENGTH) < 0.0001) {
		// The top edge of the old wall across the back of the mouth, drawn back to the end of the throat as the
		// mouth opens: the wall becomes the floor of a short tunnel (its roof and the gills in it are in the
		// model). Shut, it is where it always was.
		v = mix(v, THROAT_Q, smoothstep(0.0, 0.35, clamp(gape, 0.0, 1.0)));
		rest = v;
	}
	if (gape <= 0.0001 && ((part < 0.5 && UV2.x > 0.99 && UV.x > JAW_TO / LENGTH + 0.0001) || abs(part - GILL_PART) < 0.5)) {
		// Shut, the throat's roof and the gills are folded away into the end of the throat, so that nothing of
		// them shows through the hairline seams of the closed mouth.
		v = THROAT_Q;
	}
	if (abs(part - GILL_PART) < 0.5) {
		// the gill arches spread a little as the mouth opens
		v.x *= 1.0 + 0.12 * clamp(gape, 0.0, 1.0);
	}
	if (part > 5.5 && part < 6.5 && (cartoon_eyes > 0.0 || blink > 0.0)) {
		// The eye grown about its middle, its rim kept on the skin; and squashed for a blink.
		float side = v.x < 0.0 ? -1.0 : 1.0;
		vec3 mid = vec3(EYE_MID.x * side, EYE_MID.yz);
		vec3 out_n = vec3(EYE_OUT.x * side, EYE_OUT.yz);
		float s = mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
		vec2 d0 = vec2(v.y - mid.y, v.z - mid.z);
		v = mid + (v - mid) * s + out_n * (s * s - s) * (EYE_SAG.x * d0.x * d0.x + EYE_SAG.y * d0.y * d0.y);
		v.y = mid.y + (v.y - mid.y) * (1.0 - 0.85 * clamp(blink, 0.0, 1.0));
	}
	vec3 nn = NORMAL;
	float xm = v.z + HALF;
	float open = clamp(gape, 0.0, 1.0);
	if ((part > 6.5 && part < 7.5) || (part > 8.5 && part < 9.5)) {
		// The lower jaw and its teeth swing down whole about the hinge; its back slides up into the
		// throat, inside the body.
		hinge_turn(v, nn, open * GAPE_OPEN);
	} else if (part < 0.5 || (part > 5.5 && part < 6.5) || (part > 7.5 && part < 8.5)) {
		// The snout ahead of the hinge (with the roof of the mouth and its teeth) tips up a little.
		hinge_turn(v, nn, -open * SNOUT_LIFT * (1.0 - smoothstep(JAW_TO * 0.4, JAW_TO, xm)));
	}
	xm = v.z + HALF;
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.003) - side_at(zc - 0.003)) / 0.006;
	float turn = atan(slope) * (1.0 + 0.2 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(nn.x * c + nn.z * sn, nn.y, -nn.x * sn + nn.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return -0.0030 - 0.045 * xm;
}

float gill_x(float y) {
	return 0.255 - 3.0 * (y + 0.005) * (y + 0.005);
}

// The bean-shaped spots: rows along the flank, each row half a spot along from the next; each
// spot a pale oval lying along the body, a little bent, its size and place a little different.
float beans(float xm, float arc) {
	float rowh = 0.018;
	float row = floor(arc / rowh);
	float step_x = 0.030;
	float lane = xm / step_x + 0.5 * mod(row, 2.0) + (hash2(vec2(row, 3.0)) - 0.5) * 0.6;
	vec2 id = vec2(floor(lane), row);
	vec2 f = vec2(fract(lane) - 0.5, fract(arc / rowh) - 0.5);
	f += (vec2(hash2(id + 1.3), hash2(id + 5.1)) - 0.5) * vec2(0.12, 0.1);
	float size = 0.75 + 0.35 * hash2(id + 9.2);
	vec2 d = vec2(f.x * step_x, f.y * rowh);
	// (bent: its middle sags, as a bean)
	d.y -= 22.0 * d.x * d.x * (hash2(id + 2.2) - 0.5);
	float e = length(vec2(d.x / (0.0105 * size), d.y / (0.0042 * size)));
	return (1.0 - smoothstep(0.75, 1.0, e)) * step(0.12, hash2(id + 7.7));
}

// How much of the cartoon eye's pupil covers `q` (from the pupil's middle, in the eye's flat): a keyhole pupil pointing to the snout.
float pupil_cover(vec2 q, float size, float aa) {
	// a round pupil with a point drawn out from it towards the snout (+x)
	float round_one = 1.0 - smoothstep(1.0 - aa, 1.0 + aa, length(q) / size);
	float along = q.x / size;
	float reach = 1.0 - along / 1.9;
	float point = step(0.0, along) * (1.0 - smoothstep(-aa, aa, abs(q.y) / size - 0.75 * reach));
	return max(round_one, point * step(0.0, reach));
}

// The cartoon eye at `e` (in the eye's own flat: x towards the snout, y up, 1 at its rim).
vec3 cartoon_eye(vec2 e) {
	float r = length(e);
	float aa = max(fwidth(r), 0.002) * 1.2;
	vec2 look = LOOK_REST + clamp(eye_look, vec2(-1.0), vec2(1.0)) * 0.24;
	vec2 q = e - look;
	float ri = length(q) / IRIS;
	float around = atan(q.y, q.x);
	vec3 iris = mix(eye_iris, eye_iris_dark, smoothstep(0.35, 1.0, ri)) * (0.85 + 0.15 * noise2(vec2(around * 7.0, ri * 2.0)));
	vec3 c = mix(iris, eye_white, smoothstep(1.0 - aa / IRIS, 1.0 + aa / IRIS, ri));
	// a dark ring round the iris
	c = mix(c, eye_iris_dark * 0.4, (1.0 - smoothstep(0.0, 0.07 + aa / IRIS, abs(ri - 1.0))) * 0.8);
	c = mix(c, vec3(0.01), pupil_cover(q, IRIS * PUPIL, aa / (IRIS * PUPIL)));
	// the highlight (two spots, up and forward; the big one kept below the lid)
	float glint = 1.0 - smoothstep(0.15 - aa, 0.15 + aa, length(e - vec2(0.24, min(0.30, LID_AT + LID_SLOPE * 0.24 - 0.2))));
	glint += (1.0 - smoothstep(0.065 - aa, 0.065 + aa, length(e - vec2(-0.12, -0.26)))) * 0.8;
	c = mix(c, vec3(1.0), clamp(glint, 0.0, 1.0));
	// the lid that gives it its character, a dark line along its edge
	float lid_y = LID_AT + LID_SLOPE * e.x;
	c = mix(c, eye_lid * 0.8, smoothstep(lid_y - aa, lid_y + aa, e.y));
	c = mix(c, vec3(0.03), 1.0 - smoothstep(0.035, 0.035 + 2.0 * aa, abs(e.y - lid_y)));
	// the outline
	c = mix(c, vec3(0.02, 0.025, 0.03), smoothstep(0.84 - aa, 0.84 + aa, r));
	return c;
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.42;
	float spec = 0.5;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		float cloud = noise2(vec2(xm * 14.0, q * 3.0) + 2.0);
		float behind = xm - gill_x(y);
		float arc = acos(clamp(q, -1.0, 1.0)) * 0.06;
		// The scales: small, in half-stepped rows, faint.
		float srow = floor(arc / 0.0045);
		float along = xm / 0.005 + 0.5 * mod(srow, 2.0);
		vec2 f = vec2(fract(along), fract(arc / 0.0045));
		float rim = smoothstep(0.75, 0.97, length(vec2(f.x, (f.y - 0.5) * 1.15)));
		float scaled = smoothstep(0.0, 0.01, behind) * (1.0 - smoothstep(0.85, 0.875, xm));
		// Dark olive back, olive-green flank going golden low down, a cream belly.
		float dark = smoothstep(0.2, 0.85, q + (cloud - 0.5) * 0.2);
		c = mix(olive, back, dark);
		c = mix(c, olive * vec3(1.35, 1.25, 0.9), smoothstep(-0.05, -0.45, q) * 0.5);
		c = mix(c, belly, smoothstep(-0.48, -0.72, q + (cloud - 0.5) * 0.08));
		// The spots: on the flank behind the head, fading out up the back and down to the belly;
		// smaller marbling on the cheek and the gill cover.
		float bean = beans(xm, arc + 0.004 * sin(xm * 9.0));
		float on_flank = smoothstep(0.85, 0.6, q) * smoothstep(-0.6, -0.3, q) * smoothstep(0.0, 0.03, behind) * (1.0 - smoothstep(0.85, 0.875, xm));
		c = mix(c, spot * mix(1.0, 0.75, dark), bean * on_flank * spots_show * 0.85);
		float marble = smoothstep(0.62, 0.78, noise2(vec2(xm * 160.0, y * 160.0)));
		float cheek = (1.0 - smoothstep(-0.02, 0.0, behind)) * smoothstep(0.12, 0.2, xm) * smoothstep(-0.5, -0.1, q) * (1.0 - smoothstep(0.4, 0.7, q));
		c = mix(c, spot * 0.85, marble * cheek * 0.3 * spots_show);
		c *= 1.0 - scaled * 0.1 * rim;
		// The lateral line: a faint row of pale dots along the middle of the flank.
		float lateral = (1.0 - smoothstep(0.0, 0.0015, abs(y - 0.004 * (1.0 - xm)))) * smoothstep(0.25, 0.3, xm) * step(0.5, fract(xm / 0.006));
		c = mix(c, belly * 0.8, lateral * 0.35);
		// The head: the line of the mouth, the gill cover's edge, the pores under the lower jaw.
		float mouth = (1.0 - smoothstep(0.0004, 0.0014, abs(y - mouth_y(xm)))) * (1.0 - smoothstep(MOUTH_TO - 0.008, MOUTH_TO, xm));
		c = mix(c, back * 0.5, mouth * 0.7);
		float span = smoothstep(-0.95, -0.75, q) * (1.0 - smoothstep(0.6, 0.8, q));
		float crease = (1.0 - smoothstep(0.0, 0.0025, abs(behind - 0.0015))) * 0.6 + (1.0 - smoothstep(0.0, 0.02, behind)) * step(0.0, behind) * 0.12;
		c = mix(c, c * 0.35, crease * span);
		float pores = 0.0;
		for (int k = 0; k < 5; k++) {
			float px = 0.03 + float(k) * 0.02;
			pores = max(pores, 1.0 - smoothstep(0.0012, 0.0022, length(vec2(xm - px, abs(rest.x) - 0.6 * (0.008 + 0.15 * px)))));
		}
		c = mix(c, fin_dark, pores * (p == 7 ? 1.0 : 0.0) * smoothstep(-0.5, -0.8, q) * 0.8);
		c += vec3(0.75, 0.8, 0.6) * 0.12 * glance * glance;
		rough = mix(0.32, 0.5, dark);
		spec = 0.5;
		// The inside of the mouth: pale, as a pike's is, darker towards the throat.
		c = mix(c, mouth_inside * mix(1.0, 0.45, smoothstep(0.05, 0.13, xm)), inside);
		rough = mix(rough, 0.7, inside);
		spec = mix(spec, 0.3, inside);
	} else if (p == 1 || p == 2 || p == 3) {
		// The dorsal, anal and tail fins: an olive-orange ground with rays and dark blotches in rows.
		float ray = pow(abs(cos(3.14159265 * UV.y * (p == 3 ? 20.0 : 16.0))), 6.0);
		c = mix(olive * 0.9, fin, smoothstep(0.0, 0.4, UV.x));
		c = mix(c, fin_low, 0.2 * UV.x * (p == 2 ? 1.0 : 0.3));
		float blot = smoothstep(0.52, 0.66, noise2(vec2(UV.x * 7.0, UV.y * (p == 3 ? 9.0 : 6.0)) + float(p) * 11.0));
		c = mix(c, fin_dark, blot * 0.75 * spots_show);
		c = mix(c, fin_dark * 1.5, ray * 0.25);
		rough = 0.55;
	} else if (p == 4 || p == 5) {
		// The pectoral and pelvic fins: pale orange, clear, with rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		c = mix(fin_low, fin_low * 1.15, UV.x) * (0.85 + 0.15 * ray);
		rough = 0.55;
		spec = 0.35;
	} else if (p == 8 || p == 9) {
		// A tooth: ivory, glossy, a little darker at its root.
		c = mix(tooth * 0.7, tooth, smoothstep(0.0, 0.5, UV.x));
		rough = 0.25;
		spec = 0.6;
	} else if (p == int(GILL_PART)) {
		// A gill arch: pale rakers along its front, a deep red fringe of filaments behind, darker deeper in
		// the throat (UV2.x, here how deep it stands).
		float fringe = 0.72 + 0.28 * cos(UV.x * 150.0);
		vec3 gill_r = gill_red * mix(1.0, fringe, smoothstep(0.3, 0.55, UV.y));
		c = mix(gill_raker, gill_r, smoothstep(0.02, 0.07, UV.y));
		c *= mix(1.0, 0.4, inside);
		rough = 0.4;
		spec = 0.5;
	} else {
		// An eye: a black pupil, a bright golden-yellow iris, a dark rim.
		float r = UV.x;
		float round_it = atan(rest.y - EYE_AT.y, rest.z + HALF - EYE_AT.x);
		vec3 iris = mix(vec3(0.85, 0.7, 0.25), vec3(0.6, 0.45, 0.12), smoothstep(0.55, 0.9, r)) * (0.8 + 0.2 * noise2(vec2(round_it * 9.0, r * 3.0)));
		c = mix(vec3(0.004, 0.004, 0.004), iris, smoothstep(0.42, 0.48, r));
		c = mix(c, back * 0.8, smoothstep(0.86, 1.0, r) * 0.85);
		rough = 0.14;
		spec = 0.6;
		// (in the eye's own flat: x towards the snout, y up, 1 at its rim)
		vec2 e = vec2(EYE_AT.x - (rest.z + HALF), rest.y - EYE_AT.y) / EYE_RADIUS;
		if (cartoon_eyes > 0.0) {
			c = mix(c, cartoon_eye(e), clamp(cartoon_eyes, 0.0, 1.0));
			rough = mix(rough, 0.5, clamp(cartoon_eyes, 0.0, 1.0));
			spec = mix(spec, 0.3, clamp(cartoon_eyes, 0.0, 1.0));
		}
		// the blink: a lid of its skin's colour drawn down over it
		float shut = clamp(blink, 0.0, 1.0);
		if (shut > 0.0) {
			float shut_y = mix(1.3, -1.3, shut);
			float aa = fwidth(e.y) * 1.5;
			c = mix(c, eye_lid, smoothstep(shut_y - aa, shut_y + aa, e.y));
		}
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
