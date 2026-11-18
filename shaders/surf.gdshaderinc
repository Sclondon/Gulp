// The surf along every shore and the rogue wave: the same sums as scripts/surf.gd (keep them alike;
// every number comes from there through Surf.dress). tools/WATER_FX.md, "Surf and rogue waves".

// The shores, baked by Surf.bake: a texel every shore_rect.zw metres from shore_rect.xy: distance to
// the shore (m, less than 0 on land), depth (m), how open to the sea (0 in the slough and harbours).
// (With none set it reads 0, 0, 0: no surf.)
uniform sampler2D shore_map : filter_linear, repeat_disable, hint_default_black;
uniform vec4 shore_rect = vec4(-122.0, -160.0, 2.0, 2.0);
uniform vec2 shore_texel = vec2(0.0035, 0.0031);
// The surf: height, length, period, reach; the shoals' width and depth, McCowan's 0.78, the swash.
uniform vec4 surf_a = vec4(0.85, 14.0, 7.0, 28.0);
uniform vec4 surf_b = vec4(14.0, 5.0, 0.78, 0.3);
// The rogue wave: where it started (x, z) and its way; its age (s, less than 0 for none) and speed;
// its length, width, life and highest.
uniform vec4 rogue_a = vec4(0.0, 0.0, 1.0, 0.0);
uniform vec2 rogue_b = vec2(-1.0, 5.5);
uniform vec4 rogue_c = vec4(6.5, 30.0, 30.0, 4.5);
// The surf's colours: the green of a lit wave face, and the sandy green of the churned shallows.
uniform vec4 surf_glow : source_color = vec4(0.22, 0.72, 0.6, 1.0);
uniform vec4 surf_sandy : source_color = vec4(0.36, 0.58, 0.48, 1.0);
uniform vec4 surf_body : source_color = vec4(0.07, 0.34, 0.4, 1.0);
// (1 draws the baked shores as colours: red the distance to the shore over 30 m, green the depth over
// 10 m, blue the surf's weight)
uniform int surf_debug = 0;
// 1 while the eye is above the water (Sea.set_above)
uniform float eye_above = 0.0;

vec3 shore_at(vec2 xz) {
	return textureLod(shore_map, ((xz - shore_rect.xy) / shore_rect.zw + 0.5) * shore_texel, 0.0).rgb;
}

// Which way the surf runs here: down the shore distance, flat.
vec2 shore_way(vec2 xz) {
	vec2 g = vec2(shore_at(xz - vec2(shore_rect.z, 0.0)).x - shore_at(xz + vec2(shore_rect.z, 0.0)).x,
			shore_at(xz - vec2(0.0, shore_rect.w)).x - shore_at(xz + vec2(0.0, shore_rect.w)).x);
	float l = length(g);
	return l > 0.001 ? g / l : vec2(0.0);
}

float surf_jitter(vec2 p) {
	return 1.2 * sin(p.x * 0.045 + 1.3) * sin(p.y * 0.037 + 0.4) + 0.8 * sin((p.x + p.y) * 0.021 + 2.0);
}

// The surf at an (undisplaced) point: wa = (height, push shoreward, phase, the wave's height),
// wb = (breaking, steepness, wavenumber, weight). Surf.wave.
void surf_wave(vec2 p, float t, vec3 shore, out vec4 wa, out vec4 wb) {
	float d = shore.x;
	float h = shore.y;
	float w = shore.z * (1.0 - smoothstep(surf_a.w * 0.6, surf_a.w, d)) * (1.0 - smoothstep(9.0, 16.0, h)) * smoothstep(-6.0, -2.5, d);
	if (w <= 0.0) {
		wa = vec4(0.0);
		wb = vec4(0.0, 0.0, 1.0, 0.0);
		return;
	}
	float flat_w = surf_b.x;
	float dd = max(d, 0.25);
	float s = dd >= flat_w ? dd + flat_w : 2.0 * sqrt(dd * flat_w);
	float squeeze = dd >= flat_w ? 1.0 : min(sqrt(flat_w / dd), 3.0);
	float k0 = 6.2831853 / surf_a.y;
	float phase = -(k0 * s + 6.2831853 / surf_a.z * t) + surf_jitter(p);
	float sets = 0.8 + 0.3 * sin(phase * 0.27 + 1.0);
	float hh = max(h, 0.05);
	float shoal = surf_a.x * sets * pow(clamp(surf_b.y / max(hh, 0.5), 0.6, 3.0), 0.25);
	float limit = surf_b.z * 0.5 * hh;
	float ratio = shoal / max(limit, 0.01);
	float breaking = smoothstep(0.85, 1.25, ratio);
	float a = min(shoal, max(limit * 1.2, surf_b.w));
	float kl = k0 * squeeze;
	float steep = mix(0.3, 1.0, smoothstep(0.45, 1.05, ratio));
	float across = min(steep / kl, 2.5 * a);
	float up = sin(phase);
	float push = across * cos(phase) + breaking * a * 1.4 * pow(max(up, 0.0), 3.0);
	wa = vec4(a * up * w, push * w, phase, a);
	// (the fragment takes the shoaling ratio, not the breaking, which it works out from it)
	wb = vec4(min(ratio, 4.0), across * kl, kl, w);
}

float sech2(float v) {
	float c = cosh(clamp(v, -20.0, 20.0));
	return 1.0 / (c * c);
}

// The rogue wave at an (undisplaced) point: (height, push along its way, breaking, growth); its slope
// (world x, z) in `slope`, and in `shape` (along / length, how much of its width is here).
vec4 rogue_at(vec2 p, out vec2 slope, out vec2 shape) {
	slope = vec2(0.0);
	shape = vec2(10.0, 0.0);
	if (rogue_b.x < 0.0) {
		return vec4(0.0);
	}
	vec2 way = rogue_a.zw;
	vec2 rel = p - rogue_a.xy;
	float len = rogue_c.x;
	float along = dot(rel, way) - rogue_b.y * rogue_b.x;
	float across = dot(rel, vec2(-way.y, way.x));
	float grow = pow(sin(3.14159265 * clamp(rogue_b.x / rogue_c.z, 0.0, 1.0)), 1.5);
	float lat = exp(-pow(across / rogue_c.y, 2.0));
	float crest = sech2(along / len);
	float ta = (along - 1.7 * len) / (1.3 * len);
	float trough = sech2(ta);
	float high = rogue_c.w * grow * lat;
	float breaking = smoothstep(0.7, 0.92, grow) * lat;
	float push = high * (0.3 * crest * -tanh(along / len) + 0.35 * breaking * pow(crest, 4.0));
	float eta = high * (crest - 0.3 * trough);
	float d_along = high * (-2.0 / len * crest * tanh(along / len) + 0.3 * 2.0 / (1.3 * len) * trough * tanh(ta));
	float d_across = eta * (-2.0 * across / (rogue_c.y * rogue_c.y));
	slope = way * d_along + vec2(-way.y, way.x) * d_across;
	shape = vec2(along / len, lat);
	return vec4(eta, push, breaking, grow);
}
