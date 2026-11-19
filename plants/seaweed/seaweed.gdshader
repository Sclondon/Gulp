shader_type spatial;
render_mode cull_disabled, world_vertex_coords, vertex_lighting;
// Seaweed, drawn a plant at a time by SeaweedBed's MultiMeshes (the plants are
// models/seaweed_*.glb; tools/build_seaweed.py says what their UVs hold). One shader for all six
// kinds: each kind has its own material, with the settings below that SeaweedBed.LOOK gives it.
// All of its moving is here, from `water_clock`:
// - a plant rooted on the floor bends over as one arc (its length kept), leaning down-current and
//   swung to and fro by a slow surge that runs through the bed as a wave; each point bends with the
//   point of the plant's axis that carries it (UV2), so a sea palm's crown rides on its stalk;
// - blades flap a little, more towards their tips; a long strap (feather boa) has a wave running up it;
// - a floating kind (sargassum) does not bend: it bobs and rocks on the swell at its waterline.
// Blades are single sheets drawn from both sides (Godot turns the normal round for the back face);
// light shows through them. Nothing here needs more than GL Compatibility has.

// Seconds, set by the game (a global shader uniform: Project Settings > Shader Globals, or
// SeaweedBed adds and runs one if the project declares none).
global uniform float water_clock;

// Which way the water streams (world x, z) and how hard: 1 bends a plant over about 70 degrees.
uniform vec2 current = vec2(0.0);
// How far the surge swings them: 1 about 25 degrees either way at the top, 0 still.
uniform float sway = 1.0;
// Seconds for the surge to go there and back, and metres between its crests through the bed.
uniform float surge_period = 7.0;
uniform float surge_length = 26.0;
// How much every blade flaps on its own (times `flap`).
uniform float flutter = 1.0;

// Each kind's own (SeaweedBed sets them from LOOK):
// its height at scale 1 (metres; the plant's axis is that long);
uniform float model_tall = 0.5;
// how far it bends with the current and the surge (1 as above);
uniform float bendy = 1.0;
// how far its blades flap at their tips (metres at scale 1);
uniform float flap = 0.02;
// a wave running up the plant, sideways (0 none; 1 about a twelfth of its height at the top);
uniform float snake = 0.0;
// 1: it floats at the surface (bobs and rocks, no bending); how far it bobs (metres at scale 1);
uniform float floating = 0.0;
uniform float bob = 0.03;
// how much light shows through a blade; a darker (or, below 0, paler) line down a blade's middle.
uniform float translucency = 0.5;
uniform float midrib = 0.0;

uniform vec3 colour_foot : source_color = vec3(0.1, 0.3, 0.08);
uniform vec3 colour_tip : source_color = vec3(0.3, 0.6, 0.15);
uniform vec3 colour_stem : source_color = vec3(0.3, 0.25, 0.1);
uniform vec3 colour_float : source_color = vec3(0.5, 0.4, 0.12);
uniform vec3 colour_lit : source_color = vec3(0.5, 0.8, 0.3);

varying float v_own;
varying float v_plant;
varying float v_part;

void vertex() {
	vec3 foot = MODEL_MATRIX[3].xyz;
	float scale = max(length(MODEL_MATRIX[1].xyz), 0.001);
	float tall = model_tall * scale;
	float plant = INSTANCE_CUSTOM.x; // a number of the plant's own
	float part = floor(UV2.y * 3.0 + 0.001); // 0 a blade, 1 a stem, 2 a float
	float carrier = clamp((UV2.y - part / 3.0) / 0.3, 0.0, 1.0);
	float own = UV2.x;
	vec3 rel = VERTEX - foot;
	vec3 pos = VERTEX;
	vec3 n = NORMAL;
	// (a blade's flap: more towards its tip; stems and floats do not flap)
	float wob = sin(water_clock * 2.1 + own * 37.0 + UV.y * 2.5 + plant * 11.0) * flap * scale * flutter
			* UV.y * (part < 0.5 ? 1.0 : 0.0);

	if (floating > 0.5) {
		// Riding the swell: up and down, and tilted with its slope.
		float swell = water_clock * 0.8 + dot(foot.xz, vec2(0.31, 0.19));
		vec2 slope = vec2(cos(swell * 0.7 + plant * 6.0), sin(swell * 0.9 + plant * 3.0)) * 0.06 * sway;
		pos.y += sin(swell) * bob * scale * sway + dot(rel.xz, slope);
		// (and turning slowly a little this way and that)
		float turn = sin(water_clock * 0.23 + plant * TAU) * 0.15 * sway;
		vec2 r = vec2(rel.x * cos(turn) - rel.z * sin(turn), rel.x * sin(turn) + rel.z * cos(turn));
		pos.xz = foot.xz + r;
		n.xz = vec2(n.x * cos(turn) - n.z * sin(turn), n.x * sin(turn) + n.z * cos(turn));
		pos += n * wob;
	} else {
		vec2 axis = length(current) > 0.001 ? normalize(current) : vec2(1.0, 0.0);
		vec2 cross_axis = vec2(-axis.y, axis.x);
		float beat = water_clock * TAU / surge_period - dot(foot.xz, axis) * TAU / surge_length + plant * 0.5;
		// The bend at the top: the current's, the surge's, a little of the plant's own.
		vec2 bend = (current * 1.2
				+ axis * sway * 0.45 * sin(beat)
				+ cross_axis * sway * 0.1 * sin(beat * 0.63 + plant * TAU + dot(foot.xz, vec2(0.21, 0.13)))) * bendy;
		float angle = min(length(bend), 1.4);
		vec2 d = angle > 0.0001 ? bend / length(bend) : axis;
		// The carrying point on the axis moves along an arc of that angle (its length kept).
		float h = carrier * tall;
		float a = angle * carrier;
		float out_ = angle > 0.0001 ? tall * (1.0 - cos(a)) / angle : 0.0;
		float up = angle > 0.0001 ? tall * sin(a) / angle : h;
		vec2 side = vec2(-d.y, d.x);
		vec2 wave = side * sin(carrier * 6.0 - water_clock * 1.4 + plant * 6.0) * snake * 0.08 * tall * carrier;
		pos += vec3(d.x * out_ + wave.x, up - h, d.y * out_ + wave.y);
		// The normal turned as far as the plant is there (about the line across the bend).
		vec3 k = vec3(d.y, 0.0, -d.x);
		n = n * cos(a) + cross(k, n) * sin(a) + k * dot(k, n) * (1.0 - cos(a));
		pos += n * wob;
	}
	VERTEX = pos;
	NORMAL = normalize(n);
	v_own = own;
	v_plant = plant;
	v_part = part;
}

void fragment() {
	vec3 colour;
	float rough = 0.6;
	float spec = 0.25;
	if (v_part > 1.5) {
		// A float or bladder: a little glossy, a little lighter at its top.
		colour = colour_float * (0.85 + 0.3 * fract(v_own * 5.3 + v_plant));
		rough = 0.35;
		spec = 0.5;
	} else if (v_part > 0.5) {
		colour = colour_stem * mix(0.65, 1.0, smoothstep(0.0, 0.4, UV.y));
	} else {
		float tone = fract(v_own * 3.7 + v_plant * 1.3);
		colour = mix(colour_foot, colour_tip, smoothstep(0.05, 1.0, UV.y)) * (0.86 + 0.28 * tone);
		float across = abs(UV.x * 2.0 - 1.0);
		colour *= 1.0 - midrib * 0.35 * (1.0 - smoothstep(0.0, 0.2, across));
		// Faint lines along the blade.
		colour *= 0.95 + 0.05 * cos(across * 10.0 + v_own * 6.0);
	}
	ALBEDO = colour;
	ROUGHNESS = rough;
	SPECULAR = spec;
}

void light() {
	float facing = dot(NORMAL, LIGHT);
	float behind = max(-facing, 0.0) * translucency * (v_part < 0.5 ? 1.0 : 0.3);
	DIFFUSE_LIGHT += (max(facing, 0.0) + behind * 0.8 * colour_lit) * ATTENUATION * LIGHT_COLOR / PI;
}
