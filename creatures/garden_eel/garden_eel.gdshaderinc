// The garden eel's pose and colours, shared by garden_eel.gdshader (one eel, GardenEel) and
// garden_eel_colony.gdshader (hundreds in one MultiMesh, GardenEelColony).
//
// The models (tools/build_garden_eel.py) stand straight up like a pencil drawn out of the sand: the
// tip of the snout at y = 0.3, the tail's tip at y = -0.1, the back to +Z, the belly to -Z, the
// origin at the mouth of the burrow. eel_pose() slides it down into its burrow (`out`), stands what
// is out of the sand up from the burrow's mouth, leaning back a little away from the current, and
// curls its top over forward into a question mark so that its head faces -Z, into the current; then
// sways it and turns its head a little, all as a function of `turn` (TAU times its phase).
// UV2.y is the part (0 body, 1 an eye, 2 a pectoral fin, 3 the inside of the mouth and the throat,
// 4 a gill arch). UV.x on the body: 0 snout to 1 tail.
// Nothing here needs more than GL Compatibility has.

// Kept in step with the model (and GardenEel.head_at): the snout's height in the still model, and
// how much of it from the snout is curled over.
const float EEL_TOP = 0.3;
const float EEL_HOOK = 0.2;
// As the build script has them: the line of the mouth, the eye.
const float EEL_MOUTH_TO = 0.0072;
const vec2 EEL_EYE_AT = vec2(0.0088, 0.0012);
const float EEL_EYE_RADIUS = 0.0031;

// Its colours: pale, a little warmer on the back; the small dark specks; the large black spots;
// the eye's ring.
uniform vec3 skin : source_color = vec3(0.9, 0.88, 0.8);
uniform vec3 skin_back : source_color = vec3(0.8, 0.76, 0.64);
uniform vec3 speck : source_color = vec3(0.08, 0.07, 0.06);
uniform vec3 spot : source_color = vec3(0.02, 0.02, 0.02);
uniform vec3 eye_ring : source_color = vec3(0.75, 0.68, 0.45);
// How many of the small specks show (0 none, 1 many).
uniform float specks = 0.6;
// The cartoon eye: 0 the eye as in life, 1 a bigger cartoon eye (a white, an iris, a pupil, a
// highlight, a dark outline and lids of its own character); where its pupils look (x forward,
// towards the snout, y up, towards its back, -1..1, in each eye's own plane); a blink (0 open,
// 1 shut: lids the colour of its skin close over the eye, the cartoon one and the one in life).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The garden eel's cartoon eye: shy and wary, a peeker. Big and round, a pale gold iris almost
// filled by a big round pupil, and the lower lid pushed up into a wary squint, higher towards
// the snout; no upper lid in sight. It grows EEL_EYE_BIG times about a point a little out from
// the skin (so that its rim stays on the round of the head). (Kept in step with the model:
// build_garden_eel.py prints the eye's middle on the skin and its way out, the left one's.)
const vec3 EEL_EYE_SKIN = vec3(0.005817, 0.2912, 0.0012);
const vec3 EEL_EYE_OUT = vec3(0.992877, 0.0, 0.119145);
const float EEL_EYE_LIFT = 0.0013;
const float EEL_EYE_BIG = 1.5;
const vec3 EEL_SCLERA = vec3(0.97, 0.97, 0.94);
const vec3 EEL_IRIS_IN = vec3(0.96, 0.86, 0.52);
const vec3 EEL_IRIS_OUT = vec3(0.6, 0.48, 0.2);
const float EEL_IRIS_R = 0.5;
const float EEL_PUPIL = 0.33;
// The upper lid's edge (eye radii up from the middle) and its slant (up per radius forward); the
// lower lid's.
const float EEL_LID_TOP = 1.3;
const float EEL_LID_SLANT = 0.0;
const float EEL_LID_LOW = -0.4;
const float EEL_LID_LOW_SLANT = 0.14;

// The mouth (gape, in garden_eel.gdshader): how far the lower jaw turns at its widest (radians),
// about its hinge at the corner of the mouth (as the build script has it: there, on the line of
// the mouth).
const float EEL_GAPE = 0.6;
const float EEL_HINGE_D = -0.00364;
// (as the build script has it, SNAP_RANGE: how far a COLOR of 0 or 1 slides a lip's point)
const float EEL_SNAP_RANGE = 0.003;

// Which way its middle line runs at `h` metres up it from the burrow's mouth (radians from upright,
// more than 0 bowing forward to -Z): leaning back `th0` low down, turning a further `total` over the
// top EEL_HOOK of what is out, smoothly (the most bend half way along that), the head straight.
float eel_angle(float h, float shown, float th0, float total) {
	return th0 + total * smoothstep(shown - EEL_HOOK, shown - 0.012, h);
}

// Puts one point of the still model where it is on the eel standing `out` (0..1) of its burrow.
// `hook`: radians its top is curled over (2.0: the head a little below level, facing -Z); `lean`:
// radians its stalk leans back (+Z) from upright; `motion`: how much it sways (1 as it lives).
void eel_pose(inout vec3 v, inout vec3 n, float out_amount, float turn, float motion, float hook, float lean) {
	float s = EEL_TOP - v.y;
	float shown = out_amount * EEL_TOP;
	float h = shown - s;
	float hh = max(h, 0.0);
	float up = smoothstep(0.15, 0.7, out_amount);
	float total = hook * up * (1.0 + 0.1 * motion * sin(turn + 1.3));
	float th0 = -lean * up * (1.0 + 0.3 * motion * sin(turn + 2.4));
	// (y, z) of its middle line: straight up to where the curl starts, then summed in ten steps
	float from = clamp(shown - EEL_HOOK, 0.0, hh);
	vec2 p = from * vec2(cos(th0), -sin(th0));
	float dh = (hh - from) * 0.1;
	for (int i = 0; i < 10; i++) {
		float a = eel_angle(from + (float(i) + 0.5) * dh, shown, th0, total);
		p += dh * vec2(cos(a), -sin(a));
	}
	float th = eel_angle(hh, shown, th0, total);
	if (h < 0.0) {
		// in the burrow: straight down, and thinned away below the sand
		p = vec2(h, 0.0);
		th = 0.0;
	}
	float thick = smoothstep(-0.03, -0.004, h);
	vec2 tangent = vec2(cos(th), -sin(th));
	vec2 back = vec2(sin(th), cos(th));
	vec2 yz = p + v.z * thick * back;
	vec3 placed = vec3(v.x * thick, yz.x, yz.y);
	vec2 nyz = n.y * tangent + n.z * back;
	vec3 turned = vec3(n.x, nyz.x, nyz.y);
	// swaying from side to side (more the higher up), and the head turning to look about
	float high = hh / max(shown, 0.02);
	placed.x += motion * 0.014 * out_amount * high * high * sin(turn - hh * 9.0);
	float look = motion * 0.35 * sin(turn + 0.9) * smoothstep(0.0, EEL_TOP, hh);
	float c = cos(look);
	float sn = sin(look);
	placed = vec3(placed.x * c + placed.z * sn, placed.y, -placed.x * sn + placed.z * c);
	turned = vec3(turned.x * c + turned.z * sn, turned.y, -turned.x * sn + turned.z * c);
	v = placed;
	n = turned;
}

float eel_hash(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

// The eye, `r` from its middle (0) to its rim (1): a big black pupil in a pale gold ring.
vec3 eel_eye(float r) {
	vec3 c = mix(vec3(0.01), eye_ring, smoothstep(0.5, 0.58, r));
	return mix(c, skin * 0.7, smoothstep(0.86, 0.98, r));
}

// The cartoon eye at `e`: a point of the eye in its own plane, in eye radii (x forward, towards
// the snout; y up, towards its back). A white shaded towards its rim, an iris and a big pupil
// that slide together as far as `eye_look` asks and the white allows, and highlights that stay
// put, up and forward, towards the light.
vec3 eel_cartoon_eye(vec2 e) {
	vec2 d = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.86 - EEL_IRIS_R);
	float ir = length(d) / EEL_IRIS_R;
	vec3 c = EEL_SCLERA * (1.0 - 0.2 * smoothstep(0.45, 0.95, length(e)));
	vec3 iris = mix(EEL_IRIS_IN, EEL_IRIS_OUT, smoothstep(0.55, 1.0, ir));
	iris = mix(iris, iris * 0.35, smoothstep(0.82, 0.96, ir));
	c = mix(c, iris, 1.0 - smoothstep(0.96, 1.0, ir));
	c = mix(c, vec3(0.01, 0.01, 0.015), 1.0 - smoothstep(0.9, 1.0, length(d) / EEL_PUPIL));
	float shine = 1.0 - smoothstep(0.1, 0.135, length(e - vec2(0.2, 0.28)));
	shine = max(shine, 1.0 - smoothstep(0.04, 0.065, length(e - vec2(-0.13, -0.17))));
	return mix(c, vec3(1.0), shine);
}

// The lids over an eye at `e` (as above), `lid` the colour of its skin: in the cartoon eye where
// its character puts them, with a dark line along each edge and a dark outline round the eye; in
// the eye in life, out of sight. `blink` brings them together.
vec3 eel_lids(vec3 c, vec2 e, vec3 lid) {
	float top = mix(1.3, EEL_LID_TOP + EEL_LID_SLANT * e.x, cartoon_eyes);
	float low = mix(-1.3, EEL_LID_LOW + EEL_LID_LOW_SLANT * e.x, cartoon_eyes);
	float meet = mix(top, low, 0.6);
	top = mix(top, meet, blink);
	low = mix(low, meet, blink);
	float over = max(smoothstep(-0.02, 0.02, e.y - top), smoothstep(-0.02, 0.02, low - e.y));
	c = mix(c, lid, over);
	float line = max(1.0 - smoothstep(0.035, 0.07, abs(e.y - top)), 1.0 - smoothstep(0.025, 0.05, abs(e.y - low)));
	c = mix(c, vec3(0.03, 0.03, 0.035), line * mix(0.5, 1.0, cartoon_eyes) * step(0.001, max(cartoon_eyes, blink)));
	return mix(c, vec3(0.03, 0.03, 0.035), smoothstep(0.84, 0.92, length(e)) * cartoon_eyes);
}

// The colour of a point of the still model `rest` (part 0 the body, 1 an eye, 2 a fin, 3 the inside
// of the mouth, 4 a gill arch; `uv` its UV). `drawn_eye`: draw the eye on the skin (the colony's
// model has none of its own).
vec3 eel_colour(vec3 rest, float part, vec2 uv, bool drawn_eye) {
	int p = int(part + 0.5);
	if (p == 1) {
		vec2 e = vec2(EEL_EYE_AT.x - (EEL_TOP - rest.y), rest.z - EEL_EYE_AT.y) / EEL_EYE_RADIUS;
		// (UV.y 1: the game model's eye, of few rings, drawn from where the point is so that it stays round)
		float r = uv.y > 0.5 ? min(length(e), 1.0) : uv.x;
		vec3 c = mix(eel_eye(r), eel_cartoon_eye(e), cartoon_eyes);
		return eel_lids(c, e, skin);
	}
	if (p == 2) {
		return mix(skin, vec3(0.95, 0.93, 0.88), 0.5);
	}
	if (p == 3) {
		// the inside of the mouth and the throat: dark red, darker deeper in
		float deep = smoothstep(EEL_MOUTH_TO - 0.004, 0.026, EEL_TOP - rest.y);
		return mix(vec3(0.3, 0.09, 0.09), vec3(0.05, 0.012, 0.012), deep);
	}
	if (p == 4) {
		// a gill arch: its bar pinkish and pale where it faces the mouth (the rakers), the filaments
		// blood red; darker the deeper in the throat
		float deep = smoothstep(0.011, 0.023, EEL_TOP - rest.y);
		vec3 c = uv.y < 0.5 ? vec3(0.78, 0.5, 0.48) : (uv.y < 1.5 ? vec3(0.62, 0.04, 0.06) : vec3(0.9, 0.8, 0.72));
		return c * (1.0 - 0.25 * deep);
	}
	float s = EEL_TOP - rest.y;
	float around = atan(rest.x, rest.z);
	float side = abs(around) / PI;
	// paler on the belly, a little warmer on the back
	vec3 c = mix(skin_back, skin, smoothstep(0.15, 0.6, side));
	// the small dark specks, in cells along the body and round it
	vec2 at = vec2(s, around * 0.006) / 0.0042;
	vec2 cell = floor(at);
	float dark = 0.0;
	for (int i = -1; i <= 1; i++) {
		for (int j = -1; j <= 1; j++) {
			vec2 here = cell + vec2(float(i), float(j));
			float h = eel_hash(here);
			if (h < specks) {
				vec2 middle = here + vec2(eel_hash(here + 17.0), eel_hash(here + 41.0)) * 0.8 + 0.1;
				float size = 0.13 + 0.1 * eel_hash(here + 7.0);
				dark = max(dark, 1.0 - smoothstep(size * 0.7, size, length(at - middle)));
			}
		}
	}
	// (seen from far off, where a speck is smaller than a pixel, they blend into a light grey wash
	// rather than glittering)
	dark = mix(dark, specks * 0.12, smoothstep(0.1, 0.35, fwidth(at.x)));
	dark *= smoothstep(0.012, 0.02, s);
	c = mix(c, speck, dark * 0.85);
	// the large black spots: one on each side just behind the gill opening, one half way down
	vec2 flank = vec2(s, (side - 0.5) * PI * 0.006);
	float big = 1.0 - smoothstep(0.0036, 0.0046, length(flank - vec2(0.043, 0.0)));
	big = max(big, 1.0 - smoothstep(0.0034, 0.0044, length(flank - vec2(0.175, 0.0))));
	c = mix(c, spot, big);
	// the line of the mouth, climbing towards the front
	float mouth_d = -0.0004 - 0.45 * s;
	float lip = (1.0 - smoothstep(0.00022, 0.0004, abs(rest.z - mouth_d))) * (1.0 - smoothstep(EEL_MOUTH_TO - 0.0012, EEL_MOUTH_TO, s));
	c = mix(c, vec3(0.12, 0.08, 0.07), lip * smoothstep(0.0012, 0.0022, abs(rest.x)));
	if (drawn_eye) {
		float big = mix(1.0, EEL_EYE_BIG, cartoon_eyes);
		float r = length(vec2(s, rest.z) - EEL_EYE_AT) / (EEL_EYE_RADIUS * big);
		if (r < 1.0 && abs(rest.x) > 0.0025) {
			vec2 e = vec2(EEL_EYE_AT.x - s, rest.z - EEL_EYE_AT.y) / (EEL_EYE_RADIUS * big);
			c = eel_lids(mix(eel_eye(r), eel_cartoon_eye(e), cartoon_eyes), e, skin);
		}
	}
	return c;
}

// The mouth opening `gape` (0 shut, 1 wide) on a point `v` (normal `n`) of the still model, before it
// is posed: the lower jaw (`w` its jaw weight, UV2.x) turns down about its hinge at the corner of
// the mouth; behind the mouth the throat and the gill arches (`p` 3 and 4) widen, the arches
// (`arch` 0..1, which of the four) spreading apart along it.
void eel_open(inout vec3 v, inout vec3 n, float gape_by, int p, float w, float arch) {
	if (w > 0.0) {
		float a = gape_by * EEL_GAPE * w;
		float c = cos(a);
		float sn = sin(a);
		vec2 d = vec2(EEL_TOP - v.y - EEL_MOUTH_TO, v.z - EEL_HINGE_D);
		d = vec2(d.x * c - d.y * sn, d.x * sn + d.y * c);
		v.y = EEL_TOP - EEL_MOUTH_TO - d.x;
		v.z = EEL_HINGE_D + d.y;
		vec2 m = vec2(-n.y, n.z);
		m = vec2(m.x * c - m.y * sn, m.x * sn + m.y * c);
		n = vec3(n.x, -m.x, m.y);
	}
	float s = EEL_TOP - v.y;
	if (p >= 3 && s > EEL_MOUTH_TO) {
		float open = gape_by * smoothstep(EEL_MOUTH_TO, EEL_MOUTH_TO + 0.004, s);
		v.x *= 1.0 + 0.25 * open;
		if (p == 4) {
			v.y -= 0.0005 * open * (arch * 2.0 - 1.0);
		}
	}
}

// The cartoon eye is bigger: grows about a point a little out from the skin over the eye's middle.
void eel_grow_eye(inout vec3 v) {
	vec3 pivot = EEL_EYE_SKIN + EEL_EYE_OUT * EEL_EYE_LIFT;
	pivot.x *= sign(v.x);
	v = pivot + (v - pivot) * mix(1.0, EEL_EYE_BIG, cartoon_eyes);
}
