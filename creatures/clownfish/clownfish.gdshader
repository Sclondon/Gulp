shader_type spatial;
// The ocellaris clownfish (clownfish.gd): its whole body waggles busily and bends in a short wave, its
// pectoral fins paddle, its mouth opens; and every marking is drawn here: no texture files. What each point
// is comes from the model (tools/build_clownfish.py): COLOR.r the part, as a tenth (0 body, 1 lower jaw, 2
// eye, 4 dorsal, 6 tail, 7 anal, 8 pelvic, 9 pectoral). On the body and the jaw UV.x is how far along the
// fish (0 snout to 1 tail tip), UV.y how high on the head and body (0 the chin or the belly line, 1 the back
// line), COLOR.b the inside of the mouth. On an eye UV is where a point is on its round face. On a fin UV.x
// is along its rays (0 root, 1 edge), UV.y across it counted in rays, COLOR.g how far across it (0 leading
// edge, 1 trailing edge); UV2.xy and COLOR.b the way its flat side faces. Nothing here needs more than GL
// Compatibility has. One opaque draw, back faces culled.
//
// Everything that moves runs on `phase` (0..1 through one beat): in a beat the tail beats (and the body
// waggles) `tail_beats` times and the pectoral fins paddle `strokes` times (whole numbers), so a film of it
// loops exactly.
render_mode cull_back, depth_draw_opaque;

// As the model is built (tools/build_clownfish.py prints these): its length, where its lower jaw hinges
// (how far along, how high, in body lengths) and where its gill cover's rear edge is.
const float LENGTH = 0.09;
const float HINGE_S = 0.047;
const float HINGE_Y = -0.011;
const float GILL_S = 0.235;
// How many body lengths one wave of the swimming bend is.
const float WAVE = 1.1;
// How far a pectoral fin's edge paddles out and in (body lengths; the build script checks the gap it
// leaves to the body with the same numbers: out to 1.5 of it, in to 0.5).
const float ROW_REACH = 0.05;

// How far through a beat it is (0..1), and how many times in a beat its tail beats and its pectoral fins
// paddle (whole numbers).
uniform float phase = 0.0;
uniform float tail_beats = 2.0;
uniform float strokes = 3.0;
// How widely its body and tail bend (1: the tail's tip a tenth of its length each way), how much the whole
// fish waggles from side to side about its middle (1: its snout about a twentieth of its length each
// way), and how hard its pectoral fins paddle.
uniform float sway = 0.6;
uniform float waggle = 1.0;
uniform float row = 1.0;
// Turning: how far the body is bent round to one side behind the gills, in radians from gills to tail
// (0 straight; more than 0 the tail comes round to +X). The head stays as it is.
uniform float curl = 0.0;
// The mouth: 0 shut, 1 wide open. `gape_angle` is how far (radians) the lower jaw swings down at 1, and
// `lip_lift` how far the snout's tip lifts with it.
uniform float gape = 0.0;
uniform float gape_angle = 0.75;
uniform float lip_lift = 0.15;

// The colours: the orange of the body (its back, side and belly), the white of the bands, the black that
// edges the bands and the fins, the fins' orange, the ring round the pupil, the inside of the mouth.
uniform vec3 orange_back : source_color = vec3(0.95, 0.33, 0.02);
uniform vec3 orange : source_color = vec3(1.0, 0.42, 0.04);
uniform vec3 orange_belly : source_color = vec3(1.0, 0.54, 0.14);
uniform vec3 white : source_color = vec3(0.97, 0.97, 0.95);
uniform vec3 black : source_color = vec3(0.025, 0.02, 0.02);
uniform vec3 fin_orange : source_color = vec3(1.0, 0.45, 0.06);
uniform vec3 eye_ring : source_color = vec3(0.5, 0.22, 0.04);
uniform vec3 mouth : source_color = vec3(0.2, 0.06, 0.05);
// How wide the black edges of the bands are (in body lengths).
uniform float edge_width = 0.011;
// How much it shines where it is seen aslant.
uniform float sheen = 0.3;

varying float part;
varying float inside;
varying float along_rest;


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


void vertex() {
	part = floor(COLOR.r * 10.0 + 0.5);
	inside = COLOR.b;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float s = v.z / LENGTH + 0.5;
	along_rest = s;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float tail = phase * TAU * tail_beats;
	float wave = tail - TAU * clamp(s, 0.0, 1.05) / WAVE;
	float open = clamp(gape, 0.0, 1.0);
	if (part == 1.0) {
		// The lower jaw swings down about its hinge at the corner of the mouth; the throat behind stays.
		about_hinge(v, n, open * gape_angle * smoothstep(HINGE_S + 0.024, HINGE_S - 0.008, s));
	} else if (part == 0.0) {
		// The snout's tip lifts a little as the mouth opens.
		about_hinge(v, n, -open * lip_lift * smoothstep(HINGE_S + 0.012, HINGE_S - 0.02, s));
	} else if (part >= 4.0) {
		vec3 flat_way = normalize(vec3(UV2.x, UV2.y, COLOR.b * 2.0 - 1.0));
		float r = UV.x;
		float across = COLOR.g;
		if (part == 9.0) {
			// The pectorals paddle: each stroke swings the fin out and back, then feathers it in and
			// forward, the leading edge leading; the two sides out of step, as a clownfish's are.
			float a = phase * TAU * strokes + (side_is > 0.0 ? 0.0 : PI) - across * 1.0;
			v += flat_way * (LENGTH * ROW_REACH * row * r * (sin(a) + 0.5));
			v.z += LENGTH * 0.045 * row * r * cos(a);
		} else if (part == 8.0) {
			float a = phase * TAU * strokes + (side_is > 0.0 ? 1.8 : 1.8 + PI);
			v += flat_way * (LENGTH * 0.015 * row * r * r * sin(a));
		} else if (part == 6.0) {
			// (the tail's edge lags behind the bend that carries it)
			v.x += LENGTH * 0.06 * sway * r * r * sin(wave - 1.1 - across * 0.4);
		} else {
			// The dorsal and anal fins ripple, a wave running back along them.
			v.x += LENGTH * 0.035 * sway * r * r * sin(wave - 1.0 - across * 2.0);
		}
	}
	// The waggle: the whole fish turns a little from side to side about a third of the way back.
	float yaw = waggle * 0.1 * sin(tail + 0.7);
	float pivot = (0.35 - 0.5) * LENGTH;
	vec2 d = vec2(v.x, v.z - pivot);
	v.x = d.x * cos(yaw) + d.y * sin(yaw);
	v.z = pivot - d.x * sin(yaw) + d.y * cos(yaw);
	n.xz = vec2(n.x * cos(yaw) + n.z * sin(yaw), -n.x * sin(yaw) + n.z * cos(yaw));
	// The swimming bend: a short wave from head to tail, the tail swinging widest. Each place is carried
	// sideways and turned to lie along the bent body, so the fins follow it.
	float sb = clamp(v.z / LENGTH + 0.5, 0.0, 1.05);
	float reach = 0.012 - 0.05 * sb + 0.135 * sb * sb;
	float reach_slope = -0.05 + 0.27 * sb;
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


// How far a place is outside the nearest white band (in body lengths along the fish; less than 0 inside
// it): the head band behind the eye, bowed back at its middle; the middle band, with a wedge pointing
// forward at its middle that runs up into the dorsal fin; the narrow band round the tail's wrist.
float out_of_bands(float s, float h) {
	float bow = 1.0 - pow(2.0 * h - 1.0, 2.0);
	float head_band = abs(s - (0.205 + 0.04 * bow)) - (0.03 + 0.004 * bow);
	float wedge = max(0.0, 1.0 - abs(h - 0.46) * 2.6);
	float middle_band = abs(s - (0.5 - 0.06 * wedge)) - (0.034 + 0.03 * wedge);
	float tail_band = abs(s - 0.783) - 0.02;
	return min(min(head_band, middle_band), tail_band);
}


// The colour of a place on the body (`s` along, `h` up): orange, white in the bands, black at their edges.
vec3 skin(float s, float h) {
	vec3 c = mix(orange_belly, orange, smoothstep(0.05, 0.4, h));
	c = mix(c, orange_back, smoothstep(0.7, 1.0, h));
	float d = out_of_bands(s, h);
	float soft = 0.0025;
	c = mix(c, black, 1.0 - smoothstep(edge_width - soft, edge_width + soft, d));
	c = mix(c, white, 1.0 - smoothstep(-soft, soft, d));
	return c;
}


void fragment() {
	vec3 c = orange;
	float rough = 0.42;
	float glint = sheen;
	if (part < 1.5) {
		// The body and the lower jaw.
		float s = UV.x;
		float h = UV.y;
		c = skin(s, h);
		// (the lips a little darker)
		c *= 1.0 - 0.25 * (1.0 - smoothstep(0.02, 0.045, s)) * smoothstep(0.25, 0.0, abs(h - 0.12) * 2.0);
		// (where the skin runs out over the root of the tail it takes the tail's colour)
		c = mix(c, fin_orange, smoothstep(0.815, 0.83, s));
		c = mix(c, mouth, inside);
		glint *= 1.0 - inside;
	} else if (part < 2.5) {
		// An eye: a black pupil in an orange-brown ring, dark at its rim.
		vec2 on_eye = UV * 2.0 - 1.0;
		float r = length(on_eye);
		c = mix(eye_ring * 1.3, eye_ring * 0.6, smoothstep(0.35, 0.6, r));
		c = mix(c, vec3(0.03), smoothstep(0.6, 0.7, r));
		c = mix(c, vec3(0.01), 1.0 - smoothstep(0.3, 0.34, r));
		rough = 0.08;
		glint = 0.0;
	} else {
		// A fin: orange, its rays as fine lines, edged with black.
		float r = UV.x;
		float between = abs(fract(UV.y) - 0.5) * 2.0;
		float lines = smoothstep(0.55, 1.0, between) * smoothstep(0.05, 0.3, r);
		c = fin_orange;
		if (part > 3.5 && part < 4.5) {
			// (the middle band runs up into the dorsal fin at its notch, white edged with black)
			float d = out_of_bands(along_rest - 0.03 * r, 1.0);
			c = mix(c, black, 1.0 - smoothstep(edge_width * 0.8 - 0.003, edge_width * 0.8 + 0.003, d));
			c = mix(c, white, 1.0 - smoothstep(-0.003, 0.003, d));
		}
		float rim = part > 8.5 ? 0.9 : 0.84;
		c = mix(c, black, smoothstep(rim, rim + 0.06, r));
		c *= 1.0 - 0.1 * lines;
		rough = 0.5;
		glint *= 0.4;
	}
	float seen = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	c += vec3(1.0, 0.95, 0.9) * glint * pow(1.0 - seen, 3.0);
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.4;
}
