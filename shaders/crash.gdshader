shader_type spatial;
// The crash where a barrel's lip lands (scripts/breakers.gd, `_land`; tools/WATER_FX.md, "Third pass: the crash").
// One painted puff a MultiMesh instance, all of it worked out here from the water's clock: the instance's
// transform is not a turn but the landing's data (full floats):
//   origin: where the lip's tip came down; column 0: (the heading of the way in to the shore, the sea floor's height
//   there, the time it landed);
//   column 1: (along the break x, z, the wave's height); column 2: (which kind of puff, its seed, its strength).
// The kinds are listed at Breakers.CRASH_KINDS. Each flies by a closed sum (linear drag: no state), so the crash is
// the same whether the clock runs or is held.
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, skip_vertex_transform, shadows_disabled;

global uniform float water_clock;
uniform sampler2D puff : source_color, filter_linear_mipmap, repeat_disable;
// The light of the hour (unshaded, so dimmed by hand, as the plume is).
uniform float lit = 1.0;
// 1 with the eye under the water: only the bubbles are drawn then, and only they are hidden above it.
uniform float under = 0.0;

varying vec4 v_tint;
varying float v_cut;
varying float v_seed;

float hash1(float n) {
	return fract(sin(n * 12.9898 + 4.1414) * 43758.5453);
}

// Flight under a pull g with linear drag k from a start speed v0: where it is after t (s).
vec3 fly(vec3 v0, vec3 g, float k, float t) {
	return g * (t / k) + (v0 - g / k) * ((1.0 - exp(-k * t)) / k);
}

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec3 way = vec3(cos(MODEL_MATRIX[0].x), 0.0, sin(MODEL_MATRIX[0].x));
	float bed = MODEL_MATRIX[0].y;
	float birth = MODEL_MATRIX[0].z;
	vec3 along = vec3(MODEL_MATRIX[1].x, 0.0, MODEL_MATRIX[1].y);
	float h = max(MODEL_MATRIX[1].z, 0.3);
	int kind = int(MODEL_MATRIX[2].x + 0.5);
	float seed = MODEL_MATRIX[2].y;
	float strength = MODEL_MATRIX[2].z;
	float r1 = hash1(seed);
	float r2 = hash1(seed + 1.7);
	float r3 = hash1(seed + 3.1);
	float r4 = hash1(seed + 5.3);
	vec3 up = vec3(0.0, 1.0, 0.0);
	// (sizes and speeds follow the wave: 3 m is the full set at Steamer Lane)
	float s = sqrt(h / 3.0);
	float t = water_clock - birth;
	vec3 p = o;
	float delay = 0.0;
	float life = 1.0;
	float size = 0.0;
	float alpha = 1.0;
	float fade_in = 0.06;
	float fade_out = 0.4;
	vec3 tint = vec3(1.0);
	float squash = 1.0;
	float spin = (r1 - 0.5) * 0.8;
	float cut = 0.0;
	bool air = true;
	// (faded out this near the eye: from, to (m))
	vec2 near = vec2(1.5, 7.0);
	float tt = 0.0;
	if (kind == 0) {
		// the splash-up: the lip's jet hits the water and throws a sheet of white up and forward over it, about as
		// high as the wave (most nearly upright, some leaning forward to curl over); a little later along the
		// landing line, a few at a time
		delay = r1 * 0.1;
		tt = max(t - delay, 0.0);
		life = 1.1 + r2 * 0.6;
		float lean = mix(-0.15, 0.9, r3);
		float speed = sqrt(2.0 * 9.8 * h * mix(0.7, 1.6, r4)) * strength;
		vec3 v0 = normalize(up + way * lean + along * (r2 - 0.5) * 0.5) * speed;
		p = o + way * 0.1 * h + along * (r2 - 0.5) * 0.9 + fly(v0, vec3(0.0, -9.8, 0.0), 0.8, tt);
		// (the fast ones are the spray thrown off its top: smaller, and gone sooner)
		size = h * mix(0.55, 0.2, r4) * (0.45 + 0.9 * smoothstep(0.0, 0.7, tt / life));
		life *= mix(1.0, 0.75, r4);
		// (some thinner than others, so the heap shows its folds instead of a row of beads)
		alpha = mix(0.7, 0.97, r3);
	} else if (kind == 1) {
		// the second splash, ahead of the first and lower, thrown further forward: the secondary curl
		delay = 0.28 + r1 * 0.18;
		tt = max(t - delay, 0.0);
		life = 0.9 + r2 * 0.5;
		float lean = mix(0.35, 1.3, r3);
		float speed = sqrt(2.0 * 9.8 * h * mix(0.3, 0.7, r4)) * strength;
		vec3 v0 = normalize(up + way * lean + along * (r2 - 0.5) * 0.4) * speed;
		p = o + way * 0.75 * h + along * (r2 - 0.5) * 0.9 + fly(v0, vec3(0.0, -9.8, 0.0), 0.8, tt);
		size = h * mix(0.4, 0.2, r4) * (0.5 + 0.8 * smoothstep(0.0, 0.7, tt / life));
		alpha = 0.95;
	} else if (kind == 2) {
		// mist: big faint puffs that rise off the splash and hang, drifting back out to sea in the offshore wind
		delay = 0.12 + r1 * 0.4;
		tt = max(t - delay, 0.0);
		life = 3.4 + r4 * 1.6;
		vec3 v0 = (up * (1.6 + 1.6 * r3) + way * 0.6) * s * strength;
		vec3 wind = -way * 0.7 + up * 0.12;
		p = o + up * 0.55 * h + way * 0.2 * h + along * (r2 - 0.5) * 1.4 + fly(v0, wind, 0.9, tt);
		size = h * mix(0.55, 0.85, r3) * (0.7 + 0.9 * smoothstep(0.0, 1.0, tt / life));
		alpha = 0.22;
		near = vec2(2.0, 9.0);
		fade_in = 0.12;
		fade_out = 0.55;
		tint = vec3(0.92, 0.96, 1.0);
		spin = (r1 - 0.5) * 0.8 + tt * 0.12 * (r2 - 0.5);
	} else if (kind == 3) {
		// the spit: the closing tube's air blasts spray along it and out of its open end
		delay = 0.06 + r1 * 0.3;
		tt = max(t - delay, 0.0);
		life = 1.3 + r4 * 0.5;
		// (faster than the peel, so it gets out of the tube's open end ahead of the lip: 14 to 22 m/s at a full set,
		// most of it gone in 15 to 20 m)
		vec3 v0 = (along * (14.0 + 8.0 * r2) * s + up * (0.3 + r3 * 0.8) + way * (r3 - 0.5) * 1.2) * strength;
		p = o - way * 0.95 * h + up * 0.42 * h + fly(v0, vec3(0.0, -1.5, 0.0), 1.1, tt);
		size = h * (0.14 + 0.5 * smoothstep(0.0, 1.0, tt / life)) * (0.8 + 0.4 * r4);
		alpha = 0.8 * strength;
		squash = 0.7;
		tint = vec3(0.95, 0.98, 1.0);
	} else if (kind == 4) {
		// the bore: the white water rolls on towards the beach as a tumbling heap, slowing, flattening, breaking up
		// into trails and gone
		delay = r1 * 0.45;
		tt = max(t - delay, 0.0);
		life = 3.4 + r4 * 1.4;
		float c = 3.4 * s * (0.8 + 0.4 * r3);
		float k = 0.42;
		float run = c * (1.0 - exp(-k * tt)) / k;
		float sinks = smoothstep(0.0, 1.0, tt / life);
		p = o + way * (0.3 * h + run) + along * (r2 - 0.5) * 1.5 + up * (0.14 * h * (1.0 - sinks) + 0.05 * h * sin(tt * 3.0 + r4 * 6.3) - 0.05 * h);
		// (a low heap, wider than it is high, lower still as it thins)
		size = h * mix(0.28, 0.42, r4) * (0.5 + 0.7 * smoothstep(0.0, 0.8, tt)) * (1.0 + 0.4 * sinks);
		squash = mix(0.7, 0.3, smoothstep(0.2, 1.0, tt / life));
		near = vec2(2.0, 9.0);
		cut = smoothstep(0.4, 1.0, tt / life);
		spin = r1 * 6.2832 + tt * (1.2 + r3) * (1.0 - 0.7 * sinks);
		alpha = 0.97;
		fade_in = 0.1;
		fade_out = 0.2;
		// (its front shaded blue-grey under the white, as the concept's rolling foam, so the heap reads over the flat foam)
		tint = mix(mix(vec3(0.8, 0.88, 0.93), vec3(1.0), r3), vec3(0.86, 0.93, 0.97), sinks);
	} else if (kind == 5) {
		// the air trapped under the lip bursts out on the wave's back, half a second later
		delay = 0.45 + r1 * 0.35;
		tt = max(t - delay, 0.0);
		life = 1.0 + r2 * 0.5;
		vec3 v0 = (up * (2.2 + 1.8 * r3) - way * 0.8 + along * (r2 - 0.5)) * s * strength;
		p = o - way * 1.25 * h + up * 0.5 * h + along * (r4 - 0.5) * 1.0 + fly(v0, vec3(0.0, -5.0, 0.0), 1.1, tt);
		size = h * mix(0.2, 0.32, r4) * (0.5 + 0.7 * smoothstep(0.0, 0.7, tt / life));
		alpha = 0.85;
	} else {
		// bubbles: driven down and forward under the landing, turning in a vortex round the line it landed on, then
		// rising and fading
		air = false;
		delay = r1 * 0.25;
		tt = max(t - delay, 0.0);
		life = 2.4 + r2 * 0.9;
		vec3 c = o + way * (-0.35 * h + 2.2 * s * (1.0 - exp(-0.7 * tt))) - up * (0.2 * h + 0.35 * h * (1.0 - exp(-1.6 * tt)))
				+ along * (r2 - 0.5) * 1.4;
		float a = r3 * 6.2832 + 3.2 * (1.0 - exp(-0.6 * tt)) / 0.6;
		float rad = 0.3 * h * (0.35 + 0.65 * r4) * (0.5 + 0.6 * smoothstep(0.0, 1.5, tt));
		p = c + way * cos(a) * rad + up * sin(a) * rad + up * 0.35 * pow(max(tt - 1.0, 0.0), 1.5);
		// (between the surface and the sand: a barrel breaks in water little deeper than it is high)
		p.y = clamp(p.y, min(bed + 0.25 + 0.3 * r4, o.y - 0.12 * h - 0.05), o.y - 0.12 * h);
		size = h * mix(0.22, 0.38, r4) * (0.6 + 0.7 * smoothstep(0.0, 1.0, tt / life));
		alpha = 0.72;
		tint = vec3(0.82, 0.94, 1.0);
		cut = smoothstep(0.5, 1.0, tt / life) * 0.7;
	}
	// (the white water low by the sea is greener, lit through the water it is made of; white higher up: the concept's
	// painted spray)
	if (air && kind != 2) {
		tint *= mix(vec3(0.78, 0.93, 0.9), vec3(1.0), smoothstep(o.y - 0.1 * h, o.y + 0.6 * h, p.y));
	}
	// (the splashes fall back into the water, not through it)
	if (air && kind != 4) {
		alpha *= 1.0 - smoothstep(o.y - 0.05 * h, o.y - 0.3 * h, p.y);
	}
	float f = tt / life;
	alpha *= smoothstep(0.0, fade_in, tt) * (1.0 - smoothstep(1.0 - fade_out, 1.0, f));
	bool on = t >= delay && f < 1.0 && strength > 0.0 && (air == (under < 0.5));
	vec3 c_view = (VIEW_MATRIX * vec4(p, 1.0)).xyz;
	// (gone right at the eye, so a puff blown past the camera never fills the screen)
	alpha *= smoothstep(near.x, near.y, -c_view.z);
	vec2 q = VERTEX.xy;
	float cs = cos(spin);
	float sn = sin(spin);
	q = vec2(q.x * cs - q.y * sn, q.x * sn + q.y * cs);
	q.y *= squash;
	VERTEX = c_view + vec3(q * (on ? size : 0.0), 0.0);
	v_tint = vec4(tint * lit, on ? alpha : 0.0);
	v_cut = cut;
	v_seed = r2 * 7.0;
}

float vnoise(vec2 x) {
	vec2 i = floor(x);
	vec2 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash1(dot(i, vec2(1.0, 57.0)));
	float b = hash1(dot(i + vec2(1.0, 0.0), vec2(1.0, 57.0)));
	float c = hash1(dot(i + vec2(0.0, 1.0), vec2(1.0, 57.0)));
	float d = hash1(dot(i + vec2(1.0, 1.0), vec2(1.0, 57.0)));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void fragment() {
	vec4 tex = texture(puff, UV);
	float a = tex.a * v_tint.a;
	// (white water thinning: holes eaten into the puff, so a heap breaks up into trails)
	if (v_cut > 0.0) {
		float n = vnoise(UV * 5.0 + v_seed) * 0.65 + vnoise(UV * 11.0 + v_seed * 1.3) * 0.35;
		a *= smoothstep(v_cut - 0.08, v_cut + 0.08, n);
	}
	if (a < 0.01) {
		discard;
	}
	ALBEDO = tex.rgb * v_tint.rgb;
	ALPHA = a;
}
