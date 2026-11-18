shader_type spatial;
// The nudibranch (nudibranch.gd), a Spanish shawl: its colours, and all of its moving. What each
// point is comes from the model (tools/build_nudibranch.py): UV2.y the part (0 body, 1 a ceras,
// 2 a rhinophore, 3 an oral tentacle). UV, on the body: x how far along (0 head to 1 tail), y how
// high (0 the foot to 1 the top of the back); on anything else: x from its root (0) to its tip
// (1). UV2.x, on anything but the body, a number of its own (0..1).
//
// It crawls with a slow ripple that runs back along its body, its cerata waving; and it swims
// (`swim` 1) by flexing its whole body to one side into a U, then to the other. All of it is a
// function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model: its length, and its origin is under its middle.
const float LENGTH = 0.07;
const float HALF = 0.035;

// How far through a beat (0..1, it wraps). Set by Nudibranch.
uniform float phase = 0.0;
// 0 crawling on the bottom, 1 swimming: flexing into a U one way then the other.
uniform float swim : hint_range(0.0, 1.0) = 0.0;
// How strongly it moves at all (1 as it lives, 0 still).
uniform float sway = 1.0;
// How far round it bends at the height of a swimming stroke (radians, from head to tail).
uniform float flex = 2.7;
// How many ripples lie along its body as it crawls.
uniform float ripples = 2.0;

// The body, and the paler violet of its foot's edge, its head and the tips of its tentacles.
uniform vec3 body : source_color = vec3(0.38, 0.06, 0.82);
uniform vec3 body_pale : source_color = vec3(0.62, 0.3, 0.98);
// The cerata, and their tips.
uniform vec3 cerata : source_color = vec3(1.0, 0.36, 0.02);
uniform vec3 cerata_tip : source_color = vec3(1.0, 0.62, 0.12);
// The rhinophores.
uniform vec3 rhinophore : source_color = vec3(0.8, 0.03, 0.08);
// How much of its colour shows without any light on it (it is vivid even in dim water).
uniform float vivid = 0.18;

varying vec3 rest;
varying float part;

// The body laid round an arc about its middle: more than 0 and both its ends come round to +X.
void arc(inout vec3 v, inout vec3 n, float k) {
	if (abs(k) < 0.01) {
		return;
	}
	float a = v.z * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, (r - v.x) * sn);
}

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float along = (v.z + HALF) / LENGTH;
	float turn = TAU * phase;
	float crawl = sway * (1.0 - swim);
	float stroke = sin(turn);
	if (part > 0.5) {
		// What stands on it waves from its root: a wave running back along the mane, no two
		// stalks quite together; and as it swims they trail behind the body's swing.
		float reach = part < 1.5 ? 0.0036 : (part < 2.5 ? 0.0012 : 0.0032);
		float w = UV.x * UV.x * reach * sway * (1.0 + 0.8 * swim);
		float a = turn - along * 7.0 + UV2.x * 2.2;
		v.x += w * sin(a);
		v.z += w * 0.7 * cos(a + UV2.x * 1.3);
		v.x -= UV.x * UV.x * 0.004 * sway * swim * cos(turn) * (0.4 + abs(along - 0.5) * 2.4);
	}
	// Crawling: a ripple that runs back along the body (it swells and sinks a little as each
	// passes), and the head and the tail swinging slowly from side to side.
	float ripple = sin(turn - along * ripples * TAU);
	float low = 1.0 - smoothstep(0.0, 0.006, v.y);
	v.x *= 1.0 + crawl * 0.08 * ripple * (part < 0.5 ? 1.0 : 0.35);
	v.y *= 1.0 - crawl * 0.05 * ripple * (1.0 - low);
	v.z += crawl * 0.0009 * cos(turn - along * ripples * TAU);
	float ends = (along - 0.5) * 2.0;
	v.x += crawl * 0.0022 * ends * ends * sin(turn - along * 2.2);
	// Swimming: the whole body bent round to one side, then the other.
	arc(v, n, sway * swim * flex * stroke / LENGTH);
	VERTEX = v;
	NORMAL = n;
}

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

float noise2(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash2(i), hash2(i + vec2(1.0, 0.0)), f.x), mix(hash2(i + vec2(0.0, 1.0)), hash2(i + vec2(1.0, 1.0)), f.x), f.y);
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.35;
	if (p == 0) {
		// The body: violet, paler along the edge of the foot and at the front of the head.
		float grain = noise2(rest.zx * 2600.0);
		c = mix(body, body_pale, 0.75 * (1.0 - smoothstep(0.0, 0.25, UV.y)));
		c = mix(c, body_pale, 0.45 * (1.0 - smoothstep(0.0, 0.08, UV.x)));
		c *= 0.93 + 0.14 * grain;
	} else if (p == 1) {
		// A ceras: violet where it joins the back, orange above, brighter at its tip.
		c = mix(body, cerata, smoothstep(0.03, 0.2, UV.x));
		c = mix(c, cerata_tip, smoothstep(0.55, 1.0, UV.x));
	} else if (p == 2) {
		// A rhinophore: scarlet, darker between its rings.
		float leaf = 0.5 + 0.5 * sin(TAU * 9.0 * UV.x - 1.57);
		c = mix(body, rhinophore, smoothstep(0.02, 0.2, UV.x));
		c *= mix(1.0, 0.55 + 0.45 * leaf, smoothstep(0.2, 0.32, UV.x));
	} else {
		// An oral tentacle: violet, paler towards its tip.
		c = mix(body, body_pale, smoothstep(0.2, 1.0, UV.x));
	}
	// (soft, half-clear flesh: it brightens where it is seen edge on)
	c += c * 0.6 * glance * glance;
	ALBEDO = c;
	EMISSION = c * vivid;
	ROUGHNESS = rough;
	SPECULAR = 0.45;
}
