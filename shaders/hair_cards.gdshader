shader_type spatial;
// Hair, beards and moustaches as painted lock cards (tools/build_hair.py has the decision and how they are built).
// Each card carries a painted lock from a small atlas (colour and alpha); the alpha is cut, not blended (alpha
// scissor: opaque pass, no sorting, works the same in GL Compatibility on a phone). Both sides are drawn, and a back
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

varying vec3 lie;
varying float paint_light;

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
	ALPHA = paint.a * (1.0 + mip * keep_tips);
	ALPHA_SCISSOR_THRESHOLD = cut_off;
	vec3 c = paint.rgb * tint;
	c *= mix(1.0, COLOR.r, layer_shade);
	c *= mix(1.0 - root_dark, 1.0, smoothstep(0.0, 0.5, COLOR.g));
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
