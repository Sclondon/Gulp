shader_type spatial;
render_mode cull_disabled;
// Red mangroves, drawn a tree (or root cluster) at a time by MangroveStand's MultiMeshes (the pieces are
// models/mangrove_*.glb; tools/build_mangrove.py says what their UVs and vertex colours hold). In each piece's own
// space y = 0 is the waterline:
// - wood (trunk, limbs, roots) is smooth reddish-brown bark above the water, a dark tide stain just over it, and
//   below it a crust (by vertex colour) of oysters and barnacles near the surface and algae fuzz deeper;
// - the canopy's clumps and leaf cards stir a little (from where they are in the world and `water_clock`), the cards
//   cut into sprays of thick oval leaves (discard: no blending), glossy dark green above and paler below;
// - pods hang green, browning to the tip; fallen leaves float yellow just under the surface or lie brown on the mud.
// Nothing here needs more than GL Compatibility has.

// Seconds, set by the game (a global shader uniform: Project Settings > Shader Globals, or
// RenderingServer.global_shader_parameter_add; MangroveStand adds and runs one if there is none).
global uniform float water_clock;

// How much the canopy stirs (0 still).
uniform float stir = 1.0;
// How thickly barnacles stud the crust (0 none).
uniform float barnacles = 1.0;

uniform vec3 bark : source_color = vec3(0.4, 0.22, 0.14);
uniform vec3 bark_stain : source_color = vec3(0.2, 0.13, 0.09);
uniform vec3 crust_oyster : source_color = vec3(0.5, 0.47, 0.4);
uniform vec3 crust_algae : source_color = vec3(0.24, 0.3, 0.13);
uniform vec3 barnacle : source_color = vec3(0.82, 0.8, 0.72);
uniform vec3 root_tip : source_color = vec3(0.7, 0.58, 0.38);
uniform vec3 leaf_top : source_color = vec3(0.09, 0.22, 0.05);
uniform vec3 leaf_under : source_color = vec3(0.27, 0.36, 0.12);
uniform vec3 leaf_clump : source_color = vec3(0.04, 0.11, 0.03);
uniform vec3 pod : source_color = vec3(0.24, 0.36, 0.11);
uniform vec3 pod_tip : source_color = vec3(0.36, 0.22, 0.1);
uniform vec3 leaf_fallen : source_color = vec3(0.72, 0.6, 0.16);
uniform vec3 leaf_rotting : source_color = vec3(0.26, 0.17, 0.08);

varying vec3 v_local;
varying float v_part;
varying float v_own;
varying vec3 v_mask;

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash13(i), hash13(i + vec3(1, 0, 0)), f.x), mix(hash13(i + vec3(0, 1, 0)), hash13(i + vec3(1, 1, 0)), f.x), f.y),
			mix(mix(hash13(i + vec3(0, 0, 1)), hash13(i + vec3(1, 0, 1)), f.x), mix(hash13(i + vec3(0, 1, 1)), hash13(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

// How far inside one oval leaf `q` is (> 0 inside), the leaf leaving the middle along `dir`.
float leaf(vec2 q, vec2 dir, float long, float wide) {
	float along = dot(q, dir);
	float across = dot(q, vec2(-dir.y, dir.x));
	float a = (along - long * 0.55) / (long * 0.5);
	float b = across / wide;
	return 1.0 - (a * a + b * b);
}

void vertex() {
	v_local = VERTEX;
	v_part = UV2.x;
	v_own = fract(UV2.y + INSTANCE_CUSTOM.x);
	v_mask = COLOR.rgb;
	if (v_part > 0.5 && v_part < 3.5) {
		vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		float t = water_clock;
		// (clumps stir a little, cards more and flutter, pods swing from their stalks)
		float weight = v_part < 1.5 ? 0.5 : (v_part < 2.5 ? 1.0 : UV.y * 1.4);
		vec3 gust = vec3(sin(t * 1.3 + world.x * 0.35 + world.z * 0.21),
				0.4 * sin(t * 2.1 + world.y * 1.7 + world.x * 0.5),
				sin(t * 1.07 + world.z * 0.37 - world.x * 0.15));
		VERTEX += gust * 0.035 * stir * weight;
		if (v_part > 1.5 && v_part < 2.5) {
			VERTEX += NORMAL * sin(t * 3.7 + v_own * 40.0 + world.y * 3.0) * 0.025 * stir;
		}
	}
}

void fragment() {
	vec3 colour = bark;
	float rough = 0.85;
	float spec = 0.25;
	if (v_part < 0.5) {
		// Bark: fine streaks along the wood, a stain just over the waterline.
		float grain = noise3(v_local * vec3(11.0, 3.0, 11.0));
		colour = bark * (0.78 + 0.4 * grain);
		colour = mix(colour, bark_stain, smoothstep(0.7, 0.05, v_local.y) * 0.8);
		// The crust: oysters and barnacles near the surface, algae fuzz deeper, mottled.
		float crust = clamp(v_mask.r, 0.0, 1.0);
		float mottle = noise3(v_local * 7.0);
		float fuzz = noise3(v_local * 31.0);
		vec3 crusted = mix(crust_oyster * (0.75 + 0.5 * mottle), crust_algae * (0.7 + 0.6 * fuzz), clamp(v_mask.g + (mottle - 0.5) * 0.6, 0.0, 1.0));
		// Barnacles: little pale rings, thickest a little under the waterline.
		vec3 g = v_local * 24.0;
		vec3 cell = floor(g);
		vec3 off = vec3(hash13(cell + 3.1), hash13(cell + 7.7), hash13(cell + 1.9)) - 0.5;
		float d = length(fract(g) - 0.5 - off * 0.35);
		float many = mix(0.04, 0.42, smoothstep(-1.8, -0.25, v_local.y)) * barnacles;
		float shell = smoothstep(0.3, 0.24, d) * step(hash13(cell), many);
		// (a low white cone, a dark slit at its top)
		vec3 cone = barnacle * mix(0.35, mix(1.0, 0.7, smoothstep(0.1, 0.26, d)), smoothstep(0.04, 0.08, d));
		crusted = mix(crusted, cone, shell * (1.0 - v_mask.g * 0.6));
		colour = mix(colour, crusted, crust);
		rough = mix(0.75, 0.95, crust);
		// The hanging roots' pale growing tips.
		colour = mix(colour, root_tip, clamp(v_mask.b, 0.0, 1.0));
	} else if (v_part < 1.5) {
		// A clump: a dark mass of leaves, lighter here and there.
		float n = noise3(v_local * 6.0);
		float bits = smoothstep(0.55, 0.75, noise3(v_local * 17.0 + v_own * 10.0));
		colour = leaf_clump * (0.75 + 0.5 * n);
		colour = mix(colour, leaf_top * 0.8, bits * 0.5);
		// (its facets hidden: the normal turned about by noise, so it is lit as a rough mass)
		vec3 wob = vec3(noise3(v_local * 5.0), noise3(v_local * 5.0 + 17.0), noise3(v_local * 5.0 + 31.0)) - 0.5;
		NORMAL = normalize(NORMAL + (VIEW_MATRIX * vec4(wob * 1.6, 0.0)).xyz);
		rough = 1.0;
		spec = 0.05;
	} else if (v_part < 2.5) {
		// A card: nine twig tips (three by three), each a fan of five thick oval leaves pointing
		// more or less one way (opposite pairs up a short twig), each leaf its own shade.
		vec2 uv = UV * 3.0;
		vec2 cellid = floor(uv);
		float seed = hash13(vec3(cellid, v_own * 91.0));
		vec2 q = (fract(uv) - 0.5) * 2.0 + (vec2(hash13(vec3(cellid, seed * 7.0)), hash13(vec3(seed * 5.0, cellid))) - 0.5) * 0.35;
		float turn = seed * 6.2832;
		float inside = -1.0;
		float rib = 1.0;
		float along_best = 0.0;
		float shade = 1.0;
		for (int k = 0; k < 5; k++) {
			float fk = float(k);
			float a = turn + (fk - 2.0) * 0.78 + sin(seed * 40.0 + fk * 2.3) * 0.22;
			vec2 dir = vec2(cos(a), sin(a));
			// (the leaves leave the twig a little way along it, not all from one point)
			vec2 at = q + vec2(cos(turn), sin(turn)) * (0.12 * abs(fk - 2.0) - 0.2);
			float long = 0.72 + 0.14 * sin(seed * 17.0 + fk * 3.0);
			float here = leaf(at, dir, long, 0.2);
			if (here > inside) {
				inside = here;
				rib = abs(dot(at, vec2(-dir.y, dir.x)));
				along_best = dot(at, dir) / long;
				shade = 0.8 + 0.4 * fract(seed * 13.0 + fk * 0.37);
			}
		}
		if (inside < 0.0) {
			discard;
		}
		colour = FRONT_FACING ? leaf_top : leaf_under;
		colour *= shade * (0.85 + 0.25 * along_best);
		colour *= mix(0.78, 1.0, smoothstep(0.0, 0.035, rib));
		rough = FRONT_FACING ? 0.55 : 0.8;
		spec = 0.3;
	} else if (v_part < 3.5) {
		// A pod: green, browning towards its tip.
		colour = mix(pod, pod_tip, smoothstep(0.55, 1.0, UV.y));
		colour *= 0.85 + 0.3 * noise3(v_local * 40.0);
		rough = 0.5;
	} else {
		// A fallen leaf: one oval, yellow on the water, brown on the mud.
		vec2 q = (UV - 0.5) * 2.0;
		if (q.x * q.x + q.y * q.y > 1.0) {
			discard;
		}
		colour = v_part < 4.5 ? mix(leaf_fallen, leaf_top, v_own * 0.5) : leaf_rotting * (0.8 + 0.4 * v_own);
		colour *= mix(0.8, 1.0, smoothstep(0.0, 0.06, abs(q.y)));
		rough = 0.6;
	}
	ALBEDO = colour;
	ROUGHNESS = rough;
	SPECULAR = spec;
}
