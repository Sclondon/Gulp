shader_type spatial;
// The carp (carp.gd), the common carp and its koi: it swims by a wave down its body, its mouth opens
// and pushes out into a tube, its fins scull; and every marking is drawn here, for each type, from
// the species (the component's README says what was used): no texture files. What each point is
// comes from the model (tools/build_carp.py): COLOR.r the part, as a tenth (0 body, 1 lower jaw and
// its lip, 2 eye, 3 upper lip, 4 dorsal, 5 barbel, 6 tail, 7 anal, 8 pelvic, 9 pectoral, 10 the throat
// and gills: COLOR.g 0 the throat's wall, 0.5 a gill arch, whose UV.x is along it and UV.y from its
// rakers' edge (0) to the wall (1), UV2.x which arch, - on the left). On the
// body UV.x is how far along the fish (0 snout to 1 tail tip), UV.y how high (0 belly line to 1 back
// line), UV2.x how far round the skin from the back line (metres, + right, - left), UV2.y the whole
// way from back line to belly line; COLOR.g the gill cover's edge, COLOR.b the inside of the mouth.
// On a barbel UV.x is along it (0 root to 1 tip) and UV2 where its root is (along, up, in body
// lengths). On a fin UV.x is along its rays (0 root to 1 edge), UV.y across it counted in rays; UV2
// and COLOR.b the way its flat side faces. Nothing here needs more than GL Compatibility has.
//
// Everything that moves runs on `phase` (0..1 through one beat, set by Carp): the tail beats and the
// fins' sculls each go a whole number of times a beat, so a picture of it comes round again exactly.
//
// The type (`kind`): 0 the common carp (bronze-gold, each big scale edged dark); 1 kohaku (white with
// red patches); 2 sanke (white, red patches and small black marks); 3 showa (black with red and white
// patches); 4 ogon (one metallic colour, gold or platinum). Where a koi's patches fall is from
// `pattern_seed`: each seed another fish.
render_mode cull_back, depth_draw_opaque, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// As the model is built (tools/build_carp.py prints the SHAPE line): body lengths are of this many
// metres; the lower jaw hinges at the corner of the mouth (how far along, how high, in body lengths);
// the gill cover's rear edge reaches back this far.
const float LENGTH = 0.7;
const float HINGE_S = 0.066;
const float HINGE_Y = -0.033;
const float GILL_S = 0.212;
// How many body lengths one wave of the swimming bend is.
const float WAVE = 0.95;
// The mouth wide open (`gape` 1): how far the lower jaw swings down (radians), and how far the lips
// and the front of the snout push forward and down (body lengths).
const float GAPE_TURN = 0.42;
const float PROTRUDE = 0.03;
const float DROP = 0.022;
// How far the floor of the mouth (the inside of the lower jaw near its hinge) sinks with the mouth wide open,
// so that the way into the throat is open (body lengths; THROAT_SINK in the build script).
const float THROAT_SINK = 0.018;
// And how far the roof of the mouth near the hinge vaults up into the head (THROAT_RAISE).
const float THROAT_RAISE = 0.02;

uniform float phase = 0.0;
uniform float tail_beats = 2.0;
uniform float sculls = 2.0;
// How hard it is swimming: how far its tail swings (1 is a tenth of its length each way).
uniform float sway = 0.6;
// The mouth: 0 shut, 1 wide open and pushed out into a tube.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to
// the tail (0 straight; more than 0 the tail comes round to +X). The head stays as it is.
uniform float curl = 0.0;
// How far the pectoral and pelvic fins scull.
uniform float scull = 1.0;

// The type and its pattern.
uniform float kind = 0.0;
uniform float pattern_seed = 0.0;
// Colours. The common carp's ramp (belly, side, back) and its head; a koi's white, red (hi), black
// (sumi); the metal of an ogon is `side` (and `back` a little darker).
uniform vec3 back : source_color = vec3(0.22, 0.2, 0.1);
uniform vec3 side : source_color = vec3(0.62, 0.48, 0.2);
uniform vec3 belly : source_color = vec3(0.86, 0.78, 0.52);
uniform vec3 head : source_color = vec3(0.56, 0.44, 0.2);
uniform vec3 head_top : source_color = vec3(0.24, 0.21, 0.1);
uniform vec3 lip_colour : source_color = vec3(0.7, 0.56, 0.4);
uniform vec3 mouth : source_color = vec3(0.35, 0.16, 0.14);
uniform vec3 scale_edge : source_color = vec3(0.12, 0.09, 0.04);
uniform vec3 white : source_color = vec3(0.93, 0.92, 0.88);
uniform vec3 hi : source_color = vec3(0.82, 0.16, 0.06);
uniform vec3 sumi : source_color = vec3(0.04, 0.04, 0.04);
uniform vec3 fin_upper : source_color = vec3(0.34, 0.3, 0.2);
uniform vec3 fin_lower : source_color = vec3(0.62, 0.36, 0.2);
uniform vec3 fin_pectoral : source_color = vec3(0.52, 0.4, 0.22);
uniform vec3 fin_dark : source_color = vec3(0.12, 0.1, 0.06);
uniform vec3 eye_gold : source_color = vec3(0.86, 0.66, 0.22);
uniform vec3 sheen_colour : source_color = vec3(1.0, 0.9, 0.62);
// How dark each scale's edge is (less than 0 lightens it: an ogon's bright-edged scales); how big the
// scales are (metres, at scale 1); how much of a koi is red, black, white (0..1); black stripes in a
// koi's fins (sanke); black at the roots of the pectoral fins (showa); the sheen; how metallic.
uniform float scale_dark = 0.55;
uniform float scale_size = 0.0135;
uniform float hi_amount = 0.5;
uniform float sumi_amount = 0.5;
uniform float white_amount = 0.5;
uniform float fin_stripes = 0.0;
uniform float motoguro = 0.0;
uniform float sheen = 0.35;
uniform float metal = 0.0;
// The cartoon eye (the user, 2026-11-18: "the eyes for most of them should be more cartoony and
// personalized"): 0 the eye as the species has it, 1 the cartoon eye (bigger, a pale ring round a gold
// iris, a big round pupil, a highlight that stays towards the light, a dark outline, and a carp's heavy,
// placid upper lid). `eye_look` slides the iris and pupil (x towards the snout, y up; -1..1); `blink` 0
// open to 1 shut (the eye squashed flat and the lid drawn down over it).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The right eye's middle (metres) and the way it looks out (the build prints the EYE line); the cartoon
// eye's width, how far it bulges, how far the iris slides, its size, the pupil's, and the lid's line.
const vec3 EYE_MIDDLE = vec3(0.02285, 0.01832, -0.28474);
const vec3 EYE_OUT = vec3(0.9280, 0.2197, -0.3008);
const float EYE_GROW = 1.5;
const float EYE_BULGE = 1.15;
const float EYE_PUSH = 0.0025;
const float IRIS_TRAVEL = 0.22;
const float IRIS_R = 0.68;
const float PUPIL_R = 0.38;
const float LID_Y = 0.3;
const float LID_SLANT = 0.1;

varying vec3 rest;
varying float part;
varying vec2 extra;


vec4 hash4(vec2 p) {
	vec4 q = fract(p.xyxy * vec4(0.1031, 0.1030, 0.0973, 0.1099));
	q += dot(q, q.wzxy + 33.33);
	return fract((q.xxyz + q.yzzw) * q.zywx);
}


// Soft patches, 0..1, a patch to each 1 of `p`.
float cloud(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash4(i).x, hash4(i + vec2(1.0, 0.0)).x, f.x), mix(hash4(i + vec2(0.0, 1.0)).x, hash4(i + vec2(1.0, 1.0)).x, f.x), f.y);
}


// How far the lips and the front of the snout are pushed out at a place (s along, y up, in body
// lengths) when the mouth opens: the lower front of the head, none of its top.
float pushed(float s, float y) {
	return smoothstep(0.06, 0.0, s) * smoothstep(-0.004, -0.024, y);
}


void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.24 * LENGTH;
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

	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float s = v.z / LENGTH + 0.5;
	float y = v.y / LENGTH;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float tail = phase * TAU * tail_beats;
	float open = clamp(gape, 0.0, 1.0);
	if (part == 2.0 && (cartoon_eyes > 0.0 || blink > 0.0)) {
		// The eye: wider and a little prouder as a cartoon eye, squashed flat to blink.
		vec3 mid = EYE_MIDDLE;
		vec3 o = EYE_OUT;
		if (v.x < 0.0) {
			mid.x = -mid.x;
			o.x = -o.x;
		}
		vec3 up = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
		float wide = mix(1.0, EYE_GROW, cartoon_eyes);
		float proud = mix(1.0, EYE_BULGE, cartoon_eyes);
		float shut = 1.0 - 0.8 * clamp(blink, 0.0, 1.0);
		vec3 d = v - mid;
		float d_out = dot(d, o);
		vec3 flat_d = d - o * d_out;
		float d_up = dot(flat_d, up);
		v = mid + o * (d_out * proud + EYE_PUSH * cartoon_eyes) + (flat_d - up * d_up) * wide + up * (d_up * wide * shut);
		float n_out = dot(n, o);
		vec3 n_flat = n - o * n_out;
		float n_up = dot(n_flat, up);
		n = o * (n_out / proud) + (n_flat - up * n_up) / wide + up * (n_up / (wide * shut));
	}
	// The mouth: the lower jaw swings down about its hinge at the corner of the mouth (its throat
	// behind stays), then the lips and the front of the snout push forward and down into a tube.
	float push = 0.0;
	if (part == 1.0) {
		// (near the hinge only, where the jaw is deep enough; floor_sink in the build script)
		v.y -= open * COLOR.b * THROAT_SINK * LENGTH * smoothstep(0.0, HINGE_S, s);
		float a = open * GAPE_TURN * smoothstep(HINGE_S + 0.025, HINGE_S - 0.02, s);
		vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5) * LENGTH;
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
		push = smoothstep(0.095, 0.02, s);
	} else if (part == 0.0 || part == 3.0) {
		push = part == 3.0 ? smoothstep(0.085, 0.0, s) : pushed(s, y);
		if (part == 0.0) {
			// (the roof of the mouth near the hinge vaults up, opening the way into the throat)
			v.y += open * COLOR.b * THROAT_RAISE * LENGTH * smoothstep(0.03, 0.062, s);
		}
	} else if (part == 5.0) {
		// a barbel goes with the lip it grows from, and trails a little as the fish swims
		push = smoothstep(0.085, 0.0, UV2.x);
		v.x += LENGTH * 0.004 * sway * UV.x * UV.x * sin(tail - UV.x * 2.0);
	}
	v.z -= open * push * PROTRUDE * LENGTH;
	v.y -= open * push * DROP * LENGTH;
	if (part == 10.0 && COLOR.g > 0.25) {
		// The gill arches spread a little as the mouth opens.
		v.z += (abs(UV2.x) - 1.5) * 0.005 * LENGTH * open;
	}
	if (part >= 4.0 && part != 5.0 && part < 9.5) {
		// A fin waves the way its flat side faces, more towards its edge.
		vec3 flat_way = normalize(vec3(UV2.x, UV2.y, COLOR.b * 2.0 - 1.0));
		float r = UV.x;
		float turn = phase * TAU * sculls;
		float w = tail - TAU * clamp(s, 0.0, 1.05) / WAVE;
		if (part == 9.0) {
			// the pectorals scull, one a little after the other
			float a = turn + (side_is > 0.0 ? 0.0 : 1.3);
			v += flat_way * LENGTH * 0.03 * scull * (r * (sin(a) + 0.35) + 0.7 * r * r * sin(a - 1.2));
		} else if (part == 8.0) {
			float a = turn + (side_is > 0.0 ? 2.2 : 3.3);
			v += flat_way * LENGTH * 0.012 * scull * r * r * sin(a - UV.y * 0.25);
		} else if (part == 6.0) {
			// (the tail's edge lags behind the bend that carries it)
			v.x += LENGTH * 0.024 * sway * r * r * sin(w - 1.1);
		} else {
			v.x += LENGTH * 0.014 * sway * r * r * sin(w - 1.0 - UV.y * 0.2);
		}
	}
	// The swimming bend: a wave from head to tail, the head nearly still and the tail swinging
	// widest; each place carried sideways and turned to lie along the bent body.
	float sb = clamp(v.z / LENGTH + 0.5, 0.0, 1.05);
	float reach = 0.012 - 0.05 * sb + 0.14 * sb * sb;
	float reach_slope = -0.05 + 0.28 * sb;
	float w = tail - TAU * sb / WAVE;
	float off = LENGTH * sway * reach * sin(w);
	float slope = sway * (reach_slope * sin(w) - reach * TAU / WAVE * cos(w));
	vec3 along = normalize(vec3(slope, 0.0, 1.0));
	vec3 across = vec3(along.z, 0.0, -along.x);
	v = vec3(off, v.y, v.z) + across * v.x;
	n = across * n.x + vec3(0.0, n.y, 0.0) + along * n.z;
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = normalize(n);
}


// The big scales: [how near the edge of the scale on top here (0 its edge, 1 its middle), a number of
// its own (0..1)]. Each scale is a disc whose front lies under the scale ahead of it; where discs
// overlap, the one furthest forward is on top. `g` in scales: x along (towards the tail), y round.
vec2 scale_at(vec2 g) {
	float best_x = 1e6;
	vec2 found = vec2(1.0, 0.0);
	float row0 = floor(g.y);
	for (int j = -1; j <= 1; j++) {
		float row = row0 + float(j);
		float shift = 0.5 * mod(row, 2.0);
		float col0 = floor(g.x - shift);
		for (int i = -1; i <= 1; i++) {
			vec2 c = vec2(col0 + float(i) + shift + 0.5, row + 0.5);
			vec2 d = (g - c) * vec2(1.0, 1.1);
			float r = length(d);
			if (r < 0.78 && c.x < best_x) {
				best_x = c.x;
				found = vec2(r / 0.78, hash4(c * 1.37 + 0.5).y);
			}
		}
	}
	return vec2(1.0 - found.x, found.y);
}


// The cartoon eye's colour at `e` on its face (x towards the snout, y up, 1 at its rim), `nv` the
// way it faces (view space): a pale ring round a gold iris, a big round pupil, a highlight that stays
// towards the light (where the dome faces it), a dark outline.
vec3 cartoon_eye(vec2 e, vec3 nv) {
	float r = length(e);
	vec2 q = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * IRIS_TRAVEL;
	float ri = length(q);
	vec3 c = vec3(0.96, 0.94, 0.86);
	vec3 iris = mix(eye_gold * 1.25, eye_gold * 0.6, smoothstep(0.1, IRIS_R, ri));
	// (rays in the iris, and a darker ring at its edge)
	iris *= 0.9 + 0.1 * sin(atan(q.y, q.x) * 14.0);
	iris = mix(iris, eye_gold * 0.3, smoothstep(IRIS_R - 0.14, IRIS_R - 0.02, ri));
	c = mix(c, iris, 1.0 - smoothstep(IRIS_R - 0.02, IRIS_R + 0.02, ri));
	c = mix(c, vec3(0.015, 0.012, 0.01), 1.0 - smoothstep(PUPIL_R - 0.02, PUPIL_R + 0.02, ri));
	// the highlight, and a small second one below it
	vec3 light = normalize(vec3(-0.3, 0.35, 0.9));
	float spot = smoothstep(0.955, 0.965, dot(nv, light));
	spot = max(spot, smoothstep(0.996, 0.998, dot(nv, normalize(vec3(0.15, -0.12, 0.98)))));
	c = mix(c, vec3(1.0), spot);
	return mix(c, vec3(0.03, 0.025, 0.02), smoothstep(0.84, 0.9, r));
}


// The lid over an eye (`c` its colour, at `e` on its face): the cartoon eye's heavy upper lid with a dark
// line along its edge (none on the eye as the species has it), drawn down over it to blink.
vec3 eye_lid(vec2 e, vec3 c, vec3 lid_c) {
	float line = mix(mix(1.1, LID_Y + LID_SLANT * e.x, cartoon_eyes), -1.1, clamp(blink, 0.0, 1.0));
	float edge = (1.0 - smoothstep(0.0, 0.1, line - e.y)) * smoothstep(-1.0, -0.6, line) * max(cartoon_eyes, step(0.001, blink));
	c = mix(c, vec3(0.03, 0.025, 0.02), edge);
	return mix(c, lid_c, smoothstep(line - 0.01, line + 0.01, e.y));
}


// The common carp's colour at a place on its body: `s` along, `h` up.
vec3 ramp(float s, float h) {
	vec3 c = mix(belly, side, smoothstep(0.08, 0.4, h));
	return mix(c, back, smoothstep(0.62, 0.95, h));
}


void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

