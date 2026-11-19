shader_type spatial;
// The sea's mythical creatures (SeaMyth: Mermaid, Hippocampus, DeepSpawn): one shader for all of
// them, so a game that shows all three compiles one program, not three. Each creature's script sets
// the numbers that make it itself (where its joints are, how it swims, its patterns); its colours
// are in its model (vertex colours). Nothing is drawn from texture files.
//
// What each point is comes from the model (creatures/sea_myth/tools/myth_build.py): UV2.y its part
// (0 body, 1 jaw, 2 limb, 3 strand, 4 tentacle, 5 upright fin, 6 flat fin, 7 eye, 8 kelpie weed),
// UV2.x how far out along its part (0 root, 1 tip); UV a pattern place (on a body's skin x metres
// along, y round it: 0 its back, 0.25 its right, 0.5 its belly, 0.75 its left; on a fin x leading
// to trailing edge, y root to edge; on a strand or tentacle x along it, y its own number);
// COLOR.rgb its colour, COLOR.a where its pattern (scales, or lights) is drawn.
//
// Everything that moves is a function of `phase` alone (0..1 through one beat), so a picture of it
// loops exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// --- How far through a beat (0..1, it wraps); in a beat its tail beats `tail_beats` times, its
// limbs stroke `limb_beats` times, its strands sway `strand_beats` times, its fins ripple
// `fin_beats` times (whole numbers, so it loops).
uniform float phase = 0.0;
uniform float tail_beats = 2.0;
uniform float limb_beats = 1.0;
uniform float strand_beats = 1.0;
uniform float fin_beats = 2.0;

// --- The body's wave. Where its nose is (z, metres) and how long it is, which way it beats (0 from
// side to side as a fish, 1 up and down as a dolphin), from how far back (0..1 of its length) the
// wave grows, how far its tail tip goes (metres, at sway 1), how long the wave is (body lengths), how
// far the head swings the other way (a fish's recoil, metres).
uniform float nose_z = -1.0;
uniform float body_len = 2.0;
uniform float wave_axis = 0.0;
uniform float wave_from = 0.3;
uniform float wave_amp = 0.12;
uniform float wave_len = 1.1;
uniform float recoil = 0.0;
// How widely it swims (0 still, 1 cruising, 2 hard).
uniform float sway = 1.0;
// Bent round to one side behind `curl_from` (radians at its tail; more than 0 the tail comes round
// to +X), and up or down about its middle (radians at each end: more than 0 both ends up).
uniform float curl = 0.0;
uniform float curl_from = 0.25;
uniform float arch = 0.0;

// --- The jaw: 0 shut, 1 wide open; where it hinges (y, z) and how far it opens (radians).
uniform float gape = 0.0;
uniform vec2 jaw_hinge = vec2(0.0, 0.0);
uniform float gape_max = 0.5;

// --- The limbs (arms, forelegs), as on its right side (the left is its mirror): its shoulder and
// its elbow (or knee), how far along the limb (UV2.x) the elbow is; how far the limb swings about
// the shoulder and bends at the elbow (radians either way of its pose in the model; more than 0
// swings it back), how far the bend lags the swing and the left limb the right (in strokes).
uniform vec3 shoulder = vec3(0.2, 0.0, -0.5);
uniform vec3 elbow = vec3(0.25, -0.1, -0.3);
uniform float elbow_w = 0.5;
uniform float limb_swing = 0.3;
uniform float limb_bend = 0.3;
uniform float limb_lag = 0.2;
uniform float limb_off = 0.0;
uniform float limb_rest = 0.0;

// --- Strands (hair, a mane, weed) sway this far at their tips (metres); tentacles writhe this far
// and spread this far out from the mouth (at `mouth_xy`) as it opens.
uniform float strand_amp = 0.06;
uniform float tent_amp = 0.05;
uniform float tent_spread = 0.1;
uniform vec2 mouth_xy = vec2(0.0, 0.0);
// Fins ripple this far at their edges (metres).
uniform float fin_amp = 0.02;

// --- The kelpie's look (Hippocampus): 0 not (its weed folded away), 1 the kelpie: darker, draped.
uniform float kelpie = 0.0;
uniform vec3 kelpie_tint : source_color = vec3(0.5, 0.56, 0.45);

// --- Its looks. Scales where COLOR.a says (how strongly, how long each is along the body in
// metres, how many round it); lights where COLOR.a says (how strongly they glow, how far apart
// along, how many rows round, their colour); a sheen at its outline; mottling over its skin; how
// shiny its skin is; rays on its fins (how many).
uniform float scales = 0.0;
uniform float scale_size = 0.05;
uniform float scale_round = 24.0;
uniform float spots = 0.0;
uniform float spot_size = 0.06;
uniform float spot_round = 14.0;
uniform vec3 glow_col : source_color = vec3(0.55, 0.85, 1.0);
uniform float rim = 0.0;
uniform vec3 rim_col : source_color = vec3(0.7, 0.85, 0.9);
uniform float mottle = 0.15;
uniform float rough = 0.55;
uniform float fin_rays = 9.0;

varying vec3 rest;
varying float part;
varying float along;

float hash2(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float n000 = hash2(i.xy + i.z * 17.0);
	float n100 = hash2(i.xy + vec2(1.0, 0.0) + i.z * 17.0);
	float n010 = hash2(i.xy + vec2(0.0, 1.0) + i.z * 17.0);
	float n110 = hash2(i.xy + vec2(1.0, 1.0) + i.z * 17.0);
	float n001 = hash2(i.xy + (i.z + 1.0) * 17.0);
	float n101 = hash2(i.xy + vec2(1.0, 0.0) + (i.z + 1.0) * 17.0);
	float n011 = hash2(i.xy + vec2(0.0, 1.0) + (i.z + 1.0) * 17.0);
	float n111 = hash2(i.xy + vec2(1.0, 1.0) + (i.z + 1.0) * 17.0);
	return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y), mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}

// Turns a point and its normal about an axis parallel to X through a pivot (y, z): more than 0
// swings what is below the pivot backwards (+Z).
void turn_x(inout vec3 v, inout vec3 n, vec2 pivot, float a) {
	float c = cos(a);
	float s = sin(a);
	vec2 d = v.yz - pivot;
	v.yz = pivot + vec2(d.x * c + d.y * s, d.y * c - d.x * s);
	n.yz = vec2(n.y * c + n.z * s, n.z * c - n.y * s);
}

// How far the body's line is moved at s (0 nose, 1 tail) by its wave, and its slope (per metre).
float wave_at(float s) {
	float grow = pow(smoothstep(wave_from, 1.0, s), 1.4);
	float head = recoil * (1.0 - smoothstep(0.0, wave_from + 0.1, s));
	float ph = TAU * (phase * tail_beats - s / wave_len);
	return sway * (wave_amp * grow * sin(ph) - head * sin(TAU * phase * tail_beats));
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	along = UV2.x;
	rest = VERTEX;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	int p = int(part + 0.5);
	float w = UV2.x;
	float side = v.x >= 0.0 ? 1.0 : -1.0;
	if (p == 1) {
		turn_x(v, n, jaw_hinge, gape_max * clamp(gape, 0.0, 1.0));
	} else if (p == 2) {
		// A limb: the bend at the elbow first (below it only), then the swing at the shoulder.
		float stroke = TAU * (phase * limb_beats + (side < 0.0 ? limb_off : 0.0));
		float swing = limb_rest + limb_swing * sway * sin(stroke);
		float bend = limb_bend * sway * (0.5 + 0.5 * sin(stroke - TAU * limb_lag));
		float below = smoothstep(elbow_w - 0.08, elbow_w + 0.08, w);
		turn_x(v, n, elbow.yz, bend * below);
		turn_x(v, n, shoulder.yz, swing);
	} else if (p == 3 || p == 8) {
		float seed = UV.y;
		float ph = TAU * (phase * strand_beats + seed) - w * 4.0;
		float reach = strand_amp * pow(w, 1.5) * (0.6 + 0.6 * sway);
		v += vec3(sin(ph), 0.6 * cos(ph * 1.0 + seed * 3.0), 0.25 * sin(ph * 0.5)) * reach;
	} else if (p == 4) {
		float seed = UV.y;
		float ph = TAU * (phase * strand_beats * 2.0 + seed) - w * 6.0;
		float reach = tent_amp * pow(w, 1.2);
		v.xy += vec2(sin(ph), cos(ph * 0.8 + seed * 5.0)) * reach;
		vec2 away = rest.xy - mouth_xy;
		float r = length(away);
		v.xy += (r > 0.0001 ? away / r : vec2(0.0, 1.0)) * gape * tent_spread * w;
		v.z += gape * tent_spread * 0.6 * w;
	} else if (p == 5 || p == 6) {
		float ph = TAU * phase * fin_beats - UV.x * 2.5 - rest.z * 4.0;
		float reach = fin_amp * w * (0.5 + 0.5 * sway) * sin(ph);
		if (p == 5) {
			v.x += reach;
		} else {
			v.y += reach;
		}
	}
	// The body's wave, by how far back the point is (from where it is in the still model).
	float s = clamp((rest.z - nose_z) / body_len, 0.0, 1.0);
	float d = wave_at(s);
	float slope = (wave_at(min(s + 0.01, 1.0)) - wave_at(max(s - 0.01, 0.0))) / (0.02 * body_len);
	if (wave_axis < 0.5) {
		v.x += d;
		n.z -= slope * n.x;
	} else {
		v.y += d;
		n.z -= slope * n.y;
	}
	// Bent up or down about its middle, and round to one side behind its head.
	float zr = rest.z - (nose_z + 0.5 * body_len);
	v.y += arch * zr * zr / body_len;
	n.z -= 2.0 * arch * zr / body_len * n.y;
	float back = (1.0 - curl_from) * body_len;
	float t = max(rest.z - (nose_z + curl_from * body_len), 0.0);
	v.x += curl * t * t / (2.0 * back);
	n.z -= curl * t / back * n.x;
	// The kelpie's weed: folded away to nothing (every point of it in one place) in the other look.
	if (p == 8 && kelpie < 0.5) {
		v = vec3(0.0);
	}
	VERTEX = v;
	NORMAL = normalize(n);
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

