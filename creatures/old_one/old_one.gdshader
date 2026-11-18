shader_type spatial;
// The old one (old_one.gd): every marking drawn here (no texture files); its breathing, its tentacles drifting
// like rope, its wings parting and its eyes lighting one by one as it stirs (`wake`). What each point is comes
// from the model (tools/build_old_one.py, whose docstring lists the parts): UV2.y the part (0 the body mound, 1
// the head, 2 an eye, 3 an eye's socket, 4 a tentacle, 5 a wing's bones, 6 a wing's skin, 7 a wing's claw, 8 weed
// on the head or body, 9 weed on a wing, 10 a knob on its back); UV2.x and UV what the build script says.
//
// All of it is a function of `phase` (0..1 through one slow breath) and `wake`, so a film of it loops exactly.
// Nothing here needs more than GL Compatibility has. One opaque draw, back faces culled (the skins of the wings
// and the weed are closed or two-sheeted in the model).
render_mode cull_back;

// Kept in step with the model (as the build script has them).
const vec3 HEAD_A = vec3(0.0, 6.5, -5.0);
const vec3 HEAD_B = vec3(0.0, 19.5, 3.0);
const vec3 BODY_C = vec3(0.0, -1.2, 8.0);
const vec3 WRIST = vec3(9.5, 27.0, 8.0);
const vec3 SPREAD_AXIS = vec3(0.8969, 0.2393, 0.3719);
const float EYES = 10.0;

// How far through one breath (0..1, it wraps). Set by OldOne.
uniform float phase = 0.0;
// Asleep (0) to stirring (1): its eyes open one by one and brighten, its tentacles lift and writhe wider, its
// wings part and lift, its head rises, its glow brightens.
uniform float wake : hint_range(0.0, 1.0) = 0.0;
// How deeply it breathes (1 as built; 0 still), and how far its tentacles drift (1 as built).
uniform float breathe = 1.0;
uniform float drift = 1.0;

// Its skin: the dark of its back, the skin of its head and arms, the paler underside of its tentacles and
// face, the silt settled on it, its wings' skin and veins, bone and claw, the weed, the glow and its eyes.
uniform vec3 dark : source_color = vec3(0.07, 0.13, 0.14);
uniform vec3 skin : source_color = vec3(0.2, 0.33, 0.33);
uniform vec3 pale : source_color = vec3(0.45, 0.56, 0.52);
uniform vec3 silt : source_color = vec3(0.36, 0.38, 0.33);
uniform vec3 wing_skin : source_color = vec3(0.14, 0.22, 0.23);
uniform vec3 vein : source_color = vec3(0.07, 0.11, 0.12);
uniform vec3 bone : source_color = vec3(0.62, 0.66, 0.6);
uniform vec3 weed : source_color = vec3(0.2, 0.27, 0.09);
uniform vec3 glow_colour : source_color = vec3(0.45, 1.0, 0.85);
uniform vec3 eye_colour : source_color = vec3(0.78, 1.0, 0.95);
// How strongly its spots glow, asleep (it is brighter as it wakes).
uniform float glow = 1.0;

// The cartoon eye (0 a plain glowing eye, 1 the cartoon eye: a thin dark slit of a pupil, a dark rim and a
// glint), where its eyes look (x across, y up, -1..1) and its lids (0 as `wake` has them, 1 shut).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

varying vec3 rest;
varying vec3 rest_normal;
varying float part;
varying float extra;
varying vec2 at;

float hash1(float x) {
	return fract(sin(x * 127.1) * 43758.5453);
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

float noise3(vec3 p) {
	return noise2(p.xz + p.y * 0.71) * 0.5 + noise2(p.zy * 1.13 + 7.0) * 0.5;
}

// Turns `v` about an axis through `o` by `a` radians.
vec3 turn(vec3 v, vec3 o, vec3 axis, float a) {
	vec3 d = v - o;
	float c = cos(a);
	float s = sin(a);
	return o + d * c + cross(axis, d) * s + axis * dot(axis, d) * (1.0 - c);
}

// How far eye `i` (0..EYES-1) is open: a slit asleep, opening in its turn as it wakes.
float eye_open(float i) {
	float order = fract(i * 0.618 + 0.13);
	float from = order * 0.62;
	return mix(0.24, 1.0, smoothstep(from, from + 0.18, wake)) * (1.0 - clamp(blink, 0.0, 1.0));
}

void vertex() {
	part = UV2.y;
	extra = UV2.x;
	at = UV;
	rest = VERTEX;
	rest_normal = NORMAL;
	int p = int(part + 0.5);
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float w = clamp(wake, 0.0, 1.0);
	float a = TAU * phase;
	float br = sin(a) * breathe;
	vec3 axis = normalize(HEAD_B - HEAD_A);
	float axis_len = length(HEAD_B - HEAD_A);
	if (p == 1 || p == 2 || p == 3 || (p == 8 && UV2.x > 0.5)) {
		// The head swells and settles with each breath (not at its face, where the tentacles grow), and rises a
		// little as it stirs.
		vec3 d = v - HEAD_A;
		float t = dot(d, axis) / axis_len;
		vec3 radial = d - axis * (t * axis_len);
		float k = smoothstep(0.0, 0.45, t);
		v += radial * (0.035 * br * (1.0 + 0.5 * w)) * k;
		v.y += (1.4 * w + 0.15 * br) * k;
	} else if (p == 0 || p == 10 || p == 8) {
		// The body breathes a little.
		v += (v - BODY_C) * (0.008 * br);
	} else if (p == 4) {
		// A tentacle drifts like a rope in the water, its far end most; stirring, its end lifts and writhes wider.
		float s = UV.y;
		float id = UV2.x * 16.0;
		float reach = drift * s * s * (1.4 + 1.6 * w);
		vec3 sway = vec3(sin(a + id * 1.7 - s * 5.0), 0.5 + 0.5 * sin(2.0 * a + id * 2.3 - s * 4.0), cos(a + id * 2.9 - s * 4.5));
		v += sway * reach;
		v.y += w * (2.5 + 4.5 * hash1(id + 0.5)) * smoothstep(0.2, 1.0, s) * (0.75 + 0.25 * sin(a + id));
	} else if (p >= 5 && p <= 7 || p == 9) {
		// A wing: its hand spreads about the wrist (the leading finger most), and the whole of it lifts and parts
		// from the body as it stirs, breathing a little; built for the right wing, mirrored for the left.
		float sx = v.x >= 0.0 ? 1.0 : -1.0;
		vec3 r = vec3(v.x * sx, v.y, v.z);
		vec3 rn = vec3(n.x * sx, n.y, n.z);
		float fan = UV.x;
		float att = UV.y;
		float spread = (0.55 * w + 0.03 * br) * fan;
		r = turn(r, WRIST, SPREAD_AXIS, spread);
		rn = turn(rn, vec3(0.0), SPREAD_AXIS, spread);
		r += att * (w * vec3(2.5, 3.5, -1.0) + vec3(0.3, 0.35, 0.0) * br);
		v = vec3(r.x * sx, r.y, r.z);
		n = vec3(rn.x * sx, rn.y, rn.z);
	}
	if (p == 8 || p == 9) {
		// Weed sways in the water, its tip most.
		float f = p == 9 ? UV2.x : UV.y;
		float seed = rest.x * 0.37 + rest.z * 0.23 - f * 1.5;
		v += vec3(sin(a + seed), 0.0, cos(2.0 * a + seed * 1.3)) * (f * f * (0.9 + 0.6 * w));
	}
	VERTEX = v;
	NORMAL = n;
}

// Glowing freckles: small spots scattered over its skin, `scale` per metre.
float freckles(vec3 q, float scale) {
	vec3 c = q * scale;
	vec3 cell = floor(c);
	vec3 f = fract(c) - 0.5;
	float h = hash2(cell.xy + cell.z * 17.3 + 3.1);
	vec3 o = vec3(hash2(cell.yz + 1.7), hash2(cell.zx + 9.2), hash2(cell.xy + 4.4)) - 0.5;
	return step(0.8, h) * (1.0 - smoothstep(0.1, 0.18, length(f - o * 0.5)));
}

vec3 eye_colour_at(vec2 e, float open, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	// the lids: an almond opening, as wide as `open` lets it be
	float height = open * 0.92 * sqrt(max(1.0 - e.x * e.x, 0.0));
	float shown = 1.0 - smoothstep(height - aa, height + aa, abs(e.y));
	// the eye: pale and glowing, brighter in the middle
	vec3 c = mix(eye_colour, eye_colour * vec3(0.35, 0.75, 0.75), smoothstep(0.25, 0.75, r));
	c = mix(c, eye_colour * 0.25, smoothstep(0.78, 0.95, r));
	lit = 0.35 + 0.65 * (1.0 - smoothstep(0.0, 0.7, r));
	if (cartoon_eyes > 0.0) {
		vec2 q = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * vec2(0.3, 0.2);
		float slit = length(q / vec2(0.09, 0.62));
		float iris = length(q);
		vec3 toon = mix(c, eye_colour * 0.75, smoothstep(0.35, 0.6, iris) * 0.5);
		toon = mix(toon, vec3(0.01, 0.02, 0.02), 1.0 - smoothstep(1.0 - aa * 8.0, 1.0 + aa * 8.0, slit));
		float glint = 1.0 - smoothstep(0.1, 0.14, length(e - vec2(0.3, 0.32)));
		toon = mix(toon, vec3(1.0), glint);
		toon = mix(toon, vec3(0.01, 0.03, 0.03), smoothstep(0.8, 0.9, r));
		c = mix(c, toon, cartoon_eyes);
	}
	vec3 lid = mix(dark, skin, 0.45);
	// (a dark line along the lids' edges)
	float edge = smoothstep(height - 0.12, height - 0.02, abs(e.y)) * shown;
	c = mix(c, vec3(0.01, 0.02, 0.02), edge * 0.8);
	lit *= shown * (1.0 - edge);
	return mix(lid, c, shown);
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.7;
	float spec = 0.3;
	vec3 emit = vec3(0.0);
	float w = clamp(wake, 0.0, 1.0);
	float glow_now = glow * (0.25 + 0.75 * w);
	float grain = noise3(rest * 1.4);
	float blotch = noise3(rest * 0.22 + 4.0);
	float up = rest_normal.y;
	if (p == 0 || p == 10) {
		// The body: dark and mottled, silt settled thick on top.
		c = mix(dark, skin, smoothstep(0.3, 0.7, blotch));
		c *= 0.85 + 0.25 * grain;
		c = mix(c, silt, smoothstep(0.2, 0.8, up) * (0.45 + 0.4 * noise3(rest * 0.6)));
		if (p == 10) {
			c = mix(c, bone * 0.7, smoothstep(0.4, 1.0, at.y) * 0.6);
		}
		emit = glow_colour * freckles(rest, 0.9) * glow_now * 0.8;
	} else if (p == 1 || p == 3) {
		// The head: darker over its crown, paler towards its face, wrinkled, with glowing freckles round the face.
		float t = at.y;
		c = mix(pale * 0.8, skin, smoothstep(0.0, 0.25, t));
		c = mix(c, dark, smoothstep(0.35, 0.9, t) * 0.75 * (0.6 + 0.4 * blotch));
		float wrinkle = noise2(vec2(at.x * 60.0, t * 22.0));
		c *= 0.82 + 0.3 * wrinkle;
		c = mix(c, silt, smoothstep(0.55, 0.95, up) * smoothstep(0.3, 0.6, t) * 0.4);
		if (p == 3) {
			c = mix(c, dark, 0.3);
		}
		emit = glow_colour * freckles(rest, 1.3) * (1.0 - smoothstep(0.1, 0.45, t)) * glow_now;
		rough = 0.55;
		spec = 0.4;
	} else if (p == 2) {
		float i = floor(extra * EYES);
		float lit;
		c = eye_colour_at(at, eye_open(i), lit);
		emit = eye_colour * lit * (0.3 + 0.7 * smoothstep(0.2, 1.0, eye_open(i)));
		rough = lit > 0.01 ? 0.2 : 0.65;
		spec = 0.6;
	} else if (p == 4) {
		// A tentacle: darker on top, pale beneath with a double row of suckers, darker to its tip.
		float s = at.y;
		float around = at.x;
		float d = min(around, 1.0 - around);
		float under = 1.0 - smoothstep(0.08, 0.2, d);
		c = mix(skin * (0.85 + 0.3 * blotch), dark, 0.45 * smoothstep(0.3, 0.5, d));
		c = mix(c, pale, under);
		float rows = 34.0;
		vec2 cell = vec2(fract(s * rows) - 0.5, (d - 0.05) * 9.0);
		float sucker = 1.0 - smoothstep(0.22, 0.32, length(cell));
		c = mix(c, pale * 1.25, sucker * under * (1.0 - smoothstep(0.85, 1.0, s)));
		c = mix(c, c * 0.55, smoothstep(0.7, 1.0, s));
		c *= 0.88 + 0.22 * grain;
		emit = glow_colour * freckles(rest, 1.6) * (1.0 - under) * glow_now * 0.8;
		rough = 0.5;
		spec = 0.45;
	} else if (p == 5) {
		// A wing's bones: dark ridged skin over them, paler at the knuckles.
		c = mix(dark, skin, 0.4 + 0.3 * blotch);
		c *= 0.8 + 0.3 * noise2(vec2(rest.y * 3.0, rest.x * 3.0 + rest.z));
		c = mix(c, silt, smoothstep(0.5, 0.95, up) * 0.35);
	} else if (p == 6) {
		// A wing's skin: thin and dark, veined along its fingers and across, its edge darker and ragged.
		float v = extra;
		float fan = at.x * 3.0;
		float along_vein = 1.0 - smoothstep(0.0, 0.06, abs(fract(fan * 2.0 + 0.5) - 0.5) - 0.0);
		float across = 1.0 - smoothstep(0.0, 0.03, abs(fract(v * 5.0 + noise2(rest.xz * 0.2)) - 0.5) - 0.44);
		c = wing_skin * (0.8 + 0.35 * blotch);
		c = mix(c, vein, max(along_vein * 0.6, across * 0.35));
		c = mix(c, vein * 0.7, smoothstep(0.85, 1.0, v));
		c *= 0.85 + 0.2 * grain;
		c = mix(c, silt, smoothstep(0.6, 1.0, up) * 0.3);
		rough = 0.6;
	} else if (p == 7) {
		// A claw: old bone, dark at its root.
		c = mix(bone * 0.75, bone, grain);
		rough = 0.4;
		spec = 0.5;
	} else {
		// Weed: olive, browner and paler to its tip.
		float f = p == 9 ? extra : at.y;
		c = mix(weed * 0.7, weed * vec3(1.35, 1.2, 0.8), f);
		c *= 0.85 + 0.3 * noise2(vec2(f * 6.0, rest.x + rest.z));
		rough = 0.8;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = emit;
}
