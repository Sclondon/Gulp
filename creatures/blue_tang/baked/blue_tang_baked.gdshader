shader_type spatial;
// The regal blue tang (blue_tang.gd): it swims by a small wave down its body and rows with its pectoral
// fins, its mouth opens, its fins wave; and every marking is drawn here: no texture files. What each point
// is comes from the model (tools/build_blue_tang.py): COLOR.r the part, as a tenth (0 body, 1 lower jaw, 2
// eye, 3 spine, 4 dorsal, 6 tail, 7 anal, 8 pelvic, 9 pectoral). On the body and the jaw UV.x is how far
// along the fish (0 snout to 1 tail tip), UV.y how high on the head and body (0 the chin or the belly line,
// 1 the back line), COLOR.b the inside of the mouth. On an eye UV is where a point is on its round face. On
// a fin UV.x is along its rays (0 root, 1 edge), UV.y across it counted in rays, COLOR.g how far across it
// (0 leading edge, 1 trailing edge); UV2.xy and COLOR.b the way its flat side faces. Nothing here needs more
// than GL Compatibility has. One opaque draw, back faces culled. (The school model does not wear this
// shader: its colours are in its points.)
//
// Everything that moves runs on `phase` (0..1 through one beat): in a beat the tail beats `tail_beats`
// times and the pectoral fins row `strokes` times (whole numbers), so a film of it loops exactly.
render_mode cull_back, depth_draw_opaque, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// As the model is built (tools/build_blue_tang.py prints these): its length, where its lower jaw hinges
// (how far along, how high, in body lengths) and where its gill cover's rear edge is.
const float LENGTH = 0.25;
const float HINGE_S = 0.037;
const float HINGE_Y = -0.007;
const float GILL_S = 0.225;
// How many body lengths one wave of the swimming bend is.
const float WAVE = 1.05;
// How far a pectoral fin's edge rows out and in (body lengths; the build script checks the gap it leaves
// to the body with the same numbers: out to 1.5 of it, in to 0.5).
const float ROW_REACH = 0.035;

// How far through a beat it is (0..1), and how many times in a beat its tail beats and its pectoral fins
// row (whole numbers).
uniform float phase = 0.0;
uniform float tail_beats = 2.0;
uniform float strokes = 3.0;
// How widely its body and tail sway (1: the tail's tip a tenth of its length each way), and how hard its
// pectoral fins row (1 as it cruises).
uniform float sway = 0.35;
uniform float row = 1.0;
// Turning: how far the body is bent round to one side behind the gills, in radians from gills to tail
// (0 straight; more than 0 the tail comes round to +X). The head stays as it is.
uniform float curl = 0.0;
// The mouth: 0 shut, 1 wide open. `gape_angle` is how far (radians) the lower jaw swings down at 1, and
// `lip_lift` how far the snout's tip lifts with it.
uniform float gape = 0.0;
uniform float gape_angle = 0.8;
uniform float lip_lift = 0.15;

// The colours: the royal blue of the body, paler towards the belly; the black of the "palette"; the yellow
// of the tail and the pectoral fins' tips; the fins' blue and their black edges; the spine; the ring round
// the pupil; the inside of the mouth. (The school model's are written into its points by the build
// script: change both.)
uniform vec3 blue : source_color = vec3(0.1, 0.32, 0.86);
uniform vec3 belly : source_color = vec3(0.22, 0.46, 0.9);
uniform vec3 black : source_color = vec3(0.03, 0.03, 0.06);
uniform vec3 yellow : source_color = vec3(1.0, 0.84, 0.1);
uniform vec3 fin_blue : source_color = vec3(0.12, 0.34, 0.84);
uniform vec3 fin_edge : source_color = vec3(0.04, 0.05, 0.12);
uniform vec3 spine_colour : source_color = vec3(0.95, 0.92, 0.7);
uniform vec3 eye_ring : source_color = vec3(0.16, 0.16, 0.12);
uniform vec3 mouth : source_color = vec3(0.16, 0.05, 0.06);
// How much it shines where it is seen aslant.
uniform float sheen = 0.3;
// The cartoon eye (the user, 2026-11-18: "the eyes for most of them should be more cartoony and
// personalized"). `cartoon_eyes` 0 is the eye as it always was (the default), 1 the cartoon eye: grown
// `eye_grow` times about the middle of its rim (`eye_centre`, the +X eye's, metres, as the build script
// prints it), a pale white, a coloured iris with a dark rim, a dark pupil (`pupil_size` across and up on
// the eye's face: equal for a round one), two fixed highlights, a dark outline, and an upper lid of the
// colour `lid` that comes down `lid_low` of the way over it (0 not at all, 0.5 to its middle), sloping
// by `lid_slant` (more than 0 higher towards the snout). `eye_look` slides the iris and pupil (x towards
// the snout, y up, -1..1). `blink` (0 open, 1 shut) squashes the eye flat and draws the lid down over
// it, on either eye. Its character (Claude's pick):
// a friendly, eager eye, a little anxious, its lid raised towards its snout and drooping behind.
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
uniform vec3 eye_centre = vec3(0.00474, 0.01653, -0.09238);
uniform float eye_grow = 1.7;
uniform vec3 eye_white : source_color = vec3(0.97, 0.97, 0.95);
uniform vec3 iris : source_color = vec3(0.3, 0.18, 0.1);
uniform float iris_size = 0.6;
uniform vec2 pupil_size = vec2(0.38, 0.38);
uniform vec3 lid : source_color = vec3(0.1, 0.32, 0.86);
uniform float lid_low = 0.1;
uniform float lid_slant = 0.3;

// THE THROAT AND THE GILLS (part 5: four gill arches a side, inside the head behind the jaw's hinge and above the
// line of the mouth). As the mouth opens, the roof of the mouth (the body's skin that is the inside of the mouth,
// COLOR.b; on the game and low models also what the build marked in COLOR.g) is lifted THROAT_LIFT (body lengths
// at gape 1) into a vault, and its back (from THROAT_BACK ahead of the hinge to the hinge) drawn back THROAT_DEPTH,
// so that the old dark wall at the back of the mouth becomes a short tunnel with the arches standing in it,
// darker deeper in. Shut, nothing of them shows. Kept in step with the build script's THROAT_* numbers.
const float THROAT_LIFT = 0.03;
const float THROAT_DEPTH = 0.085;
const float THROAT_BACK = 0.02;
// The gill arches: their filaments and their pale rakers.
uniform vec3 gill_red : source_color = vec3(0.6, 0.05, 0.07);
uniform vec3 gill_raker : source_color = vec3(0.9, 0.8, 0.74);

varying float part;
varying float inside;
// how far the throat's skin has been pushed back here (0..1), and where a point was along the fish at rest
varying float throat_deep;
varying float throat_s;


// The body behind the gills laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = (GILL_S - 0.5) * LENGTH;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (0.7 * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}


// Turns a point and its normal about the jaw's hinge (a > 0 swings what is ahead of it down).
void about_hinge(inout vec3 v, inout vec3 n, float a) {
	vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5) * LENGTH;
	vec2 d = v.yz - hinge;
	float c = cos(a);
	float sn = sin(a);
	v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
}


// An eye's point: grown about the middle of its rim for the cartoon eye, and squashed flat as it blinks.
void eye_shape(inout vec3 v, inout vec3 n, float side_is) {
	float grow = mix(1.0, eye_grow, clamp(cartoon_eyes, 0.0, 1.0));
	float shut = 1.0 - 0.8 * clamp(blink, 0.0, 1.0);
	if (grow == 1.0 && shut == 1.0) {
		return;
	}
	vec3 middle = vec3(eye_centre.x * side_is, eye_centre.yz);
	vec3 d = (v - middle) * grow;
	d.y *= shut;
	v = middle + d;
	n.y /= shut;
}


// The cartoon eye's colour on its round face (`uv`), over `old` (the eye as it was), and the lid.
vec3 cartoon_eye(vec3 old, vec2 uv, inout float rough) {
	// (x towards the snout, y up; 1 at the rim where it meets the head)
	vec2 q = vec2(uv.y - 0.5, uv.x - 0.5) * 2.0 / 0.86;
	float r = length(q);
	float toon = clamp(cartoon_eyes, 0.0, 1.0);
	vec2 at = q - clamp(eye_look, vec2(-1.0), vec2(1.0)) * vec2(0.24, 0.2);
	float ir = length(at);
	vec3 c = eye_white;
	vec3 ring = mix(iris * 1.3, iris * 0.75, smoothstep(0.0, iris_size, ir));
	c = mix(c, ring, 1.0 - smoothstep(iris_size - 0.03, iris_size + 0.01, ir));
	c = mix(c, iris * 0.3, smoothstep(iris_size - 0.1, iris_size - 0.02, ir) * (1.0 - smoothstep(iris_size - 0.02, iris_size + 0.01, ir)));
	c = mix(c, vec3(0.015), 1.0 - smoothstep(0.92, 1.05, length(at / pupil_size)));
	float shine = 1.0 - smoothstep(0.1, 0.14, length(q - vec2(0.24, 0.3)));
	shine = max(shine, 1.0 - smoothstep(0.04, 0.07, length(q - vec2(-0.2, -0.24))));
	c = mix(c, vec3(1.0), shine);
	c = mix(c, vec3(0.02), smoothstep(0.84, 0.92, r));
	c = mix(old, c, toon);
	float open_line = mix(1.3, 1.0 - 2.0 * lid_low + lid_slant * q.x, toon);
	float line = mix(open_line, -1.25, clamp(blink, 0.0, 1.0));
	vec3 lid_colour = mix(lid, vec3(0.02), (1.0 - smoothstep(0.04, 0.12, q.y - line)) * toon);
	float over = smoothstep(line - 0.02, line + 0.02, q.y);
	// (the outline and the lid matte, so that they stay dark where the eye is seen aslant)
	rough = mix(rough, 0.65, max(toon * smoothstep(0.8, 0.88, r), over));
	return mix(c, lid_colour, over);
}


void vertex() {
	bake_uv = CUSTOM0.xy;

	part = floor(COLOR.r * 10.0 + 0.5);
	inside = COLOR.b;
	vec3 v = VERTEX;
	throat_deep = 0.0;
	throat_s = VERTEX.z / LENGTH + 0.5;
	vec3 n = NORMAL;
	float s = v.z / LENGTH + 0.5;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float tail = phase * TAU * tail_beats;
	float wave = tail - TAU * clamp(s, 0.0, 1.05) / WAVE;
	float open = clamp(gape, 0.0, 1.0);
	if (part == 1.0) {
		// The lower jaw swings down about its hinge at the corner of the mouth; the throat behind stays.
		about_hinge(v, n, open * gape_angle * smoothstep(HINGE_S + 0.022, HINGE_S - 0.008, s));
	} else if (part == 0.0) {
		// The snout's tip lifts a little as the mouth opens.
		about_hinge(v, n, -open * lip_lift * smoothstep(HINGE_S + 0.012, HINGE_S - 0.02, s));
		// The roof of the mouth is lifted into a vault and drawn back into a throat as it opens (the
		// tip of the snout stays where it is).
		if (open > 0.0) {
			float w = max(COLOR.b, COLOR.g) * smoothstep(HINGE_S * 0.35, HINGE_S, s);
			throat_deep = w * open;
			v.y += LENGTH * THROAT_LIFT * throat_deep;
			v.z += LENGTH * THROAT_DEPTH * throat_deep * smoothstep(HINGE_S - THROAT_BACK, HINGE_S, s);
		}
	} else if (part == 2.0) {
		eye_shape(v, n, side_is);
	} else if (part == 5.0) {
		// The gill arches spread a little as the mouth opens.
		v.x *= 1.0 + 0.12 * open;
	} else if (part >= 4.0) {
		vec3 flat_way = normalize(vec3(UV2.x, UV2.y, COLOR.b * 2.0 - 1.0));
		float r = UV.x;
		float across = COLOR.g;
		if (part == 9.0) {
			// The pectorals row: each stroke swings the fin out and back, then feathers it in and
			// forward, the leading edge leading; one side a little after the other.
			float a = phase * TAU * strokes + (side_is > 0.0 ? 0.0 : 0.3) - across * 0.9;
			v += flat_way * (LENGTH * ROW_REACH * row * r * (sin(a) + 0.5));
			v.z += LENGTH * 0.03 * row * r * cos(a);
		} else if (part == 8.0) {
			float a = phase * TAU * strokes + (side_is > 0.0 ? 1.8 : 2.2);
			v += flat_way * (LENGTH * 0.01 * row * r * r * sin(a));
		} else if (part == 6.0) {
			// (the tail's edge lags behind the bend that carries it)
			v.x += LENGTH * 0.05 * sway * r * r * sin(wave - 1.1 - across * 0.4);
		} else {
			// The dorsal and anal fins ripple, a wave running back along them.
			v.x += LENGTH * 0.03 * sway * r * r * sin(wave - 1.0 - across * 2.5);
		}
	}
	// The swimming bend: a wave from head to tail, the head nearly still and the tail swinging widest.
	// Each place is carried sideways and turned to lie along the bent body, so the fins follow it.
	float sb = clamp(v.z / LENGTH + 0.5, 0.0, 1.05);
	float reach = 0.008 - 0.04 * sb + 0.13 * sb * sb;
	float reach_slope = -0.04 + 0.26 * sb;
	float w = tail - TAU * sb / WAVE;
	float off = LENGTH * sway * reach * sin(w);
	float slope = sway * (reach_slope * sin(w) - reach * TAU / WAVE * cos(w));
	vec3 along = normalize(vec3(slope, 0.0, 1.0));
	vec3 across_body = vec3(along.z, 0.0, -along.x);
	v = vec3(off, v.y, v.z) + across_body * v.x;
	n = across_body * n.x + vec3(0.0, n.y, 0.0) + along * n.z;
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = normalize(n);
}


float band(float x, float centre, float half_width, float soft) {
	return 1.0 - smoothstep(half_width - soft, half_width + soft, abs(x - centre));
}


float gill_edge(float h) {
	return GILL_S - 0.22 * (h - 0.5) * (h - 0.5);
}


// The body's colour at a place: `s` along, `h` up. The black "palette": a band from the eye along the
// back to the tail's wrist, and a loop from it down round the flank and back to the wrist, holding an oval
// of blue; yellow from the spine back over the tail's root. (tools/build_blue_tang.py's `palette` is the
// same, for the school model: change both.)
vec3 skin(float s, float h) {
	vec3 c = mix(belly, blue, smoothstep(0.05, 0.35, h));
	float centre = 0.665 + 0.055 * smoothstep(0.12, 0.3, s) - 0.17 * smoothstep(0.55, 0.8, s);
	float wide = 0.05 + 0.07 * smoothstep(0.12, 0.3, s) - 0.07 * smoothstep(0.5, 0.8, s);
	float dark = smoothstep(0.092, 0.112, s) * (1.0 - smoothstep(wide - 0.015, wide + 0.015, abs(h - centre)));
	float outer = pow((s - 0.585) / 0.235, 2.0) + pow((h - 0.5) / 0.3, 2.0);
	float inner = pow((s - 0.6) / 0.135, 2.0) + pow((h - 0.52) / 0.15, 2.0);
	dark = max(dark, (1.0 - smoothstep(0.85, 1.0, outer)) * smoothstep(0.85, 1.0, inner));
	c = mix(c, black, dark);
	float gold = smoothstep(0.74, 0.76, s) * (1.0 - smoothstep(-0.015, 0.015, abs(h - 0.5) - 0.06 - (s - 0.75) * 3.0));
	c = mix(c, yellow, gold);
	// The gill cover's edge: a fine darker crescent.
	float edge = gill_edge(h);
	c *= 1.0 - 0.25 * band(s, edge, 0.0016, 0.0012) * smoothstep(0.12, 0.25, h) * (1.0 - smoothstep(0.78, 0.9, h));
	return c;
}


void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

