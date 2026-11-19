shader_type spatial;
// The harbor seal (harbor_seal.gd): its coat, spots and face drawn here (no texture files), its
// swimming, its hind flippers and its jaw. What each point is comes from the model
// (tools/build_harbor_seal.py): COLOR.r what it is made of, as a tenth (0 fur, 1 an eye, 2 a
// tooth, 3 the tongue, 4 a whisker, 5 bare hide, 6 a claw); COLOR.g how far inside the mouth it
// is (0.5 the lip's edge); COLOR.b how far along its flipper it is (on an eye, 0 its middle to 1
// its rim; on the head and jaw, how much it is the lips' edge); UV2.y what moves it, as an eighth (0 nothing, 1 the lower jaw, 2 and 3 the left and
// right fore flippers, 4 and 5 the left and right hind flippers); UV.x, UV.y and UV2.x its hinge
// (z, y, x in body lengths, plus a half).
//
// It swims as true seals do: the fore flippers held to its sides, the rear of the body and the
// hind flippers sculled from side to side like a fish's tail, each hind flipper fanned open as it
// pushes and closed as it comes back. All of it is a function of `phase` alone, so a picture of
// it loops exactly. Nothing here needs more than GL Compatibility has.
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
const float LENGTH = 1.6;
const float HALF = 0.8;
// The corner of the mouth and the jaw's hinge (metres behind the nose).
const float CORNER = 0.082;
const float HINGE_X = 0.128;
// Where the hind flippers are hinged: behind it they swing as one plate.
const float JOINT = 1.36;
const float TURN = 6.2831853;
// The left eye, as the model is built (the build script prints its EYE line): its middle on the
// skin, the way it faces, the way to the nose and up across it, its radius and how far its rim
// lies below a flat across it. The cartoon eye is EYE_GROW times as big.
const vec3 EYE_MID = vec3(0.0580, 0.0596, -0.7120);
const vec3 EYE_OUT = vec3(0.6805, 0.5607, -0.4718);
const vec3 EYE_AHEAD = vec3(-0.3641, -0.3000, -0.8817);
const vec3 EYE_UP = vec3(-0.6359, 0.7718, 0.0);
const float EYE_R = 0.0215;
const float EYE_SAG = 0.00313;
const float EYE_GROW = 1.35;

// How far through a stroke it is (0..1, it wraps). Set by HarborSeal.
uniform float phase = 0.0;
// How widely it sculls, for 1 as a seal cruising (its flipper tips swing about 0.2 m either way).
uniform float sway = 1.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the neck
// to the hind flippers (more than 0 and its tail comes round to +X, its left).
uniform float curl = 0.0;
// Diving and rising: the same, up (more than 0: its tail comes up) or down.
uniform float arch = 0.0;
// The mouth: 0 shut, 1 wide open.
uniform float gape = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.25;

// The coat on its flanks, on its back, on its belly; `tawny` (0..1) turns a silver-grey seal
// into a tan one.
uniform vec3 coat : source_color = vec3(0.47, 0.48, 0.47);
uniform vec3 coat_back : source_color = vec3(0.2, 0.215, 0.23);
uniform vec3 belly : source_color = vec3(0.74, 0.72, 0.66);
uniform vec3 coat_tan : source_color = vec3(0.56, 0.44, 0.3);
uniform float tawny = 0.0;
// The dark spots, the pale rings round some of them, and how strongly they show.
uniform vec3 spot : source_color = vec3(0.035, 0.036, 0.04);
uniform vec3 ring : source_color = vec3(0.8, 0.79, 0.74);
uniform float spots_show = 1.0;
// The nose and lips, the inside of the mouth, the teeth, the whiskers, the claws.
uniform vec3 nose : source_color = vec3(0.075, 0.07, 0.075);
uniform vec3 mouth_inside : source_color = vec3(0.62, 0.3, 0.3);
uniform vec3 tooth : source_color = vec3(0.92, 0.9, 0.8);
uniform vec3 whiskers : source_color = vec3(0.85, 0.83, 0.75);
uniform vec3 claw : source_color = vec3(0.06, 0.055, 0.05);
// How wet it looks: 1 just out of a dive, 0 dry fur.
uniform float wet = 0.8;
// The cartoon eye (0 the eye as it is, 1 the cartoon one: bigger, a pale white, a dark brown iris
// and a big round pupil, a highlight, a soft heavy upper lid); where both eyes look (x towards its
// nose, y up, -1..1); its lids (0 open, 1 shut: they work with either eye).
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
uniform vec3 iris : source_color = vec3(0.2, 0.11, 0.05);

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

// The nearest of a scatter of points, one to a cell: (how far, in cells; a number of its own).
vec2 scatter(vec3 p) {
	vec3 b = floor(p - 0.5);
	float best = 9.0;
	float id = 0.0;
	for (int k = 0; k < 8; k++) {
		vec3 cell = b + vec3(float(k & 1), float((k >> 1) & 1), float((k >> 2) & 1));
		vec3 h = hash3(cell);
		float d = length(p - (cell + 0.5 + (h - 0.5) * 0.6));
		if (d < best) {
			best = d;
			id = fract(h.x * 7.3 + h.y * 3.1);
		}
	}
	return vec2(best, id);
}

// How far to one side the middle line of the body is, `xm` metres behind the nose: a wave that
// runs back along it, small as far as the middle, large at the hips.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.004 - 0.012 * s + 0.01 * s * s + 0.072 * s * s * s);
	return sway * reach * sin(TURN * (phase - s / wave));
}

vec3 turned(vec3 p, vec3 axis, float a) {
	return p * cos(a) + cross(axis, p) * sin(a) + axis * dot(axis, p) * (1.0 - cos(a));
}

// The body behind the head laid round an arc: to one side (`curl`) and up or down (`arch`).
void bend(inout vec3 v, inout vec3 n, float sideways, float upward) {
	float from = -0.2 * LENGTH;
	float d = v.z - from;
	if (d <= 0.0) {
		return;
	}
	if (abs(sideways) > 0.001) {
		float k = sideways / (0.7 * LENGTH);
		float a = d * k;
		float r = 1.0 / k;
		n = vec3(n.x * cos(a) + n.z * sin(a), n.y, -n.x * sin(a) + n.z * cos(a));
		v = vec3(r + (v.x - r) * cos(a), v.y, from + (r - v.x) * sin(a));
		d = v.z - from;
	}
	if (abs(upward) > 0.001 && d > 0.0) {
		float k = upward / (0.7 * LENGTH);
		float a = d * k;
		float r = 1.0 / k;
		n = vec3(n.x, n.y * cos(a) + n.z * sin(a), -n.y * sin(a) + n.z * cos(a));
		v = vec3(v.x, r + (v.y - r) * cos(a), from + (r - v.y) * sin(a));
	}
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
	if (group == 1) {
		// The lower jaw swings down about its hinge; the skin between the corner of the mouth
		// and the hinge stretches.
		float a = -clamp(gape, 0.0, 1.0) * 0.78 * (1.0 - smoothstep(CORNER, HINGE_X, v.z + HALF));
		v = hinge + turned(v - hinge, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	} else if (group >= 4) {
		// A hind flipper fans open as it pushes (the right one as the tail swings to its left,
		// the left one as it swings back) and closes as it is carried back.
		float side = group == 4 ? 1.0 : -1.0;
		float open = 1.0 - 0.34 * clamp(sway, 0.0, 1.5) * side * cos(TURN * (phase - 1.0 / wave));
		v.y = hinge.y + (v.y - hinge.y) * mix(1.0, open, smoothstep(0.0, 0.5, extra.y));
	}
	// The scull: each cross-section moved to the body's line and turned to stay square to it;
	// behind their hinge the hind flippers swing as one plate, a little further.
	float xm = v.z + HALF;
	float zc = clamp(xm, 0.0, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.008) - side_at(zc - 0.008)) / 0.016;
	float yaw = atan(slope) * (1.0 + 0.45 * smoothstep(0.85 * JOINT, JOINT, zc));
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * cos(yaw) + o.z * sin(yaw), o.y, zc - HALF - o.x * sin(yaw) + o.z * cos(yaw));
	n = vec3(n.x * cos(yaw) + n.z * sin(yaw), n.y, -n.x * sin(yaw) + n.z * cos(yaw));
	bend(v, n, curl, arch);
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

