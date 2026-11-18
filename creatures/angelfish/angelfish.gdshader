shader_type spatial;
// The angelfish (angelfish.gd), every type: it rows with its pectoral fins, steers with
// its tail (its body hardly bends), its jaw works; and every marking of every type is drawn here
// (`kind`: 0 emperor, 1 queen, 2 French): no texture files. The same swimming and the same
// layout as GameCommon's butterflyfish, whose shader this began as.
// What each point is comes from the model (tools/build_angelfish.py): COLOR.r the part, as a
// tenth (0 body, 1 lower jaw, 2 eye, 3 cheek spine, 4 dorsal, 6 tail, 7 anal, 8 pelvic,
// 9 pectoral). On the body and jaw UV.x is how far along the fish (0 snout to 1 tail tip), UV.y
// how high (0 belly line to 1 back line), COLOR.b the inside of the mouth. On a fin UV.x is along
// its rays (0 root to 1 edge), UV.y across it counted in rays; UV2 and COLOR.b the way its flat
// side faces. The markings are drawn from where a point is in the fish's side view, as it is
// built (`rest`): how far along (0..1) and how high (body lengths from its middle line), so they
// run across body and fins alike. Nothing here needs more than GL Compatibility has.
//
// Everything that moves runs on `phase` (0..1 through one beat, set by Angelfish): the tail
// beats and the fins' strokes each go a whole number of times a beat, so it comes round exactly.
render_mode cull_back, depth_draw_opaque;

// As the models are built: every type is this long.
const float LENGTH = 0.35;
// How many body lengths one wave of the swimming bend is (long: the body is stiff).
const float WAVE = 1.8;
// How far the lower jaw swings down when `gape` is 1 (radians), and how far the upper snout lifts.
const float GAPE_ANGLE = 0.8;
const float GAPE_LIFT = 0.16;

// Which type's markings (Angelfish.Type), and the places on that type's model the shader
// needs (Angelfish.TYPES has them: the build script prints them): where the lower jaw hinges
// (how far along, how high, body lengths), where its eye is, and the middle of its right pectoral
// fin's root (x out, y up, how far along; body lengths).
uniform int kind = 0;
uniform float hinge_s = 0.036;
uniform float hinge_y = -0.033;
uniform vec2 eye_at = vec2(0.115, 0.058);
uniform vec3 pec_root = vec3(0.0705, -0.0675, 0.265);

// How far through a beat it is (0..1), and how many times in a beat its tail beats and its
// pectoral fins row (whole numbers).
uniform float phase = 0.0;
uniform float tail_beats = 2.0;
uniform float strokes = 3.0;
// How widely its tail swings (1: a tenth of its length each way), and how hard its pectoral fins
// row (1 as it hovers and paddles about; 0 held still).
uniform float sway = 0.3;
uniform float row = 1.0;
// The mouth: 0 shut, 1 wide open (the lower jaw swings down about its hinge, the snout lifts a
// little).
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// The same up and down: how far the whole body is bent about its middle, radians from snout to
// tail tip (more than 0 its head and its tail both come up).
uniform float arch = 0.0;
// For a game: `flash` adds white light to the whole fish (a hit); `rim` lights its edges with
// its own colour so that it stands out (0 none); `tint` multiplies its colours.
uniform float flash = 0.0;
uniform float rim = 0.0;
uniform vec3 tint : source_color = vec3(1.0);
// The inside of the mouth; how strong the skin's sheen is; how clearly the fins' rays show.
uniform vec3 mouth : source_color = vec3(0.16, 0.05, 0.06);
uniform float sheen = 0.2;
uniform float ray_lines = 1.0;

// The cartoon eye: 0 the eye as it is built, 1 bigger, a white with a coloured iris, a big pupil,
// a highlight that stays put, a dark outline and lids. `eye_look`: where both eyes look (-1..1: x
// towards the nose, y up). `blink`: 0 open, 1 shut (the lids meet and the eye squashes).
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
// Each type's cartoon eye (Angelfish.TYPES): where the eye sits on the skin (x out, y up, how
// far along; body lengths), how much bigger than life, the iris's colour and width (of the eye),
// the pupil's width (of the iris) and shape (0 round, 1 a bar across, 2 an upright slit, 3 a
// keyhole), where the upper lid rests (eye radii up from the middle; 1 or more: none shows) and
// how it slants (more than 0: higher at the nose), and where the lower lid rests.
uniform vec3 eye_skin = vec3(0.0393, 0.04, 0.132);
uniform float eye_size = 1.7;
uniform vec3 iris : source_color = vec3(0.95, 0.6, 0.12);
uniform float iris_size = 0.6;
uniform float pupil_size = 0.6;
uniform int pupil_shape = 0;
uniform float lid = 0.8;
uniform float lid_tilt = 0.0;
uniform float lower_lid = -1.2;

// The throat (added 2026-11-18): a short tunnel back from the jaw's hinge, four gill arches a side in it
// (part 10). Its ovals, THROAT_KNOTS of them: (how far along, the height of its middle, half height, half
// width; body lengths), as the model is built (Angelfish.TYPES "throat"). While the mouth is open, what
// of the body and the jaw lies inside it (the dark wall at the back of the mouth) is cut away, so that the
// throat shows. `gill_red`: the gills' colour.
const int THROAT_KNOTS = 5;
uniform vec4 throat[5];
uniform vec3 gill_red : source_color = vec3(0.66, 0.06, 0.08);

varying vec3 rest;
varying float part;
varying float inside;
varying float lining;


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


// The whole body laid round an arc that goes up and down, about its middle (see `arch`).
void arch_bend(inout vec3 v, inout vec3 n) {
	if (abs(arch) < 0.001) {
		return;
	}
	float k = arch / LENGTH;
	float a = v.z * k;
	float r = 1.0 / k;
	float c = cos(a);
	float sn = sin(a);
	n = vec3(n.x, n.y * c + n.z * sn, n.z * c - n.y * sn);
	v = vec3(v.x, r - (r - v.y) * c, (r - v.y) * sn);
}


void vertex() {
	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	inside = part < 1.5 ? COLOR.b : 0.0;
	lining = part < 0.5 ? COLOR.g : 0.0;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float s = v.z / LENGTH + 0.5;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float tail = phase * TAU * tail_beats;
	float stroke = phase * TAU * strokes;
	float wave = tail - TAU * clamp(s, 0.0, 1.05) / WAVE;
	if (part == 2.0 && cartoon_eyes > 0.0) {
		// The cartoon eye: grown about where it sits on the skin, and squashed as it blinks.
		vec3 at = vec3(eye_skin.x * side_is, eye_skin.y, eye_skin.z - 0.5) * LENGTH;
		vec3 d = v - at;
		d.y *= 1.0 - 0.45 * blink * cartoon_eyes;
		v = at + d * mix(1.0, eye_size, cartoon_eyes);
	} else if (part == 1.0 || part == 0.0) {
		// The lower jaw swings down about its hinge (the throat behind it stays); the upper snout
		// lifts a little. (The throat's lining goes with the jaw below the hinge's height and with the
		// snout above it: its front is the inside of the mouth.)
		bool with_jaw = part == 1.0 || (COLOR.g > 0.5 && VERTEX.y < hinge_y * LENGTH);
		float a = with_jaw
			? gape * GAPE_ANGLE * smoothstep(hinge_s + 0.02, hinge_s - 0.008, s)
			: -gape * GAPE_LIFT * smoothstep(hinge_s + 0.04, hinge_s - 0.01, s);
		vec2 hinge = vec2(hinge_y, hinge_s - 0.5) * LENGTH;
		vec2 d = v.yz - hinge;
		v.yz = hinge + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	} else if (part > 9.5) {
		// The gill arches spread a little as the mouth opens.
		v.z += gape * LENGTH * 0.005 * (floor(UV.y) - 1.5);
	} else if (part >= 4.0) {
		// A fin waves the way its flat side faces, more towards its edge.
		vec3 flat_way = normalize(vec3(UV2.x, UV2.y, COLOR.b * 2.0 - 1.0));
		float r = UV.x;
		if (part == 9.0) {
			// The pectoral fins row: each turns out from the body and back about the upright line
			// through its root, the left a little after the right, its edge trailing the stroke.
			float a = stroke + (side_is > 0.0 ? 0.0 : 0.9);
			float turn = side_is * row * (0.38 * sin(a) + 0.1);
			vec3 root = vec3(pec_root.x * side_is, pec_root.y, pec_root.z - 0.5) * LENGTH;
			float c = cos(turn);
			float sn = sin(turn);
			vec3 d = v - root;
			v = root + vec3(d.x * c + d.z * sn, d.y, d.z * c - d.x * sn);
			n = vec3(n.x * c + n.z * sn, n.y, n.z * c - n.x * sn);
			flat_way = vec3(flat_way.x * c + flat_way.z * sn, flat_way.y, flat_way.z * c - flat_way.x * sn);
			v += flat_way * LENGTH * 0.022 * row * r * r * sin(a - 1.3);
		} else if (part == 8.0) {
			float a = stroke + (side_is > 0.0 ? 2.2 : 3.3);
			v += flat_way * LENGTH * 0.012 * row * r * r * sin(a - UV.y * 0.3);
		} else if (part == 6.0) {
			// (the tail's edge lags behind the bend that carries it)
			v.x += LENGTH * 0.03 * sway * r * r * sin(wave - 1.1);
		} else if (part == 5.0) {
			// (the filament or banner streams)
			v.x += LENGTH * 0.05 * (0.25 + sway) * r * r * sin(tail - r * 2.6);
		} else {
			// (the soft rear of the dorsal and anal fins ripples)
			v.x += LENGTH * 0.012 * (0.4 + 0.6 * row) * r * r * smoothstep(0.45, 0.7, s) * sin(stroke - s * 13.0);
		}
	}
	// The swimming bend: little of it, behind the middle; the tail steers. Each place is carried
	// sideways and turned to lie along the bent body, so that the fins and the tail follow it.
	float sb = clamp(v.z / LENGTH + 0.5, 0.0, 1.05);
	float behind = max(sb - 0.3, 0.0);
	float reach = 0.204 * behind * behind;
	float reach_slope = 0.408 * behind;
	float w = tail - TAU * sb / WAVE;
	float off = LENGTH * sway * reach * sin(w);
	float slope = sway * (reach_slope * sin(w) - reach * TAU / WAVE * cos(w));
	vec3 along = normalize(vec3(slope, 0.0, 1.0));
	vec3 across = vec3(along.z, 0.0, -along.x);
	v = vec3(off, v.y, v.z) + across * v.x;
	n = across * n.x + vec3(0.0, n.y, 0.0) + along * n.z;
	curl_bend(v, n);
	arch_bend(v, n);
	VERTEX = v;
	NORMAL = normalize(n);
}


// 1 inside a band `half` either side of 0, soft over `soft`.
float band(float x, float half, float soft) {
	return 1.0 - smoothstep(half - soft, half + soft, abs(x));
}


// Thin lines every `period` of x, each `duty` of a period wide; they fade to their mean far off.
float lines_of(float x, float period, float duty) {
	float u = x / period;
	float f = abs(fract(u) - 0.5) * 2.0;
	float fine = 1.0 - smoothstep(0.35, 0.9, fwidth(u));
	return mix(duty, 1.0 - smoothstep(duty - 0.12, duty + 0.12, f), fine);
}


// 1 inside a round spot.
float spot(vec2 q, vec2 at, float radius, float soft) {
	return 1.0 - smoothstep(radius - soft, radius + soft, length(q - at));
}


// The rear edges of scales in staggered rows, each `cell` across (body lengths): 0 on a scale, 1 on
// its edge, the edges `wide` wide; they fade to their mean far off.
float scale_rim(vec2 q, float cell, float wide) {
	vec2 sc = q / cell;
	sc.y *= 1.15;
	sc.x += 0.5 * mod(floor(sc.y), 2.0);
	vec2 f = fract(sc) - 0.5;
	float d = length(f - vec2(-0.25, 0.0));
	float edge = band(d - 0.6 + 0.5 * wide, 0.5 * wide, 0.04) * smoothstep(-0.3, 0.0, f.x);
	float fine = 1.0 - smoothstep(0.25, 0.7, (fwidth(q.x) + fwidth(q.y)) / cell);
	return mix(0.9 * wide, edge, fine);
}


// The cartoon eye at a point of the eye's dome (`uv` its UV), in skin of colour `skin`. On the
// dome, e is (towards the nose, up) in seen radii of the eye: 1 where the eye meets the skin.
vec3 cartoon_eye(vec2 uv, vec3 skin) {
	vec2 on_eye = uv * 2.0 - 1.0;
	vec2 e = vec2(on_eye.y, on_eye.x) / 0.644;
	float er = length(e);
	vec3 white = vec3(0.97, 0.96, 0.92);
	vec3 ink = vec3(0.02, 0.02, 0.025);
	// the iris and the pupil slide the way it looks
	vec2 ic = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * (0.92 - iris_size) * 0.75;
	float ir = length(ic) / iris_size;
	float aa = max(fwidth(ir), 0.02);
	vec3 c = mix(white * 0.86, white, smoothstep(1.0, 0.4, er));
	vec3 ring = mix(iris * 1.2, iris * 0.6, smoothstep(0.3, 1.0, ir));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ir));
	c = mix(c, iris * 0.3, smoothstep(0.82, 0.95, ir) * (1.0 - smoothstep(1.0 - aa, 1.0 + aa, ir)));
	vec2 pp = ic / (iris_size * pupil_size);
	float pd = length(pp);
	if (pupil_shape == 1) {
		pd = length(pp * vec2(0.55, 1.9));
	} else if (pupil_shape == 2) {
		pd = length(pp * vec2(2.6, 0.72));
	} else if (pupil_shape == 3) {
		pd = min(pd, length((pp - vec2(0.55, -0.45)) * 1.9));
	}
	float pa = max(fwidth(pd), 0.02);
	c = mix(c, ink, 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	// the highlights, where the light is (up and towards the nose), not moving as it looks
	float ea = max(fwidth(er), 0.01);
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.17 - ea, 0.17 + ea, length(e - vec2(0.24, 0.36))));
	c = mix(c, vec3(1.0), 0.8 * (1.0 - smoothstep(0.07 - ea, 0.07 + ea, length(e - vec2(-0.2, -0.3)))));
	// the lids, which give it its character; they meet as it blinks
	float shut = -0.12;
	float upper = mix(lid + lid_tilt * e.x, shut, blink);
	float lower = mix(lower_lid - 0.12 * e.x * e.x, shut + 0.03, blink);
	float la = max(fwidth(e.y), 0.01);
	float on_lid = max(smoothstep(upper - la, upper + la, e.y), 1.0 - smoothstep(lower - la, lower + la, e.y));
	float lid_edge = max(1.0 - smoothstep(0.06, 0.06 + 2.0 * la, abs(e.y - upper)),
		0.6 * (1.0 - smoothstep(0.04, 0.04 + 2.0 * la, abs(e.y - lower))));
	c = mix(c, skin * 0.92, on_lid);
	c = mix(c, ink, lid_edge * step(er, 1.0));
	// the dark outline, and the skin beyond where the eye meets it
	c = mix(c, ink, smoothstep(0.84 - ea, 0.86 + ea, er));
	c = mix(c, skin, smoothstep(1.0 - ea, 1.0 + ea, er));
	return c;
}


// Whether a point of the body or the jaw as it is built lies inside the throat (well inside its ovals).
bool in_throat(vec3 at) {
	float s = at.z / LENGTH + 0.5;
	if (s <= throat[0].x + 0.001 || s >= throat[THROAT_KNOTS - 1].x) {
		return false;
	}
	for (int i = 0; i < THROAT_KNOTS - 1; i++) {
		if (s <= throat[i + 1].x) {
			float t = (s - throat[i].x) / max(throat[i + 1].x - throat[i].x, 1e-6);
			vec3 o = mix(throat[i].yzw, throat[i + 1].yzw, t);
			vec2 e = vec2(at.x / LENGTH / o.z, (at.y / LENGTH - o.x) / o.y);
			return dot(e, e) < 0.72;
		}
	}
	return false;
}


void fragment() {
	// (the back of the mouth cut away while it is open: the throat shows)
	if (gape > 0.0 && part < 1.5 && lining < 0.5 && in_throat(rest)) {
		discard;
	}
	vec3 c = vec3(1.0);
	float rough = 0.4;
	float glint = sheen;
	float seen = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	// Where this is in the side view: how far along, how high.
	vec2 q = vec2(rest.z / LENGTH + 0.5, rest.y / LENGTH);
	float s = q.x;
	float y = q.y;
	bool is_fin = part > 3.5 && part < 9.5;
	float r = is_fin ? UV.x : 0.0;
	bool skin_part = part < 1.5;
	float h = skin_part ? UV.y : 0.5;
	vec3 black = vec3(0.025, 0.025, 0.03);
	vec3 eye_ring = vec3(0.25, 0.17, 0.06);
	// How far behind the eye's upright line this is, leaning as the face does.
	float eye_line = s - eye_at.x - 0.28 * (y - eye_at.y);
	vec3 electric = vec3(0.16, 0.52, 1.0);
	// How far behind the gill cover's rear edge this is.
	float behind_head = s - 0.25 + 0.22 * (h - 0.45) * (h - 0.45);
	if (kind == 0) {
		// EMPEROR: blue and yellow stripes running back along the body and up onto the dorsal
		// fin; a pale face with a black mask over the eyes, edged with bright blue; a black
		// patch behind the gill cover, edged with blue; a dark chest; an orange-yellow tail.
		vec3 yellow = vec3(1.0, 0.83, 0.08);
		vec3 blue = vec3(0.07, 0.2, 0.74);
		vec3 navy = vec3(0.03, 0.05, 0.17);
		vec3 face = vec3(0.8, 0.87, 0.93);
		float fan = y - (0.03 + 0.55 * max(y + 0.06, 0.0)) * (s - 0.32);
		c = mix(yellow, blue, lines_of(fan, 0.037, 0.52));
		// (the chest and belly dark)
		c = mix(c, navy, smoothstep(-0.115, -0.165, y) * (1.0 - smoothstep(0.42, 0.6, s)));
		c = mix(c, vec3(1.0, 0.7, 0.08), smoothstep(0.82, 0.86, s));
		if (part < 3.5) {
			// (the patch behind the gill cover, from the root of the pectoral fin up)
			vec2 in_patch = vec2((s - 0.31 - 0.14 * y) / 0.05, (y + 0.035) / 0.19);
			float patch_r = length(in_patch);
			c = mix(c, electric, 1.0 - smoothstep(1.06, 1.12, patch_r));
			c = mix(c, black, 1.0 - smoothstep(0.92, 1.0, patch_r));
			// (the head)
			float on_head = 1.0 - smoothstep(-0.006, 0.006, behind_head);
			vec3 hc = mix(face, vec3(0.74, 0.76, 0.22), smoothstep(0.07, 0.14, y - 0.3 * (s - 0.12)));
			float mask = eye_line + 0.004;
			float mask_is = smoothstep(-0.15, -0.11, y);
			hc = mix(hc, electric, band(mask, 0.044, 0.004) * mask_is);
			hc = mix(hc, black, band(mask, 0.035, 0.004) * mask_is);
			c = mix(c, hc, on_head);
			eye_ring = vec3(0.55, 0.3, 0.06);
		}
		if (part > 2.5 && part < 3.5) {
			c = vec3(0.7, 0.85, 1.0);
		} else if (part > 3.5 && part < 4.5) {
			c = mix(c, vec3(0.88, 0.94, 1.0), smoothstep(0.93, 0.96, r));
		} else if (part > 6.5 && part < 7.5) {
			c = mix(navy, electric, 0.8 * lines_of(r + 0.02 * UV.y, 0.15, 0.22));
			c = mix(c, electric, smoothstep(0.94, 0.97, r));
		} else if (part > 5.5 && part < 6.5) {
			c = vec3(1.0, 0.7, 0.08);
		} else if (part > 7.5 && part < 8.5) {
			c = mix(navy, blue, 0.5);
		} else if (part > 8.5) {
			c = mix(navy, vec3(0.5, 0.5, 0.3), smoothstep(0.2, 0.9, r));
		}
	} else if (kind == 1) {
		// QUEEN: blue-green, every scale edged with gold; a yellow-green face with blue about
		// the mouth and gill cover; the crown, a dark spot ringed and flecked with bright blue,
		// on its nape; a blue blotch at the root of the pectoral fin; yellow tail and pectoral
		// fins; the long fin tips orange, the fins' edges bright blue.
		vec3 teal = vec3(0.07, 0.46, 0.74);
		vec3 gold = vec3(1.0, 0.8, 0.08);
		vec3 navy = vec3(0.03, 0.08, 0.32);
		float edges = scale_rim(q, 0.026, 0.2);
		c = mix(teal, gold, 0.9 * edges);
		// (the chest and belly more golden)
		c = mix(c, gold, 0.5 * smoothstep(-0.08, -0.2, y) * (1.0 - smoothstep(0.4, 0.62, s)));
		if (part < 3.5) {
			float on_head = 1.0 - smoothstep(-0.006, 0.006, behind_head);
			vec3 hc = mix(vec3(0.8, 0.8, 0.16), vec3(0.45, 0.66, 0.3), smoothstep(0.0, 0.14, y));
			// (blue about the mouth and chin; a blue line down the gill cover's edge and under the eye)
			hc = mix(hc, vec3(0.1, 0.3, 0.85), 1.0 - smoothstep(0.03, 0.06, s - 0.2 * min(y + 0.03, 0.0)));
			hc = mix(hc, electric, band(behind_head + 0.014, 0.006, 0.003) * smoothstep(-0.16, -0.12, y) * smoothstep(0.12, 0.08, y));
			hc = mix(hc, electric, 0.8 * band(eye_line - 0.05, 0.005, 0.003) * smoothstep(0.02, -0.01, y - eye_at.y) * smoothstep(-0.13, -0.09, y));
			c = mix(c, hc, on_head);
			// (the blotch at the root of the pectoral fin)
			vec2 from_pec = q - vec2(pec_root.z + 0.004, pec_root.y);
			c = mix(c, electric, spot(from_pec * vec2(1.7, 1.0), vec2(0.0), 0.038, 0.004));
			c = mix(c, navy, spot(from_pec * vec2(1.7, 1.0), vec2(0.0), 0.03, 0.004));
			// (the crown)
			vec2 from_crown = q - vec2(0.2, 0.186);
			float away = length(from_crown);
			c = mix(c, electric, 1.0 - smoothstep(0.042, 0.047, away));
			c = mix(c, navy, 1.0 - smoothstep(0.033, 0.037, away));
			vec2 fleck = fract(from_crown / 0.017 + 0.5) - 0.5;
			c = mix(c, electric, (1.0 - smoothstep(0.16, 0.26, length(fleck))) * (1.0 - smoothstep(0.022, 0.03, away)));
			eye_ring = vec3(0.75, 0.6, 0.08);
		}
		if (part > 2.5 && part < 3.5) {
			c = vec3(0.3, 0.6, 1.0);
		} else if ((part > 3.5 && part < 4.5) || (part > 6.5 && part < 7.5)) {
			// (the long tips orange; the edges bright blue)
			c = mix(c, vec3(1.0, 0.56, 0.06), smoothstep(0.8, 0.92, s));
			c = mix(c, mix(teal, electric, 0.5), 0.6 * smoothstep(0.5, 0.9, r) * (1.0 - smoothstep(0.78, 0.9, s)));
			c = mix(c, electric, smoothstep(0.92, 0.96, r) * (1.0 - smoothstep(0.82, 0.92, s)));
		} else if (part > 5.5) {
			// (tail, pelvic and pectoral fins all yellow)
			c = gold;
		}
	} else {
		// FRENCH: black, the scales of its sides each with a yellow rear edge; a slate face with
		// a white mouth; a yellow ring round the eye; a yellow bar at the root of the pectoral
		// fin.
		vec3 dark = vec3(0.035, 0.035, 0.045);
		vec3 yellow = vec3(1.0, 0.8, 0.12);
		c = dark;
		float scaled = smoothstep(-0.02, 0.06, behind_head - 0.1 * max(-0.05 - y, 0.0)) * (1.0 - smoothstep(0.8, 0.85, s));
		if (part < 0.5) {
			c = mix(c, yellow, scale_rim(q, 0.041, 0.13) * scaled);
		} else if ((part > 3.5 && part < 4.5) || (part > 6.5 && part < 7.5)) {
			c = mix(c, yellow, scale_rim(q, 0.041, 0.13) * scaled * (1.0 - smoothstep(0.25, 0.5, r)));
			// (the leading edge of the dorsal fin's long tip yellow)
			if (part < 4.5) {
				c = mix(c, yellow, 0.9 * band(UV.y - 18.2, 0.5, 0.25) * smoothstep(0.35, 0.6, r));
			}
		}
		if (part < 3.5) {
			vec3 slate = vec3(0.2, 0.25, 0.32);
			float on_face = 1.0 - smoothstep(0.1, 0.24, s - 0.25 * y);
			c = mix(c, slate, on_face);
			c = mix(c, vec3(0.93, 0.93, 0.88), 1.0 - smoothstep(0.022, 0.042, s - 0.25 * min(y + 0.03, 0.0)));
			// (the yellow ring round the eye)
			c = mix(c, yellow, band(length(q - eye_at) - 0.031, 0.005, 0.003));
			// (the bar at the root of the pectoral fin; a yellow edge to the gill cover)
			c = mix(c, vec3(1.0, 0.7, 0.1), band(s - pec_root.z + 0.004, 0.011, 0.004) * band(y - pec_root.y, 0.034, 0.008));
			c = mix(c, yellow, 0.7 * band(behind_head + 0.004, 0.004, 0.003) * smoothstep(-0.15, -0.11, y) * smoothstep(0.1, 0.06, y));
			eye_ring = vec3(1.0, 0.78, 0.1);
		}
		if (part > 2.5 && part < 3.5) {
			c = vec3(0.6, 0.66, 0.72);
		} else if (part > 5.5 && part < 6.5) {
			c = mix(dark, vec3(0.75, 0.72, 0.5), smoothstep(0.94, 0.98, r));
		} else if (part > 8.5) {
			c = mix(vec3(1.0, 0.7, 0.1), dark, smoothstep(0.1, 0.3, r));
		}
	}
	if (part > 1.5 && part < 2.5) {
		// An eye: a dark pupil in a ring, dark at the rim; it sits in whatever its type has there.
		vec2 on_eye = UV * 2.0 - 1.0;
		float er = length(on_eye);
		vec3 around = c;
		c = mix(eye_ring, around * 0.5, smoothstep(0.52, 0.64, er));
		c = mix(c, vec3(0.85, 0.7, 0.3), 0.5 * (1.0 - smoothstep(0.36, 0.44, er)));
		c = mix(c, vec3(0.01), 1.0 - smoothstep(0.3, 0.34, er));
		if (cartoon_eyes > 0.0) {
			c = mix(c, cartoon_eye(UV, around), cartoon_eyes);
		}
		rough = 0.08;
		glint = 0.0;
	} else if (part > 9.5) {
		// A gill arch: pale rakers along its inner edge, the bar, a fringe of deep red filaments behind (fine lines
		// across it); darker than out in the light: it is deep in the throat.
		float u = UV.x;
		c = mix(gill_red, gill_red * vec3(0.55, 0.35, 0.45), smoothstep(0.4, 0.95, u));
		float strands = step(0.5, fract(UV.y * 22.0)) * (1.0 - smoothstep(0.3, 0.8, fwidth(UV.y * 22.0)));
		c *= 1.0 - 0.3 * strands * smoothstep(0.45, 0.8, u);
		c = mix(c, vec3(0.86, 0.8, 0.72), 1.0 - smoothstep(0.04, 0.1, u));
		rough = 0.35;
		glint = 0.1;
	} else if (is_fin) {
		// A fin: its rays as fine lines.
		float between = abs(fract(UV.y) - 0.5) * 2.0;
		float lines = smoothstep(0.55, 1.0, between) * smoothstep(0.03, 0.25, r);
		lines *= 1.0 - smoothstep(0.3, 0.8, fwidth(UV.y));
		c *= 1.0 - 0.16 * ray_lines * lines;
		rough = 0.5;
		glint *= 0.4;
	}
	// The inside of the mouth.
	c = mix(c, mouth * (1.0 + 0.8 * lining), inside);
	// (the throat darker the deeper it goes)
	c *= 1.0 - 0.3 * lining * smoothstep(throat[0].x, throat[THROAT_KNOTS - 1].x, s);
	glint *= 1.0 - inside;
	c *= tint;
	// The sheen: the skin's shine where it is seen aslant.
	float aslant = pow(1.0 - seen, 3.0);
	c += vec3(1.0, 0.97, 0.9) * glint * aslant;
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.4;
	EMISSION = c * (rim * 0.8 * aslant) + vec3(flash);
}
