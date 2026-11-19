shader_type spatial;
// The mahi-mahi (mahi_mahi.gd): every marking drawn here (no texture files), its mouth opened and its
// swimming. What each point is comes from the model (tools/build_mahi_mahi.py): UV2.y the part (0 body,
// 1 the dorsal fin, 2 the anal fin, 3 the lower jaw, 4 the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an
// eye). UV, on the body: x how far along, y how high on its side (1 the ridge of the back, 0 the keel of
// the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge (1) (on the dorsal and
// the anal fin, front to back along the fin); on the lower jaw: x tip (0) to rear end (1), y the middle
// of the mouth's floor (0) round to the chin (1); on an eye: x middle (0) to rim (1). UV2.x, on the body
// and the lower jaw: how much the point is inside the mouth (the roof and the floor).
//
// It swims as jacks and dorados do (carangiform): the head one stiff piece, a wave that runs back along
// the body and grows through its rear half, the tail wrist flexing and the forked tail swung as one plate.
// All of it is a function of `phase` alone, so a picture of it loops exactly.
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
const float LENGTH = 1.2;
const float HALF = 0.6;
// Ahead of this (metres behind the lip) the head is one stiff piece.
const float HEAD = 0.18;
// Where the tail fin is hinged: behind it the tail is one stiff plate.
const float JOINT = 1.04;
// The lower jaw's hinge (metres behind the lip, metres above the middle line) and how far it swings
// down at `gape` 1 (radians).
const vec2 HINGE = vec2(0.085, -0.024);
const float GAPE_MAX = 0.62;
const float DORSAL_RAYS = 60.0;
const float ANAL_RAYS = 27.0;
const vec2 EYE_AT = vec2(0.068, 0.024);

// How far through a beat of its tail (0..1, it wraps). Set by MahiMahi.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to
// the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The head
// stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How widely it beats, for 1 as a mahi-mahi cruising (its tail tips swing about 0.08 m either way).
uniform float sway = 1.0;
// The mouth: 0 shut, 1 wide open, as when it bites (the lower jaw swings down about its hinge).
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The cartoon eye (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0 the eye as it was (the default: nothing changes), 1 the cartoon eye: bigger, a clean white,
// a coloured iris, a big dark pupil, a highlight that stays put, a dark outline, and this animal's own lid. Its
// character: a goofy, eager eye: big and round, lots of white, a small golden iris and round pupil, no lid at all: wide awake and pleased with everything.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the pupil and iris look, -1..1 each way in the eye's own plane: x forward (towards the snout), y up.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat (a fish has no lids) and, on the cartoon eye, a lid the colour of the
// skin comes down over it.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(1.0, 0.72, 0.08);
uniform vec3 eye_white : source_color = vec3(0.97, 0.97, 0.94);
// As the model is built: where the middle of the left eye lies on the skin (the build script prints it as
// EYE_MIDDLE; the right eye is its mirror), and the eye's radius. Then this animal's eye: how much bigger the
// cartoon eye is, its iris's and its pupil's size (shares of the eye's radius; the pupil's along and up), where
// its upper lid's edge rests (-1 the bottom of the eye, 1 the top; above 1 no lid) and how that slopes (more than
// 0 higher towards the snout), where its lower lid rests (below -1 none).
const vec3 EYE_MIDDLE = vec3(0.0314, 0.0240, -0.5320);
const float EYE_R = 0.017;
const float EYE_GROW = 1.9;
const float EYE_IRIS = 0.48;
const vec2 EYE_PUPIL = vec2(0.27, 0.27);
const float EYE_LID = 1.6;
const float EYE_SLANT = 0.0;
const float EYE_LOWER = -1.6;

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
const vec2 THROAT_HOLE = vec2(0.061, 0.021);
const float THROAT_HOLE_W = 0.0075;
const float THROAT_HOLE_Y = 0.007;
const float COVER_BAND = 0.03;
const float COVER_FLARE = 0.003;
const float ARCH_SPREAD = 0.002;
uniform vec3 gill_red : source_color = vec3(0.62, 0.04, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.8, 0.72);

// (the edge of the gill cover, as gill_x has it)
float gill_edge(float y) {
	return 0.168 - 2.2 * (y - 0.02) * (y - 0.02);
}

// (how much of the gill cover's lift a point of the skin takes: its rear band, the lower and middle of the side)
float cover_lift(vec3 p, float high) {
	float c = high * 2.0 - 1.0;
	float ahead = gill_edge(p.y) - (p.z + HALF);
	float mask = smoothstep(-0.95, -0.8, c) * (1.0 - smoothstep(0.4, 0.6, c));
	return step(0.0, ahead) * (1.0 - smoothstep(0.0, COVER_BAND, ahead)) * mask;
}
// How long the wave along its body is, in body lengths.
uniform float wave = 1.0;

// The back and the dorsal fin: electric blue-green, bluer where light glances off it.
uniform vec3 back : source_color = vec3(0.0, 0.42, 0.42);
uniform vec3 back_blue : source_color = vec3(0.05, 0.3, 0.85);
// Where the back turns to the flank: green-gold.
uniform vec3 green : source_color = vec3(0.35, 0.62, 0.12);
// The flanks, and the belly.
uniform vec3 gold : source_color = vec3(1.0, 0.78, 0.06);
uniform vec3 belly : source_color = vec3(1.0, 0.93, 0.55);
// The small dark spots scattered over the flanks, and how many show (0 none, 1 all).
uniform vec3 spots : source_color = vec3(0.02, 0.06, 0.16);
uniform float spots_show = 1.0;
// The dorsal fin, the other fins, the inside of the mouth.
uniform vec3 fin_blue : source_color = vec3(0.04, 0.22, 0.62);
uniform vec3 fin_gold : source_color = vec3(0.92, 0.75, 0.2);
uniform vec3 mouth : source_color = vec3(0.12, 0.04, 0.04);

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

// How far to one side the middle line of the body is, `xm` metres behind the lip: a wave that runs
// back along it, small at the head, growing through the rear half.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.4 * (0.01 - 0.035 * s + 0.07 * s * s + 0.06 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 0.2 - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - 0.2);
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
	inside = UV2.x;
	rest = VERTEX;
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
	vec3 n = NORMAL;
	if (part > 2.5 && part < 3.5) {
		// The lower jaw swings down about its hinge; its rear end, in the throat, stays.
		float a = clamp(gape, 0.0, 1.0) * GAPE_MAX * smoothstep(HINGE.x + 0.03, HINGE.x - 0.002, v.z + HALF);
		vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	float xm = v.z + HALF;
	// (the head ahead, and the tail behind its hinge, are stiff: they turn as one piece)
	float zc = clamp(xm, HEAD, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.002) - side_at(zc - 0.002)) / 0.004;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.4 * smoothstep(0.86 * JOINT, JOINT, zc));
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

// The edge of the gill cover, as the model has it.
float gill_x(float y) {
	return 0.168 - 2.2 * (y - 0.02) * (y - 0.02);
}

// The dark spots: a few in each cell of a grid laid on the flank, each a small round dot.
float spot_at(vec2 p) {
	vec2 cell = floor(p);
	float best = 0.0;
	for (int i = -1; i <= 1; i++) {
		for (int j = -1; j <= 1; j++) {
			vec2 k = cell + vec2(float(i), float(j));
			float here = hash2(k * 1.7 + 3.1);
			vec2 at = k + vec2(hash2(k + 11.3), hash2(k + 27.9));
			float r = 0.12 + 0.12 * hash2(k + 5.5);
			float dot_ = 1.0 - smoothstep(r * 0.7, r, length(p - at));
			best = max(best, dot_ * step(here, 0.55 * spots_show));
		}
	}
	return best;
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

