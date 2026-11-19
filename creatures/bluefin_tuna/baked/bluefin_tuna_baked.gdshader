shader_type spatial;
// The Pacific bluefin tuna (bluefin_tuna.gd): every marking drawn here (no texture files), its
// swimming and its jaw. It began as GameCommon's yellowfin tuna's shader. What each point is
// comes from the model (tools/build_bluefin_tuna.py): UV2.y the part (0 body, 1 first dorsal,
// 2 the second dorsal and the anal fin, 3 a finlet, 4 the tail, 5 a pectoral fin, 6 a pelvic fin,
// 7 an eye, 8 a gill: see `throat` in the build script). UV, on the body: x how far along, y how high on its side (1 the ridge of the back,
// 0 the keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge
// (1); on an eye: x middle (0) to rim (1). UV2.x, on the first dorsal, how far the point stands
// above the fin's root (metres); on the body, what it is of the mouth (0 skin, 1 the lower jaw's
// skin, 2 the roof of the mouth, 3 its floor, 4 a tooth above, 5 a tooth below: the odd ones
// swing with the jaw).
//
// The model is drawn 1.5 long ("units", the yellowfin's numbers) and scaled to LENGTH: every
// measure below is in units but where it says metres.
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


// Kept in step with the model (its SHAPE line).
const float LENGTH = 2.5;
const float U = LENGTH / 1.5;
const float HALF = 0.75;
// Where the tail fin is hinged (units behind the snout): behind it the tail is one stiff plate.
const float JOINT = 1.335;
// Where the lower jaw hinges (units behind the snout, units above the middle line); how much of
// the jaw's length, ahead of the hinge, bends rather than swings; how far the jaw drops and the
// snout lifts with the mouth wide open (radians).
const float HINGE = 0.14;
const float HINGE_Y = -0.0536;
const float SOFT = 0.4;
const float JAW_DROP = 0.62;
const float SNOUT_LIFT = 0.06;
const float GILL = 0.385;
const vec2 EYE_AT = vec2(0.152, 0.026);

// How far through a beat of its tail (0..1, it wraps). Set by BluefinTuna.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left).
// The head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// The mouth: 0 shut, 1 wide open, as when it bites.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How widely it beats, for 1 as a tuna cruising (its tail tips swing about 0.2 m either way).
uniform float sway = 1.0;
// How far the first dorsal fin is raised (0 folded down into its groove, 1 up).
uniform float first_dorsal = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;

// The back, and the metallic blue it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.006, 0.012, 0.035);
uniform vec3 back_blue : source_color = vec3(0.02, 0.075, 0.26);
// The flank and the belly; the pale lines and dots low on them.
uniform vec3 silver : source_color = vec3(0.56, 0.6, 0.66);
uniform vec3 belly : source_color = vec3(0.9, 0.91, 0.92);
uniform vec3 marks : source_color = vec3(0.97, 0.98, 1.0);
// The second dorsal (reddish brown); the anal fin and the finlets (a dusky yellow), the finlets'
// black edges; the tail and the pectoral fins; the first dorsal.
uniform vec3 fin_red : source_color = vec3(0.36, 0.13, 0.07);
uniform vec3 fin_yellow : source_color = vec3(0.78, 0.62, 0.12);
uniform vec3 fin_edge : source_color = vec3(0.02, 0.02, 0.025);
uniform vec3 tail_dark : source_color = vec3(0.03, 0.04, 0.065);
uniform vec3 fin_dusk : source_color = vec3(0.16, 0.19, 0.2);
// The inside of the mouth.
uniform vec3 mouth : source_color = vec3(0.16, 0.035, 0.04);
// How strongly the pale marks on the belly show.
uniform float marks_show = 0.3;

// The cartoon eye (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0 the eye as it always was, 1 the cartoon eye: bigger, a white, a coloured iris, a big
// pupil, a highlight and a dark outline, under a lid that gives it its character. The bluefin's: the
// heavy, unbothered old boss: a small steel-blue iris filling most of the eye, a round pupil, a heavy
// flat lid down over its top third.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the pupil and iris look, in the eye's own flat: x towards the snout (+) or the tail (-), y up
// (+) or down (-), each -1 to 1.
uniform vec2 eye_look = vec2(0.0);
// A lid the colour of the skin closing over the cartoon eye: 0 open, 1 shut.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.32, 0.46, 0.62);
// The gills (added 2026-11-18): the red of the gill arches and their filaments, seen through the open mouth.
uniform vec3 gill_red : source_color = vec3(0.6, 0.05, 0.07);
// As the model has it (its EYE line): the middle of the left eye on the skin, the way the skin faces
// there (units), the eye's radius.
const vec3 EYE_MID = vec3(0.08427, 0.02600, -0.59800);
const vec3 EYE_OUT = vec3(0.91521, 0.17230, -0.36428);
const float EYE_RADIUS = 0.023;
// The cartoon eye's character: how much bigger it is drawn; the iris's radius and the pupil's (shares
// of the eye's); the pupil's shape (0 round, 1 a teardrop pointing forward); how far the iris roams
// for `eye_look`; the lid's edge (how high at the middle, how much higher towards the snout); where
// the highlight is.
const float EYE_GROW = 1.5;
const float IRIS = 0.7;
const float PUPIL = 0.3;
const int PUPIL_SHAPE = 0;
const float EYE_ROAM = 0.22;
const float LID = 0.3;
const float LID_TILT = 0.06;
const vec2 SHINE = vec2(0.3, 0.05);

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
// (0 skin, 1 the inside of the mouth, 2 a tooth)
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

// How far to one side the middle line of the body is, `xm` units behind the snout: a wave that
// runs back along it, all but nothing as far as the middle, large only near the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = 1.05 * (0.012 - 0.03 * s + 0.03 * s * s + 0.085 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.3;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / 1.05;
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
	vec3 v = VERTEX / U;
	vec3 n = NORMAL;
	rest = v;
	rest_normal = n;
	float what = part < 0.5 ? UV2.x : 0.0;
	inside = floor(what * 0.5 + 0.2);
	float jaw = what - 2.0 * inside;
	if (part > 0.5 && part < 1.5) {
		// The first dorsal folds back and down into its groove.
		float down = UV2.x / U * (1.0 - clamp(first_dorsal, 0.0, 1.0));
		v.y -= down * 0.93;
		v.z += down * 0.45;
	} else if (part > 6.5 && part < 7.5) {
		// The cartoon eye: grown about its middle.
		eye_grow(v);
	} else if (part > 7.5 && part < 8.5) {
		// The gill arches spread a little as the mouth opens.
		v.x *= 1.0 + 0.1 * clamp(gape, 0.0, 1.0);
	}
	float xm = v.z + HALF;
	if (xm < HINGE) {
		// The lower jaw swings down about its hinge (the skin just ahead of the hinge bends), and
		// the snout lifts a little.
		float a = clamp(gape, 0.0, 1.0) * (1.0 - smoothstep(HINGE * (1.0 - SOFT), HINGE, xm));
		a *= jaw > 0.5 ? JAW_DROP : -SNOUT_LIFT;
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = v.yz - vec2(HINGE_Y, HINGE - HALF);
		v.yz = vec2(HINGE_Y, HINGE - HALF) + vec2(d.x * ca + d.y * sa, d.y * ca - d.x * sa);
		n.yz = vec2(n.y * ca + n.z * sa, n.z * ca - n.y * sa);
		xm = v.z + HALF;
	}
	// (the tail, behind its hinge, is one stiff plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.86 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	vec3 bent = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	vec3 bent_normal = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(bent, bent_normal);
	VERTEX = bent * U;
	NORMAL = bent_normal;
}

// The edge of the gill cover, as the model has it.
float gill_x(float y) {
	return GILL - 3.0 * (y + 0.015) * (y + 0.015);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	if (gape > 0.0 && paint.a < 0.5) {
		discard;
	}
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

