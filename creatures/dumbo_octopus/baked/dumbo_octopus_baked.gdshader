shader_type spatial;
// The dumbo octopus (dumbo_octopus.gd): every marking drawn here (no texture files), its fins' flapping, its web
// opening and closing, its bend, and its faint glow. What each point is comes from the model
// (tools/build_dumbo_octopus.py): UV2.y the part (0 the body, 1 the web's outside, 2 the web's underside and the
// underside of the body, 3 a fin, 4 an eye); UV2.x on the web how far along it from its root (metres; 0 on the body).
// UV on the web: x how far along it (0 its root, 1 its edge); on a fin: x root (0) to tip (1), y leading edge (0) to
// trailing edge (1); on an eye: its own plane, x towards the front, y up, 1 at its rim.
//
// It floats upright facing -Z. The web is bent along its length as the build script lays it (it leaves its root at
// THETA0 from straight down and curls outward by KAPPA radians a metre): the shader lays it again with more curl
// (open) or less (shut), so it opens and closes once a beat. The fins flap `flaps` times a beat. Everything that
// moves is a function of `phase` alone, so a picture of it loops exactly. What lights up (EMISSION): a faint glow
// over all its skin, brighter along the web's edge and the fins' edges, and small pale blue lights in the suckers
// under its arms. Nothing here needs more than GL Compatibility has. One opaque draw, back faces culled.
render_mode cull_back, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// Kept in step with the model (tools/build_dumbo_octopus.py).
const float R0 = 0.0695;
const float Y0 = -0.010;
const float THETA0 = 0.2;
const float KAPPA = 5.0;
const float ARM_LONG = 0.18;
const vec3 FIN_ROOT = vec3(0.06043, 0.092, 0.0);
const vec3 EYE_BASE = vec3(0.04053, 0.034, -0.05678);
const float EYE_R = 0.0165;
const float LENGTH = 0.3;

// How far through a beat (0..1, it wraps): the web opens and closes once, the fins flap `flaps` times. Set by
// DumboOctopus.
uniform float phase = 0.0;
// Fin strokes in a beat (a whole number, so that it comes round).
uniform float flaps = 2.0;
// How much it moves: 1 as one swimming gently, 0 still (as built), 2 twice as much.
uniform float sway = 1.0;
// The web held more open (up to 1: spread wide like an umbrella) or more shut (down to -1: hanging in a bell), as
// well as its pulse.
uniform float open : hint_range(-1.0, 1.0) = 0.0;
// Turning: how far the web and arms are bent round to one side below the head, radians from the head to the arms'
// tips (more than 0: they come round to +X, its left).
uniform float curl = 0.0;
// How strongly it glows (0 none, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;

// Its pale pink-orange skin, paler beneath; the web's underside; its freckles; its suckers' light.
uniform vec3 skin : source_color = vec3(0.96, 0.6, 0.47);
uniform vec3 pale : source_color = vec3(0.99, 0.84, 0.76);
uniform vec3 web_under : source_color = vec3(0.93, 0.56, 0.5);
uniform vec3 freckle : source_color = vec3(0.72, 0.27, 0.2);
uniform vec3 light_colour : source_color = vec3(0.55, 0.85, 1.0);
uniform vec3 iris : source_color = vec3(0.22, 0.16, 0.12);

// The cartoon eye (0 the eye as made, 1 the cartoon one; Gulp uses 1). Huge, round and sweet: grown to 1.7 times, a
// big warm brown iris round a big round pupil with two bright highlights, a little white showing round it, no
// heavy lid, a soft lid line. `eye_look` slides the iris and pupil (x + towards the front, y + up; -1..1), `blink`
// closes the lid over it (0 open, 1 shut).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_white : source_color = vec3(0.97, 0.95, 0.93);
uniform vec3 eye_iris : source_color = vec3(0.36, 0.2, 0.14);
const float EYE_GROW = 1.7;
const float IRIS_R = 0.64;
const float PUPIL_R = 0.42;

varying float part;
varying float along;
varying vec3 rest;
varying vec2 at;

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

// Freckles: round spots, some cells of a grid with one each, of their own sizes (1 on a spot).
float freckles(vec3 p) {
	vec3 cell = floor(p);
	vec3 f = fract(p);
	vec3 o = vec3(hash3(cell + 1.7), hash3(cell + 4.3), hash3(cell + 8.1)) * 0.4 + 0.3;
	float r = 0.1 + 0.16 * hash3(cell + 2.9);
	return step(0.5, hash3(cell)) * (1.0 - smoothstep(r * 0.6, r, length(f - o)));
}

// The web's outer skin along its length at `d` metres from its root, curled by `k` radians a metre: (radius,
// height), and its angle from straight down.
vec3 web_line(float d, float k) {
	float th = THETA0 + k * d;
	if (abs(k) < 0.001) {
		return vec3(R0 + sin(THETA0) * d, Y0 - cos(THETA0) * d, th);
	}
	return vec3(R0 + (cos(THETA0) - cos(th)) / k, Y0 - (sin(th) - sin(THETA0)) / k, th);
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 0.03;
	float d = from - v.y;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.6 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float s = sin(a);
	n = vec3(n.x * c + n.y * s, -n.x * s + n.y * c, n.z);
	v = vec3(r - (r - v.x) * c, from - (r - v.x) * s, v.z);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	along = UV2.x;
	at = UV;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	float beat = 6.2831853 * phase;
	if ((p == 1 || p == 2) && along > 0.0) {
		// The web: laid again along its line, curled more (open) or less (shut).
		vec3 e = normalize(vec3(v.x, 0.0, v.z));
		vec3 side = vec3(-e.z, 0.0, e.x);
		vec3 was = web_line(along, KAPPA);
		vec3 tw = e * sin(was.z) - vec3(0.0, cos(was.z), 0.0);
		vec3 nw = e * cos(was.z) + vec3(0.0, sin(was.z), 0.0);
		vec3 o = v - (e * was.x + vec3(0.0, was.y, 0.0));
		float ot = dot(o, tw);
		float on = dot(o, nw);
		float os = dot(o, side);
		float angle = atan(e.x, -e.z);
		float k = KAPPA + open * 4.0 + sway * (3.0 * cos(beat) + 0.9 * sin(beat + 3.0 * angle));
		vec3 now = web_line(along, k);
		vec3 tn = e * sin(now.z) - vec3(0.0, cos(now.z), 0.0);
		vec3 nn = e * cos(now.z) + vec3(0.0, sin(now.z), 0.0);
		v = e * now.x + vec3(0.0, now.y, 0.0) + tn * ot + nn * on + side * os;
		float turn = now.z - was.z;
		float ne = dot(n, e);
		float ns = dot(n, side);
		n = e * (ne * cos(turn) - n.y * sin(turn)) + vec3(0.0, ne * sin(turn) + n.y * cos(turn), 0.0) + side * ns;
	} else if (p == 3) {
		// A fin: it flaps about its root, the tip a little behind the root.
		float sx = sign(v.x);
		vec3 root = vec3(sx * FIN_ROOT.x, FIN_ROOT.y, FIN_ROOT.z);
		float a = sx * sway * 0.42 * sin(beat * flaps - 0.9 * UV.x) * (0.35 + 0.65 * UV.x);
		float c = cos(a);
		float s = sin(a);
		vec3 d = v - root;
		v = root + vec3(d.x * c - d.y * s, d.x * s + d.y * c, d.z);
		n = vec3(n.x * c - n.y * s, n.x * s + n.y * c, n.z);
	} else if (p == 4) {
		// An eye: grown about its middle for the cartoon eye, squashed a little as it blinks.
		vec3 base = vec3(sign(v.x) * EYE_BASE.x, EYE_BASE.y, EYE_BASE.z);
		vec3 d = (v - base) * mix(1.0, EYE_GROW, cartoon_eyes);
		d.y *= 1.0 - 0.3 * blink * cartoon_eyes;
		v = base + d;
	}
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = n;
}

// The cartoon eye at `q` (its own plane: x towards the front, y up, 1 at the rim), its lid the colour `lid`;
// `lidded` says where the lid covers it.
vec3 cartoon_eye(vec2 q, vec3 lid, out float lidded) {
	float r = length(q);
	float aa = max(fwidth(r), 0.01) * 1.2;
	vec2 iq = q - clamp(eye_look, vec2(-1.0), vec2(1.0)) * 0.16;
	float ir = length(iq);
	vec3 c = eye_white * (1.0 - 0.18 * smoothstep(0.4, 0.82, r));
	// the iris: warm, lighter low in it; a darker ring at its edge; the big round pupil
	vec3 ring = eye_iris * (0.6 + 0.8 * smoothstep(IRIS_R, 0.0, length(iq - vec2(0.0, -0.35 * IRIS_R))));
	ring = mix(ring, eye_iris * 0.3, smoothstep(IRIS_R * 0.8, IRIS_R, ir));
	c = mix(c, ring, 1.0 - smoothstep(IRIS_R - aa, IRIS_R + aa, ir));
	c = mix(c, vec3(0.012, 0.008, 0.01), 1.0 - smoothstep(PUPIL_R - aa, PUPIL_R + aa, ir));
	// two highlights that stay put towards the light: a big one up and to the front, a small one below
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.17 - aa, 0.17 + aa, length(q - vec2(0.2, 0.26))));
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.075 - aa, 0.075 + aa, length(q - vec2(-0.18, -0.24))));
	// the dark outline, then the skin round it out to the rim
	c = mix(c, vec3(0.16, 0.06, 0.05), smoothstep(0.82 - aa, 0.82 + aa, r));
	float skirt = smoothstep(0.92 - aa, 0.92 + aa, r);
	// the lid: out of sight above it, closing with `blink`
	float edge = mix(1.1, -1.1, clamp(blink, 0.0, 1.0));
	c = mix(c, vec3(0.3, 0.1, 0.08), (1.0 - smoothstep(0.0, 0.07, abs(q.y - edge + 0.05))) * step(r, 0.92) * step(0.02, blink));
	lidded = max(smoothstep(edge - aa, edge + aa, q.y), skirt);
	return mix(c, lid, lidded);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	EMISSION = texture(baked_glow, bake_uv).rgb * baked_glow_scale;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

