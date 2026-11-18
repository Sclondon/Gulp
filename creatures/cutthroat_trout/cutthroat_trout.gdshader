shader_type spatial;
// The cutthroat trout (cutthroat_trout.gd): it swims by a wave down its body, its jaw and gill
// covers work, its fins wave and scull; and every marking is drawn here, from the species (the
// component's README describes the references): no texture files. What each point is comes from
// the model (tools/build_cutthroat_trout.py): COLOR.r the part, as a tenth (0 body, 1 lower jaw,
// 2 eye, 3 maxilla, 4 dorsal, 5 adipose, 6 tail, 7 anal, 8 pelvic, 9 pectoral). On the body UV.x is how far
// along the fish (0 snout to 1 tail tip), UV.y how high (0 belly line to 1 back line), UV2.x how
// far round the skin from the back line (metres, + right, - left), UV2.y the whole way from back
// line to belly line; COLOR.g the gill cover's moving edge, COLOR.b the inside of the mouth. On a
// fin UV.x is along its rays (0 root to 1 edge), UV.y across it counted in rays; UV2 and COLOR.b
// the way its flat side faces. Nothing here needs more than GL Compatibility has.
//
// Everything that moves runs on `phase` (0..1 through one beat, set by CutthroatTrout): the tail
// beats, the breaths and the fins' sculls each go a whole number of times a beat, so a picture of
// it comes round again exactly.
render_mode cull_back, depth_draw_opaque;

// Kept in step with the model and the script.
const float LENGTH = 0.4;
const float HINGE_S = 0.112;
const float HINGE_Y = -0.031;
// How many body lengths one wave of the swimming bend is.
const float WAVE = 0.95;

// How far through a beat it is (0..1), and how many times in a beat its tail beats, it breathes
// and its pectoral fins scull (whole numbers).
uniform float phase = 0.0;
// Turning (the user, 2026-11-17, of fish swimming tight rounds: "The fish need to bend more"):
// how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns left). The
// head stays as it is; set it from how tightly the fish is turning.
uniform float curl = 0.0;
uniform float tail_beats = 3.0;
uniform float breaths = 2.0;
uniform float sculls = 2.0;
// How hard it is swimming: how far its tail swings (1 is a tenth of its length each way).
uniform float swim = 0.5;
// The mouth: how far open it is held (radians) and how much further each breath opens it. The
// gill covers: how far their edges lift with each breath (metres).
uniform float gape = 0.05;
uniform float gape_breath = 0.09;
uniform float gill_flare = 0.003;
// How far the pectoral fins scull (1 as it holds its place).
uniform float scull = 1.0;

// The colours (the greenback's by default; CutthroatTrout.look sets them all).
uniform vec3 back : source_color = vec3(0.1, 0.17, 0.09);
uniform vec3 side : source_color = vec3(0.52, 0.55, 0.2);
uniform vec3 flush : source_color = vec3(0.9, 0.27, 0.1);
uniform vec3 belly : source_color = vec3(0.95, 0.5, 0.28);
uniform vec3 band : source_color = vec3(0.86, 0.42, 0.36);
uniform vec3 gill : source_color = vec3(0.84, 0.3, 0.3);
uniform vec3 jaw_pale : source_color = vec3(0.86, 0.78, 0.6);
uniform vec3 slash : source_color = vec3(0.92, 0.12, 0.05);
uniform vec3 mouth : source_color = vec3(0.86, 0.68, 0.66);
uniform vec3 spot : source_color = vec3(0.02, 0.02, 0.02);
uniform vec3 parr : source_color = vec3(0.3, 0.4, 0.48);
uniform vec3 fin_low : source_color = vec3(0.93, 0.36, 0.14);
uniform vec3 fin_edge : source_color = vec3(1.0, 0.93, 0.82);
uniform vec3 fin_top : source_color = vec3(0.58, 0.52, 0.2);
uniform vec3 fin_tail : source_color = vec3(0.42, 0.5, 0.24);
uniform vec3 eye_gold : source_color = vec3(0.85, 0.66, 0.25);
uniform vec3 sheen_colour : source_color = vec3(0.8, 0.7, 0.9);
// How strong the flush of the lower side, the rosy band along the lateral line, the parr marks
// and the sheen are.
uniform float flush_amount = 1.0;
uniform float band_amount = 0.3;
uniform float parr_amount = 0.22;
uniform float sheen = 0.35;
// The spots: how far apart they are laid (metres), how big for 1, how many of them there are at
// the head end for 1 at the tail, and how far down the side they reach at the head end (0 the
// back line, 0.5 the lateral line, 1 the belly line).
uniform float spot_cell = 0.0092;
uniform float spot_size = 1.0;
uniform float spot_fore = 0.4;
uniform float spot_low = 0.5;

// Cartoon eyes (added 2026-11-18; the user: "the eyes for most of them should be more cartoony and
// personalized"). 0, the default, is the eye drawn below, as it always was; 1 is the cartoon eye:
// grown about the middle of its face, a pale white, a coloured iris, a big dark pupil, a highlight
// that stays put (up and forward, towards the light) and a dark rim, under an upper lid.
uniform float cartoon_eyes = 0.0;
// Where the pupil looks, in the eye's own plane: x forward (towards the snout; -1 back towards the
// tail), y up; -1..1. Only the cartoon eye's pupil moves.
uniform vec2 eye_look = vec2(0.0);
// 0 open, 1 shut: the eye squashes flat from above and below and a lid of `lid_colour` closes over it.
uniform float blink = 0.0;
// The right eye's middle on the skin and the way it faces (metres, as the model is built: the build
// script prints them; the left eye is its mirror).
uniform vec3 eye_at = vec3(0.01514, 0.012, -0.172);
uniform vec3 eye_out = vec3(0.9063, 0.3634, -0.2157);
// The trout's own cartoon eye (the README says what character it has): how much bigger it is
// drawn, its white, its iris (how wide, of the eye's face to its rim), its pupil (how wide, of the
// iris; 0 round, 1 an upright slit, 2 a level bar, 3 a keyhole), where the upper lid's edge rests
// (1 the top of the eye, no lid; 0 its middle) and how much lower it comes at the front (a frown).
uniform float eye_grow = 1.6;
// (how fast the head's skin falls away round the eye: 1 / (2 x its radius there), per metre)
// (eye_sink: 0, not sunk, looked cleanest on all of them: sunk, the rim dipped under the skin and came
// out again below the eye as a dark crescent)
uniform float eye_sink = 0.0;
uniform vec3 eye_white : source_color = vec3(0.97, 0.95, 0.86);
uniform vec3 iris : source_color = vec3(0.98, 0.72, 0.2);
uniform float iris_size = 0.62;
uniform float pupil_size = 0.56;
uniform int pupil_shape = 0;
uniform float lid = 0.6;
uniform float lid_slant = 0.14;
uniform vec3 lid_colour : source_color = vec3(0.26, 0.32, 0.13);

varying vec3 rest;
varying float part;
varying vec2 extra;


float gill_edge(float h) {
	return 0.218 - 0.25 * (h - 0.45) * (h - 0.45);
}


vec4 hash4(vec2 p) {
	vec4 q = fract(p.xyxy * vec4(0.1031, 0.1030, 0.0973, 0.1099));
	q += dot(q, q.wzxy + 33.33);
	return fract((q.xxyz + q.yzzw) * q.zywx);
}


// Soft patches, 0..1, a patch to each 1 of `p`: the skin is not one flat colour.
float cloud(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash4(i).x, hash4(i + vec2(1.0, 0.0)).x, f.x), mix(hash4(i + vec2(0.0, 1.0)).x, hash4(i + vec2(1.0, 1.0)).x, f.x), f.y);
}


// How many spots there are at a place on the body (0..1): `s` along it, `a` round it from the
// back line (0) to the belly line (1). Few and high at the head end, crowded and all the way
// down at the wrist of the tail.
float spot_share(float s, float a) {
	float along = mix(spot_fore, 1.0, smoothstep(0.34, 0.8, s));
	float reach = mix(spot_low, 0.94, smoothstep(0.52, 0.82, s));
	float down = 1.0 - smoothstep(reach - 0.14, reach, a);
	// (the head has a few on top only)
	float head = mix(0.5 * (1.0 - smoothstep(0.12, 0.25, a)), 1.0, smoothstep(0.17, 0.24, s));
	// (none where the skin runs out over the root of the tail: the tail has its own)
	return along * down * head * (1.0 - smoothstep(0.872, 0.895, s));
}


// Round spots scattered over a skin: `p` is the place on it (metres), `share` of the places
// that may have one do, each `grown` times its size (less than 1 shrinks them away, as towards a
// fin's edge). `on_body` works the share out for each spot from where its middle is.
float spots(vec2 p, float cell, float share, float grown, bool on_body, float girth) {
	vec2 id = floor(p / cell);
	float found = 0.0;
	float soft = max(fwidth(p.x) + fwidth(p.y), 1e-5) * 0.7;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 c = id + vec2(float(i), float(j));
			vec4 r = hash4(c);
			vec2 middle = (c + 0.5 + (r.xy - 0.5) * 0.72) * cell;
			float there = share;
			float size = cell * (0.2 + 0.15 * r.w) * spot_size * grown;
			if (on_body) {
				float s = middle.x / LENGTH + 0.5;
				there = spot_share(s, abs(middle.y) / girth);
				size *= mix(0.8, 1.0, smoothstep(0.3, 0.8, s));
			}
			// (not quite round: each a little longer one way)
			vec2 d = p - middle;
			float lean = r.z * 6.283;
			d = vec2(d.x * cos(lean) + d.y * sin(lean), (d.y * cos(lean) - d.x * sin(lean)) * 1.18);
			found = max(found, step(fract(r.z * 7.31 + r.w), there) * (1.0 - smoothstep(size - soft, size + soft, length(d))));
		}
	}
	return found;
}


// The cartoon eye's dome grown about the middle of its face, and squashed from above and below as
// it blinks (nothing moves while cartoon_eyes and blink are 0).
void eye_shape(inout vec3 v, float side_is) {
	if (cartoon_eyes <= 0.0 && blink <= 0.0) {
		return;
	}
	vec3 at = vec3(eye_at.x * side_is, eye_at.yz);
	vec3 o = normalize(vec3(eye_out.x * side_is, eye_out.yz));
	vec3 up = normalize(vec3(0.0, 1.0, 0.0) - o * o.y);
	vec3 d = v - at;
	float grow = mix(1.0, eye_grow, cartoon_eyes);
	float before = dot(d - o * dot(d, o), d - o * dot(d, o));
	// (grown across, and outward; what lies behind its face, deep in the head, is not pushed further in,
	// or it would come out through the other side of a narrow head)
	float deep = min(dot(d, o), 0.0);
	d = (d - o * deep) * grow + o * deep;
	// (sunk as the head's skin falls away round it, so that the grown rim stays in the skin)
	d -= o * eye_sink * before * (grow * grow - 1.0);
	d -= up * dot(d, up) * 0.8 * blink;
	v = at + d;
}


// The cartoon eye's colour at a place on its face: `e` x up, y forward, 1 at its rim.
vec3 cartoon_eye(vec2 e) {
	float r = length(e);
	vec2 q = e - vec2(eye_look.y, eye_look.x) * (0.9 - iris_size);
	float ri = length(q) / iris_size;
	float aa = fwidth(ri) + 0.01;
	vec3 c = eye_white * mix(1.0, 0.82, smoothstep(0.4, 1.0, r));
	vec3 ring = mix(iris * 1.2, iris * 0.6, smoothstep(0.25, 0.95, ri));
	ring = mix(ring, iris * 0.25, smoothstep(0.82, 1.0, ri));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ri));
	vec2 p = q / (iris_size * pupil_size);
	float pd = length(p);
	if (pupil_shape == 1) {
		pd = length(vec2(p.x * 0.6, p.y * 2.4));
	} else if (pupil_shape == 2) {
		pd = length(vec2(p.x * 2.4, p.y * 0.6));
	} else if (pupil_shape == 3) {
		pd = min(length(p - vec2(0.22, 0.0)) * 1.15, length(vec2((p.x + 0.35) * 0.75, p.y * 2.8)));
	}
	float pa = fwidth(pd) + 0.02;
	c = mix(c, vec3(0.015), 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	float shine = 1.0 - smoothstep(0.17, 0.21, length(e - vec2(0.36, 0.3)));
	shine = max(shine, 0.85 * (1.0 - smoothstep(0.07, 0.1, length(e - vec2(-0.22, -0.3)))));
	c = mix(c, vec3(1.0), shine);
	return mix(c, vec3(0.02), smoothstep(0.83, 0.9, r));
}


// The body behind the head laid round an arc (see `curl`).
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
	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float s = v.z / LENGTH + 0.5;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float breath = phase * TAU * breaths;
	float tail = phase * TAU * tail_beats;
	float wave = tail - TAU * clamp(s, 0.0, 1.05) / WAVE;
	if (part == 2.0) {
		eye_shape(v, side_is);
	}
	if (part == 1.0) {
		// The lower jaw swings about its hinge under the eye; the throat behind it stays.
		float a = (gape + gape_breath * (0.5 - 0.5 * cos(breath))) * smoothstep(0.137, 0.09, s);
		vec2 hinge = vec2(HINGE_Y, HINGE_S - 0.5) * LENGTH;
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	} else if (part == 0.0) {
		// The gill covers lift at their rear edges, a little after the mouth opens.
		v.x += side_is * COLOR.g * gill_flare * (0.5 - 0.5 * cos(breath - 1.3));
	} else if (part >= 4.0) {
		// A fin waves the way its flat side faces, more towards its edge.
		vec3 flat_way = normalize(vec3(UV2.x, UV2.y, COLOR.b * 2.0 - 1.0));
		float r = UV.x;
		float turn = phase * TAU * sculls;
		if (part == 9.0) {
			// the pectorals scull, one a little after the other, the stroke running out to the edge
			float a = turn + (side_is > 0.0 ? 0.0 : 1.3);
			// (more out from the body than in towards it: tools/build_cutthroat_trout.py measures the gap left)
			v += flat_way * LENGTH * 0.03 * scull * (r * (sin(a) + 0.35) + 0.7 * r * r * sin(a - 1.2));
		} else if (part == 8.0) {
			float a = turn + (side_is > 0.0 ? 2.2 : 3.3);
			v += flat_way * LENGTH * 0.012 * scull * r * r * sin(a - UV.y * 0.25);
		} else if (part == 6.0) {
			// (the tail's edge lags behind the bend that carries it)
			v.x += LENGTH * 0.022 * swim * r * r * sin(wave - 1.1);
		} else {
			v.x += LENGTH * 0.014 * swim * r * r * sin(wave - 1.0 - UV.y * 0.2);
		}
	}
	// The swimming bend: a wave that runs from head to tail, the head nearly still and the tail
	// swinging widest. Each place is carried sideways and turned to lie along the bent body, so
	// that the fins and the tail follow it.
	float sb = clamp(v.z / LENGTH + 0.5, 0.0, 1.05);
	float reach = 0.012 - 0.05 * sb + 0.14 * sb * sb;
	float reach_slope = -0.05 + 0.28 * sb;
	float w = tail - TAU * sb / WAVE;
	float off = LENGTH * swim * reach * sin(w);
	float slope = swim * (reach_slope * sin(w) - reach * TAU / WAVE * cos(w));
	vec3 along = normalize(vec3(slope, 0.0, 1.0));
	vec3 across = vec3(along.z, 0.0, -along.x);
	v = vec3(off, v.y, v.z) + across * v.x;
	n = across * n.x + vec3(0.0, n.y, 0.0) + along * n.z;
	VERTEX = v;
	NORMAL = normalize(n);
	vec3 curled = VERTEX;
	vec3 curled_normal = NORMAL;
	curl_bend(curled, curled_normal);
	VERTEX = curled;
	NORMAL = curled_normal;
}


// The colour of the body's skin at a place, before its spots: `s` along, `h` up.
vec3 skin(float s, float h) {
	// (the flush of the lower side is strongest at the middle of the body, and fades to the tail)
	float flushed = flush_amount * smoothstep(0.16, 0.3, s) * (1.0 - 0.75 * smoothstep(0.62, 0.86, s));
	vec3 low = mix(side, flush, flushed);
	vec3 under = mix(mix(side, vec3(1.0), 0.45), belly, clamp(flushed + 0.25, 0.0, 1.0));
	vec3 c = mix(under, low, smoothstep(0.02, 0.14, h));
	c = mix(c, side, smoothstep(0.24, 0.5, h));
	c = mix(c, back, smoothstep(0.6, 0.9, h));
	return c;
}


void fragment() {
	vec3 c = side;
	float rough = 0.36;
	float glint = sheen;
	float seen = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	if (part < 0.5) {
		float s = UV.x;
		float h = UV.y;
		float girth = max(UV2.y, 0.001);
		vec2 p = vec2(rest.z, UV2.x);
		c = skin(s, h);
		// The rosy band along the lateral line, and the line itself.
		float along_body = smoothstep(0.2, 0.26, s) * (1.0 - smoothstep(0.8, 0.87, s));
		c = mix(c, band, band_amount * along_body * exp(-pow((h - 0.47) / 0.11, 2.0)));
		// The parr marks: a row of faint upright ovals along the lateral line.
		float mark = clamp(floor((s - 0.27) / 0.062 + 0.5), 0.0, 9.0);
		vec4 mr = hash4(vec2(mark, 7.0));
		vec2 md = vec2((s - 0.27 - mark * 0.062 - (mr.x - 0.5) * 0.012) / (0.0165 + 0.004 * mr.y), (h - 0.49 - (mr.z - 0.5) * 0.05) / 0.19);
		c = mix(c, parr, parr_amount * (1.0 - smoothstep(0.15, 1.0, dot(md, md))));
		c *= 1.0 - 0.14 * along_body * (1.0 - smoothstep(0.004, 0.009, abs(h - 0.5)));
		// The head: dark on top, the cheek and gill cover rosy, pale underneath; the gill
		// cover's edge a dark crescent; the cut, red, under the gill covers.
		float edge = gill_edge(h);
		float cheek = smoothstep(0.085, 0.125, s) * (1.0 - smoothstep(edge - 0.006, edge + 0.001, s)) * smoothstep(0.1, 0.24, h) * (1.0 - smoothstep(0.58, 0.8, h));
		// (rosiest low and towards its rear edge, the skin's own colour showing through above)
		c = mix(c, gill, cheek * mix(0.5, 0.92, smoothstep(0.7, 0.3, h) * smoothstep(0.1, 0.17, s)));
		// (the line of the cheek plate ahead of the gill cover)
		c *= 1.0 - 0.22 * exp(-pow((s - edge + 0.052 + 0.03 * (h - 0.45)) / 0.0028, 2.0)) * smoothstep(0.14, 0.24, h) * (1.0 - smoothstep(0.55, 0.68, h));
		float head = 1.0 - smoothstep(0.15, 0.22, s);
		c = mix(c, mix(jaw_pale, side, 0.35), head * (1.0 - smoothstep(0.1, 0.3, h)) * (1.0 - cheek));
		c = mix(c, back, head * smoothstep(0.55, 0.8, h) * 0.6);
		c *= 1.0 - 0.5 * exp(-pow((s - edge - 0.0025) / 0.003, 2.0)) * smoothstep(0.08, 0.2, h) * (1.0 - smoothstep(0.76, 0.9, h));
		c = mix(c, slash, 0.9 * smoothstep(0.115, 0.14, s) * (1.0 - smoothstep(0.195, 0.225, s)) * (1.0 - smoothstep(0.07, 0.15, h)) * smoothstep(0.0, 0.035, h));
		// The scales: fine, in rows, seen only close.
		vec2 sc = p / 0.0024;
		sc.x += 0.5 * mod(floor(sc.y), 2.0);
		// (each a crescent: the free rear edge of a scale)
		vec2 in_scale = fract(sc) - 0.5;
		float scale_edge = smoothstep(0.28, 0.5, length(in_scale)) * smoothstep(-0.25, 0.25, in_scale.x);
		float fine = 1.0 - smoothstep(0.25, 0.7, fwidth(sc.x) + fwidth(sc.y));
		float scaled = smoothstep(0.2, 0.24, s) * (1.0 - smoothstep(0.82, 0.95, abs(UV2.x) / girth)) * fine * (1.0 - smoothstep(0.85, 0.875, s));
		c *= 1.0 - 0.07 * scale_edge * scaled;
		rough += 0.08 * scale_edge * scaled;
		// (mottled a little, in big soft patches and small ones)
		c *= mix(1.0, 0.92 + 0.1 * cloud(p / 0.03) + 0.06 * cloud(p / 0.009 + 7.3), 1.0 - smoothstep(0.8, 0.95, abs(UV2.x) / girth));
		// The spots.
		c = mix(c, spot, 0.94 * spots(p, spot_cell, 1.0, 1.0, true, girth));
		// (where the skin runs out over the root of the tail it takes the tail's colour, as the tail does there)
		c = mix(c, fin_tail, smoothstep(0.871, 0.915, s));
		// The inside of the mouth.
		c = mix(c, mouth, extra.y);
		glint *= smoothstep(0.1, 0.3, h) * (1.0 - extra.y);
	} else if (part < 1.5) {
		// The lower jaw: pale, darker along the lip, the cut along each side of its underside.
		float s = UV.x;
		float h = UV.y;
		// (towards the throat it takes the colour the head has there)
		c = mix(jaw_pale, mix(jaw_pale, side, 0.35), smoothstep(0.09, 0.15, s));
		c = mix(c, mix(side, back, 0.55), smoothstep(0.55, 0.9, h) * 0.85);
		c = mix(c, slash, 0.92 * smoothstep(0.045, 0.09, s) * smoothstep(0.1, 0.2, h) * (1.0 - smoothstep(0.4, 0.58, h)));
		c = mix(c, mouth, extra.y);
		glint *= 0.3;
	} else if (part < 2.5) {
		// An eye: a dark pupil in a gold ring, dark at the rim.
		vec2 on_eye = UV * 2.0 - 1.0;
		float r = length(on_eye);
		// (the gold darker above, as a trout's is, and brightest next to the pupil)
		float above = smoothstep(-0.3, 0.9, on_eye.x / max(r, 0.001));
		c = mix(eye_gold, eye_gold * 0.45, 0.6 * above * smoothstep(0.4, 0.58, r));
		c = mix(c, vec3(0.04, 0.035, 0.03), smoothstep(0.6, 0.7, r));
		c = mix(c, vec3(1.0, 0.92, 0.62), 0.45 * (1.0 - smoothstep(0.38, 0.48, r)));
		c = mix(c, vec3(0.01), 1.0 - smoothstep(0.32, 0.36, r));
		if (cartoon_eyes > 0.0) {
			c = mix(c, cartoon_eye(on_eye), cartoon_eyes);
		}
		// (past its rim, where the grown dome runs back into the head and a sliver may show below it: the skin's colour, not the dark rim)
		c = mix(c, lid_colour, cartoon_eyes * smoothstep(0.95, 1.0, length(on_eye)));
		// (the upper lid: none on the eye as it was, until it blinks)
		float lid_edge = mix(mix(1.3, lid, cartoon_eyes) - lid_slant * cartoon_eyes * on_eye.y, -1.3, blink);
		c = mix(c, vec3(0.02), smoothstep(lid_edge - 0.16, lid_edge - 0.06, on_eye.x) * step(on_eye.x, 1.0) * step(lid_edge, 1.2));
		c = mix(c, lid_colour, smoothstep(lid_edge - 0.05, lid_edge, on_eye.x));
		rough = 0.06;
		glint = 0.0;
	} else if (part < 3.5) {
		// A maxilla, the plate along the upper lip: the head's colour, paler along its lower edge.
		c = mix(mix(jaw_pale, side, 0.5), mix(side, back, 0.5), smoothstep(0.3, 0.8, UV.y));
		glint *= 0.5;
	} else {
		// A fin: its rays as fine lines that fork towards the edge.
		float r = UV.x;
		float ty = UV.y;
		float between = abs(fract(ty) - 0.5) * 2.0;
		float between_fine = abs(fract(ty * 2.0) - 0.5) * 2.0;
		float lines = mix(smoothstep(0.55, 1.0, between), smoothstep(0.5, 1.0, between_fine), smoothstep(0.45, 0.7, r));
		lines *= smoothstep(0.03, 0.25, r) * (part > 5.5 && part < 6.5 ? smoothstep(0.2, 0.5, r) : 1.0);
		float marked = 0.0;
		if (part > 6.5) {
			// The lower fins: orange-red, pale along the leading edge.
			c = mix(fin_low * 0.8, fin_low, smoothstep(0.0, 0.5, r));
			c = mix(c, fin_edge, 0.9 * (1.0 - smoothstep(0.35, 1.25, ty)) * smoothstep(0.05, 0.3, r));
			c = mix(c, fin_edge, 0.25 * smoothstep(0.8, 1.0, r));
		} else if (part > 5.5) {
			// The tail: the colour of the body at its root, spotted all over.
			float t = ty / 19.0;
			c = mix(skin(0.9, 1.0 - t), fin_tail, smoothstep(0.1, 0.5, r));
			c = mix(c, fin_low, 0.35 * smoothstep(0.75, 1.0, abs(t * 2.0 - 1.0)) * smoothstep(0.2, 0.7, r));
			marked = spots(vec2(r * 0.052 / 1.5, ty * 0.0042), spot_cell * 0.78, 0.8, 1.0 - smoothstep(0.8, 0.98, r), false, 1.0);
		} else if (part > 4.5) {
			// The adipose fin: the back's colour, spotted, dark at its edge.
			c = mix(back, fin_top, 0.45);
			c = mix(c, back * 0.5, smoothstep(0.72, 0.98, r));
			marked = spots(vec2(r * 0.014, ty * 0.012), spot_cell * 0.6, 0.7, 1.0 - smoothstep(0.55, 0.85, r), false, 1.0);
			lines = 0.0;
		} else {
			// The dorsal fin: spotted.
			c = mix(mix(back, fin_top, 0.5), fin_top, smoothstep(0.0, 0.35, r));
			c = mix(c, fin_edge, 0.5 * (1.0 - smoothstep(0.3, 1.0, ty)) * smoothstep(0.55, 0.95, r));
			marked = spots(vec2(r * 0.044 / 1.3, ty * 0.0043), spot_cell * 0.78, 0.8, 1.0 - smoothstep(0.78, 0.98, r), false, 1.0);
		}
		c *= 1.0 - 0.22 * lines;
		c = mix(c, spot, 0.92 * marked);
		rough = 0.45;
		glint *= 0.4;
	}
	// The sheen: the skin's silvery, rosy shine where it is seen aslant.
	c += sheen_colour * glint * pow(1.0 - seen, 3.0);
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.5;
}
