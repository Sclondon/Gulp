shader_type spatial;
// The red-bellied piranha (piranha.gd): every marking drawn here (no texture files), and its
// swimming. What each point is comes from the model (tools/build_piranha.py): UV2.y the part
// (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an
// eye, 7 the lower jaw, 8 an upper tooth, 9 a lower tooth, 10 the adipose fin). UV2.x: 1 inside
// the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its side
// (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y leading
// edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1); on a tooth: x root to point.
//
// It swims as deep-bodied carangiform fish do: the front two thirds of the body hardly bend, the
// wave grows fast over the back third and the broad tail swings behind a short wrist. All of it
// is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 0.30;
const float HALF = 0.15;
// Where the tail fin is hinged (metres behind the jaw): behind it the tail is one plate.
const float JOINT = 0.242;
const float MOUTH_TO = 0.031;
const vec2 EYE_AT = vec2(0.042, 0.0205);
// The lower jaw: how far back it runs (metres behind its tip), where its hinge is there (on the
// line of the mouth), and how far it swings down, wide open (radians).
const float JAW_TO = 0.030;
const float HINGE_Y = -0.0156;
const float GAPE_OPEN = 0.72;

// How far through a beat of its tail (0..1, it wraps). Set by Piranha.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is. (As the yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely it beats, for 1 a piranha cruising (its tail tips swing about 0.025 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.05;
// How far its mouth is open: 0 shut, 1 wide open (as when it bites). The lower jaw swings down
// about its hinge and both rows of teeth show.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The back, the silver-grey flank, and the brassy tint low on the flank.
uniform vec3 back : source_color = vec3(0.20, 0.23, 0.23);
uniform vec3 silver : source_color = vec3(0.60, 0.63, 0.64);
uniform vec3 brass : source_color = vec3(0.66, 0.55, 0.36);
// The belly, the chin and the throat.
uniform vec3 red : source_color = vec3(0.82, 0.22, 0.07);
// The fine sparkling spots over the flank: how strongly they show.
uniform float sparkle = 1.0;
// The fins: grey, the tail's dark band; the red of the anal and lower fins.
uniform vec3 fin : source_color = vec3(0.30, 0.32, 0.32);
uniform vec3 fin_dark : source_color = vec3(0.04, 0.04, 0.05);
uniform vec3 fin_red : source_color = vec3(0.70, 0.17, 0.06);
// The teeth, and the inside of the mouth.
uniform vec3 tooth : source_color = vec3(0.92, 0.90, 0.82);
uniform vec3 mouth_inside : source_color = vec3(0.24, 0.05, 0.05);
// The gills (seen through the wide-open mouth): the red of their filaments and the pale of their rakers.
uniform vec3 gill_red : source_color = vec3(0.62, 0.05, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.80, 0.72);
// As the model has it (tools/build_piranha.py, its THROAT_Q line): the point at the back of the throat, where the
// old wall across the back of the mouth is drawn to so that it becomes the throat's floor; and the gills' part.
const vec3 THROAT_Q = vec3(0.0, -0.02560, -0.09521);
const float GILL_PART = 11.0;

// The cartoon eye: 0 the eye as it is in life (the default), 1 the cartoon eye: bigger, a pale white round
// a coloured iris, a big dark pupil, a highlight that stays put up and forward (towards the light from the
// surface) and a dark outline, so that it reads from far off. Its character: a mean, hungry glare: a blood-red iris round a small round pupil, not much white, and a heavy
// brow slanting down towards the snout, the lid cutting across the top of the eye in a scowl.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where it looks: x towards its snout (less than 0 back towards its tail), y up; -1..1. Both eyes look the
// same way. (The cartoon eye's iris and pupil slide.)
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashed flat and a lid of its skin's colour drawn down over it (a fish has
// no lids; this is the cartoon's blink).
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.95, 0.20, 0.08);
uniform vec3 eye_iris_dark : source_color = vec3(0.45, 0.04, 0.02);
uniform vec3 eye_white : source_color = vec3(0.95, 0.92, 0.84);
uniform vec3 eye_lid : source_color = vec3(0.38, 0.42, 0.42);

// As the model has it (the build script prints them: its EYE line): the left eye's middle on the skin, the
// way it faces, how the skin falls away from it going up and going along (along its normal, per metre
// squared), and the eye's radius.
const vec3 EYE_MID = vec3(0.01712, 0.02050, -0.10800);
const vec3 EYE_OUT = vec3(0.9562, 0.2059, -0.2082);
const vec2 EYE_SAG = vec2(-6.022, -5.360);
const float EYE_RADIUS = 0.0086;
// The cartoon eye: how much bigger it is, the iris's size (of the eye's), the pupil's (of the iris's),
// where it looks when `eye_look` is 0 (in the eye's flat, 1 its rim), and its lid's line: how high it
// comes down (1 the top of the eye) and how it slants (more than 0 higher towards the snout).
const float EYE_GROW = 1.45;
const float IRIS = 0.72;
const float PUPIL = 0.36;
const vec2 LOOK_REST = vec2(0.10, -0.04);
const float LID_AT = 0.30;
const float LID_SLOPE = -0.42;

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
	float reach = LENGTH * (0.006 - 0.022 * s + 0.072 * s * s * s);
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
	float xm = v.z + HALF;
	if ((part > 6.5 && part < 7.5) || (part > 8.5 && part < 9.5)) {
		// The lower jaw and its teeth swing down whole about the hinge (the line across the head
		// through both corners of the mouth); its back slides up into the throat, inside the body.
		float a = clamp(gape, 0.0, 1.0) * GAPE_OPEN;
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0008) - side_at(zc - 0.0008)) / 0.0016;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(NORMAL.x * c + NORMAL.z * sn, NORMAL.y, -NORMAL.x * sn + NORMAL.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return -0.0120 - 0.12 * xm;
}

float gill_x(float y) {
	return 0.074 - 7.0 * (y - 0.004) * (y - 0.004);
}

// How much of the cartoon eye's pupil covers `q` (from the pupil's middle, in the eye's flat): a small round pupil.
float pupil_cover(vec2 q, float size, float aa) {
	return 1.0 - smoothstep(1.0 - aa, 1.0 + aa, length(q) / size);
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
		float cloud = noise2(vec2(xm * 45.0, q * 3.0) + 7.0);
		float behind = xm - gill_x(y);
		// The scales: small, in rows that step half a scale from one to the next.
		float arc = acos(clamp(q, -1.0, 1.0)) * 0.042;
		float row = floor(arc / 0.0026);
		float along = xm / 0.0028 + 0.5 * mod(row, 2.0);
		vec2 f = vec2(fract(along), fract(arc / 0.0026));
		float rim = smoothstep(0.72, 0.97, length(vec2(f.x, (f.y - 0.5) * 1.15)));
		float scaled = smoothstep(0.0, 0.004, behind) * (1.0 - smoothstep(0.236, 0.246, xm));
		// Silver-grey flank, darker back, a brassy flush low on the flank.
		float dark = smoothstep(0.15, 0.75, q + (cloud - 0.5) * 0.15);
		c = mix(silver, back, dark);
		c = mix(c, brass, smoothstep(0.0, -0.35, q) * 0.45);
		// The red: the belly from the throat to the anal fin, up over the chin, the lower jaw and the
		// cheek; it fades out over the tail wrist.
		float red_line = mix(-0.05, -0.42, smoothstep(0.03, 0.10, xm)) + (cloud - 0.5) * 0.12;
		float reds = smoothstep(red_line + 0.12, red_line - 0.12, q) * (1.0 - smoothstep(0.17, 0.225, xm));
		c = mix(c, red, reds);
		c *= 1.0 - scaled * 0.12 * rim;
		// The fine sparkling spots: specks scattered over the flank, each glinting as it turns to the
		// light, darker spots among them on the upper flank.
		vec2 cell = vec2(xm / 0.0036, arc / 0.0036);
		vec2 id = floor(cell);
		vec2 at = vec2(hash2(id + 3.1), hash2(id + 8.7)) * 0.6 + 0.2;
		float dot_here = 1.0 - smoothstep(0.1, 0.22, length(fract(cell) - at));
		float kind = hash2(id + 1.7);
		float glint = 0.55 + 0.9 * pow(clamp(dot(normalize(NORMAL), normalize(VIEW + vec3(kind - 0.5, hash2(id) - 0.5, 0.0))), 0.0, 1.0), 6.0);
		float spread = smoothstep(-0.55, -0.15, q) * smoothstep(0.065, 0.09, xm) * (1.0 - smoothstep(0.215, 0.235, xm));
		c = mix(c, vec3(0.95, 0.96, 0.97) * glint, dot_here * step(0.35, kind) * spread * 0.75 * sparkle);
		c = mix(c, back * 0.4, dot_here * (1.0 - step(0.35, kind)) * spread * smoothstep(0.0, 0.5, q) * 0.6 * sparkle);
		// The shoulder blotch: a dark smudge just behind the top of the gill cover.
		float blotch = 1.0 - smoothstep(0.0, 0.012, length(vec2(behind - 0.012, (y - 0.018) * 0.8)));
		c = mix(c, back * 0.55, blotch * 0.55 * smoothstep(-0.1, 0.2, q));
		// The head: the line of the mouth, the gill cover's edge, darker over the snout.
		float mouth = (1.0 - smoothstep(0.00015, 0.0005, abs(y - mouth_y(xm)))) * (1.0 - smoothstep(MOUTH_TO - 0.003, MOUTH_TO, xm));
		c = mix(c, vec3(0.08, 0.04, 0.04), mouth * 0.75);
		float span = smoothstep(-0.95, -0.75, q) * (1.0 - smoothstep(0.55, 0.75, q));
		float crease = (1.0 - smoothstep(0.0, 0.0009, abs(behind - 0.0005))) * 0.6 + (1.0 - smoothstep(0.0, 0.006, behind)) * step(0.0, behind) * 0.15;
		c = mix(c, c * 0.35, crease * span);
		c = mix(c, back * 0.7, (1.0 - smoothstep(0.0, 0.03, xm)) * smoothstep(-0.1, 0.5, q) * 0.5);
		c += vec3(0.85, 0.88, 0.9) * 0.18 * glance * glance * (1.0 - reds * 0.6);
		rough = mix(0.3, 0.5, dark);
		spec = mix(0.65, 0.4, dark);
		// The inside of the mouth.
		c = mix(c, mouth_inside, inside);
		rough = mix(rough, 0.8, inside);
		spec = mix(spec, 0.2, inside);
	} else if (p == 1) {
		// The dorsal fin: grey, darker at its root, about sixteen rays.
		float ray = pow(abs(cos(3.14159265 * UV.y * 16.0)), 6.0);
		c = mix(back * 0.9, fin * 1.1, smoothstep(0.0, 0.5, UV.x));
		c = mix(c, fin_dark, ray * 0.3);
		c = mix(c, fin_dark, smoothstep(0.8, 1.0, UV.x) * 0.35);
	} else if (p == 10) {
		// The adipose fin: small, fleshy, dark with a pale rim.
		c = mix(back * 0.5, fin_dark, UV.x * 0.6);
		c = mix(c, fin, smoothstep(0.8, 1.0, UV.x) * 0.4);
		rough = 0.6;
	} else if (p == 2) {
		// The anal fin: red, with a dark band along its edge.
		float ray = 0.5 + 0.5 * cos(UV.y * 120.0);
		c = mix(red * 0.9, fin_red, UV.x) * (0.88 + 0.12 * ray);
		c = mix(c, fin_dark, smoothstep(0.72, 0.92, UV.x) * 0.85);
	} else if (p == 3) {
		// The tail: pale grey at its root, a broad dark band along its back edge.
		float ray = 0.5 + 0.5 * cos(UV.y * 80.0);
		c = mix(silver * 0.75, fin, smoothstep(0.05, 0.35, UV.x)) * (0.85 + 0.15 * ray);
		c = mix(c, fin_dark, smoothstep(0.6, 0.8, UV.x) * 0.9);
		rough = 0.5;
	} else if (p == 4) {
		// A pectoral fin: clear orange-red.
		float ray = 0.5 + 0.5 * cos(UV.y * 55.0);
		c = mix(fin_red * 1.1, fin * 1.4, 0.3 * UV.x) * (0.85 + 0.15 * ray);
		rough = 0.5;
		spec = 0.35;
	} else if (p == 5) {
		// A pelvic fin: red.
		c = mix(red, fin_red, 0.5 * UV.x) * (0.9 + 0.1 * cos(UV.y * 40.0));
	} else if (p == 8 || p == 9) {
		// A tooth: ivory, glossy, a little darker at its root.
		c = mix(tooth * 0.75, tooth, smoothstep(0.0, 0.5, UV.x));
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
		// An eye: a big black pupil, a silver iris washed with red-gold, a dark rim.
		float r = UV.x;
		float round_it = atan(rest.y - EYE_AT.y, rest.z + HALF - EYE_AT.x);
		vec3 iris = mix(vec3(0.7, 0.66, 0.6), vec3(0.75, 0.32, 0.12), smoothstep(0.55, 0.8, r) * 0.6) * (0.85 + 0.15 * noise2(vec2(round_it * 9.0, r * 3.0)));
		c = mix(vec3(0.004, 0.004, 0.006), iris, smoothstep(0.48, 0.54, r));
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
