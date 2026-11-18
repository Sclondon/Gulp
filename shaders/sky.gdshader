shader_type sky;
// The sky over the water, seen only from above it (scripts/sea.gd sets it in the air, a plain water
// colour under it): pale at the horizon, deeper overhead, the sun (or the moon) with a glow round it,
// and soft clouds drifting slowly. Its colours follow the hour (scripts/day.gd), set by Sea._look.
// It does not light anything: the ambient light is still Sea's own colour.

uniform vec3 zenith : source_color = vec3(0.16, 0.38, 0.85);
uniform vec3 horizon : source_color = vec3(0.7, 0.84, 0.97);
uniform vec3 sun_colour : source_color = vec3(1.0, 0.95, 0.85);
// 0 none, 1 a broken sky
uniform float cover = 0.45;
uniform vec3 cloud_lit : source_color = vec3(1.0);
uniform vec3 cloud_shade : source_color = vec3(0.68, 0.74, 0.84);
// how far the clouds have drifted (Sea sets it from its clock a few times a second: the sky is then not
// redrawn into its radiance every frame, as TIME would make it)
uniform vec2 drift = vec2(0.0);

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
	float sum = 0.0;
	float k = 0.5;
	for (int i = 0; i < 4; i++) {
		sum += noise(p) * k;
		p = p * 2.03 + vec2(1.7, 9.2);
		k *= 0.5;
	}
	return sum;
}

void sky() {
	vec3 d = normalize(EYEDIR);
	float up = max(d.y, 0.0);
	vec3 c = mix(horizon, zenith, pow(up, 0.55));
	float toward = LIGHT0_ENABLED ? max(dot(d, LIGHT0_DIRECTION), 0.0) : 0.0;
	// (the glow round the sun, and the disc)
	c += sun_colour * (pow(toward, 10.0) * 0.22 + pow(toward, 90.0) * 0.35);
	c = mix(c, sun_colour * 1.6, smoothstep(0.9993, 0.9996, toward));
	// Clouds: noise on a high flat ceiling, thinning out toward the horizon.
	if (d.y > 0.0) {
		vec2 at = d.xz / (d.y + 0.08) * 1.4 + drift;
		float n = fbm(at);
		float cloud = smoothstep(1.0 - cover * 0.75, 1.15 - cover * 0.6, n) * smoothstep(0.02, 0.2, d.y);
		float lit = clamp(fbm(at + vec2(0.04, 0.03)) - n + 0.55, 0.0, 1.0);
		vec3 cc = mix(cloud_shade, cloud_lit, lit) + sun_colour * pow(toward, 6.0) * 0.25;
		c = mix(c, cc, cloud * 0.9);
	}
	COLOR = c;
}
