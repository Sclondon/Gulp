shader_type spatial;
// The oysters (oyster.gd): one Pacific oyster, or a clump of five grown together. Their colours and their
// opening, in one shader; Oyster sets every setting below for the model it shows.
//
// What each point is comes from the model (tools/build_oyster.py): UV2.y the part (0 the shell's outside, 1 its
// inside, 2 its lip, 3 the soft body, 4 the pearl); UV2.x which oyster of the clump it belongs to and which way it
// swings, 2 x (its number) + 1 for the upper valve. UV on the shell: x from the hinge (0) to the edge (1), y round
// it; on the body: x from its middle (0) to its edge (1).
//
// The models are built shut; `open` swings each upper valve up about its hinge (`hinge_at[i]`, `hinge_axis[i]`)
// by `upper_turn` radians at 1 (in a clump each by its own share, `opens[i]`). The body breathes a little on
// `phase`. Nothing here needs more than GL Compatibility has.
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


// How far open (0 shut, 1 as far as it opens: a little).
uniform float open : hint_range(0.0, 1.0) = 0.0;
// 1 shows the pearl lying on the body (seen when it is open), 0 hides it.
uniform float pearl : hint_range(0.0, 1.0) = 0.0;
// How far through a beat (0..1) and how strongly it moves (the body's slow breathing).
uniform float phase = 0.0;
uniform float sway = 1.0;
// Each oyster's hinge: a point on it and the way it runs; how far its upper valve turns at `open` 1 (radians),
// and each oyster's share of that (so that the five of a clump do not open alike).
uniform vec3 hinge_at[5];
uniform vec3 hinge_axis[5];
uniform float opens[5];
uniform float upper_turn = 0.16;
// Where the pearl's middle is (it is drawn shrunk to that point when hidden).
uniform vec3 pearl_at = vec3(0.0);
// How big the oyster is (metres): for the scale of its markings.
uniform float size = 0.16;

// The colours: the rough outside (grey, with brown and violet in its layers), the lip, the mother-of-pearl
// inside and its dark violet muscle scar, the body and its dark mantle edge, the pearl.
uniform vec3 shell : source_color = vec3(0.58, 0.56, 0.52);
uniform vec3 shell_dark : source_color = vec3(0.32, 0.27, 0.26);
uniform vec3 shell_tint : source_color = vec3(0.45, 0.36, 0.42);
uniform vec3 lip : source_color = vec3(0.3, 0.24, 0.3);
uniform vec3 nacre : source_color = vec3(0.9, 0.9, 0.88);
uniform vec3 scar : source_color = vec3(0.35, 0.2, 0.38);
uniform vec3 flesh : source_color = vec3(0.82, 0.76, 0.62);
uniform vec3 mantle_edge : source_color = vec3(0.12, 0.1, 0.1);
uniform vec3 pearl_colour : source_color = vec3(0.96, 0.93, 0.9);
// How strong the mother-of-pearl's colours are.
uniform float pearly = 0.75;

varying vec3 rest;
varying float part;

void turn_about(inout vec3 p, inout vec3 n, vec3 at, vec3 axis, float a) {
	float c = cos(a);
	float s = sin(a);
	vec3 d = p - at;
	p = at + d * c + cross(axis, d) * s + axis * dot(axis, d) * (1.0 - c);
	n = n * c + cross(axis, n) * s + axis * dot(axis, n) * (1.0 - c);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	int which = int(floor(UV2.x * 0.5 + 0.01));
	float upper = mod(floor(UV2.x + 0.01), 2.0);
	if (p == 4) {
		v = mix(pearl_at, v, step(0.5, pearl));
	} else if (p == 3) {
		// the body swells and settles slowly as it breathes
		v.y += sway * 0.0006 * (size / 0.16) * sin(TAU * phase + UV.y * 3.0) * (1.0 - UV.x) * open;
	}
	if (upper > 0.5) {
		turn_about(v, n, hinge_at[which], hinge_axis[which], open * opens[which] * upper_turn);
	}
	VERTEX = v;
	NORMAL = n;
}

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

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

