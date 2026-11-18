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
render_mode cull_back;

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

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
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
	int p = int(part + 0.5);
	float upper = smoothstep(-0.25, 0.1, rest_normal.y);
	float xm = rest.z + HALF;
	float side = abs(rest.x);
	vec3 c;
	float rough = 0.5;
	float spec = 0.5;
	// The upper side: brown-olive, smooth, darker towards the wing tips and edges; a faint cloud.
	float cloud = 0.6 * noise2(rest.xz * 9.0) + 0.4 * noise2(rest.xz * 31.0 + 5.0);
	vec3 above = mix(back, back_dark, 0.75 * smoothstep(0.2, 0.62, side) + 0.25 * smoothstep(0.35, 0.7, cloud));
	above *= 0.92 + 0.16 * noise2(rest.xz * 240.0);
	if (p == 0) {
		// The spiracles: a dark opening behind each eye.
		vec2 hole = vec2((side - 0.064) / 0.007, (xm - 0.088) / 0.013);
		above = mix(above, back_dark * 0.3, 1.0 - smoothstep(0.7, 1.0, length(hole)));
		// The under side: white, dusky at the wings' edges; five gill slits each side; the
		// mouth, dark under its plate; the nostrils ahead of it.
		vec3 below = mix(belly, belly_dusk, 0.8 * smoothstep(0.3, 0.6, side + 0.25 * smoothstep(0.3, 0.65, xm)));
		for (int k = 0; k < 5; k++) {
			float at = 0.155 + 0.021 * float(k);
			float slit = (1.0 - smoothstep(0.0012, 0.0026, abs(xm - at - 0.25 * (side - 0.05))));
			slit *= smoothstep(0.03, 0.036, side) * (1.0 - smoothstep(0.06 - 0.002 * float(k), 0.066 - 0.002 * float(k), side));
			below = mix(below, mouth * 1.5, slit * 0.85);
		}
		float in_mouth = (1.0 - smoothstep(MOUTH_WIDE * 0.5 - 0.009, MOUTH_WIDE * 0.5 - 0.006, side));
		in_mouth *= smoothstep(MOUTH_HINGE - MOUTH_LONG + 0.003, MOUTH_HINGE - MOUTH_LONG + 0.006, xm) * (1.0 - smoothstep(MOUTH_HINGE - 0.002, MOUTH_HINGE + 0.001, xm));
		below = mix(below, mouth, in_mouth);
		vec2 nostril = vec2((side - 0.022) / 0.008, (xm - 0.058) / 0.005);
		below = mix(below, mouth * 1.5, 1.0 - smoothstep(0.7, 1.0, length(nostril)));
		c = mix(below, above, upper);
		rough = mix(0.55, 0.5, upper);
	} else if (p == 1) {
		// The mouth's plate: the belly's colour, a shade greyer, dark at its hinge.
		c = belly * vec3(0.9, 0.87, 0.86);
		c = mix(c, belly_dusk, 0.5 * smoothstep(0.75, 1.0, UV.x));
	} else if (p == 2) {
		c = mix(belly, above, upper);
	} else if (p == 5) {
		// An eye: a dark pupil (a level slot), a dull gold iris, the skin's colour at its rim.
		float r = UV.x;
		c = mix(vec3(0.01, 0.01, 0.012), iris, smoothstep(0.42, 0.5, r));
		c = mix(c, back * 0.7, smoothstep(0.76, 0.9, r));
		rough = 0.12;
		spec = 0.6;
	} else if (p == 6) {
		// The tail: the back's colour at its root, near black towards its tip.
		c = mix(mix(belly_dusk, above, smoothstep(-0.6, 0.0, rest_normal.y)), back_dark * 0.5, smoothstep(0.05, 0.5, UV.x));
	} else {
		c = spine * (0.85 + 0.15 * noise2(vec2(UV.x * 60.0, 0.0)));
		rough = 0.5;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
