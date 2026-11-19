shader_type spatial;
// The cameroceras (cameroceras.gd): every marking drawn here (no texture files), its rocking as it
// jets, its trailing, curling arms, its head pulled into the shell (`withdraw`) and its cartoon
// eyes. What each point is comes from the model (tools/build_cameroceras.py): UV2.y the part times
// 16 plus which one of them it is (0 the shell, 1 the head (0) or the funnel (1), 2 an eye, 3 the
// hood, 4 an arm, 0 to 9); the colour's red, green and blue a place (in the box BOX_MIN to
// BOX_MAX: an arm's root, the hood's hinge, an eye's middle); the colour's alpha how far along an
// arm, the funnel or the hood (0 at its root, 1 at its end); UV.x, UV.y and UV2.x three more
// numbers: on the shell 0 its outside, 1 the inner wall and the septum, 2 the lip; on an arm, the
// way it points at rest.
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


// Kept in step with the model (build_cameroceras.py): the box the places are written in; the
// opening (its middle) and its radius; the shell's point and the growth bands' spacing.
const vec3 BOX_MIN = vec3(-0.6, -0.6, 1.0);
const vec3 BOX_MAX = vec3(0.6, 0.6, 2.6);
const vec3 APERTURE = vec3(0.0, 0.0, 1.75);
const float APEX_Z = -3.0;
const float BAND = 0.1;
// Withdrawn: how far back into the shell the head goes (metres), and how far the hood turns down
// over the opening (radians).
const float BACK = 0.5;
const float HOOD_SHUT = 1.5;

// How far through one beat (0..1, it wraps): one jet. Set by Cameroceras.
uniform float phase = 0.0;
// How strongly it rocks and jets, and how much its arms trail and curl: 1 swimming, 0 still.
uniform float sway = 1.0;
// Its head and arms: 0 out, 1 pulled right into the shell behind the hood.
uniform float withdraw : hint_range(0.0, 1.0) = 0.0;

// The shell: its pale ground, the brown of its zigzag stripes and how strongly they show; the soft
// body: its reddish skin, the hood's darker hide, the arms' paler skin.
uniform vec3 shell_colour : source_color = vec3(0.82, 0.74, 0.58);
uniform vec3 stripe : source_color = vec3(0.45, 0.25, 0.13);
uniform float stripes_show = 0.5;
uniform vec3 skin : source_color = vec3(0.62, 0.33, 0.24);
uniform vec3 hide : source_color = vec3(0.34, 0.2, 0.15);
uniform vec3 arm : source_color = vec3(0.8, 0.56, 0.45);

// Cartoon eyes: 0 its eyes as they are (dark, a golden ring round a bar of a pupil), 1 the cartoon
// eye (the cameroceras's own: an old giant's calm, heavy-lidded stare, a gold iris round a wide
// bar of a pupil, the upper lid low and level). `eye_look` slides the iris and pupil (x towards its
// face and arms, y up, -1..1); `blink` brings a lid the colour of its skin down over each eye
// (0 open, 1 shut), cartoon or not.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// As the model has it: the middle of the left eye (the right one mirrored).
const vec3 EYE_MIDDLE = vec3(0.262, 0.05, 1.93);
// This one's cartoon eye: the way the left one looks; how much bigger it is; its white, its iris;
// how wide the iris and the pupil are (as the sine of the angle from where it looks); the pupil's
// shape (its width and height); where the upper lid rests (1 above the eye, -1 shut) and how it
// slopes (+ lower at the front); how far the iris slides at `eye_look` 1.
const vec3 EYE_GAZE = vec3(1.0, 0.12, 0.3);
const float EYE_GROW = 1.45;
const vec3 EYE_WHITE = vec3(0.96, 0.94, 0.88);
const vec3 EYE_IRIS = vec3(0.86, 0.6, 0.12);
const float IRIS_SIZE = 0.6;
const float PUPIL_SIZE = 0.3;
const vec2 PUPIL_SHAPE = vec2(1.5, 0.42);
const float LID_REST = 0.32;
const float LID_SLOPE = 0.06;
const float LOOK_REACH = 0.32;

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

// The eye on the side of `p` (at rest): its middle, the way it looks, its up and its across
// (towards its face).
void eye_frame(vec3 p, out vec3 mid, out vec3 gaze, out vec3 up, out vec3 across) {
	float side = p.x >= 0.0 ? 1.0 : -1.0;
	mid = EYE_MIDDLE * vec3(side, 1.0, 1.0);
	gaze = normalize(EYE_GAZE * vec3(side, 1.0, 1.0));
	up = normalize(vec3(0.0, 1.0, 0.0) - gaze * gaze.y);
	across = normalize(cross(gaze, up)) * side;
}

// The colour of a point `p` (at rest) of an eye: `plain` as it is, mixed to the cartoon eye by
// `cartoon_eyes`, the lid (`lid_skin`) over it as `blink` (and, cartooned, `LID_REST`) has it;
// `lid` is set to how far the lid covers it, `glint` to where the cartoon eye's highlights are.
vec3 eye_colour(vec3 p, vec3 plain, vec3 lid_skin, out float lid, out float glint) {
	vec3 mid, gaze, up, across;
	eye_frame(p, mid, gaze, up, across);
	vec3 d = normalize(p - mid);
	vec2 q = vec2(dot(d, across), dot(d, up));
	float front = smoothstep(-0.05, 0.1, dot(d, gaze));
	vec2 at = q - eye_look * LOOK_REACH;
	float r = length(at);
	vec3 c = EYE_WHITE;
	float iris = (1.0 - smoothstep(IRIS_SIZE - 0.03, IRIS_SIZE, r)) * front;
	float streaks = 0.85 + 0.15 * sin(atan(at.y, at.x) * 22.0);
	c = mix(c, EYE_IRIS * mix(1.25, 0.55, smoothstep(0.0, IRIS_SIZE, r)) * streaks, iris);
	c = mix(c, vec3(0.03, 0.02, 0.02), (1.0 - smoothstep(0.015, 0.045, abs(r - IRIS_SIZE))) * front);
	float pupil = 1.0 - smoothstep(PUPIL_SIZE - 0.03, PUPIL_SIZE, length(at / PUPIL_SHAPE));
	c = mix(c, vec3(0.01, 0.01, 0.015), pupil * front);
	c = mix(plain, c, cartoon_eyes);
	// the upper lid: its edge comes down from above the eye (or from where it rests) to below it
	float edge = mix(mix(1.08, LID_REST, cartoon_eyes), -1.08, blink) - LID_SLOPE * q.x;
	lid = smoothstep(edge - 0.02, edge + 0.02, q.y);
	glint = smoothstep(0.955, 0.97, dot(d, normalize(gaze + up * 0.62 + across * 0.3)));
	glint = max(glint, 0.7 * smoothstep(0.991, 0.995, dot(d, normalize(gaze + up * 0.18 + across * 0.52))));
	glint *= 1.0 - lid;
	c = mix(c, lid_skin, lid);
	c = mix(c, lid_skin * 0.35, (1.0 - smoothstep(0.02, 0.07, abs(q.y - edge))) * step(edge, 1.0) * max(cartoon_eyes, step(0.001, blink)));
	return c;
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
	float wave = 6.2831853 * phase;
	// (each beat a jet: the head draws in a little and the arms bunch)
	float pulse = sway * pow(0.5 + 0.5 * sin(wave), 4.0);
	float w = clamp(withdraw + 0.08 * pulse * (1.0 - withdraw), 0.0, 1.0);
	if (p == 4) {
		// An arm: it trails and curls, a wave running out along it, each a little out of step with
		// the next; at the jet they bunch together; withdrawn they draw in to their roots.
		vec3 dir = normalize(kk);
		vec3 out_way = normalize(vec3(joint.xy - vec2(0.0, -0.02), 0.0));
		vec3 spread_axis = normalize(cross(dir, out_way));
		float curl = sway * (0.12 + 0.28 * sin(wave - 2.6 * along + index * 0.63)) - 0.45 * pulse;
		v = joint + turned(v - joint, spread_axis, curl * along);
		n = turned(n, spread_axis, curl * along);
		float side = sway * 0.2 * sin(wave * 1.0 - 1.8 * along + index * 1.3) * along;
		v = joint + turned(v - joint, out_way, side);
		n = turned(n, out_way, side);
		v = joint + (v - joint) * (1.0 - 0.72 * w);
	}
	if (p == 2 && cartoon_eyes > 0.0) {
		// the cartoon eye: bigger about its own middle
		v = joint + (v - joint) * mix(1.0, EYE_GROW, cartoon_eyes);
	}
	if (p == 1 || p == 2 || p == 4) {
		// The head, the eyes, the funnel and the arms: withdrawn, a little smaller and back into the
		// body chamber.
		v = APERTURE + (v - APERTURE) * vec3(1.0 - 0.12 * w, 1.0 - 0.12 * w, 1.0 - 0.3 * w) - vec3(0.0, 0.0, BACK * w);
	} else if (p == 3) {
		// The hood: withdrawn, it stretches and turns down about its hinge over the opening.
		float a = HOOD_SHUT * withdraw;
		vec3 d = v - joint;
		d.z *= 1.0 + 0.45 * withdraw;
		d.x *= 1.0 - 0.15 * withdraw;
		v = joint + turned(d, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	}
	// The whole of it rocks nose up and down a little and bobs as it jets.
	float rock = sway * 0.012 * sin(wave + 0.6);
	v = turned(v, vec3(1.0, 0.0, 0.0), rock);
	n = turned(n, vec3(1.0, 0.0, 0.0), rock);
	v.y += sway * 0.025 * sin(wave - 1.0);
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

