shader_type spatial;
// The yellowfin tuna (yellowfin_tuna.gd): every marking drawn here (no texture files), and its
// swimming. What each point is comes from the model (tools/build_yellowfin_tuna.py): UV2.y the
// part (0 body, 1 first dorsal, 2 the sickle fins, 3 a finlet, 4 the tail, 5 a pectoral fin, 6 a
// pelvic fin, 7 an eye, 8 the lower jaw, 9 a cheek, 10 a gill: see `gills` in the build script). UV, on the body and the lower jaw: x how far
// along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x
// root (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim
// (1); on a cheek: x how far along. UV2.x, on the first dorsal, how far the point stands above the
// fin's root (metres); on the body and the lower jaw, how far inside the mouth (0 skin and lips, 1
// the middle of its roof or floor); on a cheek, how far down it from the upper lip (0) to the
// lower (1).
//
// It swims as tunas do (thunniform): the body all but rigid, a wave that only grows large in the
// last third, the tail wrist flexing and the stiff crescent tail swung as one plate. All of it is
// a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// Kept in step with the model.
const float LENGTH = 1.5;
const float HALF = 0.75;
// Where the tail fin is hinged (metres behind the snout): behind it the tail is one stiff plate.
const float JOINT = 1.335;
const float MOUTH_TO = 0.132;
// Where the lower jaw hinges (metres behind the snout, metres up: the corner of the mouth), as the
// model has it, and how far it swings down for `gape` 1 (radians: its tip drops about 0.07 m).
const vec2 HINGE = vec2(0.132, -0.0393);
const float GAPE_TURN = 0.55;
// Where the lower jaw ends at the throat (metres behind the snout).
const float JAW_BACK = 0.172;

// How far through a beat of its tail (0..1, it wraps). Set by YellowfinTuna.
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of fish swimming tight rounds: "The fish need to bend more"):
// how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The
// head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How widely it beats, for 1 as a tuna cruising (its tail tips swing about 0.12 m either way).
uniform float sway = 1.0;
// How far its mouth is open (the user, 2026-11-17: "the fish should be able to open their
// mouths"): 0 shut, 1 wide open, as when it bites. Set by YellowfinTuna.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How far the first dorsal fin is raised (0 folded down into its groove, 1 up).
uniform float first_dorsal = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;

// The back, and the metallic blue it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.012, 0.022, 0.05);
uniform vec3 back_blue : source_color = vec3(0.03, 0.13, 0.36);
// The thin bright line over the gold band, and the band.
uniform vec3 line_blue : source_color = vec3(0.1, 0.5, 0.9);
uniform vec3 gold : source_color = vec3(0.95, 0.72, 0.1);
// The flank and the belly; the pale dots and broken lines on them.
uniform vec3 silver : source_color = vec3(0.62, 0.66, 0.71);
uniform vec3 belly : source_color = vec3(0.93, 0.94, 0.93);
uniform vec3 marks : source_color = vec3(0.97, 0.98, 1.0);
// The sickle fins and the finlets; the finlets' dark edges; the tail; the first dorsal.
uniform vec3 fin_yellow : source_color = vec3(1.0, 0.8, 0.06);
uniform vec3 fin_edge : source_color = vec3(0.03, 0.03, 0.035);
uniform vec3 tail_dark : source_color = vec3(0.05, 0.065, 0.085);
uniform vec3 fin_dusk : source_color = vec3(0.3, 0.29, 0.14);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.07, 0.03, 0.035);
// How strongly the pale marks on the belly show.
uniform float marks_show = 0.55;

// The cartoon eye (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0 the eye as it always was, 1 the cartoon eye: bigger, a white, a coloured iris, a big
// pupil, a highlight and a dark outline, under a lid that gives it its character. The yellowfin's: the
// keen, sporty one: a bright gold iris like its fins, a teardrop pupil pointing forward (as a tuna's
// gap ahead of its lens), a lid level and low enough to look intent.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the pupil and iris look, in the eye's own flat: x towards the snout (+) or the tail (-), y up
// (+) or down (-), each -1 to 1.
uniform vec2 eye_look = vec2(0.0);
// A lid the colour of the skin closing over the cartoon eye: 0 open, 1 shut.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.95, 0.68, 0.08);
// The gills (added 2026-11-18): the red of the gill arches and their filaments, seen through the open mouth.
uniform vec3 gill_red : source_color = vec3(0.6, 0.05, 0.07);
// As the model has it (its EYE line): the middle of the left eye on the skin, the way the skin faces
// there (metres), the eye's radius.
const vec3 EYE_MID = vec3(0.07126, 0.02400, -0.60500);
const vec3 EYE_OUT = vec3(0.92575, 0.18181, -0.33156);
const float EYE_RADIUS = 0.03;
// The cartoon eye's character: how much bigger it is drawn; the iris's radius and the pupil's (shares
// of the eye's); the pupil's shape (0 round, 1 a teardrop pointing forward); how far the iris roams
// for `eye_look`; the lid's edge (how high at the middle, how much higher towards the snout); where
// the highlight is.
const float EYE_GROW = 1.6;
const float IRIS = 0.6;
const float PUPIL = 0.3;
const int PUPIL_SHAPE = 1;
const float EYE_ROAM = 0.26;
const float LID = 0.62;
const float LID_TILT = -0.12;
const vec2 SHINE = vec2(0.28, 0.3);

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

// How far to one side the middle line of the body is, `xm` metres behind the snout: a wave that
// runs back along it, all but nothing as far as the middle, large only near the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.7 * (0.012 - 0.03 * s + 0.03 * s * s + 0.085 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// How much of the jaw's swing a point `xm` metres behind the snout takes: all of it ahead of the
// corner of the mouth, none at the throat (as the model has it: `jaw_turn`).
float jaw_turn(float xm) {
	return 1.0 - smoothstep(MOUTH_TO - 0.02, JAW_BACK, xm);
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

// The cartoon eye: the dome grown about its middle (`cartoon_eyes`), along the skin, its rim following
// the skin as the head curves away from it.
void eye_grow(inout vec3 v) {
	if (cartoon_eyes <= 0.0) {
		return;
	}
	float sx = v.x < 0.0 ? -1.0 : 1.0;
	vec3 mid = vec3(EYE_MID.x * sx, EYE_MID.y, EYE_MID.z);
	vec3 o = normalize(vec3(EYE_OUT.x * sx, EYE_OUT.y, EYE_OUT.z));
	vec3 d = v - mid;
	float dn = dot(d, o);
	vec3 dt = d - dn * o;
	float k = mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
	dn = dn < 0.0 ? dn * k * k : dn * k;
	v = mid + dt * k + o * dn;
}

// The cartoon eye's colour at `e`, a place in the eye's own flat (x towards the snout, y up, 1 its rim),
// under a lid of `skin`.
vec3 cartoon_eye(vec2 e, vec3 skin) {
	float r = length(e);
	vec2 look = eye_look;
	if (length(look) > 1.0) {
		look = normalize(look);
	}
	vec2 at = e - look * EYE_ROAM;
	// the white, a little grey towards its rim so that it reads as a ball
	vec3 c = vec3(0.95, 0.95, 0.92) * (1.0 - 0.22 * smoothstep(0.45, 0.95, r));
	// the iris: lighter in its middle, fine fibres, a dark ring round it
	float ri = length(at) / IRIS;
	vec3 iris = mix(eye_iris * 1.3, eye_iris * 0.6, smoothstep(0.25, 1.0, ri)) * (0.9 + 0.1 * sin(atan(at.y, at.x) * 22.0));
	c = mix(c, iris, 1.0 - smoothstep(0.97, 1.02, ri));
	c = mix(c, eye_iris * 0.25, smoothstep(0.86, 0.96, ri) * (1.0 - smoothstep(0.98, 1.03, ri)));
	// the pupil
	vec2 p = at / PUPIL;
	if (PUPIL_SHAPE == 1) {
		// (a teardrop that points forward, as a tuna's gap ahead of its lens)
		float ahead = max(p.x, 0.0);
		p = vec2(p.x > 0.0 ? p.x * 0.62 : p.x, p.y * (1.0 + 0.55 * ahead));
	}
	c = mix(c, vec3(0.008, 0.009, 0.012), 1.0 - smoothstep(0.94, 1.04, length(p)));
	// the highlight, which stays put towards the light, and a small glint below it
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.85, 1.0, length(e - SHINE) / 0.16));
	c = mix(c, vec3(1.0), 0.8 * (1.0 - smoothstep(0.8, 1.0, length(e - vec2(-0.6 * SHINE.x, SHINE.y - 0.42)) / 0.065)));
	// the lid, closing down over it for `blink`, its edge a dark line
	float lid_y = mix(LID + LID_TILT * e.x, -1.25, clamp(blink, 0.0, 1.0));
	c = mix(c, skin, smoothstep(-0.015, 0.015, e.y - lid_y));
	c = mix(c, vec3(0.01, 0.012, 0.02), (1.0 - smoothstep(0.035, 0.08, abs(e.y - lid_y))) * (1.0 - smoothstep(0.9, 1.0, r)));
	// the outline
	return mix(c, vec3(0.01, 0.012, 0.02), smoothstep(0.82, 0.9, r));
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part > 0.5 && part < 1.5) {
		// The first dorsal folds back and down into its groove.
		float down = UV2.x * (1.0 - clamp(first_dorsal, 0.0, 1.0));
		v.y -= down * 0.93;
		v.z += down * 0.45;
	} else if (part > 6.5 && part < 7.5) {
		// The cartoon eye: grown about its middle.
		eye_grow(v);
	} else if (part > 9.5) {
		// The gills (added 2026-11-18), laid on the cheeks: like a cheek, built as they hang with the mouth wide open
		// and folded up along the line of the mouth as it shuts (each point as far as it is down from the upper lip,
		// UV2.x).
		float a = (clamp(gape, 0.0, 1.0) - 1.0) * GAPE_TURN * jaw_turn(UV.x * LENGTH) * UV2.x;
		vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	} else if (part > 7.5) {
		// The lower jaw swings down about its hinge: all of it ahead of the corner of the mouth, its
		// back less and less, as the throat stretches. A cheek (part 9) hangs between the lips: the
		// model has it as it is with the mouth wide open; it folds up along the line of the mouth as
		// the mouth shuts (each point swung as far as it is down the cheek, UV2.x).
		float a = clamp(gape, 0.0, 1.0) * GAPE_TURN * jaw_turn(v.z + HALF);
		if (part > 8.5) {
			a = (clamp(gape, 0.0, 1.0) - 1.0) * GAPE_TURN * jaw_turn(UV.x * LENGTH) * UV2.x;
		}
		vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	}
	float xm = v.z + HALF;
	// (the tail, behind its hinge, is one stiff plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.86 * JOINT, JOINT, zc));
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

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return -0.004 - 0.34 * xm + 0.55 * xm * xm;
}

float gill_x(float y) {
	return 0.36 - 3.0 * (y + 0.015) * (y + 0.015);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

