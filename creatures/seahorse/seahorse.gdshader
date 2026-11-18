shader_type spatial;
// The seahorse (seahorse.gd), every type: it hangs upright and bobs; its dorsal fin buzzes and
// its pectoral fins flutter; its tail curls from nearly straight to a tight spiral (`grip`);
// the tip of its snout opens (`gape`). Every marking of every type is drawn here (`kind`:
// 0 common, 1 spiny, 2 pygmy): no texture files. Nothing here needs more than GL Compatibility.
//
// It stands upright, +Y up, its snout towards -Z; its origin half way up its height on the line
// of its tail (which, as built, hangs straight down the Y axis).
//
// What each point is comes from the model (tools/build_seahorse.py): COLOR.r the part, as a
// tenth (0 trunk and tail, 1 head, 2 lower jaw, 3 eye, 4 coronet, 5 spike, 6 tubercle, 7 dorsal,
// 8 pectoral). On the trunk and tail UV.x is how high (0 the tail's tip, 1 the neck's top), UV.y
// how far round from the back line (0 to 1, the right side first), UV2.x the ring it is on (a
// rim at each whole number; 0 where the tail meets the trunk). On the head and jaw UV.x is how
// far along (0 snout tip, 1 back of the head), UV.y how high, COLOR.b the inside of the mouth. On
// a fin UV.x is along its rays (0 root, 1 edge), UV.y across it counted in rays; UV2 and COLOR.b
// the way its flat side faces. On a spike or tubercle UV.x runs from its root (0) to its tip (1).
//
// Everything that moves runs on `phase` (0..1 through one beat, set by Seahorse): the fins'
// buzzes and strokes and the bobs each go a whole number of times a beat, so it comes round
// exactly.
render_mode cull_back, depth_draw_opaque;

// As the models are built: every type is this tall, and its tail's tip is this far down.
const float LENGTH = 0.15;
const float TIP_Y = -0.5;
// How far the lower jaw swings down when `gape` is 1 (radians), and how far the snout's tip lifts.
const float GAPE_ANGLE = 0.7;
const float GAPE_LIFT = 0.12;

// Which type's markings (Seahorse.Type), and the places on that type's model the shader needs
// (Seahorse.TYPES has them; the build script prints them; heights, 1 = LENGTH): where the lower
// jaw hinges (z, y), where the right eye sits on the skin, the middle of the right pectoral
// fin's root, where the dorsal fin's root runs (y, z at its bottom and top ends), and the height
// where the tail meets the trunk.
uniform int kind = 0;
uniform vec2 hinge = vec2(-0.232, 0.3785);
uniform vec3 eye_skin = vec3(0.0411, 0.404, -0.068);
uniform vec3 pec_root = vec3(0.0325, 0.338, 0.0388);
uniform vec4 dorsal_root = vec4(-0.0188, 0.0363, 0.0722, 0.0315);
uniform float tail_root = -0.06;

// How far through a beat it is (0..1); how many times in a beat its dorsal fin buzzes, its
// pectoral fins flutter and it bobs (whole numbers).
uniform float phase = 0.0;
uniform float buzzes = 12.0;
uniform float strokes = 6.0;
uniform float bobs = 1.0;
// How hard its fins work (1 as it hangs about; 0 held still); how much it bobs up and down and
// rocks (1 gently; 0 still); how much its tail sways from side to side.
uniform float row = 1.0;
uniform float bob = 1.0;
uniform float sway = 0.3;
// Its tail: 0 nearly straight (hanging down, the tip turned a little forward), 1 curled forward
// into a tight spiral, as when it holds on to something.
uniform float grip : hint_range(0.0, 1.0) = 0.0;
// The mouth at the tip of its snout: 0 shut, 1 open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;
// For a game: `flash` adds white light (a hit); `rim` lights its edges with its own colour;
// `tint` multiplies its colours.
uniform float flash = 0.0;
uniform float rim = 0.0;
uniform vec3 tint : source_color = vec3(1.0);
uniform vec3 mouth : source_color = vec3(0.16, 0.05, 0.06);
uniform float sheen = 0.18;

// The cartoon eyes: 0 the eye as it is built, 1 bigger, a white with a coloured iris, a big pupil,
// a highlight that stays put, a dark outline and lids. Its eyes swivel each on its own:
// `eye_look` is where its right eye looks, `eye_look_other` its left (-1..1: x towards the snout,
// y up). `blink`: 0 open, 1 shut. Each type's eye (Seahorse.TYPES): how much bigger than life,
// the iris's colour and width, the pupil's width, where the upper lid rests (eye radii up from
// the middle; 1 or more: none shows) and how it slants (more than 0: higher at the snout), and
// where the lower lid rests.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform vec2 eye_look_other = vec2(0.0);
uniform float blink : hint_range(0.0, 1.0) = 0.0;
uniform float eye_size = 1.7;
uniform vec3 iris : source_color = vec3(0.95, 0.62, 0.1);
uniform float iris_size = 0.6;
uniform float pupil_size = 0.58;
uniform float lid = 0.6;
uniform float lid_tilt = 0.0;
uniform float lower_lid = -1.2;

varying vec3 rest;
// (flat: interpolated, the part number can come out a hair off and fail the tests below)
varying flat float part;
varying float inside;


void vertex() {
	rest = VERTEX;
	part = floor(COLOR.r * 10.0 + 0.5);
	inside = (part > 0.5 && part < 2.5) ? COLOR.b : 0.0;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float side_is = v.x >= 0.0 ? 1.0 : -1.0;
	float buzz = phase * TAU * buzzes;
	float stroke = phase * TAU * strokes;
	float bobbing = phase * TAU * bobs;
	float z = v.z / LENGTH;
	if (part == 1.0 || part == 2.0) {
		// The lower jaw swings down about its hinge; the tip of the snout above it lifts a little.
		float a = part == 2.0
			? gape * GAPE_ANGLE * smoothstep(hinge.x + 0.012, hinge.x - 0.004, z)
			: -gape * GAPE_LIFT * smoothstep(hinge.x + 0.02, hinge.x - 0.004, z);
		vec2 at = vec2(hinge.y, hinge.x) * LENGTH;
		vec2 d = v.yz - at;
		v.yz = at + vec2(d.x * cos(a) + d.y * sin(a), d.y * cos(a) - d.x * sin(a));
		n.yz = vec2(n.y * cos(a) + n.z * sin(a), n.z * cos(a) - n.y * sin(a));
	} else if (part == 3.0 && cartoon_eyes > 0.0) {
		// The cartoon eye: grown about where it sits on the skin, squashed as it blinks.
		vec3 at = vec3(eye_skin.x * side_is, eye_skin.y, eye_skin.z) * LENGTH;
		vec3 d = v - at;
		d.y *= 1.0 - 0.45 * blink * cartoon_eyes;
		v = at + d * mix(1.0, eye_size, cartoon_eyes);
	} else if (part == 7.0) {
		// The dorsal fin buzzes from side to side, a wave running up it, most at its edge.
		float t = clamp(UV.y / 18.0, 0.0, 1.0);
		v.x += LENGTH * 0.014 * row * pow(UV.x, 1.3) * sin(buzz - t * 4.0);
	} else if (part == 8.0) {
		// The pectoral fins flutter: each turns out and back about the upright line through its
		// root, the left half a stroke after the right, and ripples.
		float a = stroke + (side_is > 0.0 ? 0.0 : PI);
		float spin = side_is * row * (0.5 * sin(a) + 0.1);
		vec3 root = vec3(pec_root.x * side_is, pec_root.y, pec_root.z) * LENGTH;
		float c = cos(spin);
		float sn = sin(spin);
		vec3 d = v - root;
		v = root + vec3(d.x * c + d.z * sn, d.y, d.z * c - d.x * sn);
		n = vec3(n.x * c + n.z * sn, n.y, n.z * c - n.x * sn);
		v.x += side_is * LENGTH * 0.006 * row * UV.x * UV.x * sin(a - 1.3);
	}
	// The tail: below its root it sways a little from side to side, and curls forward along a
	// spiral that tightens towards its tip (`grip`). Each point is carried along the curled line
	// of the tail and turned with it.
	float root_y = tail_root * LENGTH;
	if (v.y < root_y && (part < 0.5 || part == 5.0 || part == 6.0)) {
		float tail_long = (tail_root - TIP_Y) * LENGTH;
		float l = clamp(root_y - v.y, 0.0, tail_long);
		float u = l / tail_long;
		v.x += LENGTH * 0.03 * sway * u * u * sin(bobbing * 2.0 - u * 2.5);
		float total = mix(0.75, 8.6, grip);
		float power = mix(2.4, 1.75, grip);
		vec2 along = vec2(0.0);
		float dl = l / 14.0;
		for (int i = 0; i < 14; i++) {
			float th = total * pow((float(i) + 0.5) * dl / tail_long, power);
			along += dl * vec2(-cos(th), -sin(th));
		}
		float th = total * pow(u, power);
		float c = cos(th);
		float sn = sin(th);
		float oz = v.z;
		v.y = root_y + along.x - oz * sn;
		v.z = along.y + oz * c;
		n.yz = vec2(n.y * c - n.z * sn, n.y * sn + n.z * c);
	}
	// It bobs up and down and rocks a little, about its middle.
	float rock = bob * 0.05 * sin(bobbing + 1.2);
	float c = cos(rock);
	float sn = sin(rock);
	v.yz = vec2(v.y * c - v.z * sn, v.y * sn + v.z * c);
	n.yz = vec2(n.y * c - n.z * sn, n.y * sn + n.z * c);
	v.y += bob * 0.012 * LENGTH * sin(bobbing);
	VERTEX = v;
	NORMAL = normalize(n);
}


vec2 hash2(vec2 p) {
	p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
	return fract(sin(p) * 43758.5453);
}


// Small round flecks scattered over a place (`q` in heights; `cell` how far apart; `size` of a
// cell): 1 on a fleck.
float flecks(vec2 q, float cell, float size, float keep) {
	vec2 g = q / cell;
	vec2 base = floor(g);
	float aa = max(length(fwidth(g)) * 0.7, 0.02);
	float best = 0.0;
	for (int i = -1; i <= 1; i++) {
		for (int j = -1; j <= 1; j++) {
			vec2 c = base + vec2(float(i), float(j));
			vec2 h = hash2(c);
			if (fract(h.x * 7.13 + h.y) > keep) {
				continue;
			}
			float d = length(g - (c + 0.2 + 0.6 * h));
			best = max(best, 1.0 - smoothstep(size - aa, size + aa, d));
		}
	}
	return best;
}


// The cartoon eye at a point of the eye's dome (`uv` its UV), in skin of colour `skin`, looking
// `look`. On the dome, e is (towards the snout, up) in seen radii of the eye.
vec3 cartoon_eye(vec2 uv, vec3 skin, vec2 look) {
	vec2 on_eye = uv * 2.0 - 1.0;
	vec2 e = vec2(on_eye.y, on_eye.x) / 0.644;
	float er = length(e);
	vec3 white = vec3(0.97, 0.96, 0.92);
	vec3 ink = vec3(0.02, 0.02, 0.025);
	vec2 ic = e - clamp(look, vec2(-1.0), vec2(1.0)) * (0.92 - iris_size) * 0.75;
	float ir = length(ic) / iris_size;
	float aa = max(fwidth(ir), 0.02);
	vec3 c = mix(white * 0.86, white, smoothstep(1.0, 0.4, er));
	vec3 ring = mix(iris * 1.2, iris * 0.6, smoothstep(0.3, 1.0, ir));
	c = mix(c, ring, 1.0 - smoothstep(1.0 - aa, 1.0 + aa, ir));
	c = mix(c, iris * 0.3, smoothstep(0.82, 0.95, ir) * (1.0 - smoothstep(1.0 - aa, 1.0 + aa, ir)));
	float pd = length(ic / (iris_size * pupil_size));
	float pa = max(fwidth(pd), 0.02);
	c = mix(c, ink, 1.0 - smoothstep(1.0 - pa, 1.0 + pa, pd));
	float ea = max(fwidth(er), 0.01);
	c = mix(c, vec3(1.0), 1.0 - smoothstep(0.16 - ea, 0.16 + ea, length(e - vec2(0.25, 0.36))));
	c = mix(c, vec3(1.0), 0.8 * (1.0 - smoothstep(0.065 - ea, 0.065 + ea, length(e - vec2(-0.2, -0.3)))));
	float shut = -0.12;
	float upper = mix(lid + lid_tilt * e.x, shut, blink);
	float lower = mix(lower_lid - 0.12 * e.x * e.x, shut + 0.03, blink);
	float la = max(fwidth(e.y), 0.01);
	float on_lid = max(smoothstep(upper - la, upper + la, e.y), 1.0 - smoothstep(lower - la, lower + la, e.y));
	float lid_edge = max(1.0 - smoothstep(0.06, 0.06 + 2.0 * la, abs(e.y - upper)),
		0.6 * (1.0 - smoothstep(0.04, 0.04 + 2.0 * la, abs(e.y - lower))));
	c = mix(c, skin * 0.92, on_lid);
	c = mix(c, ink, lid_edge * step(er, 1.0) * step(upper, 1.0));
	c = mix(c, ink, smoothstep(0.85 - ea, 0.87 + ea, er));
	c = mix(c, skin, smoothstep(1.0 - ea, 1.0 + ea, er));
	return c;
}


void fragment() {
	vec3 q = rest / LENGTH;
	float rough = 0.45;
	float glint = sheen;
	float seen = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	bool tube = part < 0.5;
	// How far round from the back line (radians, + to its right), and the ring (a rim at each
	// whole number) where that is known; on the head and the rest, from where the point is.
	float phi = tube ? (UV.y * TAU) : atan(q.x, q.z);
	float ring = tube ? UV2.x : 0.0;
	float on_rim = tube ? pow(0.5 + 0.5 * cos(TAU * ring), 6.0) : 0.0;
	float tail = tube ? smoothstep(tail_root + 0.025, tail_root - 0.02, q.y) : 0.0;
	float on_ridge = tube ? mix(pow(0.5 + 0.5 * cos(7.0 * phi), 6.0), pow(0.5 - 0.5 * cos(4.0 * phi), 6.0), tail) : 0.0;
	// (how far towards its front a point is, and its height, for the bands and the belly)
	float front = smoothstep(0.3, 0.95, -cos(phi));
	vec3 c;
	vec3 fin;
	vec3 tip_colour;
	if (kind == 0) {
		// COMMON (the Pacific seahorse): golden yellow-orange, a little dusky in saddles across the
		// back, the rims of its rings darker, its ridges paler, white flecks; a paler belly.
		vec3 gold = vec3(0.96, 0.64, 0.16);
		c = mix(gold, vec3(1.0, 0.8, 0.42), 0.45 * front * smoothstep(0.35, 0.0, abs(q.y - 0.05)));
		float saddle = smoothstep(0.55, 0.9, sin(q.y * 26.0 + 0.6)) * smoothstep(0.2, -0.4, -cos(phi));
		c = mix(c, vec3(0.62, 0.34, 0.08), 0.45 * saddle * (1.0 - tail * 0.5));
		c = mix(c, vec3(0.58, 0.32, 0.07), 0.4 * on_rim);
		c = mix(c, vec3(1.0, 0.86, 0.5), 0.35 * on_ridge);
		float f = flecks(vec2(phi * 0.06, q.y), 0.018, 0.16, 0.55);
		c = mix(c, vec3(1.0, 0.97, 0.88), 0.85 * f * (tube || part == 1.0 ? 1.0 : 0.0));
		fin = vec3(0.98, 0.84, 0.5);
		tip_colour = vec3(0.45, 0.24, 0.06);
	} else if (kind == 1) {
		// SPINY (the thorny seahorse): pale sandy cream with broad red-brown bands every few rings,
		// its spikes pale at the root and dark at the tip.
		vec3 cream = vec3(0.93, 0.8, 0.6);
		vec3 band_colour = vec3(0.6, 0.27, 0.12);
		float bands = tube ? smoothstep(0.62, 0.8, 0.5 + 0.5 * cos(TAU * (ring + 0.5) / 3.0)) : 0.0;
		bands = max(bands, (part == 1.0) ? smoothstep(0.6, 0.85, 0.5 + 0.5 * cos(q.z * 38.0)) * smoothstep(-0.12, -0.2, q.z) : 0.0);
		c = mix(cream, band_colour, 0.8 * bands);
		c = mix(c, cream * 0.75, 0.4 * on_rim * (1.0 - bands));
		c = mix(c, vec3(0.98, 0.9, 0.75), 0.3 * on_ridge);
		fin = vec3(0.95, 0.86, 0.7);
		tip_colour = vec3(0.3, 0.12, 0.06);
	} else {
		// PYGMY: pale lilac-pink, mottled with soft rosy blotches; its tubercles bright red-pink.
		vec3 lilac = vec3(0.93, 0.76, 0.86);
		c = lilac;
		float blotch = flecks(vec2(phi * 0.06, q.y), 0.03, 0.34, 0.7);
		c = mix(c, vec3(0.88, 0.56, 0.7), 0.6 * blotch * (tube || part == 1.0 ? 1.0 : 0.0));
		fin = vec3(0.97, 0.85, 0.92);
		tip_colour = vec3(0.92, 0.3, 0.42);
	}
	if (part == 4.0) {
		// The coronet: its points darker at their tips.
		c = mix(c, tip_colour * 1.2, 0.6 * smoothstep(0.55, 1.0, UV.x));
	} else if (part == 5.0) {
		c = mix(c * 1.05, tip_colour, smoothstep(0.35, 0.9, UV.x));
		rough = 0.35;
	} else if (part == 6.0) {
		// A tubercle: its own red-pink, paler at its crown, a little darker where it meets the skin.
		c = mix(tip_colour * 0.8, mix(tip_colour, vec3(1.0, 0.75, 0.75), 0.4), smoothstep(0.3, 1.0, UV.x));
		rough = 0.3;
		glint = 0.35;
	} else if (part > 6.5) {
		// A fin: pale, its rays as fine lines.
		c = fin;
		float between = abs(fract(UV.y) - 0.5) * 2.0;
		float lines = smoothstep(0.55, 1.0, between) * smoothstep(0.05, 0.3, UV.x) * (1.0 - smoothstep(0.3, 0.8, fwidth(UV.y)));
		c *= 1.0 - 0.2 * lines;
		c = mix(c, tip_colour, 0.3 * smoothstep(0.85, 1.0, UV.x));
		rough = 0.5;
		glint *= 0.4;
	}
	if (part > 2.5 && part < 3.5) {
		// An eye: a dark pupil in a gold ring lined with dark rays; the skin round it.
		vec2 on_eye = UV * 2.0 - 1.0;
		float er = length(on_eye);
		vec3 around = c;
		float rays = 0.5 + 0.5 * cos(atan(on_eye.y, on_eye.x) * 14.0);
		c = mix(mix(vec3(0.85, 0.62, 0.2), vec3(0.35, 0.2, 0.05), 0.5 * rays), around * 0.55, smoothstep(0.52, 0.64, er));
		c = mix(c, vec3(0.01), 1.0 - smoothstep(0.26, 0.3, er));
		if (cartoon_eyes > 0.0) {
			c = mix(c, cartoon_eye(UV, around, rest.x >= 0.0 ? eye_look : eye_look_other), cartoon_eyes);
		}
		rough = 0.08;
		glint = 0.0;
	}
	c = mix(c, mouth, inside);
	glint *= 1.0 - inside;
	c *= tint;
	float aslant = pow(1.0 - seen, 3.0);
	c += vec3(1.0, 0.97, 0.9) * glint * aslant;
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = 0.4;
	EMISSION = c * (rim * 0.8 * aslant) + vec3(flash);
}
