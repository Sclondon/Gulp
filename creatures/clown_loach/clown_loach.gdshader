shader_type spatial;
// The clown loach (clown_loach.gd): every marking drawn here (no texture files), and all of its
// moving. What each point is comes from the model (tools/build_clown_loach.py): UV2.y the part
// (0 body, 1 dorsal, 2 anal, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 a barbel).
// UV, on the body: x how far along, y how high on its side (1 the ridge of the back, 0 the keel
// of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge (1); on an
// eye: x middle (0) to rim (1); on a barbel: x root (0) to tip (1), y which barbel (over 8).
//
// It swims with a quick wriggle: a wave that runs back along the whole body and grows towards
// the tail, which swings wide; its pectoral fins fan about their roots; its barbels twitch. All of
// it is a function of `phase` alone (0 to 1 through one beat, with whole numbers of tail beats,
// fannings and twitches in a beat), so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model (the build script prints the pectoral numbers: SHADER).
const float LENGTH = 0.2;
const float HALF = 0.1;
const vec3 PECTORAL_ROOT = vec3(0.00985, -0.00657, -0.05100);
const vec3 PECTORAL_AXIS = vec3(-0.4633, -0.8623, -0.2043);

// How far through a beat it is (0..1, it wraps), and how many times in a beat its tail beats, its
// pectoral fins fan and its barbels twitch (whole numbers). Set by ClownLoach.
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of fish swimming tight rounds: "The fish need to bend more"):
// how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The
// head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
uniform float tail_beats = 4.0;
uniform float fans = 3.0;
uniform float twitches = 2.0;
// How widely it wriggles, for 1 as a loach on its way somewhere (its tail tips swing about a
// tenth of its length either way); 0 still.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.85;
// How far its pectoral fins fan (1: about a quarter of a right angle either way), and how far its
// barbels twitch (1: their tips about 2 mm).
uniform float fan = 1.0;
uniform float twitch = 1.0;

// The body: orange above, paler and yellower underneath, browner along the ridge of the back.
uniform vec3 orange : source_color = vec3(0.93, 0.45, 0.07);
uniform vec3 pale : source_color = vec3(0.98, 0.74, 0.34);
uniform vec3 ridge : source_color = vec3(0.62, 0.3, 0.08);
// The three bands, and the blue they glance with.
uniform vec3 band : source_color = vec3(0.03, 0.03, 0.045);
uniform vec3 band_glance : source_color = vec3(0.1, 0.13, 0.24);
// The fins: the red of the tail and the pelvic fins, the red-orange of the others, the dark of the
// dorsal and anal fins' roots and of the streaks on the pelvic fins.
uniform vec3 fin_red : source_color = vec3(0.86, 0.13, 0.03);
uniform vec3 fin_orange : source_color = vec3(0.95, 0.36, 0.06);
uniform vec3 fin_dark : source_color = vec3(0.045, 0.035, 0.045);
// The lips and the barbels.
uniform vec3 barbel : source_color = vec3(0.93, 0.66, 0.56);
// How much of each band shows (1 all of it; a loach "greys out" when it squabbles).
uniform float bands_show = 1.0;

varying vec3 rest;
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

// How far to one side the middle line of the body is, `xm` metres behind the snout: a wave that
// runs back along it, smallest behind the head, growing all the way to the tips of the tail.
float side_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * (0.016 - 0.062 * s + 0.146 * s * s);
	return sway * reach * sin(TAU * (tail_beats * phase - s / wave));
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
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part > 3.5 && part < 4.5) {
		// A pectoral fin fans about the line of its root, the fanning running out along it.
		float side = v.x < 0.0 ? -1.0 : 1.0;
		v.x *= side;
		n.x *= side;
		float a = -fan * (0.18 + 0.32 * sin(TAU * fans * phase - 1.3 * UV.x));
		float ca = cos(a);
		float sa = sin(a);
		vec3 r = v - PECTORAL_ROOT;
		v = PECTORAL_ROOT + r * ca + cross(PECTORAL_AXIS, r) * sa + PECTORAL_AXIS * dot(PECTORAL_AXIS, r) * (1.0 - ca);
		n = n * ca + cross(PECTORAL_AXIS, n) * sa + PECTORAL_AXIS * dot(PECTORAL_AXIS, n) * (1.0 - ca);
		v.x *= side;
		n.x *= side;
	} else if (part > 6.5) {
		// A barbel twitches, each in its own time, most at its tip.
		float id = UV.y * 8.0;
		float a = sin(TAU * twitches * phase + id * 2.4) + 0.5 * sin(TAU * (2.0 * twitches + 1.0) * phase + id * 4.1);
		float b = sin(TAU * (twitches + 1.0) * phase + id * 1.7);
		v += vec3(a, 0.3 * b, 0.6 * b) * (UV.x * UV.x * 0.0013 * twitch);
	}
	float xm = v.z + HALF;
	float zc = clamp(xm, 0.0, LENGTH);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0006) - side_at(zc - 0.0006)) / 0.0012;
	// (each slice of the body is turned to stay square to its middle line: a bend, not a shear)
	float turn = atan(slope);
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The edge of the gill cover, as the model has it (metres behind the snout, at a height).
float gill_x(float y) {
	return 0.047 - 14.0 * (y + 0.002) * (y + 0.002);
}

// The colour of the tail and of the plate it grows from, `s` along the fish: the orange of the
// body at the wrist, red by the fork.
vec3 tail_colour(float s) {
	return mix(mix(orange, fin_orange, smoothstep(0.73, 0.79, s)), fin_red, smoothstep(0.77, 0.9, s));
}

// How much of a band there is at `s` along the body, for a band whose middle is at `middle` and
// which is `half` wide either way (its edge a little soft).
float band_at(float s, float middle, float half) {
	return 1.0 - smoothstep(half - 0.005, half + 0.004, abs(s - middle));
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	if (p == 0) {
		float xm = rest.z + HALF;
		float s = xm / LENGTH;
		float q = UV.y;
		float y = rest.y;
		// (a fine grain, as of very small scales, and a slow unevenness)
		float grain = 0.6 * noise2(vec2(xm * 5200.0, q * 110.0)) + 0.4 * noise2(vec2(xm * 11000.0 + 7.0, q * 240.0));
		float cloud = noise2(vec2(s * 30.0, q * 7.0) + 4.0);
		c = mix(pale, orange, smoothstep(0.03, 0.5, q));
		c = mix(c, ridge, smoothstep(0.82, 1.0, q) * 0.55);
		// (the snout and the top of the head a little browner)
		c = mix(c, ridge, (1.0 - smoothstep(0.03, 0.2, s)) * smoothstep(0.35, 0.8, q) * 0.35);
		c *= 0.95 + 0.1 * grain;
		// The three bands, each a wedge (broad on the back, narrower below), their edges a little
		// uneven: one from the top of the head down through the eye to the cheek, one in front of
		// the dorsal fin, one from the dorsal fin down and back to the anal fin and the tail wrist.
		float wob = (cloud - 0.5) * 0.014;
		float b1 = band_at(s + wob * 0.5, 0.086 + 0.094 * q, 0.012 + 0.03 * q) * smoothstep(0.16, 0.34, q);
		float b2 = band_at(s + wob, 0.332 + 0.02 * q, 0.042 + 0.04 * q) * smoothstep(0.0, 0.05, q);
		float b3 = band_at(s + wob, 0.632 - 0.076 * q, 0.079);
		float dark = max(b1, max(b2, b3)) * bands_show;
		c = mix(c, band * (0.9 + 0.2 * grain) + band_glance * glance * glance, dark);
		// The head: the edge of the gill cover, the small mouth under the tip of the snout and its
		// pale lips.
		float span = smoothstep(0.03, 0.12, q) * (1.0 - smoothstep(0.75, 0.9, q));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.0006, abs(behind - 0.0003))) * 0.5 + (1.0 - smoothstep(0.0, 0.005, behind)) * step(0.0, behind) * 0.2;
		c = mix(c, c * 0.35, crease * span);
		float under = 1.0 - smoothstep(0.22, 0.36, q);
		c = mix(c, barbel, under * (1.0 - smoothstep(0.006, 0.011, xm)) * 0.8);
		float mouth = (1.0 - smoothstep(0.0003, 0.0009, abs(xm - 0.0052 + 0.004 * q))) * (1.0 - smoothstep(0.1, 0.2, q));
		c = mix(c, vec3(0.12, 0.03, 0.03), mouth * 0.9);
		// The plate the tail grows from: it reddens into the tail (as the tail does: tail_colour).
		c = mix(c, tail_colour(s) * (0.95 + 0.1 * grain), smoothstep(0.74, 0.785, s) * (1.0 - dark));
		rough = mix(0.36, 0.5, dark);
		spec = mix(0.55, 0.4, dark);
	} else if (p == 1) {
		// The dorsal: dark from its root (the third band runs up into it), its rays and its edge
		// red-orange.
		float ray = pow(abs(cos(3.14159265 * UV.y * 10.0)), 6.0);
		c = mix(fin_dark, fin_orange * 0.8, smoothstep(0.5, 1.0, UV.x) * 0.75);
		c = mix(c, fin_orange * 0.75, ray * smoothstep(0.25, 0.9, UV.x) * 0.45);
		c = mix(c, fin_orange, (1.0 - smoothstep(0.0, 0.07, UV.y)) * smoothstep(0.2, 0.6, UV.x) * 0.6);
		rough = 0.5;
	} else if (p == 2) {
		// The anal fin: dark at its root, red towards its edge.
		float ray = pow(abs(cos(3.14159265 * UV.y * 7.0)), 6.0);
		c = mix(fin_dark, fin_red, smoothstep(0.35, 0.85, UV.x));
		c = mix(c, c * 0.6, ray * 0.35);
		rough = 0.5;
	} else if (p == 3) {
		// The tail: red, the reddest of its fins, fine rays, a little darker at the tips.
		float ray = 0.5 + 0.5 * cos(UV.y * 80.0);
		c = tail_colour((rest.z + HALF) / LENGTH) * (0.84 + 0.22 * ray * smoothstep(0.76, 0.84, (rest.z + HALF) / LENGTH));
		c = mix(c, c * 0.7, smoothstep(0.75, 1.0, UV.x) * 0.5);
		rough = 0.5;
	} else if (p == 4) {
		// A pectoral fin: red-orange, paler at its root, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		c = mix(orange, fin_orange, smoothstep(0.0, 0.5, UV.x));
		c = mix(c, fin_red, smoothstep(0.5, 1.0, UV.x) * 0.5) * (0.85 + 0.2 * ray);
		rough = 0.5;
	} else if (p == 5) {
		// A pelvic fin: red, with dark streaks between its rays.
		float ray = pow(abs(cos(3.14159265 * UV.y * 6.0)), 3.0);
		c = fin_red * (0.9 + 0.15 * ray);
		c = mix(c, fin_dark, (1.0 - ray) * smoothstep(0.1, 0.45, UV.x) * (1.0 - smoothstep(0.7, 1.0, UV.x)) * 0.6);
		rough = 0.5;
	} else if (p == 6) {
		// An eye: a black pupil, a thin dark gold iris, a dark rim (it sits in the first band).
		float r = UV.x;
		c = mix(vec3(0.004, 0.004, 0.006), vec3(0.42, 0.26, 0.08), smoothstep(0.6, 0.68, r));
		c = mix(c, band, smoothstep(0.82, 0.98, r));
		rough = 0.12;
		spec = 0.65;
	} else {
		// A barbel: pale and fleshy.
		c = barbel * (0.9 + 0.1 * UV.x);
		rough = 0.55;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
