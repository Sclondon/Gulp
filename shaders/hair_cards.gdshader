shader_type spatial;
// Hair, beards and moustaches as painted lock cards (tools/build_hair.py has the decision and how they are built).
// Each card carries a painted lock from a small atlas (colour and alpha); the alpha is cut, not blended (a discard,
// dithered over `feather`: opaque pass, no sorting, works the same in GL Compatibility on a phone). Both sides are drawn, and a back
// face keeps the normal it was given (the smooth hull's, outward), so every card shades as part of one soft mass.
//
// Vertex colour: r = layer shade (deep layers darker), g = along the lock (0 root .. 1 tip), b = 1 on cards, 0 on the
// under-shell.
render_mode cull_disabled, depth_draw_opaque;

uniform sampler2D locks : source_color, filter_linear_mipmap, repeat_disable;
// Multiplies the painted colour (white keeps the painting).
uniform vec3 tint : source_color = vec3(1.0);
uniform float cut_off = 0.5;
// Far off a mipmapped alpha thins and the tips vanish: alpha is raised by this much a mip level.
uniform float keep_tips = 0.3;
// How much the vertex colour's red (the layer) and green (root to tip) darken.
uniform float layer_shade = 1.0;
uniform float root_dark = 0.2;
// Light: wrapped and soft (a painted look); the shadow side is tinted.
uniform float wrap = 0.45;
uniform float softness = 0.6;
uniform vec3 shade_tint : source_color = vec3(0.75, 0.7, 0.8);
// The warm light hair catches in sun (the brother's amber-red): added where the sun faces it, and a rim where the sun
// is behind it, scaled by how light the painting is there.
uniform vec3 sheen : source_color = vec3(1.0, 0.45, 0.15);
uniform float sheen_gain = 0.0;
uniform float sheen_power = 2.0;
uniform float rim_gain = 0.0;
// A soft gloss band across the mass (Kajiya-Kay along the lock), broken by the painting.
uniform vec3 gloss_colour : source_color = vec3(1.0, 0.95, 0.85);
uniform float gloss_gain = 0.0;
uniform float gloss_power = 30.0;
// Wind or swimming: tips sway by this many metres (0 off).
uniform float sway = 0.0;
uniform float sway_rate = 1.3;
// A soft edge (fourth pass): the cut is DITHERED over this much of the alpha round cut_off (a 4 x 4 ordered pattern on
// screen), so painted tips and a beard's outline feather out instead of ending razor-cut; still opaque (no sorting).
// 0 is a hard cut.
uniform float feather = 0.0;
// A soft light along the middle of each modelled lock and card (from the tile's u: 1 at the middle, 0 at the edges),
// so a lock's crest is a highlight, not a geometric ridge. Applies where the vertex colour's blue is 1 (not the shell).
uniform float crest_gain = 0.0;

varying vec3 lie;
varying float paint_light;

float bayer4(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	int i = q.x + q.y * 4;
	// (the 4 x 4 Bayer matrix, row by row)
	const float m[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
	return (m[i] + 0.5) / 16.0;
}

void vertex() {
	if (sway > 0.0) {
		float t = COLOR.g * COLOR.b;
		VERTEX += NORMAL * sway * t * t * sin(TIME * sway_rate + VERTEX.x * 31.0 + VERTEX.z * 23.0);
	}
	lie = normalize((MODELVIEW_MATRIX * vec4(BINORMAL, 0.0)).xyz);
}

void fragment() {
	vec4 paint = texture(locks, UV);
	vec2 px = UV * vec2(textureSize(locks, 0));
	float mip = max(0.0, 0.5 * log2(max(dot(dFdx(px), dFdx(px)), dot(dFdy(px), dFdy(px)))));
	float a = paint.a * (1.0 + mip * keep_tips);
	// (cut by hand, not with ALPHA_SCISSOR: the threshold dithered over `feather`; nothing writes ALPHA, so it stays
	// in the opaque pass)
	if (a < cut_off + (bayer4(FRAGCOORD.xy) - 0.5) * feather) {
		discard;
	}
	vec3 c = paint.rgb * tint;
	c *= mix(1.0, COLOR.r, layer_shade);
	c *= mix(1.0 - root_dark, 1.0, smoothstep(0.0, 0.5, COLOR.g));
	if (crest_gain > 0.0) {
		float u = fract(UV.x * 4.0) * 2.0 - 1.0;
		c *= 1.0 + crest_gain * COLOR.b * (exp(-u * u * 3.0) - 0.45);
	}
	ALBEDO = c;
	paint_light = dot(paint.rgb, vec3(0.3, 0.5, 0.2));
	// (Godot turns a back face's normal round; give it back the hull's)
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float w = (ndl + wrap) / (1.0 + wrap);
	float lit = mix(step(0.5, w), smoothstep(0.0, 1.0, w), softness) * ATTENUATION;
	vec3 lc = LIGHT_COLOR / PI;
	DIFFUSE_LIGHT += lc * lit;
	DIFFUSE_LIGHT += lc * shade_tint * 0.12 * (1.0 - lit);
	if (sheen_gain > 0.0) {
		DIFFUSE_LIGHT += lc * sheen * sheen_gain * pow(clamp(ndl, 0.0, 1.0), sheen_power) * ATTENUATION
				* smoothstep(0.08, 0.5, paint_light);
	}
	if (rim_gain > 0.0) {
		float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0) * clamp(dot(-VIEW, LIGHT) + 0.3, 0.0, 1.0);
		DIFFUSE_LIGHT += lc * sheen * rim_gain * rim * ATTENUATION;
	}
	if (gloss_gain > 0.0) {
		vec3 h = normalize(LIGHT + VIEW);
		float th = dot(lie, h);
		float band = pow(sqrt(max(1.0 - th * th, 0.0)), gloss_power);
		SPECULAR_LIGHT += lc * gloss_colour * gloss_gain * band * clamp(ndl + 0.2, 0.0, 1.0) * ATTENUATION
				* smoothstep(0.1, 0.6, paint_light);
	}
}
