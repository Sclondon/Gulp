shader_type spatial;
// The goldfish (goldfish.gd): every marking drawn here (no texture files), and its swimming, for both
// kinds (common and fantail: goldfish.gd sets the numbers that differ, `joint` to `gill_at`, from its
// KINDS). What each point is comes from the model (tools/build_goldfish.py): UV2.y the part (0 body, 1 the
// dorsal fin, 2 an anal fin, 3 a tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw).
// UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its
// side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to edge (1), y leading
// edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1).
//
// It swims as carp do (subcarangiform): a wave runs back along the body, small at the head and growing
// through the back half; behind its hinge the tail is carried round with the wrist, and its fins billow
// (a wave that runs out from root to edge: `billow`, much more on the fantail's long double tail). All of
// it is a function of `phase` alone, so a picture of it loops exactly. The mouth opens (`gape`): the
// lower jaw swings down about its hinge and the whole mouth pushes forward a little, as a goldfish's does.
// Nothing here needs more than GL Compatibility has.
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


const float LENGTH = 0.15;
const float HALF = 0.075;
// How far the lower jaw swings down, wide open (radians), and how far the mouth pushes forward and up.
const float GAPE_OPEN = 0.95;
const float PROTRUDE = 0.0012;
const float LIFT = 0.0003;

// Kept in step with the model of each kind (goldfish.gd's KINDS; the build script prints them).
// Where the tail is hinged (metres behind the snout); where the lower jaw is hinged, along and up; where
// the body ends; the eye's middle (along, up); where the gill cover's edge is, at the middle line.
uniform float joint = 0.108;
uniform float jaw_to = 0.0095;
uniform float hinge_y = -0.00154;
uniform float body_to = 0.116;
uniform vec2 eye_at = vec2(0.0175, 0.0042);
uniform float gill_at = 0.029;

// How far through a beat of its tail (0..1, it wraps). Set by Goldfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats, for 1 as a goldfish cruising.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.0;
// How much its fins billow (the tail most): 0 stiff, 1 the fantail's long tail flowing.
uniform float billow = 0.3;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The colours. `base` all over, `back` the top of the back shades to, `belly` the belly. Patches of `patch`
// (red on a red-and-white, orange on a calico) cover about `patch_amount` of it; patches of `black` cover
// `black_amount`, and black `speckle` (0 none) peppers it, as on a calico.
uniform vec3 base : source_color = vec3(0.98, 0.45, 0.06);
uniform vec3 back : source_color = vec3(0.82, 0.3, 0.03);
uniform vec3 belly : source_color = vec3(1.0, 0.72, 0.36);
uniform vec3 patch : source_color = vec3(0.86, 0.12, 0.04);
uniform float patch_amount = 0.0;
uniform vec3 black : source_color = vec3(0.03, 0.03, 0.04);
uniform float black_amount = 0.0;
uniform float speckle = 0.0;
// Patches lie more on the back and the head than low on the flank, this much (0 evenly).
uniform float patch_on_back = 0.5;
// How bright the scales are (metallic scales shine; a calico's are matt): 0 matt, 1 bright.
uniform float shine = 0.8;
// How strongly the scales' edges show.
uniform float scales_show = 0.7;
// The fins: their colour at the root and at the edge; how see-through they look (paler, like the water).
uniform vec3 fin_root : source_color = vec3(0.98, 0.48, 0.1);
uniform vec3 fin_edge : source_color = vec3(1.0, 0.7, 0.42);
uniform float fin_clear = 0.35;
// The water's colour that clear fins take on.
uniform vec3 water : source_color = vec3(0.55, 0.7, 0.78);
// The eye's ring (iris); the inside of the mouth.
uniform vec3 iris : source_color = vec3(0.85, 0.55, 0.12);
uniform vec3 mouth_inside : source_color = vec3(0.32, 0.06, 0.06);

// Cartoon eyes (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0, the default, is the eye drawn below, as it always was; 1 the cartoon eye: grown about
// its middle, a white, the colouring's `iris`, a big round pupil, a highlight that stays put (up and forward,
// towards the light) and a dark rim, under an upper lid the colour of its skin. The goldfish's: a wide,
// goggling, empty-headed stare: much white, a big round pupil, the lid barely over its top.
uniform float cartoon_eyes = 0.0;
// Where the cartoon eye looks, -1..1 each way: x towards the nose (+) or the tail, y up (+) or down.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat from above and below (a fish has no lids) and the lid comes down.
uniform float blink = 0.0;
// As the model has it (goldfish.gd's KINDS, from the build script's EYE line): the left eye's middle on the
// skin and the way it faces (metres; the right eye is its mirror), and its radius over the skin.
uniform vec3 eye_middle = vec3(0.00989, 0.0042, -0.0575);
uniform vec3 eye_out = vec3(0.9694, 0.1511, -0.1933);
uniform float eye_radius = 0.0043;
// How much bigger the cartoon eye is; how far its grown rim sinks back towards the skin (1 / (2 x the head's
// radius there), up and down and along); its white; its iris (how wide, of the eye's face); its pupil (how wide, of the iris); where
// the upper lid's edge rests (1 the top of the eye: no lid; 0 its middle) and how much lower it comes at the
// front (less than 0 raises it there).
uniform float eye_grow = 1.55;
uniform vec2 eye_sink = vec2(30.0, 6.0);
uniform vec3 eye_white : source_color = vec3(0.98, 0.97, 0.92);
uniform float iris_size = 0.62;
uniform float pupil_size = 0.7;
uniform float lid = 0.92;
uniform float lid_slant = -0.1;

// The gills (added 2026-11-18; the user: "The fish need modeled gills as well, ... so like when it opens its
// mouth wide you can see them"): four arches a side in the throat behind the mouth, seen through it when it is
// open (closed in, they are not seen at all). As the model has them (KINDS, the build script's GILLS line):
// the gap between two arches and where the throat ends. Their red, and their rakers' pale.
uniform float gill_gap = 0.00338;
uniform float throat_end = 0.0319;
uniform vec3 gill_red : source_color = vec3(0.66, 0.05, 0.07);
uniform vec3 gill_raker : source_color = vec3(0.9, 0.66, 0.62);

varying vec3 rest;
varying float part;
varying float inside;

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), f.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), f.x), f.y);
	float b = mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), f.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), f.x), f.y);
	return mix(a, b, f.z);
}

float fbm3(vec3 p) {
	return 0.55 * noise3(p) + 0.3 * noise3(p * 2.1 + 7.0) + 0.15 * noise3(p * 4.3 + 13.0);
}

// How far to one side the middle line of the body is, `xm` metres behind the snout.
float side_at(float xm) {
	float s = xm / joint;
	float reach = LENGTH * (0.01 - 0.035 * s + 0.085 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * joint / (LENGTH * wave)));
}

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

// The cartoon eye grown about its middle, and squashed from above and below as it blinks (nothing moves
// while cartoon_eyes and blink are 0).
void eye_shape(inout vec3 v) {
	if (cartoon_eyes <= 0.0 && blink <= 0.0) {
		return;
	}
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	vec3 at = vec3(eye_middle.x * side_is, eye_middle.yz);
	vec3 o = normalize(vec3(eye_out.x * side_is, eye_out.yz));
	vec3 up = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
	vec3 d = v - at;
	float grow = mix(1.0, eye_grow, cartoon_eyes);
	// (grown across and outward; what lies behind its face is not pushed further in; the grown rim sinks
	// back as the head's skin falls away round it)
	float deep = min(dot(d, o), 0.0);
	vec3 across = d - o * dot(d, o);
	vec3 up_d = up * dot(across, up);
	float before = eye_sink.x * dot(up_d, up_d) + eye_sink.y * dot(across - up_d, across - up_d);
	d = (d - o * deep) * grow + o * deep;
	d -= o * before * (grow * grow - 1.0);
	d -= up * dot(d, up) * 0.85 * blink;
	v = at + d;
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	inside = UV2.x;
	vec3 v = VERTEX;
	float xm = v.z + HALF;
	float g = clamp(gape, 0.0, 1.0);
	if (part > 5.5 && part < 6.5) {
		eye_shape(v);
		xm = v.z + HALF;
	}
	// The gill arches spread a little apart as the mouth opens.
	if (part > 9.5) {
		v.z += g * 0.14 * gill_gap * (floor(UV.y) - 1.5);
		xm = v.z + HALF;
	}
	// The mouth pushes forward (and the upper lip lifts) as it opens: all of it ahead of the hinge.
	if ((part < 0.5 || (part > 6.5 && part < 7.5)) && xm < jaw_to) {
		float w = 1.0 - smoothstep(0.3 * jaw_to, jaw_to, xm);
		v.z -= g * PROTRUDE * w;
		v.y += g * LIFT * w * step(part, 0.5);
		xm = v.z + HALF;
	}
	if (part > 6.5 && part < 7.5) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = g * GAPE_OPEN * (1.0 - smoothstep(0.55 * jaw_to, 0.97 * jaw_to, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - hinge_y, xm - jaw_to);
		v.y = hinge_y + d.x * ca + d.y * sa;
		v.z = jaw_to - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	// The fins billow: a wave that runs out from root to edge, most on the tail.
	if (part > 0.5 && part < 5.5) {
		float t = UV.x;
		float amount = billow * (part > 2.5 && part < 3.5 ? 1.0 : 0.3) * (0.4 + 0.6 * min(sway, 1.5));
		float flow = sin(6.2831853 * (phase - 0.75 * t - 0.25 * UV.y));
		v.x += amount * LENGTH * 0.05 * pow(t, 1.5) * flow;
		v.y -= amount * LENGTH * 0.012 * t * t * (0.5 + 0.5 * flow);
	}
	// (the tail, behind its hinge, is carried round with the wrist)
	float zc = min(xm, joint);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0005) - side_at(zc - 0.0005)) / 0.001;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.85 * joint, joint, zc));
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

// The colour of the skin (and the fins' roots) at a place: the base colour, its patches and speckles.
vec4 coat(vec3 p, float high) {
	vec3 c = base;
	float plain = 1.0;
	float field = fbm3(p * 70.0 + vec3(3.0, 1.0, 5.0)) + patch_on_back * 0.35 * (high - 0.5);
	float edge = 1.0 - patch_amount;
	float in_patch = smoothstep(0.43 + 0.3 * edge - 0.03, 0.43 + 0.3 * edge + 0.03, field) * step(0.001, patch_amount);
	c = mix(c, patch, in_patch);
	plain -= in_patch;
	float dark = fbm3(p * 95.0 + vec3(11.0, 4.0, 2.0));
	float in_black = smoothstep(0.73 - 0.3 * black_amount - 0.03, 0.73 - 0.3 * black_amount + 0.03, dark) * step(0.001, black_amount);
	c = mix(c, black, in_black);
	plain *= 1.0 - in_black;
	float specks = noise3(p * 900.0);
	c = mix(c, black, smoothstep(0.86 - 0.12 * speckle, 0.9 - 0.12 * speckle, specks) * step(0.001, speckle) * smoothstep(0.3, 0.7, noise3(p * 160.0 + 2.0)));
	return vec4(c, max(plain, 0.0));
}

// The cartoon eye's colour at a place on its face: `e` x up, y forward, 1 at its rim. A round pupil.
vec3 cartoon_eye(vec2 e) {
	float r = length(e);
	vec2 q = e - vec2(eye_look.y, eye_look.x) * (0.92 - iris_size);
	float ri = length(q) / iris_size;
	float aa = fwidth(ri) + 0.01;
	vec3 c = eye_white * mix(1.0, 0.8, smoothstep(0.45, 1.0, r));
	vec3 ring = mix(iris * 1.25, iris * 0.6, smoothstep(0.3, 0.95, ri));
	ring = mix(ring, iris * 0.2, smoothstep(0.84, 1.0, ri));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ri));
	float pd = length(q) / (iris_size * pupil_size);
	float pa = fwidth(pd) + 0.02;
	c = mix(c, vec3(0.012), 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	// (the highlight: up and forward, where the light comes from, and a small second one below behind)
	float glint = 1.0 - smoothstep(0.15, 0.19, length(e - vec2(0.34, 0.3)));
	glint = max(glint, 0.8 * (1.0 - smoothstep(0.06, 0.09, length(e - vec2(-0.24, -0.26)))));
	c = mix(c, vec3(1.0), glint);
	// (the dark outline, so that it reads from far off)
	return mix(c, vec3(0.03, 0.015, 0.0), smoothstep(0.84, 0.91, r));
}

// The gills' colour: `uv` as the model gives it (x 0 the rakers' side, about 0.35 the bar, 1 the filaments;
// y the arch's number plus how far along it), `xm` how far back: blood red, the filaments darker with fine
// lines across, the rakers pale, all darker deeper in the throat.
vec3 gills(vec2 uv, float xm) {
	float along = fract(uv.y);
	vec3 fringe = gill_red * 0.62 * (0.72 + 0.28 * cos(along * 160.0));
	vec3 c = mix(gill_red * 1.15, fringe, smoothstep(0.45, 0.9, uv.x));
	float teeth = 0.6 + 0.4 * step(0.45, fract(along * 11.0));
	c = mix(c, gill_raker, (1.0 - smoothstep(0.06, 0.24, uv.x)) * teeth);
	return c * (1.0 - 0.5 * smoothstep(jaw_to, throat_end, xm));
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

