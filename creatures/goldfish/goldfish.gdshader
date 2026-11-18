shader_type spatial;
// The goldfish (goldfish.gd): every marking drawn here (no texture files), and its swimming, for both
// kinds (common and fantail: goldfish.gd sets the numbers that differ, `joint` to `gill_at`, from its
// KINDS). What each point is comes from the model (tools/build_goldfish.py): UV2.y the part (0 body, 1 the
// dorsal fin, 2 an anal fin, 3 a tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw).
// UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the body and the jaw: x how far along, y how high on its
// side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to edge (1), y leading
// edge (0) to trailing edge (1); on an eye: x middle (0) to rim (1).
//
// It swims as carp do (subcarangiform): a wave runs back along the body, small at the head and growing
// through the back half; behind its hinge the tail is carried round with the wrist, and its fins billow
// (a wave that runs out from root to edge: `billow`, much more on the fantail's long double tail). All of
// it is a function of `phase` alone, so a picture of it loops exactly. The mouth opens (`gape`): the
// lower jaw swings down about its hinge and the whole mouth pushes forward a little, as a goldfish's does.
// Nothing here needs more than GL Compatibility has.
render_mode cull_back;

const float LENGTH = 0.15;
const float HALF = 0.075;
// How far the lower jaw swings down, wide open (radians), and how far the mouth pushes forward and up.
const float GAPE_OPEN = 0.95;
const float PROTRUDE = 0.0012;
const float LIFT = 0.0003;

// Kept in step with the model of each kind (goldfish.gd's KINDS; the build script prints them).
// Where the tail is hinged (metres behind the snout); where the lower jaw is hinged, along and up; where
// the body ends; the eye's middle (along, up); where the gill cover's edge is, at the middle line.
uniform float joint = 0.108;
uniform float jaw_to = 0.0095;
uniform float hinge_y = -0.00154;
uniform float body_to = 0.116;
uniform vec2 eye_at = vec2(0.0175, 0.0042);
uniform float gill_at = 0.029;

// How far through a beat of its tail (0..1, it wraps). Set by Goldfish.
uniform float phase = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the gills to the
// tail (0 straight; more than 0 the tail comes round to +X, its left). As the yellowfin tuna's `curl`.
uniform float curl = 0.0;
// How widely it beats, for 1 as a goldfish cruising.
uniform float sway = 1.0;
// How long the wave along its body is, in body lengths.
uniform float wave = 1.0;
// How much its fins billow (the tail most): 0 stiff, 1 the fantail's long tail flowing.
uniform float billow = 0.3;
// How far its mouth is open: 0 shut, 1 wide open.
uniform float gape : hint_range(0.0, 1.0) = 0.0;

// The colours. `base` all over, `back` the top of the back shades to, `belly` the belly. Patches of `patch`
// (red on a red-and-white, orange on a calico) cover about `patch_amount` of it; patches of `black` cover
// `black_amount`, and black `speckle` (0 none) peppers it, as on a calico.
uniform vec3 base : source_color = vec3(0.98, 0.45, 0.06);
uniform vec3 back : source_color = vec3(0.82, 0.3, 0.03);
uniform vec3 belly : source_color = vec3(1.0, 0.72, 0.36);
uniform vec3 patch : source_color = vec3(0.86, 0.12, 0.04);
uniform float patch_amount = 0.0;
uniform vec3 black : source_color = vec3(0.03, 0.03, 0.04);
uniform float black_amount = 0.0;
uniform float speckle = 0.0;
// Patches lie more on the back and the head than low on the flank, this much (0 evenly).
uniform float patch_on_back = 0.5;
// How bright the scales are (metallic scales shine; a calico's are matt): 0 matt, 1 bright.
uniform float shine = 0.8;
// How strongly the scales' edges show.
uniform float scales_show = 0.7;
// The fins: their colour at the root and at the edge; how see-through they look (paler, like the water).
uniform vec3 fin_root : source_color = vec3(0.98, 0.48, 0.1);
uniform vec3 fin_edge : source_color = vec3(1.0, 0.7, 0.42);
uniform float fin_clear = 0.35;
// The water's colour that clear fins take on.
uniform vec3 water : source_color = vec3(0.55, 0.7, 0.78);
// The eye's ring (iris); the inside of the mouth.
uniform vec3 iris : source_color = vec3(0.85, 0.55, 0.12);
uniform vec3 mouth_inside : source_color = vec3(0.32, 0.06, 0.06);

varying vec3 rest;
varying float part;
varying float inside;

float hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), f.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), f.x), f.y);
	float b = mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), f.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), f.x), f.y);
	return mix(a, b, f.z);
}

float fbm3(vec3 p) {
	return 0.55 * noise3(p) + 0.3 * noise3(p * 2.1 + 7.0) + 0.15 * noise3(p * 4.3 + 13.0);
}

// How far to one side the middle line of the body is, `xm` metres behind the snout.
float side_at(float xm) {
	float s = xm / joint;
	float reach = LENGTH * (0.01 - 0.035 * s + 0.085 * s * s);
	return sway * reach * sin(6.2831853 * (phase - s * joint / (LENGTH * wave)));
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
	// The mouth pushes forward (and the upper lip lifts) as it opens: all of it ahead of the hinge.
	if ((part < 0.5 || part > 6.5) && xm < jaw_to) {
		float w = 1.0 - smoothstep(0.3 * jaw_to, jaw_to, xm);
		v.z -= g * PROTRUDE * w;
		v.y += g * LIFT * w * step(part, 0.5);
		xm = v.z + HALF;
	}
	if (part > 6.5) {
		// The lower jaw swings down about its hinge; its end inside the head stays where it is.
		float a = g * GAPE_OPEN * (1.0 - smoothstep(0.55 * jaw_to, 0.97 * jaw_to, xm));
		float ca = cos(a);
		float sa = sin(a);
		vec2 d = vec2(v.y - hinge_y, xm - jaw_to);
		v.y = hinge_y + d.x * ca + d.y * sa;
		v.z = jaw_to - HALF + d.y * ca - d.x * sa;
		NORMAL = vec3(NORMAL.x, NORMAL.y * ca + NORMAL.z * sa, NORMAL.z * ca - NORMAL.y * sa);
		xm = v.z + HALF;
	}
	// The fins billow: a wave that runs out from root to edge, most on the tail.
	if (part > 0.5 && part < 5.5) {
		float t = UV.x;
		float amount = billow * (part > 2.5 && part < 3.5 ? 1.0 : 0.3) * (0.4 + 0.6 * min(sway, 1.5));
		float flow = sin(6.2831853 * (phase - 0.75 * t - 0.25 * UV.y));
		v.x += amount * LENGTH * 0.05 * pow(t, 1.5) * flow;
		v.y -= amount * LENGTH * 0.012 * t * t * (0.5 + 0.5 * flow);
	}
	// (the tail, behind its hinge, is carried round with the wrist)
	float zc = min(xm, joint);
	float h = side_at(zc);
	float slope = (side_at(zc + 0.0005) - side_at(zc - 0.0005)) / 0.001;
	float turn = atan(slope) * (1.0 + 0.25 * smoothstep(0.85 * joint, joint, zc));
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

// The colour of the skin (and the fins' roots) at a place: the base colour, its patches and speckles.
vec4 coat(vec3 p, float high) {
	vec3 c = base;
	float plain = 1.0;
	float field = fbm3(p * 70.0 + vec3(3.0, 1.0, 5.0)) + patch_on_back * 0.35 * (high - 0.5);
	float edge = 1.0 - patch_amount;
	float in_patch = smoothstep(0.43 + 0.3 * edge - 0.03, 0.43 + 0.3 * edge + 0.03, field) * step(0.001, patch_amount);
	c = mix(c, patch, in_patch);
	plain -= in_patch;
	float dark = fbm3(p * 95.0 + vec3(11.0, 4.0, 2.0));
	float in_black = smoothstep(0.73 - 0.3 * black_amount - 0.03, 0.73 - 0.3 * black_amount + 0.03, dark) * step(0.001, black_amount);
	c = mix(c, black, in_black);
	plain *= 1.0 - in_black;
	float specks = noise3(p * 900.0);
	c = mix(c, black, smoothstep(0.86 - 0.12 * speckle, 0.9 - 0.12 * speckle, specks) * step(0.001, speckle) * smoothstep(0.3, 0.7, noise3(p * 160.0 + 2.0)));
	return vec4(c, max(plain, 0.0));
}

void fragment() {
	int p = int(part + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	vec3 c;
	float rough = 0.4;
	float spec = 0.5;
	if (p == 0 || p == 7) {
		float xm = rest.z + HALF;
		float q = UV.y * 2.0 - 1.0;
		vec4 coated = coat(rest, UV.y);
		c = coated.rgb;
		// The back a deeper shade, the belly paler (where the base shows; patches keep their own colour).
		c = mix(c, back, smoothstep(0.3, 1.0, q) * 0.65 * coated.a);
		c = mix(c, belly, (1.0 - smoothstep(-0.8, -0.15, q)) * 0.75 * coated.a);
		// The scales: large, in rows that step half a scale from one to the next, each a little brighter or
		// duller than its neighbours, its rear edge a darker arc. Not on the head.
		float behind = xm - (gill_at - 18.0 * (rest.y - 0.002) * (rest.y - 0.002));
		float arc = acos(clamp(q, -1.0, 1.0)) * 0.018;
		float row = floor(arc / 0.0028);
		float along = xm / 0.0031 + 0.5 * mod(row, 2.0);
		vec2 f = vec2(fract(along), fract(arc / 0.0028));
		float rim = smoothstep(0.7, 0.96, length(vec2(f.x, (f.y - 0.5) * 1.2)));
		float foil = hash3(vec3(floor(along), row, 1.0));
		float scaled = smoothstep(0.0, 0.003, behind) * (1.0 - smoothstep(body_to - 0.012, body_to - 0.004, xm));
		c *= 1.0 + scaled * scales_show * (0.12 * (foil - 0.5) * shine - 0.2 * rim);
		// (metallic scales light up where the light glances off them)
		c += c * 0.45 * shine * glance * glance;
		// The head: the gill cover's edge, a crease; the nostril, a small dark pit ahead of the eye.
		float cover = (1.0 - smoothstep(0.0, 0.0006, abs(behind))) * smoothstep(-0.95, -0.7, q) * (1.0 - smoothstep(0.5, 0.75, q));
		c = mix(c, c * 0.55, cover * 0.7);
		float nostril = length(vec2(xm - (eye_at.x - 0.0062), rest.y - (eye_at.y + 0.0018)));
		c = mix(c, c * 0.35, 1.0 - smoothstep(0.0005, 0.0009, nostril));
		rough = mix(0.5, 0.25, shine);
		spec = mix(0.35, 0.7, shine);
		// The inside of the mouth.
		c = mix(c, mouth_inside, inside);
		rough = mix(rough, 0.8, inside);
		spec = mix(spec, 0.2, inside);
	} else if (p >= 1 && p <= 5) {
		// The fins: the coat's colour at the root fading out to the edge colour, clearer towards the edge,
		// with fine rays; the tail's rays fork and run long.
		float ray_count = p == 3 ? 26.0 : (p == 1 ? 16.0 : 10.0);
		float ray = pow(abs(cos(3.14159265 * UV.y * ray_count)), 8.0);
		vec3 root = mix(fin_root, coat(rest, 0.5).rgb, 0.6);
		c = mix(root, fin_edge, smoothstep(0.05, 0.8, UV.x));
		c = mix(c, c * 0.72, ray * 0.4 * smoothstep(0.05, 0.3, UV.x));
		c = mix(c, water, fin_clear * smoothstep(0.2, 1.0, UV.x));
		c += c * 0.25 * shine * glance;
		rough = 0.5;
		spec = 0.35;
	} else {
		// An eye: a big black pupil, a gold iris, a dark rim.
		float r = UV.x;
		float round_it = atan(rest.y - eye_at.y, rest.z + HALF - eye_at.x);
		vec3 ring = iris * (0.75 + 0.25 * noise3(vec3(round_it * 3.0, r * 3.0, 0.0)));
		c = mix(vec3(0.004, 0.004, 0.006), ring, smoothstep(0.52, 0.58, r));
		c = mix(c, base * 0.5, smoothstep(0.86, 1.0, r) * 0.8);
		rough = 0.12;
		spec = 0.65;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
