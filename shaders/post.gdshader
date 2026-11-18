// Screen post-process for the low-res 3D view: under water, a swimming picture in the colour
// of the water; the water churned behind a fast fish (a shimmer, like heat haze) and streaks
// past the edges while it bursts; then colour quantisation + Bayer dither + vignette.
// (The shafts of light that were drawn here stand in the sea now: scripts/light_shafts.gd.
// The control panel is drawn over this by its own Control, so nothing here touches it.)
shader_type canvas_item;

uniform float levels = 28.0;
// How much of the banded, dithered colour is mixed in (0 leaves the picture smooth).
uniform float dither = 0.5;
uniform float vignette = 0.2;
// How far under the water the camera is (0 above the surface, 1 below it), and the colour of
// the water it is in.
uniform float underwater = 0.0;
uniform vec4 water_tint : source_color = vec4(0.16, 0.7, 0.64, 1.0);
// Under water: how far the picture sways (in screen widths), how strongly it is tinted.
uniform float sway = 0.0045;
uniform float tint = 0.42;
// (no longer used: the shafts of light stand in the sea)
uniform float shafts = 0.0;
// The churned water behind the fish (scripts/effects.gd): up to eight points on the screen, each
// (x, y as UV, radius in screen heights, strength 0..1).
uniform vec4 haze[8];
// How strongly streaks run out past the edges (0 none; while it bursts, by how fast it goes).
uniform float streaks = 0.0;
// The machine's signal failing (0 clear to 1 lost): below the depth its amplifier reaches the
// picture fills with static (DESIGN.md; scripts/main.gd sets it).
uniform float signal_loss = 0.0;

const float BAYER[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0,
		3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);

float hash1(float n) {
	return fract(sin(n * 12.9898) * 43758.5453);
}

void fragment() {
	vec2 uv = UV;
	float aspect = TEXTURE_PIXEL_SIZE.y / TEXTURE_PIXEL_SIZE.x;
	// the picture sways, as seen through moving water
	uv += vec2(sin(UV.y * 17.0 + TIME * 2.1), cos(UV.x * 13.0 + TIME * 1.6)) * sway * underwater;
	// and shimmers where the water has just been churned by the fish
	float churn = 0.0;
	for (int i = 0; i < 8; i++) {
		vec4 h = haze[i];
		if (h.w > 0.001) {
			vec2 d = (UV - h.xy) * vec2(aspect, 1.0);
			churn += h.w * exp(-dot(d, d) / max(h.z * h.z, 0.00001));
		}
	}
	churn = min(churn, 0.8) * underwater;
	uv += vec2(sin(UV.y * 70.0 + TIME * 9.0), cos(UV.x * 60.0 * aspect - TIME * 7.0)) * 0.0022 * churn;
	vec4 c = texture(TEXTURE, clamp(uv, vec2(0.001), vec2(0.999)));
	if (underwater > 0.001) {
		// brightened towards the colour of the water, a little washed out
		vec3 hue = normalize(water_tint.rgb + 0.05) * 1.35;
		float grey = dot(c.rgb, vec3(0.3, 0.5, 0.2));
		vec3 w = mix(c.rgb, vec3(grey), 0.1) * mix(vec3(1.0), hue, tint) + water_tint.rgb * 0.1;
		// and darker towards the edges and the depths
		vec2 e = UV - vec2(0.5, 0.35);
		w *= 1.0 - dot(e, e) * 0.7;
		c.rgb = mix(c.rgb, w, underwater);
	}
	if (streaks > 0.001) {
		// Pale streaks running out from the middle past the edges, as specks rushing by: thin
		// spokes, only some of them lit, each a dash or two that runs outwards.
		vec2 d = (UV - vec2(0.5, 0.45)) * vec2(aspect, 1.0);
		float r = length(d);
		float spoke = (atan(d.y, d.x) / 6.2832 + 0.5) * 110.0;
		float id = floor(spoke);
		float seed = hash1(id);
		float thin = 1.0 - smoothstep(0.0, 0.16 + 0.1 * seed, abs(fract(spoke) - 0.5));
		float dash = fract(r * (1.6 + seed) - TIME * (1.4 + 1.6 * seed) * (0.6 + streaks) + seed * 7.0);
		float lit = step(0.66, seed) * smoothstep(0.0, 0.08, dash) * (1.0 - smoothstep(0.25, 0.55, dash));
		// (by how far out towards the corners, whichever way up the screen is)
		float edge = smoothstep(0.35, 0.95, r / length(vec2(aspect, 1.0) * 0.5));
		c.rgb = mix(c.rgb, vec3(0.85, 0.95, 1.0), thin * lit * edge * streaks * 0.55);
	}
	if (signal_loss > 0.001) {
		// Static: grey snow in blocks of the low picture, changing every frame, rolling bands and
		// lines torn sideways; the picture behind it greyed and fading as the signal goes.
		vec2 cell = floor(UV / TEXTURE_PIXEL_SIZE);
		float frame = floor(TIME * 30.0);
		float snow = hash1(cell.x * 1.37 + cell.y * 113.1 + frame * 7.13);
		float band = 0.5 + 0.5 * sin(UV.y * 9.0 - TIME * 5.0);
		float tear = step(1.0 - 0.25 * signal_loss, hash1(cell.y * 0.71 + frame * 3.1));
		vec4 torn = texture(TEXTURE, clamp(uv + vec2(0.04 * tear * signal_loss, 0.0), vec2(0.001), vec2(0.999)));
		vec3 base = mix(c.rgb, torn.rgb, tear);
		vec3 grey = vec3(dot(base, vec3(0.3, 0.5, 0.2)));
		vec3 under = mix(base, grey, signal_loss) * (1.0 - 0.6 * signal_loss);
		float amount = clamp(signal_loss * (0.5 + 0.3 * band), 0.0, 0.85);
		c.rgb = mix(under, vec3(snow), amount);
	}
	ivec2 px = ivec2(mod(floor(UV / TEXTURE_PIXEL_SIZE), 4.0));
	float threshold = BAYER[px.y * 4 + px.x] / 16.0;
	c.rgb = mix(c.rgb, floor(c.rgb * levels + threshold) / levels, dither);
	vec2 d = UV - 0.5;
	c.rgb *= 1.0 - dot(d, d) * vignette * 2.0;
	COLOR = vec4(c.rgb, 1.0);
}
