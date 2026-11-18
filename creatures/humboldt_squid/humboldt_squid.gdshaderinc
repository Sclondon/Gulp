// The Humboldt squid (humboldt_squid.gd): its mantle breathes in slowly and squeezes quickly, its
// fins flap, every arm and tentacle is laid along its rope (which HumboldtSquid simulates), and
// its skin changes colour. This is the whole shader: humboldt_squid_body.gdshader (solid) and
// humboldt_squid_fins.gdshader (seen from both sides: it defines SQUID_FINS) only choose how it
// is drawn. Built on the giant squid's (godot/giant-squid).
//
// What each point is comes from the model (tools/build_humboldt_squid.py): COLOR.r the part (0
// the mantle, 0.2 a fin, 0.4 the head and siphon, 0.6 an eye, 0.8 the skin of a strand, 1 a
// sucker cup); COLOR.g 1 on a tentacle, and on the head 1 for the bulb of the mouth; COLOR.b
// which strand ((n + 0.5) / 16: arms 0 to 7, tentacles 8 and 9); UV.x round it, UV.y along it;
// UV2.x a strand's length, UV2.y its phase.
//
// THE COLOUR CHANGE. A Humboldt squid's skin is pale (white to pink, with a sheen) under a
// sheet of red-brown colour cells (chromatophores), each a dot that its muscles pull wide open
// (the skin goes deep red) or let shrink to a speck (the skin goes pale). Rosen, Gilly and
// others (2015) filmed two things: FLASHING, the whole body going between red and white 2 to 4
// times a second; and FLICKERING, irregular waves of paler and redder running through
// neighbouring patches of cells. Here every point of the skin has an `open` (0 its cells shut
// to specks, 1 wide open), and the dots are drawn from it: two sizes of dot, and under them the
// wash of red that many layers of open cells make. `open` is worked out from phases that
// HumboldtSquid sets, and nothing else that moves: so it comes round. No texture files.
// Nothing here needs more than GL Compatibility has.

// Kept in step with the model and the script.
const int ARMS = 8;
const int ARM_POINTS = 8;
const int TENTACLE_POINTS = 10;
const float ARM_RING = 0.088;
const float ARM_Z = 0.17;
const float SQUEEZE_AT = 0.62;
const float FIN_FROM = 0.55;
// From the mantle's tip to the arms' tips, in its own space (for the waves that run along it).
const float BODY_FROM = -1.3;
const float BODY_LONG = 2.3;

// Set by HumboldtSquid each frame.
// The ropes: a picture TENTACLE_POINTS wide, a row a strand (as `HumboldtSquid.strands()` lists
// them), each point of it a point of that strand's rope from its root to its tip, in the
// squid's own space. (A picture, not a list of numbers: see the sea nettle's README.)
uniform sampler2D ropes : filter_nearest, repeat_disable;
// How far through a jet (0..1): it breathes in until SQUEEZE_AT, then squeezes.
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of a squid swimming tight rounds: "The squid should bend too"):
// how far the mantle is bent round to one side ahead of the head, in radians from the head to
// its tip (0 straight; more than 0 the tip comes round to +X). The head and the strands stay.
uniform float curl = 0.0;
// How many times the fins flap in a jet (a whole number, so that it comes round).
uniform float fin_ripples = 2.0;
// A light of its own (0 none).
uniform float glow = 0.0;

// Its colours' round (0..1), and what happens in one. Set by HumboldtSquid.
uniform float colour_phase = 0.0;
// How red it is when calm (0 pale, 1 deep red all over).
uniform float redness = 0.82;
// Flashes in a round (a whole number), how pale a flash goes (1: right to white), the share of
// a flash's turn it spends going pale and coming back (the rest it is red), and how much the
// flash is a wave that runs from the mantle's tip to the arms' tips (0: the whole body at once;
// 1: the wave takes a whole turn to cross it).
uniform float flashes = 1.0;
uniform float flash_strength = 1.0;
uniform float flash_share = 0.3;
uniform float flash_wave = 0.2;
// The flicker: how strong (0 none), and how many times its waves come round in a round (a whole
// number).
uniform float flicker = 0.3;
uniform float flicker_rounds = 2.0;
// A flash of its own, now (0..1 pale): `HumboldtSquid.flash()`.
uniform float flash_now = 0.0;

// Its skin: the red of its open colour cells, their darkest, the pale skin under them; its
// suckers; the silver of its eye and its sheen.
uniform vec3 skin : source_color = vec3(0.52, 0.07, 0.055);
uniform vec3 deep : source_color = vec3(0.26, 0.02, 0.03);
uniform vec3 pale : source_color = vec3(0.97, 0.88, 0.86);
uniform vec3 cup : source_color = vec3(0.86, 0.78, 0.84);
uniform vec3 silver : source_color = vec3(0.85, 0.86, 0.9);
// How clear the fins are at their edges (the fins' shader only: a Humboldt's fins are thick).
uniform float fin_alpha = 0.93;
// How big its colour cells are (metres across a cell's place, at size 1).
uniform float cell = 0.016;
// Cartoon eyes: 1 draws each eye as a white ball with a big round black pupil, 0 the dark eye
// with its silver ring of the real animal.
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
	float k = curl / 1.2;
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
		// A fin: it goes with the mantle it is joined to, and flaps: a wave runs back along
		// it, more the further out towards its edge.
		float t = FIN_FROM + (1.0 - FIN_FROM) * uv.y;
		vertex.xy *= mix(swell(t), 1.0, uv.x);
		float side = vertex.x < 0.0 ? 3.14159 : 0.0;
		float wave = sin(6.2831853 * (fin_ripples * phase - uv.y * 0.8) + side);
		vertex.y += wave * 0.11 * uv.x * uv.x * (0.45 + 0.55 * sin(3.14159 * uv.y));
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
			root = vec3(row == ARMS ? 0.032 : -0.032, -0.02, ARM_Z + 0.015);
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

// How pale a flash makes the skin (0..1) at `x` through a flash's turn: red, quickly white,
// quickly red again, then red for the rest of the turn.
float flash_at(float x) {
	x = fract(x) / max(flash_share, 0.001);
	float s = sin(3.14159 * min(x, 1.0));
	return s * s;
}

// How far open the colour cells are at `p`, a point of the skin at rest (0 shut to specks: pale;
// 1 wide open: deep red).
float cells_open(vec3 p) {
	// (how far along it from the mantle's tip to the arms' tips, 0..1)
	float along = clamp((p.z - BODY_FROM) / BODY_LONG, 0.0, 1.0);
	// Calm: patches a hand or two across, each paling and reddening at its own time, the
	// paleness running through neighbours as waves from tail to head.
	float patch = noise3(p * 3.4 + 1.5) + 0.6 * noise3(p * 8.5 + 4.0);
	float turn = 6.2831853 * (flicker_rounds * colour_phase + patch * 1.3 - along * 0.5);
	float open = redness - flicker * (0.5 + 0.5 * sin(turn)) * (0.6 + 0.4 * sin(turn * 0.5 + patch * 9.0));
	// The flash: the whole body to white and back, or sweeping along it as a wave.
	float pale_now = flash_at(flashes * colour_phase - flash_wave * along) * flash_strength;
	pale_now = max(pale_now, flash_now);
	return clamp(mix(open, 0.02, pale_now), 0.0, 1.0);
}

// A sheet of colour cells: how much of the skin at `p` one sheet's dots cover (0..1), its cells
// `size` across and `open` wide. Each cell of space has one dot, set a little off its middle.
float dots(vec3 p, float size, float open) {
	// (the cells' places are turned out of line with the body, or their rows would show)
	vec3 q = vec3(0.36 * p.x + 0.48 * p.y + 0.8 * p.z, -0.8 * p.x + 0.6 * p.y, -0.48 * p.x - 0.64 * p.y + 0.6 * p.z) / size;
	vec3 home = floor(q);
	vec3 middle = home + 0.5 + (vec3(hash3(home), hash3(home + 7.3), hash3(home + 13.7)) - 0.5) * 0.16;
	float wide = (0.1 + 0.36 * open) * (0.8 + 0.4 * hash3(home + 3.1));
	return 1.0 - smoothstep(wide - 0.07, wide, length(q - middle));
}

// The skin at `p` with its cells `open` wide: pale under specks, or red under wide dots.
vec3 skin_of(vec3 p, float open) {
	float big = dots(p, cell, open);
	float small = dots(p.zxy + 0.37, cell * 0.57, open);
	// (many layers of open cells are a red wash over the whole skin; the dots are darker in it)
	float wash = smoothstep(0.12, 0.8, open);
	vec3 c = mix(pale, skin, wash * 0.9);
	c = mix(c, mix(skin, deep, 0.35 + 0.65 * wash), max(big, small * 0.8) * (0.55 + 0.45 * open));
	return c;
}

void fragment() {
	bool front = FRONT_FACING;
	float alpha;
	float rough;
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	// (how far round to its underside this point is: 1 on its back, 0 beneath)
	float above = smoothstep(-0.8, 0.1, normalize(rest_normal).y);
	float open = cells_open(rest);
	vec3 c;
	alpha = 1.0;
	rough = 0.34;
	if (part < 0.1) {
		// (fewer cells beneath: its underside is always the paler)
		c = skin_of(rest, open * (0.62 + 0.38 * above));
	} else if (part < 0.3) {
		// A fin: as the mantle, a little paler towards its edge.
		c = skin_of(rest, open * (0.92 - 0.2 * at.x) * (front ? 1.0 : 0.7));
		alpha = mix(1.0, fin_alpha, smoothstep(0.3, 0.95, at.x));
	} else if (part < 0.5) {
		c = skin_of(rest, open * (0.62 + 0.38 * above));
		if (flag > 0.5) {
			// The mouth: a pale bulb, the dark tip of the beak in the middle of it.
			c = mix(vec3(0.07, 0.04, 0.03), vec3(0.93, 0.88, 0.86), smoothstep(0.3, 0.46, at.x));
			c = mix(c, pale, smoothstep(0.75, 1.0, at.x));
			rough = 0.25;
		}
	} else if (part < 0.7) {
		// An eye: a black pupil, a ring of silver, the lid of skin closing round it.
		float out_from = at.x;
		c = mix(vec3(0.004, 0.005, 0.008), silver * 0.8, smoothstep(0.15, 0.175, out_from));
		c = mix(c, silver * 0.45, smoothstep(0.2, 0.28, out_from));
		c = mix(c, skin_of(rest, open), smoothstep(0.28, 0.33, out_from));
		rough = mix(0.08, 0.34, smoothstep(0.26, 0.34, out_from));
		if (cartoon_eyes > 0.5) {
			c = mix(vec3(0.01, 0.01, 0.015), vec3(0.96, 0.97, 1.0), smoothstep(0.13, 0.15, out_from));
			c = mix(c, skin_of(rest, open), smoothstep(0.33, 0.36, out_from));
			rough = 0.12;
		}
	} else if (part < 0.9) {
		// A strand's skin: its back as the body; its inner, suckered face always pale.
		float inner = 1.0 - smoothstep(0.12, 0.26, abs(at.x - 0.5));
		c = skin_of(rest, open * (1.0 - 0.9 * inner) * (1.0 - 0.3 * flag));
	} else {
		// A sucker cup: pale and a little purple, its toothed ring pale, its hollow dark.
		c = mix(cup, vec3(0.98, 0.96, 0.94), smoothstep(0.5, 0.6, at.x) * (1.0 - smoothstep(0.62, 0.7, at.x)));
		c = mix(c, vec3(0.2, 0.1, 0.16), smoothstep(0.72, 0.95, at.x));
	}
	// (a sheen where the skin turns away from the eye; more of it shows when it is pale)
	c = mix(c, silver, (0.16 + 0.2 * (1.0 - open)) * pow(edge, 2.2) * (part > 0.5 && part < 0.7 ? 0.0 : 1.0));
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.5;
	EMISSION = c * glow * (0.3 + 0.5 * edge);
#ifdef SQUID_FINS
	ALPHA = alpha;
#endif
}
