shader_type spatial;
// The blue marlin (blue_marlin.gd): every marking drawn here (no texture files), its mouth opened
// and its swimming. What each point is comes from the model (tools/build_blue_marlin.py): UV2.y the
// part (0 body, 1 the first dorsal, 2 the small middle fins, 3 the lower jaw, 4 the tail, 5 a
// pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body: x how far along, y how high on its
// side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip (1), y
// leading edge (0) to trailing edge (1); on the lower jaw: x tip (0) to rear end (1), y the middle
// of the mouth's floor (0) round to the chin (1); on an eye: x middle (0) to rim (1). UV2.x, on the
// body and the lower jaw: how much the point is inside the mouth (the roof and the floor).
//
// It swims as tunas and billfish do (thunniform): the head and bill one stiff piece, the body all
// but rigid, a wave that only grows large in the last third, the tail wrist flexing and the stiff
// crescent tail swung as one plate. All of it is a function of `phase` alone, so a picture of it
// loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 3.6;
const float HALF = 1.8;
// Ahead of this (metres behind the bill's tip) the head and bill are one stiff piece.
const float HEAD = 1.1;
// Where the tail fin is hinged: behind it the tail is one stiff plate.
const float JOINT = 3.22;
// The lower jaw's hinge (metres behind the bill's tip, metres above the middle line) and how far
// it swings down at `gape` 1 (radians).
const vec2 HINGE = vec2(0.81, -0.05);
const float GAPE_MAX = 0.42;
const float DORSAL_RAYS = 41.0;
const vec2 EYE_AT = vec2(0.775, 0.05);

// How far through a beat of its tail (0..1, it wraps). Set by BlueMarlin.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills
// to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left).
// The bill and head stay as they are; set it from how tightly the fish is turning.
uniform float curl = 0.0;
// How widely it beats, for 1 as a marlin cruising (its tail tips swing about 0.3 m either way).
uniform float sway = 1.0;
// The mouth: 0 shut, 1 wide open, as when it bites (the lower jaw swings down about its hinge).
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The cartoon eye (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0 the eye as it was (the default: nothing changes), 1 the cartoon eye: bigger, a clean white,
// a coloured iris, a big dark pupil, a highlight that stays put, a dark outline, and this animal's own lid. Its
// character: a proud, haughty eye: cobalt blue, a wide bar of a pupil lying flat, the upper lid level and half down, looking down its bill at everything.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the pupil and iris look, -1..1 each way in the eye's own plane: x forward (towards the snout), y up.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat (a fish has no lids) and, on the cartoon eye, a lid the colour of the
// skin comes down over it.
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.08, 0.3, 0.9);
uniform vec3 eye_white : source_color = vec3(0.94, 0.95, 0.98);
// As the model is built: where the middle of the left eye lies on the skin (the build script prints it as
// EYE_MIDDLE; the right eye is its mirror), and the eye's radius. Then this animal's eye: how much bigger the
// cartoon eye is, its iris's and its pupil's size (shares of the eye's radius; the pupil's along and up), where
// its upper lid's edge rests (-1 the bottom of the eye, 1 the top; above 1 no lid) and how that slopes (more than
// 0 higher towards the snout), where its lower lid rests (below -1 none).
const vec3 EYE_MIDDLE = vec3(0.0907, 0.0500, -1.0250);
const float EYE_R = 0.034;
const float EYE_GROW = 1.7;
const float EYE_IRIS = 0.62;
const vec2 EYE_PUPIL = vec2(0.44, 0.24);
const float EYE_LID = 0.28;
const float EYE_SLANT = 0.0;
const float EYE_LOWER = -1.5;

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
// the rear of the roof of the mouth, lined with four gill arches a side (part 8: UV.x the kind, 0 the throat's
// wall, 1 a bar, 2 its filaments, 3 its rakers, plus a tenth of the arch's number; UV.y how deep; UV2.x how far
// along the arch). While the mouth is open, the roof is cut open over the throat (THROAT_HOLE: its middle and half
// length along the body, metres behind the snout's tip, its half width, and the height below which the skin there
// is the roof), the arches spread a little and the gill covers lift (COVER_FLARE metres at their rear edge, over
// COVER_BAND metres ahead of it), red filaments showing in the gap. With the mouth shut nothing of it changes.
const vec2 THROAT_HOLE = vec2(0.735, 0.065);
const float THROAT_HOLE_W = 0.023;
const float THROAT_HOLE_Y = 0.03;
const float COVER_BAND = 0.12;
const float COVER_FLARE = 0.015;
const float ARCH_SPREAD = 0.007;
uniform vec3 gill_red : source_color = vec3(0.62, 0.04, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.8, 0.72);

// (the edge of the gill cover, as gill_x has it)
float gill_edge(float y) {
	return 1.07 - 1.5 * (y + 0.03) * (y + 0.03);
}

// (how much of the gill cover's lift a point of the skin takes: its rear band, the lower and middle of the side)
float cover_lift(vec3 p, float high) {
	float c = high * 2.0 - 1.0;
	float ahead = gill_edge(p.y) - (p.z + HALF);
	float mask = smoothstep(-0.95, -0.8, c) * (1.0 - smoothstep(0.4, 0.6, c));
	return step(0.0, ahead) * (1.0 - smoothstep(0.0, COVER_BAND, ahead)) * mask;
}
// How long the wave along its body is, in body lengths.
uniform float wave = 1.2;

// The back, and the cobalt it turns to towards the flank and where light glances off it.
uniform vec3 back : source_color = vec3(0.008, 0.02, 0.09);
uniform vec3 back_blue : source_color = vec3(0.02, 0.13, 0.62);
// The lower flank and the belly.
uniform vec3 silver : source_color = vec3(0.7, 0.75, 0.8);
uniform vec3 belly : source_color = vec3(0.95, 0.96, 0.96);
// The upright pale bars down the flanks, and how strongly they show.
uniform vec3 bars : source_color = vec3(0.42, 0.68, 1.0);
uniform float bars_show = 0.75;
// The fins, the bill, the inside of the mouth.
uniform vec3 fin_dark : source_color = vec3(0.012, 0.03, 0.11);
uniform vec3 bill : source_color = vec3(0.02, 0.035, 0.09);
uniform vec3 mouth : source_color = vec3(0.07, 0.018, 0.022);

varying vec3 rest;
varying float part;
varying float inside;

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

// How far to one side the middle line of the body is, `xm` metres behind the bill's tip: a wave
// that runs back along it, all but nothing as far as the middle, large only near the tail.
float side_at(float xm) {
	float s = xm / JOINT;
	float reach = LENGTH * 0.4 * (0.006 - 0.02 * s + 0.02 * s * s + 0.09 * s * s * s * s);
	return sway * reach * sin(6.2831853 * (phase - s / wave));
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = 1.15 - HALF;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / (LENGTH - 1.15);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}

void vertex() {
	part = UV2.y;
	inside = UV2.x;
	rest = VERTEX;
	vec3 v = VERTEX;
	if (part > 6.5 && part < 7.5) {
		eye_vertex(v);
	}
	if (gape > 0.0 && part < 0.5) {
		// the gill cover lifts as the mouth opens
		v.x += sign(v.x) * clamp(gape, 0.0, 1.0) * COVER_FLARE * cover_lift(v, UV.y);
	}
	if (gape > 0.0 && part > 7.5 && UV.x > 0.5) {
		// the gill arches spread a little
		float arch = floor(fract(UV.x + 0.001) * 10.0 + 0.5);
		v.z += clamp(gape, 0.0, 1.0) * ARCH_SPREAD * (arch - 1.5);
	}
	vec3 n = NORMAL;
	if (part > 2.5 && part < 3.5) {
		// The lower jaw swings down about its hinge; its rear end, in the throat, stays.
		float a = clamp(gape, 0.0, 1.0) * GAPE_MAX * smoothstep(HINGE.x + 0.06, HINGE.x - 0.01, v.z + HALF);
		vec2 hinge = vec2(HINGE.y, HINGE.x - HALF);
		vec2 d = v.yz - hinge;
		float c = cos(a);
		float sn = sin(a);
		v.yz = hinge + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
		n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
	}
	float xm = v.z + HALF;
	// (the head and bill ahead, and the tail behind its hinge, are stiff: they turn as one piece)
	float zc = clamp(xm, HEAD, JOINT);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.004) - side_at(zc - 0.004)) / 0.008;
	// (the wrist flexes a little further than the body's own line)
	float turn = atan(slope) * (1.0 + 0.3 * smoothstep(0.86 * JOINT, JOINT, zc));
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
	return 1.07 - 1.5 * (y + 0.03) * (y + 0.03);
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
	float rough = 0.42;
	float spec = 0.5;
	if (p == 0) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		// (a fine grain, like small scales)
		float grain = 0.6 * noise2(vec2(xm * 400.0, q * 90.0)) + 0.4 * noise2(vec2(xm * 900.0 + 7.0, q * 200.0));
		float cloud = noise2(vec2(xm * 5.0, q * 3.0) + 4.0);
		// The belly white, the lower flank silver, the back cobalt blue, nearly black along its ridge.
		c = mix(belly, silver, smoothstep(-0.8, -0.1, q));
		c *= 0.95 + 0.1 * grain;
		float dark = smoothstep(-0.12, 0.2, q + (cloud - 0.5) * 0.1);
		vec3 top = mix(back_blue, back, smoothstep(0.35, 0.9, q));
		top += back_blue * (0.8 * glance * glance + 0.1 * (grain - 0.5));
		c = mix(c, top, dark);
		// The bars: about fifteen upright pale blue bars down the flanks, each a narrow stripe broken
		// into round dots, from behind the gill cover to the tail wrist.
		float lane = (xm - 1.13) / 0.125;
		float row = floor(lane);
		float lean = (noise2(vec2(row * 3.1, y * 9.0)) - 0.5) * 0.03;
		float across = (fract(lane) - 0.5) * 0.125 + lean;
		float stripe = 1.0 - smoothstep(0.007, 0.02, abs(across));
		float down = y / 0.034 + hash2(vec2(row, 5.0));
		float bead = 1.0 - smoothstep(0.2, 0.5, abs(fract(down) - 0.5));
		float pale = stripe * (0.45 + 0.55 * bead);
		float where = smoothstep(1.13, 1.2, xm) * (1.0 - smoothstep(2.95, 3.05, xm)) * (1.0 - smoothstep(0.6, 0.85, q)) * smoothstep(-0.55, -0.15, q);
		c = mix(c, bars, pale * where * bars_show);
		// The bill and the top of the head: blue-black, paler underneath.
		float beak = (1.0 - smoothstep(0.55, 0.85, xm)) * smoothstep(-0.7, 0.0, q);
		c = mix(c, bill * (0.9 + 0.2 * grain), beak);
		// The gill cover's edge.
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.4, 0.6, q));
		float behind = xm - gill_x(y);
		float crease = (1.0 - smoothstep(0.0, 0.006, abs(behind - 0.003))) * 0.6 + (1.0 - smoothstep(0.0, 0.05, behind)) * step(0.0, behind) * 0.22;
		c = mix(c, c * 0.35, crease * span);
		// The tail wrist: dark along its keels.
		float wrist = smoothstep(3.0, 3.12, xm) * (1.0 - smoothstep(0.35, 0.75, abs(q)));
		c = mix(c, back, wrist * 0.85);
		rough = mix(0.3, 0.5, max(dark, wrist));
		spec = mix(0.65, 0.4, max(dark, wrist));
		// The roof of the mouth.
		float in_mouth = smoothstep(0.3, 0.7, inside);
		c = mix(c, mouth, in_mouth);
		rough = mix(rough, 0.6, in_mouth);
		spec = mix(spec, 0.2, in_mouth);
	} else if (p == 1) {
		// The first dorsal: blue-black, darker along its rays, a little cobalt where light glances.
		float ray = pow(abs(cos(3.14159265 * UV.y * DORSAL_RAYS)), 10.0);
		float cloud = noise2(vec2(rest.z * 6.0, rest.y * 6.0) + 11.0);
		c = mix(fin_dark * 0.7, fin_dark * 1.6 + back_blue * 0.12, smoothstep(0.0, 0.5, UV.x)) * (0.8 + 0.4 * cloud);
		c = mix(c, fin_dark * 0.4, ray * 0.6);
		c += back_blue * 0.4 * glance * glance;
		rough = 0.5;
		spec = 0.4;
	} else if (p == 2) {
		// The second dorsal and the anal fins: blue-black, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 50.0);
		c = fin_dark * (0.8 + 0.4 * ray) + back_blue * 0.3 * glance * glance;
		rough = 0.5;
	} else if (p == 3) {
		// The lower jaw: silver-white, dusky towards its tip; its top is the floor of the mouth.
		c = mix(silver, belly, smoothstep(0.55, 0.95, UV.y));
		c = mix(c, bill * 3.0, (1.0 - smoothstep(0.0, 0.5, UV.x)) * 0.6);
		float in_mouth = smoothstep(0.3, 0.7, inside);
		c = mix(c, mouth, in_mouth);
		rough = mix(0.4, 0.6, in_mouth);
		spec = mix(0.5, 0.2, in_mouth);
	} else if (p == 4) {
		// The tail: blue-black, fine rays.
		float ray = 0.5 + 0.5 * cos(UV.y * 90.0);
		c = fin_dark * (0.8 + 0.4 * ray);
		c += back_blue * 0.4 * glance * glance;
		rough = 0.45;
	} else if (p == 5) {
		// A pectoral fin: blue-black, a little paler towards its root.
		float ray = 0.5 + 0.5 * cos(UV.y * 60.0);
		c = mix(fin_dark * 2.0 + silver * 0.08, fin_dark, smoothstep(0.0, 0.5, UV.x)) * (0.85 + 0.3 * ray);
		c += back_blue * 0.35 * glance * glance;
		rough = 0.5;
		spec = 0.35;
	} else if (p == 6) {
		// A pelvic fin: blue-black.
		c = fin_dark * 1.2 + back_blue * 0.25 * glance * glance;
		rough = 0.5;
	} else if (p == 8) {
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
		// An eye: a big black pupil, a silver-blue iris, a dark rim.
		float r = UV.x;
		vec3 iris = mix(vec3(0.42, 0.47, 0.52), vec3(0.55, 0.6, 0.55), smoothstep(0.7, 0.95, r) * 0.4) * (0.85 + 0.15 * noise2(vec2(atan(rest.y - EYE_AT.y, rest.z + HALF - EYE_AT.x) * 14.0, r * 3.0)));
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.56, 0.62, r));
		c = mix(c, back * 2.0, smoothstep(0.84, 1.0, r) * 0.9);
		rough = 0.14;
		spec = 0.6;
		if (cartoon_eyes > 0.0) {
			vec4 toon = cartoon_eye(rest, back_blue * 0.55);
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
