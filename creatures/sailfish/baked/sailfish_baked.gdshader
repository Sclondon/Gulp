shader_type spatial;
// The sailfish (sailfish.gd): every marking drawn here (no texture files), its sail folded and
// rippled, and its swimming. What each point is comes from the model (tools/build_sailfish.py):
// UV2.y the part (0 body, 1 the sail, 2 the small middle fins, 3 the lower jaw, 4 the tail, 5 a
// pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body: x how far along, y how high on its
// side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y
// leading edge (0) to trailing edge (1); on the lower jaw: x tip (0) to hinge (1), y the line of
// the mouth (0) to the chin (1); on an eye: x middle (0) to rim (1). UV2.x, on the sail, how far
// the point stands above the fin's root (metres).
//
// It swims as tunas and billfish do (thunniform): the head and bill one stiff piece, the body all
// but rigid, a wave that only grows large in the last third, the tail wrist flexing and the stiff
// crescent tail swung as one plate. All of it is a function of `phase` alone, so a picture of it
// loops exactly.
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
const float LENGTH = 2.6;
const float HALF = 1.3;
// Ahead of this (metres behind the bill's tip) the head and bill are one stiff piece.
const float HEAD = 0.82;
// Where the tail fin is hinged: behind it the tail is one stiff plate.
const float JOINT = 2.29;
const float SAIL_RAYS = 46.0;
const float SAIL_HIGH = 0.54;
// The lower jaw: where its tip and its sunk end are, its hinge (metres behind the bill's tip, metres
// up), and how far it swings down when the mouth is wide open (radians).
const float JAW_FROM = 0.30;
const float JAW_TO = 0.64;
const vec2 JAW_HINGE = vec2(0.63, -0.06);
const float JAW_SWING = 0.36;

// How far through a beat of its tail (0..1, it wraps). Set by Sailfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left).
// The bill and head stay as they are; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How widely it beats, for 1 as a sailfish cruising (its tail tips swing about 0.2 m either way).
uniform float sway = 1.0;
// How far the sail is raised (0 folded down into its groove along the back, 1 up).
uniform float sail = 1.0;
// How far the top of the raised sail ripples to each side (metres).
uniform float ripple = 0.022;
// How far its mouth is open (0 shut, 1 wide open, as when it bites): the lower jaw swings down
// about its hinge under the eye.
uniform float gape = 0.0;

// The cartoon eye (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0 the eye as it was (the default: nothing changes), 1 the cartoon eye: bigger, a clean white,
// a coloured iris, a big dark pupil, a highlight that stays put, a dark outline, and this animal's own lid. Its
// character: a keen hunter's eye: steel blue, a round pupil, the upper lid low and sloping down towards the bill, intent on its prey.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the pupil and iris look, -1..1 each way in the eye's own plane: x forward (towards the snout), y up.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat (a fish has no lids) and, on the cartoon eye, a lid the colour of the
// skin comes down over it.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.22, 0.45, 0.78);
uniform vec3 eye_white : source_color = vec3(0.93, 0.95, 0.97);
// As the model is built: where the middle of the left eye lies on the skin (the build script prints it as
// EYE_MIDDLE; the right eye is its mirror), and the eye's radius. Then this animal's eye: how much bigger the
// cartoon eye is, its iris's and its pupil's size (shares of the eye's radius; the pupil's along and up), where
// its upper lid's edge rests (-1 the bottom of the eye, 1 the top; above 1 no lid) and how that slopes (more than
// 0 higher towards the snout), where its lower lid rests (below -1 none).
const vec3 EYE_MIDDLE = vec3(0.0507, 0.0220, -0.6650);
const float EYE_R = 0.022;
const float EYE_GROW = 1.8;
const float EYE_IRIS = 0.6;
const vec2 EYE_PUPIL = vec2(0.34, 0.34);
const float EYE_LID = 0.42;
const float EYE_SLANT = -0.28;
const float EYE_LOWER = -1.5;

// (the eye's dome made bigger about its middle on the skin, and squashed as it blinks)
void eye_vertex(inout vec3 v) {
	vec3 mid = vec3(sign(v.x) * EYE_MIDDLE.x, EYE_MIDDLE.y, EYE_MIDDLE.z);
	vec3 o = (v - mid) * mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
	o.y *= 1.0 - 0.6 * clamp(blink, 0.0, 1.0);
	v = mid + o;
}

// The cartoon eye at a point of the still model's eye: its colour, and how much of it is lid (for roughness).
vec4 cartoon_eye(vec3 p, vec3 skin) {
	vec2 e = vec2(EYE_MIDDLE.z - p.z, p.y - EYE_MIDDLE.y) / EYE_R;
	float r = length(e);
	vec2 q = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.92 - EYE_IRIS) * 0.9;
	float iris_at = length(q) / EYE_IRIS;
	float pupil_at = length(q / EYE_PUPIL);
	vec3 c = eye_white * (1.0 - 0.12 * smoothstep(0.5, 0.9, r));
	vec3 ring = eye_iris * (0.6 + 0.55 * smoothstep(1.0, 0.35, iris_at));
	c = mix(c, ring, 1.0 - smoothstep(0.94, 1.0, iris_at));
	c = mix(c, eye_iris * 0.25, smoothstep(0.8, 0.95, iris_at) * (1.0 - smoothstep(0.95, 1.0, iris_at)));
	c = mix(c, vec3(0.008, 0.008, 0.012), 1.0 - smoothstep(0.9, 1.0, pupil_at));
	// (the highlights stay put, up and forward, wherever it looks)
	float shine = 1.0 - smoothstep(0.1, 0.14, length(e - vec2(0.2, 0.15)));
	shine = max(shine, 0.8 * (1.0 - smoothstep(0.05, 0.08, length(e - vec2(-0.12, -0.22)))));
	c = mix(c, vec3(1.0), shine);
	// the dark outline
	c = mix(c, vec3(0.01, 0.01, 0.015), smoothstep(0.8, 0.86, r));
	// the lids: the upper comes down as it blinks, its edge a dark line
	float b = clamp(blink, 0.0, 1.0);
	float edge = mix(EYE_LID + EYE_SLANT * e.x, -1.05, b);
	float lower = EYE_LOWER;
	float lid = max(smoothstep(edge - 0.025, edge + 0.025, e.y), 1.0 - smoothstep(lower - 0.025, lower + 0.025, e.y));
	float line = (1.0 - smoothstep(0.05, 0.1, abs(e.y - edge))) * step(edge, 1.0);
	line = max(line, (1.0 - smoothstep(0.05, 0.1, abs(e.y - lower))) * step(-1.0, lower));
	c = mix(c, skin, lid);
	c = mix(c, vec3(0.01, 0.01, 0.015), line * 0.85 * step(r, 0.9));
	return vec4(c, lid);
}

// The gills (added 2026-11-18; the user: "The fish need modeled gills as well, well for relevant fish, so like when
// it opens its mouth wide you can see them"). The model has a short throat inside the head, its floor just above
// the rear of the roof of the mouth, lined with four gill arches a side (part 8: UV.x the kind, 0 the throat's
// wall, 1 a bar, 2 its filaments, 3 its rakers, plus a tenth of the arch's number; UV.y how deep; UV2.x how far
// along the arch). While the mouth is open, the roof is cut open over the throat (THROAT_HOLE: its middle and half
// length along the body, metres behind the snout's tip, its half width, and the height below which the skin there
// is the roof), the arches spread a little and the gill covers lift (COVER_FLARE metres at their rear edge, over
// COVER_BAND metres ahead of it), red filaments showing in the gap. With the mouth shut nothing of it changes.
const vec2 THROAT_HOLE = vec2(0.54, 0.08);
const float THROAT_HOLE_W = 0.008;
const float THROAT_HOLE_Y = -0.02;
const float COVER_BAND = 0.06;
const float COVER_FLARE = 0.008;
const float ARCH_SPREAD = 0.004;
uniform vec3 gill_red : source_color = vec3(0.62, 0.04, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.8, 0.72);

// (the edge of the gill cover, as gill_x has it)
float gill_edge(float y) {
	return 0.83 - 2.5 * (y + 0.02) * (y + 0.02);
}

// (how much of the gill cover's lift a point of the skin takes: its rear band, the lower and middle of the side)
float cover_lift(vec3 p, float high) {
	float c = high * 2.0 - 1.0;
	float ahead = gill_edge(p.y) - (p.z + HALF);
	float mask = smoothstep(-0.95, -0.8, c) * (1.0 - smoothstep(0.4, 0.6, c));
	return step(0.0, ahead) * (1.0 - smoothstep(0.0, COVER_BAND, ahead)) * mask;
}
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;

// The back, and the cobalt it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.012, 0.022, 0.075);
uniform vec3 back_blue : source_color = vec3(0.03, 0.11, 0.42);
// The flank (brownish blue), the lower flank and the belly.
uniform vec3 flank : source_color = vec3(0.2, 0.22, 0.31);
uniform vec3 silver : source_color = vec3(0.62, 0.66, 0.72);
uniform vec3 belly : source_color = vec3(0.93, 0.94, 0.94);
// The upright rows of pale dots down the flanks, and how strongly they show.
uniform vec3 bars : source_color = vec3(0.5, 0.7, 0.95);
uniform float bars_show = 0.8;
// The sail: its membrane, its rays and root, its spots.
uniform vec3 sail_blue : source_color = vec3(0.07, 0.17, 0.5);
uniform vec3 sail_dark : source_color = vec3(0.02, 0.04, 0.14);
uniform vec3 sail_spots : source_color = vec3(0.006, 0.008, 0.025);
// The other fins and the bill.
uniform vec3 fin_dark : source_color = vec3(0.02, 0.03, 0.075);
uniform vec3 bill : source_color = vec3(0.03, 0.04, 0.08);
// The inside of the mouth (seen only when it is open).
uniform vec3 mouth : source_color = vec3(0.05, 0.016, 0.022);

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

// How far to one side the middle line of the body is, `xm` metres behind the bill's tip: a wave
// that runs back along it, all but nothing as far as the middle, large only near the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.42 * (0.006 - 0.02 * s + 0.02 * s * s + 0.09 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 0.85 - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - 0.85);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	if (part > 6.5 && part < 7.5) {
		eye_vertex(v);
	}
	if (gape > 0.0 && part < 0.5) {
		// the gill cover lifts as the mouth opens
		v.x += sign(v.x) * clamp(gape, 0.0, 1.0) * COVER_FLARE * cover_lift(v, UV.y);
	}
	if (gape > 0.0 && part > 7.5 && UV.x > 0.5) {
		// the gill arches spread a little
		float arch = floor(fract(UV.x + 0.001) * 10.0 + 0.5);
		v.z += clamp(gape, 0.0, 1.0) * ARCH_SPREAD * (arch - 1.5);
	}
	if (part > 0.5 && part < 1.5) {
		// The sail folds back and down into its groove; raised, a wave runs back along its top.
		float up = clamp(sail, 0.0, 1.0);
		float down = UV2.x * (1.0 - up);
		v.y -= down * 0.97;
		v.z += down * 0.3;
		float high = UV2.x / SAIL_HIGH;
		v.x += up * ripple * high * high * sin(6.2831853 * (phase - rest.z * 1.4));
	}
	vec3 nn = NORMAL;
	if (part > 2.5 && part < 3.5) {
		// The lower jaw swings down about its hinge.
		float a = clamp(gape, 0.0, 1.0) * JAW_SWING;
		float ca = cos(a);
		float sa = sin(a);
		float dy = v.y - JAW_HINGE.y;
		float dz = v.z - (JAW_HINGE.x - HALF);
		v.y = JAW_HINGE.y + dy * ca + dz * sa;
		v.z = JAW_HINGE.x - HALF + dz * ca - dy * sa;
		nn = vec3(nn.x, nn.y * ca + nn.z * sa, nn.z * ca - nn.y * sa);
	}
	float xm = v.z + HALF;
	// (the head and bill ahead, and the tail behind its hinge, are stiff: they turn as one piece)
	float zc = clamp(xm, HEAD, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.86 * JOINT, JOINT, zc));
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

// The edge of the gill cover, as the model has it.
float gill_x(float y) {
	return 0.83 - 2.5 * (y + 0.02) * (y + 0.02);
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

