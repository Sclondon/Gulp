shader_type spatial;
// The pyrosome (pyrosome.gd): its thousands of members and their lights drawn here (no texture files), its sway like
// a windsock, its bend, and the waves of light that run along it. What each point is comes from the model
// (tools/build_pyrosome.py): UV2.y the part (0 the outer wall, 1 the open end's lip and diaphragm, 2 the inner wall);
// UV.y how far along (0 the closed end .. 1 the open end).
//
// It swims closed end first: the closed end is at -Z, the open end at +Z. The members (zooids) are drawn in
// staggered rows over the outer wall, ZOOIDS_AROUND round it: each a low pale dome with a dark opening and a pair of
// small light organs beside it. What lights up (EMISSION): those light organs, in waves that run along the colony
// from the closed end to the open end (`pulses` a beat, `light_waves` on it at once), each member a little out of
// step with its neighbours; and a faint blue-green glow over the whole tunic and inside its mouth. Everything that
// moves goes by `phase` alone, so it loops. Nothing here needs more than GL Compatibility has. One opaque draw, back
// faces culled.
render_mode cull_back;

const float LENGTH = 2.0;
const float ZOOIDS_AROUND = 72.0;
const float ZOOID_ALONG = 0.022;

// How far through a beat (0..1, it wraps). Set by Pyrosome.
uniform float phase = 0.0;
// Waves of light that pass along it in a beat (a whole number), and how many stand on it at once.
uniform float pulses = 1.0;
uniform float light_waves = 1.6;
// How much it sways: 1 a slow wave running back along it, the open end swinging most (about 0.08 m either way), 0
// still (as built), 2 twice as much. `sway_waves` waves stand on it at once.
uniform float sway = 1.0;
uniform float sway_waves = 0.7;
// Bent round to one side behind its closed end, radians from end to end (more than 0 the open end comes round to +X).
uniform float curl = 0.0;
// How strongly it glows (0 dark, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;
// Its pale blue-green tunic, the members' openings, its light.
uniform vec3 tunic : source_color = vec3(0.62, 0.8, 0.8);
uniform vec3 opening : source_color = vec3(0.2, 0.3, 0.32);
uniform vec3 inside : source_color = vec3(0.32, 0.45, 0.48);
uniform vec3 light_colour : source_color = vec3(0.35, 1.0, 0.85);

varying float part;
varying vec3 rest;

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

// How far it is pushed aside (x, y) at `s` along it (0 the closed end, 1 the open end).
vec2 swing(float s) {
	float w = 6.2831853 * (phase - sway_waves * s);
	float reach = 0.085 * sway * pow(s, 1.6);
	return vec2(reach * sin(w), 0.35 * reach * sin(w + 1.3));
}

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float s = clamp((v.z + 1.0) / LENGTH, 0.0, 1.0);
	vec2 h = swing(s);
	vec2 slope = (swing(s + 0.005) - swing(s - 0.005)) / (0.01 * LENGTH);
	// (the ways round it and along it, for the members' domes in the fragment shader)
	float around = atan(v.x, v.y);
	TANGENT = vec3(cos(around), -sin(around), 0.0);
	BINORMAL = vec3(0.0, 0.0, 1.0);
	v.xy += h;
	// (the normal tipped by the sway's slope)
	n = normalize(vec3(n.x - slope.x * n.z, n.y - slope.y * n.z, n.z + slope.x * n.x + slope.y * n.y));
	if (abs(curl) > 0.001) {
		float d = v.z + 1.0;
		float k = curl / LENGTH;
		float a = d * k;
		float r = 1.0 / k;
		float c = cos(a);
		float sn = sin(a);
		n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
		v = vec3(r - (r - v.x) * c, v.y, -1.0 + (r - v.x) * sn);
	}
	VERTEX = v;
	NORMAL = n;
}

// How bright the light organs are at `s` along it, for a member with its own number `own`.
float lit_at(float s, float own) {
	float w = 0.5 + 0.5 * sin(6.2831853 * (pulses * phase - light_waves * s) + own * 1.2);
	return 0.12 + 0.88 * w * w * w * w;
}

void fragment() {
	int p = int(part + 0.5);
	float s = clamp((rest.z + 1.0) / LENGTH, 0.0, 1.0);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	vec3 e = vec3(0.0);
	float rough = 0.5;
	if (p == 0) {
		// The members, in staggered rows: where this point is in its member's cell.
		float a = atan(rest.x, rest.y) / 6.2831853 + 0.5;
		float row = floor(rest.z / ZOOID_ALONG);
		float col = a * ZOOIDS_AROUND + 0.5 * mod(row, 2.0);
		vec2 cell = vec2(floor(col), row);
		vec2 f = vec2(fract(col), fract(rest.z / ZOOID_ALONG)) - 0.5;
		float own = hash2(cell);
		f += (vec2(hash2(cell + 3.7), hash2(cell + 7.1)) - 0.5) * 0.18;
		float d = length(f * vec2(1.0, 1.05));
		// (a low dome: its slope tips the normal, so each member catches the light)
		float dome = max(0.0, 1.0 - d * d / 0.2);
		vec2 grad = -f * 2.0 / 0.2 * step(d, 0.447);
		NORMAL_MAP = normalize(vec3(-grad.x * 0.35, -grad.y * 0.35, 1.0)) * 0.5 + 0.5;
		c = mix(tunic * 0.82, tunic * 1.08, dome);
		// its opening, towards the open end of the colony; its two light organs, either side of it
		float hole = 1.0 - smoothstep(0.07, 0.11, length(f - vec2(0.0, 0.08)));
		c = mix(c, opening, hole * 0.85);
		float organs = 1.0 - smoothstep(0.06, 0.11, min(length(f - vec2(-0.17, -0.05)), length(f - vec2(0.17, -0.05))));
		c = mix(c, vec3(0.8, 1.0, 0.95), organs * 0.6);
		// (the closed end's tip is bare tunic)
		float bare = smoothstep(0.0, 0.014, s);
		organs *= bare;
		c = mix(tunic, c, bare);
		c = mix(c, tunic * 1.15, 0.3 * glance * glance);
		// (the light: the organs, and the tunic round them lit up as the wave passes)
		float wave = lit_at(s, own);
		e = light_colour * (organs * wave * 2.6 + 0.3 * wave * wave * bare) + tunic * 0.04;
	} else if (p == 1) {
		// The lip and diaphragm: smooth tunic, glowing a little at its edge.
		c = tunic * 0.95;
		e = light_colour * 0.18 * lit_at(s, 0.0) + tunic * 0.05;
	} else {
		// The inside: darker, a faint glow.
		c = inside;
		e = light_colour * 0.08 * lit_at(s, 0.5);
		rough = 0.7;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.4;
	EMISSION = e * glow;
}
