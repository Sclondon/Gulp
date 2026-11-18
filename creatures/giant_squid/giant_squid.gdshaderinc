// The giant squid (giant_squid.gd): its mantle breathes in slowly and squeezes quickly, its fins
// ripple, and every arm and tentacle is laid along its rope, which GiantSquid simulates. This is
// the whole shader: giant_squid_body.gdshader (solid) and giant_squid_fins.gdshader (a little
// clear: it defines SQUID_FINS) only choose how it is drawn.
//
// What each point is comes from the model (tools/build_giant_squid.py): COLOR.r the part (0 the
// mantle, 0.2 a fin, 0.4 the head and siphon, 0.6 an eye, 0.8 the skin of a strand, 1 a sucker
// cup); COLOR.g 1 on a tentacle; COLOR.b which strand ((n + 0.5) / 16: arms 0 to 7, tentacles
// 8 and 9); UV.x round it, UV.y along it; UV2.x a strand's length, UV2.y its phase.
//
// Its skin is drawn here (no texture files): deep red to maroon above, paler beneath, mottled
// and speckled with its colour cells, a faint silver where it turns from the eye. Nothing here
// needs more than GL Compatibility has.

// Kept in step with the model and the script.
const int ARMS = 8;
const int ARM_POINTS = 10;
const int TENTACLE_POINTS = 14;
const float ARM_RING = 0.15;
const float ARM_Z = 0.3;
const float SQUEEZE_AT = 0.62;

// Set by GiantSquid each frame.
// The ropes: a picture TENTACLE_POINTS wide, a row a strand (as `GiantSquid.strands()` lists
// them), each point of it a point of that strand's rope from its root to its tip, in the
// squid's own space. (A picture, not a list of numbers: see the sea nettle's README.)
uniform sampler2D ropes : filter_nearest, repeat_disable;
// How far through a jet (0..1): it breathes in until SQUEEZE_AT, then squeezes.
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of a squid swimming tight rounds: "The squid should bend too"):
// how far the mantle is bent round to one side ahead of the head, in radians from the head to
// its tip (0 straight; more than 0 the tip comes round to +X). The head and the strands stay.
uniform float curl = 0.0;
// How many times the fins ripple in a jet (a whole number, so that it comes round).
uniform float fin_ripples = 2.0;
// A light of its own (0 none).
uniform float glow = 0.0;
// Its skin: above, in its darker mottles, beneath; its suckers; the silver of its eye.
uniform vec3 skin : source_color = vec3(0.56, 0.1, 0.085);
uniform vec3 deep : source_color = vec3(0.24, 0.03, 0.045);
uniform vec3 belly : source_color = vec3(0.93, 0.7, 0.66);
uniform vec3 cup : source_color = vec3(0.97, 0.86, 0.82);
uniform vec3 silver : source_color = vec3(0.85, 0.84, 0.8);
// How clear the fins are at their edges (the fins' shader only).
uniform float fin_alpha = 0.72;
// Cartoon eyes (the user, 2026-11-17: "His eyes should be cartoonish and bigger too"): 1 draws each
// eye as a white ball with a big round black pupil and a white glint, 0 the black-and-silver eye
// of the real animal.
uniform float cartoon_eyes = 0.0;

varying float part;
varying float flag;
varying vec2 at;
varying float long_is;
varying vec3 rest;
varying vec3 rest_normal;

// How full of water the mantle is, through a jet (0..1): filling slowly, emptied quickly.
float fullness(float x) {
	x = fract(x);
	float through = x < SQUEEZE_AT ? 0.5 * x / SQUEEZE_AT : 0.5 + 0.5 * (x - SQUEEZE_AT) / (1.0 - SQUEEZE_AT);
	return 0.5 - 0.5 * cos(through * 6.2831853);
}

// How much wider the mantle is than at rest, `t` from its collar (0) to its tip (1): it swells
// most a third of the way back, its collar gapes as it fills, and the squeeze runs back
// along it.
float swell(float t) {
	float full = fullness(phase - 0.12 * t);
	float where = pow(1.0 - t, 0.7) * (0.55 + 0.45 * smoothstep(0.0, 0.3, t));
	float gape = (1.0 - smoothstep(0.0, 0.1, t)) * 0.07 * fullness(phase + 0.08);
	return 1.0 + (0.11 * full - 0.05) * where + gape;
}

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

// Smooth noise, 0..1.
float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(
			mix(mix(hash3(i), hash3(i + vec3(1.0, 0.0, 0.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 0.0)), hash3(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
			mix(mix(hash3(i + vec3(0.0, 0.0, 1.0)), hash3(i + vec3(1.0, 0.0, 1.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 1.0)), hash3(i + vec3(1.0, 1.0, 1.0)), f.x), f.y),
			f.z);
}

// The mantle and its fins laid round an arc ahead of the head (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.08;
	float d = from - v.z;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / 2.0;
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c - n.z * sn, n.y, n.x * sn + n.z * c);
	v = vec3(r - (r - v.x) * c, v.y, from - (r - v.x) * sn);
}

void vertex() {
	vec3 vertex = VERTEX;
	vec3 normal = NORMAL;
	vec4 colour = COLOR;
	vec2 uv = UV;
	vec2 uv2 = UV2;
	part = colour.r;
	flag = colour.g;
	at = uv;
	long_is = uv2.x;
	rest = vertex;
	rest_normal = normal;
	if (part < 0.1) {
		// The mantle: breathing.
		vertex.xy *= swell(uv.y);
	} else if (part < 0.3) {
		// A fin: it goes with the mantle it is joined to, and a wave runs back along it, more
		// the further out towards its edge.
		float t = 0.64 + 0.36 * uv.y;
		vertex.xy *= mix(swell(t), 1.0, uv.x);
		float side = vertex.x < 0.0 ? 3.14159 : 0.0;
		float wave = sin(6.2831853 * (fin_ripples * phase - uv.y * 1.15) + side);
		vertex.y += wave * 0.085 * uv.x * uv.x * (0.5 + 0.5 * sin(3.14159 * uv.y));
		normal = normalize(normal + vec3(sign(vertex.x) * -wave * 0.45 * uv.x, 0.0, 0.0));
	} else if (part > 0.7) {
		// A strand: where this point is along its rope, and its offset from the strand's own
		// middle line (straight back from its root, as the model has it) turned to lie the
		// way the rope runs there.
		float s = uv.y;
		float long = uv2.x;
		int row = int(floor(colour.b * 16.0));
		bool arm = row < ARMS;
		int count = arm ? ARM_POINTS : TENTACLE_POINTS;
		vec3 root;
		if (arm) {
			float a = (float(row) + 0.5) * 0.7853982;
			root = vec3(cos(a) * ARM_RING, sin(a) * ARM_RING, ARM_Z);
		} else {
			root = vec3(row == ARMS ? 0.05 : -0.05, -0.035, ARM_Z + 0.02);
		}
		vec3 offset = vertex - (root + vec3(0.0, 0.0, s * long));
		float f = clamp(s, 0.0, 1.0) * float(count - 1);
		int i1 = min(int(f), count - 2);
		float t = f - float(i1);
		vec3 p0 = texelFetch(ropes, ivec2(max(i1 - 1, 0), row), 0).xyz;
		vec3 p1 = texelFetch(ropes, ivec2(i1, row), 0).xyz;
		vec3 p2 = texelFetch(ropes, ivec2(i1 + 1, row), 0).xyz;
		vec3 p3 = texelFetch(ropes, ivec2(min(i1 + 2, count - 1), row), 0).xyz;
		// (a smooth curve through the points)
		vec3 c1 = p2 - p0;
		vec3 c2 = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3;
		vec3 c3 = 3.0 * (p1 - p2) + p3 - p0;
		vec3 on_line = 0.5 * (2.0 * p1 + c1 * t + c2 * t * t + c3 * t * t * t);
		vec3 way = normalize(0.5 * (c1 + 2.0 * c2 * t + 3.0 * c3 * t * t) + vec3(0.0, 0.0, 0.0001));
		// (the smallest turn that takes straight back to the way the rope runs; where a strand
		// starts, inside the head, it stays as the head has it)
		vec3 w = cross(vec3(0.0, 0.0, 1.0), way);
		float c = max(way.z, -0.98);
		float follows = smoothstep(0.0, 0.03, s);
		offset += (cross(w, offset) + cross(w, cross(w, offset)) / (1.0 + c)) * follows;
		normal = normalize(normal + (cross(w, normal) + cross(w, cross(w, normal)) / (1.0 + c)) * follows);
		vertex = on_line + offset;
	}
	if (part < 0.7) {
		curl_bend(vertex, normal);
	}
	VERTEX = vertex;
	NORMAL = normal;
}

// The colour cells of its skin at `p` (a point of it at rest): how dark (0..1). Blotches a
// hand across, and fine specks.
float mottle(vec3 p) {
	float blotch = noise3(p * 7.0 + 3.0) * 0.65 + noise3(p * 17.0) * 0.35;
	float speck = noise3(p * 95.0);
	return clamp(smoothstep(0.42, 0.7, blotch) * 0.75 + smoothstep(0.62, 0.8, speck) * 0.5, 0.0, 1.0);
}

void fragment() {
	bool front = FRONT_FACING;
	float alpha;
	float rough;
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	float dark = mottle(rest);
	// (how far round to its underside this point is: 1 on its back, 0 beneath)
	float above = smoothstep(-0.75, 0.15, normalize(rest_normal).y);
	vec3 c;
	alpha = 1.0;
	rough = 0.38;
	if (part < 0.1) {
		c = mix(belly, skin, above);
		c = mix(c, deep, dark * (0.35 + 0.5 * above));
	} else if (part < 0.3) {
		// A fin: thinner, so paler and a little clear towards its edge, fine rays running out.
		float rays = 0.5 + 0.5 * sin(at.y * 150.0 + at.x * 9.0);
		c = mix(skin, belly, 0.35 + 0.35 * at.x);
		c = mix(c, deep, dark * 0.3 + 0.12 * rays * at.x);
		alpha = mix(1.0, fin_alpha, smoothstep(0.1, 0.8, at.x));
		if (!front) {
			c = mix(c, belly, 0.3);
		}
	} else if (part < 0.5) {
		c = mix(belly, skin, above);
		c = mix(c, deep, dark * (0.3 + 0.45 * above));
	} else if (part < 0.7) {
		// An eye: a great black pupil, a ring of silver, the red lid closing round it.
		float out_from = at.x;
		c = mix(vec3(0.004, 0.005, 0.008), silver * 0.75, smoothstep(0.18, 0.205, out_from));
		c = mix(c, silver * vec3(0.9, 0.55, 0.45), smoothstep(0.22, 0.3, out_from));
		c = mix(c, mix(skin, deep, 0.4 + 0.4 * dark), smoothstep(0.29, 0.34, out_from));
		rough = mix(0.08, 0.38, smoothstep(0.26, 0.34, out_from));
		if (cartoon_eyes > 0.5) {
			c = mix(vec3(0.01, 0.01, 0.015), vec3(0.96, 0.97, 1.0), smoothstep(0.13, 0.15, out_from));
			c = mix(c, mix(skin, deep, 0.5), smoothstep(0.33, 0.36, out_from));
			rough = 0.12;
		}
	} else if (part < 0.9) {
		// A strand's skin: red on its outer face, pale down its inner, suckered face.
		float inner = 1.0 - smoothstep(0.1, 0.3, abs(at.x - 0.5));
		c = mix(skin, belly, inner * 0.85);
		c = mix(c, deep, dark * (0.55 - 0.4 * inner));
		// (a tentacle's stalk is paler than an arm)
		c = mix(c, belly, 0.25 * flag * (1.0 - inner));
	} else {
		// A sucker cup: pale, its rim a little red, its hollow dark.
		c = mix(cup, skin, 0.35 * smoothstep(0.5, 0.62, at.x) * (1.0 - smoothstep(0.62, 0.7, at.x)));
		c = mix(c, deep * 0.6, smoothstep(0.72, 0.95, at.x));
	}
	// (a silver film where the skin turns away from the eye, as living ones have)
	c = mix(c, silver, 0.32 * pow(edge, 2.2) * (part > 0.5 && part < 0.7 ? 0.0 : 1.0));
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.45;
	EMISSION = c * glow * (0.3 + 0.5 * edge);
#ifdef SQUID_FINS
	ALPHA = alpha;
#endif
}
