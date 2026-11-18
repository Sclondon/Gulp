shader_type spatial;
render_mode cull_disabled, world_vertex_coords;
// Giant kelp, drawn a metre of frond bundle at a time by KelpForest's MultiMeshes (the pieces are
// models/kelp_*.glb; tools/build_kelp.py says what their UVs hold). All of its moving is here:
// - a slow surge to and fro that grows with the height above the holdfast, and runs through the
//   forest as a wave (from where the plant stands and `water_clock`);
// - a steady lean down-current;
// - where a frond reaches `surface_y` it turns over and lies along the surface, streaming
//   down-current, flattened into a canopy;
// - each blade flutters.
// The blades are single sheets drawn from both sides, their toothed edge cut here (discard: no
// blending), their crinkles drawn; light shows through them. Nothing here needs more than GL
// Compatibility has.

// Seconds, set by the game (a global shader uniform: Project Settings > Shader Globals, or
// RenderingServer.global_shader_parameter_add; KelpForest adds and runs one if there is none).
global uniform float water_clock;

// The world height of the water's surface.
uniform float surface_y = 0.0;
// Which way the water streams (world x, z) and how hard: 1 leans a frond's top about 14 degrees.
uniform vec2 current = vec2(0.0);
// How far the surge swings them: 1 about 12 degrees either way at the top, 0 still.
uniform float sway = 1.0;
// Seconds for the surge to go there and back, and metres between its crests through the forest.
uniform float surge_period = 7.0;
uniform float surge_length = 34.0;
// How much each blade flutters.
uniform float flutter = 1.0;
// How deep the teeth of a blade's edge are cut (0 for a plain edge).
uniform float teeth = 1.0;
// How much light shows through a blade (seen from below against the surface, or against a light).
uniform float translucency = 0.55;

uniform vec3 blade : source_color = vec3(0.47, 0.37, 0.09);
uniform vec3 blade_amber : source_color = vec3(0.68, 0.43, 0.08);
uniform vec3 blade_lit : source_color = vec3(0.86, 0.64, 0.2);
uniform vec3 bulb : source_color = vec3(0.58, 0.47, 0.14);
uniform vec3 stipe : source_color = vec3(0.3, 0.23, 0.08);

varying float v_part;
varying float v_own;
varying float v_high;

void vertex() {
	vec3 foot = MODEL_MATRIX[3].xyz;
	vec4 own = INSTANCE_CUSTOM; // metres this piece is above the holdfast, the plant's height, a number of its own, 1 for a holdfast
	vec3 root = foot - vec3(0.0, own.x, 0.0);
	vec3 rel = VERTEX - foot;
	// How far up the frond this point is, and where it is from the frond's middle line.
	float s = max(own.x + rel.y, 0.0);
	vec3 off = vec3(rel.x, 0.0, rel.z);
	float depth = max(surface_y - 0.05 - root.y, 0.5);
	float reach = max(min(depth, own.y), 1.0);

	// The lean: the current's, and the surge, a wave through the forest that the tops follow late.
	vec2 axis = length(current) > 0.001 ? normalize(current) : vec2(1.0, 0.0);
	float beat = water_clock * TAU / surge_period - dot(root.xz, axis) * TAU / surge_length - s * 0.1 + own.z * 0.7;
	vec2 lean = current * 0.25
			+ axis * sway * 0.21 * sin(beat)
			+ vec2(-axis.y, axis.x) * sway * 0.07 * sin(beat * 0.61 + own.z * TAU + dot(root.xz, vec2(0.13, 0.08)));

	// Up to the surface, then over and along it (a smooth least of `s` and the depth: its slope is `up`).
	float turn = min(2.5, depth * 0.6);
	float up = clamp(0.5 + 0.5 * (depth - s) / turn, 0.0, 1.0);
	float y = mix(depth, s, up) - turn * up * (1.0 - up);
	float run = s - y;
	float lying = 1.0 - up;
	// (the canopy streams down-current, each plant a little to one side; in still water each its own way)
	float fan = length(current) > 0.001 ? (own.z - 0.5) * 1.1 : own.z * TAU;
	vec2 stream = vec2(axis.x * cos(fan) - axis.y * sin(fan), axis.x * sin(fan) + axis.y * cos(fan));
	vec2 across = vec2(-stream.y, stream.x);
	float snake = sin(run * 0.55 - water_clock * 0.6 + own.z * 9.0) * 0.35 * smoothstep(0.0, 3.0, run);
	vec2 flat_at = lean * (y * y) / (2.0 * reach) + stream * run + across * snake;
	vec3 along = normalize(vec3(lean.x * y / reach * up + stream.x * lying, up + 0.0001, lean.y * y / reach * up + stream.y * lying));

	// The bundle is drawn in at the holdfast and spreads where it lies on the surface.
	// (`own.w` is 1 for a holdfast, which keeps its own width)
	off *= mix(mix(0.45, 1.0, smoothstep(0.0, 2.5, s)), 1.0, own.w) * (1.0 + 0.5 * lying);
	// Turned the least way that takes straight up to the frond's line there.
	vec3 both = vec3(0.0, 1.0, 0.0) + along;
	vec3 moved = off - both * (dot(off, both) / (1.0 + along.y));
	vec3 normal = NORMAL - both * (dot(NORMAL, both) / (1.0 + along.y)) + 2.0 * NORMAL.y * along;
	// (flattened where it lies)
	moved.y *= mix(1.0, 0.22, lying);
	// (and drawn in across the stream, so that its blades trail along it)
	vec3 across3 = vec3(across.x, 0.0, across.y);
	moved -= across3 * dot(moved, across3) * 0.45 * lying;
	normal.y *= mix(1.0, 4.5, lying);
	normal = normalize(normal);
	vec3 pos = root + vec3(flat_at.x, y, flat_at.y) + moved;

	float part = UV2.x;
	if (part > 1.5) {
		// A blade: it flutters, more towards its tip, and trails the way the water is taking the frond.
		float along_blade = UV.y;
		float wave = sin(water_clock * 2.1 + UV2.y * 40.0 + along_blade * 3.5 + s * 0.8);
		pos += normal * wave * 0.035 * flutter * along_blade * along_blade;
		pos.xz += lean * along_blade * along_blade * 0.35 * (1.0 - lying);
		pos.xz += stream * along_blade * 0.3 * lying;
	}
	pos.y = min(pos.y, surface_y - 0.01);

	VERTEX = pos;
	NORMAL = normal;
	v_part = part;
	v_own = UV2.y;
	v_high = s / max(own.y, 1.0);
}

void fragment() {
	vec3 colour = stipe;
	if (v_part > 1.5) {
		float side = abs(UV.x * 2.0 - 1.0);
		float along_blade = UV.y;
		// The toothed edge.
		float saw = abs(fract(along_blade * 30.0 + v_own * 7.0) - 0.5) * 2.0;
		if (side > 1.0 - teeth * 0.16 * saw * smoothstep(0.02, 0.14, along_blade)) {
			discard;
		}
		// Crinkles: ridges along the blade that wander, lighter and darker.
		float ridge = sin(UV.x * 16.0 + sin(along_blade * 19.0 + v_own * 40.0) * 1.6);
		float pucker = sin(along_blade * 47.0 + UV.x * 9.0 + v_own * 13.0);
		colour = mix(blade, blade_amber, clamp(fract(v_own * 5.3) * 0.7 + along_blade * 0.3 + v_high * 0.25, 0.0, 1.0));
		colour *= 0.88 + 0.08 * ridge + 0.04 * pucker;
		colour *= 1.0 - 0.25 * smoothstep(0.75, 1.0, side);
		// Light from the surface shows through it: brighter seen from below, looking up.
		vec3 to_eye = (INV_VIEW_MATRIX * vec4(VIEW, 0.0)).xyz;
		float against = clamp(-to_eye.y, 0.0, 1.0);
		colour = mix(colour, blade_lit * (0.8 + 0.25 * ridge), translucency * against * against * 0.5);
	} else if (v_part > 0.5) {
		colour = bulb;
	}
	ALBEDO = colour;
	ROUGHNESS = 0.6;
	SPECULAR = 0.2;
}

void light() {
	float facing = dot(NORMAL, LIGHT);
	float thin = step(1.5, v_part);
	// A sheet lit from behind glows; seen against the light, more.
	float behind = max(-facing, 0.0) * translucency * thin;
	float against = pow(max(dot(VIEW, -LIGHT), 0.0), 3.0) * translucency * thin;
	DIFFUSE_LIGHT += (max(facing, 0.0) + (behind * 0.8 + against) * vec3(1.35, 1.1, 0.55)) * ATTENUATION * LIGHT_COLOR / PI;
}
