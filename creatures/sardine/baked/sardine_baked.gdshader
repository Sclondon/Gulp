shader_type spatial;
// The Pacific sardine (sardine.gd): every marking drawn here (no texture files), and its
// swimming. What each point is comes from the model (tools/build_sardine.py): UV2.y the part
// (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an
// eye, 7 the lower jaw, 8 a gill arch). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x
// how far along, y how high on its side (1 the ridge of the back, 0 the
// keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge (1);
// on an eye: x middle (0) to rim (1).
//
// It swims as sardines and herrings do (between subcarangiform and carangiform): a wave runs
// back along the body, small at the head (which swings a little, as it does in life), growing
// through the whole back half, the forked tail swung behind the wrist. All of it is a function
// of `phase` alone, so a picture of it loops exactly.
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
const float LENGTH = 0.22;
const float HALF = 0.11;
// Where the tail fin is hinged (metres behind the jaw): behind it the tail is one plate.
const float JOINT = 0.183;
const float MOUTH_TO = 0.018;
const vec2 EYE_AT = vec2(0.021, 0.0042);
// The lower jaw: how far back it runs (metres behind its tip), where its hinge is there (on the
// line of the mouth), and how far it swings down, wide open (radians).
const float JAW_TO = 0.019;
const float HINGE_Y = -0.0049;
const float GAPE_OPEN = 0.8;
// The throat and the gills (kept in step with the model): where the gill arches stand and where the throat
// ends (metres behind the jaw), and how high inside the head the full model's old wall across the back of the
// mouth is lifted, out of the way, as the mouth opens.
const float GILL_FROM = 0.02481;
const float GILL_TO = 0.04540;
const float WALL_Y = 0.00134;
// The row of spots: where the first is (metres behind the jaw), how far apart, how many.
const float SPOT_FROM = 0.058;
const float SPOT_STEP = 0.0132;
const float SPOT_COUNT = 8.0;

// How far through a beat of its tail (0..1, it wraps). Set by Sardine.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is; set it from how tightly the fish is turning. (As the
// yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely it beats, for 1 as a sardine cruising (its tail tips swing about 0.02 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.95;
// How far its mouth is open: 0 shut, 1 wide open (as when it bites, or swims open-mouthed to
// strain its food from the water). The lower jaw swings down about its hinge.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The back, and the blue-green it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.02, 0.09, 0.19);
uniform vec3 back_green : source_color = vec3(0.03, 0.36, 0.44);
// The flank and the belly; the faint brassy green under the back's edge.
uniform vec3 silver : source_color = vec3(0.74, 0.78, 0.81);
uniform vec3 belly : source_color = vec3(0.95, 0.95, 0.93);
uniform vec3 sheen : source_color = vec3(0.55, 0.72, 0.55);
// The spots; how strongly the row shows, and the fainter second row above it (0 none).
uniform vec3 spot : source_color = vec3(0.02, 0.04, 0.07);
uniform float spots_show = 0.92;
uniform float second_row = 0.3;
// How strongly the scales' edges show.
uniform float scales_show = 0.6;
// The pale fins; the dusky tail and dorsal fin.
uniform vec3 fin : source_color = vec3(0.7, 0.75, 0.74);
uniform vec3 fin_dusk : source_color = vec3(0.2, 0.28, 0.29);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.1, 0.035, 0.04);
// The gills: the filaments' blood red, and the pale gill rakers.
uniform vec3 gill_red : source_color = vec3(0.62, 0.05, 0.07);
uniform vec3 gill_raker : source_color = vec3(0.72, 0.6, 0.56);
// The cartoon eye: 0 the eye as in life, 1 a bigger cartoon eye (a white, an iris, a pupil, a
// highlight, a dark outline and lids of its own character); where its pupils look (x forward,
// towards the snout, y up, -1..1, in each eye's own plane); a blink (0 open, 1 shut: lids the
// colour of the skin close over the eye, the cartoon one and the one in life alike).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The sardine's cartoon eye: a wide, startled stare, the small fry's. White all round a small
// silver-blue iris with a small round pupil, and no lid in sight: it is always wide open (until it
// blinks). (Kept in step with the model: the eye's radius, and the point it grows about, a little
// above its middle so that it does not grow over the top of the head: out, up, along, in metres.)
const float EYE_R = 0.0056;
const vec3 EYE_PIVOT = vec3(0.00596, 0.00756, 0.021);
const float EYE_BIG = 1.45;
const vec3 SCLERA = vec3(0.97, 0.97, 0.96);
const vec3 IRIS_IN = vec3(0.62, 0.78, 0.92);
const vec3 IRIS_OUT = vec3(0.2, 0.38, 0.6);
const float IRIS_R = 0.42;
// The pupil's half width and half height, in eye radii.
const vec2 PUPIL = vec2(0.19, 0.19);
// The upper lid's edge (eye radii up from the middle) and its slant (up per radius forward); the
// lower lid's (beyond 1 or -1: none).
const float LID_TOP = 1.3;
const float LID_SLANT = 0.0;
const float LID_LOW = -1.3;
const float LID_LOW_SLANT = 0.0;

varying vec3 rest;
varying vec3 rest_normal;
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

// How far to one side the middle line of the body is, `xm` metres behind the jaw: a wave that
// runs back along it, smallest a little behind the head, growing all the way to the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.008 - 0.03 * s + 0.082 * s * s);
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

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	rest_normal = NORMAL;
	inside = UV2.x;
	vec3 v = VERTEX;
	// The cartoon eye is bigger: the eye grows about a point near its middle.
	if (abs(part - 6.0) < 0.5 && cartoon_eyes > 0.0) {
		vec3 pivot = vec3(sign(v.x) * EYE_PIVOT.x, EYE_PIVOT.y, EYE_PIVOT.z - HALF);
		v = pivot + (v - pivot) * mix(1.0, EYE_BIG, cartoon_eyes);
	}
	// The full model's old wall across the back of the mouth (points of the body, inside the mouth, UV y 0.5,
	// where the jaw ends) is lifted up inside the head as soon as the mouth opens, so the throat behind it shows.
	if (part < 0.5 && UV2.x > 0.5 && abs(UV.y - 0.5) < 0.01 && v.z + HALF > JAW_TO - 0.0002 && gape > 0.0) {
		v.y = WALL_Y;
		v.x *= 0.5;
	}
	float xm = v.z + HALF;
	// (the jaw's own part only: the gills stay where they are)
	if (abs(part - 7.0) < 0.5) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = clamp(gape, 0.0, 1.0) * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.008, JAW_TO - 0.0005, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	// (the tail, behind its hinge, is one plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0006) - side_at(zc - 0.0006)) / 0.0012;
	// (the wrist flexes a little further than the body's own line)
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

// The line of the mouth and the edge of the gill cover, as the model has them.
float mouth_y(float xm) {
	return 0.0008 - 0.30 * xm;
}

float gill_x(float y) {
	return 0.050 - 26.0 * (y + 0.002) * (y + 0.002);
}

// One spot of a row: `lane` counts along the row (a whole number at each spot's middle).
float spot_of(float xm, float q, float lane, float last, float high, float radius, float seed) {
	float k = clamp(floor(lane + 0.5), 0.0, last);
	float r = radius * (1.0 - 0.04 * k) * (0.85 + 0.3 * hash2(vec2(k, seed)));
	vec2 d = vec2((lane - k) * SPOT_STEP + (hash2(vec2(k, seed + 1.0)) - 0.5) * 0.0016,(q - high - (hash2(vec2(k, seed + 2.0)) - 0.5) * 0.04) * (0.0195 - 0.0125 * smoothstep(0.085, 0.185, xm)));
	return 1.0 - smoothstep(r * 0.62, r, length(d));
}

// The cartoon eye at `e`: a point of the eye in its own plane, in eye radii (x forward, towards
// the snout; y up). A white shaded towards its rim, an iris (darker at its edge) and a pupil that
// slide together as far as `eye_look` asks and the white allows, and highlights that stay put,
// up and forward, towards the light.
vec3 cartoon_eye(vec2 e) {
	vec2 d = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.86 - IRIS_R);
	float ir = length(d) / IRIS_R;
	vec3 c = SCLERA * (1.0 - 0.2 * smoothstep(0.45, 0.95, length(e)));
	vec3 iris = mix(IRIS_IN, IRIS_OUT, smoothstep(0.25, 1.0, ir));
	iris = mix(iris, iris * 0.3, smoothstep(0.8, 0.95, ir));
	c = mix(c, iris, 1.0 - smoothstep(0.96, 1.0, ir));
	c = mix(c, vec3(0.01, 0.01, 0.015), 1.0 - smoothstep(0.88, 1.0, length(d / PUPIL)));
	float shine = 1.0 - smoothstep(0.1, 0.135, length(e - vec2(0.22, 0.3)));
	shine = max(shine, 1.0 - smoothstep(0.04, 0.065, length(e - vec2(-0.14, -0.2))));
	return mix(c, vec3(1.0), shine);
}

// The lids over an eye at `e` (as above), the colour of the skin: in the cartoon eye, where its
// character puts them, with a dark line along each edge and a dark outline round the eye; in the
// eye in life, out of sight. `blink` brings them together.
vec3 eye_lids(vec3 c, vec2 e, vec3 lid) {
	float top = mix(1.3, LID_TOP + LID_SLANT * e.x, cartoon_eyes);
	float low = mix(-1.3, LID_LOW + LID_LOW_SLANT * e.x, cartoon_eyes);
	float meet = mix(top, low, 0.7);
	top = mix(top, meet, blink);
	low = mix(low, meet, blink);
	float over = max(smoothstep(-0.02, 0.02, e.y - top), smoothstep(-0.02, 0.02, low - e.y));
	c = mix(c, lid, over);
	float line = max(1.0 - smoothstep(0.035, 0.07, abs(e.y - top)), 1.0 - smoothstep(0.025, 0.05, abs(e.y - low)));
	c = mix(c, vec3(0.02, 0.02, 0.03), line * mix(0.5, 1.0, cartoon_eyes) * step(0.001, max(cartoon_eyes, blink)));
	return mix(c, vec3(0.02, 0.02, 0.03), smoothstep(0.84, 0.92, length(e)) * cartoon_eyes);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

