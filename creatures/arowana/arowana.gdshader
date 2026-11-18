shader_type spatial;
// The silver arowana (arowana.gd): every marking drawn here (no texture files), and its swimming.
// What each point is comes from the model (tools/build_arowana.py): UV2.y the part (0 body, 1 the
// dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower
// jaw, 8 a barbel). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far
// along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x
// root (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim
// (1); on a barbel: x root to tip.
//
// It swims as arowanas do: a long, slow wave down most of the body, the long dorsal and anal fins
// and the small tail working together behind it. It can also be arched in the up-and-down plane
// (`arch`), for a leap. All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 0.9;
const float HALF = 0.45;
// Where the tail fin is hinged (metres behind the jaw): behind it the tail is one plate.
const float JOINT = 0.805;
const float MOUTH_TO = 0.106;
const vec2 EYE_AT = vec2(0.068, 0.040);
// The lower jaw: how far back it runs (metres behind its tip), where its hinge is there (on the
// line of the mouth), and how far it swings down, wide open (radians).
const float JAW_TO = 0.105;
const float HINGE_Y = -0.005;
const float GAPE_OPEN = 0.8;
// The snout tips up a little as the mouth opens (radians, wide open), less and less back to the
// hinge.
const float SNOUT_LIFT = 0.06;

// How far through a beat of its tail (0..1, it wraps). Set by Arowana.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is. (As the yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// Arching, for a leap: how far the whole body is bent in the up-and-down plane, in radians from
// nose to tail, about its middle. More than 0 the back is bowed up and the head and tail hang down
// (as at the top of a leap, and as it falls back); less than 0 the head and the tail are raised
// (as it gathers to spring up out of the water).
uniform float arch = 0.0;
// How widely it beats, for 1 an arowana cruising (its tail swings about 0.06 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.85;
// How far its mouth is open: 0 shut, 1 wide open (as when it snatches prey from the surface). The
// lower jaw with its barbels swings down about its hinge, and the snout tips up a little.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The back, the silver flank and the white belly.
uniform vec3 back : source_color = vec3(0.17, 0.22, 0.21);
uniform vec3 silver : source_color = vec3(0.78, 0.80, 0.82);
uniform vec3 belly : source_color = vec3(0.93, 0.93, 0.91);
// The great scales: the pink flush at the edge of each, the blue-green sheen of the scales near
// the back, how strongly the scales show.
uniform vec3 scale_rim : source_color = vec3(0.88, 0.58, 0.60);
uniform vec3 sheen : source_color = vec3(0.45, 0.65, 0.85);
uniform float scales_show = 1.0;
// The fins and the barbels.
uniform vec3 fin : source_color = vec3(0.24, 0.27, 0.30);
uniform vec3 fin_dark : source_color = vec3(0.07, 0.08, 0.10);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.30, 0.18, 0.18);

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
	float reach = LENGTH * (0.009 - 0.03 * s + 0.078 * s * s);
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

// The whole body laid round an arc in the up-and-down plane, about its middle (see `arch`).
void arch_bend(inout vec3 v, inout vec3 n) {
	if (abs(arch) < 0.001) {
		return;
	}
	float k = arch / LENGTH;
	float r = 1.0 / k;
	float a = v.z * k;
	float c = cos(a);
	float sn = sin(a);
	float rr = r + v.y;
	v = vec3(v.x, rr * c - r, rr * sn);
	n = vec3(n.x, n.y * c - n.z * sn, n.y * sn + n.z * c);
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
	vec3 nn = NORMAL;
	float xm = v.z + HALF;
	float open = clamp(gape, 0.0, 1.0);
	if (part > 6.5) {
		// The lower jaw and its barbels swing down whole about the hinge; its back slides up into
		// the throat, inside the body.
		hinge_turn(v, nn, open * GAPE_OPEN);
	} else if (part < 0.5 || (part > 5.5 && part < 6.5)) {
		// The head above the line of the mouth (with the roof of the mouth and the eyes) tips up a
		// little.
		hinge_turn(v, nn, -open * SNOUT_LIFT * (1.0 - smoothstep(JAW_TO * 0.4, JAW_TO * 1.1, xm)));
	}
	xm = v.z + HALF;
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.002) - side_at(zc - 0.002)) / 0.004;
	float turn = atan(slope) * (1.0 + 0.15 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(nn.x * c + nn.z * sn, nn.y, -nn.x * sn + nn.z * c);
	vec3 bent = VERTEX;
	vec3 bent_normal = NORMAL;
	curl_bend(bent, bent_normal);
	arch_bend(bent, bent_normal);
	VERTEX = bent;
	NORMAL = bent_normal;
}

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return 0.0580 - 0.60 * xm;
}

float gill_x(float y) {
	return 0.178 - 5.0 * (y - 0.005) * (y - 0.005);
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
		float behind = xm - gill_x(y);
		float cloud = noise2(vec2(xm * 20.0, q * 3.0) + 5.0);
		// The great scales: about eight rows from the back to the belly, each row half a scale along
		// from the next. Each scale is a round plate; the one in front overlaps the one behind, so
		// what shows of each is its back part, bounded by the round back edges of the scales in front
		// of it. Its back edge is flushed pink and outlined.
		vec2 g = vec2((xm - 0.16) / 0.026, acos(clamp(q, -1.0, 1.0)) / 3.14159265 * 8.5);
		float best = 1e9;
		float r = 1.0;
		vec2 which = vec2(0.0);
		for (int dj = -1; dj <= 1; dj++) {
			float j = floor(g.y) + float(dj);
			float off = 0.5 * mod(j, 2.0);
			for (int di = -1; di <= 1; di++) {
				float i = floor(g.x - off) + float(di);
				vec2 centre = vec2(i + off, j + 0.5);
				float dist = length((g - centre) * vec2(1.0, 0.95));
				if (dist < 0.92 && centre.x < best) {
					best = centre.x;
					r = dist / 0.92;
					which = vec2(i, j);
				}
			}
		}
		float foil = hash2(which);
		float scaled = smoothstep(0.0, 0.006, behind) * (1.0 - smoothstep(0.80, 0.82, xm)) * scales_show;
		float rim = smoothstep(0.62, 0.94, r) * scaled;
		float line = smoothstep(0.93, 1.0, r) * scaled;
		// The ground: a narrow dark band along the back, silver flanks, white below.
		float dark = smoothstep(0.62, 0.9, q + (cloud - 0.5) * 0.08);
		c = mix(silver, belly, smoothstep(-0.2, -0.7, q));
		c = mix(c, sheen * 0.85, smoothstep(0.2, 0.62, q) * 0.45);
		c *= 1.0 + scaled * (0.1 * (foil - 0.5) + 0.06 * (1.0 - r));
		c = mix(c, scale_rim, rim * 0.45 * (1.0 - dark));
		c = mix(c, back * 1.2, line * 0.5);
		c = mix(c, back, dark);
		// (each scale catches the light as a whole, a little differently from its neighbours)
		c += mix(sheen, vec3(1.0), 0.5) * 0.22 * glance * glance * (0.6 + 0.8 * foil * scaled);
		// The head: bony, silvery, with a faint mosaic over the cheek and the gill cover; the line of
		// the mouth, the gill cover's edge.
		float head = 1.0 - smoothstep(-0.004, 0.0, behind);
		float mosaic = noise2(vec2(xm * 220.0, y * 220.0));
		c = mix(c, c * (0.94 + 0.1 * mosaic), head * smoothstep(-0.7, -0.2, q));
		float mouth = (1.0 - smoothstep(0.0003, 0.0011, abs(y - mouth_y(xm)) * 0.8)) * (1.0 - smoothstep(MOUTH_TO - 0.006, MOUTH_TO, xm));
		c = mix(c, back * 0.4, mouth * 0.8);
		float span = smoothstep(-0.95, -0.75, q) * (1.0 - smoothstep(0.6, 0.8, q));
		float crease = (1.0 - smoothstep(0.0, 0.0018, abs(behind - 0.001))) * 0.6 + (1.0 - smoothstep(0.0, 0.012, behind)) * step(0.0, behind) * 0.12;
		c = mix(c, c * 0.35, crease * span);
		rough = mix(0.28, 0.5, dark);
		spec = mix(0.7, 0.4, dark);
		// The inside of the mouth.
		c = mix(c, mouth_inside, inside);
		rough = mix(rough, 0.8, inside);
		spec = mix(spec, 0.2, inside);
	} else if (p == 1 || p == 2) {
		// The dorsal and anal fins: dark grey with a blue tint, fine rays, darker towards the back
		// and the edge.
		float ray = pow(abs(cos(3.14159265 * UV.y * (p == 1 ? 34.0 : 40.0))), 6.0);
		c = mix(fin * 1.2, fin, smoothstep(0.0, 0.6, UV.y));
		c = mix(c, fin_dark, smoothstep(0.55, 1.0, UV.x) * 0.5);
		c = mix(c, fin_dark, ray * 0.25);
		c += sheen * 0.1 * glance;
		rough = 0.5;
	} else if (p == 3) {
		// The tail: dark grey, rays fanning back, darker at its edge.
		float ray = 0.5 + 0.5 * cos(UV.y * 70.0);
		c = mix(fin * 1.1, fin_dark, smoothstep(0.4, 1.0, UV.x) * 0.6) * (0.85 + 0.15 * ray);
		c = mix(c, fin_dark, (1.0 - smoothstep(0.0, 0.15, UV.y)) * smoothstep(0.3, 0.7, UV.x) * 0.5);
		rough = 0.5;
	} else if (p == 4 || p == 5) {
		// The pectoral and pelvic fins: grey, clear, with rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 70.0);
		c = mix(fin * 1.6, fin * 1.25, UV.x) * (0.85 + 0.15 * ray);
		rough = 0.5;
		spec = 0.35;
	} else if (p == 8) {
		// A barbel: dark grey, paler at its tip.
		c = mix(fin * 0.8, fin * 1.6, smoothstep(0.5, 1.0, UV.x));
		rough = 0.55;
	} else {
		// An eye: a big black pupil, a dark iris with a gold ring round it, a dark rim.
		float r = UV.x;
		float round_it = atan(rest.y - EYE_AT.y, rest.z + HALF - EYE_AT.x);
		vec3 iris = mix(vec3(0.8, 0.62, 0.25), vec3(0.25, 0.22, 0.18), smoothstep(0.62, 0.8, r)) * (0.8 + 0.2 * noise2(vec2(round_it * 9.0, r * 3.0)));
		c = mix(vec3(0.004, 0.004, 0.006), iris, smoothstep(0.5, 0.56, r));
		c = mix(c, back * 0.7, smoothstep(0.88, 1.0, r) * 0.85);
		rough = 0.14;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
