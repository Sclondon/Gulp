shader_type spatial;
// The sea otter (sea_otter.gd): its fur and face drawn here (no texture files), its swimming, its
// jaw, and its floating on its back. What each point is comes from the model
// (tools/build_sea_otter.py): COLOR.r what it is made of, as a tenth (0 fur, 1 an eye, 2 a tooth,
// 3 the tongue, 4 a whisker, 5 bare hide, 6 a claw); COLOR.g how far inside the mouth it is;
// COLOR.b how far along its limb it is (on an eye, 0 its middle to 1 its rim; on the head and
// jaw, how much it is the lips' edge); UV2.y what moves it, as an eighth (0 nothing, 1 the lower
// jaw, 2 and 3 the left and right fore legs, 4 and 5 the left and right hind feet); UV.x, UV.y
// and UV2.x its hinge (z, y, x in body lengths, plus a half).
//
// Under water it swims as otters do: a wave runs back along its body UP AND DOWN, growing to the
// hips, and the big hind feet and the flat tail beat up and down together at the end of it; the
// fore legs stay tucked to the chest. `afloat` turns it over on to its back at the surface, its
// head and feet lifted, its paws together on its chest. All of it is a function of `phase`
// alone, so a picture of it loops exactly. Nothing here needs more than GL Compatibility has.
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
const float LENGTH = 1.3;
const float HALF = 0.65;
// The corner of the mouth and the jaw's hinge (metres behind the nose).
const float CORNER = 0.058;
const float HINGE_X = 0.094;
const float TURN = 6.2831853;
// The left eye, as the model is built (the build script prints its EYE line): its middle on the
// skin, the way it faces, the way to the nose and up across it, its radius and how far its rim
// lies below a flat across it. The cartoon eye is EYE_GROW times as big.
const vec3 EYE_MID = vec3(0.0428, 0.0449, -0.5900);
const vec3 EYE_OUT = vec3(0.7041, 0.6234, -0.3401);
const vec3 EYE_AHEAD = vec3(-0.2546, -0.2254, -0.9404);
const vec3 EYE_UP = vec3(-0.6629, 0.7487, 0.0);
const float EYE_R = 0.0085;
const float EYE_SAG = 0.00062;
const float EYE_GROW = 1.9;

// How far through a stroke it is (0..1, it wraps). Set by SeaOtter.
uniform float phase = 0.0;
// How hard it swims: 1 an otter cruising under water (its tail tip beats about 0.09 m either way).
uniform float sway = 1.0;
// Floating: 0 swimming belly down, 1 on its back at the surface with its paws on its chest
// (between, it rolls over). Afloat, it does not swim: it only bobs its feet a little.
uniform float afloat = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the neck
// to the tail (more than 0 and its tail comes round to +X, its left).
uniform float curl = 0.0;
// Diving and rising: the same, up (more than 0: its tail comes up) or down.
uniform float arch = 0.0;
// The mouth: 0 shut, 1 wide open.
uniform float gape = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.15;

// The fur of its body; the paler, blonder fur of its head and throat.
uniform vec3 coat : source_color = vec3(0.15, 0.085, 0.045);
uniform vec3 coat_tip : source_color = vec3(0.34, 0.24, 0.15);
uniform vec3 blond : source_color = vec3(0.66, 0.54, 0.38);
// The bare hide of its paws and feet, its nose and lips, the inside of its mouth, its teeth, whiskers.
uniform vec3 hide : source_color = vec3(0.085, 0.06, 0.048);
uniform vec3 nose : source_color = vec3(0.03, 0.025, 0.025);
uniform vec3 mouth_inside : source_color = vec3(0.62, 0.3, 0.3);
uniform vec3 tooth : source_color = vec3(0.92, 0.9, 0.8);
uniform vec3 whiskers : source_color = vec3(0.86, 0.82, 0.7);
// How wet it looks: 1 soaked and sleek, 0 dry and fluffy.
uniform float wet = 0.45;
// The cartoon eye (0 the eye as it is, 1 the cartoon one: big, round and nearly all black, two
// bright highlights, its cheeks pushed up under it in a grin); where both eyes look (x towards its
// nose, y up, -1..1); its lids (0 open, 1 shut: they work with either eye).
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
uniform vec3 iris : source_color = vec3(0.1, 0.055, 0.03);

varying vec3 rest;
varying vec3 rest_normal;
varying float kind;
varying vec2 extra;
varying float moved;

vec3 hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.xxy + p.yxx) * p.zyx);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(hash3(i).x, hash3(i + vec3(1.0, 0.0, 0.0)).x, f.x);
	float b = mix(hash3(i + vec3(0.0, 1.0, 0.0)).x, hash3(i + vec3(1.0, 1.0, 0.0)).x, f.x);
	float c = mix(hash3(i + vec3(0.0, 0.0, 1.0)).x, hash3(i + vec3(1.0, 0.0, 1.0)).x, f.x);
	float d = mix(hash3(i + vec3(0.0, 1.0, 1.0)).x, hash3(i + vec3(1.0, 1.0, 1.0)).x, f.x);
	return mix(mix(a, b, f.y), mix(c, d, f.y), f.z);
}

// How hard it is swimming: not at all when it floats.
float going() {
	return clamp(sway, 0.0, 1.5) * (1.0 - smoothstep(0.0, 0.6, afloat));
}

// How far the middle line of the body is lifted, `xm` metres behind the nose: a wave that runs
// back along it, small at the head, large at the hips and the tail.
float up_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * (0.008 - 0.03 * s + 0.09 * s * s);
	return going() * reach * sin(TURN * (phase - s / wave));
}

vec3 turned(vec3 p, vec3 axis, float a) {
	return p * cos(a) + cross(axis, p) * sin(a) + axis * dot(axis, p) * (1.0 - cos(a));
}

// The body laid round an arc up or down, from `from` back (or, if `ahead`, from there forward):
// `k` is radians a metre, more than 0 and its tail comes up (ahead: less than 0 and its head
// goes down towards its belly).
void bend_up(inout vec3 v, inout vec3 n, float from, float k, bool ahead) {
	float d = v.z - from;
	if (abs(k) < 0.0005 || (d <= 0.0 && !ahead) || (d >= 0.0 && ahead)) {
		return;
	}
	float a = d * k;
	float r = 1.0 / k;
	n = vec3(n.x, n.y * cos(a) + n.z * sin(a), -n.y * sin(a) + n.z * cos(a));
	v = vec3(v.x, r + (v.y - r) * cos(a), from + (r - v.y) * sin(a));
}

void bend_side(inout vec3 v, inout vec3 n, float from, float k) {
	float d = v.z - from;
	if (abs(k) < 0.0005 || d <= 0.0) {
		return;
	}
	float a = d * k;
	float r = 1.0 / k;
	n = vec3(n.x * cos(a) + n.z * sin(a), n.y, -n.x * sin(a) + n.z * cos(a));
	v = vec3(r + (v.x - r) * cos(a), v.y, from + (r - v.x) * sin(a));
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	kind = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	int group = int(UV2.y * 8.0 + 0.5);
	moved = float(group);
	vec3 hinge = (vec3(UV2.x, UV.y, UV.x) - 0.5) * LENGTH;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	rest = v;
	rest_normal = n;
	if (kind == 1.0 && cartoon_eyes > 0.0) {
		// The cartoon eye: the dome made bigger about its own middle, its rim kept down on the
		// skin of the head (which curves away under a bigger eye).
		float g = mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
		vec3 p = vec3(abs(v.x), v.yz) - EYE_MID;
		float o = dot(p, EYE_OUT) * g - (g * g - g) * EYE_SAG * extra.y * extra.y;
		p = EYE_MID + (EYE_AHEAD * dot(p, EYE_AHEAD) + EYE_UP * dot(p, EYE_UP)) * g + EYE_OUT * o;
		v = vec3(v.x < 0.0 ? -p.x : p.x, p.yz);
	}
	float lying = smoothstep(0.0, 1.0, clamp(afloat, 0.0, 1.0));
	if (group == 1) {
		// The lower jaw swings down about its hinge; the skin between the corner of the mouth
		// and the hinge stretches.
		float a = -clamp(gape, 0.0, 1.0) * 0.75 * (1.0 - smoothstep(CORNER, HINGE_X, v.z + HALF));
		v = hinge + turned(v - hinge, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	} else if (group == 2 || group == 3) {
		// The fore legs: tucked back along the chest to swim; brought forward and in, so that the
		// paws meet on the chest, to float.
		float side = group == 2 ? 1.0 : -1.0;
		vec3 axis = normalize(vec3(0.8, -side * 0.575, -side * 0.16));
		v = hinge + turned(v - hinge, axis, 1.94 * lying);
		n = turned(n, axis, 1.94 * lying);
	} else if (group >= 4) {
		// The hind feet: they beat up and down behind the body's wave, bending along their
		// length; afloat, they are turned up out of the water, and bob a little.
		float s = (hinge.z + HALF) / LENGTH;
		float beat = going() * 0.55 * sin(TURN * (phase - s / wave - 0.16 - 0.1 * extra.y));
		float bob = lying * (0.95 + 0.12 * clamp(sway, 0.0, 1.5) * sin(TURN * phase + (group == 4 ? 0.0 : 2.0)));
		float a = (beat + bob) * smoothstep(0.0, 0.35, extra.y);
		v = hinge + turned(v - hinge, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	}
	// The swim: each cross-section moved to the body's line and turned to stay square to it.
	float xm = v.z + HALF;
	float zc = clamp(xm, 0.0, LENGTH);
	float g = up_at(zc);
	float pitch = atan((up_at(zc + 0.008) - up_at(zc - 0.008)) / 0.016);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(o.x, g + o.y * cos(pitch) + o.z * sin(pitch), zc - HALF - o.y * sin(pitch) + o.z * cos(pitch));
	n = vec3(n.x, n.y * cos(pitch) + n.z * sin(pitch), -n.y * sin(pitch) + n.z * cos(pitch));
	bend_side(v, n, -0.2 * LENGTH, curl / (0.7 * LENGTH));
	bend_up(v, n, -0.2 * LENGTH, arch / (0.7 * LENGTH), false);
	// Afloat: its head and chest lifted towards its belly, then the whole of it rolled over on
	// to its back.
	bend_up(v, n, -0.1 * LENGTH, -1.0 * lying, true);
	float roll = 3.14159265 * lying;
	v.xy = vec2(v.x * cos(roll) - v.y * sin(roll), v.x * sin(roll) + v.y * cos(roll));
	n.xy = vec2(n.x * cos(roll) - n.y * sin(roll), n.x * sin(roll) + n.y * cos(roll));
	VERTEX = v;
	NORMAL = n;
}

float to_segment(vec2 p, vec2 a, vec2 b) {
	vec2 d = b - a;
	return length(p - a - d * clamp(dot(p - a, d) / dot(d, d), 0.0, 1.0));
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

