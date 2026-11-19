shader_type spatial;
// The viperfish (viperfish.gd): every marking drawn here (no texture files), its swimming, its mouth, its long
// dorsal ray and its lights. What each point is comes from the model (tools/build_viperfish.py): UV2.y the part
// (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 the long dorsal ray, 6 an eye, 7 the
// lower jaw, 8 a tooth of the upper jaw, 9 a tooth of the lower jaw, 10 the light at the ray's tip, 11 a
// photophore, 12 a pelvic fin, 13 the adipose fin, 14 a gill arch). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the
// jaw: x how far along, y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root
// (0) to tip (1), y leading edge (0) to trailing edge (1); on an eye or a photophore: x middle (0) to rim (1); on
// the ray and a tooth: x root (0) to tip (1); on the ray's light: x its base (0) to its top (1).
//
// It swims with a slow wave down the long body (more of it bends than in a tuna or a sardine). When it opens its
// mouth the lower jaw swings down and the head lifts back, as a viperfish's does. The photophores and the light on
// the ray glow (EMISSION). All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
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


// Kept in step with the model.
const float LENGTH = 0.30;
const float HALF = 0.15;
const float JOINT = 0.268;
// The lower jaw: how far back it runs, where its hinge is (on the line of the mouth, whose slope is SLOPE), how
// far it swings down and how far the head lifts back, wide open (radians).
const float JAW_TO = 0.04;
const float HINGE_Y = -0.0029;
const float SLOPE = 0.11;
const float GAPE_OPEN = 1.05;
const float HEAD_LIFT = 0.32;
// The root of the long dorsal ray (y, z in the model).
const vec2 RAY_ROOT = vec2(0.01581, -0.09);
const vec2 EYE_AT = vec2(0.0145, 0.0042);

// How far through a beat of its tail (0..1, it wraps). Set by Viperfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the tail
// (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats: 1 as one cruising (its tail tips swing about 0.025 m either way), 0 still.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.75;
// How far its mouth is open: 0 shut, 1 wide open (the jaw swings down, the head lifts back).
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// How strongly its lights glow (0 none, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;
// How far the long dorsal ray is leant forward (radians; less than 0 further back).
uniform float ray_lean = 0.0;

// The dark skin, the iridescence on it (blue-green, turning violet where light glances off), the black lines of
// its net of hexagonal marks.
uniform vec3 skin : source_color = vec3(0.025, 0.032, 0.045);
uniform vec3 sheen : source_color = vec3(0.12, 0.34, 0.38);
uniform vec3 sheen_glance : source_color = vec3(0.3, 0.16, 0.42);
uniform vec3 net : source_color = vec3(0.004, 0.005, 0.008);
// How strongly the net shows.
uniform float net_show = 0.8;
// The fins: dark, clearer at their edges.
uniform vec3 fin : source_color = vec3(0.05, 0.06, 0.07);
uniform vec3 mouth_inside : source_color = vec3(0.07, 0.02, 0.03);
uniform vec3 tooth : source_color = vec3(0.86, 0.88, 0.9);
// The photophores' and the ray light's colour.
uniform vec3 light_colour : source_color = vec3(0.3, 0.6, 1.0);

// The cartoon eye (0 the eye as made, 1 the cartoon one; Gulp uses 1). This one is a cold reptile stare: the eye grown to 1.35 times, a pale grey-green white, a wide ice-green iris round a tall slit of a pupil, and a flat heavy lid low over its top, unblinking. `eye_look` slides
// the iris and pupil (x + towards the snout, y + up; -1..1), `blink` closes the lid over it (0 open, 1 shut).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_white : source_color = vec3(0.72, 0.78, 0.74);
uniform vec3 eye_iris : source_color = vec3(0.35, 0.85, 0.62);
// The eye's dome: the middle of its base on the left side (x, y, z in the model; the right eye is at -x), its
// radius; how much bigger the cartoon eye is; the iris's and the pupil's radius (1 the eye's rim); the pupil
// squeezed across into a slit (1 round); how far the lid hangs down at rest (0 none, 1 to the middle) and how much
// lower it is towards the snout.
const vec3 EYE_BASE = vec3(0.00801, 0.0042, -0.1355);
const float EYE_RADIUS = 0.0052;
const float EYE_GROW = 1.35;
const float IRIS_R = 0.6;
const float PUPIL_R = 0.5;
const float PUPIL_SLIT = 2.8;
const float LID_REST = 0.22;
const float LID_SLANT = 0.12;


// THE GILLS (part 14): four arches a side standing in the throat, a short tunnel from the back of the mouth
// back to GILL_TO (metres behind the snout's tip, as the model has them). Seen only through the open mouth; as it
// opens they spread a little. Blood red with pale rakers, darker deeper in the throat. WALL_UP: where the full
// model's old wall across the back of its mouth is lifted to as it opens.
const float GILL_FROM = 0.0436;
const float GILL_TO = 0.052;
const float WALL_UP = 0.01194;
uniform vec3 gill_red : source_color = vec3(0.55, 0.04, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.74, 0.70);


varying vec3 rest;
varying float part;
varying float inside;
varying vec2 eye_q;

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.006 - 0.022 * s + 0.075 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.09;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.75 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

// Turns `v` and `n` about the X axis through `at` (y, z) by `a` (more than 0: what is above `at` goes forward,
// what is ahead of it goes down).
void pitch(inout vec3 v, inout vec3 n, vec2 at, float a) {
	float c = cos(a);
	float s = sin(a);
	vec2 d = vec2(v.y - at.x, v.z - at.y);
	v.y = at.x + d.x * c + d.y * s;
	v.z = at.y + d.y * c - d.x * s;
	n = vec3(n.x, n.y * c + n.z * s, n.z * c - n.y * s);
}

// The cartoon eye at `q` (its own plane: x towards the snout, y up, 1 at the rim), its lid the colour `lid`;
// `lidded` says where the lid covers it.
vec3 cartoon_eye(vec2 q, vec3 lid, out float lidded) {
	float r = length(q);
	float aa = max(fwidth(r), 0.01) * 1.2;
	vec2 iq = q - clamp(eye_look, vec2(-1.0), vec2(1.0)) * max(0.78 - IRIS_R, 0.08) * vec2(1.0, 0.8);
	float ir = length(iq);
	vec3 c = eye_white * (1.0 - 0.25 * smoothstep(0.3, 0.8, r));
	// the iris: darker at its edge, lighter low in it; then the pupil, then the highlight towards the light
	vec3 iris = eye_iris * (0.55 + 0.6 * smoothstep(IRIS_R, 0.0, length(iq - vec2(0.0, -0.3 * IRIS_R))));
	iris = mix(iris, eye_iris * 0.25, smoothstep(IRIS_R * 0.75, IRIS_R, ir));
	c = mix(c, iris, 1.0 - smoothstep(IRIS_R - aa, IRIS_R + aa, ir));
	float pr = length(iq * vec2(PUPIL_SLIT, 1.0));
	c = mix(c, vec3(0.008), 1.0 - smoothstep(PUPIL_R - aa, PUPIL_R + aa, pr));
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.13 - aa, 0.13 + aa, length(q - vec2(-0.3, 0.12))));
	c = mix(c, vec3(0.9), 1.0 - smoothstep(0.055 - aa, 0.055 + aa, length(q - vec2(0.22, -0.3))));
	// the dark outline, a round one inside the eye's many-sided rim, and the skin round it out to the rim
	c = mix(c, vec3(0.01), smoothstep(0.8 - aa, 0.8 + aa, r));
	float skirt = smoothstep(0.93 - aa, 0.93 + aa, r);
	// the lid: hanging down at rest, lower towards the snout, closing with `blink`
	float edge = mix(1.05 - 2.0 * LID_REST, -1.1, clamp(blink, 0.0, 1.0)) - LID_SLANT * q.x * (1.0 - blink);
	c = mix(c, vec3(0.01), smoothstep(edge - 0.1 - aa, edge - 0.1 + aa, q.y));
	lidded = max(smoothstep(edge - aa, edge + aa, q.y), skirt);
	c = mix(c, lid, lidded);
	return c;
}



void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	rest = VERTEX;
	inside = UV2.x;
	vec3 v = VERTEX;
	vec3 nn = NORMAL;
	int p = int(part + 0.5);
	eye_q = vec2(0.0);
	if (p == 6) {
		// The eye: where each point is in its own plane (x towards the snout, y up, 1 at the rim); grown about its
		// middle for the cartoon eye, and squashed a little as it blinks.
		vec3 base = vec3(sign(v.x) * EYE_BASE.x, EYE_BASE.y, EYE_BASE.z);
		eye_q = vec2(base.z - v.z, v.y - base.y) / EYE_RADIUS;
		vec3 d = (v - base) * mix(1.0, EYE_GROW, cartoon_eyes);
		d.y *= 1.0 - 0.45 * blink * cartoon_eyes;
		v = base + d;
	}
	if (gape > 0.0 && p == 0 && UV2.x > 0.999 && UV.y > 0.45 && UV.y < 0.55 && abs(v.z + HALF - JAW_TO) < 0.0001) {
		// The full model's old wall across the back of the mouth (the foot of it): as the mouth opens it is lifted
		// up out of the way, above the roof of the mouth, so that the throat and the gills behind it show. (The
		// throat's own points are told apart by their UV's y, 0.)
		v = vec3(v.x * 0.55, WALL_UP, v.z + 0.1 * (GILL_TO - JAW_TO));
	}
	if (p == 14) {
		// The gill arches spread a little as the mouth opens.
		float open = clamp(gape, 0.0, 1.0);
		v.x *= 1.0 + 0.1 * open;
		v.z += (v.z + HALF - 0.5 * (GILL_FROM + GILL_TO)) * 0.15 * open;
	}
	float xm = v.z + HALF;
	float g = clamp(gape, 0.0, 1.0);
	vec2 hinge = vec2(HINGE_Y, JAW_TO - HALF);
	if (p == 7 || p == 9) {
		// The lower jaw (and its teeth) swings down about its hinge; its end inside the head stays where it is.
		pitch(v, nn, hinge, g * GAPE_OPEN * (1.0 - smoothstep(JAW_TO - 0.016, JAW_TO - 0.0005, xm)));
	} else if (p == 5 || p == 10) {
		// The long ray sways, bent more towards its tip.
		float t = p == 5 ? UV.x : 1.0;
		pitch(v, nn, RAY_ROOT, (ray_lean + 0.1 * sway * sin(6.2831853 * phase + 1.0)) * t);
		v.x += 0.006 * sway * pow(t, 1.5) * sin(6.2831853 * phase + 2.2);
	} else if (p == 4) {
		v.x += sign(rest.x) * UV.x * 0.0025 * sway * sin(6.2831853 * phase);
	}
	// The head (and everything on it, the jaw too) lifts back about the hinge as the mouth opens, the neck bending.
	pitch(v, nn, hinge, -g * HEAD_LIFT * (1.0 - smoothstep(JAW_TO - 0.012, JAW_TO + 0.03, xm)));
	xm = v.z + HALF;
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0008) - side_at(zc - 0.0008)) / 0.0016;
	float turn = atan(slope) * (1.0 + 0.2 * smoothstep(0.9 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	nn = vec3(nn.x * c + nn.z * sn, nn.y, -nn.x * sn + nn.z * c);
	curl_bend(v, nn);
	VERTEX = v;
	NORMAL = nn;
}

// How near a point is to the edge of its cell in a grid of hexagons (0 at the edge, 0.5 in the middle), and which
// cell it is in.
vec3 hexes(vec2 p) {
	vec2 r = vec2(1.0, 1.7320508);
	vec2 h = r * 0.5;
	vec2 a = mod(p, r) - h;
	vec2 b = mod(p - h, r) - h;
	vec2 g = dot(a, a) < dot(b, b) ? a : b;
	vec2 id = p - g;
	vec2 q = abs(g);
	float edge = 0.5 - max(dot(q, normalize(vec2(1.0, 1.7320508))), q.x);
	return vec3(edge, id);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	EMISSION = texture(baked_glow, bake_uv).rgb * baked_glow_scale;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

