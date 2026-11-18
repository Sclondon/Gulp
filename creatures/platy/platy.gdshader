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

void vertex() {
	part = UV2.y;
	rest = VERTEX;
	inside = UV2.x;
	vec3 v = VERTEX;
	float xm = v.z + HALF;
	float g = clamp(gape, 0.0, 1.0);
	if ((part < 0.5 || part > 6.5) && xm < JAW_TO) {
		v.z -= g * PROTRUDE * (1.0 - smoothstep(0.3 * JAW_TO, JAW_TO, xm));
		xm = v.z + HALF;
	}
	if (part > 6.5) {
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
		rough = mix(0.35, 0.85, inside);
		spec = mix(0.55, 0.2, inside);
	} else if (p == 6) {
		// An eye: a black pupil, a gold ring, a dark rim.
		float r = UV.x;
		c = mix(vec3(0.004, 0.004, 0.006), iris, smoothstep(0.5, 0.58, r));
		c = mix(c, back * 0.5, smoothstep(0.86, 1.0, r) * 0.8);
		rough = 0.12;
		spec = 0.65;
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
