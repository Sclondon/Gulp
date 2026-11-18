// The giant Pacific octopus (giant_pacific_octopus.gd): its mantle breathes in slowly and
// squeezes quickly, every arm is laid along its rope (which GiantPacificOctopus simulates), the
// web is hung between each arm and the next, and its skin is drawn: brick red to rust with paler
// mottling, its suckers and the inner faces of its arms pale, its eyes gold with a level slit of a
// pupil that stays level with the world, however the octopus is turned (as a living one's does).
// No texture files; nothing here needs more than GL Compatibility has. One opaque draw, back
// faces culled (the web is two sheets back to back in the model).
//
// What each point is comes from the model (tools/build_giant_pacific_octopus.py): COLOR.r the part
// (0 the mantle, 0.2 the web, 0.4 the head and siphon, 0.6 an eye, 0.8 an arm's skin, 1 a sucker);
// COLOR.g on the web 0 the sheet that looks out and 1 the one that looks in, on the head 1 for the
// mouth; COLOR.b on an arm, a sucker or the web which arm ((n + 0.5) / 16), on the mantle and head
// 1 at a papilla's point. UV.x round it (the web: 0 at its own arm to 1 at the next; an arm: 0.5
// down the middle of its suckered face); UV.y along it (the mantle: collar 0 to tip 1; an arm or
// the web: root 0 to tip 1); UV2.x an arm's length, UV2.y its phase. On the game model
// (giant_pacific_octopus_game.glb) COLOR.g is 1 on an arm's skin: it has no suckers of its own, and
// they are painted here where the full model has them.
shader_type spatial;
render_mode cull_back;

// Kept in step with the model and the script.
const int ARMS = 8;
const int ARM_POINTS = 14;
const float ARM_RING = 0.09;
const float ARM_Z = 0.13;
const float SQUEEZE_AT = 0.6;
const vec3 EYE = vec3(0.074, 0.092, 0.0);
const vec3 EYE_OUT = vec3(0.7509, 0.6608, 0.0);

// The ropes: a picture ARM_POINTS wide, a row an arm, each point of it a point of that arm's rope
// from its root to its tip, in the octopus's own space. Set by GiantPacificOctopus.
uniform sampler2D ropes : filter_nearest, repeat_disable;
// How far through a jet (0..1): it breathes in until SQUEEZE_AT, then squeezes.
uniform float phase = 0.0;
// How much its mantle breathes (1 jetting; less settled).
uniform float breathe = 1.0;
// Settled (0..1): only to keep the web slack as the arms spread.
uniform float sit = 0.0;
// Roused: dark red all over, its mottling gone (0..1).
uniform float blush = 0.0;
// A flash of its own, now (0..1 pale): `flash()`.
uniform float flash_now = 0.0;
// How strongly its paler mottling shows.
uniform float mottle = 1.0;

uniform vec3 skin : source_color = vec3(0.47, 0.12, 0.07);
uniform vec3 rust : source_color = vec3(0.56, 0.26, 0.11);
uniform vec3 dark : source_color = vec3(0.24, 0.035, 0.03);
uniform vec3 pale : source_color = vec3(0.86, 0.6, 0.5);
uniform vec3 under : source_color = vec3(0.86, 0.68, 0.6);
uniform vec3 sucker : source_color = vec3(0.95, 0.86, 0.78);
uniform vec3 iris : source_color = vec3(0.78, 0.56, 0.2);

// Cartoon eyes (0 its own eye; 1 bigger, a cream white, a gold iris, a level bar of a pupil, a
// highlight, a dark outline and a heavy, knowing upper lid), where they look (x towards its arms,
// y up its back, -1..1), and how shut its lids are (0 open, 1 shut).
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
uniform vec3 eye_white : source_color = vec3(0.96, 0.92, 0.8);
// How much bigger the cartoon eye is than its own.
const float CARTOON_EYE = 1.45;
const float EYE_R = 0.036;

varying float part;
varying float flag;
varying float tip;
varying vec2 at;
varying vec3 rest;
varying vec3 rest_normal;
varying vec3 up_here;
varying float long_is;

float fullness(float x) {
	x = fract(x);
	float through = x < SQUEEZE_AT ? 0.5 * x / SQUEEZE_AT : 0.5 + 0.5 * (x - SQUEEZE_AT) / (1.0 - SQUEEZE_AT);
	return 0.5 - 0.5 * cos(through * 6.2831853);
}

// How much wider the mantle is than at rest, `t` from its collar (0) to its tip (1): a bag that
// swells most behind its middle, the squeeze running back along it.
float swell(float t) {
	float full = fullness(phase - 0.1 * t);
	float where = smoothstep(0.0, 0.25, t) * (1.0 - smoothstep(0.75, 1.0, t) * 0.6);
	return 1.0 + (0.12 * full - 0.05) * where * breathe;
}

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(
			mix(mix(hash3(i), hash3(i + vec3(1.0, 0.0, 0.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 0.0)), hash3(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
			mix(mix(hash3(i + vec3(0.0, 0.0, 1.0)), hash3(i + vec3(1.0, 0.0, 1.0)), f.x), mix(hash3(i + vec3(0.0, 1.0, 1.0)), hash3(i + vec3(1.0, 1.0, 1.0)), f.x), f.y),
			f.z);
}

// Arm `row` at `s` (0 root .. 1 tip) along its rope: the point on the smooth curve through the
// rope's points, and the way the curve runs there.
void on_rope(int row, float s, out vec3 point, out vec3 way) {
	float f = clamp(s, 0.0, 1.0) * float(ARM_POINTS - 1);
	int i1 = min(int(f), ARM_POINTS - 2);
	float t = f - float(i1);
	vec3 p0 = texelFetch(ropes, ivec2(max(i1 - 1, 0), row), 0).xyz;
	vec3 p1 = texelFetch(ropes, ivec2(i1, row), 0).xyz;
	vec3 p2 = texelFetch(ropes, ivec2(i1 + 1, row), 0).xyz;
	vec3 p3 = texelFetch(ropes, ivec2(min(i1 + 2, ARM_POINTS - 1), row), 0).xyz;
	vec3 c1 = p2 - p0;
	vec3 c2 = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3;
	vec3 c3 = 3.0 * (p1 - p2) + p3 - p0;
	point = 0.5 * (2.0 * p1 + c1 * t + c2 * t * t + c3 * t * t * t);
	way = normalize(0.5 * (c1 + 2.0 * c2 * t + 3.0 * c3 * t * t) + vec3(0.0, 0.0, 0.0001));
}

// `v` turned by the smallest turn that takes straight back (+Z) to `way`.
vec3 turn_to(vec3 v, vec3 way) {
	vec3 w = cross(vec3(0.0, 0.0, 1.0), way);
	float c = max(way.z, -0.98);
	return v + cross(w, v) + cross(w, cross(w, v)) / (1.0 + c);
}

void vertex() {
	vec3 vertex = VERTEX;
	vec3 normal = NORMAL;
	part = COLOR.r;
	flag = COLOR.g;
	tip = COLOR.b;
	at = UV;
	long_is = UV2.x;
	rest = vertex;
	rest_normal = normal;
	// (the world's up, in its own space: for the eyes' level pupils)
	up_here = normalize(transpose(mat3(MODEL_MATRIX)) * vec3(0.0, 1.0, 0.0));
	int row = int(floor(COLOR.b * 16.0));
	if (part < 0.1) {
		// The mantle (and the papillae on it): breathing.
		vertex.xy *= swell(UV.y);
	} else if (part < 0.3) {
		// The web: hung between this arm's rope and the next one's, as far down them as it is.
		int next = (row + 1) % ARMS;
		vec3 a;
		vec3 a_way;
		vec3 b;
		vec3 b_way;
		on_rope(row, UV.y, a, a_way);
		on_rope(next, UV.y, b, b_way);
		float w = UV.x;
		vec3 across = b - a;
		vec3 along = normalize(mix(a_way, b_way, w));
		// (slack between them: it bellies back a little, more as the arms spread)
		float slack = sin(3.14159 * w) * length(across) * (0.08 + 0.12 * sit);
		vertex = mix(a, b, w) + along * slack;
		vec3 n = normalize(cross(along, across) + vec3(0.0, 0.0, 1e-5));
		// (the outer sheet looks the way the rest normal, turned with its arm, looks; the inner the other)
		if (dot(n, turn_to(normal, a_way)) < 0.0) {
			n = -n;
		}
		normal = n;
	} else if (part > 0.7) {
		// An arm, or a sucker on it: its offset from the arm's own middle line (straight back from
		// its root, as the model has it) turned to lie the way the rope runs there.
		float s = UV.y;
		float long = UV2.x;
		float a = (float(row) + 0.5) * 0.7853982;
		vec3 root = vec3(cos(a) * ARM_RING, sin(a) * ARM_RING, ARM_Z);
		vec3 offset = vertex - (root + vec3(0.0, 0.0, s * long));
		vec3 on_line;
		vec3 way;
		on_rope(row, s, on_line, way);
		float follows = smoothstep(0.0, 0.03, s);
		offset = mix(offset, turn_to(offset, way), follows);
		normal = normalize(mix(normal, turn_to(normal, way), follows));
		vertex = on_line + offset;
	} else if (part > 0.5) {
		// An eye: bigger, about its own middle, as it turns cartoon.
		vec3 centre = vec3(vertex.x < 0.0 ? -EYE.x : EYE.x, EYE.y, EYE.z);
		vertex = centre + (vertex - centre) * mix(1.0, CARTOON_EYE, cartoon_eyes);
	}
	VERTEX = vertex;
	NORMAL = normal;
}

// The calm skin at `p` (a point at rest): brick red and rust in slow patches, with paler mottling
// (a net of pale blotches) over it; `pale_by` how much paler this part is anyway.
vec3 skin_at(vec3 p, float pale_by) {
	float slow = noise3(p * 5.0 + 2.0);
	vec3 c = mix(skin, rust, smoothstep(0.35, 0.75, slow));
	// (the blotches: pale where a finer noise is high, ragged at their edges)
	float blot = noise3(p * 38.0) * 0.65 + noise3(p * 95.0 + 5.0) * 0.35;
	float mott = smoothstep(0.58, 0.7, blot) * mottle * (1.0 - blush);
	c = mix(c, pale, mott * 0.5);
	// (and darker veins between them)
	c = mix(c, dark, smoothstep(0.34, 0.24, blot) * 0.3);
	c = mix(c, under, pale_by);
	// roused, dark red all over; flashing, pale
	c = mix(c, dark * 1.25, blush * 0.8 * (1.0 - pale_by * 0.6));
	c = mix(c, vec3(0.93, 0.86, 0.8), flash_now * 0.85);
	return c;
}

void fragment() {
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	float above = smoothstep(-0.8, 0.2, normalize(rest_normal).y);
	vec3 c;
	float rough = 0.42;
	if (part < 0.1) {
		c = skin_at(rest, (1.0 - above) * 0.35);
		// (a papilla's point a little paler)
		c = mix(c, pale, smoothstep(0.5, 1.0, tip) * 0.45 * (1.0 - blush));
	} else if (part < 0.3) {
		// The web: as the arms outside, paler on the inner sheet.
		c = skin_at(rest, flag > 0.5 ? 0.7 : 0.1);
	} else if (part < 0.5) {
		c = skin_at(rest, (1.0 - above) * 0.3);
		c = mix(c, pale, smoothstep(0.5, 1.0, tip) * 0.45 * (1.0 - blush));
		if (flag > 0.5) {
			// The mouth: pale lips, dark in the middle where the beak is.
			c = mix(vec3(0.08, 0.04, 0.03), sucker * 0.9, smoothstep(0.25, 0.5, at.x));
		}
	} else if (part < 0.7) {
		// An eye: gold, a darker rim, the pupil a level slit (level with the world, not the body).
		vec3 centre = vec3(rest.x < 0.0 ? -EYE.x : EYE.x, EYE.y, EYE.z);
		vec3 o = vec3(rest.x < 0.0 ? -EYE_OUT.x : EYE_OUT.x, EYE_OUT.y, EYE_OUT.z);
		vec3 d = rest - centre;
		vec3 u = up_here - o * dot(up_here, o);
		u = length(u) > 0.05 ? normalize(u) : normalize(cross(o, vec3(0.0, 0.0, 1.0)));
		vec3 h = cross(o, u);
		// (the eye's own frame, with the body: x towards its arms, y up its back; `eye_look` slides
		// the iris and pupil that way)
		vec3 ub = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
		vec3 hb = cross(o, ub);
		hb *= sign(hb.z);
		vec3 dl = d - (hb * eye_look.x + ub * eye_look.y) * 0.006;
		float x = dot(dl, h);
		float y = dot(dl, u);
		float r = length(vec2(x, y));
		c = mix(iris, iris * 0.55, smoothstep(0.014, 0.026, r));
		c = mix(c, vec3(0.92, 0.84, 0.6), smoothstep(0.004, 0.0, abs(r - 0.012)) * 0.3);
		float slit = pow(abs(x) / 0.019, 4.0) + pow(abs(y) / 0.0048, 2.0);
		c = mix(vec3(0.01, 0.008, 0.008), c, smoothstep(0.85, 1.15, slit));
		float r0 = length(vec2(dot(d, h), dot(d, u)));
		c = mix(c, skin_at(rest, 0.0), smoothstep(0.029, 0.034, r0));
		rough = mix(0.08, 0.42, smoothstep(0.028, 0.034, r0));
		if (cartoon_eyes > 0.0) {
			// The cartoon eye (in its own measure, 1 its edge): a cream white, a gold iris, a level
			// bar of a pupil (level with the world, as its own is), a highlight up and towards its
			// arms that stays put, a dark outline; a heavy, knowing upper lid (below).
			vec2 e = vec2(dot(d, hb), dot(d, ub)) / EYE_R;
			vec2 ei = e - eye_look * 0.3;
			float er = length(e);
			float ir = length(ei);
			vec3 k = eye_white;
			k = mix(k, mix(iris * 1.2, iris * 0.62, smoothstep(0.08, 0.42, ir)), 1.0 - smoothstep(0.41, 0.45, ir));
			k = mix(k, vec3(0.22, 0.1, 0.03), (1.0 - smoothstep(0.015, 0.035, abs(ir - 0.43))) * 0.8);
			vec3 ev = (hb * ei.x + ub * ei.y);
			vec2 bar = vec2(dot(ev, h), dot(ev, u));
			float bar_in = length(max(abs(bar) - vec2(0.2, 0.025), 0.0)) - 0.07;
			k = mix(k, vec3(0.01, 0.008, 0.008), 1.0 - smoothstep(-0.01, 0.015, bar_in));
			float shine = 1.0 - smoothstep(0.07, 0.095, length(e - vec2(0.2, 0.26)));
			shine = max(shine, 1.0 - smoothstep(0.03, 0.05, length(e - vec2(0.33, 0.1))));
			k = mix(k, vec3(1.0), shine);
			k = mix(k, vec3(0.12, 0.03, 0.02), smoothstep(0.68, 0.72, er));
			k = mix(k, skin_at(rest, 0.0), smoothstep(0.8, 0.84, er));
			c = mix(c, k, cartoon_eyes);
			rough = mix(rough, mix(0.06, 0.42, smoothstep(0.68, 0.84, er)), cartoon_eyes);
		}
		// The lids: the upper one sits over the cartoon eye's top third (sloping down towards its
		// arms), its edge drawn dark; `blink` brings it down to meet the lower one.
		vec2 e = vec2(dot(d, hb), dot(d, ub)) / EYE_R;
		float lid_at = mix(mix(1.4, 0.34 - 0.14 * e.x, cartoon_eyes), -0.2, blink);
		float low_at = mix(-1.4, -0.2, blink);
		float lid = max(smoothstep(lid_at - 0.02, lid_at + 0.02, e.y), 1.0 - smoothstep(low_at - 0.02, low_at + 0.02, e.y));
		float lash = cartoon_eyes * (1.0 - smoothstep(0.03, 0.08, abs(e.y - lid_at))) * (1.0 - smoothstep(0.78, 0.84, length(e)));
		c = mix(c, vec3(0.12, 0.025, 0.02), lash * 0.9);
		c = mix(c, skin_at(rest + vec3(0.0, 0.02, 0.0), 0.0), lid);
		rough = mix(rough, 0.42, lid);
	} else if (part < 0.9) {
		// An arm's skin: its back as the body, its suckered face pale.
		float inner = 1.0 - smoothstep(0.1, 0.26, abs(at.x - 0.5));
		c = skin_at(rest, inner * 0.85);
		if (flag > 0.5) {
			// The game model: its suckers painted where the full model has them, two rows of 52
			// down each arm (suckers() in the build script), each a cream rim round a pinker cup.
			float s = at.y;
			float x_at = 1.0 - sqrt(max(1.0 - clamp((s - 0.015) / 0.97, 0.0, 1.0), 0.0));
			float r_arm = 0.05 * pow(max(1.0 - s, 0.0), 0.85) + 0.0035;
			float size = max(0.4 * r_arm, 0.0022);
			float best = 9.0;
			for (int row = 0; row < 2; row++) {
				float f = clamp(round(x_at * 52.0 - 0.25 - 0.5 * float(row)), 0.0, 51.0);
				float xi = (f + 0.25 + 0.5 * float(row)) / 52.0;
				float si = 0.015 + 0.97 * (1.0 - (1.0 - xi) * (1.0 - xi));
				float across = (at.x - 0.5 - (row == 1 ? 0.085 : -0.085)) * 6.2831853 * r_arm;
				best = min(best, length(vec2(across, (s - si) * long_is)) / size);
			}
			vec3 cup = mix(sucker * 0.92, sucker, smoothstep(0.45, 0.6, best));
			cup = mix(vec3(0.78, 0.55, 0.5), cup, smoothstep(0.42, 0.55, best));
			cup = mix(cup, dark, blush * 0.25);
			c = mix(c * 0.75, c, smoothstep(1.0, 1.2, best));
			c = mix(c, cup, 1.0 - smoothstep(0.9, 1.0, best));
		}
	} else {
		// A sucker: a cream rim, its cup a little darker and pinker.
		c = mix(sucker * 0.92, sucker, smoothstep(0.35, 0.5, at.x));
		c = mix(c, vec3(0.78, 0.55, 0.5), smoothstep(0.7, 0.98, at.x));
		c = mix(c, dark, blush * 0.25);
		rough = 0.35;
	}
	// (wet: a little sheen where the skin turns away)
	c = mix(c, vec3(0.9, 0.8, 0.78), 0.12 * pow(edge, 2.5));
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.45;
}
