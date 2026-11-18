shader_type spatial;
// The swordfish (swordfish.gd): every marking drawn here (no texture files), and its swimming.
// What each point is comes from the model (tools/build_swordfish.py): UV2.y the part (0 body, 1
// first dorsal, 2 the small fins, 3 the lower jaw, 4 the tail, 5 a pectoral fin, 6 an eye). UV, on
// the body and the lower jaw: x how far along, y how high on its side (1 the ridge of the back, 0
// the keel of the belly); on a fin: x root (0) to tip (1), y leading edge (0) to trailing edge
// (1); on an eye: x middle (0) to rim (1). UV2.x, on the body and the lower jaw: how far inside
// the mouth (0 skin and lips, 1 the middle of its roof or floor).
//
// It swims as tunas do (thunniform): the sword and head still, the body all but rigid, a wave that
// only grows large in the last third, the tail wrist flexing and the stiff crescent tail swung as
// one plate. All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 3.0;
const float HALF = 1.5;
// Where the lower jaw's tip is (metres behind the sword's tip): ahead of it there is only sword.
const float SWORD = 0.95;
// Where the tail fin is hinged: behind it the tail is one stiff plate.
const float JOINT = 2.68;
// Where the lower jaw hinges (metres behind the sword's tip, metres up), as the model has it, and how
// far it swings down for `gape` 1 (radians: its tip drops about 0.18 m).
const vec2 HINGE = vec2(1.33, -0.16);
const float GAPE_TURN = 0.5;
// Where the body starts to bend into a turn (just behind the gill covers).
const float CURL_FROM = 1.45;

// How far through a beat of its tail (0..1, it wraps). Set by Swordfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left).
// The sword and head stay as they are; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How far its mouth is open: 0 shut, 1 wide open, as when it bites. Set by Swordfish.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The cartoon eye (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0 the eye as it was (the default: nothing changes), 1 the cartoon eye: bigger, a clean white,
// a coloured iris, a big dark pupil, a highlight that stays put, a dark outline, and this animal's own lid. Its
// character: a deep diver's huge night eye: mostly iris, deep blue-green, a great round pupil, under a heavy brow that slopes down hard towards the sword, and a lower lid pushed up: gruff and stern.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the pupil and iris look, -1..1 each way in the eye's own plane: x forward (towards the snout), y up.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat (a fish has no lids) and, on the cartoon eye, a lid the colour of the
// skin comes down over it.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.15, 0.5, 0.62);
uniform vec3 eye_white : source_color = vec3(0.88, 0.9, 0.88);
// As the model is built: where the middle of the left eye lies on the skin (the build script prints it as
// EYE_MIDDLE; the right eye is its mirror), and the eye's radius. Then this animal's eye: how much bigger the
// cartoon eye is, its iris's and its pupil's size (shares of the eye's radius; the pupil's along and up), where
// its upper lid's edge rests (-1 the bottom of the eye, 1 the top; above 1 no lid) and how that slopes (more than
// 0 higher towards the snout), where its lower lid rests (below -1 none).
const vec3 EYE_MIDDLE = vec3(0.1008, 0.0400, -0.2950);
const float EYE_R = 0.05;
const float EYE_GROW = 1.5;
const float EYE_IRIS = 0.72;
const vec2 EYE_PUPIL = vec2(0.42, 0.42);
const float EYE_LID = 0.32;
const float EYE_SLANT = -0.45;
const float EYE_LOWER = -0.82;

// (the eye's dome made bigger about its middle on the skin, and squashed as it blinks)
void eye_vertex(inout vec3 v) {
	vec3 mid = vec3(sign(v.x) * EYE_MIDDLE.x, EYE_MIDDLE.y, EYE_MIDDLE.z);
	vec3 o = (v - mid) * mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
	o.y *= 1.0 - 0.6 * clamp(blink, 0.0, 1.0);
	v = mid + o;
}

// The cartoon eye at a point of the still model's eye: its colour, and how much of it is lid (for roughness).
vec4 cartoon_eye(vec3 p, vec3 skin) {
	vec2 e = vec2(EYE_MIDDLE.z - p.z, p.y - EYE_MIDDLE.y) / EYE_R;
	float r = length(e);
	vec2 q = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.92 - EYE_IRIS) * 0.9;
	float iris_at = length(q) / EYE_IRIS;
	float pupil_at = length(q / EYE_PUPIL);
	vec3 c = eye_white * (1.0 - 0.12 * smoothstep(0.5, 0.9, r));
	vec3 ring = eye_iris * (0.6 + 0.55 * smoothstep(1.0, 0.35, iris_at));
	c = mix(c, ring, 1.0 - smoothstep(0.94, 1.0, iris_at));
	c = mix(c, eye_iris * 0.25, smoothstep(0.8, 0.95, iris_at) * (1.0 - smoothstep(0.95, 1.0, iris_at)));
	c = mix(c, vec3(0.008, 0.008, 0.012), 1.0 - smoothstep(0.9, 1.0, pupil_at));
	// (the highlights stay put, up and forward, wherever it looks)
	float shine = 1.0 - smoothstep(0.1, 0.14, length(e - vec2(0.2, 0.15)));
	shine = max(shine, 0.8 * (1.0 - smoothstep(0.05, 0.08, length(e - vec2(-0.12, -0.22)))));
	c = mix(c, vec3(1.0), shine);
	// the dark outline
	c = mix(c, vec3(0.01, 0.01, 0.015), smoothstep(0.8, 0.86, r));
	// the lids: the upper comes down as it blinks, its edge a dark line
	float b = clamp(blink, 0.0, 1.0);
	float edge = mix(EYE_LID + EYE_SLANT * e.x, -1.05, b);
	float lower = EYE_LOWER;
	float lid = max(smoothstep(edge - 0.025, edge + 0.025, e.y), 1.0 - smoothstep(lower - 0.025, lower + 0.025, e.y));
	float line = (1.0 - smoothstep(0.05, 0.1, abs(e.y - edge))) * step(edge, 1.0);
	line = max(line, (1.0 - smoothstep(0.05, 0.1, abs(e.y - lower))) * step(-1.0, lower));
	c = mix(c, skin, lid);
	c = mix(c, vec3(0.01, 0.01, 0.015), line * 0.85 * step(r, 0.9));
	return vec4(c, lid);
}

// The gills (added 2026-11-18; the user: "The fish need modeled gills as well, well for relevant fish, so like when
// it opens its mouth wide you can see them"). The model has a short throat inside the head, its floor just above
// the rear of the roof of the mouth, lined with four gill arches a side (part 7: UV.x the kind, 0 the throat's
// wall, 1 a bar, 2 its filaments, 3 its rakers, plus a tenth of the arch's number; UV.y how deep; UV2.x how far
// along the arch). While the mouth is open, the roof is cut open over the throat (THROAT_HOLE: its middle and half
// length along the body, metres behind the snout's tip, its half width, and the height below which the skin there
// is the roof), the arches spread a little and the gill covers lift (COVER_FLARE metres at their rear edge, over
// COVER_BAND metres ahead of it), red filaments showing in the gap. With the mouth shut nothing of it changes.
const vec2 THROAT_HOLE = vec2(1.1925, 0.0225);
const float THROAT_HOLE_W = 0.026;
const float THROAT_HOLE_Y = 0.06;
const float COVER_BAND = 0.12;
const float COVER_FLARE = 0.015;
const float ARCH_SPREAD = 0.006;
uniform vec3 gill_red : source_color = vec3(0.62, 0.04, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.8, 0.72);

// (the edge of the gill cover, as gill_x has it)
float gill_edge(float y) {
	return 1.43 - 1.5 * (y + 0.02) * (y + 0.02);
}

// (how much of the gill cover's lift a point of the skin takes: its rear band, the lower and middle of the side)
float cover_lift(vec3 p, float high) {
	float c = high * 2.0 - 1.0;
	float ahead = gill_edge(p.y) - (p.z + HALF);
	float mask = smoothstep(-0.95, -0.8, c) * (1.0 - smoothstep(0.4, 0.6, c));
	return step(0.0, ahead) * (1.0 - smoothstep(0.0, COVER_BAND, ahead)) * mask;
}
// How widely it beats, for 1 as a swordfish cruising (its tail tips swing about 0.29 m either way).
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths (the body: lower jaw to tail).
uniform float wave = 1.2;

// The back, the bronze it turns to towards the flank, and the purple-blue where light glances off it.
uniform vec3 back : source_color = vec3(0.06, 0.05, 0.055);
uniform vec3 bronze : source_color = vec3(0.3, 0.2, 0.12);
uniform vec3 sheen : source_color = vec3(0.16, 0.14, 0.42);
// The flank under the dark back, and the belly it shades to.
uniform vec3 flank : source_color = vec3(0.42, 0.33, 0.27);
uniform vec3 belly : source_color = vec3(0.8, 0.78, 0.74);
// The inside of the mouth.
uniform vec3 mouth : source_color = vec3(0.05, 0.02, 0.025);
// The fins.
uniform vec3 fin_dark : source_color = vec3(0.1, 0.075, 0.06);
// The eye's iris.
uniform vec3 iris : source_color = vec3(0.2, 0.25, 0.33);

varying vec3 rest;
varying vec3 rest_normal;
varying float part;

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

// How far to one side the middle line of the body is, `xm` metres behind the sword's tip: a wave
// that runs back along it, nothing at all in the sword and head, large only near the tail.
float side_at(float xm) {
	float s = max(xm - SWORD, 0.0) / (JOINT - SWORD);
	float reach = (LENGTH - SWORD) * 0.7 * (0.012 * s * s + 0.085 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = CURL_FROM - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - CURL_FROM);
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
	rest_normal = NORMAL;
	vec3 v = VERTEX;
	if (part > 5.5 && part < 6.5) {
		eye_vertex(v);
	}
	if (gape > 0.0 && part < 0.5) {
		// the gill cover lifts as the mouth opens
		v.x += sign(v.x) * clamp(gape, 0.0, 1.0) * COVER_FLARE * cover_lift(v, UV.y);
	}
	if (gape > 0.0 && part > 6.5 && UV.x > 0.5) {
		// the gill arches spread a little
		float arch = floor(fract(UV.x + 0.001) * 10.0 + 0.5);
		v.z += clamp(gape, 0.0, 1.0) * ARCH_SPREAD * (arch - 1.5);
	}
	vec3 n = NORMAL;
	if (part > 2.5 && part < 3.5) {
		// The lower jaw swings down about its hinge, all of it as one stiff piece.
		float a = clamp(gape, 0.0, 1.0) * GAPE_TURN;
		vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	}
	float xm = v.z + HALF;
	// (the tail, behind its hinge, is one stiff plate: it turns about the hinge)
	float zc = min(xm, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.006) - side_at(zc - 0.006)) / 0.012;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.9 * JOINT, JOINT, zc));
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	VERTEX = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	NORMAL = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}

// The edge of the gill cover, as the model has it.
float gill_x(float y) {
	return 1.43 - 1.5 * (y + 0.02) * (y + 0.02);
}

void fragment() {
	int p = int(part + 0.5);
	if (p == 0 && gape > 0.0) {
		// (the rear of the roof of the mouth opens onto the throat while the mouth is open)
		vec2 hole = vec2((rest.z + HALF - THROAT_HOLE.x) / THROAT_HOLE.y, rest.x / THROAT_HOLE_W);
		if (rest.y < THROAT_HOLE_Y && dot(hole, hole) < 1.0) {
			discard;
		}
	}
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	if (p == 0 || p == 3) {
		// The skin (no scales): a blackish-brown back, bronze and brown flanks, a pale belly.
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		float cloud = noise2(vec2(xm * 6.0, q * 2.5) + 4.0);
		float fine = noise2(vec2(xm * 90.0, q * 30.0));
		// Where the dark back ends: at the sword's edge, lower on the body, a little waved.
		float edge = mix(-0.05, 0.12, smoothstep(0.95, 1.5, xm)) + (cloud - 0.5) * 0.1;
		c = mix(belly, belly * vec3(0.8, 0.78, 0.77), smoothstep(-0.95, -0.4, q));
		c = mix(c, flank, smoothstep(edge - 0.75, edge - 0.12, q));
		c *= 0.95 + 0.1 * cloud;
		float dark = smoothstep(edge - 0.2, edge + 0.22, q);
		vec3 top = mix(bronze, back, smoothstep(edge - 0.05, edge + 0.45, q));
		top *= 0.9 + 0.2 * cloud;
		top += sheen * (0.75 * glance * glance + 0.06 * (fine - 0.5));
		c = mix(c, top, dark);
		// The sword: dark above, a paler grey-brown below.
		float blade = 1.0 - smoothstep(0.9, 1.05, xm);
		c = mix(c, mix(mix(flank, belly, 0.35), back * 1.4, smoothstep(-0.5, 0.3, q)), blade);
		// The head: inside the mouth, the gill cover's edge.
		float in_mouth = step(SWORD, xm) * (1.0 - step(1.34, xm));
		if (p == 0) {
			// (not right at the jaw's tip, where the roof shows from below beside it)
			in_mouth *= smoothstep(0.98, 1.04, xm) * smoothstep(0.75, 0.95, -rest_normal.y) * smoothstep(-0.2, -0.6, q);
		} else {
			in_mouth *= smoothstep(0.75, 0.95, rest_normal.y);
		}
		// (and its lining, which the model marks: the roof and the floor of the mouth, seen when it gapes)
		float lined = smoothstep(0.0, 0.12, UV2.x);
		c = mix(c, mouth, max(in_mouth * 0.9, lined));
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.4, 0.6, q));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.007, abs(behind - 0.004))) * 0.55 + (1.0 - smoothstep(0.0, 0.06, behind)) * step(0.0, behind) * 0.2;
		c = mix(c, c * 0.3, crease * span * step(xm, 1.8));
		// The tail wrist: dark along its keels.
		float wrist = smoothstep(2.4, 2.6, xm) * (1.0 - smoothstep(0.3, 0.75, abs(q)));
		c = mix(c, back * 1.2, wrist * 0.85);
		rough = mix(mix(0.32, 0.5, max(dark, wrist)), 0.7, lined);
		spec = mix(0.6, 0.4, max(dark, wrist));
	} else if (p == 1 || p == 2 || p == 4) {
		// The first dorsal, the small fins and the tail: dark brown, fine rays, a glance of blue.
		float rays = p == 4 ? 80.0 : 55.0;
		float ray = 0.5 + 0.5 * cos(UV.y * rays + UV.x * 6.0);
		c = fin_dark * (0.8 + 0.4 * ray);
		c = mix(c, back, (1.0 - smoothstep(0.0, 0.25, UV.x)) * 0.5);
		c += sheen * 0.35 * glance * glance;
		rough = 0.5;
		spec = 0.4;
	} else if (p == 5) {
		// A pectoral fin: dark above, a paler brown below.
		float ray = 0.5 + 0.5 * cos(UV.y * 50.0);
		vec3 above = fin_dark + sheen * 0.3 * glance;
		vec3 below = mix(fin_dark, flank, 0.6);
		c = mix(below, above, smoothstep(-0.15, 0.15, rest_normal.y)) * (0.85 + 0.15 * ray);
		rough = 0.55;
		spec = 0.3;
	} else if (p == 7) {
		// The throat and the gills: a dark throat, blood-red bars and filaments (fine ones across them), pale
		// rakers, all darker deeper in.
		float kind = floor(UV.x + 0.01);
		if (kind < 0.5) {
			c = mix(mouth, gill_red * 0.3, 0.6);
		} else if (kind < 1.5) {
			c = gill_red * 0.9;
		} else if (kind < 2.5) {
			c = gill_red * (0.85 + 0.45 * pow(abs(cos(UV2.x * 90.0)), 3.0));
		} else {
			c = gill_raker;
		}
		c *= mix(1.0, 0.6, clamp(UV.y, 0.0, 1.0));
		rough = 0.3;
		spec = 0.55;
	} else {
		// An eye: very large, a big blue-black pupil, a pale iris, a dark rim.
		float r = UV.x;
		vec3 ring = iris * (0.8 + 0.3 * noise2(vec2(rest.y, rest.z) * 260.0));
		c = mix(vec3(0.004, 0.006, 0.014), ring, smoothstep(0.7, 0.76, r));
		c = mix(c, back, smoothstep(0.88, 1.0, r) * 0.9);
		rough = 0.12;
		spec = 0.6;
		if (cartoon_eyes > 0.0) {
			vec4 toon = cartoon_eye(rest, mix(back, bronze, 0.6));
			c = mix(c, toon.rgb, cartoon_eyes);
			rough = mix(rough, mix(0.1, 0.5, toon.a), cartoon_eyes);
			spec = mix(spec, mix(0.7, 0.4, toon.a), cartoon_eyes);
		}
	}
	if (p == 0 && gape > 0.0) {
		// (under the lifted gill cover: red filaments in the gap)
		float behind = rest.z + HALF - gill_edge(rest.y);
		float c2 = UV.y * 2.0 - 1.0;
		float mask = smoothstep(-0.95, -0.8, c2) * (1.0 - smoothstep(0.4, 0.6, c2));
		float gap = (1.0 - smoothstep(0.0, COVER_BAND * 0.25, abs(behind - COVER_BAND * 0.05))) * mask * smoothstep(0.0, 0.3, gape);
		c = mix(c, gill_red * (0.55 + 0.45 * pow(abs(cos(rest.y * 600.0)), 2.0)), gap);
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
