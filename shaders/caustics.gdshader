// Caustics on everything under the water (scripts/caustics.gd; CLAUDE.md, "Decision: caustics as one
// pass over the picture"). A full-screen quad drawn first among the see-through things: for every
// pixel it rebuilds the place in the world from the depth buffer, which way that surface faces from
// how the place changes between neighbouring pixels, and then lays the net of light (the same net,
// scale, drift and clock the sand had) over the picture already drawn: brighter lines and darker
// cells on what faces up, fading with depth, with distance from the eye, never above the surface.
// The fog's share of a pixel is left alone, so far things are not lit through the murk.
shader_type spatial;
render_mode unshaded, blend_mix, depth_test_disabled, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;

uniform sampler2D screen : hint_screen_texture, filter_nearest;
uniform sampler2D depth : hint_depth_texture, filter_nearest;
uniform sampler2D caustic_tex : repeat_enable, filter_linear_mipmap;
// Strength by the hour (Sea._look), the surface's height, and the water's fog (colour, density).
uniform float caustics = 0.0;
uniform float caustic_surface = 40.0;
uniform vec3 fog_colour = vec3(0.0);
uniform float fog_density = 0.03;
global uniform float water_clock;

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * 0.1031);
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

float patches(vec2 p) {
	vec2 whole = floor(p);
	vec2 part = fract(p);
	part = part * part * (3.0 - 2.0 * part);
	return mix(mix(hash2(whole), hash2(whole + vec2(1.0, 0.0)), part.x),
			mix(hash2(whole + vec2(0.0, 1.0)), hash2(whole + vec2(1.0, 1.0)), part.x), part.y);
}

// The net (the user, 2026-11-18: "We need better looking caustics as well"): the usual way games draw
// caustics, two copies of one sharp, tileable net of light (Sea.caustic_texture: the edges of a Voronoi
// pattern, thin bright lines round soft dark cells) panning different ways at different sizes, a little
// warped, brightest where they cross; each colour read a little apart, for the thin rainbow fringe real
// caustics have. In patches, so that some stretches have more of it.
vec3 caustic_layer(vec2 uv, float split) {
	return vec3(texture(caustic_tex, uv + vec2(split, 0.0)).r, texture(caustic_tex, uv).r, texture(caustic_tex, uv - vec2(split, 0.0)).r);
}

vec3 caustic_net(vec3 p) {
	float t = water_clock;
	vec2 q = p.xz;
	vec2 warp = (vec2(patches(q * 0.18 + vec2(t * 0.05, 0.0)), patches(q * 0.18 + vec2(3.7, t * 0.04))) - 0.5) * 0.12;
	vec3 a = caustic_layer(q * 0.11 + warp + vec2(t * 0.013, t * 0.008), 0.0015);
	vec3 b = caustic_layer(q * 0.15 - warp + vec2(-t * 0.011, t * 0.012) + 0.37, 0.0015);
	vec3 net = max(a, b) * 0.55 + a * b * 1.3;
	net = pow(net, vec3(1.3)) * 1.6;
	float spread = 0.5 + 0.5 * smoothstep(0.3, 0.65, patches(p.xz * 0.035 + 4.0));
	return net * spread;
}

void vertex() {
	// (a 2 x 2 quad covering the whole view, whatever the camera does)
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec3 seen = texture(screen, SCREEN_UV).rgb;
	ALBEDO = seen;
	float d = texture(depth, SCREEN_UV).r;
	if (caustics <= 0.0 || d >= 1.0) {
		ALPHA = 0.0;
	} else {
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
		vec3 ndc = vec3(SCREEN_UV, d) * 2.0 - 1.0;
#else
		vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, d);
#endif
		vec4 view = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
		view.xyz /= view.w;
		vec3 at = (INV_VIEW_MATRIX * vec4(view.xyz, 1.0)).xyz;
		float far = length(view.xyz);
		// Which way the surface faces, from its neighbours (flat per pixel: enough for a net this
		// soft). Where the next pixel is much further off (an outline), the facing is unknown: none there.
		vec3 dx = dFdx(at);
		vec3 dy = dFdy(at);
		vec3 n = normalize(cross(dy, dx));
		n *= sign(dot(n, CAMERA_POSITION_WORLD - at) + 1e-6);
		float step_size = max(length(dx), length(dy));
		float edge = 1.0 - smoothstep(0.02, 0.06, step_size / max(far, 0.1));
		float deep = caustic_surface - at.y;
		float k_strength = caustics
				* mix(1.0, 0.3, smoothstep(3.0, 30.0, deep)) * (1.0 - smoothstep(30.0, 45.0, deep))
				* smoothstep(0.05, 0.3, deep)
				* smoothstep(0.1, 0.75, n.y) * edge
				* (1.0 - smoothstep(25.0, 40.0, far));
		vec3 k = mix(vec3(1.0), vec3(0.55) + caustic_net(at), k_strength);
		// (moderate peaks: the bloom smears very bright lines)
		k = min(k, vec3(1.9));
		// Only the surface's own share of the pixel is lit; the fog's share is kept.
		float fogged = 1.0 - exp(-far * fog_density);
		vec3 own = max(seen - fog_colour * fogged, vec3(0.0));
		ALBEDO = seen + own * (k - 1.0) * 0.8;
		ALPHA = 1.0;
	}
}
