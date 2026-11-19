shader_type spatial;
// The comb jelly (comb_jelly.gd): a clear lobed body, its eight comb rows beating in waves and scattering running
// rainbow light, drawn here (no texture files). What each point is comes from the model (tools/build_comb_jelly.py):
// UV2.y the part (0 the outer skin, 1 the lobes' edges and their inner skin, to the mouth); UV2.x how much of a comb
// row's ridge the point is on (the full model's ridges; 0 elsewhere). UV.y how far along: 0 the aboral end .. 1 the
// lobes' edge, then 1 .. 2 back down the inside to the mouth.
//
// It swims mouth first: the lobes are ahead (-Z), above and below (+Y, -Y). It is drawn see-through (alpha blended,
// back faces culled, so at most the near skin and the inside of the far lobe show: one or two layers). What lights up
// (EMISSION): the comb rows, in rainbow bands that run along them from the aboral end towards the lobes as the plates
// beat; a faint blue glow at its edges where the skin turns away; the statocyst, a small bright dot at the aboral
// end. Everything that moves goes by `phase` alone, so it loops. Nothing here needs more than GL Compatibility has.
render_mode blend_mix, cull_back, depth_draw_opaque, vertex_lighting;

// Kept in step with the model.
const float RX = 0.0185;
const float RY = 0.0265;
const float LENGTH = 0.1;
const float ROW_FROM = 0.1;

// How far through a beat (0..1, it wraps). Set by CombJelly.
uniform float phase = 0.0;
// Waves that pass along the comb rows in a beat (a whole number, so that it comes round).
uniform float rounds = 2.0;
// How much it moves: 1 its plates beating and its lobes swaying gently, 0 still (as built), 2 twice as much.
uniform float sway = 1.0;
// Turning: how far the body is bent round behind the lobes, radians from the lobes to the aboral end (more than 0
// the aboral end comes round to +X).
uniform float curl = 0.0;
// How strongly it shines (0 none, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;
// How clear it is (0 nearly invisible but for its rows and edges, 1 as made, 2 cloudier).
uniform float cloudy : hint_range(0.0, 2.0) = 1.0;
// Its tint, the lobes' inner tint, the glow at its edges, the statocyst.
uniform vec3 body : source_color = vec3(0.78, 0.88, 0.95);
uniform vec3 inside : source_color = vec3(0.92, 0.8, 0.88);
uniform vec3 edge_colour : source_color = vec3(0.45, 0.75, 1.0);
uniform vec3 statocyst : source_color = vec3(0.9, 1.0, 0.85);

varying float part;
varying float along;
varying float ridge_is;
varying vec3 rest;

vec3 rainbow(float h) {
	return clamp(abs(mod(h * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.03;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.8 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float s = sin(a);
	n = vec3(n.x * c + n.z * s, n.y, -n.x * s + n.z * c);
	v = vec3(r - (r - v.x) * c, v.y, from + (r - v.x) * s);
}

// The metachronal wave on the comb rows at `z`: 1 where the plates are beating now. It runs from the aboral end
// towards the lobes.
float beating(float z) {
	return 0.5 + 0.5 * sin(6.2831853 * (rounds * phase + z / 0.018));
}

void vertex() {
	part = UV2.y;
	along = UV.y;
	ridge_is = UV2.x;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	// The plates beat: the ridge stands up and lies down in the wave.
	v += n * 0.00035 * sway * UV2.x * (beating(v.z) - 0.5);
	// The lobes open and close a little.
	float lobe = smoothstep(-0.012, -0.045, v.z);
	v.y *= 1.0 + 0.07 * sway * lobe * sin(6.2831853 * phase);
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	float glance = 1.0 - clamp(abs(dot(normalize(NORMAL), normalize(VIEW))), 0.0, 1.0);
	float a = atan(rest.x / RX, rest.y / RY);
	float w = length(rest.xy / vec2(RX, RY));
	// (radians to the nearest comb row: they are at an eighth of a half turn and every quarter of a half turn on)
	float off = mod(a, 0.7853982) - 0.3926991;
	float row_angle = a - off;
	float reach = abs(cos(row_angle)) > 0.5 ? 0.93 : 0.68;
	float across = off * w * 0.5 * (RX + RY);
	float on_row = (1.0 - smoothstep(0.0007, 0.0015, abs(across))) * smoothstep(ROW_FROM - 0.02, ROW_FROM + 0.02, along) * (1.0 - smoothstep(reach - 0.05, reach, along)) * step(part, 0.5);
	// the comb plates: short bars across the row, one every 1.7 mm
	float plate = smoothstep(0.15, 0.45, abs(fract(rest.z / 0.0017) - 0.5) * 2.0);
	float beat = beating(rest.z);
	// the rainbow: bands that run along the row with the wave, shifting as the light glances off
	vec3 bands = rainbow(fract(rest.z / 0.025 + rounds * phase + glance * 0.6 + float(int(row_angle * 1.27)) * 0.13));
	vec3 c;
	float alpha;
	vec3 e = vec3(0.0);
	if (part < 0.5) {
		c = body;
		alpha = (0.1 + 0.45 * glance * glance) * cloudy;
		// (the outer skin a little milkier towards the aboral end)
		alpha += 0.06 * (1.0 - smoothstep(0.0, 0.5, along)) * cloudy;
		e = edge_colour * 0.25 * glance * glance;
		float st = 1.0 - smoothstep(0.0012, 0.0025, length(rest.xy)) ;
		st *= step(along, 0.06);
		e += statocyst * st * 1.2;
		alpha = max(alpha, st * 0.9);
	} else {
		c = inside;
		alpha = (0.06 + 0.3 * glance * glance) * cloudy;
		// (the lobes' edges a little brighter)
		float rim = 1.0 - smoothstep(0.0, 0.15, abs(along - 1.0));
		e = edge_colour * (0.15 * glance * glance + 0.3 * rim);
		alpha += 0.15 * rim;
	}
	float lit = on_row * (0.45 + 0.55 * plate) * (0.3 + 0.7 * beat);
	c = mix(c, bands * 0.6 + 0.4, on_row * 0.6);
	e += bands * lit * 1.6;
	alpha = max(alpha, on_row * (0.35 + 0.4 * beat));
	ALBEDO = c;
	ALPHA = clamp(alpha, 0.0, 1.0);
	ROUGHNESS = 0.15;
	SPECULAR = 0.6;
	EMISSION = e * glow;
}
