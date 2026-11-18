shader_type spatial;
// The moray eel (moray_eel.gd): the still model, which lies straight along +Z from its snout,
// is laid here along the eel's spine, which MorayEel simulates; its lower jaw is swung about
// its hinge, its throat swells as it breathes, its fin ripples. What each point is comes from
// the model (tools/build_moray_eel.py): COLOR.r the part (0 skin, 0.2 inside the mouth, 0.4 a
// tooth, 0.6 an eye, 0.8 the hole of a nostril, 1 the throat and the gills: COLOR.b 0 the throat's
// wall, 0.5 a gill arch, whose UV.x is along it and UV.y from its rakers' edge to the wall); COLOR.g how much it swings with the jaw;
// COLOR.b how far out on the fin it is; UV.x round the body, UV.y along it (on an eye, 0 the
// middle of the pupil to 1; on a tooth, root to point).
//
// The skin is drawn here (no texture files), after photographs of green morays (the
// component's README). Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model and the script.
const float LENGTH = 1.8;
const int POINTS = 25;
const float MOUTH = 0.115;
const float HINGE_Y = -0.007;
const float GILL_AT = 0.26;

// Set by MorayEel each frame.
// The spine: a picture POINTS wide and two high. Its top row is the body's middle line, snout
// to tail tip, in the eel's own space; its bottom row, which way the eel's back is at each.
uniform sampler2D spine : filter_nearest, repeat_disable;
// How far the lower jaw is swung open (radians), how far through a gape it is (0..1), and
// where the beat is (0..1: the fin's ripple goes by it).
uniform float jaw = 0.09;
uniform float gape = 0.0;
uniform float phase = 0.0;
// How far the fin's edge ripples from side to side (metres), and how deep the skin's wrinkles are (1 as made).
uniform float fin_ripple = 0.006;
uniform float wrinkles = 1.0;
// The skin: yellow-green, and the deeper green it is mottled and shaded with; the inside of
// the mouth; the teeth; the eye's iris.
uniform vec3 skin : source_color = vec3(0.47, 0.53, 0.13);
uniform vec3 skin_deep : source_color = vec3(0.2, 0.3, 0.09);
uniform vec3 mouth : source_color = vec3(0.4, 0.36, 0.34);
uniform vec3 tooth : source_color = vec3(0.93, 0.92, 0.86);
uniform vec3 iris : source_color = vec3(0.62, 0.72, 0.8);
// The cartoon eye (the user, 2026-11-18: "the eyes for most of them should be more cartoony and
// personalized"): 0 the eye as the species has it, 1 the cartoon eye: a moray's small mean one, only a
// little bigger, a pale icy iris round a small pupil, little white, and a heavy brow of a lid slanting
// down towards the snout in a scowl. `eye_look` slides the iris and pupil (x towards the snout, y up;
// -1..1); `blink` 0 open to 1 shut (the eye squashed flat and the lid drawn down).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The right eye's middle (metres, the model as it lies) and the way it looks out (the build prints the
// EYE line); how far round its face (UV.y) the skin covers it; the cartoon eye's width, how far it bulges
// and stands out, how far the iris slides, its size, the pupil's, and the lid's line (x towards the
// snout, y up, 1 the eye's rim).
const vec3 EYE_MIDDLE = vec3(0.02019, 0.01955, 0.05708);
const vec3 EYE_OUT = vec3(0.8146, 0.4651, -0.3466);
const float EYE_SEEN = 0.45;
const float EYE_GROW = 1.4;
const float EYE_BULGE = 1.1;
const float EYE_PUSH = 0.0015;
const float IRIS_TRAVEL = 0.18;
const float IRIS_R = 0.66;
const float PUPIL_R = 0.27;
const float LID_Y = 0.3;
const float LID_SLANT = -0.55;

varying float part;
varying float fin;
varying vec2 at;
varying vec3 rest;

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

void vertex() {
	part = COLOR.r;
	fin = COLOR.b;
	at = UV;
	rest = VERTEX;
	vec3 p = VERTEX;
	vec3 n = NORMAL;
	if (part > 0.5 && part < 0.7 && (cartoon_eyes > 0.0 || blink > 0.0)) {
		// The eye: a little bigger and prouder as a cartoon eye, squashed flat to blink.
		vec3 mid = EYE_MIDDLE;
		vec3 o = EYE_OUT;
		if (p.x < 0.0) {
			mid.x = -mid.x;
			o.x = -o.x;
		}
		vec3 up = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
		float wide = mix(1.0, EYE_GROW, cartoon_eyes);
		float proud = mix(1.0, EYE_BULGE, cartoon_eyes);
		float shut = 1.0 - 0.8 * clamp(blink, 0.0, 1.0);
		vec3 d = p - mid;
		float d_out = dot(d, o);
		vec3 flat_d = d - o * d_out;
		float d_up = dot(flat_d, up);
		p = mid + o * (d_out * proud + EYE_PUSH * cartoon_eyes) + (flat_d - up * d_up) * wide + up * (d_up * wide * shut);
		float n_out = dot(n, o);
		vec3 n_flat = n - o * n_out;
		float n_up = dot(n_flat, up);
		n = o * (n_out / proud) + (n_flat - up * n_up) / wide + up * (n_up / (wide * shut));
	}
	if (part < 0.1) {
		// It breathes: the throat swells as the mouth shuts and falls as it opens.
		float throat = smoothstep(0.07, 0.17, p.z) * (1.0 - smoothstep(0.2, 0.32, p.z)) * (1.0 - smoothstep(-0.03, 0.02, p.y));
		p += n * 0.006 * (0.5 - gape) * throat;
		// The fin's edge ripples, a wave running tailwards with the beat.
		p.x += sin((phase - p.z * 1.9) * TAU) * fin_ripple * fin * fin * smoothstep(0.2, 0.5, p.z);
	}
	// The lower jaw, swung down about its hinge (a line across the corners of the mouth).
	float turn = jaw * COLOR.g;
	vec2 arm = vec2(p.y - HINGE_Y, p.z - MOUTH);
	p.y = HINGE_Y + arm.x * cos(turn) + arm.y * sin(turn);
	p.z = MOUTH + arm.y * cos(turn) - arm.x * sin(turn);
	n = vec3(n.x, n.y * cos(turn) + n.z * sin(turn), n.z * cos(turn) - n.y * sin(turn));
	// Laid along the spine: where this point is along it, and its offset from the model's
	// middle line carried over to the spine's own right, back and way there.
	float along = clamp(p.z, 0.0, LENGTH);
	float f = along / LENGTH * float(POINTS - 1);
	int i1 = min(int(f), POINTS - 2);
	float t = f - float(i1);
	vec3 p0 = texelFetch(spine, ivec2(max(i1 - 1, 0), 0), 0).xyz;
	vec3 p1 = texelFetch(spine, ivec2(i1, 0), 0).xyz;
	vec3 p2 = texelFetch(spine, ivec2(i1 + 1, 0), 0).xyz;
	vec3 p3 = texelFetch(spine, ivec2(min(i1 + 2, POINTS - 1), 0), 0).xyz;
	// (a smooth curve through the points)
	vec3 c1 = p2 - p0;
	vec3 c2 = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3;
	vec3 c3 = 3.0 * (p1 - p2) + p3 - p0;
	vec3 on_line = 0.5 * (2.0 * p1 + c1 * t + c2 * t * t + c3 * t * t * t);
	vec3 way = normalize(0.5 * (c1 + 2.0 * c2 * t + 3.0 * c3 * t * t) + vec3(0.0, 0.0, 0.00001));
	vec3 back = mix(texelFetch(spine, ivec2(i1, 1), 0).xyz, texelFetch(spine, ivec2(i1 + 1, 1), 0).xyz, t);
	back = normalize(back - way * dot(back, way) + vec3(0.0, 0.00001, 0.0));
	vec3 right = cross(back, way);
	VERTEX = on_line + right * p.x + back * p.y + way * (p.z - along);
	NORMAL = normalize(right * n.x + back * n.y + way * n.z);
}

// The cartoon eye's colour at `e` on its face (x towards the snout, y up, 1 where the skin meets it),
// `nv` the way it faces (view space): a pale icy iris filling most of it round a small pupil, a
// highlight that stays towards the light (where the dome faces it), a dark outline.
vec3 cartoon_eye(vec2 e, vec3 nv) {
	float r = length(e);
	vec2 q = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * IRIS_TRAVEL;
	float ri = length(q);
	vec3 c = vec3(0.9, 0.9, 0.82);
	vec3 ic = mix(iris * 1.2, iris * 0.7, smoothstep(0.1, IRIS_R, ri));
	ic = mix(ic, iris * 0.3, smoothstep(IRIS_R - 0.1, IRIS_R - 0.02, ri));
	c = mix(c, ic, 1.0 - smoothstep(IRIS_R - 0.02, IRIS_R + 0.02, ri));
	c = mix(c, vec3(0.01), 1.0 - smoothstep(PUPIL_R - 0.02, PUPIL_R + 0.02, ri));
	vec3 light = normalize(vec3(-0.3, 0.35, 0.9));
	c = mix(c, vec3(1.0), smoothstep(0.993, 0.996, dot(nv, light)));
	return mix(c, vec3(0.02, 0.025, 0.015), smoothstep(0.86, 0.93, r));
}


// The lid over an eye (`c` its colour, at `e` on its face): the cartoon eye's heavy scowling brow of a
// lid with a dark line along its edge (none on the eye as the species has it), drawn down to blink.
vec3 eye_lid(vec2 e, vec3 c, vec3 lid_c) {
	float line = mix(mix(1.2, LID_Y + LID_SLANT * e.x, cartoon_eyes), -1.2, clamp(blink, 0.0, 1.0));
	float edge = (1.0 - smoothstep(0.0, 0.12, line - e.y)) * smoothstep(-1.1, -0.7, line) * max(cartoon_eyes, step(0.001, blink));
	c = mix(c, vec3(0.02, 0.025, 0.015), edge);
	return mix(c, lid_c, smoothstep(line - 0.01, line + 0.01, e.y));
}


// The normal turned by a bumpy surface `high` (metres) over it, from how `high` changes across the screen.
vec3 bumped(vec3 normal, vec3 where, float high) {
	vec3 dx = dFdx(where);
	vec3 dy = dFdy(where);
	vec3 r1 = cross(dy, normal);
	vec3 r2 = cross(normal, dx);
	float det = dot(dx, r1);
	vec3 slope = sign(det) * (dFdx(high) * r1 + dFdy(high) * r2);
	return normalize(abs(det) * normal - slope);
}

void fragment() {
	vec3 c;
	float rough = 0.34;
	float shine = 0.55;
	if (part < 0.1) {
		// The skin: thick, scaleless, slimy. Yellow-green, softly mottled with a deeper green;
		// furrowed lengthwise, deepest on the throat and the sides of the head; finely pebbled.
		float s = rest.z;
		float mottle = noise3(rest * vec3(21.0, 21.0, 15.0));
		float pebble = noise3(rest * vec3(210.0, 210.0, 140.0));
		float head = 1.0 - smoothstep(0.12, 0.36, s);
		float under = 1.0 - smoothstep(-0.03, 0.03, rest.y);
		// (the furrows: so many round the body, wandering; what is too fine for the picture's
		// pixels is left out, or it would shimmer)
		float lines = atan(rest.x, rest.y) / TAU * 56.0 + 3.5 * noise3(rest * vec3(22.0, 22.0, 7.0));
		float seen = 1.0 - smoothstep(0.25, 0.6, fwidth(lines));
		float fine = 1.0 - smoothstep(0.3, 0.8, length(fwidth(rest)) * 210.0);
		float furrow = mix(0.5, 0.5 + 0.5 * cos(lines * TAU), seen);
		pebble = mix(0.5, pebble, fine);
		float folded = (0.07 + 0.93 * head * (0.22 + 0.78 * under)) * (0.4 + 0.6 * noise3(rest * vec3(9.0, 9.0, 4.0) + 5.0))
				* (1.0 - fin) * smoothstep(0.004, 0.03, s);
		c = mix(skin, skin_deep, 0.32 * smoothstep(0.3, 0.8, mottle) + 0.25 * smoothstep(0.9, 1.7, s));
		c *= 1.0 - 0.2 * folded * (1.0 - furrow) * (1.0 - furrow);
		c *= 0.93 + 0.14 * pebble;
		// The fin: its rays show as fine lines leaning back; deeper green, dusky at its edge.
		float rays = 0.5 + 0.5 * cos((s * 330.0 - fin * 5.0) * TAU);
		c = mix(c, skin_deep, fin * (0.3 + 0.25 * rays) + 0.35 * smoothstep(0.8, 1.0, fin));
		// The gill opening: a small dark hole on each side, a little behind the head. A row
		// of dark pores along each jaw.
		float gill = 1.0 - smoothstep(0.55, 1.0, length(vec2((s - GILL_AT) / 0.009, (rest.y + 0.004) / 0.0055)));
		float pore_row = fract((s - 0.018) / 0.021);
		float pores = (1.0 - smoothstep(0.0009, 0.0016, length(vec2((pore_row - 0.5) * 0.021, abs(rest.y - HINGE_Y * s / MOUTH) - 0.009))))
				* step(0.015, s) * (1.0 - step(MOUTH - 0.01, s));
		c = mix(c, vec3(0.02, 0.03, 0.02), max(gill, 0.8 * pores));
		float high = (furrow * folded * 0.0008 + pebble * 0.0003) * wrinkles * (1.0 - gill);
		NORMAL = bumped(normalize(NORMAL), VERTEX, high);
		rough = mix(0.34, 0.55, fin);
	} else if (part < 0.3) {
		// Inside the mouth: grey-mauve flesh, dark down the throat.
		c = mix(mouth, mouth * 0.25, smoothstep(0.03, MOUTH, rest.z));
		rough = 0.3;
	} else if (part < 0.5) {
		// A tooth: glassy white, yellower at its root.
		c = mix(tooth * vec3(0.8, 0.74, 0.6), tooth, smoothstep(0.0, 0.5, at.y));
		rough = 0.2;
	} else if (part < 0.7) {
		// An eye: a dark pupil, a pale blue-grey iris with a dark rim, the skin round it.
		float r = at.y;
		c = mix(vec3(0.01, 0.012, 0.015), iris * (0.75 + 0.25 * smoothstep(0.26, 0.5, r)), smoothstep(0.24, 0.28, r));
		c = mix(c, iris * 0.3, smoothstep(0.5, 0.56, r));
		c = mix(c, skin_deep, smoothstep(0.58, 0.66, r));
		rough = mix(0.08, 0.34, smoothstep(0.58, 0.66, r));
		if (cartoon_eyes > 0.0 || blink > 0.0) {
			// (where on its face: round it by UV.x, out from the middle by UV.y; forward is the other
			// way round on the left eye)
			float a = at.x * TAU;
			vec2 e = vec2(-cos(a) * sign(rest.x), -sin(a)) * (r / EYE_SEEN);
			c = mix(c, cartoon_eye(e, normalize(NORMAL)), cartoon_eyes * (1.0 - smoothstep(0.58, 0.66, r)));
			c = eye_lid(e, c, mix(skin, skin_deep, 0.5));
			rough = mix(rough, 0.1, cartoon_eyes);
		}
		shine = 0.8;
	} else if (part > 0.9) {
		// The throat and the gills, darker the deeper in: the throat's wall the mouth's colour; an arch
		// pale gill rakers like a comb on its inner edge, a pink bar, and the deep red fringe of filaments.
		float deep = mix(1.0, 0.5, smoothstep(MOUTH, 0.26, rest.z));
		if (fin < 0.25) {
			c = mouth * 0.85;
		} else {
			float u = at.y;
			float comb = smoothstep(0.35, 0.6, abs(fract(at.x * 14.0) - 0.5) * 2.0);
			float fringe = smoothstep(0.2, 0.9, abs(fract(at.x * 40.0) - 0.5) * 2.0);
			c = mix(vec3(0.86, 0.8, 0.7), mouth * 0.6, comb * 0.7);
			c = mix(c, vec3(0.78, 0.42, 0.4), smoothstep(0.26, 0.34, u));
			c = mix(c, mix(vec3(0.62, 0.05, 0.06), vec3(0.3, 0.01, 0.02), fringe), smoothstep(0.44, 0.52, u));
		}
		c *= deep;
		// (with the jaw nearly shut, all of it in the dark of the closed mouth: only a glimpse through
		// the corners of the mouth, which should not show red)
		c = mix(mouth * 0.25, c, smoothstep(0.1, 0.22, jaw));
		rough = 0.3;
	} else {
		c = vec3(0.02, 0.025, 0.02);
		rough = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = shine;
}
