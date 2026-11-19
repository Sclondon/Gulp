shader_type spatial;
// The sea monsters' one shader, shared by GameCommon's `leviathan` (Leviathan) and `sea-serpent` (SeaSerpent):
// one shader program for both (a browser compiles each new program once, which takes a second or more). Every
// marking is drawn here (no texture files), and it swims them, opens their mouths and sways what hangs off them.
// Each creature's script sets the settings that say where its parts are (the "shape" settings below), once, on its
// material; `kind` picks its markings and its eye. Both components carry this same file at the same path
// (creatures/sea_monster/sea_monster.gdshader): installing either puts it there, and both use the one copy.
//
// What each point is comes from the model: UV2.y the part (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower tooth,
// 4 a fin, 5 weed, 6 a side fin that flaps, 7 an eye, 8 a barnacle, 9 a harpoon or anchor, 10 a rope, 11 an
// armour scute); UV2.x, on the body and the jaw, how much it is inside the mouth (on a harpoon or anchor, 1 its
// iron; on a barnacle, 1 the hole in its top; on a scute, a number of its own for its tint).
// UV, on the body and jaw: x how far along (0 the tip of the snout, 1 the tail), y how high on its side (1 the
// ridge of the back, 0 the keel); on a fin: x root (0) to tip (1), y leading (0) to trailing edge (1); on an eye:
// x middle (0) to rim (1); on a rope or weed: x from where it is tied (0) to its free end (1).
//
// All motion is a function of `phase` alone, so a picture of it loops exactly. Nothing here needs more than GL
// Compatibility has; it runs the same under Forward+.
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


// Which monster: 0 the leviathan, 1 the sea serpent.
uniform int kind = 0;

// ---- Shape (set by each creature's script from its build script's numbers) ----
// Its length (metres, as built) and where its tail fin is hinged (metres behind the tip; behind it, one plate).
uniform float body_length = 40.0;
uniform float joint = 37.2;
// The corner of the mouth (metres behind the tip), the height of the jaw's hinge, how far the jaw's turn is spread
// round it, how far the lower jaw swings for `gape` 1 and the skull lifts with it (radians), where the lower jaw
// begins, and the line of the mouth (y = mouth_a + mouth_b * metres behind the tip).
uniform float corner = 10.2;
uniform float hinge_y = -1.5;
uniform float hinge_spread = 1.2;
uniform float gape_max = 1.05;
uniform float lift_max = 0.2;
uniform float jaw_from = 0.55;
uniform float mouth_a = -0.42;
uniform float mouth_b = -0.105;
// The side-to-side wave: how far the middle line swings (of its length, at `sway` 1), how that grows along it
// (a + b s + c s^2 + d s^3, s from the snout 0 to the tail 1), and the wave's length (body lengths).
uniform float reach = 0.05;
uniform vec4 reach_poly = vec4(0.05, -0.3, 0.6, 0.6);
uniform float wave = 0.9;
// The up-and-down wave (the serpent's humps): how high (metres, at `humps` 1), from where it starts (metres behind
// the tip) and over how far it grows, its length (body lengths), and how many times it passes in a beat.
uniform float hump_height = 0.0;
uniform float hump_from = 6.0;
uniform float hump_rise = 4.0;
uniform float hump_wave = 0.45;
// The neck held up (the serpent): the neck bends up about `rear_at` (metres behind the tip) over `rear_span`
// ahead of it by up to `rear_max` radians at `rear` 1; the head bends back down about `head_at` over `head_span`
// by `head_keep` of that, so that it looks ahead.
uniform float rear_at = 8.0;
uniform float rear_span = 5.0;
uniform float rear_max = 1.1;
uniform float head_at = 2.6;
uniform float head_span = 1.0;
uniform float head_keep = 0.9;
// An S in the neck (the serpent): between the head and the base of the neck it bends forward again about
// `neck_at` over `neck_span`, by `neck_keep` of the rise.
uniform float neck_at = 4.2;
uniform float neck_span = 1.4;
uniform float neck_keep = 0.0;
// The tail curled up and round (`coil`): about `coil_at` (metres behind the tip) over `coil_span` behind it, by up
// to `coil_max` radians.
uniform float coil_at = 27.0;
uniform float coil_span = 11.0;
uniform float coil_max = 3.0;
// How far a side fin's tip rises and falls in a beat, how far the trailing edges of the fins ripple, how far a rope's
// and a weed's free end swings (metres).
uniform float flap = 0.6;
uniform float trail = 0.25;
uniform float rope_sway = 1.0;
uniform float weed_sway = 0.3;
// The leviathan's armour bands (as tools/build_leviathan.py): from where, how long the first, how much shorter
// they grow, to where.
uniform float plate_from = 11.6;
uniform float plate_long = 2.6;
uniform float plate_grow = 0.3;
uniform float plate_to = 36.0;
// Where the right eye sits (the build script prints it: EYE_FRAME; the left eye is its mirror): its middle on the
// skin, the way out of the head, the way to the nose and the way up in its own plane, how fast the skin falls away
// from that plane round it, its radius; how much bigger the cartoon eye is; where the brow is (metres behind the
// tip, metres up).
uniform vec3 eye_centre = vec3(2.6, 1.2, -13.0);
uniform vec3 eye_out = vec3(1.0, 0.0, 0.0);
uniform vec3 eye_fwd = vec3(0.0, 0.0, -1.0);
uniform vec3 eye_up = vec3(0.0, 1.0, 0.0);
uniform float eye_sag = 0.08;
uniform float eye_radius = 0.36;
uniform float eye_grow = 2.0;
uniform vec2 eye_at_side = vec2(7.0, 1.2);

// ---- Driven (by the creature's node) ----
// How far through a beat (0..1, it wraps); how widely it beats; its mouth (0 shut, 1 wide open); how far its body
// is bent round behind the head (radians; more than 0 the tail comes round to +X); the humps and the neck held up.
uniform float phase = 0.0;
uniform float sway = 1.0;
uniform float gape = 0.0;
uniform float curl = 0.0;
uniform float humps = 1.0;
uniform float rear = 0.0;
// The tail curled up: 0 straight, 1 hooked up and round.
uniform float coil = 0.0;
// The cartoon eye (0 as in life, 1 the cartoon eye), where it looks (x +1 to the nose, y +1 up), its lids (0 open).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// ---- Colours (each creature's script sets its own) ----
uniform vec3 back : source_color = vec3(0.16, 0.25, 0.26);
uniform vec3 flank : source_color = vec3(0.3, 0.42, 0.42);
uniform vec3 belly : source_color = vec3(0.55, 0.6, 0.55);
uniform vec3 seam : source_color = vec3(0.06, 0.1, 0.1);
uniform vec3 moss : source_color = vec3(0.2, 0.3, 0.15);
uniform vec3 fin : source_color = vec3(0.28, 0.38, 0.38);
uniform vec3 fin_edge : source_color = vec3(0.6, 0.62, 0.55);
uniform vec3 weed : source_color = vec3(0.3, 0.36, 0.12);
uniform vec3 mouth : source_color = vec3(0.45, 0.16, 0.16);
uniform vec3 tooth : source_color = vec3(0.88, 0.84, 0.7);
uniform vec3 shell : source_color = vec3(0.72, 0.7, 0.62);
uniform vec3 wood : source_color = vec3(0.3, 0.2, 0.12);
uniform vec3 iron : source_color = vec3(0.22, 0.12, 0.07);
uniform vec3 rope : source_color = vec3(0.45, 0.36, 0.22);
// How strongly the plates' seams / the scales show (0 none).
uniform float pattern = 1.0;
// The eye: the white, the iris light and dark, the pupil's half size (x across, y up, of the eye's radius), how far
// the natural eye glows, the iris's size, and the lids: the upper and the lower lid's line (a + b x + c x^2, x +1 to
// the nose, in eye radii) and the width of the dark line along each.
uniform vec3 sclera : source_color = vec3(0.85, 0.86, 0.8);
uniform vec3 iris_light : source_color = vec3(0.78, 0.84, 0.82);
uniform vec3 iris_dark : source_color = vec3(0.42, 0.5, 0.5);
uniform vec2 pupil_size = vec2(0.16, 0.16);
uniform float iris_size = 0.62;
uniform float eye_glow = 0.25;
uniform vec3 lid_up_k = vec3(0.3, -0.2, -0.12);
uniform vec3 lid_down_k = vec3(-0.6, 0.06, 0.12);
uniform vec2 lid_line = vec2(0.16, 0.07);

const vec3 OUTLINE = vec3(0.02, 0.025, 0.025);

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float inside;
varying vec2 eye_at;

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

// The eye's dome grown about its own middle for the cartoon eye, its rim laid back on the skin.
void grow_eye(inout vec3 v, out vec2 at) {
	vec3 m = vec3(v.x >= 0.0 ? 1.0 : -1.0, 1.0, 1.0);
	vec3 d = v - eye_centre * m;
	vec2 pl = vec2(dot(d, eye_fwd * m), dot(d, eye_up * m));
	at = pl / eye_radius;
	if (cartoon_eyes <= 0.0) {
		return;
	}
	float g = mix(1.0, eye_grow, cartoon_eyes);
	float r2 = dot(pl, pl);
	float over = dot(d, eye_out * m) + eye_sag * r2;
	float h = over * g - eye_sag * r2 * g * g;
	v = eye_centre * m + (eye_fwd * m * pl.x + eye_up * m * pl.y) * g + eye_out * m * h;
}

float lid_up(float x) {
	return lid_up_k.x + lid_up_k.y * x + lid_up_k.z * x * x;
}

float lid_down(float x) {
	return lid_down_k.x + lid_down_k.y * x + lid_down_k.z * x * x;
}

// The cartoon eye's colour at `e` (eye_at); `lit` how much of it glows a little.
vec3 cartoon_eye(vec2 e, vec3 lid_colour, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 q = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * vec2(0.22, 0.14);
	float qi = length(q);
	vec3 c = sclera * (1.0 - 0.25 * smoothstep(0.5, 0.86, r));
	float rays = 0.5 + 0.5 * sin(atan(q.y, q.x) * 19.0);
	vec3 ir = mix(iris_light, iris_dark, smoothstep(iris_size * 0.25, iris_size, qi) * 0.8 + rays * 0.15);
	c = mix(c, ir, 1.0 - smoothstep(iris_size - aa, iris_size + aa, qi));
	float pu = (length(q / pupil_size) - 1.0) * min(pupil_size.x, pupil_size.y);
	c = mix(c, vec3(0.005), 1.0 - smoothstep(-aa * 0.3, aa * 0.3, pu));
	float glint = max(1.0 - smoothstep(0.1 - aa, 0.1 + aa, length(e - vec2(0.24, 0.22))),
		1.0 - smoothstep(0.04 - aa, 0.04 + aa, length(e - vec2(-0.2, -0.2))));
	c = mix(c, vec3(1.0), glint);
	lit = mix(0.45, 1.0, glint);
	c = mix(c, OUTLINE, smoothstep(0.84 - aa, 0.86 + aa, r));
	float b = clamp(blink, 0.0, 1.0);
	float meet = mix(lid_down(e.x), lid_up(e.x), 0.55);
	float up = mix(lid_up(e.x), meet, b);
	float down = mix(lid_down(e.x), meet, b);
	float over_up = e.y - up;
	float over_down = down - e.y;
	float lid = max(smoothstep(-aa, aa, over_up), smoothstep(-aa, aa, over_down));
	c = mix(c, lid_colour, lid);
	lit *= 1.0 - lid;
	float line = max(smoothstep(-aa, aa, over_up) * (1.0 - smoothstep(lid_line.x - aa, lid_line.x + aa, over_up)),
		smoothstep(-aa, aa, over_down) * (1.0 - smoothstep(lid_line.y - aa, lid_line.y + aa, over_down)));
	c = mix(c, OUTLINE, line * (1.0 - smoothstep(0.92, 1.0, r)));
	return c;
}

// How far the middle line is moved (to the side, up) `xm` metres behind the tip.
vec2 swim_at(float xm) {
	float s = xm / body_length;
	float env = max(reach_poly.x + reach_poly.y * s + reach_poly.z * s * s + reach_poly.w * s * s * s, 0.0);
	float side = sway * body_length * reach * env * sin(TAU * (phase - s / wave));
	float up = 0.0;
	if (hump_height > 0.0) {
		float e = smoothstep(hump_from, hump_from + hump_rise, xm) * (1.0 - 0.3 * s);
		up = humps * hump_height * e * sin(TAU * (phase - s / hump_wave));
	}
	return vec2(side, up);
}

// The part ahead of `at` (metres behind the tip) bent up round an arc over `span` ahead of it, by `angle` radians
// (more than 0, the front rises); straight beyond the arc.
void bend_up(inout vec3 v, inout vec3 n, float at, float span, float angle) {
	float half_len = body_length * 0.5;
	float d = (at - half_len) - v.z;
	if (d <= 0.0 || abs(angle) < 0.0005) {
		return;
	}
	float r = span / angle;
	float a = angle * min(d, span) / span;
	float ca = cos(a);
	float sa = sin(a);
	float yc = r * (1.0 - ca);
	float zc = (at - half_len) - r * sa;
	float beyond = max(d - span, 0.0);
	yc += beyond * sa;
	zc -= beyond * ca;
	v = vec3(v.x, yc + v.y * ca, zc + v.y * sa);
	n = vec3(n.x, n.y * ca - n.z * sa, n.y * sa + n.z * ca);
}

// The tail behind `coil_at` curled up and round over an arc (see `coil`); straight beyond the arc.
void coil_up(inout vec3 v, inout vec3 n) {
	float angle = coil * coil_max;
	float at = coil_at - body_length * 0.5;
	float d = v.z - at;
	if (d <= 0.0 || angle < 0.0005) {
		return;
	}
	float r = coil_span / angle;
	float a = angle * min(d, coil_span) / coil_span;
	float ca = cos(a);
	float sa = sin(a);
	float yc = r * (1.0 - ca);
	float zc = at + r * sa;
	float beyond = max(d - coil_span, 0.0);
	yc += beyond * sa;
	zc += beyond * ca;
	v = vec3(v.x, yc + v.y * ca, zc - v.y * sa);
	n = vec3(n.x, n.y * ca + n.z * sa, -n.y * sa + n.z * ca);
}

// The body behind the head laid round an arc to one side (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.3 * body_length;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.7 * body_length);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// Turns `v` and `n` by `a` about the hinge of the jaw (more than 0: the front goes down).
void about_hinge(inout vec3 v, inout vec3 n, float a) {
	vec2 hinge = vec2(hinge_y, corner - body_length * 0.5);
	vec2 d = v.yz - hinge;
	float c = cos(a);
	float sn = sin(a);
	v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
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
	float half_len = body_length * 0.5;
	eye_at = vec2(0.0);
	if (p == 7) {
		vec2 at;
		grow_eye(v, at);
		eye_at = at;
	}
	// What hangs off it swings: a rope's or a weed's free end, in a wave running down it.
	if (p == 10 || p == 5) {
		float u = UV.x;
		float amp = (p == 10 ? rope_sway : weed_sway) * u * u;
		float w = TAU * (phase - 0.8 * u) + rest.z * 0.15;
		v.x += amp * sin(w);
		v.y += amp * 0.35 * sin(w + 1.3);
	}
	// A side fin's tip rises and falls; every fin's trailing edge ripples.
	if (p == 6) {
		v.y += flap * UV.x * UV.x * sin(TAU * phase + 0.6);
		v.y += trail * UV.x * UV.y * sin(TAU * (phase - 0.5 * UV.y));
	} else if (p == 4) {
		v.x += trail * UV.x * UV.y * sin(TAU * (phase - 0.5 * UV.y) + rest.z * 0.2);
	}
	float open = clamp(gape, 0.0, 1.0);
	if (p == 1 || p == 3) {
		// The lower jaw (and its teeth) swings down about the corner of the mouth; behind the corner, inside the
		// body, it stays.
		about_hinge(v, n, gape_max * open * smoothstep(corner + 0.04 * hinge_spread, corner - hinge_spread, v.z + half_len));
	} else if ((p == 0 || p == 2 || p == 7 || p == 8 || p == 5 || p == 11) && open > 0.0) {
		// The skull (the upper head, its teeth, eyes and what grows on it) lifts about the same hinge; the throat
		// under the hinge and the neck behind it stay.
		float w = smoothstep(corner + 2.0 * hinge_spread, corner - 0.2 * hinge_spread, v.z + half_len)
			* smoothstep(hinge_y - 0.1 * hinge_spread, hinge_y + 0.05 * hinge_spread, v.y);
		about_hinge(v, n, -lift_max * open * w);
	}
	// (where along it this point belongs: before the neck is raised)
	float xm = v.z + half_len;
	// The neck held up and the head looking ahead (the serpent).
	if (rear > 0.0) {
		bend_up(v, n, head_at, head_span, -rear * rear_max * head_keep);
		bend_up(v, n, neck_at, neck_span, -rear * rear_max * neck_keep);
		bend_up(v, n, rear_at, rear_span, rear * rear_max);
	}
	// The swim: the middle line moved by the waves, each section kept square to it; behind the tail fin's hinge,
	// one stiff plate.
	float zc = min(xm, joint);
	float hs = 0.015 * body_length;
	vec2 c0 = swim_at(zc);
	vec2 sl = (swim_at(zc + hs) - swim_at(zc - hs)) / (2.0 * hs);
	vec3 t = normalize(vec3(sl.x, sl.y, 1.0));
	vec3 r = normalize(cross(vec3(0.0, 1.0, 0.0), t));
	vec3 u = cross(t, r);
	vec3 o = vec3(v.x, v.y, v.z - (zc - half_len));
	v = vec3(c0.x, c0.y, zc - half_len) + r * o.x + u * o.y + t * o.z;
	n = r * n.x + u * n.y + t * n.z;
	coil_up(v, n);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

float mouth_y(float xm) {
	return mouth_a + mouth_b * xm;
}

float plate_phase(float xm) {
	float d = (xm - plate_from) / plate_long;
	return d * (1.0 + plate_grow * d / 10.0);
}

// The leviathan's hide at a place: `xm` behind the tip, `h` how high on its side (0..1). Its armour is modelled
// (the scutes, part 11, painted by `scute_colour`); what shows of the skin between them is the dark of the grooves.
vec3 hide_base(float xm, float h, float side) {
	float cloud = noise2(vec2(xm * 0.4, h * 3.0) + side * 5.0);
	vec3 c = mix(belly, flank, smoothstep(0.16, 0.34, h + (cloud - 0.5) * 0.1));
	return mix(c, back, smoothstep(0.58, 0.9, h + (cloud - 0.5) * 0.12));
}

// Short pale scars: a few strokes scattered over it, each a few metres long.
float scars(vec2 p) {
	vec2 cell = floor(p / 2.4);
	vec2 f = p / 2.4 - cell;
	float k = hash2(cell + 17.0);
	if (k < 0.72) {
		return 0.0;
	}
	float a = k * 13.0;
	vec2 dir = vec2(cos(a), sin(a));
	vec2 q = f - 0.5;
	float along = dot(q, dir);
	float across = abs(dot(q, vec2(-dir.y, dir.x)));
	return (1.0 - smoothstep(0.012, 0.03, across)) * (1.0 - smoothstep(0.25, 0.4, abs(along)));
}

vec3 leviathan_skin(float xm, float h, float side, out float rough) {
	float grain = noise2(vec2(xm * 9.0, h * 30.0 + side * 7.0));
	vec3 c = hide_base(xm, h, side);
	rough = 0.65;
	float pat = clamp(pattern, 0.0, 1.0);
	// Between the scutes of the trunk: the dark of the grooves.
	float under = smoothstep(0.26, 0.4, h) * smoothstep(corner + 0.5, corner + 1.5, xm);
	c = mix(c, mix(c, seam, 0.55), under * pat);
	// The belly: long pale scutes across it, darker grooves between.
	float on_belly = 1.0 - smoothstep(0.16, 0.26, h);
	float groove = 1.0 - smoothstep(0.0, 0.1, abs(fract(xm / 1.25 + 0.15 * sin(h * 9.0)) - 0.5) * 2.0 - 0.08);
	c = mix(c, mix(c, seam, 0.5), on_belly * groove * pat * step(corner * 0.4, xm));
	// Moss and stains on the back and upper flanks; pale old scars.
	float m = noise2(vec2(xm * 0.7, h * 5.0) + side * 3.0) * 0.7 + noise2(vec2(xm * 2.3, h * 14.0)) * 0.3;
	c = mix(c, moss, smoothstep(0.55, 0.75, m) * smoothstep(0.55, 0.85, h) * 0.6);
	c = mix(c, belly * 1.05, scars(vec2(xm, h * 9.0 + side * 30.0)) * 0.6 * (1.0 - on_belly));
	c *= 0.9 + 0.15 * grain;
	return c;
}

// A scute (part 11): its colour from the hide's at its place, each a little different (`tint`), its rim worn pale
// and chipped, dark cracks across it, moss on the high ones, the odd pale scar; `rim` 0 at its crown to 1 at its rim.
vec3 scute_colour(float xm, float h, float side, float rim, float tint, vec3 at, out float rough) {
	vec3 c = hide_base(xm, h, side) * (0.88 + 0.26 * tint);
	rough = 0.7;
	float worn = smoothstep(0.7, 1.0, rim) * (0.6 + 0.4 * noise2(at.xz * 3.0 + at.y));
	c = mix(c, mix(c, belly, 0.55), worn * 0.7);
	float crack = 1.0 - smoothstep(0.0, 0.05, abs(noise2(at.xz * 1.6 + at.yx * 1.3 + tint * 9.0) - 0.5));
	c = mix(c, seam, crack * 0.55 * smoothstep(0.1, 0.5, rim));
	float m = noise2(at.xz * 0.9 + tint * 7.0);
	c = mix(c, moss, smoothstep(0.5, 0.75, m) * smoothstep(0.6, 0.85, h) * 0.6);
	c = mix(c, belly * 1.08, scars(vec2(xm * 1.3, h * 11.0 + tint * 40.0)) * 0.7);
	// (shaded darker under its lifted back edge)
	c *= 0.85 + 0.2 * (1.0 - rim);
	return c;
}

// The sea serpent's scaled hide.
vec3 serpent_skin(float xm, float h, float side, out float rough) {
	float cloud = noise2(vec2(xm * 0.8, h * 3.0) + side * 5.0);
	vec3 c = mix(belly, flank, smoothstep(0.24, 0.36, h + (cloud - 0.5) * 0.06));
	c = mix(c, back, smoothstep(0.62, 0.92, h + (cloud - 0.5) * 0.12));
	rough = 0.5;
	// The belly: pale plates across it.
	float on_belly = 1.0 - smoothstep(0.22, 0.28, h);
	float pl = abs(fract(xm / 0.34) - 0.5) * 2.0;
	float groove = 1.0 - smoothstep(0.75, 0.95, pl);
	vec3 belly_c = mix(c * 0.78, c * 1.04, groove);
	// Elsewhere: overlapping diamond scales, each with a darker edge, smaller on the head.
	float sz = xm < 2.8 ? 0.09 : 0.2;
	vec2 q = vec2(xm / sz, h * 5.0 / sz * 0.18);
	vec2 a = vec2(q.x + q.y, q.x - q.y);
	vec2 f = abs(fract(a) - 0.5);
	float e = max(f.x, f.y);
	float scale = smoothstep(0.5, 0.42, e);
	vec3 scaled = c * mix(0.78, 1.05, scale) * (0.92 + 0.12 * hash2(floor(a) + side * 7.0));
	c = mix(c, mix(scaled, belly_c, on_belly), clamp(pattern, 0.0, 1.0));
	// A darker line of blotches along the back.
	float blot = smoothstep(0.55, 0.7, noise2(vec2(xm * 1.1, side * 3.0))) * smoothstep(0.75, 0.9, h);
	c = mix(c, back * 0.55, blot * 0.6);
	return c;
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

