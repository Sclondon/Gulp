shader_type spatial;
// The ghosts' glow, shared by the ghost whale (ghost_whale.gd) and the ghost fish
// (creatures/ghost_fish/ghost_fish.gd): one shader program for both, so a game that shows both
// compiles one. Pale light added over whatever is behind (no lights, no shadows, no fog: it fades
// out with distance by itself), so a ghost lights the dark water and can be faded right out (`fade`).
//
// What each point is comes from the model (UV2.y the part): 0 a bone, 1 a lower jawbone (it drops
// with `gape`), 2 a shell of mist (UV2.x 0 the inner shell, 1 the outer), 3 a flipper's bone (it
// sculls; UV2.x 0 on the left, +X, 1 on the right), 4 a blade of mist (a flipper's or a fluke's;
// UV.x under 0.5 a flipper's, which sculls with its bones), 5 a halo card (a fish's: UV across it
// 0..1 each way). UV.x how far along the animal (0 the snout, 1 the tail), UV.y along a bone (0..1).
// Bones are closed meshes; the mist's shells and blades too; only the fish's ribs, fins and halo are
// single cards. Everything is drawn from both sides (cull_disabled), the back faces of bones dimmed.
//
// It swims: the whale beats its flukes up and down (`lateral` false), a wave growing down the tail;
// a fish sweeps its tail side to side (`lateral` true). Everything that moves is a function of
// `phase` (or, drawn as a school by a Flock's MultiMesh, `school` true: of each fish's own beat in
// INSTANCE_CUSTOM.x, radians, its effort in .y), so a picture of it loops exactly.
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, fog_disabled;

// How far through a beat (0..1). Set by GhostWhale or GhostFish.
uniform float phase = 0.0;
uniform float tail_beats = 1.0;
// How hard it swims (1 cruising).
uniform float sway = 1.0;
// Its jaws: 0 shut, 1 dropped wide (the whale's).
uniform float gape = 0.0;
// Turning: radians from a third of the way back to the tail (more than 0 the tail comes round to +X).
uniform float curl = 0.0;
// 0 not there at all, 1 fully there: to bring it in at night or in the deep and out again.
uniform float fade : hint_range(0.0, 1.0) = 1.0;
// How brightly it glows (1 as made).
uniform float glow = 1.0;
// How far off (metres) it has faded to nothing, and how far its mist wavers (1 as made).
uniform float far = 70.0;
uniform float waver = 1.0;
uniform vec3 bone_colour : source_color = vec3(0.78, 0.92, 1.0);
uniform vec3 mist_colour : source_color = vec3(0.55, 0.8, 1.0);

// The animal's own numbers (set by its node and its material): its length as built (metres), side
// to side (a fish) or up and down (a whale), how far its tail swings (of its length at the tip), the
// wave's length (body lengths), the hinge of its jaws (metres behind the snout, metres up) and the root
// of its flippers (metres behind the snout, metres up, metres out).
uniform float body_length = 14.0;
uniform bool lateral = false;
uniform float reach = 0.07;
uniform float wave = 1.3;
uniform vec2 jaw_hinge = vec2(3.55, -0.3);
uniform vec3 flipper_root = vec3(4.35, -0.75, 1.0);
// Drawn as a school (a Flock's MultiMesh): each fish's beat and effort from its instance data.
uniform bool school = false;

varying vec3 rest;
varying float part;
varying float layer;
varying float beat_at;

// How far the middle line is moved (up and down, or to the side), `s` along the body (0..1).
float bend_at(float s, float ph, float effort) {
	float a = body_length * reach * (0.1 - 0.4 * s + 0.7 * s * s + 0.6 * s * s * s);
	if (lateral) {
		a = body_length * reach * (0.04 - 0.2 * s + 0.6 * s * s + 0.56 * s * s * s);
	}
	return sway * effort * a * sin(TAU * (tail_beats * ph - s / wave));
}

void vertex() {
	part = UV2.y;
	layer = UV2.x;
	rest = VERTEX;
	int p = int(part + 0.5);
	float ph = phase;
	float effort = 1.0;
	if (school) {
		ph = INSTANCE_CUSTOM.x / TAU;
		effort = clamp(0.6 + 0.4 * INSTANCE_CUSTOM.y, 0.3, 1.6);
	}
	beat_at = ph;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float half_l = body_length * 0.5;
	if (p == 1 && gape > 0.0) {
		// The lower jawbones drop about their hinge.
		vec2 hp = vec2(jaw_hinge.y, jaw_hinge.x - half_l);
		vec2 d = v.yz - hp;
		float a = -0.55 * clamp(gape, 0.0, 1.0) * smoothstep(jaw_hinge.x + 0.1, jaw_hinge.x - 0.6, v.z + half_l);
		float c = cos(a);
		float s = sin(a);
		v.yz = hp + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
	}
	if (p == 3 || (p == 4 && UV.x < 0.5)) {
		// A flipper sculls slowly, up and down about its root.
		float side = v.x >= 0.0 ? 1.0 : -1.0;
		vec2 root = vec2(side * flipper_root.z, flipper_root.y);
		float a = side * sway * 0.2 * sin(TAU * ph + (side > 0.0 ? 0.0 : 0.6));
		vec2 d = v.xy - root;
		float c = cos(a);
		float s = sin(a);
		v.xy = root + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
		n.xy = vec2(n.x * c - n.y * s, n.x * s + n.y * c);
	}
	if (p == 2 || p == 4) {
		// The mist wavers and trails: it billows out and in along waves running back down the body,
		// the outer shell further, more towards the tail, and streams back behind.
		float xm = v.z + half_l;
		float s = xm / body_length;
		float round_a = atan(v.y, v.x);
		float w = sin(TAU * (s * 3.0 - 2.0 * ph) + round_a * 3.0) * 0.55 + sin(TAU * (s * 6.0 - 3.0 * ph) + round_a * 2.0 + 1.7) * 0.35;
		float far_out = (0.035 + 0.05 * layer) * body_length * (0.4 + s) * waver;
		v += n * w * far_out * 0.5;
		v.z += layer * 0.04 * body_length * s * s * waver * (1.2 + 0.4 * sin(TAU * (2.0 * ph - s * 2.0)));
	}
	// Swimming, and turning.
	float s = clamp((v.z + half_l) / body_length, -0.2, 1.3);
	float h = bend_at(s, ph, effort);
	float slope = (bend_at(s + 0.01, ph, effort) - bend_at(s - 0.01, ph, effort)) / (0.02 * body_length);
	float turn = atan(slope);
	float c = cos(turn);
	float sn = sin(turn);
	if (lateral) {
		v = vec3(h + v.x * c, v.y, v.z - v.x * sn);
		n = vec3(n.x * c + n.z * sn, n.y, -n.x * sn + n.z * c);
	} else {
		v = vec3(v.x, h + v.y * c, v.z - v.y * sn);
		n = vec3(n.x, n.y * c + n.z * sn, -n.y * sn + n.z * c);
	}
	float from = -0.2 * body_length;
	float d = v.z - from;
	if (abs(curl) > 0.001 && d > 0.0) {
		float k = curl / (0.7 * body_length);
		float a = d * k;
		float r = 1.0 / k;
		float cc = cos(a);
		float ss = sin(a);
		n = vec3(n.x * cc + n.z * ss, n.y, -n.x * ss + n.z * cc);
		v = vec3(r + (v.x - r) * cc, v.y, from + (r - v.x) * ss);
	}
	VERTEX = v;
	NORMAL = n;
}

void fragment() {
	int p = int(part + 0.5);
	vec3 nrm = FRONT_FACING ? NORMAL : -NORMAL;
	float ndv = clamp(abs(dot(nrm, VIEW)), 0.0, 1.0);
	float light;
	vec3 c;
	if (p == 0 || p == 1 || p == 3) {
		// A bone: a pale glow, brightest where it faces the eye, a soft edge; its far side dim.
		light = mix(0.3, 1.0, pow(ndv, 0.7)) * (FRONT_FACING ? 1.0 : (lateral ? 0.8 : 0.25));
		// (a little brighter at its knobbly ends)
		light *= 0.85 + 0.25 * (1.0 - sin(PI * clamp(UV.y, 0.0, 1.0)));
		c = bone_colour * 0.62;
	} else if (p == 5) {
		// A fish's halo: a soft round glow on a card.
		vec2 q = UV * 2.0 - 1.0;
		float r = clamp(length(q), 0.0, 1.0);
		light = 0.32 * (1.0 - r) * (1.0 - r);
		c = mist_colour;
	} else {
		// The mist: a faint haze, brighter towards its edges as seen (the outline of the body it lost),
		// in wisps that run back down it; the outer shell fainter.
		float xm = rest.z / body_length + 0.5;
		float round_a = atan(rest.y, rest.x);
		float wisps = 0.55 + 0.45 * sin(TAU * (xm * 5.0 - 2.0 * beat_at) + round_a * 4.0) * sin(TAU * (xm * 2.0 + beat_at) + round_a * 2.0 + 0.5);
		float rim = pow(1.0 - ndv, 1.6);
		light = (0.1 + 0.42 * rim) * wisps * (p == 4 ? sin(PI * clamp(UV.y, 0.0, 1.0)) * 1.3 : mix(1.0, 0.55, layer));
		// (thinner towards the tip of the snout and the end of the trail)
		light *= smoothstep(0.0, 0.08, xm) * (1.0 - 0.5 * smoothstep(0.85, 1.05, xm));
		c = mist_colour;
	}
	float away = 1.0 - smoothstep(far * 0.45, far, length(VERTEX));
	ALBEDO = c * light * glow * clamp(fade, 0.0, 1.0) * away;
	ALPHA = 1.0;
}
