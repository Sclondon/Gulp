// The cuttlefish (cuttlefish.gd): its fin skirt ripples in a wave running back along each side,
// its mantle bends round (`curl`), its arms are bent and spread (`spread`) and sway, its two
// tentacles are folded away or shot out (`strike`), and its skin is drawn: mottled sandy
// camouflage, the zebra bands, the passing cloud, blanched, and the startled flash. Everything
// that moves goes by `phase` and `colour_phase` only, so it loops. No texture files; nothing here
// needs more than GL Compatibility has. One opaque draw, back faces culled (the fin is two sheets
// back to back in the model).
//
// What each point is comes from the model (tools/build_cuttlefish.py): COLOR.r the part (0 the
// mantle, 0.2 the fin, 0.4 the head and siphon, 0.6 an eye, 0.8 an arm, 1 a tentacle); COLOR.g on
// the fin 0 the sheet that looks up, 1 the one that looks down; COLOR.b on an arm or tentacle,
// which ((n + 0.5) / 16: arms 0 to 7, tentacles 8 and 9). UV.x round it (0.5 an arm's or
// tentacle's inner face; the fin: 0 at the mantle to 1 at its edge), UV.y along it (the mantle and
// fin: collar 0 to end 1; an arm or tentacle: root 0 to tip 1). UV2.x an arm's or tentacle's
// length, UV2.y an arm's rest angle (radians, towards the middle line).
shader_type spatial;
render_mode cull_back;

// Kept in step with the model and the script.
const float MANTLE_FROM = -0.06;
const float MANTLE_LONG = 0.26;
const float ARM_RX = 0.019;
const float ARM_RY = 0.014;
const float ARM_Z = -0.126;
const float TENTACLE_X = 0.005;
const float TENTACLE_Y = -0.004;
const float TENTACLE_Z = -0.12;
const vec3 EYE = vec3(0.042, 0.014, -0.09);
const vec3 EYE_OUT = vec3(0.9524, 0.3048, 0.0);
const float EYE_R = 0.0165;

// How far through a round of its fin's waves (0..1). Set by Cuttlefish.
uniform float phase = 0.0;
// Waves that pass along the fin in a round (a whole number, so that it comes round).
uniform float fin_ripples = 2.0;
// How many waves stand on the fin at once, from the collar to the end.
uniform float fin_waves = 2.2;
// How high the fin's waves are at its edge (metres at size 1).
uniform float fin_lift = 0.006;
// Turning: how far the mantle is bent round behind the head, in radians from the collar to its
// end (0 straight; more than 0 its end comes round to +X). The head and arms stay.
uniform float curl = 0.0;
// The arms: 0 drawn together into a point; 1 opened out wide and curled back like a flower.
uniform float spread = 0.0;
// How much the arms sway with `phase`.
uniform float arm_sway = 1.0;
// The tentacles: 0 folded away out of sight inside the arms; 1 shot out to their full length.
uniform float strike = 0.0;

// Its skin. All by `colour_phase` (0..1, a round of its colours), so it comes round.
uniform float colour_phase = 0.0;
// 0..1 each: the black and white bands of a displaying male; the dark band that passes down its
// body (`cloud_rounds` bands go by in a round, a whole number); pale all over.
uniform float zebra = 0.0;
uniform float cloud = 0.0;
uniform float cloud_rounds = 2.0;
uniform float blanch = 0.0;
// A flash, now (0..1): `Cuttlefish.flash()`. It goes pale, with dark eyespots on its back and its
// fin's edge dark (a startle).
uniform float flash_now = 0.0;

uniform vec3 sand : source_color = vec3(0.66, 0.55, 0.4);
uniform vec3 brown : source_color = vec3(0.34, 0.24, 0.15);
uniform vec3 white : source_color = vec3(0.93, 0.91, 0.86);
uniform vec3 black : source_color = vec3(0.06, 0.05, 0.05);
uniform vec3 belly : source_color = vec3(0.9, 0.88, 0.83);
uniform vec3 iris : source_color = vec3(0.8, 0.72, 0.5);

// Cartoon eyes (0 its own eye; 1 bigger, a white, a green-gold iris round its W of a pupil, a
// highlight, a dark outline, a low upper lid and the lower lid pushed up: a sly look), where they
// look (x towards its arms, y up its back, -1..1), and how shut its lids are (0 open, 1 shut).
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
uniform vec3 cartoon_iris : source_color = vec3(0.6, 0.72, 0.3);
// How much bigger the cartoon eye is than its own.
const float CARTOON_EYE = 1.6;

varying float part;
varying float flag;
varying float row_is;
varying vec2 at;
varying float long_is;
varying vec3 rest;
varying vec3 rest_normal;

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

// `v` turned by `angle` about `axis` (a unit).
vec3 turned(vec3 v, vec3 axis, float angle) {
	float c = cos(angle);
	float s = sin(angle);
	return v * c + cross(axis, v) * s + axis * dot(axis, v) * (1.0 - c);
}

// The mantle (and the fin on it) laid round an arc behind the head (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float d = v.z - MANTLE_FROM;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / MANTLE_LONG;
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float s = sin(a);
	n = vec3(n.x * c + n.z * s, n.y, -n.x * s + n.z * c);
	v = vec3(r - (r - v.x) * c, v.y, MANTLE_FROM + (r - v.x) * s);
}

void vertex() {
	vec3 vertex = VERTEX;
	vec3 normal = NORMAL;
	part = COLOR.r;
	flag = COLOR.g;
	at = UV;
	long_is = UV2.x;
	rest = vertex;
	rest_normal = normal;
	int row = int(floor(COLOR.b * 16.0));
	row_is = float(row);
	if (part > 0.1 && part < 0.3) {
		// The fin: a wave runs back along it (it swims arms first: the wave runs to its end),
		// highest at its edge, the same on both sides.
		float t = UV.y;
		float w = UV.x;
		float angle = 6.2831853 * (fin_ripples * phase - fin_waves * t);
		float lift = fin_lift * pow(w, 1.3) * smoothstep(0.0, 0.12, t) * (1.0 - smoothstep(0.85, 1.0, t) * 0.5);
		vertex.y += sin(angle) * lift;
		// (the slopes of the wave, across the fin and along it, for its light; the upper sheet
		// looks up, the lower one down)
		float across = sin(angle) * fin_lift * 1.3 * pow(max(w, 0.05), 0.3) / 0.014 * sign(vertex.x);
		float along = -cos(angle) * 6.2831853 * fin_waves / (MANTLE_LONG * 0.92) * lift;
		normal = normalize(vec3(-across, 1.0, -along)) * (normal.y < 0.0 ? -1.0 : 1.0);
	} else if (part > 0.7 && part < 0.9) {
		// An arm: bent in the plane that holds the middle line and the way it leans out. Its
		// angle from straight ahead runs from `rest` (leaning in, the pointed bunch) at its root,
		// opened by `spread` and curled back towards its tip, swaying a little with `phase`.
		float s = UV.y;
		float long = UV2.x;
		float rest_angle = UV2.y;
		float a = (float(row) + 0.5) * 0.7853982;
		vec3 lean = vec3(cos(a), sin(a), 0.0);
		vec3 root = vec3(cos(a) * ARM_RX, sin(a) * ARM_RY, ARM_Z);
		vec3 ahead = vec3(0.0, 0.0, -1.0);
		vec3 axis = normalize(cross(ahead, lean));
		vec3 way0 = ahead * cos(rest_angle) + lean * sin(rest_angle);
		vec3 offset = vertex - (root + way0 * long * s);
		float sway = arm_sway * 0.22 * sin(6.2831853 * phase + float(row) * 0.9) * (0.4 + 0.6 * spread);
		// (the angle grows along it: A at the root, A + B at the tip)
		float A = rest_angle + spread * 1.0 + sway * 0.3;
		float B = spread * 1.6 + sway;
		float sc = max(s, 0.0);
		float th = A + B * sc;
		vec3 along;
		if (abs(B) > 0.0001) {
			along = ahead * (sin(th) - sin(A)) / B + lean * (cos(A) - cos(th)) / B;
		} else {
			along = (ahead * cos(A) + lean * sin(A)) * sc;
		}
		float follows = smoothstep(0.0, 0.08, s);
		vec3 on_line = root + mix(way0 * sc, along, follows) * long;
		float turn = (th - rest_angle) * follows;
		vertex = on_line + turned(offset, axis, turn);
		normal = turned(normal, axis, turn);
	} else if (part > 0.9) {
		// A tentacle: folded away, squeezed into a short stub just inside the bunch of arms;
		// struck, shot out to its full length, the two a little apart.
		float s = UV.y;
		float side = row == 8 ? 1.0 : -1.0;
		vec3 root = vec3(side * TENTACLE_X, TENTACLE_Y, TENTACLE_Z);
		vec3 offset = vertex - (root + vec3(0.0, 0.0, -long_is * s));
		float reach = mix(0.05, 1.0, strike);
		float thick = mix(0.6, 1.0, strike);
		vertex = root + vec3(side * 0.012 * strike * s, 0.0, 0.006 * (1.0 - strike) - long_is * s * reach) + offset * thick;
	} else if (part > 0.5 && part < 0.7) {
		// An eye: bigger, about its own middle, as it turns cartoon.
		vec3 centre = vec3(vertex.x < 0.0 ? -EYE.x : EYE.x, EYE.y, EYE.z);
		vertex = centre + (vertex - centre) * mix(1.0, CARTOON_EYE, cartoon_eyes);
	}
	if (part < 0.3) {
		curl_bend(vertex, normal);
	}
	VERTEX = vertex;
	NORMAL = normal;
}

// The camouflage at `p` (a point at rest): sand mottled with brown blotches and pale flecks, a pale
// square in the middle of its back, a row of pale spots along the fin's root.
vec3 camo(vec3 p) {
	// (the noise's lattice turned out of line with the body, or its squares would show)
	p = vec3(0.36 * p.x + 0.48 * p.y + 0.8 * p.z, -0.8 * p.x + 0.6 * p.y, -0.48 * p.x - 0.64 * p.y + 0.6 * p.z);
	float big = noise3(p * 55.0 + 3.0) * 0.55 + noise3(p * 120.0) * 0.3 + noise3(p * 300.0 + 1.7) * 0.15;
	vec3 c = mix(sand, brown, smoothstep(0.45, 0.7, big) * 0.85);
	float fleck = noise3(p * 260.0 + 9.0) * 0.8 + noise3(p * 610.0) * 0.2;
	c = mix(c, white, smoothstep(0.66, 0.74, fleck) * 0.6);
	return c;
}

// The zebra bands at `p`: black and white bands across its back, wavy, and across its arms.
float zebra_dark(vec3 p, float on_arm) {
	float wave = sin(p.x * 70.0) * 0.006 + (noise3(p * 40.0) - 0.5) * 0.01;
	float bands = sin((p.z + wave) * 6.2831853 / 0.024 + abs(p.x) * 30.0);
	float arm_bands = sin(at.y * long_is * 6.2831853 / 0.016);
	return smoothstep(-0.15, 0.25, mix(bands, arm_bands, on_arm));
}

// The passing cloud at `p`: dark bands that run back along it, from its arms to its end.
float cloud_dark(vec3 p) {
	float x = fract((p.z + (noise3(p * 30.0) - 0.5) * 0.03 + abs(p.x) * 0.4 + 0.2) / 0.14 - colour_phase * cloud_rounds);
	return smoothstep(0.15, 0.45, x) * (1.0 - smoothstep(0.55, 0.85, x));
}

vec3 skin_at(vec3 p, float back, float on_arm) {
	vec3 c = camo(p);
	// (the pale square in the middle of its back, and the pale spots along the fin's root)
	if (part < 0.1) {
		vec2 sq = abs(vec2(p.x, p.z - 0.05)) / vec2(0.016, 0.022);
		c = mix(c, white, (1.0 - smoothstep(0.6, 1.2, length(sq * sq * sq))) * 0.45 * back);
		// (a dot every 11 mm along the fin's root, just above it)
		float dz = (fract(p.z / 0.011) - 0.5) * 0.011;
		float spots = 1.0 - smoothstep(0.0025, 0.0035, length(vec2(dz, p.y - 0.0045)));
		c = mix(c, white, spots * 0.85 * smoothstep(-0.04, -0.02, p.z) * (1.0 - smoothstep(0.17, 0.19, p.z)));
	}
	c = mix(belly, c, back);
	c = mix(c, mix(white, black, zebra_dark(p, on_arm)), zebra * mix(0.4, 1.0, back));
	c = mix(c, brown * 0.3, cloud * cloud_dark(p) * mix(0.3, 0.92, back));
	c = mix(c, white, blanch * 0.9);
	return c;
}

void fragment() {
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	// (how far round to its back this point is: 1 on its back, 0 beneath)
	float back = smoothstep(-0.35, 0.25, normalize(rest_normal).y);
	vec3 c;
	float rough = 0.45;
	if (part < 0.1) {
		c = skin_at(rest, back, 0.0);
	} else if (part < 0.3) {
		// The fin: thin and a little clear-looking, paler towards its edge, its edge white.
		c = skin_at(rest, flag > 0.5 ? 0.0 : 0.7, 0.0);
		c = mix(c, white, smoothstep(0.75, 1.0, at.x) * 0.6);
	} else if (part < 0.5) {
		c = skin_at(rest, back, 0.0);
	} else if (part < 0.7) {
		// An eye: the W of its pupil in a pale gold-grey eye, under a lid of skin.
		vec3 centre = vec3(rest.x < 0.0 ? -EYE.x : EYE.x, EYE.y, EYE.z);
		vec3 o = vec3(rest.x < 0.0 ? -EYE_OUT.x : EYE_OUT.x, EYE_OUT.y, EYE_OUT.z);
		vec3 d = rest - centre;
		vec3 u = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
		vec3 h = normalize(cross(o, u)) * sign(rest.x);
		// (`eye_look` slides the pupil: x towards its arms, which is -h, y up its back)
		vec3 dl = d - (-h * eye_look.x + u * eye_look.y) * 0.003;
		float x = dot(dl, h) / 0.012;
		float y = dot(dl, u) / 0.012;
		float r = length(vec2(x, y * 1.15));
		c = mix(iris, iris * 0.6, smoothstep(0.55, 0.95, r));
		// the W: a band that dips twice
		float mid = -0.24 + 0.52 * pow(abs(abs(x) - 0.42) / 0.42, 1.4);
		float band = abs(y - mid) - 0.22 * (1.0 - smoothstep(0.55, 0.95, abs(x)));
		float pupil = (1.0 - smoothstep(-0.02, 0.04, band)) * (1.0 - smoothstep(0.85, 0.95, abs(x)));
		c = mix(c, vec3(0.01), pupil);
		// (the lid: skin round the eye's edge)
		float lid = smoothstep(0.86, 1.0, length(d - o * dot(d, o)) / EYE_R);
		c = mix(c, skin_at(rest, back, 0.0), lid);
		rough = mix(0.08, 0.45, lid);
		// (in its own measure, 1 its edge: x towards its arms, y up its back)
		vec2 e = vec2(dot(d, -h), dot(d, u)) / EYE_R;
		if (cartoon_eyes > 0.0) {
			// The cartoon eye: a white, a green-gold iris round its W, a highlight up and towards
			// its arms that stays put, a dark outline; its sly lids are below.
			vec2 ei = e - eye_look * 0.28;
			float er = length(e);
			float ir = length(ei);
			vec3 k = vec3(0.95, 0.95, 0.9);
			k = mix(k, mix(cartoon_iris * 1.15, cartoon_iris * 0.55, smoothstep(0.1, 0.48, ir)), 1.0 - smoothstep(0.47, 0.51, ir));
			k = mix(k, vec3(0.1, 0.14, 0.04), (1.0 - smoothstep(0.015, 0.035, abs(ir - 0.49))) * 0.8);
			// (the W, a band that dips twice, across the iris)
			float wx = ei.x / 0.4;
			float wy = ei.y / 0.4;
			float wmid = -0.24 + 0.52 * pow(abs(abs(wx) - 0.42) / 0.42, 1.4);
			float wband = abs(wy - wmid) - 0.24 * (1.0 - smoothstep(0.55, 0.95, abs(wx)));
			float w = (1.0 - smoothstep(-0.02, 0.05, wband)) * (1.0 - smoothstep(0.88, 0.98, abs(wx)));
			k = mix(k, vec3(0.01), w);
			float shine = 1.0 - smoothstep(0.08, 0.11, length(e - vec2(0.22, 0.3)));
			shine = max(shine, 1.0 - smoothstep(0.035, 0.055, length(e - vec2(0.36, 0.14))));
			k = mix(k, vec3(1.0), shine);
			k = mix(k, vec3(0.06, 0.05, 0.04), smoothstep(0.7, 0.74, er));
			k = mix(k, skin_at(rest, back, 0.0), smoothstep(0.82, 0.86, er));
			c = mix(c, k, cartoon_eyes);
			rough = mix(rough, mix(0.06, 0.45, smoothstep(0.7, 0.86, er)), cartoon_eyes);
		}
		// The lids: the cartoon eye's upper lid low and level, its lower lid pushed up (a sly
		// squint); `blink` brings them together.
		float lid_at = mix(mix(1.4, 0.36 + 0.06 * e.x, cartoon_eyes), -0.12, blink);
		float low_at = mix(mix(-1.4, -0.5 + 0.08 * e.x, cartoon_eyes), -0.12, blink);
		float lids = max(smoothstep(lid_at - 0.02, lid_at + 0.02, e.y), 1.0 - smoothstep(low_at - 0.02, low_at + 0.02, e.y));
		float lash = cartoon_eyes * (1.0 - smoothstep(0.03, 0.08, min(abs(e.y - lid_at), abs(e.y - low_at)))) * (1.0 - smoothstep(0.78, 0.84, length(e)));
		c = mix(c, vec3(0.08, 0.06, 0.04), lash * 0.9);
		// (its lids the sandy skin of its back, not its pale belly)
		c = mix(c, skin_at(rest, 1.0, 0.0) * 0.92, lids);
		rough = mix(rough, 0.45, lids);
	} else {
		// An arm or tentacle: its back as the body, its inner face pale with little suckers.
		float inner = 1.0 - smoothstep(0.12, 0.28, abs(at.x - 0.5));
		c = skin_at(rest, 1.0 - 0.75 * inner, part > 0.9 ? 0.0 : 1.0);
		float along = at.y * long_is;
		float s_rows = fract(along / 0.0035);
		float s_across = fract((at.x - 0.5) * 18.0 + 0.5);
		float cup = 1.0 - smoothstep(0.15, 0.3, length(vec2(s_rows - 0.5, s_across - 0.5)));
		float club = part > 0.9 ? smoothstep(0.68, 0.72, at.y) : 1.0;
		c = mix(c, white * 0.82, cup * inner * club * 0.6);
	}
	// The startle: pale, two dark eyespots on its back, the fin's edge dark.
	if (flash_now > 0.0) {
		vec3 pale = mix(white, c, 0.25);
		float spots = 0.0;
		if (part < 0.1) {
			vec2 q = vec2(abs(rest.x) - 0.026, rest.z - 0.04);
			spots = (1.0 - smoothstep(0.009, 0.012, length(q))) * back;
		}
		float rim = part > 0.1 && part < 0.3 ? smoothstep(0.6, 0.9, at.x) : 0.0;
		pale = mix(pale, black, max(spots, rim));
		c = mix(c, pale, flash_now);
	}
	// (an iridescent sheen where the skin turns away)
	c = mix(c, vec3(0.75, 0.82, 0.86), 0.1 * pow(edge, 2.5));
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.4;
}
