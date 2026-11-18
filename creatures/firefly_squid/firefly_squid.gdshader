shader_type spatial;
// The firefly squid (firefly_squid.gd): every marking and every tiny light drawn here (no texture files), its arms
// bent and swaying, its fins rippling, its mantle bent round (`curl`), and its lights flashing in waves. What each
// point is comes from the model (tools/build_firefly_squid.py): UV2.y the part (0 the body: mantle and head, 1 a fin,
// 2 an eye, 3 an arm or tentacle, 4 a big light); UV2.x on an arm or a light on one, which arm (1 to 10: arms 1 to 8,
// tentacles 9 and 10), 0 elsewhere. UV on the body: x how far along (0 the arms' tips, 1 the mantle's end), y how
// high round it (1 its back, 0 its belly); on a fin: x out from its root (0) to its edge (1), y front (0) to back
// (1); on an arm: x round it (0.5 its inner face), y root (0) to tip (1); on an eye: its own plane (x towards the
// arms, y up, 1 at its rim); on a light: x middle (0) to rim (1).
//
// IT SWIMS ARMS FIRST: its arms point along -Z, the end of its mantle is at +Z, its back +Y. What lights up
// (EMISSION): the many tiny photophores drawn over its skin (thick on its belly and lower sides, fewer on its back,
// a few along its arms), the three big beads at the tip of each of its lowest arms, and the five small lights round
// the lower rim of each eye. They brighten in waves that travel back along it from its arms to its mantle's end, by
// `colour_phase`. Everything that moves goes by `phase` and the lights by `colour_phase` only, so it loops. Nothing
// here needs more than GL Compatibility has. One opaque draw, back faces culled.
render_mode cull_back;

// Kept in step with the model (tools/build_firefly_squid.py).
const float HALF = 0.035;
const float COLLAR_Z = -0.0093;
const float MANTLE_LONG = 0.044;
const float ARM_RX = 0.0021;
const float ARM_RY = 0.0019;
const float ARM_Z = -0.0188;
const float ARM_ANGLE[10] = float[](0.3926991, 1.1780972, 1.9634954, 2.7488936, 3.5342917, 4.3196899, 5.1050881, 5.8904862, 4.1015237, 5.3232542);
const float ARM_RING[10] = float[](1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.55, 0.55);
const float ARM_LONG[10] = float[](0.0118, 0.0102, 0.0102, 0.0118, 0.0130, 0.0158, 0.0158, 0.0130, 0.0166, 0.0166);
const float ARM_REST[10] = float[](0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.06, 0.06);
const vec3 EYE_BASE = vec3(0.00463, 0.0005, -0.0138);
const float EYE_RADIUS = 0.0034;

// How far through a beat (0..1, it wraps): its arms sway once, its fins ripple `flaps` times. Set by FireflySquid.
uniform float phase = 0.0;
// Fin ripples in a beat (a whole number).
uniform float flaps = 2.0;
// How much it moves: 1 swimming gently, 0 still (as built), 2 twice as much.
uniform float sway = 1.0;
// Its arms: 0 drawn together ahead of it; 1 opened out wide and curled back.
uniform float spread : hint_range(0.0, 1.0) = 0.0;
// Turning: how far its mantle is bent round behind its head, radians from its collar to its end (more than 0 its
// end comes round to +X, its left). The head and arms stay.
uniform float curl = 0.0;

// Its lights. All by `colour_phase` (0..1, a round of its lights), so it comes round: `light_rounds` waves pass back
// along it in a round (a whole number), `light_waves` stand on it at once. `glow` 0 dark, 1 as made, 2 twice as
// bright; `twinkle` how much each light flickers in its own time; `flash` all of them at once (0..1, set it for a
// burst).
uniform float colour_phase = 0.0;
uniform float light_rounds = 2.0;
uniform float light_waves = 1.5;
uniform float glow : hint_range(0.0, 2.0) = 1.0;
uniform float twinkle : hint_range(0.0, 1.0) = 0.5;
uniform float flash : hint_range(0.0, 1.0) = 0.0;

// Its dusky red-violet skin, paler beneath, its dark chromatophores, its lights' blue, its eye's silver.
uniform vec3 skin : source_color = vec3(0.4, 0.17, 0.23);
uniform vec3 belly : source_color = vec3(0.6, 0.42, 0.48);
uniform vec3 freckle : source_color = vec3(0.2, 0.05, 0.08);
uniform vec3 light_colour : source_color = vec3(0.22, 0.58, 1.0);
uniform vec3 eye_silver : source_color = vec3(0.6, 0.66, 0.78);

// The cartoon eye (0 the eye as made, 1 the cartoon one; Gulp uses 1). Bright and curious, a little starry: grown to
// 1.45 times, a clean white, a big deep-blue iris with a ring of light flecks round a big round pupil, two highlights,
// a dark outline, wide open. `eye_look` slides the iris and pupil (x + towards the arms, y + up; -1..1), `blink`
// closes a lid over it (0 open, 1 shut).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_white : source_color = vec3(0.95, 0.96, 0.98);
uniform vec3 eye_iris : source_color = vec3(0.12, 0.32, 0.75);
const float EYE_GROW = 1.45;
const float IRIS_R = 0.62;
const float PUPIL_R = 0.36;

varying float part;
varying float arm;
varying vec3 rest;
varying vec2 at;

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float hash2(vec2 p) {
	return hash3(vec3(p, 7.31));
}

vec3 turned(vec3 v, vec3 axis, float angle) {
	float c = cos(angle);
	float s = sin(angle);
	return v * c + cross(axis, v) * s + axis * dot(axis, v) * (1.0 - c);
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float d = v.z - COLLAR_Z;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / MANTLE_LONG;
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float s = sin(a);
	n = vec3(n.x * c + n.z * s, n.y, -n.x * s + n.z * c);
	v = vec3(r - (r - v.x) * c, v.y, COLLAR_Z + (r - v.x) * s);
}

void vertex() {
	part = UV2.y;
	arm = UV2.x;
	at = UV;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	int k = int(arm + 0.5) - 1;
	if (k >= 0 && (p == 3 || p == 4)) {
		// An arm (and the lights on it): bent in the plane that holds the middle line and the way it leans out.
		// Its angle from straight ahead runs from its rest at its root, opened by `spread` and curled back towards
		// its tip, swaying a little with `phase`.
		float s = UV.y;
		float long = ARM_LONG[k];
		float rest_angle = ARM_REST[k];
		float a = ARM_ANGLE[k];
		vec3 lean = vec3(cos(a), sin(a), 0.0);
		vec3 root = vec3(cos(a) * ARM_RX * ARM_RING[k], sin(a) * ARM_RY * ARM_RING[k], ARM_Z);
		vec3 ahead = vec3(0.0, 0.0, -1.0);
		vec3 axis = normalize(cross(ahead, lean));
		vec3 way0 = ahead * cos(rest_angle) + lean * sin(rest_angle);
		vec3 offset = v - (root + way0 * long * s);
		float tentacle = k >= 8 ? 1.0 : 0.0;
		float wave = sway * 0.2 * sin(6.2831853 * phase + float(k) * 0.9) * (0.5 + 0.5 * spread);
		float A = rest_angle + spread * mix(0.9, 0.25, tentacle) + wave * 0.3;
		float B = spread * mix(1.5, 0.4, tentacle) + wave;
		float sc = max(s, 0.0);
		float th = A + B * sc;
		vec3 along;
		if (abs(B) > 0.0001) {
			along = ahead * (sin(th) - sin(A)) / B + lean * (cos(A) - cos(th)) / B;
		} else {
			along = (ahead * cos(A) + lean * sin(A)) * sc;
		}
		float follows = smoothstep(0.0, 0.1, s);
		vec3 on_line = root + mix(way0 * sc, along, follows) * long;
		float turn = (th - rest_angle) * follows;
		v = on_line + turned(offset, axis, turn);
		n = turned(n, axis, turn);
	} else if (p == 1) {
		// A fin: a ripple runs back along its edge.
		v.y += sway * 0.0011 * pow(UV.x, 1.3) * sin(6.2831853 * flaps * phase - 3.0 * UV.y);
	} else if (p == 2 || p == 4) {
		// An eye, and the lights round it: grown about the eye's middle for the cartoon eye (the eye squashed a
		// little as it blinks).
		vec3 base = vec3(sign(v.x) * EYE_BASE.x, EYE_BASE.y, EYE_BASE.z);
		vec3 d = (v - base) * mix(1.0, EYE_GROW, cartoon_eyes);
		if (p == 2) {
			d.y *= 1.0 - 0.35 * blink * cartoon_eyes;
		}
		v = base + d;
	}
	if (p <= 1) {
		curl_bend(v, n);
	}
	VERTEX = v;
	NORMAL = n;
}

// Round dark spots, some cells of a grid with one each (1 on a spot).
float freckles(vec3 q) {
	vec3 cell = floor(q);
	vec3 f = fract(q);
	vec3 o = vec3(hash3(cell + 1.7), hash3(cell + 4.3), hash3(cell + 8.1)) * 0.4 + 0.3;
	float r = 0.12 + 0.16 * hash3(cell + 2.9);
	return step(0.45, hash3(cell)) * (1.0 - smoothstep(r * 0.6, r, length(f - o)));
}

// How bright the lights are at `xm` (metres behind the arms' tips), each with its own number `own`: waves that
// travel back along it, each light flickering a little in its own time.
float lit_at(float xm, float own) {
	float w = 0.5 + 0.5 * sin(6.2831853 * (light_rounds * colour_phase - light_waves * xm / 0.07) + own * 6.2831853 * 0.25 * twinkle);
	float flick = 1.0 - twinkle * 0.4 * (0.5 + 0.5 * sin(6.2831853 * (colour_phase * floor(3.0 + own * 5.0) + own * 7.0)));
	return mix(0.18 + 0.82 * w * w * w * flick, 1.0, flash);
}

// The tiny photophores over the skin at `q` (a place in a flat of metres round it and along it), thick where
// `thick` is 1: 1 on a light; `own` its own number.
float specks(vec2 q, float size, float thick, out float own) {
	vec2 cell = floor(q / size);
	vec2 f = q / size - cell;
	vec2 o = vec2(hash2(cell + 1.3), hash2(cell + 5.9)) * 0.5 + 0.25;
	own = hash2(cell + 3.1);
	float there = step(hash2(cell + 9.7), thick);
	return there * (1.0 - smoothstep(0.17, 0.27, length(f - o)));
}

vec3 cartoon_eye(vec2 q, vec3 lid, out float lidded) {
	float r = length(q);
	float aa = max(fwidth(r), 0.01) * 1.2;
	vec2 iq = q - clamp(eye_look, vec2(-1.0), vec2(1.0)) * 0.17;
	float ir = length(iq);
	vec3 c = eye_white * (1.0 - 0.2 * smoothstep(0.4, 0.82, r));
	vec3 ring = eye_iris * (0.55 + 0.9 * smoothstep(IRIS_R, 0.0, length(iq - vec2(0.0, -0.3 * IRIS_R))));
	ring = mix(ring, eye_iris * 0.3, smoothstep(IRIS_R * 0.78, IRIS_R, ir));
	// (a ring of light flecks in the iris)
	float fa = atan(iq.y, iq.x);
	float flecks = smoothstep(0.55, 0.95, sin(fa * 9.0) * 0.5 + 0.5) * (1.0 - smoothstep(0.03, 0.07, abs(ir - (PUPIL_R + IRIS_R) * 0.5)));
	ring = mix(ring, vec3(0.6, 0.85, 1.0), flecks * 0.8);
	c = mix(c, ring, 1.0 - smoothstep(IRIS_R - aa, IRIS_R + aa, ir));
	c = mix(c, vec3(0.01, 0.012, 0.03), 1.0 - smoothstep(PUPIL_R - aa, PUPIL_R + aa, ir));
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.15 - aa, 0.15 + aa, length(q - vec2(0.18, 0.25))));
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.065 - aa, 0.065 + aa, length(q - vec2(-0.17, -0.2))));
	c = mix(c, vec3(0.05, 0.03, 0.06), smoothstep(0.82 - aa, 0.82 + aa, r));
	float skirt = smoothstep(0.92 - aa, 0.92 + aa, r);
	float edge = mix(1.1, -1.1, clamp(blink, 0.0, 1.0));
	lidded = max(smoothstep(edge - aa, edge + aa, q.y), skirt);
	return mix(c, lid, lidded);
}

void fragment() {
	int p = int(part + 0.5);
	float xm = rest.z + HALF;
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	vec3 e = vec3(0.0);
	float rough = 0.45;
	float spec = 0.45;
	float spots = max(freckles(rest * 1500.0), 0.6 * freckles(rest * 2700.0 + 3.0));
	if (p == 0) {
		// The skin: dusky red-violet, paler beneath, freckled with dark chromatophores, the collar's edge a fine line;
		// and its tiny lights, thick on its belly and lower sides, fewer up its flanks, few on its back.
		float high = at.y;
		c = mix(belly, skin, smoothstep(0.2, 0.7, high));
		c = mix(c, freckle, spots * mix(0.35, 0.7, high));
		float collar = 1.0 - smoothstep(0.0, 0.00025, abs(xm - 0.0258));
		c = mix(c, freckle, collar * 0.6);
		c += vec3(0.25, 0.2, 0.3) * glance * glance * 0.4;
		float angle = atan(rest.x, rest.y);
		vec2 q = vec2(angle * max(length(rest.xy), 0.001), xm);
		float own;
		float thick = mix(0.95, 0.12, smoothstep(0.25, 0.85, high)) * smoothstep(0.016, 0.019, xm);
		float dot_ = specks(q, 0.00085, thick, own);
		c = mix(c, vec3(0.75, 0.85, 1.0), dot_ * 0.8);
		e = light_colour * dot_ * lit_at(xm, own) * 2.2;
		rough = 0.35;
	} else if (p == 1) {
		// A fin: the skin, thinner and paler towards its edge.
		c = mix(skin, belly, 0.3 + 0.4 * at.x);
		c = mix(c, freckle, spots * 0.4 * (1.0 - at.x));
		rough = 0.5;
	} else if (p == 3) {
		// An arm: the skin on its back, paler on its inner face, a row of tiny lights down its back.
		float inner = 1.0 - smoothstep(0.12, 0.3, abs(at.x - 0.5));
		c = mix(skin, belly, inner * 0.7);
		c = mix(c, freckle, spots * 0.5 * (1.0 - inner));
		float long = ARM_LONG[clamp(int(arm + 0.5) - 1, 0, 9)];
		float along = at.y * long / 0.0011;
		float d = length(vec2((fract(along) - 0.5) * 0.0011, min(at.x, 1.0 - at.x) * 0.002));
		float dot_ = (1.0 - smoothstep(0.00012, 0.0002, d)) * step(at.y, 0.85) * step(0.1, at.y) * step(arm, 8.5);
		c = mix(c, vec3(0.75, 0.85, 1.0), dot_ * 0.8);
		e = light_colour * dot_ * lit_at(xm, fract(floor(along) * 0.37 + arm * 0.13)) * 1.6;
	} else if (p == 2) {
		// An eye: a big dark round pupil in a silver eye with a blue sheen.
		float r = length(at);
		c = mix(vec3(0.005, 0.006, 0.012), eye_silver, smoothstep(0.6, 0.66, r));
		c = mix(c, eye_silver * vec3(0.7, 0.85, 1.1), 0.4 * smoothstep(0.66, 0.85, r));
		c = mix(c, skin * 0.6, smoothstep(0.88, 1.0, r));
		rough = 0.1;
		spec = 0.8;
		if (cartoon_eyes > 0.0) {
			float lidded;
			c = mix(c, cartoon_eye(at, skin, lidded), cartoon_eyes);
			rough = mix(rough, mix(0.15, 0.45, lidded), cartoon_eyes);
		}
		e = c * 0.1 * cartoon_eyes;
	} else {
		// A big light: a bright blue middle, a dark rim; the beads on the arms' tips flash with the waves, the
		// lights round the eyes burn steadier.
		float r = at.x;
		float on_arm = step(0.5, arm);
		float lit = mix(0.75 + 0.25 * lit_at(xm, 0.3), lit_at(xm, 0.0) * 0.8 + 0.2, on_arm);
		float middle = on_arm > 0.5 ? 1.0 : 1.0 - smoothstep(0.45, 0.8, r);
		c = mix(vec3(0.05, 0.05, 0.08), vec3(0.7, 0.85, 1.0), middle);
		e = light_colour * middle * lit * mix(2.6, 3.2, on_arm);
		rough = 0.2;
		spec = 0.7;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = e * glow;
}
