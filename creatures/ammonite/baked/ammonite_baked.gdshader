shader_type spatial;
// The ammonite (ammonite.gd): every marking drawn here (no texture files), its rocking and
// bobbing as it jets, its trailing, curling tentacles and its head pulled into the shell
// (`withdraw`). What each point is comes from the model (tools/build_ammonite.py): UV2.y the part
// times 16 plus which one of them it is (0 the shell, 1 the head and funnel, 2 an eye, 3 the hood,
// 4 a tentacle, 0 to 9); the colour's red, green and blue a place (in the box BOX_MIN to BOX_MAX:
// a tentacle's root, the hood's hinge, an eye's middle); the colour's alpha how far along a
// tentacle (0 root, 1 tip) or the hood (0 hinge, 1 front edge); UV.x, UV.y and UV2.x three more
// numbers: on the shell how far round the coil (radians), how far round its section from the
// outer edge (0) to the inner side (1), and 0 outside, 1 the inner wall, 2 the lip; on a
// tentacle, its direction at rest.
//
// Its -Z is the way it jets, shell first. All of the motion is a function of `phase` (and
// `withdraw`) alone, so a picture of it loops exactly. Nothing here needs more than GL
// Compatibility has.
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


// Kept in step with the model (build_ammonite.py prints them as AS THE SHADER HAS IT).
const vec3 BOX_MIN = vec3(-0.3, -0.3, -0.3);
const vec3 BOX_MAX = vec3(0.3, 0.3, 0.3);
// The coil's axis (along X through this point), the aperture's middle, the way out of it, and
// down its section towards the outer edge; where the aperture is round the coil (radians); the
// ribs to a turn.
const vec3 COIL = vec3(0.0, 0.03827, 0.03553);
const vec3 APERTURE = vec3(0.0, -0.12104, 0.01145);
const vec3 OUT_OF = vec3(0.0, -0.28445, 0.95869);
const vec3 DOWN = vec3(0.0, -0.95869, -0.28445);
const float PHI_END = 1.42080;
const float RIBS = 26.0;
// Withdrawn: how far round the coil the head is drawn back into the body chamber (radians), and
// how far the hood turns down over the aperture (radians).
const float BACK = 0.85;
const float HOOD_SHUT = 1.45;

// How far through one beat (0..1, it wraps): one jet, one rock and bob. Set by Ammonite.
uniform float phase = 0.0;
// How strongly it rocks, bobs and jets, and how much its tentacles trail and curl: 1 swimming.
uniform float sway = 1.0;
// Its head and tentacles: 0 out, 1 pulled right into the shell behind the hood.
uniform float withdraw : hint_range(0.0, 1.0) = 0.0;

// The shell: its cream ground, the reddish-brown flames, the sheen of mother-of-pearl, how strongly
// the flames show and how pearly it is.
uniform vec3 cream : source_color = vec3(0.86, 0.79, 0.66);
uniform vec3 flame : source_color = vec3(0.47, 0.17, 0.08);
uniform float flames_show = 0.9;
uniform float pearl = 0.6;
// The soft body: its leathery skin, the hood's darker hide, the tentacles' paler skin.
uniform vec3 skin : source_color = vec3(0.6, 0.36, 0.25);
uniform vec3 hide : source_color = vec3(0.36, 0.22, 0.15);
uniform vec3 tentacle : source_color = vec3(0.84, 0.64, 0.52);
// The cartoon eye: 0 the eye as in life, 1 a bigger cartoon eye (a white, an iris, a pupil, a
// highlight, a dark outline and lids of its own character); where its pupils look (x towards
// its front, where its tentacles reach, y up, -1..1, in each eye's own plane); a blink (0 open,
// 1 shut: lids the colour of its skin close over the eye, the cartoon one and the one in life).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

// The ammonite's cartoon eye: old, slow and kindly. A cream white, a deep amber iris round a
// wide bar of a pupil (its cephalopod cousins'), a heavy upper lid drooping a little towards its
// front, half over the eye, and a soft lower lid: an old thing, half asleep. (Kept in step with
// the model, build_ammonite.py prints it: the eye's radius across its face.)
const float EYE_R = 0.02383;
const float EYE_BIG = 1.4;
const vec3 SCLERA = vec3(0.95, 0.93, 0.86);
const vec3 IRIS_IN = vec3(0.96, 0.72, 0.26);
const vec3 IRIS_OUT = vec3(0.55, 0.28, 0.06);
const float IRIS_R = 0.5;
// The pupil's half width and half height, in eye radii (a bar with rounded ends).
const vec2 PUPIL = vec2(0.33, 0.12);
// The upper lid's edge (eye radii up from the middle) and its slant (up per radius forward); the
// lower lid's.
const float LID_TOP = 0.24;
const float LID_SLANT = -0.12;
const float LID_LOW = -0.78;
const float LID_LOW_SLANT = 0.06;

varying vec3 rest;
varying float part;
varying float index;
varying float along;
varying vec3 kk;
varying vec3 joint;

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

// `v` turned by `a` about the axis `k` (a unit vector).
vec3 turned(vec3 v, vec3 k, float a) {
	float c = cos(a);
	float s = sin(a);
	return v * c + cross(k, v) * s + k * dot(k, v) * (1.0 - c);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	float code = floor(UV2.y + 0.5);
	part = floor((code + 0.5) / 16.0);
	index = code - part * 16.0;
	along = COLOR.a;
	kk = vec3(UV.x, UV.y, UV2.x);
	joint = mix(BOX_MIN, BOX_MAX, COLOR.rgb);
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	// The cartoon eye is bigger: the eye grows about its own middle.
	if (p == 2 && cartoon_eyes > 0.0) {
		v = joint + (v - joint) * mix(1.0, EYE_BIG, cartoon_eyes);
	}
	float wave = 6.2831853 * phase;
	// (each beat a jet: the head draws in a little and the tentacles bunch)
	float pulse = sway * pow(0.5 + 0.5 * sin(wave), 4.0);
	float w = clamp(withdraw + 0.1 * pulse * (1.0 - withdraw), 0.0, 1.0);
	if (p == 4) {
		// A tentacle: it trails and curls down, a wave running out along it, each a little out of
		// step with the next; at the jet they bunch; withdrawn they draw in to their roots.
		vec3 dir = normalize(kk);
		vec3 bend = normalize(cross(dir, DOWN));
		float curl = 0.15 + sway * (0.3 + 0.3 * sin(wave - 2.5 * along + index * 0.63)) - 0.25 * pulse;
		v = joint + turned(v - joint, bend, curl * along);
		n = turned(n, bend, curl * along);
		float side = sway * 0.18 * sin(wave + index * 1.3) * along;
		v = joint + turned(v - joint, DOWN, side);
		n = turned(n, DOWN, side);
		v = joint + (v - joint) * (1.0 - 0.72 * w);
	}
	if (p == 1 || p == 2 || p == 4) {
		// The head, the eyes, the tentacles and the funnel: withdrawn, a little smaller, back
		// along the tube and round the coil into the body chamber.
		v = APERTURE + (v - APERTURE) * (1.0 - 0.22 * w) - OUT_OF * (0.025 * w);
		float b = BACK * w;
		v = COIL + turned(v - COIL, vec3(1.0, 0.0, 0.0), b);
		n = turned(n, vec3(1.0, 0.0, 0.0), b);
	} else if (p == 3) {
		// The hood: withdrawn, it stretches and turns down about its hinge over the aperture.
		float a = HOOD_SHUT * withdraw;
		vec3 d = v - joint;
		d += OUT_OF * (dot(d, OUT_OF) * 0.55 * withdraw);
		v = joint + turned(d, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	}
	// The whole of it rocks nose up and down and bobs as it jets.
	float rock = sway * 0.06 * sin(wave + 0.6);
	v = turned(v, vec3(1.0, 0.0, 0.0), rock);
	n = turned(n, vec3(1.0, 0.0, 0.0), rock);
	v.y += sway * 0.006 * sin(wave - 1.0);
	VERTEX = v;
	NORMAL = n;
}

// The cartoon eye at `e`: a point of the eye in its own plane, in eye radii (x towards its front,
// y up). A white shaded towards its rim, an iris (darker at its edge) and a pupil that slide
// together as far as `eye_look` asks and the white allows, and highlights that stay put, up and
// forward, towards the light.
vec3 cartoon_eye(vec2 e) {
	vec2 d = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.86 - IRIS_R);
	float ir = length(d) / IRIS_R;
	vec3 c = SCLERA * (1.0 - 0.22 * smoothstep(0.45, 0.95, length(e)));
	vec3 iris = mix(IRIS_IN, IRIS_OUT, smoothstep(0.2, 1.0, ir));
	iris = mix(iris, iris * 0.3, smoothstep(0.8, 0.95, ir));
	c = mix(c, iris, 1.0 - smoothstep(0.96, 1.0, ir));
	vec2 q = d / PUPIL;
	q *= q;
	float bar = sqrt(sqrt(q.x * q.x + q.y * q.y));
	c = mix(c, vec3(0.02, 0.012, 0.01), 1.0 - smoothstep(0.85, 1.0, bar));
	float shine = 1.0 - smoothstep(0.09, 0.125, length(e - vec2(0.27, 0.06)));
	shine = max(shine, 1.0 - smoothstep(0.035, 0.06, length(e - vec2(-0.12, -0.3))));
	return mix(c, vec3(1.0), shine);
}

// The lids over an eye at `e` (as above), `lid` the colour of its skin: in the cartoon eye where
// its character puts them, with a dark line along each edge and a dark outline round the eye; in
// the eye in life, out of sight. `blink` brings them together.
vec3 eye_lids(vec3 c, vec2 e, vec3 lid) {
	float top = mix(1.3, LID_TOP + LID_SLANT * e.x, cartoon_eyes);
	float low = mix(-1.3, LID_LOW + LID_LOW_SLANT * e.x, cartoon_eyes);
	float meet = mix(top, low, 0.65);
	top = mix(top, meet, blink);
	low = mix(low, meet, blink);
	float over = max(smoothstep(-0.02, 0.02, e.y - top), smoothstep(-0.02, 0.02, low - e.y));
	c = mix(c, lid, over);
	float line = max(1.0 - smoothstep(0.035, 0.07, abs(e.y - top)), 1.0 - smoothstep(0.025, 0.05, abs(e.y - low)));
	c = mix(c, vec3(0.03, 0.02, 0.015), line * mix(0.5, 1.0, cartoon_eyes) * step(0.001, max(cartoon_eyes, blink)));
	return mix(c, vec3(0.03, 0.02, 0.015), smoothstep(0.84, 0.92, length(e)) * cartoon_eyes);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

