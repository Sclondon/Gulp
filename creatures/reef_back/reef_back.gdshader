shader_type spatial;
// The reef-back (reef_back.gd): every marking drawn here (no texture files); the kelp on its back and its gill
// frills swaying, its throat glowing (`glow`), and a bend round to one side for a turn (`curl`). Its walk and its
// jaw are its skeleton's (the node plays the clips); this works on the skinned points. What each point is comes
// from the model (tools/build_reef_back.py, whose docstring lists the parts): UV2.y the part (0 skin, 1 the lower
// jaw, 2 inside the mouth, 3 a rock plate, 4 coral, 5 kelp, 6 a barnacle, 7 a sponge, 8 a gill frill, 9 a claw,
// 10 an eye, 11 the fin along its tail); UV2.x and UV what the build script says.
//
// All of it is a function of `phase`, so a film of it loops. Nothing here needs more than GL Compatibility has.
// One opaque draw, back faces culled (the kelp, frills and fin are two sheets back to back in the model).
render_mode cull_back;

// Kept in step with the model (as the build script has them).
const float NOSE = -17.5;
const float LENGTH = 35.0;

// How far through the clip it is playing (0..1, it wraps). Set by ReefBack.
uniform float phase = 0.0;
// How brightly its throat glows (0 dark; 1 as built).
uniform float glow = 1.0;
// Turning: how far its body is bent round to one side behind its shoulders, radians from the shoulders to the tail
// tip (more than 0, the tail comes round to +X).
uniform float curl = 0.0;
// How far the weed on its back sways (1 as built).
uniform float sway = 1.0;

// Its skin: the dark of its back, the green of its flanks, its belly, its pale spots; the throat's glow; inside its
// mouth; the rock of its plates and the lichen on them; coral, kelp, barnacle, sponge, frill, claw and eye.
uniform vec3 back : source_color = vec3(0.07, 0.2, 0.19);
uniform vec3 flank : source_color = vec3(0.16, 0.4, 0.34);
uniform vec3 belly : source_color = vec3(0.32, 0.46, 0.33);
uniform vec3 spot : source_color = vec3(0.38, 0.66, 0.52);
uniform vec3 glow_colour : source_color = vec3(0.35, 1.0, 0.6);
uniform vec3 mouth : source_color = vec3(0.42, 0.13, 0.15);
uniform vec3 rock : source_color = vec3(0.4, 0.42, 0.4);
uniform vec3 lichen : source_color = vec3(0.42, 0.45, 0.2);
uniform vec3 coral : source_color = vec3(0.85, 0.42, 0.45);
uniform vec3 kelp : source_color = vec3(0.3, 0.33, 0.1);
uniform vec3 barnacle : source_color = vec3(0.78, 0.74, 0.62);
uniform vec3 sponge : source_color = vec3(0.55, 0.55, 0.16);
uniform vec3 frill : source_color = vec3(0.9, 0.48, 0.55);
uniform vec3 claw : source_color = vec3(0.06, 0.07, 0.07);
uniform vec3 iris : source_color = vec3(0.62, 0.95, 0.78);

// The cartoon eye (0 a plain eye, 1 the cartoon eye: an old, sleepy, gentle look: a big pale green iris, a round
// dark pupil, a glint, a heavy upper lid half down), where its eyes look (x towards the nose, y up, -1..1) and its
// lids (0 open, 1 shut).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

varying float part;
varying float extra;
varying vec2 at;
varying vec3 rest_normal;

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

// Spots: round, of two sizes, scattered (`q` in metres on the skin's own unwrapping).
float spots(vec2 q) {
	vec2 cell = floor(q);
	vec2 f = fract(q) - 0.5;
	float h = hash2(cell);
	vec2 o = vec2(hash2(cell + 7.1), hash2(cell + 3.3)) - 0.5;
	float r = mix(0.12, 0.3, hash2(cell + 1.9));
	return step(0.45, h) * (1.0 - smoothstep(r * 0.75, r, length(f - o * 0.45)));
}

void vertex() {
	part = UV2.y;
	extra = UV2.x;
	at = UV;
	rest_normal = NORMAL;
	int p = int(part + 0.5);
	vec3 v = VERTEX;
	float a = TAU * phase;
	if (p == 5) {
		// Kelp sways, its tip most.
		float f = UV2.x;
		float seed = UV.x * 6.283;
		v += vec3(sin(a + seed), 0.0, cos(2.0 * a + seed * 1.7)) * (f * f * 1.1 * sway);
	} else if (p == 8) {
		// The frills ripple.
		float f = UV2.x;
		v.x += sign(v.x) * sin(2.0 * a + UV.x * 5.0) * 0.12 * f;
	} else if (p == 4) {
		// Coral nods a little.
		v.x += sin(a + v.z * 0.3) * 0.08 * UV2.x * sway;
	}
	// The body bent round behind the shoulders, for a turn.
	float from = -4.0;
	float d = v.z - from;
	if (abs(curl) > 0.001 && d > 0.0) {
		float k = curl / (LENGTH * 0.6);
		float ang = d * k;
		float r = 1.0 / k;
		float c = cos(ang);
		float s = sin(ang);
		NORMAL = vec3(NORMAL.x * c + NORMAL.z * s, NORMAL.y, -NORMAL.x * s + NORMAL.z * c);
		v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * s);
	}
	VERTEX = v;
}

vec3 eye_colour(vec2 e, out float lit) {
	float r = length(e);
	float aa = max(fwidth(r), 0.01);
	vec2 look = clamp(eye_look, vec2(-1.0), vec2(1.0)) * vec2(0.22, 0.16);
	vec2 q = e - look;
	// as in life: a pale green eye, a dark round pupil
	vec3 c = mix(iris, iris * 0.55, smoothstep(0.2, 0.85, length(q)));
	c = mix(c, vec3(0.02), 1.0 - smoothstep(0.26 - aa, 0.3 + aa, length(q)));
	lit = 0.35 * (1.0 - smoothstep(0.3, 0.9, r));
	if (cartoon_eyes > 0.0) {
		vec3 toon = mix(vec3(0.95, 0.97, 0.9), iris, 1.0 - smoothstep(0.62 - aa, 0.66 + aa, length(q)));
		toon = mix(toon, iris * 0.6, smoothstep(0.35, 0.62, length(q)) * (1.0 - smoothstep(0.62, 0.66, length(q))));
		toon = mix(toon, vec3(0.01), 1.0 - smoothstep(0.3 - aa, 0.33 + aa, length(q)));
		float glint = 1.0 - smoothstep(0.09, 0.13, length(e - look * 0.5 - vec2(0.22, 0.24)));
		toon = mix(toon, vec3(1.0), glint);
		toon = mix(toon, vec3(0.02, 0.05, 0.04), smoothstep(0.86, 0.94, r));
		// the heavy upper lid, half down, and a lower one, closing as it blinks
		float b = clamp(blink, 0.0, 1.0);
		float upper = mix(0.25 - 0.18 * e.x, -0.3, b);
		float lower = mix(-0.7, -0.32, b);
		float lid = max(smoothstep(upper - aa, upper + aa, e.y), 1.0 - smoothstep(lower - aa, lower + aa, e.y));
		float line = smoothstep(upper - 0.1, upper, e.y) * (1.0 - smoothstep(upper + 0.02, upper + 0.08, e.y));
		toon = mix(toon, flank * 0.9, lid);
		toon = mix(toon, vec3(0.02, 0.05, 0.04), line);
		c = mix(c, toon, cartoon_eyes);
		lit = mix(lit, 0.15 * (1.0 - lid), cartoon_eyes);
	} else {
		float b = clamp(blink, 0.0, 1.0);
		c = mix(c, flank * 0.9, step(1.0 - 2.0 * b, e.y));
	}
	return c;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c;
	float rough = 0.6;
	float spec = 0.35;
	vec3 emit = vec3(0.0);
	if (p == 0 || p == 1) {
		// Skin: dark on its back, green flanks, a paler belly, pale spots over its flanks and legs, a fine grain of
		// scales; on its throat and under its jaw the glow, in soft bands.
		float high;
		vec2 q;
		bool on_leg = at.x >= 2.0;
		if (on_leg) {
			high = 0.55;
			q = vec2(fract(at.x) * 9.0, at.y * 7.0);
		} else {
			high = at.y;
			q = vec2(at.x * LENGTH * 0.9, high * 9.0);
		}
		bool on_head = !on_leg && at.x < 0.21;
		c = mix(belly, flank, smoothstep(0.18, 0.4, high));
		c = mix(c, back, smoothstep(0.62, 0.85, high) * (on_head ? 0.45 : 1.0));
		float s = spots(q * 1.1) * (1.0 - smoothstep(0.8, 0.95, high)) * smoothstep(0.15, 0.3, high);
		c = mix(c, spot, s * 0.7);
		float scales = noise2(q * 7.0);
		c *= 0.86 + 0.22 * scales;
		if (!on_leg) {
			float z = at.x * LENGTH + NOSE;
			float throat = (1.0 - smoothstep(0.22, 0.4, high)) * smoothstep(-17.0, -15.5, z) * (1.0 - smoothstep(-9.5, -8.0, z));
			if (p == 1) {
				throat = (1.0 - smoothstep(0.06, 0.16, high)) * smoothstep(-16.6, -15.0, z);
			}
			float bands = 0.55 + 0.45 * smoothstep(0.2, 0.8, sin(z * 3.2 + high * 4.0) * 0.5 + 0.5);
			float pulse = 0.8 + 0.2 * sin(TAU * phase * 2.0);
			emit = glow_colour * throat * bands * pulse * glow * 0.8;
			c = mix(c, mix(c, glow_colour * 0.5, 0.6), throat * clamp(glow, 0.0, 1.0));
		}
	} else if (p == 2) {
		// Inside the mouth: dark red, darker to the throat.
		float z = at.x * LENGTH + NOSE;
		c = mix(mouth, mouth * 0.3, smoothstep(-16.5, -12.0, z));
		// (next to the lips, its skin: no red shows along a shut mouth)
		c = mix(belly * 0.6, c, smoothstep(0.2, 0.8, extra));
		rough = 0.4;
	} else if (p == 3 || p == 11) {
		// A rock plate: grey stone, darker in the cracks of its sides, patched with lichen on top; the fin along its
		// tail dark, its edge reddish.
		if (p == 3) {
			float top = at.y;
			c = rock * mix(0.75, 1.15, extra) * (0.75 + 0.25 * top);
			c *= 0.85 + 0.25 * noise2(at * 3.0 + extra * 50.0);
			float patch = smoothstep(0.55, 0.7, noise2(vec2(extra * 91.0, extra * 13.0) + rest_normal.xz * 2.0));
			c = mix(c, lichen, patch * smoothstep(0.4, 0.9, top) * 0.8);
			rough = 0.85;
			spec = 0.2;
		} else {
			c = mix(back * 0.8, vec3(0.38, 0.13, 0.1), smoothstep(0.5, 1.0, extra));
		}
	} else if (p == 4) {
		// Coral: pink, paler at its tips.
		c = mix(coral * 0.75, coral * 1.15 + 0.08, extra);
		rough = 0.7;
	} else if (p == 5) {
		// Kelp: olive, browner and paler to its tip.
		c = mix(kelp * 0.75, kelp * vec3(1.5, 1.35, 0.9), extra);
		rough = 0.75;
	} else if (p == 6) {
		// A barnacle: chalky, dark in its crater.
		c = mix(barnacle, vec3(0.08, 0.07, 0.06), extra);
		rough = 0.9;
	} else if (p == 7) {
		// A sponge: yellow-olive, dark inside its tube.
		c = mix(sponge, sponge * 0.2, extra);
		rough = 0.95;
	} else if (p == 8) {
		// A gill frill: pink, its rays darker, its edge paler.
		float rays = 1.0 - smoothstep(0.0, 0.06, abs(fract(at.x * 3.0 + 0.5) - 0.5));
		c = mix(frill, frill * 0.6, rays * 0.8);
		c = mix(c, vec3(1.0, 0.8, 0.82), smoothstep(0.75, 1.0, extra) * 0.5);
		rough = 0.5;
	} else if (p == 9) {
		// A claw: dark horn, a little paler at its point.
		c = mix(claw, claw * 3.0, smoothstep(0.6, 1.0, extra));
		rough = 0.35;
		spec = 0.5;
	} else {
		float lit;
		c = eye_colour(at, lit);
		emit = iris * lit;
		rough = 0.2;
		spec = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = emit;
}
