shader_type spatial;
// The ichthyosaur (ichthyosaur.gd): every marking drawn here (no texture files), its swimming, its
// mouth and its eyes. What each point is comes from the model (tools/build_ichthyosaur.py): UV2.y the
// part (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower tooth, 4 the tail's lobes, 5 the dorsal fin,
// 6 a fore flipper, 7 an eye, 8 a hind flipper); UV2.x, on the body and the jaw, how much it is inside
// the mouth (on the tail, 1 the lower lobe). UV, on the body and jaw: x how far along, y how high on
// its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y
// leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1).
//
// It swims as a tuna does: its tail beats SIDE TO SIDE. The front of the body all but still, a wave
// growing steeply down the tail stock, and the crescent tail turning about its root as one stiff
// plate. All of it is a function of `phase` alone, so a picture of it loops exactly.
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
const float LENGTH = 4.0;
const float HALF = 2.0;
// Where the tail is hinged (metres behind the tip of the beak): behind it, one stiff plate.
const float JOINT = 3.42;
// The corner of the mouth, where the lower jaw hinges (metres behind the tip, metres up), and how far
// the jaw's turn is spread round it.
const float CORNER = 0.74;
const float HINGE_Y = -0.0252;
const float HINGE_SPREAD = 0.06;
const vec2 EYE_AT = vec2(0.92, 0.05);
const float JAW_FROM = 0.022;
// How far the lower jaw swings down for `gape` 1 (radians), and how far the middle line swings for
// `sway` 1 (of its length).
const float GAPE_MAX = 0.55;
const float REACH = 0.07;

// How far through a beat of its tail (0..1, it wraps). Set by Ichthyosaur.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the fore
// flippers to the tail (0 straight; more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// How widely it beats, for 1 as one cruising (its tail tips swing about 0.25 m each way).
uniform float sway = 1.0;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape = 0.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.1;

// The back, the flank, the belly; the fins; the inside of the mouth; the teeth; the bony ring round
// the eye.
uniform vec3 back : source_color = vec3(0.09, 0.11, 0.14);
uniform vec3 flank : source_color = vec3(0.3, 0.34, 0.38);
uniform vec3 belly : source_color = vec3(0.86, 0.84, 0.78);
uniform vec3 fin : source_color = vec3(0.08, 0.095, 0.12);
uniform vec3 mouth : source_color = vec3(0.6, 0.32, 0.3);
uniform vec3 tooth : source_color = vec3(0.92, 0.88, 0.76);
uniform vec3 ring : source_color = vec3(0.42, 0.42, 0.38);
// How strongly the faint dark bands across its back show (0 none).
uniform float bands = 0.35;

// The cartoon eye (0 the eye as in life, 1 the cartoon eye), where its eyes look (x +1 towards the
// nose, y +1 up, each in its own plane) and its lids (0 open, 1 shut). Set by the node.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// Where the right eye sits, as the model has it (the build script prints it: EYE_FRAME; the left eye
// is its mirror): its middle on the skin, the way out of the head, the way to the nose and the way up
// in the eye's own plane, how fast the skin falls away from that plane round it (metres per square
// metre), and the eye's radius (its bony ring and all).
const vec3 EYE_CENTRE = vec3(0.15064, 0.05000, -1.08000);
const vec3 EYE_OUT = vec3(0.9659, 0.1317, -0.2229);
const vec3 EYE_FWD = vec3(-0.2208, -0.0301, -0.9748);
const vec3 EYE_UP = vec3(-0.1351, 0.9908, 0.0000);
const float EYE_SAG = 0.9110;
const float EYE_RADIUS = 0.095;
// The ichthyosaur's: enormous and startled. Bigger than life by only 1.3 (it is huge already); the
// eye inside its ring of bony plates (out to RING_IN of the radius, the plates beyond); a lot of
// clean white showing all round, a small pale blue-grey iris, a small round pupil (the startled
// stare), one big highlight; the lids pulled wide open, thin lines.
const float EYE_GROW = 1.3;
const float RING_IN = 0.66;
const vec3 SCLERA = vec3(0.97, 0.97, 0.95);
const vec3 IRIS_LIGHT = vec3(0.55, 0.68, 0.78);
const vec3 IRIS_DARK = vec3(0.16, 0.26, 0.36);
const float IRIS = 0.4;
const vec2 IRIS_AT = vec2(0.0, 0.0);
const vec2 LOOK_REACH = vec2(0.36, 0.3);
const vec2 GLINT_AT = vec2(0.24, 0.3);
const float GLINT = 0.14;
const vec2 GLINT2_AT = vec2(-0.2, -0.16);
const vec3 OUTLINE = vec3(0.03, 0.035, 0.045);
const float LINE_UP = 0.06;
const float LINE_DOWN = 0.05;

// (inside the pupil where this is under 0; `q` from the iris's middle, in eye radii)
float pupil(vec2 q) {
	return length(q) - 0.16;
}

float lid_up(float x) {
	return 1.02 - 0.1 * x * x;
}

float lid_down(float x) {
	return -1.0 + 0.1 * x * x;
}

vec3 lid_colour() {
	return mix(back, flank, 0.5);
}

// (where an eye's point lies in the eye's own plane, in eye radii: x towards the nose, y up)
varying vec2 eye_at;

// The eye's dome grown about its own middle for the cartoon eye, its rim laid back on the skin.
void eye_grow(inout vec3 v, out vec2 at) {
	vec3 m = vec3(v.x >= 0.0 ? 1.0 : -1.0, 1.0, 1.0);
	vec3 d = v - EYE_CENTRE * m;
	vec2 pl = vec2(dot(d, EYE_FWD * m), dot(d, EYE_UP * m));
	at = pl / EYE_RADIUS;
	if (cartoon_eyes <= 0.0) {
		return;
	}
	float g = mix(1.0, EYE_GROW, cartoon_eyes);
	float r2 = dot(pl, pl);
	float over = dot(d, EYE_OUT * m) + EYE_SAG * r2;
	float h = over * g - EYE_SAG * r2 * g * g;
	v = EYE_CENTRE * m + (EYE_FWD * m * pl.x + EYE_UP * m * pl.y) * g + EYE_OUT * m * h;
}

// The ring of bony plates round the eye (the sclerotic ring), `e` in eye radii.
vec3 bony_ring(vec2 e, vec3 c) {
	float r = length(e);
	float a = atan(e.y, e.x);
	float plate = abs(fract(a / TAU * 14.0) - 0.5);
	vec3 bone = ring * (0.8 + 0.25 * smoothstep(RING_IN, 0.85, r) * (1.0 - smoothstep(0.85, 1.0, r)));
	bone = mix(bone, ring * 0.45, smoothstep(0.42, 0.5, plate));
	return mix(c, bone, smoothstep(RING_IN - 0.02, RING_IN + 0.02, r));
}

// The cartoon eye's colour at `e` (eye_at); `lit` how much of it glows a little.
vec3 cartoon_eye(vec2 e0, out float lit) {
	// (the eye itself inside the bony ring, in its own radii)
	vec2 e = e0 / RING_IN;
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 q = e - IRIS_AT - clamp(eye_look, vec2(-1.0), vec2(1.0)) * LOOK_REACH;
	float qi = length(q);
	vec3 c = SCLERA * (1.0 - 0.18 * smoothstep(0.55, 0.9, r));
	vec3 iris = mix(IRIS_LIGHT, IRIS_DARK, smoothstep(IRIS * 0.5, IRIS, qi));
	c = mix(c, iris, 1.0 - smoothstep(IRIS - aa, IRIS + aa, qi));
	c = mix(c, vec3(0.01), 1.0 - smoothstep(-aa, aa, pupil(q)));
	float glint = max(1.0 - smoothstep(GLINT - aa, GLINT + aa, length(e - GLINT_AT)),
		1.0 - smoothstep(GLINT * 0.45 - aa, GLINT * 0.45 + aa, length(e - GLINT2_AT)));
	c = mix(c, vec3(1.0), glint);
	lit = mix(0.5, 1.0, glint);
	c = mix(c, OUTLINE, smoothstep(0.9 - aa, 0.93 + aa, r));
	// the lids, meeting at the middle as it blinks
	float b = clamp(blink, 0.0, 1.0);
	float meet = mix(lid_down(e.x), lid_up(e.x), 0.5);
	float up = mix(lid_up(e.x), meet, b);
	float down = mix(lid_down(e.x), meet, b);
	float over_up = e.y - up;
	float over_down = down - e.y;
	float lid = max(smoothstep(-aa, aa, over_up), smoothstep(-aa, aa, over_down)) * (1.0 - step(1.0, r));
	c = mix(c, lid_colour(), lid);
	lit *= 1.0 - lid;
	float line = max(smoothstep(-aa, aa, over_up) * (1.0 - smoothstep(LINE_UP - aa, LINE_UP + aa, over_up)),
		smoothstep(-aa, aa, over_down) * (1.0 - smoothstep(LINE_DOWN - aa, LINE_DOWN + aa, over_down)));
	c = mix(c, OUTLINE, line * (1.0 - step(0.98, r)));
	// (the bony plates round it stay)
	vec3 out_c = bony_ring(e0, c);
	lit *= 1.0 - smoothstep(RING_IN - 0.02, RING_IN + 0.02, length(e0));
	return out_c;
}

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

// How far to the side the middle line of the body is, `xm` metres behind the tip: a wave that runs
// back along it, least just behind the head, large only down the tail stock.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * REACH * (0.06 - 0.28 * s + 0.33 * s * s + 0.9 * s * s * s * s);
	return sway * reach * sin(TAU * (phase - s / wave));
}

// The body behind the head laid round an arc to one side (see `curl`).
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
	inside = UV2.x;
	rest = VERTEX;
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	eye_at = vec2(0.0);
	if (p == 7) {
		vec2 at;
		eye_grow(v, at);
		eye_at = at;
	}
	if (p == 1 || p == 3) {
		// The lower jaw (and its teeth) swings down about the corner of the mouth; behind the
		// corner, inside the body, it stays.
		float a = GAPE_MAX * clamp(gape, 0.0, 1.0) * smoothstep(CORNER + 0.015, CORNER - HINGE_SPREAD, v.z + HALF);
		vec2 hinge = vec2(HINGE_Y, CORNER - HALF);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	float xm = v.z + HALF;
	// (the tail, behind its hinge, is one stiff plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.01) - side_at(zc - 0.01)) / 0.02;
	// (the tail turns a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.4 * smoothstep(0.85 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The line of the mouth, as the model has it.
float mouth_y(float xm) {
	return -0.003 - 0.03 * xm;
}

// The skin at a place: `xm` behind the tip, `h` how high on its side (0..1).
vec3 skin(float xm, float h, float side) {
	float grain = noise2(vec2(xm * 70.0, h * 30.0 + side * 9.0));
	float cloud = noise2(vec2(xm * 6.0, h * 5.0) + 3.0 + side * 5.0);
	// Countershaded: the belly pale, the flank grey, the back dark, the line between wavering.
	float edge = 0.6 - 0.06 * smoothstep(0.8, 1.8, xm) + 0.1 * smoothstep(2.6, 3.4, xm) + (cloud - 0.5) * 0.08;
	vec3 c = mix(belly, flank, smoothstep(0.28, 0.46, h + (cloud - 0.5) * 0.06));
	c = mix(c, back, smoothstep(edge - 0.1, edge + 0.06, h));
	// Faint dark bands across the back, wavering, fading down the flanks.
	float wob = noise2(vec2(xm * 3.0, h * 4.0 + side * 2.0));
	float band = smoothstep(0.55, 0.9, sin(xm * 16.0 + (wob - 0.5) * 3.0 - h * 3.0));
	c = mix(c, c * 0.62, band * bands * smoothstep(0.45, 0.75, h) * smoothstep(1.0, 1.3, xm) * (1.0 - smoothstep(3.2, 3.6, xm)));
	// (the beak darker on top)
	c = mix(c, back * 1.1, (1.0 - smoothstep(0.55, 0.8, xm)) * smoothstep(0.45, 0.65, h));
	c *= 0.93 + 0.14 * grain;
	return c;
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

