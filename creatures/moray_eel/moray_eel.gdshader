shader_type spatial;
// The moray eel (moray_eel.gd): the still model, which lies straight along +Z from its snout,
// is laid here along the eel's spine, which MorayEel simulates; its lower jaw is swung about
// its hinge, its throat swells as it breathes, its fin ripples. What each point is comes from
// the model (tools/build_moray_eel.py): COLOR.r the part (0 skin, 0.2 inside the mouth, 0.4 a
// tooth, 0.6 an eye, 0.8 the hole of a nostril); COLOR.g how much it swings with the jaw;
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
		shine = 0.8;
	} else {
		c = vec3(0.02, 0.025, 0.02);
		rough = 0.6;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = shine;
}
