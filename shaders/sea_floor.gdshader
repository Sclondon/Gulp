shader_type spatial;
// The sea floor (models/sea_floor.glb): sand with wind-like ripples left by the current, rock with
// silt lying on its tops, and over both the net of light that the waves overhead throw down. The
// net is made as the pale wandering lines of Salmon Run 2's water are (shaders/water.gdshader),
// two layers of them drifting across one another; the noise is that shader's too.

// Rock (silt lies on whatever of it faces up) or sand.
uniform bool rock = false;
uniform vec3 sand : source_color = vec3(0.56, 0.55, 0.5);
uniform vec3 sand_dark : source_color = vec3(0.34, 0.36, 0.38);
uniform vec3 stone : source_color = vec3(0.2, 0.22, 0.27);
// The sand's ripples: how many metres from one to the next, and how deep they look.
uniform float ripple_length = 0.16;
uniform float ripple_depth : hint_range(0.0, 1.0) = 0.35;
// The net of light: how bright, how big its meshes are (metres), how fast it drifts.
uniform float caustics : hint_range(0.0, 3.0) = 0.9;
uniform float caustic_size = 1.3;
uniform float caustic_speed = 0.12;
uniform vec3 caustic_colour : source_color = vec3(0.55, 0.8, 1.0);

varying vec3 world;
varying vec3 world_normal;

// (worked out in whole numbers, so that it is the same on every renderer: see water.gdshader)
float hash(vec2 p) {
	ivec2 c = ivec2(round(p));
	uint h = uint(c.x) * 668265261u ^ (uint(c.y) * 374761393u);
	h ^= h >> 15u;
	h *= 2246822519u;
	h ^= h >> 13u;
	h *= 3266489917u;
	h ^= h >> 16u;
	return float(h) / 4294967295.0;
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
			mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

// One layer of wandering bright lines.
float net(vec2 p, float t) {
	vec2 lp = p + (vec2(vnoise(p * 0.7 + 1.0), vnoise(p * 0.7 + 7.0)) - 0.5) * 2.0;
	return 1.0 - smoothstep(0.0, 0.09, abs(vnoise(lp + vec2(t, t * 0.6)) - 0.5));
}

float ripples(vec2 p) {
	float bend = vnoise(p * 0.35) * 5.0 + vnoise(p * 1.3) * 1.2;
	return sin((p.x * 0.35 + p.y) * 6.2831853 / ripple_length + bend);
}

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 col;
	float up = clamp(world_normal.y, 0.0, 1.0);
	if (rock) {
		float grain = vnoise(world.xz * 9.0 + world.y * 5.0);
		col = stone * (0.7 + 0.6 * vnoise(world.xz * 1.7 + world.y * 2.3)) * (0.8 + 0.4 * grain);
		col = mix(col, sand * 0.8, smoothstep(0.55, 0.95, up + 0.2 * (grain - 0.5)) * 0.75);
	} else {
		// (ripples fade far off, where they would only shimmer)
		float far = length(VERTEX);
		float r = ripples(world.xz) * (1.0 - smoothstep(2.5, 9.0, far));
		float patch = vnoise(world.xz * 0.5);
		col = mix(sand_dark, sand, 0.55 + 0.25 * patch + 0.2 * ripple_depth * r);
		col *= 0.9 + 0.2 * vnoise(world.xz * 40.0);
	}
	ALBEDO = col;
	ROUGHNESS = 0.95;
	SPECULAR = 0.1;
	// the light of the waves, on whatever faces up
	vec2 p = world.xz / caustic_size;
	float t = TIME * caustic_speed;
	float light = net(p, t) * 0.7 + net(p * 1.7 + 5.0, -t * 1.3) * 0.45;
	light *= 0.5 + 0.5 * vnoise(p * 0.4 + t * 0.5);
	EMISSION = caustic_colour * col * light * caustics * smoothstep(0.1, 0.7, up);
}
