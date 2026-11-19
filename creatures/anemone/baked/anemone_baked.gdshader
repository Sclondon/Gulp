shader_type spatial;
// The sea anemones (anemone.gd): their tentacles sway in the water, `retract` pulls them in and squats the column
// down into a closed blob (the tube anemone instead sinks down into its tube), and every colour is drawn here: no
// texture files. What each point is comes from the model (tools/build_anemone.py):
// - COLOR.r the part, as a tenth: 0 the body (foot, column, the plumose's crown underside), 1 the oral disc (the
//   plumose's crown top), 2 a tentacle, 3 the tube anemone's tube.
// - On the body and the disc UV.x `u`, how far along the body's profile (0 the middle of the foot, 1 its rim, 2 the
//   top of the column at the disc's margin, 3 the middle of the disc), UV.y how far round (0..1).
// - On a tentacle UV.x how far along it (0 root, 1 tip), UV.y its root's height, UV2 its root's x and z, COLOR.g a
//   number of its own, COLOR.b how far out on the disc its root is (0 the middle, 1 the margin), COLOR.a 1 for the
//   tube anemone's long outer tentacles (0 the short inner ones).
// - On the tube UV.x how far up it (0 its foot, 1 its lip), UV.y how far round.
// Nothing here needs more than GL Compatibility has. One opaque draw, back faces culled.
//
// The sway runs on the project's global shader uniform `water_clock` (seconds; declared in Project Settings >
// Shader Globals) and on where each tentacle's root is in the world, so neighbouring anemones do not sway in step.
// It has no clock of its own: hold water_clock still and it stands still.
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


global uniform float water_clock;

// Which anemone (set by Anemone with its model): 0 the giant green, 1 the tube anemone, 2 the plumose.
uniform int kind = 0;
// How far the tentacles sway (1 as each kind is set), and how fast (1 about a sway every six seconds).
uniform float sway = 1.0;
uniform float sway_speed = 1.0;
// A steady lean of every tentacle's tip with the current (metres at the tip, in the anemone's own x and z).
uniform vec2 current = vec2(0.0, 0.0);
// 0 open; 1 the tentacles pulled right in and the column squatted into a closed blob (the tube anemone: down
// into its tube). The tentacles go first, then the body.
uniform float retract : hint_range(0.0, 1.0) = 0.0;

// Set per kind by Anemone: how far a tentacle's tip sways at `sway` 1 (metres), how much of a wave runs down a
// tentacle (radians root to tip), how far the top of the column sways (metres, the plumose), how high the body
// stands; the closed blob's radius and height; how far the tube anemone sinks into its tube.
uniform float sway_reach = 0.004;
uniform float wave = 0.0;
uniform float column_sway = 0.0;
uniform float body_height = 0.1;
uniform vec2 blob = vec2(0.078, 0.042);
uniform float sink = 0.06;

// The colours. `colour` is the anemone's own (the giant green's and the tube anemone's tentacles; all of the
// plumose); the rest as each kind uses them.
uniform vec3 colour : source_color = vec3(0.25, 0.62, 0.38);
uniform vec3 tip_colour : source_color = vec3(0.55, 0.85, 0.7);
uniform vec3 disc_colour : source_color = vec3(0.3, 0.55, 0.32);
uniform vec3 column_colour : source_color = vec3(0.38, 0.42, 0.22);
uniform vec3 spot_colour : source_color = vec3(0.6, 0.58, 0.46);
uniform vec3 inner_colour : source_color = vec3(0.35, 0.18, 0.3);
uniform vec3 tube_colour : source_color = vec3(0.32, 0.27, 0.22);

// As the model is built: where the dome of the closed blob ends round its pucker (radians up from the ground).
const float PHI_END = 1.45;

varying float part;
varying float along;
varying float own;
varying vec3 rest;
varying float shut;

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

// Where a point of the body (`u` along the profile, `ang` round) is on the closed blob, and the way it faces there:
// the foot stays on the ground, the column becomes a low dome, the disc a pucker sunk into its top.
vec3 blob_at(float u, float ang, out vec3 nrm) {
	vec3 dir = vec3(cos(ang), 0.0, sin(ang));
	float rb = blob.x;
	float hb = blob.y;
	if (u <= 1.0) {
		nrm = vec3(0.0, -1.0, 0.0);
		return dir * (rb * u);
	}
	if (u <= 2.0) {
		float phi = (u - 1.0) * PHI_END;
		float c = cos(phi);
		float s = sin(phi);
		nrm = normalize(dir * (c * hb) + vec3(0.0, s * rb, 0.0));
		return dir * (rb * pow(c, 0.75)) + vec3(0.0, hb * s, 0.0);
	}
	float s = clamp(u - 2.0, 0.0, 1.0);
	float re = rb * pow(cos(PHI_END), 0.75);
	float ye = hb * sin(PHI_END);
	float d = hb * 0.25;
	nrm = normalize(-dir * d + vec3(0.0, re, 0.0));
	return dir * (re * (1.0 - s)) + vec3(0.0, ye - d * s, 0.0);
}

// Where a point of the body is when it is drawn in: on the blob, or (the tube anemone) sunk into its tube and
// drawn narrower.
vec3 drawn_in(vec3 p, float u, float ang, inout vec3 nrm) {
	if (kind == 1) {
		return vec3(p.x * 0.72, p.y - sink, p.z * 0.72);
	}
	return blob_at(u, ang, nrm);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = floor(COLOR.r * 10.0 + 0.5);
	along = UV.x;
	own = COLOR.g;
	rest = VERTEX;
	// (the tentacles go in first, then the body squats)
	float in_t = smoothstep(0.0, 0.65, retract);
	float in_b = smoothstep(0.25, 1.0, retract);
	shut = in_b;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (part > 1.5 && part < 2.5) {
		vec3 root = vec3(UV2.x, UV.y, UV2.y);
		vec3 root_w = (MODEL_MATRIX * vec4(root, 1.0)).xyz;
		// (two slow waves crossing, so that the tips trace loops; a wave running down the long ones; those at the
		// margin sway more)
		float k = water_clock * sway_speed * 1.05 + dot(root_w.xz, vec2(3.1, 2.3)) + own * 2.0 - wave * UV.x;
		float bend = UV.x * UV.x;
		vec3 push = vec3(sin(k), 0.0, cos(k * 0.83 + 1.7)) * (sway_reach * sway * (0.6 + 0.6 * COLOR.b));
		push.xz += current;
		v += bend * push;
		// (a tip pushed aside sinks a little, so that the tentacle keeps about its length)
		v.y -= bend * 0.4 * length(push.xz);
		// drawn in: shrunk towards its root, the root carried with the disc
		vec3 dummy = vec3(0.0, 1.0, 0.0);
		vec3 root_in = drawn_in(root, 3.0 - COLOR.b, atan(root.z, root.x), dummy);
		vec3 off = (v - root) * (1.0 - 0.97 * in_t);
		off.xz *= 1.0 - 0.5 * in_t;
		v = mix(root, root_in, in_b) + off;
	} else if (part < 1.5) {
		vec3 nb = n;
		vec3 to = drawn_in(VERTEX, UV.x, UV.y * TAU, nb);
		v = mix(VERTEX, to, in_b);
		n = normalize(mix(n, nb, in_b));
	}
	if (kind == 2 && part < 2.5) {
		// the plumose's tall column leans slowly to and fro, its crown with it
		vec3 at = MODEL_MATRIX[3].xyz;
		float kc = water_clock * sway_speed * 0.55 + dot(at.xz, vec2(1.3, 0.9));
		float h = clamp(v.y / body_height, 0.0, 1.2);
		v.xz += vec2(sin(kc), cos(kc * 0.77 + 0.6)) * (column_sway * sway * h * h);
	}
	VERTEX = v;
	NORMAL = n;
}

// The plumose's feathery crown: very many fine tentacles drawn as fine streaks running out over it, speckled.
// Close to, a carpet of small pale tips with shadow between them; far off (where the tips would shimmer) it
// fades to their average.
vec3 feathers(vec3 base, float u, float round_way) {
	vec2 g = vec2(round_way * 420.0, u * 70.0);
	g.x += 0.5 * mod(floor(g.y), 2.0);
	vec2 f = fract(g) - 0.5;
	float jitter = hash2(floor(g));
	float tip = 1.0 - smoothstep(0.15, 0.48, length(f + (jitter - 0.5) * 0.25));
	float far = smoothstep(0.25, 0.6, max(fwidth(g.x), fwidth(g.y)));
	tip = mix(tip, 0.45, far);
	float streak = noise2(vec2(round_way * 160.0, u * 9.0));
	vec3 c = base * mix(0.55, 1.0, tip) * (0.85 + 0.2 * streak);
	return mix(c, tip_colour, 0.45 * tip * tip);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

