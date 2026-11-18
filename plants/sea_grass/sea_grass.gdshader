shader_type spatial;
render_mode cull_disabled, world_vertex_coords;
// Eelgrass, drawn a tuft at a time by SeaGrassBed's MultiMeshes (the tufts are
// models/sea_grass_*.glb; tools/build_sea_grass.py says what their UVs hold). All of its moving is
// here: every leaf bends over as one arc (its length kept), leaning down-current and swung to and
// fro by a slow surge that runs through the bed as a wave (from where the tuft stands and
// `water_clock`), a ripple running up each leaf, and up to four pushers laying it aside. The leaves
// are single sheets drawn from both sides (Godot turns the normal round for the back face);
// light shows through them. Nothing here needs more than GL Compatibility has.

// Seconds, set by the game (a global shader uniform: Project Settings > Shader Globals, or
// SeaGrassBed adds and runs one if the project declares none).
global uniform float water_clock;

// Which way the water streams (world x, z) and how hard: 1 bends a leaf's tip over about 80 degrees.
uniform vec2 current = vec2(0.0);
// How far the surge swings them: 1 about 30 degrees either way at the tip, 0 still.
uniform float sway = 1.0;
// Seconds for the surge to go there and back, and metres between its crests through the bed.
uniform float surge_period = 7.0;
uniform float surge_length = 26.0;
// How much each leaf ripples and flutters on its own.
uniform float flutter = 1.0;
// Up to four things that lay the grass aside: world x, y, z and a radius in metres (radius 0: none).
uniform vec4 pushers[4];
// How far a pusher lays the leaves over, radians at the tip.
uniform float push_bend = 1.3;
// How much light shows through a leaf.
uniform float translucency = 0.5;

// Fields only (SeaGrassBed.field sets these; 0 for fade_end leaves a planted bed as it is): the
// share of tufts kept falls as 1 / distance past lod_near (to keep_min) and to none by fade_end, the
// same sum SeaGrassBed._keep uses to choose how many each square draws. A tuft whose rank (the
// instance's custom y) is just within the share kept grows up out of the floor as the camera nears,
// and every tuft sinks into the floor over the last 40% of fade_end, so the meadow has no edge.
// Thinned tufts spread wider (up to 1.5 times), as GameCommon grass's blades do.
uniform float lod_near = 12.0;
uniform float fade_end = 0.0;
uniform float keep_min = 0.15;

uniform vec3 grass_deep : source_color = vec3(0.08, 0.27, 0.09);
uniform vec3 grass_bright : source_color = vec3(0.22, 0.5, 0.13);
uniform vec3 tip_pale : source_color = vec3(0.6, 0.68, 0.32);
uniform vec3 grass_lit : source_color = vec3(0.55, 0.8, 0.3);

varying float v_own;
varying float v_tuft;

void vertex() {
	vec3 foot = MODEL_MATRIX[3].xyz;
	float tall = max(length(MODEL_MATRIX[1].xyz), 0.01); // the tuft's height (the tallest leaf's)
	vec4 own = INSTANCE_CUSTOM; // x: a number of the tuft's own; y: its rank in a field's square
	vec3 rel = VERTEX - foot;
	if (fade_end > 0.0) {
		float seen = length(CAMERA_POSITION_WORLD - foot);
		float keep = (seen <= lod_near ? 1.0 : max(lod_near / seen, keep_min)) * (1.0 - smoothstep(fade_end * 0.72, fade_end, seen));
		float shown = clamp((keep * 1.15 - own.y) / max(0.6 * keep, 0.0001), 0.0, 1.0);
		float grown = shown * (1.0 - 0.7 * smoothstep(fade_end * 0.6, fade_end, seen));
		// (and the fewer kept, the wider each spreads, so a thinned meadow still covers its floor)
		float wide = clamp(inversesqrt(max(keep, 0.01)), 1.0, 1.5);
		rel *= vec3(grown * wide, grown, grown * wide);
		tall = max(tall * grown, 0.01);
	}
	float h = max(rel.y, 0.0);
	float leaf = UV2.x;

	vec2 axis = length(current) > 0.001 ? normalize(current) : vec2(1.0, 0.0);
	vec2 cross_axis = vec2(-axis.y, axis.x);
	float beat = water_clock * TAU / surge_period - dot(foot.xz, axis) * TAU / surge_length + own.x * 0.5;
	// The bend at the tip: the current's, the surge's, a little of the leaf's own.
	vec2 bend = current * 1.4
			+ axis * sway * 0.5 * sin(beat)
			+ cross_axis * sway * 0.12 * sin(beat * 0.63 + own.x * TAU + dot(foot.xz, vec2(0.21, 0.13)))
			+ vec2(sin(water_clock * 1.3 + leaf * 31.0), cos(water_clock * 1.1 + leaf * 23.0)) * 0.1 * flutter;
	for (int i = 0; i < 4; i++) {
		vec4 p = pushers[i];
		if (p.w <= 0.0) {
			continue;
		}
		vec2 away = foot.xz - p.xz;
		float dist = length(away);
		float close = (1.0 - smoothstep(p.w * 0.35, p.w, dist)) * (1.0 - smoothstep(1.0, 2.0, abs(p.y - foot.y)));
		bend += away / max(dist, 0.001) * close * push_bend;
	}
	float angle = min(length(bend), 1.45);
	vec2 d = angle > 0.0001 ? bend / length(bend) : axis;

	// Along an arc of that angle by the tip (a leaf's length is kept as it bends).
	float a = angle * h / tall;
	float out_ = angle > 0.0001 ? tall * (1.0 - cos(a)) / angle : 0.0;
	float up = angle > 0.0001 ? tall * sin(a) / angle : h;
	// A ripple running up the leaf, across the way it bends.
	vec2 side = vec2(-d.y, d.x);
	float t = h / tall;
	vec2 ripple = side * sin(t * 7.0 - water_clock * 2.6 + leaf * 19.0) * 0.035 * tall * t * flutter;
	vec3 pos = foot + vec3(rel.x + d.x * out_ + ripple.x, up, rel.z + d.y * out_ + ripple.y);

	// The normal turned as far as the leaf is there (about the line across the bend).
	vec3 k = vec3(d.y, 0.0, -d.x);
	vec3 n = NORMAL;
	n = n * cos(a) + cross(k, n) * sin(a) + k * dot(k, n) * (1.0 - cos(a));

	VERTEX = pos;
	NORMAL = normalize(n);
	v_own = leaf;
	v_tuft = own.x;
}

void fragment() {
	float along = UV.y;
	float tone = clamp(fract(v_own * 3.7 + v_tuft * 1.3) * 0.8 + 0.1, 0.0, 1.0);
	vec3 colour = mix(grass_deep, grass_bright, tone);
	// Darker at the foot, paler towards the tip.
	colour *= mix(0.55, 1.0, smoothstep(0.0, 0.3, along));
	colour = mix(colour, tip_pale, smoothstep(0.55, 1.0, along) * (0.35 + 0.5 * fract(v_own * 7.1)));
	// A faint midrib and veins along it.
	float across = abs(UV.x * 2.0 - 1.0);
	colour *= 0.94 + 0.06 * cos(across * 12.0);
	ALBEDO = colour;
	ROUGHNESS = 0.55;
	SPECULAR = 0.25;
}

void light() {
	float facing = dot(NORMAL, LIGHT);
	float behind = max(-facing, 0.0) * translucency;
	DIFFUSE_LIGHT += (max(facing, 0.0) + behind * 0.8 * grass_lit) * ATTENUATION * LIGHT_COLOR / PI;
}
