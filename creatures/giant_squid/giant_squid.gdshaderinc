// The giant squid (giant_squid.gd): its mantle breathes in slowly and squeezes quickly, its fins
// ripple, and every arm and tentacle is laid along its rope, which GiantSquid simulates. This is
// the whole shader: giant_squid_body.gdshader (solid) and giant_squid_fins.gdshader (a little
// clear: it defines SQUID_FINS) only choose how it is drawn.
//
// What each point is comes from the model (tools/build_giant_squid.py): COLOR.r the part (0 the
// mantle, 0.2 a fin, 0.4 the head and siphon, 0.6 an eye, 0.8 the skin of a strand, 1 a sucker
// cup); COLOR.g 1 on a tentacle; COLOR.b which strand ((n + 0.5) / 16: arms 0 to 7, tentacles
// 8 and 9); UV.x round it, UV.y along it; UV2.x a strand's length, UV2.y its phase. On the game
// model (giant_squid_game.glb) UV2.y is 2 more than the phase on its strands: it has no sucker cups
// of its own, and they are painted here where the full model has them.
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
// Cartoon eyes (the user, 2026-11-17: "His eyes should be cartoonish and bigger too"; and 2026-11-18:
// "the eyes for most of them should be more cartoony and personalized"): 0 the black-and-silver eye
// of the real animal; 1 bigger still, a white ball, a deep blue iris round a huge round pupil, two
// glints, a dark outline, and no lid in sight: a wide, awed stare, a gentle giant. Where they look
// (x towards its arms, y up its back, -1..1), and how shut its lids are (0 open, 1 shut).
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
uniform vec3 cartoon_iris : source_color = vec3(0.12, 0.3, 0.62);
// The eye's middle (+X side), its radius across its face, and how much bigger the cartoon eye is.
const vec3 EYE = vec3(0.175, 0.03, -0.02);
const float EYE_R = 0.2686;
const float CARTOON_EYE = 1.3;

varying float part;
varying float flag;
varying vec2 at;
varying float long_is;
varying vec3 rest;
varying vec3 rest_normal;
varying float painted;
varying float row_is;

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
	painted = uv2.y > 1.5 ? 1.0 : 0.0;
	row_is = floor(colour.b * 16.0);
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
	} else if (part > 0.5) {
		// An eye: bigger, about its own middle, as it turns cartoon.
		vec3 centre = vec3(vertex.x < 0.0 ? -EYE.x : EYE.x, EYE.y, EYE.z);
		vertex = centre + (vertex - centre) * mix(1.0, CARTOON_EYE, cartoon_eyes);
	}
	if (part < 0.7) {
		curl_bend(vertex, normal);
	}
	VERTEX = vertex;
	NORMAL = normal;
}

// The game model's sucker cups, painted where the full model has them (suckers() in the build
// script): how far the point `s` along strand `row` and `around` round it is from the middle of the
// nearest cup, in that cup's radii (more than 1: no cup here).
float painted_cup(int row, float s, float around) {
	float best = 9.0;
	if (row < ARMS) {
		// (two rows of 30 down an arm)
		float r_arm = (0.074 * pow(max(1.0 - s, 0.0), 0.8) + 0.005) * 1.4;
		float size = max(0.4 * r_arm, 0.004);
		float x = pow(clamp((s - 0.05) / 0.9, 0.0, 1.0), 1.0 / 0.85) * 30.0;
		for (int k = 0; k < 2; k++) {
			float i = clamp(round(x - 0.5 * float(k)), 0.0, 29.0);
			float si = 0.05 + 0.9 * pow((i + 0.5 * float(k)) / 30.0, 0.85);
			float across = (around - 0.5 - (k == 1 ? 0.085 : -0.085)) * 6.2831853 * r_arm;
			best = min(best, length(vec2(across, (s - si) * long_is)) / size);
		}
		return best;
	}
	float club = smoothstep(0.87, 0.91, s) * (1.0 - smoothstep(0.95, 1.0, s));
	float r_t = (0.021 - 0.006 * s + 0.02 * club - 0.012 * smoothstep(0.97, 1.0, s)) * 1.4;
	// (a few small ones up the stalk, alternating sides)
	float j = clamp(round((s - 0.5) / 0.035), 0.0, 9.0);
	float side = mod(j, 2.0) > 0.5 ? 0.05 : -0.05;
	best = length(vec2((around - 0.5 - side) * 6.2831853 * r_t, (s - 0.5 - 0.035 * j) * long_is)) / 0.005;
	// (the club: four rows of 12, the middle two the biggest)
	for (int k = 0; k < 4; k++) {
		float odd = float(k % 2);
		float where = k == 0 ? 0.36 : (k == 1 ? 0.455 : (k == 2 ? 0.545 : 0.64));
		float big = (k == 0 || k == 3) ? 0.6 : 1.0;
		float i = clamp(round((s - 0.885) / 0.085 * 12.0 - 0.5 * odd), 0.0, 11.0);
		float si = 0.885 + 0.085 * (i + 0.5 * odd) / 12.0;
		float size = 0.0135 * big * (0.55 + 0.45 * pow(sin(3.14159 * (i + 0.5) / 12.0), 0.6));
		float across = (around - where) * 6.2831853 * r_t;
		best = min(best, length(vec2(across, (s - si) * long_is)) / size);
	}
	return best;
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
		// (the eye's own frame: x towards its arms, y up its back; `pos` the point in it, 1 about
		// where the cartoon eye's white ends)
		vec2 e = vec2(rest.z - EYE.z, rest.y - EYE.y) / EYE_R;
		vec2 way = length(e) > 1e-5 ? normalize(e) : vec2(0.0);
		// (measured from its place, not its UV, so that its rings are round however few its points;
		// past the side of the ball, where that fails, it is far out)
		vec2 pos = way * (at.x < 0.45 ? asin(min(length(e), 1.0)) / 3.14159 : 0.8) / 0.4;
		// (`eye_look` slides its pupil that way)
		vec2 seen = e - eye_look * 0.12;
		float out_from = at.x + (asin(min(length(seen), 1.0)) - asin(min(length(e), 1.0))) / 3.14159 * (1.0 - smoothstep(0.3, 0.45, at.x));
		c = mix(vec3(0.004, 0.005, 0.008), silver * 0.75, smoothstep(0.18, 0.205, out_from));
		c = mix(c, silver * vec3(0.9, 0.55, 0.45), smoothstep(0.22, 0.3, out_from));
		c = mix(c, mix(skin, deep, 0.4 + 0.4 * dark), smoothstep(0.29, 0.34, at.x));
		rough = mix(0.08, 0.38, smoothstep(0.26, 0.34, at.x));
		if (cartoon_eyes > 0.0) {
			// The cartoon eye: a white ball, a deep blue iris round a huge round pupil, two glints
			// up and towards its arms that stay put, a dark outline, no lid: a wide, awed stare.
			vec2 ei = pos - eye_look * 0.28;
			float ir = length(ei);
			float er = length(pos);
			vec3 k = vec3(0.96, 0.97, 1.0);
			k = mix(k, mix(cartoon_iris * 1.25, cartoon_iris * 0.6, smoothstep(0.36, 0.56, ir)), 1.0 - smoothstep(0.54, 0.58, ir));
			k = mix(k, vec3(0.03, 0.06, 0.14), (1.0 - smoothstep(0.015, 0.035, abs(ir - 0.56))) * 0.8);
			k = mix(vec3(0.01, 0.01, 0.015), k, smoothstep(0.35, 0.38, ir));
			float shine = 1.0 - smoothstep(0.08, 0.11, length(pos - vec2(0.22, 0.28)));
			shine = max(shine, 1.0 - smoothstep(0.035, 0.055, length(pos - vec2(0.37, 0.12))));
			k = mix(k, vec3(1.0), shine);
			k = mix(k, vec3(0.1, 0.02, 0.03), smoothstep(0.76, 0.8, er));
			k = mix(k, mix(skin, deep, 0.5), smoothstep(0.84, 0.88, er));
			c = mix(c, k, cartoon_eyes);
			rough = mix(rough, mix(0.1, 0.38, smoothstep(0.76, 0.88, er)), cartoon_eyes);
		}
		// The lids (none to be seen open): `blink` brings the upper one down to meet the lower.
		float open_at = blink > 0.0 ? 0.95 : 2.5;
		float lid_at = mix(open_at, -0.15, blink);
		float low_at = mix(-open_at, -0.15, blink);
		float lids = max(smoothstep(lid_at - 0.02, lid_at + 0.02, pos.y), 1.0 - smoothstep(low_at - 0.02, low_at + 0.02, pos.y));
		c = mix(c, mix(skin, deep, 0.4 + 0.4 * dark), lids);
		rough = mix(rough, 0.38, lids);
	} else if (part < 0.9) {
		// A strand's skin: red on its outer face, pale down its inner, suckered face.
		float inner = 1.0 - smoothstep(0.1, 0.3, abs(at.x - 0.5));
		c = mix(skin, belly, inner * 0.85);
		c = mix(c, deep, dark * (0.55 - 0.4 * inner));
		// (a tentacle's stalk is paler than an arm)
		c = mix(c, belly, 0.25 * flag * (1.0 - inner));
		if (painted > 0.5) {
			// The game model's cups (as a cup of the full model, below): pale, the rim a little
			// red, the hollow dark; a little shadow round each.
			float n = painted_cup(int(row_is), at.y, at.x);
			vec3 k = mix(cup, skin, 0.35 * smoothstep(0.85, 0.95, n));
			k = mix(deep * 0.6, k, smoothstep(0.35, 0.5, n));
			c = mix(c * 0.72, c, smoothstep(1.0, 1.25, n));
			c = mix(c, k, 1.0 - smoothstep(0.92, 1.0, n));
		}
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
