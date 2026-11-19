shader_type spatial;
// The kelp bass (kelp_bass.gd): it swims by a wave down its body and tail, hovers and turns by
// sculling its pectoral fins, breathes with its mouth and gill covers, and opens its mouth wide
// to feed (`gape`); every marking is drawn here, no texture files. Nothing here needs more than
// GL Compatibility has.
//
// What each point is comes from the model (tools/build_kelp_bass.py says it all): COLOR.r the part,
// as a tenth (0 body, 1 lower jaw, 2 eye, 3 maxilla, 4 spiny dorsal, 5 soft dorsal, 6 tail, 7
// anal, 8 pelvic, 9 pectoral, 10 the skin at each side of the mouth). On the body UV is (how far
// along, 0 the jaw's tip to 1 the tail's tip; how high, 0 the belly line to 1 the back line), UV2
// (how far round the skin from the back line, metres, + its right side; the whole way round to
// the belly line), COLOR.g the gill cover's moving edge, COLOR.b the roof of the mouth. On the
// lower jaw UV is where the point is when shut (along; 0 its keel to 1 its lip), COLOR.b the
// inside of the mouth. On a maxilla UV2 is where the point is from the plate's front end
// (metres: up, back). On a fin UV.x runs along its rays (0 root, 1 edge), UV.y across it counted
// in rays; on the paired fins UV2 and COLOR.b are the way their flat sides face. On the mouth's
// side skin UV.y runs from the upper lip (0) to the lower (1), UV2.x is how far out it is when
// the mouth is shut (metres, signed), COLOR.b its inner face.
//
// THE MOUTH: the model is built with it wide open (the lower jaw swung GAPE_MAX down about its
// hinge, the skins at its sides spread into a round tube); this shader shuts it by `gape`, so
// that what is seen wide open is just as it was modelled. As it opens, the lower jaw drops, the
// side skins unfold from between the lips, the maxillae swing their rear ends down, and the
// upper jaw pushes forward a little: the suction feeder's round mouth.
//
// Everything that moves runs on `phase` (0..1 through one beat, set by KelpBass): the tail
// beats, the breaths and the fins' sculls each go a whole number of times a beat, so a picture
// of it comes round again exactly.
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


// As the model is built (the build script's SHAPE line): its length (metres), where the lower
// jaw hinges (along, high: body lengths), where the gill cover's rear edge reaches, how far the
// jaw is swung open in the model (radians). Change them only with the build script.
const float LENGTH = 0.500;
const float HINGE_S = 0.1300;
const float HINGE_Y = -0.0380;
const float GILL_S = 0.2900;
const float GAPE_MAX = 0.800;
// (the front end of the maxilla, along and high: the build script's SP["maxilla"])
const float MAXILLA_S = 0.0220;
const float MAXILLA_Y = -0.0010;
// How many body lengths one wave of the swimming bend is.
const float WAVE = 1.0;
// How far the upper jaw pushes forward at `gape` 1 (body lengths), and how far the rear ends of
// the maxillae swing down (radians).
const float PROTRUDE = 0.018;
const float MAXILLA_SWING = 0.2;
// THE THROAT AND THE GILLS (added 2026-11-18). The model has a short tunnel, the throat, running
// back from the back of the mouth to the gill arches (the body's code, COLOR.b 1, UV2.y 0), and
// four gill arches a side in it (COLOR.r 0.04: part 11). As the mouth opens, the middle of the
// back of the roof of the mouth rises (ROOF_LIFT), the middle of its floor (the lower jaw's top
// about its hinge) drops (FLOOR_DROP), and the skin at the back of the mouth parts along its
// middle line out to THROAT_WIDE each way, so that the throat shows through the open mouth; shut,
// all of it lies inside the head and the lower jaw. The build script's THROAT line (body lengths).
const float THROAT_END = 0.2600;
const float THROAT_WIDE = 0.0283;
const float ROOF_LIFT = 0.0156;
const float FLOOR_DROP = 0.0187;
// The right eye where it stands on the skin (metres) and the way out of the skin there: the build
// script's EYE line (the left eye is its mirror picture).
const vec3 EYE_AT = vec3(0.0163, 0.0180, -0.2040);
const vec3 EYE_OUT = vec3(0.7814, 0.5361, -0.3195);
// THE CARTOON EYE (`cartoon_eyes`), the kelp bass's own: the scrappy, keen little hunter. A
// bright amber eye with a small sharp pupil and plenty of white (wide awake), under a brow that
// slants down towards its nose (a fierce, determined frown). How much bigger than life; the
// iris's and the pupil's sizes (of the eye's face, 0.6 its rim); a keyhole drawn out forward from
// the pupil (0 none); how far the upper lid comes down at rest (of the eye), how it slopes (+
// higher at the front); the lower lid; the white.
const float EYE_BIG = 1.45;
const float IRIS_R = 0.3;
const float PUPIL_R = 0.12;
const float KEYHOLE = 0.0;
const float LID_REST = 0.22;
const float LID_SLANT = -0.36;
const float LOWER_LID = 0.0;
const vec3 SCLERA = vec3(0.95, 0.95, 0.91);

// How far through a beat it is (0..1), and how many times in a beat its tail beats, it breathes
// and its pectoral fins scull (whole numbers).
uniform float phase = 0.0;
uniform float tail_beats = 2.0;
uniform float breaths = 2.0;
uniform float sculls = 2.0;
// How hard it swims: how far its tail swings (1 about a tenth of its length each way at the tip).
uniform float sway = 0.4;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is.
uniform float curl = 0.0;
// The mouth: 0 shut, 1 wide open, as when it sucks in its prey. Each breath opens it a little
// more (`gape_breath`, of the whole way), and the gill covers' edges lift with each breath
// (metres at scale 1).
uniform float gape = 0.0;
uniform float gape_breath = 0.06;
uniform float gill_flare = 0.004;
// How far the pectoral fins scull (1 as it hovers; they never stop), and the pelvic fins with them.
uniform float scull = 1.0;
// For a game: `flash` adds white light to the whole fish (a hit); `rim` lights its edges with its
// own colour so that it stands out (0 none).
uniform float flash = 0.0;
uniform float rim = 0.0;
// The eyes: `cartoon_eyes` 0 as in life, 1 the cartoon eye (bigger, a white, an iris, a big pupil,
// a highlight, an outline and its own lids); `eye_look` slides the iris and pupil (x + towards the
// nose, y + up, -1..1); `blink` 0 open to 1 shut (a lid the colour of the skin comes down).
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
uniform vec3 iris : source_color = vec3(0.92, 0.55, 0.1);
// The gill arches: the bar, the filaments behind it, the rakers in front.
uniform vec3 gill_red : source_color = vec3(0.6, 0.07, 0.06);
uniform vec3 gill_deep : source_color = vec3(0.36, 0.02, 0.04);
uniform vec3 gill_raker : source_color = vec3(0.66, 0.5, 0.46);

// The colours.
// Olive brown on the back with two rows of pale squarish blotches along it (the calico), greyer
// olive on the sides with fainter pale patches, a yellowish cream belly; yellowish fins.
uniform vec3 back : source_color = vec3(0.2, 0.18, 0.09);
uniform vec3 side : source_color = vec3(0.33, 0.31, 0.19);
uniform vec3 belly : source_color = vec3(0.78, 0.72, 0.46);
uniform vec3 pale : source_color = vec3(0.74, 0.72, 0.54);
uniform vec3 fin_dark : source_color = vec3(0.24, 0.22, 0.12);
uniform vec3 fin_tail : source_color = vec3(0.5, 0.44, 0.2);
uniform vec3 fin_paired : source_color = vec3(0.72, 0.6, 0.24);
// How strongly the pale blotches show; how mottled the skin is.
uniform float blotch_amount = 0.85;
uniform float mottle = 1.0;
uniform vec3 mouth : source_color = vec3(0.16, 0.08, 0.08);
uniform vec3 eye_ring : source_color = vec3(0.55, 0.45, 0.28);
// How clearly the scales show; how strong the sheen is.
uniform float scales = 0.6;
uniform float sheen = 0.18;

varying vec3 rest;
varying float part;
varying vec2 extra;
varying float throat_dark;


float gill_edge(float h) {
	return GILL_S - 0.25 * (h - 0.45) * (h - 0.45);
}


vec4 hash4(vec2 p) {
	vec4 q = fract(p.xyxy * vec4(0.1031, 0.1030, 0.0973, 0.1099));
	q += dot(q, q.wzxy + 33.33);
	return fract((q.xxyz + q.yzzw) * q.zywx);
}


// Soft patches, 0..1, a patch to each 1 of `p`.
float cloud(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash4(i).x, hash4(i + vec2(1.0, 0.0)).x, f.x), mix(hash4(i + vec2(0.0, 1.0)).x, hash4(i + vec2(1.0, 1.0)).x, f.x), f.y);
}


// Blotches on a grid of `cell` (x along, y round, body lengths), each shifted and sized at random,
// their edges wobbled by soft noise; `scale_y` stretches them round the body (below 1 they are
// longer than they are tall); `ragged` how uneven their edges are. 0..1, how much a place is
// inside one; `keep` of the cells have one.
float blotches(vec2 p, vec2 cell, float size, float keep, float seed, float ragged) {
	vec2 q = p / cell;
	vec2 id = floor(q);
	float best = 0.0;
	for (int dx = -1; dx <= 1; dx++) {
		for (int dy = -1; dy <= 1; dy++) {
			vec2 c = id + vec2(float(dx), float(dy));
			vec4 r = hash4(c + seed);
			if (r.z > keep) {
				continue;
			}
			vec2 at = c + 0.5 + (r.xy - 0.5) * 0.7;
			vec2 d = (q - at) / (size * (0.7 + 0.6 * r.w));
			float wobble = ragged * (0.7 * cloud(q * 2.3 + c * 1.7) + 0.3 * cloud(q * 6.1 - c) - 0.5);
			best = max(best, 1.0 - smoothstep(0.75, 1.0, length(d) + wobble));
		}
	}
	return best;
}


// Turns a point and its normal about a line across the fish (along X) through `about` (y, z).
void swing(inout vec3 v, inout vec3 n, vec2 about, float a) {
	float c = cos(a);
	float sn = sin(a);
	vec2 d = v.yz - about;
	v.yz = about + vec2(d.x * c + d.y * sn, d.y * c - d.x * sn);
	n.yz = vec2(n.y * c + n.z * sn, n.z * c - n.y * sn);
}


// How much of the jaw's swing a place takes (the throat behind the hinge stays): as the build
// script's jaw_weight.
float jaw_weight(float s) {
	return 1.0 - smoothstep(HINGE_S - 0.03, HINGE_S + 0.07, s);
}


// How much of the upper jaw's push forward a place on the head takes: the upper lip and the snout
// ahead of the corner of the mouth, not the forehead.
float lip_weight(float s, float h) {
	return (1.0 - smoothstep(HINGE_S - 0.03, HINGE_S + 0.02, s)) * (1.0 - smoothstep(0.2, 0.55, h));
}


// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = (GILL_S - 0.5) * LENGTH;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / ((1.0 - GILL_S) * LENGTH);
	float a = d * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	v = vec3(r + (v.x - r) * c, v.y, from + (r - v.x) * sn);
}


void vertex() {
	bake_uv = CUSTOM0.xy;

	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	// (the gill arches: a code a little off the tenths, read as part 11)
	if (COLOR.r * 10.0 - part > 0.25) {
		part = 11.0;
	}
	throat_dark = 0.0;
	extra = COLOR.gb;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float breath = phase * TAU * breaths;
	float tail = phase * TAU * tail_beats;
	float open = clamp(gape + gape_breath * (0.5 - 0.5 * cos(breath)), 0.0, 1.0);
	// (eased, so that the jaw starts and ends its swing gently)
	float shut = GAPE_MAX * (1.0 - open);
	float push = PROTRUDE * LENGTH * open;
	vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5) * LENGTH;
	if (part == 1.0) {
		// The lower jaw, built open: swung shut about its hinge as far as the mouth is not open.
		swing(v, n, hinge, -shut * jaw_weight(UV.x));
		// The middle of its top about the hinge, the floor of the back of the mouth, drops as the
		// mouth opens, into the throat.
		float drop = smoothstep(HINGE_S - 0.05, HINGE_S - 0.015, UV.x) * (1.0 - smoothstep(HINGE_S + 0.05, HINGE_S + 0.075, UV.x));
		drop *= (1.0 - smoothstep(0.7, 1.05, abs(rest.x) / (THROAT_WIDE * LENGTH))) * smoothstep(0.5, 0.85, UV.y) * open;
		v.y -= FLOOR_DROP * LENGTH * drop;
		throat_dark = drop;
	} else if (part == 10.0) {
		// The side skin of the mouth: its lower edge goes with the jaw's lip, its upper edge with
		// the upper lip and the maxilla; shut, it lies flat between the lips.
		float w = UV.y;
		swing(v, n, hinge, -shut * jaw_weight(UV.x) * w);
		swing(v, n, vec2(MAXILLA_Y, MAXILLA_S - 0.5) * LENGTH, -MAXILLA_SWING * open * (1.0 - w));
		v.x = mix(v.x, UV2.x, 1.0 - open);
		v.z -= push * (1.0 - w) * lip_weight(UV.x, 0.0);
		v.y -= 0.3 * push * (1.0 - w) * lip_weight(UV.x, 0.0);
	} else if (part == 3.0) {
		// A maxilla: its rear end swings down about its front, and it goes forward with the lip.
		vec2 front = v.yz - UV2;
		swing(v, n, front, -MAXILLA_SWING * open);
		v.z -= push;
		v.y -= 0.3 * push;
	} else if (part == 2.0) {
		// An eye: the cartoon eye is bigger, spread across the skin more than it stands out of it.
		if (cartoon_eyes > 0.0) {
			float big = mix(1.0, EYE_BIG, cartoon_eyes);
			float big_out = sqrt(big);
			vec3 at = vec3(side_is * EYE_AT.x, EYE_AT.y, EYE_AT.z);
			vec3 o = vec3(side_is * EYE_OUT.x, EYE_OUT.y, EYE_OUT.z);
			vec3 d = v - at;
			float d_out = dot(d, o);
			v = at + (d - o * d_out) * big + o * d_out * big_out;
			float n_out = dot(n, o);
			n = (n - o * n_out) / big + o * n_out / big_out;
		}
	} else if (part == 0.0) {
		// The upper lip and snout push forward; the gill covers lift at their rear edges, a little
		// after the mouth opens, and stand out as it opens wide.
		float lw = lip_weight(UV.x, UV.y);
		v.z -= push * lw;
		v.y -= 0.3 * push * lw;
		v.x += side_is * COLOR.g * gill_flare * (0.5 - 0.5 * cos(breath - 1.3) + 1.5 * open);
		// The middle of the back of the roof of the mouth rises as it opens, and the skin at the
		// back of the mouth parts along its middle line, to show the throat (whose UV2.y is 0: it
		// stays as it is).
		if (UV2.y > 0.0001) {
			float across = 1.0 - smoothstep(0.7, 1.05, abs(rest.x) / (THROAT_WIDE * LENGTH));
			float lift = smoothstep(HINGE_S - 0.045, HINGE_S - 0.012, UV.x) * (1.0 - smoothstep(HINGE_S + 0.005, HINGE_S + 0.02, UV.x));
			lift *= smoothstep(0.2, 0.6, COLOR.b) * across * open;
			v.y += ROOF_LIFT * LENGTH * lift;
			float parted = smoothstep(HINGE_S - 0.022, HINGE_S - 0.006, UV.x) * (1.0 - smoothstep(HINGE_S + 0.012, HINGE_S + 0.025, UV.x));
			parted *= across * open;
			v.x = mix(v.x, (UV2.x >= 0.0 ? 1.0 : -1.0) * THROAT_WIDE * LENGTH, parted);
			throat_dark = max(lift, parted);
		}
	} else if (part == 11.0) {
		// The gill arches spread a little as the mouth opens.
		v.x *= 1.0 + 0.08 * open;
	} else if (part >= 4.0) {
		// A fin waves the way its flat side faces, more towards its edge.
		vec3 flat_way = normalize(vec3(UV2.x, UV2.y, COLOR.b * 2.0 - 1.0));
		float r = UV.x;
		float turn = phase * TAU * sculls;
		if (part == 9.0) {
			// the pectorals scull, one a little after the other, the stroke running out to the edge
			// (more out from the body than in towards it: the build script measures the gap left)
			float a = turn + (side_is > 0.0 ? 0.0 : 1.3);
			v += flat_way * LENGTH * 0.026 * scull * (0.65 * r * (sin(a) + 0.35) + 0.7 * r * r * sin(a - 1.2));
		} else if (part == 8.0) {
			float a = turn + (side_is > 0.0 ? 2.2 : 3.3);
			v += flat_way * LENGTH * 0.012 * scull * r * r * sin(a - UV.y * 0.25);
		} else if (part == 6.0) {
			// (the tail's edge lags behind the bend that carries it)
			float s = v.z / LENGTH + 0.5;
			v.x += LENGTH * 0.03 * sway * r * r * sin(tail - TAU * s / WAVE - 1.1);
		} else {
			float s = v.z / LENGTH + 0.5;
			v.x += LENGTH * 0.012 * sway * r * r * sin(tail - TAU * s / WAVE - 1.0 - UV.y * 0.2);
		}
	}
	// The swimming bend: a wave that runs from head to tail, the head nearly still and the tail
	// swinging widest. Each place is carried sideways and turned to lie along the bent body.
	float sb = clamp(v.z / LENGTH + 0.5, 0.0, 1.05);
	float reach = 0.01 - 0.06 * sb + 0.15 * sb * sb;
	float reach_slope = -0.06 + 0.3 * sb;
	float w = tail - TAU * sb / WAVE;
	float off = LENGTH * sway * reach * sin(w);
	float slope = sway * (reach_slope * sin(w) - reach * TAU / WAVE * cos(w));
	vec3 along = normalize(vec3(slope, 0.0, 1.0));
	vec3 across = vec3(along.z, 0.0, -along.x);
	v = vec3(off, v.y, v.z) + across * v.x;
	n = across * n.x + vec3(0.0, n.y, 0.0) + along * n.z;
	curl_bend(v, n);
	VERTEX = v;
	NORMAL = normalize(n);
}


// The species' colour of the body's skin at a place: `s` along, `h` up (0 belly line, 1 back
// line), `p` (along, round from the back line: body lengths, + its right side).
// One row of pale rectangles along the back: `row` its height (0..1 up the side), `tall` half its
// height, `offset` how far along it starts (of a pitch).
float calico(float s, float h, float row, float tall, float offset, float seed) {
	float pitch = 0.062;
	float k = floor((s - GILL_S) / pitch - offset);
	vec4 r = hash4(vec2(k, seed));
	float centre = GILL_S + (k + offset + 0.5 + (r.x - 0.5) * 0.25) * pitch;
	vec2 d = abs(vec2((s - centre) / (pitch * (0.36 + 0.08 * r.y)), (h - row - (r.z - 0.5) * 0.04) / tall));
	float wobble = 0.18 * (cloud(vec2(s * 90.0, h * 20.0) + seed) - 0.5);
	return 1.0 - smoothstep(0.7, 1.0, pow(pow(d.x, 4.0) + pow(d.y, 4.0), 0.25) + wobble);
}


vec3 skin(float s, float h, vec2 p) {
	vec3 c = mix(belly, side, smoothstep(0.08, 0.36, h));
	c = mix(c, back, smoothstep(0.5, 0.82, h));
	if (blotch_amount > 0.0) {
		float along = smoothstep(GILL_S - 0.02, GILL_S + 0.02, s) * (1.0 - smoothstep(0.8, 0.85, s));
		float b = max(calico(s, h, 0.83, 0.08, 0.0, 1.0), calico(s, h, 0.64, 0.085, 0.5, 2.0));
		c = mix(c, pale, blotch_amount * along * b);
		// (fainter patches lower on the side)
		float low = calico(s, h, 0.45, 0.07, 0.0, 3.0) * smoothstep(0.25, 0.4, h);
		c = mix(c, pale, 0.4 * blotch_amount * along * low);
		// (the head: a little paler mottling)
		c = mix(c, pale, 0.25 * blotch_amount * (1.0 - smoothstep(GILL_S - 0.02, GILL_S, s)) * smoothstep(0.6, 0.8, cloud(p / 0.018)) * smoothstep(0.3, 0.5, h));
	}
	c *= 1.0 + mottle * (0.18 * cloud(p / 0.015) - 0.09);
	return c;
}


// The cartoon eye at a place on its face `e` (x up, y towards the nose; its rim at about 0.6):
// the white, the iris and pupil slid by `eye_look`, a highlight that stays put, a dark outline;
// outside that (where the bigger eye stands out of a curving head) the skin's colour `around`.
vec3 cartoon_eye(vec2 e, vec3 around) {
	float r = length(e);
	float aa = max(fwidth(r), 0.004);
	vec2 look = clamp(eye_look, vec2(-1.0), vec2(1.0)).yx * vec2(0.15, 0.17);
	vec2 q = e - look;
	float ri = length(q);
	vec3 c = SCLERA * mix(1.0, 0.82, smoothstep(0.25, 0.56, r));
	vec3 ir = mix(iris * 1.15, iris * 0.55, smoothstep(0.1, IRIS_R, ri));
	ir *= 1.0 + 0.12 * sin(atan(q.x, q.y) * 14.0) * smoothstep(PUPIL_R, IRIS_R, ri);
	c = mix(c, ir, 1.0 - smoothstep(IRIS_R - aa, IRIS_R + aa, ri));
	c = mix(c, iris * 0.25, smoothstep(IRIS_R - 0.05, IRIS_R, ri) * (1.0 - smoothstep(IRIS_R, IRIS_R + aa, ri)));
	// (the pupil, drawn out forward into a keyhole where KEYHOLE is more than 0)
	float pupil = ri - PUPIL_R;
	if (KEYHOLE > 0.0) {
		pupil = min(pupil, length((q - vec2(-0.02, PUPIL_R * 0.9)) * vec2(1.0, 0.8)) - KEYHOLE);
	}
	c = mix(c, vec3(0.01), 1.0 - smoothstep(-aa, aa, pupil));
	// (the highlight, up and forward, where the light is: it does not follow the look)
	float glint = length(e - vec2(0.2, 0.13));
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.075 - aa, 0.075 + aa, glint));
	c = mix(c, vec3(0.9), 1.0 - smoothstep(0.03 - aa, 0.03 + aa, length(e - vec2(0.05, 0.25))));
	// (the outline)
	c = mix(c, vec3(0.02, 0.02, 0.015), smoothstep(0.54 - aa, 0.565 + aa, r));
	return mix(c, around, smoothstep(0.6 - aa, 0.62 + aa, r));
}


vec3 fin_colour(float which, float r, float ty) {
	if (which > 7.5) {
		// the pelvic and pectoral fins: yellowish, clear towards the edge
		return mix(fin_paired, fin_paired * 1.1, smoothstep(0.3, 1.0, r));
	}
	if (which > 6.5 && which < 7.5) {
		// the anal fin: yellowish
		return mix(belly * 0.85, fin_paired * 0.9, smoothstep(0.1, 0.4, r));
	}
	if (which > 5.5 && which < 6.5) {
		// the tail: olive at its root, yellowish olive out to a darker edge
		return mix(mix(side, fin_tail, smoothstep(0.05, 0.35, r)), fin_dark, smoothstep(0.8, 1.0, r));
	}
	// the dorsal fins: olive, the spines' membrane yellowish towards the edge
	return mix(back, mix(fin_tail, fin_paired, 0.4), smoothstep(0.2, 0.8, r));
}


void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

