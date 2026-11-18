shader_type spatial;
// The Pacific krill (krill.gd): every marking drawn here (no texture files), its beating
// swimmerets, its feeding basket and its tail flick. What each point is comes from the model
// (tools/build_krill.py): UV2.y the part times 16 plus which one of them it is (0 the body, 1 a
// leg of the feeding basket, 2 a swimmeret, 3 an eye, 4 an antenna or antennule, 5 an antennal
// scale, 6 the tail fan, 7 a fringe of hairs on a basket leg or a swimmeret); the colour's red,
// green and blue the joint the part turns about (a place in the box BOX_MIN to BOX_MAX); the
// colour's alpha how far along the part a point is (0 at its root to 1 at its tip; on an eye 0
// its stalk and 1 the eye); UV.x 1 on a swimmeret's fringe.
//
// Its five pairs of swimmerets beat in a wave from back to front, its basket of legs opens and
// closes a little, its antennae swing slowly, and with `curl` its abdomen and tail fan flick down
// and under (its backwards escape). All of it is a function of `phase` (and `curl`) alone, so a
// picture of it loops exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model: the box the joints are written in.
const vec3 BOX_MIN = vec3(-0.02, -0.01, -0.03);
const vec3 BOX_MAX = vec3(0.02, 0.01, 0.03);
// The tail flick: where the abdomen starts bending (z: the back of the carapace), the height of
// the middle line there, how long the part that bends is (behind it the tail fan is carried
// round stiffly), and how far it curls at `curl` 1 (radians).
const float CURL_FROM = -0.0048;
const float CURL_Y = 0.0001;
const float CURL_LENGTH = 0.0146;
const float CURL_MAX = 2.5;
// Where the carapace ends and each segment of the abdomen begins (z), as the model has them.
const float SEG0 = -0.0048;

// How far through one beat (0..1, it wraps). Set by Krill.
uniform float phase = 0.0;
// How many times its swimmerets beat in one beat (a whole number). Set by Krill.
uniform float strokes = 3.0;
// How widely its swimmerets beat: 0 still, 1 swimming.
uniform float sway = 1.0;
// Its tail flick: 0 straight, 1 the abdomen and tail fan curled right down and under.
uniform float curl : hint_range(0.0, 1.0) = 0.0;
// How far its feeding basket opens and closes (1 a little, as it feeds).
uniform float pump = 1.0;
// How far its long antennae swing (radians at their tips).
uniform float feel = 0.1;

// The clear pink of its body, the deeper pink where it is thickest, the red of its spots; how
// glassy it is (a bright rim where the light glances, as on a clear shell).
uniform vec3 pink : source_color = vec3(0.93, 0.72, 0.68);
uniform vec3 deep : source_color = vec3(0.82, 0.42, 0.38);
uniform vec3 red : source_color = vec3(0.72, 0.06, 0.04);
uniform float spots_show = 1.0;
uniform float glassy = 0.6;

// Cartoon eyes: 0 its eyes as they are, 1 huge glossy beads with a white, an iris, a pupil, a
// highlight and a lid (the krill's own: tiny and wide awake, wondering at everything: a thin ring
// of deep blue round a great round pupil, a rim of white, no lid at rest). `eye_look` slides the
// iris and pupil (x across the eye towards its head, y up; -1..1); `blink` brings a lid the colour
// of its shell down over each eye (0 open, 1 shut), cartoon or not.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// As the model has it: the middle of the left eye (the right one mirrored).
const vec3 EYE_MIDDLE = vec3(0.0015, 0.0009, -0.0131);
// This krill's cartoon eye: the way the left one looks; how much bigger it is; its white, its iris;
// how wide the iris and the pupil are (as the sine of the angle from where it looks); the pupil's
// shape (its width and height); where the upper lid rests (1 above the eye, -1 shut) and how it
// slopes (+ lower across towards its head); how far the iris slides at `eye_look` 1.
const vec3 EYE_GAZE = vec3(0.75, 0.15, -0.65);
const float EYE_GROW = 1.6;
const vec3 EYE_WHITE = vec3(0.97, 0.97, 1.0);
const vec3 EYE_IRIS = vec3(0.12, 0.3, 0.72);
const float IRIS_SIZE = 0.8;
const float PUPIL_SIZE = 0.6;
const vec2 PUPIL_SHAPE = vec2(1.0, 1.0);
const float LID_REST = 1.08;
const float LID_SLOPE = 0.0;
const float LOOK_REACH = 0.22;

varying vec3 rest;
varying float part;
varying float index;
varying float along;
varying float swim_fringe;

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

// `v` turned by `a` about the axis `k` (a unit vector).
vec3 turned(vec3 v, vec3 k, float a) {
	float c = cos(a);
	float s = sin(a);
	return v * c + cross(k, v) * s + k * dot(k, v) * (1.0 - c);
}

// The abdomen and the tail fan curled down and under about the back of the carapace (see `curl`).
void curl_under(inout vec3 v, inout vec3 n) {
	float d = v.z - CURL_FROM;
	if (curl < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl * CURL_MAX / CURL_LENGTH;
	float r = 1.0 / k;
	float dc = min(d, CURL_LENGTH);
	float extra = d - dc;
	float a = dc * k;
	float h = v.y - CURL_Y;
	float ca = cos(a);
	float sa = sin(a);
	v = vec3(v.x, CURL_Y - r + (r + h) * ca - extra * sa, CURL_FROM + (r + h) * sa + extra * ca);
	n = vec3(n.x, n.y * ca - n.z * sa, n.y * sa + n.z * ca);
}

// The eye on the side of `p` (at rest): its middle, the way it looks, its up and its across (towards
// the head).
void eye_frame(vec3 p, out vec3 mid, out vec3 gaze, out vec3 up, out vec3 across) {
	float side = p.x >= 0.0 ? 1.0 : -1.0;
	mid = EYE_MIDDLE * vec3(side, 1.0, 1.0);
	gaze = normalize(EYE_GAZE * vec3(side, 1.0, 1.0));
	up = normalize(vec3(0.0, 1.0, 0.0) - gaze * gaze.y);
	across = normalize(cross(up, gaze)) * side;
}

// The colour of a point `p` (at rest) of an eye: `plain` as it is, mixed to the cartoon eye by
// `cartoon_eyes`, the lid (`skin`) over it as `blink` (and, cartooned, `LID_REST`) has it; `lid` is
// set to how far the lid covers it, `glint` to where the cartoon eye's highlights are (they stay
// put, up and forward on the eye, when it looks about).
vec3 eye_colour(vec3 p, vec3 plain, vec3 skin, out float lid, out float glint) {
	vec3 mid, gaze, up, across;
	eye_frame(p, mid, gaze, up, across);
	vec3 d = normalize(p - mid);
	vec2 q = vec2(dot(d, across), dot(d, up));
	float front = smoothstep(-0.05, 0.1, dot(d, gaze));
	vec2 at = q - eye_look * LOOK_REACH;
	float r = length(at);
	vec3 c = EYE_WHITE;
	float iris = (1.0 - smoothstep(IRIS_SIZE - 0.03, IRIS_SIZE, r)) * front;
	c = mix(c, EYE_IRIS * mix(1.2, 0.6, smoothstep(0.0, IRIS_SIZE, r)), iris);
	c = mix(c, vec3(0.03, 0.02, 0.02), (1.0 - smoothstep(0.015, 0.045, abs(r - IRIS_SIZE))) * front);
	float pupil = 1.0 - smoothstep(PUPIL_SIZE - 0.03, PUPIL_SIZE, length(at / PUPIL_SHAPE));
	c = mix(c, vec3(0.01, 0.01, 0.015), pupil * front);
	c = mix(plain, c, cartoon_eyes);
	// the upper lid: its edge comes down from above the eye (or from where it rests) to below it
	float edge = mix(mix(1.08, LID_REST, cartoon_eyes), -1.08, blink) - LID_SLOPE * q.x;
	lid = smoothstep(edge - 0.02, edge + 0.02, q.y);
	glint = smoothstep(0.955, 0.97, dot(d, normalize(gaze + up * min(0.62, LID_REST - 0.28) + across * 0.3)));
	glint = max(glint, 0.7 * smoothstep(0.991, 0.995, dot(d, normalize(gaze + up * 0.18 + across * 0.52))));
	c = mix(c, skin, lid);
	c = mix(c, skin * 0.35, (1.0 - smoothstep(0.02, 0.07, abs(q.y - edge))) * step(edge, 1.0) * max(cartoon_eyes, step(0.001, blink)));
	return c;
}

void vertex() {
	float code = floor(UV2.y + 0.5);
	part = floor((code + 0.5) / 16.0);
	index = code - part * 16.0;
	along = COLOR.a;
	swim_fringe = step(0.5, UV.x);
	vec3 joint = mix(BOX_MIN, BOX_MAX, COLOR.rgb);
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	float side = joint.x >= 0.0 ? 1.0 : -1.0;
	bool swimmeret = p == 2 || (p == 7 && swim_fringe > 0.5);
	if (swimmeret) {
		// A swimmeret: it swings forwards and back about where it hangs, each pair a fifth of a
		// stroke ahead of the pair in front of it (a wave from back to front).
		float a = sway * (0.1 + 0.6 * sin(6.2831853 * (phase * strokes + 0.2 * index)));
		v = joint + turned(v - joint, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	} else if (p == 1 || p == 7) {
		// A leg of the basket: the basket opens out and closes once a beat, the front legs first.
		float open = pump * (0.5 + 0.5 * sin(6.2831853 * (phase - 0.06 * index)));
		vec3 axis = vec3(0.0, 0.0, side);
		v = joint + turned(turned(v - joint, axis, 0.25 * open), vec3(1.0, 0.0, 0.0), -0.12 * open);
		n = turned(turned(n, axis, 0.25 * open), vec3(1.0, 0.0, 0.0), -0.12 * open);
	} else if (p == 4 && index < 0.5) {
		// A long antenna: it swings slowly out and in, more towards its tip.
		float a = side * feel * along * sin(6.2831853 * (phase - 0.3 * along));
		v = joint + turned(v - joint, vec3(0.0, 1.0, 0.0), a);
		n = turned(n, vec3(0.0, 1.0, 0.0), a);
	}
	if (p == 3 && along > 0.5 && cartoon_eyes > 0.0) {
		// the cartoon eye: bigger about its own middle
		vec3 mid = EYE_MIDDLE * vec3(rest.x >= 0.0 ? 1.0 : -1.0, 1.0, 1.0);
		v = mid + (v - mid) * mix(1.0, EYE_GROW, cartoon_eyes);
	}
	if (p == 0 || p == 6 || swimmeret) {
		curl_under(v, n);
	}
	VERTEX = v;
	NORMAL = n;
}

// Red spots scattered over a surface: `q` a place on it (in tenths of a millimetre or so), `dense`
// how many of the cells hold one.
float spots(vec2 q, float dense, float size) {
	vec2 cell = floor(q);
	float h = hash2(cell);
	vec2 at = cell + 0.25 + 0.5 * vec2(hash2(cell + 7.1), hash2(cell + 3.7));
	float r = size * (0.6 + 0.8 * hash2(cell + 11.3));
	return step(h, dense) * (1.0 - smoothstep(r * 0.55, r, length(q - at)));
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.25;
	float spec = 0.6;
	vec3 emit = vec3(0.0);
	vec3 lit = vec3(0.0);
	if (p == 0 || p == 6) {
		// The body: clear pink, deeper along the back and in the thick of the carapace, each
		// segment's edge a fine darker line; red spots, most along the back and the sides of the
		// carapace, a row under the abdomen.
		float z = rest.z;
		float high = clamp(rest.y / 0.002, -1.0, 1.0);
		c = mix(pink, deep, 0.35 + 0.35 * smoothstep(-0.2, 0.9, high));
		c = mix(c, deep, 0.25 * (1.0 - smoothstep(-0.009, -0.004, z)) * smoothstep(-0.013, -0.011, z));
		float seg = abs(fract((z - SEG0) / 0.00205 + 0.5) - 0.5) * 0.00205;
		c = mix(c, deep * 0.8, (1.0 - smoothstep(0.0, 0.00012, seg)) * step(SEG0, z) * step(z, 0.0068) * 0.5);
		float round_it = atan(rest.x, rest.y);
		vec2 q = vec2(z * 2300.0, round_it * 4.5);
		float s = spots(q, 0.18 + 0.3 * smoothstep(0.3, 1.0, high), 0.3);
		s = max(s, spots(q * 1.6 + 5.0, 0.1, 0.22) * 0.7);
		if (p == 6) {
			c = mix(pink, deep, 0.4 + 0.3 * along);
			s = spots(rest.xz * 5200.0, 0.25, 0.4) * step(along, 0.5);
		}
		c = mix(c, red, s * spots_show);
		lit = pink * glassy * 0.55 * glance * glance;
		rough = 0.18;
		spec = 0.75;
	} else if (p == 1 || p == 2 || p == 4 || p == 5) {
		// A leg, a swimmeret, an antenna, a scale: clear pink, a red spot at its root.
		c = mix(pink, deep, 0.3 + 0.25 * along);
		c = mix(c, red, (1.0 - smoothstep(0.08, 0.2, along)) * 0.7 * spots_show * (p <= 2 ? 1.0 : 0.0));
		if (p == 4) {
			c = mix(c, red, 0.25 * smoothstep(0.3, 0.9, sin(along * 90.0)));
		}
		lit = pink * glassy * 0.4 * glance;
		rough = 0.3;
	} else if (p == 7) {
		// A fringe of fine hairs: paler and clearer.
		c = mix(pink, vec3(1.0), 0.25) * (0.95 + 0.05 * sin(along * 60.0));
		lit = pink * glassy * 0.5 * glance;
		rough = 0.45;
		spec = 0.4;
	} else {
		// An eye: black and glossy on a pink stalk.
		c = mix(deep, vec3(0.012, 0.01, 0.012), step(0.5, along));
		rough = mix(0.35, 0.1, along);
		spec = mix(0.5, 0.8, along);
		if (along > 0.5) {
			float lid;
			float shine;
			c = eye_colour(rest, c, deep, lid, shine);
			// cartooned: glossy, two bright highlights up and forward on it, and a dark rim so it
			// reads from far off
			float open = (1.0 - lid) * cartoon_eyes;
			c = mix(c, c * 0.15, open * (1.0 - smoothstep(0.12, 0.38, dot(normalize(NORMAL), VIEW))));
			c = mix(c, vec3(1.0), shine * open);
			emit = vec3(0.6) * shine * open;
			rough = mix(rough, 0.12, open);
			// (a shut lid is shell, not glassy eye)
			rough = mix(rough, 0.55, lid);
			spec = mix(spec, 0.35, lid);
		}
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = lit + emit;
}
