shader_type spatial;
// The lanternfish (lanternfish.gd): every marking drawn here (no texture files), its swimming and its lights. What
// each point is comes from the model (tools/build_lanternfish.py): UV2.y the part (0 body, 1 the dorsal fin, 2 the
// anal fin, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a photophore, 9 the adipose
// fin). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its side
// (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing
// edge (1); on an eye or a photophore: x middle (0) to rim (1).
//
// It swims as small fish of its kind do (subcarangiform): a wave runs back along the body, small at the head,
// growing through the back half, the forked tail swung behind the wrist. The photophores glow (EMISSION: the only
// parts that do). All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 0.08;
const float HALF = 0.04;
// Where the tail fin is hinged (metres behind the snout): behind it the tail is one plate.
const float JOINT = 0.0655;
const float MOUTH_TO = 0.012;
const vec2 EYE_AT = vec2(0.0072, 0.0015);
// The lower jaw: how far back it runs, where its hinge is there (on the line of the mouth, whose slope is SLOPE),
// and how far it swings down, wide open (radians).
const float JAW_TO = 0.0125;
const float HINGE_Y = -0.00465;
const float SLOPE = 0.42;
const float GAPE_OPEN = 0.85;

// How far through a beat of its tail (0..1, it wraps). Set by Lanternfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the tail
// (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats: 1 as one cruising (its tail tips swing about 0.007 m either way), 0 still.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.95;
// How far its mouth is open: 0 shut, 1 wide open. The lower jaw swings down about its hinge.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How strongly its photophores glow (0 none, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;

// The dark back, and the blue-green that shines on it; the silvery flank and the duskier belly.
uniform vec3 back : source_color = vec3(0.03, 0.04, 0.06);
uniform vec3 back_sheen : source_color = vec3(0.06, 0.22, 0.26);
uniform vec3 silver : source_color = vec3(0.42, 0.46, 0.52);
uniform vec3 belly : source_color = vec3(0.26, 0.27, 0.3);
// How strongly the big scales' edges show.
uniform float scales_show = 0.5;
uniform vec3 fin : source_color = vec3(0.16, 0.18, 0.21);
uniform vec3 mouth_inside : source_color = vec3(0.08, 0.03, 0.04);
// The photophores' light.
uniform vec3 light_colour : source_color = vec3(0.3, 0.95, 0.9);

// The cartoon eye (0 the eye as made, 1 the cartoon one; Gulp uses 1). This one is a huge pale eerie stare: the eye, already big, grown to 1.35 times, a cold blue-white, a wide pale silver iris round a big round pupil, wide open with no lid showing. `eye_look` slides
// the iris and pupil (x + towards the snout, y + up; -1..1), `blink` closes the lid over it (0 open, 1 shut).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_white : source_color = vec3(0.88, 0.93, 0.96);
uniform vec3 eye_iris : source_color = vec3(0.62, 0.72, 0.8);
// The eye's dome: the middle of its base on the left side (x, y, z in the model; the right eye is at -x), its
// radius; how much bigger the cartoon eye is; the iris's and the pupil's radius (1 the eye's rim); the pupil
// squeezed across into a slit (1 round); how far the lid hangs down at rest (0 none, 1 to the middle) and how much
// lower it is towards the snout.
const vec3 EYE_BASE = vec3(0.00433, 0.0015, -0.0328);
const float EYE_RADIUS = 0.0031;
const float EYE_GROW = 1.35;
const float IRIS_R = 0.58;
const float PUPIL_R = 0.4;
const float PUPIL_SLIT = 1.0;
const float LID_REST = 0.0;
const float LID_SLANT = 0.0;


varying vec3 rest;
varying float part;
varying float inside;
varying vec2 eye_q;

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

float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.01 - 0.03 * s + 0.085 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.02;
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

// The cartoon eye at `q` (its own plane: x towards the snout, y up, 1 at the rim), its lid the colour `lid`;
// `lidded` says where the lid covers it.
vec3 cartoon_eye(vec2 q, vec3 lid, out float lidded) {
	float r = length(q);
	float aa = max(fwidth(r), 0.01) * 1.2;
	vec2 iq = q - clamp(eye_look, vec2(-1.0), vec2(1.0)) * max(0.78 - IRIS_R, 0.08) * vec2(1.0, 0.8);
	float ir = length(iq);
	vec3 c = eye_white * (1.0 - 0.25 * smoothstep(0.3, 0.8, r));
	// the iris: darker at its edge, lighter low in it; then the pupil, then the highlight towards the light
	vec3 iris = eye_iris * (0.55 + 0.6 * smoothstep(IRIS_R, 0.0, length(iq - vec2(0.0, -0.3 * IRIS_R))));
	iris = mix(iris, eye_iris * 0.25, smoothstep(IRIS_R * 0.75, IRIS_R, ir));
	c = mix(c, iris, 1.0 - smoothstep(IRIS_R - aa, IRIS_R + aa, ir));
	float pr = length(iq * vec2(PUPIL_SLIT, 1.0));
	c = mix(c, vec3(0.008), 1.0 - smoothstep(PUPIL_R - aa, PUPIL_R + aa, pr));
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.13 - aa, 0.13 + aa, length(q - vec2(-0.3, 0.12))));
	c = mix(c, vec3(0.9), 1.0 - smoothstep(0.055 - aa, 0.055 + aa, length(q - vec2(0.22, -0.3))));
	// the dark outline, a round one inside the eye's many-sided rim, and the skin round it out to the rim
	c = mix(c, vec3(0.01), smoothstep(0.8 - aa, 0.8 + aa, r));
	float skirt = smoothstep(0.93 - aa, 0.93 + aa, r);
	// the lid: hanging down at rest, lower towards the snout, closing with `blink`
	float edge = mix(1.05 - 2.0 * LID_REST, -1.1, clamp(blink, 0.0, 1.0)) - LID_SLANT * q.x * (1.0 - blink);
	c = mix(c, vec3(0.01), smoothstep(edge - 0.1 - aa, edge - 0.1 + aa, q.y));
	lidded = max(smoothstep(edge - aa, edge + aa, q.y), skirt);
	c = mix(c, lid, lidded);
	return c;
}



void vertex() {
	part = UV2.y;
	rest = VERTEX;
	inside = UV2.x;
	vec3 v = VERTEX;
	float xm = v.z + HALF;
	int p = int(part + 0.5);
	eye_q = vec2(0.0);
	if (p == 6) {
		// The eye: where each point is in its own plane (x towards the snout, y up, 1 at the rim); grown about its
		// middle for the cartoon eye, and squashed a little as it blinks.
		vec3 base = vec3(sign(v.x) * EYE_BASE.x, EYE_BASE.y, EYE_BASE.z);
		eye_q = vec2(base.z - v.z, v.y - base.y) / EYE_RADIUS;
		vec3 d = (v - base) * mix(1.0, EYE_GROW, cartoon_eyes);
		d.y *= 1.0 - 0.45 * blink * cartoon_eyes;
		v = base + d;
	}
	if (p == 7) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = clamp(gape, 0.0, 1.0) * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.005, JAW_TO - 0.0002, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	} else if (p == 4) {
		v.x += sign(rest.x) * UV.x * 0.0012 * sway * sin(6.2831853 * phase + 1.0);
	}
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0002) - side_at(zc - 0.0002)) / 0.0004;
	float turn = atan(slope) * (1.0 + 0.2 * smoothstep(0.86 * JOINT, JOINT, zc));
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

float gill_x(float y) {
	return 0.0195 - 60.0 * (y + 0.0005) * (y + 0.0005);
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	vec3 e = vec3(0.0);
	float rough = 0.4;
	float spec = 0.5;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		float behind = xm - gill_x(y);
		// The big scales, in rows that step half a scale from one to the next: each a little brighter or duller
		// than its neighbours (some lost, as a lanternfish's often are), its rear edge a dark arc.
		float arc = acos(clamp(q, -1.0, 1.0)) * 0.0075;
		float row = floor(arc / 0.0022);
		float along = xm / 0.0027 + 0.5 * mod(row, 2.0);
		vec2 f = vec2(fract(along), fract(arc / 0.0022));
		float rim = smoothstep(0.8, 1.0, length(vec2(f.x, (f.y - 0.5) * 1.3)));
		float foil = hash2(vec2(floor(along), row));
		float scaled = smoothstep(0.0, 0.0012, behind) * (1.0 - smoothstep(0.062, 0.066, xm)) * scales_show;
		// Dark above, silver on the flank (with a dark sheen of blue-green), duskier on the belly.
		float edge = 0.38 + (noise2(vec2(xm * 300.0, q * 3.0)) - 0.5) * 0.06;
		c = mix(belly, silver, smoothstep(-0.85, -0.45, q));
		c *= 1.0 + scaled * (0.3 * (foil - 0.5) - 0.3 * rim) - 0.35 * scaled * step(0.86, foil);
		c += silver * 0.3 * glance * glance;
		float dark = smoothstep(edge - 0.08, edge + 0.08, q);
		vec3 top = back * (1.0 + scaled * (0.3 * (foil - 0.5) - 0.3 * rim));
		top += back_sheen * (0.3 + 0.7 * glance * glance);
		c = mix(c, top, dark);
		c = mix(c, back_sheen * 0.6 + silver * 0.15, 0.25 * (1.0 - dark) * smoothstep(-0.3, 0.3, q));
		// The head: no scales; the line of the mouth and the gill cover's edge.
		float mouth = (1.0 - smoothstep(0.00004, 0.00014, abs(y - (0.0006 - SLOPE * xm)))) * smoothstep(0.0, 0.0002, xm) * (1.0 - smoothstep(MOUTH_TO - 0.0006, MOUTH_TO, xm));
		c = mix(c, vec3(0.02, 0.025, 0.03), mouth * 0.8);
		float crease = 1.0 - smoothstep(0.0, 0.00025, abs(behind - 0.0001));
		c = mix(c, c * 0.35, crease * smoothstep(-0.97, -0.82, q) * (1.0 - smoothstep(0.6, 0.8, q)));
		rough = mix(0.25, 0.45, dark);
		spec = mix(0.7, 0.45, dark);
		c = mix(c, mouth_inside, inside);
		rough = mix(rough, 0.6, inside);
		spec = mix(spec, 0.25, inside);
	} else if (p == 1 || p == 2 || p == 3 || p == 4 || p == 5 || p == 9) {
		// The fins: dusky, clearer towards their edges, fine rays (none on the adipose fin).
		float ray = pow(abs(cos(3.14159265 * UV.y * (p == 3 ? 10.0 : 8.0))), 6.0);
		c = mix(fin, fin * 1.8, smoothstep(0.4, 1.0, UV.x) * 0.6);
		c = mix(c, back, ray * 0.5 * (p == 9 ? 0.0 : 1.0));
		rough = 0.5;
	} else if (p == 6) {
		// The big eye: a big black pupil, a silver iris, a dark rim.
		float r = UV.x;
		c = mix(vec3(0.004, 0.005, 0.008), vec3(0.62, 0.66, 0.7), smoothstep(0.58, 0.64, r));
		c = mix(c, back, smoothstep(0.88, 1.0, r) * 0.8);
		rough = 0.1;
		spec = 0.7;
		if (cartoon_eyes > 0.0) {
			float lidded;
			c = mix(c, cartoon_eye(eye_q, silver * 0.85, lidded), cartoon_eyes);
			rough = mix(rough, mix(0.2, 0.6, lidded), cartoon_eyes);
			spec = mix(spec, mix(0.6, 0.3, lidded), cartoon_eyes);
		}
	} else {
		// A photophore: a bright middle, a silvery ring, a dark rim.
		float r = UV.x;
		float lit = 1.0 - smoothstep(0.4, 0.75, r);
		c = mix(vec3(0.6, 0.85, 0.85), silver, smoothstep(0.5, 0.8, r));
		c = mix(c, back, smoothstep(0.85, 1.0, r));
		e = light_colour * 1.8 * glow * lit;
		rough = 0.2;
		spec = 0.7;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = e;
}
