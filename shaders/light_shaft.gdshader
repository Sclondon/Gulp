// A shaft of light hanging down from the surface through the water (scripts/light_shafts.gd):
// a long flat strip that turns about its own length to face the eye, slanting the way the
// light comes down, soft at its sides, fading with depth, near the eye and far off. Drawn as
// added light. Each strip is one instance of a MultiMesh: its origin is where it leaves the
// surface, and INSTANCE_CUSTOM holds (length, width, a random seed, 0).
shader_type spatial;
render_mode blend_add, unshaded, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled, world_vertex_coords;

// The way the light runs down through the water (a unit vector, y below 0).
uniform vec3 slant = vec3(0.0, -1.0, 0.0);
uniform vec4 colour : source_color = vec4(0.6, 0.85, 1.0, 1.0);
// How bright the shafts are altogether (0 hides them).
uniform float strength = 0.15;
// The height of the sea's surface.
uniform float surface = 40.0;
global uniform float water_clock;

varying float v_across;
varying float v_along;
varying float v_depth;
varying float v_far;
varying float v_seed;

void vertex() {
	vec3 top = MODEL_MATRIX[3].xyz;
	float len = INSTANCE_CUSTOM.x;
	float wide = INSTANCE_CUSTOM.y;
	v_seed = INSTANCE_CUSTOM.z;
	// (it sways a little with the ripples overhead, each at its own pace)
	top.xz += vec2(sin(water_clock * 0.23 + v_seed * 17.0), cos(water_clock * 0.19 + v_seed * 11.0)) * 0.35;
	vec3 axis = normalize(slant);
	vec3 to_eye = CAMERA_POSITION_WORLD - (top + axis * len * 0.4);
	vec3 side = cross(axis, to_eye);
	side = length(side) > 0.0001 ? normalize(side) : vec3(1.0, 0.0, 0.0);
	float u = UV.x - 0.5;
	float v = UV.y;
	// (a little wider at the bottom, where its light has spread)
	vec3 p = top + axis * (v * len) + side * (u * wide * (1.0 + 0.5 * v));
	VERTEX = p;
	v_across = u * 2.0;
	v_along = v;
	v_depth = surface - p.y;
	v_far = length(CAMERA_POSITION_WORLD - p);
}

void fragment() {
	float soft = 1.0 - v_across * v_across;
	soft *= soft;
	// (none right at the surface, brightest a little under it, then dying away with depth)
	float deep = smoothstep(0.0, 2.5, v_depth) * exp(-v_depth / 13.0);
	// (nothing in the eye's face, and gone into the murk far off)
	float seen = smoothstep(1.0, 5.0, v_far) * (1.0 - smoothstep(18.0, 40.0, v_far));
	float ends = 1.0 - smoothstep(0.75, 1.0, v_along);
	// (each one breathes, slowly, brighter and fainter, and flickers along its length)
	float breath = 0.55 + 0.45 * sin(water_clock * (0.35 + 0.2 * v_seed) + v_seed * 40.0);
	float flicker = 0.8 + 0.2 * sin(v_along * 9.0 - water_clock * 1.3 + v_seed * 7.0);
	ALBEDO = colour.rgb;
	ALPHA = clamp(soft * deep * seen * ends * breath * flicker * strength, 0.0, 1.0);
}
