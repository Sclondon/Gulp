shader_type spatial;
// The platy (platy.gd): every marking drawn here (no texture files), for each colouring (platy.gd's
// COLOURINGS sets them), and its swimming. What each point is comes from the model (tools/build_platy.py):
// UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an
// eye, 7 the lower jaw). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y
// how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to edge (1), y
// leading edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1).
//
// It swims as livebearers do (subcarangiform): a wave down the back half of its short body, the fan of its
// tail carried round behind its deep wrist and rippling a little. All of it is a function of `phase` alone,
// so a picture of it loops exactly. The mouth opens: `gape`. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model (the build script prints them).
const float LENGTH = 0.05;
const float HALF = 0.025;
const float JOINT = 0.0352;
const float JAW_TO = 0.0022;
const float HINGE_Y = -0.00016;
const float BODY_TO = 0.0375;
const vec2 EYE_AT = vec2(0.0051, 0.0013);
const float GILL_AT = 0.0098;
const float GAPE_OPEN = 1.0;
const float PROTRUDE = 0.0002;

uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats, for 1 as a platy swimming along.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;
// How much the fan of its tail ripples (0 stiff).
uniform float billow = 0.35;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The colours (platy.gd's COLOURINGS sets them). The body at the head and at the tail (a sunset's runs from
// yellow to red); the back it darkens to; the belly; the sheen where light glances off it.
uniform vec3 front : source_color = vec3(0.98, 0.72, 0.16);
uniform vec3 rear : source_color = vec3(0.95, 0.36, 0.08);
uniform vec3 back : source_color = vec3(0.86, 0.32, 0.07);
uniform vec3 belly : source_color = vec3(0.99, 0.88, 0.55);
uniform vec3 sheen : source_color = vec3(1.0, 0.85, 0.5);
uniform float sheen_amount = 0.4;
uniform float scales_show = 0.5;
// The fins' colour; how black they are (a wagtail's: 1); the lips black (a wagtail's: 1).
uniform vec3 fin : source_color = vec3(0.98, 0.5, 0.14);
uniform float fin_black = 0.0;
uniform float lips_black = 0.0;
// The mickey mouse mark at the root of the tail (a big black spot and two small ones behind it): 0 none.
uniform float mickey = 0.0;
uniform vec3 black : source_color = vec3(0.025, 0.025, 0.03);
uniform vec3 iris : source_color = vec3(0.8, 0.62, 0.3);
uniform vec3 mouth_inside : source_color = vec3(0.35, 0.1, 0.1);

// Cartoon eyes (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0, the default, is the eye drawn below, as it always was; 1 the cartoon eye: grown about
// its middle, a white, an iris, a round pupil, a highlight that stays put (up and forward, towards the light)
// and a dark rim, under an upper lid the colour of its head. The platy's: sweet, gentle and doe-eyed: a
// big iris (`iris`, set by its colouring) that fills most of the eye, so little white shows, a big pupil
// and two big soft highlights, the lid just over its top.
uniform float cartoon_eyes = 0.0;
// Where the cartoon eye looks, -1..1 each way: x towards the nose (+) or the tail, y up (+) or down.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat from above and below (a fish has no lids) and the lid comes down.
uniform float blink = 0.0;
// How much bigger the cartoon eye is; how far its grown rim sinks back towards the skin (up and down, along);
// its white; how wide its iris is (of the eye's face) and its pupil (of the iris); where the upper lid's edge
// rests (1 the top of the eye: no lid) and how much lower it comes at the front (less than 0 raises it there).
uniform float eye_grow = 1.55;
uniform vec2 eye_sink = vec2(90.0, 18.0);
uniform vec3 eye_white : source_color = vec3(0.97, 0.96, 0.92);
uniform float iris_size = 0.76;
uniform float pupil_size = 0.62;
uniform float lid = 0.86;
uniform float lid_slant = -0.1;
// As the model has it (the build script's EYE line): the left eye's middle on the skin and the way it faces
// (the right eye is its mirror), and its radius over the skin.
const vec3 EYE_MIDDLE = vec3(0.00312, 0.0013, -0.0199);
const vec3 EYE_OUT = vec3(0.9683, 0.1477, -0.2013);
const float EYE_RADIUS = 0.0016;

// The gills (added 2026-11-18; the user: "The fish need modeled gills as well, ... so like when it opens its
// mouth wide you can see them"): four arches a side in the throat behind the mouth, seen through it when it is
// open (closed in, they are not seen at all). As the model has them (the build script's GILLS line): the gap
// between two arches and where the throat ends. Their red, and their rakers' pale.
const float GILL_GAP = 0.00132;
const float THROAT_END = 0.0109;
uniform vec3 gill_red : source_color = vec3(0.66, 0.05, 0.07);
uniform vec3 gill_raker : source_color = vec3(0.9, 0.66, 0.62);

varying vec3 rest;
varying float part;
varying float inside;

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * (0.01 - 0.035 * s + 0.085 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * JOINT / (LENGTH * wave)));
}

void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2 * LENGTH;
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

// The cartoon eye grown about its middle, and squashed from above and below as it blinks (nothing moves
// while cartoon_eyes and blink are 0).
void eye_shape(inout vec3 v) {
	if (cartoon_eyes <= 0.0 && blink <= 0.0) {
		return;
	}
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	vec3 at = vec3(EYE_MIDDLE.x * side_is, EYE_MIDDLE.yz);
	vec3 o = normalize(vec3(EYE_OUT.x * side_is, EYE_OUT.yz));
	vec3 up = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
	vec3 d = v - at;
	float grow = mix(1.0, eye_grow, cartoon_eyes);
	// (grown across and outward; what lies behind its face is not pushed further in; the grown rim sinks
	// back as the head's skin falls away round it)
	float deep = min(dot(d, o), 0.0);
	vec3 across = d - o * dot(d, o);
	vec3 up_d = up * dot(across, up);
	float before = eye_sink.x * dot(up_d, up_d) + eye_sink.y * dot(across - up_d, across - up_d);
	d = (d - o * deep) * grow + o * deep;
	d -= o * before * (grow * grow - 1.0);
	d -= up * dot(d, up) * 0.85 * blink;
	v = at + d;
}

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	inside = UV2.x;
	vec3 v = VERTEX;
	float xm = v.z + HALF;
	float g = clamp(gape, 0.0, 1.0);
	if (part > 5.5 && part < 6.5) {
		eye_shape(v);
		xm = v.z + HALF;
	}
	// The gill arches spread a little apart as the mouth opens.
	if (part > 9.5) {
		v.z += g * 0.14 * GILL_GAP * (floor(UV.y) - 1.5);
		xm = v.z + HALF;
	}
	if ((part < 0.5 || (part > 6.5 && part < 7.5)) && xm < JAW_TO) {
		v.z -= g * PROTRUDE * (1.0 - smoothstep(0.3 * JAW_TO, JAW_TO, xm));
		xm = v.z + HALF;
	}
	if (part > 6.5 && part < 7.5) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = g * GAPE_OPEN * (1.0 - smoothstep(0.55 * JAW_TO, 0.97 * JAW_TO, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - HINGE_Y, xm - JAW_TO);
		v.y = HINGE_Y + d.x * ca + d.y * sa;
		v.z = JAW_TO - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	// The fan of the tail ripples: a wave that runs out from its root to its edge.
	if (part > 2.5 && part < 3.5) {
		float t = UV.x;
		v.x += billow * (0.4 + 0.6 * min(sway, 1.5)) * LENGTH * 0.03 * t * t * sin(6.2831853 * (phase - 0.6 * t));
	}
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0002) - side_at(zc - 0.0002)) / 0.0004;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.85 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(NORMAL.x * c + NORMAL.z * sn, NORMAL.y, -NORMAL.x * sn + NORMAL.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The mickey mouse mark at a place (metres behind the snout, metres up): 1 inside it.
float mickey_at(float xm, float y) {
	float head = length(vec2(xm - 0.0347, y));
	float ears = min(length(vec2(xm - 0.0366, y - 0.0023)), length(vec2(xm - 0.0366, y + 0.0023)));
	return max(1.0 - smoothstep(0.0021, 0.0025, head), 1.0 - smoothstep(0.0011, 0.0014, ears)) * mickey;
}

// The cartoon eye's colour at a place on its face: `e` x up, y forward, 1 at its rim. A round pupil.
vec3 cartoon_eye(vec2 e) {
	float r = length(e);
	vec2 q = e - vec2(eye_look.y, eye_look.x) * (0.92 - iris_size);
	float ri = length(q) / iris_size;
	float aa = fwidth(ri) + 0.01;
	vec3 c = eye_white * mix(1.0, 0.8, smoothstep(0.45, 1.0, r));
	vec3 ring = mix(iris * 1.2, iris * 0.6, smoothstep(0.3, 0.95, ri));
	ring = mix(ring, iris * 0.2, smoothstep(0.84, 1.0, ri));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ri));
	float pd = length(q) / (iris_size * pupil_size);
	float pa = fwidth(pd) + 0.02;
	c = mix(c, vec3(0.012), 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	// (the highlights: up and forward, where the light comes from, and a second one below behind)
	float glint = 1.0 - smoothstep(0.15, 0.19, length(e - vec2(0.32, 0.28)));
	glint = max(glint, 0.9 * (1.0 - smoothstep(0.1, 0.13, length(e - vec2(-0.2, -0.28)))));
	c = mix(c, vec3(1.0), glint);
	// (the dark outline, so that it reads from far off)
	return mix(c, vec3(0.04, 0.02, 0.01), smoothstep(0.84, 0.91, r));
}

// The gills' colour: `uv` as the model gives it (x 0 the rakers' side, about 0.35 the bar, 1 the filaments;
// y the arch's number plus how far along it), `xm` how far back: blood red, the filaments darker with fine
// lines across, the rakers pale, all darker deeper in the throat.
vec3 gills(vec2 uv, float xm) {
	float along = fract(uv.y);
	vec3 fringe = gill_red * 0.62 * (0.72 + 0.28 * cos(along * 160.0));
	vec3 c = mix(gill_red * 1.15, fringe, smoothstep(0.45, 0.9, uv.x));
	float teeth = 0.6 + 0.4 * step(0.45, fract(along * 11.0));
	c = mix(c, gill_raker, (1.0 - smoothstep(0.06, 0.24, uv.x)) * teeth);
	return c * (1.0 - 0.5 * smoothstep(JAW_TO, THROAT_END, xm));
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	float xm = rest.z + HALF;
	if (p == 0 || p == 7) {
		float q = UV.y * 2.0 - 1.0;
		// The body: the head's colour to the tail's, darker on the back, pale on the belly.
		c = mix(front, rear, smoothstep(0.008, 0.03, xm));
		c = mix(c, back, smoothstep(0.35, 0.9, q) * 0.7);
		c = mix(c, belly, (1.0 - smoothstep(-0.85, -0.3, q)) * 0.75);
		// The scales: in rows half a scale apart, their rear edges faint dark arcs. Not on the head.
		float behind = xm - (GILL_AT - 35.0 * (rest.y - 0.0005) * (rest.y - 0.0005));
		float arc = acos(clamp(q, -1.0, 1.0)) * 0.0058;
		float row = floor(arc / 0.0011);
		float along = xm / 0.0012 + 0.5 * mod(row, 2.0);
		vec2 f = vec2(fract(along), fract(arc / 0.0011));
		float rim = smoothstep(0.7, 0.96, length(vec2(f.x, (f.y - 0.5) * 1.2)));
		float scaled = smoothstep(0.0, 0.0012, behind) * (1.0 - smoothstep(BODY_TO - 0.004, BODY_TO - 0.001, xm));
		c *= 1.0 + scaled * scales_show * (0.08 * (hash3(vec3(floor(along), row, 2.0)) - 0.5) - 0.2 * rim);
		c += sheen * sheen_amount * glance * glance;
		// The gill cover's edge.
		c = mix(c, c * 0.55, (1.0 - smoothstep(0.0, 0.0002, abs(behind))) * smoothstep(-0.9, -0.6, q) * (1.0 - smoothstep(0.5, 0.75, q)) * 0.7);
		// The lips (a wagtail's are black): the snout ahead of the jaw's hinge.
		c = mix(c, black, lips_black * (1.0 - smoothstep(JAW_TO * 0.7, JAW_TO * 1.3, xm)));
		c = mix(c, black, mickey_at(xm, rest.y));
		c = mix(c, mouth_inside, inside);
		// (darker down the throat behind the hinge)
		c *= 1.0 - 0.6 * inside * smoothstep(JAW_TO, THROAT_END, rest.z + HALF);
		rough = mix(0.35, 0.85, inside);
		spec = mix(0.55, 0.2, inside);
	} else if (p == 10) {
		c = gills(UV, rest.z + HALF);
		rough = 0.35;
		spec = 0.6;
	} else if (p == 6) {
		// An eye: a black pupil, a gold ring, a dark rim.
		float r = UV.x;
		c = mix(vec3(0.004, 0.004, 0.006), iris, smoothstep(0.5, 0.58, r));
		c = mix(c, back * 0.5, smoothstep(0.86, 1.0, r) * 0.8);
		rough = 0.12;
		spec = 0.65;
		if (cartoon_eyes > 0.0 || blink > 0.0) {
			// (where it is on the eye's face: x up, y forward, 1 at its rim)
			vec2 e = vec2(rest.y - EYE_AT.y, EYE_AT.x - (rest.z + HALF)) / EYE_RADIUS;
			c = mix(c, cartoon_eye(e), cartoon_eyes);
			// (the upper lid, the colour of its head, with a dark edge: none until it blinks on the eye as it
			// was)
			float lid_edge = mix(mix(1.3, lid, cartoon_eyes) - lid_slant * cartoon_eyes * e.y, -1.3, blink);
			c = mix(c, vec3(0.04, 0.02, 0.01), smoothstep(lid_edge - 0.16, lid_edge - 0.06, e.x) * step(lid_edge, 1.2));
			c = mix(c, mix(front, back, 0.5), smoothstep(lid_edge - 0.05, lid_edge, e.x));
			rough = mix(rough, 0.4, smoothstep(lid_edge - 0.05, lid_edge, e.x));
		}
	} else {
		// The fins: their colour (black on a wagtail, but its pectorals stay clear), fine rays, paler and
		// clearer to their edges.
		float rays = p == 3 ? 20.0 : 9.0;
		vec3 own = mix(fin, black, fin_black * (p == 4 ? 0.0 : 1.0));
		c = mix(own, mix(own, belly, 0.45), smoothstep(0.3, 1.0, UV.x) * (1.0 - fin_black * 0.85));
		c *= 0.88 + 0.12 * pow(abs(cos(3.14159265 * UV.y * rays)), 4.0);
		if (p == 3) {
			c = mix(c, black, mickey_at(xm, rest.y));
		}
		rough = 0.5;
		spec = 0.35;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
