shader_type spatial;
// The guppy (guppy.gd): every marking drawn here (no texture files), its swimming, the ripple of
// its tail and dorsal fin, and its mouth. What each point is comes from the model
// (tools/build_guppy.py): UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin or the male's
// gonopodium, 3 the tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a gill
// arch). UV2.x: 1
// inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its
// side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip or back edge
// (1), y leading or upper edge (0) to trailing or lower edge (1); on an eye: x middle (0) to rim (1).
//
// Every place here is in BODY LENGTHS (the tip of the jaw 0, the end of the tail 1), as the build
// script has them: the model's metres are divided by `length_m`. The numbers of each model's shape
// (`jaw_to` to `gill`) are set by Guppy for the model it wears.
//
// It swims as small livebearers do: a wave runs back along the body, growing to the tail; behind
// the tail's root the fin is carried partly as one plate and partly lags behind as the wave runs
// on along it, and a ripple runs across the big tail and the dorsal fin like cloth. All of it is a
// function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back;

const float HALF = 0.5;
const float GAPE_OPEN = 1.0;

// The model's shape, as tools/build_guppy.py prints it (SHADER line). Set by Guppy.
uniform float length_m = 0.04;
uniform float jaw_to = 0.037;
uniform float hinge_y = -0.01132;
uniform vec2 eye_at = vec2(0.074, 0.013);
uniform float eye_radius = 0.031;
uniform float joint = 0.525;
uniform float body_to = 0.548;
// The line of the mouth (y at the tip, slope) and the gill cover's edge (x at its middle, curve).
uniform vec2 mouth = vec2(0.002, -0.36);
uniform vec2 gill = vec2(0.16, 8.0);
// 1 the male (a big tail that trails), 0 the female (a small tail carried stiffly).
uniform float male = 1.0;

// How far through one beat (0..1, it wraps). Set by Guppy.
uniform float phase = 0.0;
// How many times its tail beats in one beat, and how many ripples run across its fins (whole numbers).
uniform float tail_beats = 3.0;
uniform float ripples = 2.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the
// gills to the tail (0 straight; more than 0 the tail comes round to +X, its left, as it turns
// left). The head stays as it is. (As the yellowfin tuna's `curl`.)
uniform float curl = 0.0;
// How widely it beats, 1 cruising.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 0.9;
// How strongly its tail and dorsal fin ripple (0 still, 1 as a guppy cruising).
uniform float ripple = 1.0;
// How far its mouth is open: 0 shut, 1 wide open. The lower jaw swings down about its hinge.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// Which pattern: 0 the plain female, 1 a wild male (orange, black and shining blue spots), 2 a red
// delta, 3 a blue grass, 4 a cobra (snakeskin). And a number that makes each one's spots and
// marks its own.
uniform int pattern = 0;
uniform float pattern_seed = 0.0;
// The body: its back, its side, its belly, the colour its back half turns (the males), the shine
// where light glances off it.
uniform vec3 body_back : source_color = vec3(0.36, 0.34, 0.22);
uniform vec3 body_side : source_color = vec3(0.62, 0.60, 0.46);
uniform vec3 belly : source_color = vec3(0.90, 0.88, 0.80);
uniform vec3 body_rear : source_color = vec3(0.62, 0.60, 0.46);
uniform vec3 sheen : source_color = vec3(0.4, 0.7, 0.8);
// The tail and dorsal fin: their main colour, at the root, at the edge, and their marks.
uniform vec3 fin_main : source_color = vec3(0.72, 0.70, 0.60);
uniform vec3 fin_root : source_color = vec3(0.62, 0.60, 0.50);
uniform vec3 fin_edge : source_color = vec3(0.80, 0.78, 0.70);
uniform vec3 fin_mark : source_color = vec3(0.05, 0.05, 0.05);
// The spots: three colours (the wild male's orange, black and shining blue-green).
uniform vec3 spot_a : source_color = vec3(0.95, 0.42, 0.08);
uniform vec3 spot_b : source_color = vec3(0.03, 0.03, 0.03);
uniform vec3 spot_c : source_color = vec3(0.15, 0.7, 0.75);
// The small clear fins.
uniform vec3 fin_clear : source_color = vec3(0.70, 0.70, 0.66);
// The inside of the mouth.
uniform vec3 mouth_inside : source_color = vec3(0.14, 0.04, 0.05);

// THE GILLS (part 8): four arches a side standing in the throat, a short tunnel from the back of the
// mouth back to `gill_to` (the model's numbers, set by Guppy: build_guppy.py prints them). Seen only
// through the open mouth; as it opens they spread a little. Blood red, darker deeper in the throat.
// `wall_up`: where the full model's old wall across the back of its mouth is lifted to as it opens.
uniform float gill_from = 0.0806;
uniform float gill_to = 0.146;
uniform float wall_up = 0.0129;
uniform vec3 gill_red : source_color = vec3(0.55, 0.04, 0.06);
uniform vec3 gill_raker : source_color = vec3(0.86, 0.74, 0.70);

// THE CARTOON EYE (`cartoon_eyes`), the guppy's own, each type's character in its settings (set by
// Guppy): the males bright, eager show-offs (a big round stare, no lid, the iris the colour of their
// own tail: `eye_iris`), the female calm and gentle (a soft amber iris under a heavy, relaxed half lid).
// A clean white, a big round pupil, a highlight that stays put up and forward, a dark outline. The
// eye is drawn `eye_big` times its size (its dome scaled about its middle).
uniform float eye_big = 1.45;
uniform float iris_r = 0.64;
uniform float pupil_r = 0.42;
// Where its upper lid rests (on the eye's own up: 1 its top, more than 1 no lid showing), and how it
// slants (more than 0 lower towards the snout).
uniform float lid_rest = 1.3;
uniform float lid_slant = 0.0;
uniform vec3 eye_iris : source_color = vec3(0.95, 0.5, 0.1);
// 0 the eye as it is in life, 1 the cartoon eye.
uniform float cartoon_eyes : hint_range(0.0, 1.0) = 0.0;
// Where the cartoon eyes look: x towards the snout (+) or back (-), y up (+) or down (-), -1..1.
uniform vec2 eye_look = vec2(0.0);
// A blink: 0 open, 1 shut (a lid the colour of the skin comes down over the eye).
uniform float blink : hint_range(0.0, 1.0) = 0.0;

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

// Cells: x the distance to the nearest cell's middle, y to the second nearest, z a number of the
// nearest cell (0..1).
vec3 cells(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	float d1 = 8.0;
	float d2 = 8.0;
	float id = 0.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = vec2(hash2(i + g + pattern_seed * 7.31), hash2(i + g + 19.7 + pattern_seed * 3.17));
			float d = length(g + o - f);
			if (d < d1) {
				d2 = d1;
				d1 = d;
				id = hash2(i + g + 41.3 + pattern_seed * 1.93);
			} else if (d < d2) {
				d2 = d;
			}
		}
	}
	return vec3(d1, d2, id);
}

// How far to one side the middle line of the body is (body lengths), `xm` behind the jaw.
float side_at(float xm) {
	float s = xm / joint;
	float reach = 0.008 - 0.03 * s + 0.085 * s * s;
	return sway * reach * sin(6.2831853 * (phase * tail_beats - xm / wave));
}

// How far a fin behind the tail's root lags to one side of where the plate would carry it.
float trail_at(float xm) {
	float d = max(xm - joint, 0.0);
	return sway * male * 0.24 * d * sqrt(d) * sin(6.2831853 * (phase * tail_beats - xm / wave - 0.08));
}

// The ripple across the tail and the dorsal fin: how far to one side it puts a point of the fin
// (body lengths), at `xm` behind the jaw and `y` up.
float ripple_at(float xm, float y, float on_tail) {
	float rp = 6.2831853 * phase * ripples;
	float w;
	if (on_tail > 0.5) {
		w = smoothstep(joint, joint + 0.3, xm) * mix(0.004, 0.016, male);
	} else {
		w = clamp((y - 0.05) / 0.1, 0.0, 1.0) * smoothstep(0.3, 0.6, xm) * 0.012 * male;
	}
	return ripple * w * sin(rp - xm * 22.0 + y * 30.0);
}

// The body behind the head laid round an arc (see `curl`).
void curl_bend(inout vec3 v, inout vec3 n) {
	float from = -0.2;
	float d = v.z - from;
	if (abs(curl) < 0.001 || d <= 0.0) {
		return;
	}
	float k = curl / 0.7;
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
	vec3 v = VERTEX / length_m;
	rest = v;
	vec3 n = NORMAL;
	float xm = v.z + HALF;
	int p = int(part + 0.5);
	if (cartoon_eyes > 0.0 && p == 6) {
		// The cartoon eye: its dome drawn bigger about its middle, a little further out of the head.
		float big = mix(1.0, eye_big, cartoon_eyes);
		vec2 middle = vec2(eye_at.y, eye_at.x - HALF);
		v.yz = middle + (v.yz - middle) * big;
		v.x += sign(v.x) * (big - 1.0) * eye_radius * 0.3;
		// (grown backwards, onto the wider head behind it: its front edge stays about where it was)
		v.z += (big - 1.0) * eye_radius * 0.8;
		xm = v.z + HALF;
	}
	if (gape > 0.0 && p == 0 && inside > 0.999 && UV.y > 0.45 && UV.y < 0.55 && abs(xm - jaw_to) < 0.0005) {
		// The full model's old wall across the back of the mouth (the foot of it): as the mouth
		// opens it is lifted up out of the way, above the roof of the mouth, so that the throat and
		// the gills behind it show. (The throat's own points are told apart by their UV's y, 0.)
		v = vec3(v.x * 0.55, wall_up, v.z + 0.004);
	}
	if (p == 8) {
		// The gill arches spread a little as the mouth opens.
		float open = clamp(gape, 0.0, 1.0);
		v.x *= 1.0 + 0.1 * open;
		v.z += (xm - 0.5 * (gill_from + gill_to)) * 0.15 * open;
		xm = v.z + HALF;
	}
	if (p == 7) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = clamp(gape, 0.0, 1.0) * GAPE_OPEN * (1.0 - smoothstep(jaw_to - 0.016, jaw_to - 0.002, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - hinge_y, xm - jaw_to);
		v.y = hinge_y + d.x * ca + d.y * sa;
		v.z = jaw_to - HALF + d.y * ca - d.x * sa;
		n = vec3(n.x, n.y * ca + n.z * sa, n.z * ca - n.y * sa);
		xm = v.z + HALF;
	}
	if (p == 3 || p == 1) {
		// The ripple: a fold that runs back across the fin, both of its skins moved alike.
		float on_tail = p == 3 ? 1.0 : 0.0;
		float e = 0.004;
		float r = ripple_at(xm, v.y, on_tail);
		float dz = (ripple_at(xm + e, v.y, on_tail) - ripple_at(xm - e, v.y, on_tail)) / (2.0 * e);
		float dy = (ripple_at(xm, v.y + e, on_tail) - ripple_at(xm, v.y - e, on_tail)) / (2.0 * e);
		v.x += r;
		n = vec3(n.x, n.y - n.x * dy, n.z - n.x * dz);
	}
	// (behind its root the tail is carried partly as one plate, turned about the root)
	float zc = min(xm, joint);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.003) - side_at(zc - 0.003)) / 0.006;
	float turn = atan(slope) * (1.0 + 0.2 * smoothstep(0.86 * joint, joint, zc)) * mix(1.0, 0.55, step(joint, xm) * male);
	float c = cos(turn);
	float sn = sin(turn);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(h + o.x * c + o.z * sn, o.y, zc - HALF - o.x * sn + o.z * c);
	n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	// (and lags behind it as the wave runs on along the fin)
	if (xm > joint) {
		float lag = trail_at(xm);
		float lag_slope = (trail_at(xm + 0.004) - trail_at(xm - 0.004)) / 0.008;
		v.x += lag;
		n.z -= n.x * lag_slope;
	}
	curl_bend(v, n);
	VERTEX = v * length_m;
	NORMAL = normalize(n);
}

float mouth_y(float xm) {
	return mouth.x + mouth.y * xm;
}

float gill_x(float y) {
	return gill.x - gill.y * (y + 0.008) * (y + 0.008);
}

// Spots on the body or a fin: a colour, and how much of it there is here (0 none).
vec4 spots(vec2 at, float size, inout float shiny) {
	vec3 k = cells(at);
	float r = size * (0.55 + 0.6 * fract(k.z * 13.7));
	float in_spot = 1.0 - smoothstep(r * 0.75, r, k.x);
	vec3 colour = spot_b;
	float which = fract(k.z * 7.3);
	if (which < 0.35) {
		colour = spot_a;
	} else if (which < 0.6) {
		colour = spot_c;
		shiny = in_spot;
	} else if (which > 0.82) {
		in_spot = 0.0;
	}
	return vec4(colour, in_spot);
}

// The cartoon eye at a place on it `e` (x towards the snout, y up; its rim at 1): the white, the
// iris and pupil slid by `eye_look`, a highlight that stays put, a dark outline. `shine`: how much
// of it shines of itself (the highlight).
vec3 cartoon_eye(vec2 e, out vec3 shine) {
	float d = length(e);
	vec2 at = e - clamp(eye_look, vec2(-1.0), vec2(1.0)) * vec2(0.24, 0.2);
	float r = length(at);
	vec3 c = vec3(0.96, 0.95, 0.92) * mix(1.0, 0.8, smoothstep(0.35, 0.85, d));
	vec3 ring = eye_iris * mix(1.2, 0.7, smoothstep(0.1, iris_r, r)) * mix(0.85, 1.1, smoothstep(-0.4, 0.4, -at.y));
	float in_iris = 1.0 - smoothstep(iris_r - 0.03, iris_r, r);
	c = mix(c, ring, in_iris);
	c = mix(c, ring * 0.3, smoothstep(iris_r - 0.11, iris_r - 0.03, r) * in_iris);
	c = mix(c, vec3(0.008, 0.01, 0.014), 1.0 - smoothstep(pupil_r - 0.03, pupil_r, r));
	float spark = max(1.0 - smoothstep(0.12, 0.15, length(e - vec2(0.2, 0.3))), 0.8 * (1.0 - smoothstep(0.05, 0.07, length(e - vec2(-0.14, -0.2)))));
	c = mix(c, vec3(1.0), spark);
	shine = vec3(0.5) * spark;
	return mix(c, vec3(0.02, 0.02, 0.02), smoothstep(0.83, 0.9, d));
}

void fragment() {
	int p = int(part + 0.5);
	vec3 nrm = normalize(NORMAL);
	float facing = clamp(dot(nrm, normalize(VIEW)), 0.0, 1.0);
	float glance = 1.0 - facing;
	vec3 c;
	float rough = 0.45;
	float spec = 0.5;
	vec3 glow = vec3(0.0);
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float y = rest.y;
		float q = UV.y * 2.0 - 1.0;
		float behind = xm - gill_x(y);
		float cloud = noise2(vec2(xm * 50.0, y * 60.0) + pattern_seed);
		// The olive back, the paler side, the pale belly.
		c = mix(belly, body_side, smoothstep(-0.7, -0.15, q));
		c = mix(c, body_back * (0.85 + 0.3 * cloud), smoothstep(0.25, 0.75, q));
		// The scales: each edged darker, in half-stepped rows (a guppy's net of scales).
		float arc = acos(clamp(q, -1.0, 1.0)) * 0.07;
		float row = floor(arc / 0.013);
		float along = xm / 0.016 + 0.5 * mod(row, 2.0);
		vec2 f = vec2(fract(along), fract(arc / 0.013));
		float rim = smoothstep(0.6, 0.95, length(vec2(f.x, (f.y - 0.5) * 1.2)));
		float scaled = smoothstep(0.0, 0.01, behind) * (1.0 - smoothstep(body_to - 0.04, body_to, xm));
		c *= 1.0 - 0.14 * rim * scaled * (pattern == 4 ? 0.0 : 1.0);
		// The males' back half turns to their own colour.
		float rear = male * smoothstep(0.18, 0.42, xm) * smoothstep(-0.9, -0.4, q) * (1.0 - smoothstep(0.7, 0.95, q) * 0.5);
		c = mix(c, body_rear * (0.85 + 0.3 * cloud), rear);
		if (pattern == 0) {
			// The female's gravid spot: a dark patch over the belly in front of the anal fin.
			float gravid = 1.0 - smoothstep(0.03, 0.06, length(vec2((xm - 0.52) * 0.9, y + 0.045)));
			c = mix(c, vec3(0.12, 0.1, 0.08), gravid * 0.7);
		} else if (pattern == 1) {
			// A wild male: big orange, black and shining blue-green spots over the side.
			float shiny = 0.0;
			vec4 s = spots(vec2(xm * 14.0, y * 14.0), 0.42, shiny);
			float on_side = smoothstep(0.14, 0.2, xm) * (1.0 - smoothstep(body_to - 0.03, body_to, xm)) * smoothstep(-0.8, -0.5, q) * (1.0 - smoothstep(0.7, 0.9, q));
			c = mix(c, s.rgb, s.a * on_side);
			glow += spot_c * 0.3 * shiny * on_side * (0.4 + 0.6 * facing);
		} else if (pattern == 3) {
			// A blue grass: fine black dots over the blue back half.
			vec3 k = cells(vec2(xm * 55.0, y * 55.0));
			c = mix(c, fin_mark, (1.0 - smoothstep(0.12, 0.22, k.x)) * rear * step(0.3, k.z));
		} else if (pattern == 4) {
			// A cobra: the snakeskin, a dark net over the whole body.
			vec3 k = cells(vec2(xm * 34.0, y * 30.0));
			float net = 1.0 - smoothstep(0.04, 0.12, k.y - k.x);
			c = mix(c, fin_mark, net * 0.85 * smoothstep(0.08, 0.14, xm) * (1.0 - smoothstep(0.85, 1.0, q)));
		}
		// The shine where light glances off its side.
		c += sheen * (0.25 + 0.35 * male) * glance * glance * smoothstep(-0.6, 0.0, q);
		// The head: the line of the mouth, the gill cover's edge.
		float mouth_l = (1.0 - smoothstep(0.001, 0.003, abs(y - mouth_y(xm)))) * smoothstep(0.0, 0.004, xm) * (1.0 - smoothstep(jaw_to - 0.006, jaw_to, xm)) * (1.0 - smoothstep(0.0, 0.3, gape));
		c = mix(c, vec3(0.06, 0.05, 0.05), mouth_l * 0.7);
		float span = smoothstep(-0.95, -0.8, q) * (1.0 - smoothstep(0.35, 0.55, q));
		float crease = (1.0 - smoothstep(0.0, 0.004, abs(behind - 0.002))) * 0.5;
		c = mix(c, c * 0.5, crease * span);
		rough = 0.38;
		spec = 0.55;
		c = mix(c, mouth_inside, inside);
		glow *= 1.0 - inside;
		rough = mix(rough, 0.8, inside);
		spec = mix(spec, 0.2, inside);
	} else if (p == 6) {
		// An eye: a big black pupil, a pale gold-silver iris, a dark rim.
		// (the game model's eye, UV y 1, has few points: its rings are drawn round from where it is)
		float r = UV.y > 0.5 ? length(vec2(eye_at.x - (rest.z + HALF), rest.y - eye_at.y)) / eye_radius : UV.x;
		vec3 iris = mix(vec3(0.55, 0.53, 0.45), vec3(0.7, 0.55, 0.25), 0.4);
		c = mix(vec3(0.004, 0.005, 0.008), iris, smoothstep(0.52, 0.6, r));
		c = mix(c, body_back * 0.5, smoothstep(0.86, 1.0, r) * 0.85);
		rough = 0.12;
		spec = 0.7;
		if (cartoon_eyes > 0.0 || blink > 0.0) {
			// (on the eye's own face: x towards the snout, y up, its rim at 1)
			vec2 e = vec2(eye_at.x - (rest.z + HALF), rest.y - eye_at.y) / eye_radius;
			if (cartoon_eyes > 0.0) {
				vec3 shine;
				c = mix(c, cartoon_eye(e, shine), cartoon_eyes);
				glow = mix(glow, shine, cartoon_eyes);
			}
			// The lid: where it rests on the cartoon eye (the type's own), and `blink` brings it
			// down over the eye; its edge a dark line.
			float lid = mix(mix(1.3, lid_rest, cartoon_eyes) - lid_slant * e.x, -1.08, blink);
			float shut = smoothstep(lid - 0.015, lid + 0.015, e.y);
			c = mix(c, mix(body_back, body_side, 0.35), shut);
			c = mix(c, body_back * 0.3, (1.0 - smoothstep(0.02, 0.08, abs(e.y - lid))) * (1.0 - smoothstep(0.95, 1.05, lid)) * 0.85);
			glow *= 1.0 - shut;
			rough = mix(rough, 0.4, shut);
			spec = mix(spec, 0.5, shut);
		}
	} else if (p == 8) {
		// A gill arch: its pale rakers at the inner front edge, the red bar, then the fringe of
		// blood-red filaments (fine lines along it), darker deeper in the shadow of the throat.
		float t = UV.x;
		float u = UV.y;
		c = mix(gill_raker, gill_red * 1.3, smoothstep(0.08, 0.22, u));
		c = mix(c, gill_red * 0.8, smoothstep(0.3, 0.45, u));
		c *= mix(1.0, 0.7 + 0.3 * (0.5 + 0.5 * cos(t * 150.0)), smoothstep(0.35, 0.5, u));
		c = mix(c, c * 0.7, (1.0 - smoothstep(0.06, 0.12, u)) * step(0.5, fract(t * 16.0)));
		c *= mix(1.0, 0.45, smoothstep(gill_from - 0.02, gill_to, rest.z + HALF));
		rough = 0.35;
		spec = 0.45;
	} else if (p == 3 || p == 1) {
		// The tail and the dorsal fin.
		float t = UV.x;
		float u = UV.y;
		float ray = 0.5 + 0.5 * cos(u * (p == 3 ? 90.0 : 40.0));
		c = mix(fin_root, fin_main, smoothstep(0.0, 0.45, t));
		c = mix(c, fin_edge, smoothstep(0.8, 1.0, t) * 0.7);
		c *= 0.88 + 0.12 * ray;
		vec2 at = vec2(t * 9.0, u * (p == 3 ? 13.0 : 5.0));
		if (pattern == 1) {
			float shiny = 0.0;
			vec4 s = spots(at + 3.1, 0.38, shiny);
			c = mix(c, s.rgb, s.a * smoothstep(0.15, 0.3, t) * 0.9);
		} else if (pattern == 3) {
			vec3 k = cells(at * 2.8);
			c = mix(c, fin_mark, (1.0 - smoothstep(0.14, 0.26, k.x)) * step(0.25, k.z) * smoothstep(0.1, 0.3, t));
		} else if (pattern == 4) {
			vec3 k = cells(at * 2.0);
			float net = 1.0 - smoothstep(0.05, 0.14, k.y - k.x);
			c = mix(c, fin_mark, net * 0.9 * smoothstep(0.1, 0.25, t));
		}
		c += sheen * 0.15 * male * glance * glance;
		rough = 0.5;
		spec = 0.35;
	} else if (p == 2) {
		// The anal fin (clear) or the male's gonopodium (the colour of its body, darker at its tip).
		c = male > 0.5 ? mix(body_rear * 0.9, fin_mark * 2.0 + 0.1, smoothstep(0.6, 1.0, UV.x)) : fin_clear * (0.9 + 0.1 * cos(UV.y * 40.0));
	} else {
		// The pectoral and pelvic fins: clear.
		c = fin_clear * (0.9 + 0.1 * cos(UV.y * 40.0));
		rough = 0.5;
		spec = 0.35;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = glow;
}
