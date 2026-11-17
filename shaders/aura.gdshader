shader_type spatial;
// A moon jelly's aura (scripts/moon_jelly.gd): a soft halo of its light in the water round it,
// and now and then a sparkle, a small four-pointed glint that comes up and is gone (the user,
// 2026-11-17: "a bit more of an ethereal soft glow, and a occosaional sparkle effect").
// Drawn on a square that always faces the camera, as light added to the picture.
render_mode blend_add, unshaded, cull_disabled, depth_draw_never, fog_disabled;

uniform vec3 light : source_color = vec3(0.5, 0.7, 1.0);
uniform float brightness = 1.0;
uniform float clock = 0.0;
// A number of its own for each jelly, so that they do not sparkle together.
uniform float seed = 0.0;
// How bright the halo is, and the sparkles.
uniform float halo = 0.13;
uniform float sparkle = 1.2;
// As the jelly's shader: the share of its light the water takes in each metre.
uniform float murk = 0.06;

float hash(float n) {
	return fract(sin(n * 127.1 + seed * 311.7) * 43758.5453);
}

void vertex() {
	// (the square turned to face the camera, keeping its size)
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
			vec4(normalize(INV_VIEW_MATRIX[0].xyz) * length(MODEL_MATRIX[0].xyz), 0.0),
			vec4(normalize(INV_VIEW_MATRIX[1].xyz) * length(MODEL_MATRIX[1].xyz), 0.0),
			vec4(normalize(INV_VIEW_MATRIX[2].xyz) * length(MODEL_MATRIX[2].xyz), 0.0),
			MODEL_MATRIX[3]);
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float far = length(p);
	// the halo: brightest at the jelly, fading softly to nothing at the square's edge
	float glow = pow(max(1.0 - far, 0.0), 2.6) * halo;
	// the sparkles: six places take turns, each lit less than half the time
	float glints = 0.0;
	for (int i = 0; i < 6; i++) {
		float turn = clock * 0.45 + float(i) * 0.37 + hash(float(i)) * 3.0;
		float which = floor(turn) + float(i) * 17.0;
		if (hash(which) > 0.4) {
			continue;
		}
		float life = sin(fract(turn) * 3.14159);
		life *= life * life;
		float angle = hash(which + 3.0) * 6.2831853;
		vec2 q = p - vec2(cos(angle), sin(angle)) * (0.12 + 0.4 * hash(which + 5.0));
		// (a bright point with four fine rays)
		float star = exp(-dot(q, q) * 5000.0);
		star += exp(-abs(q.x) * 380.0) * exp(-abs(q.y) * 45.0) * 0.5;
		star += exp(-abs(q.y) * 380.0) * exp(-abs(q.x) * 45.0) * 0.5;
		glints += star * life;
	}
	ALBEDO = (light * glow + mix(light, vec3(1.0), 0.6) * glints * sparkle) * brightness * exp(-murk * length(VERTEX));
}
