// Water, in a flat, painted style: matte colour, clear close to and solid far off, faint pale
// lines wandering over it and drifts of flat white foam. Its colour goes from shallow to deep with how much
// water there really is under each pixel, a rim of foam forms wherever something breaks the
// surface (banks, rocks, ramps, the fish), patches of foam drift with the current, and waterfalls
// turn to white water.
//
// The waves are real: the mesh is fine enough (a few metres to a square) to be lifted into a
// swell, a sum of four trains of waves of different lengths crossing one another, and the
// light falls on the slope of that swell worked out at every pixel, so that it is smooth
// however coarse the mesh. track.gd works out the same swell (swell_y) to float things on it.
//
// Every stage can set any of these from its entry in levels.gd: a key "water_<name>" sets the
// uniform <name>.
shader_type spatial;
// (Gulp: depth_draw_always: a wave's near face hides its far side, which is drawn in the same mesh
// with no order between them; without it the far side's underside showed through every tall wave)
render_mode cull_disabled, specular_schlick_ggx, depth_draw_always;

#include "res://shaders/psx_common.gdshaderinc"
// (Gulp: the surf along the shores and the rogue wave, scripts/surf.gd; the mesh follows the eye, so
// every place on the water is worked out from the world, not from the mesh's UVs)
#include "res://shaders/surf.gdshaderinc"


group_uniforms colour;
uniform vec4 deep : source_color = vec4(0.03, 0.30, 0.36, 1.0);
uniform vec4 shallow : source_color = vec4(0.16, 0.70, 0.64, 1.0);
uniform vec4 foam_color : source_color = vec4(0.92, 1.0, 0.96, 1.0);
// Metres of water before it reaches its deep colour.
uniform float depth_range = 5.0;
// How solid the water looks where it is shallow and where it is deep (1 hides what is under it).
uniform float alpha_shallow : hint_range(0.0, 1.0) = 0.6;
uniform float alpha_deep : hint_range(0.0, 1.0) = 0.93;
// How much the surface colour varies in ripples.
uniform float colour_ripple : hint_range(0.0, 1.0) = 0.08;
// Looked straight down into, water is paler than looked across: how much (0 is no
// difference, 1 is as pale as the shallows).
uniform float view_clear : hint_range(0.0, 1.0) = 0.35;

group_uniforms foam;
// Foam is three separate things, each with its own settings: PATCHES that drift down a river
// with the current (and gather along its banks, in rapids and round whatever breaks the
// surface); WHITECAPS, drifts of flat foam lying on open water; and CREST FOAM, which rides
// the tops of the swell. All three are cut from the same grey picture, foam_texture, which
// wraps round at its edges: where it is bright there is foam. (Made by
// scripts/tools/bake_foam.gd; any picture that wraps will do. With none set there is no foam.)
uniform sampler2D foam_texture : repeat_enable, filter_linear, hint_default_black;
// Patches: how much (0 is none), how small (bigger number, smaller patches), and how fast
// they drift (1 is with the current).
uniform float foam_amount : hint_range(0.0, 3.0) = 0.18;
uniform float foam_scale : hint_range(0.02, 20.0) = 1.0;
uniform float foam_speed : hint_range(0.0, 6.0) = 1.0;
// Extra patches along a river's banks and in rapids.
uniform float edge_foam : hint_range(0.0, 3.0) = 0.35;
uniform float rapid_foam : hint_range(0.0, 3.0) = 0.5;
// The rim of foam round anything that breaks the surface: how wide (metres), and how ragged.
uniform float rim_width : hint_range(0.0, 10.0) = 0.45;
uniform float rim_ragged : hint_range(0.0, 1.0) = 0.5;

group_uniforms whitecaps;
// Whitecaps: how much of the water has flat white foam lying on it (0 is none), and how many
// metres of water one copy of the foam picture covers (bigger number, bigger pieces).
uniform float whitecaps : hint_range(0.0, 2.0) = 0.3;
uniform float whitecap_size : hint_range(0.5, 300.0) = 22.0;
// They gather into drifts with clear water between: how strongly (0 is evenly spread), and
// how big the drifts are (metres).
uniform float whitecap_clump : hint_range(0.0, 3.0) = 0.8;
uniform float whitecap_clump_size : hint_range(2.0, 400.0) = 45.0;

group_uniforms crest_foam;
// Foam on the tops of the swell, coming and going as each wave passes: how far down from
// the top it reaches (0 is none, 1 is half the wave), how many metres one copy of the foam
// picture covers, and how broken its edge is (0 is a clean line along the crest).
uniform float crest_amount : hint_range(0.0, 2.0) = 0.0;
uniform float crest_size : hint_range(0.5, 300.0) = 14.0;
uniform float crest_ragged : hint_range(0.0, 3.0) = 0.6;

group_uniforms motion;
uniform float flow = 0.6;
// The swell. How rough the stage's water is (open sea is rougher than a river: set from the
// stage), then how high its biggest wave is for each 1 of that (metres), how long (metres:
// rougher water has longer waves as well), and how fast it travels (1 is as real waves do).
uniform float swell = 1.0;
uniform float swell_height : hint_range(0.0, 1.0) = 0.18;
uniform float swell_length : hint_range(2.0, 60.0) = 12.0;
uniform float swell_speed : hint_range(0.0, 4.0) = 1.0;
// (The swell keeps time by water_clock, seconds since the stage was made: a setting of the
// whole project, sent every frame by track.gd, which keeps the same time for its own copy.)
global uniform float water_clock;

group_uniforms surface;
// The surface is lit as real water is: a smooth, shiny skin of small waves that mirrors the
// sky and catches the sun. How rough it is (0 is a mirror), and how strongly it reflects.
uniform float roughness : hint_range(0.0, 1.0) = 0.5;
uniform float specular : hint_range(0.0, 1.0) = 0.12;
// Stylised: how strongly faint pale lines are drawn wandering over the surface.
uniform float lines : hint_range(0.0, 1.0) = 0.6;
// The small waves that give it its shape: how fine they are, how steep, how peaked their
// crests are, and how fast they move.
uniform float ripple_scale : hint_range(0.005, 20.0) = 0.55;
uniform float ripple_height : hint_range(0.0, 20.0) = 0.16;
uniform float ripple_choppy : hint_range(0.1, 12.0) = 1.4;
uniform float ripple_speed : hint_range(0.0, 20.0) = 1.0;
// Blocky light: the shape the light falls on is worked out once for each square of this many
// pixels of the picture, so that the glints off the water come in squares, like the pixels
// of the picture only bigger. (0 or 1 is smooth.)
uniform float glint_pixels : hint_range(0.0, 32.0) = 0.0;
// Rain on the water (0 is none): little rings that open out and are gone, where drops land.
uniform float rain : hint_range(0.0, 1.0) = 0.0;
// How far across the water UV.x runs from 0 to 1, in metres (set from the stage).
uniform float across = 22.0;

group_uniforms wake;
// The salmon's trail, oldest first: (where across, as UV.x; metres along; seconds ago, or -1
// for a break in it). Set every frame by fx/wake.gd.
uniform vec3 wake_pts[24];
uniform int wake_count = 0;
// The stretch of water (metres along) the trail lies in: nothing outside it is looked at.
uniform vec2 wake_span = vec2(0.0, 0.0);
// How long the wake lasts (s), how fast its arms move apart (m/s), and how wide they get (m).
uniform float wake_life = 0.45;
uniform float wake_spread : hint_range(0.0, 20.0) = 2.4;
uniform float wake_width : hint_range(0.0, 6.0) = 0.4;
// The arms snake from side to side together, as a tail beats: how far (m), and how long each
// bend is (m).
uniform float wake_wiggle : hint_range(0.0, 3.0) = 0.0;
uniform float wake_wiggle_length : hint_range(0.2, 20.0) = 2.5;
// How broken the edges of its foam are (0 is clean bands), and how much of each arm is
// missing in gaps along its length (0 is none).
uniform float wake_ragged : hint_range(0.0, 1.0) = 0.5;
uniform float wake_dashes : hint_range(0.0, 1.0) = 0.0;
// Froth churned up down the middle, straight behind the fish (0 is none).
uniform float wake_churn : hint_range(0.0, 1.0) = 0.0;
// A second, thinner pair of arms outside the first (0 is none).
uniform float wake_echo : hint_range(0.0, 1.0) = 0.0;
// How much paler and flatter the water is between the arms.
uniform float wake_calm : hint_range(0.0, 1.0) = 0.3;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest, repeat_disable;

varying vec3 v_world;

varying float v_steep;
// where this is on the water in metres (across from the middle, along), and how much of
// the swell there is here (none far out to sea)
varying vec2 v_metres;
varying float v_swell;
// the surf here (Surf.wave: height, push, phase, wave height; breaking, steepness, wavenumber,
// weight), which way it runs, and where this water was before the waves moved it
varying vec4 v_surf_a;
varying vec4 v_surf_b;
varying vec2 v_surf_way;
varying vec2 v_at;

// A random number from 0 to 1 for each corner of a grid. It is worked out in whole numbers,
// so that a corner gets the same number whichever square of the grid asks for it. (The usual
// fract(sin(...)) does not: the desktop renderer works out "this corner plus one" a hair
// differently from "the next corner", the number comes out quite different, and every square
// of the noise shows as a block with a seam round it.)
float hash(vec2 p) {
	ivec2 c = ivec2(round(p));
	uint h = uint(c.x) * 668265261u ^ (uint(c.y) * 374761393u);
	h ^= h >> 15u;
	h *= 2246822519u;
	h ^= h >> 13u;
	h *= 3266489917u;
	h ^= h >> 16u;
	return float(h) / 4294967295.0;
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
			mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

// Smooth noise for anything whose slope is looked at (the shape of the waves): a slope at
// each corner of a grid, blended so that neither the height nor its slope nor its curve
// jumps from one square to the next. (vnoise above is only smooth in height: light glancing
// off waves made from it shows up every square of its grid.) From 0 to 1, like vnoise.
vec2 slope_at(vec2 corner) {
	float a = hash(corner) * 6.2831853;
	return vec2(cos(a), sin(a));
}

float gnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
	float a = dot(slope_at(i), f);
	float b = dot(slope_at(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0));
	float c = dot(slope_at(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0));
	float d = dot(slope_at(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0));
	return 0.5 + 0.7 * mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// Distance from the camera (metres) of a depth-buffer value at a point on screen.
float view_depth(vec2 screen_uv, float depth, mat4 inv_projection) {
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(screen_uv, depth) * 2.0 - 1.0;
#else
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, depth);
#endif
	vec4 view = inv_projection * vec4(ndc, 1.0);
	return -view.z / view.w;
}

// One layer of ripples: smooth humps, peaked the more the choppier.
float ripples_of(vec2 p) {
	return pow(clamp(gnoise(p), 0.0, 1.0), ripple_choppy);
}

// The height of the small waves at a point on the water (metres across, metres along):
// three layers of smooth humps, each finer than the last, each turned a different way and
// each drifting its own way, so that nothing in them lines up or comes round again. (They
// were once trains of straight waves crossing one another, which is a criss-cross: a grid.)
float wave_h(vec2 p) {
	float t = TIME * ripple_speed;
	p *= ripple_scale;
	float h = ripples_of(p * 0.33 + vec2(t * 0.17, t * 0.11)) * 1.5;
	p = vec2(p.x * 0.8 - p.y * 0.6, p.x * 0.6 + p.y * 0.8);
	h += ripples_of(p * 0.71 + vec2(-t * 0.23, t * 0.19) + 13.0) * 0.8;
	p = vec2(p.x * 0.8 - p.y * 0.6, p.x * 0.6 + p.y * 0.8);
	h += ripples_of(p * 1.57 + vec2(t * 0.31, -t * 0.37) + 31.0) * 0.4;
	return h;
}

// The swell at a point on the water (metres across, metres along): its height, and its slope
// each way. Four trains of waves, each shorter and lower than the last and running its own
// way; the long ones travel faster, as real waves do. (track.gd has the same sum: SWELLS.)
vec3 swell_at(vec2 p) {
	const vec4 trains[4] = vec4[4](
			vec4(0.34, -0.94, 1.0, 1.0),
			vec4(-0.78, -0.62, 0.62, 0.55),
			vec4(0.97, 0.26, 0.37, 0.3),
			vec4(-0.57, 0.82, 0.23, 0.16));
	float long = swell_length * (0.4 + 0.6 * swell);
	float high = swell_height * swell;
	vec3 sum = vec3(0.0);
	for (int i = 0; i < 4; i++) {
		float k = 6.2831853 / (long * trains[i].z);
		float phase = k * dot(trains[i].xy, p) - sqrt(9.8 * k) * swell_speed * water_clock + float(i) * 1.7;
		float a = high * trains[i].w;
		sum.x += a * sin(phase);
		sum.yz += trains[i].xy * (a * k * cos(phase));
	}
	return sum;
}

// (Gulp) The water's surface over an undisplaced point (world x, z): its place (world x, z, and y from
// the still surface), with the surf and the rogue wave; in `level` what the breakers ride on (the
// swell and the rogue wave). The water mesh and the breakers' sheets both draw from it.
vec3 surface_at(vec2 still, float fine, float swelling, vec3 eye, out vec4 wa, out vec4 wb, out vec2 way, out float level) {
	surf_wave(still, water_clock, shore_at(still), wa, wb);
	way = wb.w > 0.0 ? shore_way(still) : vec2(0.0);
	vec2 r_slope;
	vec2 r_shape;
	vec4 r = rogue_at(still, r_slope, r_shape);
	level = swell_at(vec2(still.x, 200.0 - still.y)).x * swelling * (1.0 - 0.6 * wb.w) + r.x;
	// (no sideways push where a breaker's sheet stands for the water, nor up to the line where it takes
	// over, on either side of it: there the sheet draws the shape by height alone, and the two meet)
	float sheet = max(shore_zone(still) * (1.0 - step(breaker_seen, length(still - eye.xz))), rogue_zone(still));
	float pushed = 1.0 - smoothstep(0.0, 0.5, sheet);
	vec2 xz = still + (way * wa.y * fine + rogue_a.zw * r.y) * pushed;
	return vec3(xz.x, level + wa.x * fine, xz.y);
}

// (the surf's shape only where the mesh is fine enough for it: near the eye; its foam goes on
// further, worked out at every pixel)
float fine_at(vec2 still, vec3 eye) {
	return 1.0 - smoothstep(45.0, 80.0, length(still - eye.xz));
}

// A point of a breaker's section (scripts/breakers.gd, Breakers.point): v is how far down the section
// (0 the back end out at sea, 1 the front end at the shore). The section stands at `base`, running in
// along `way`; for the rogue wave, `base` and `way` are its own. Its place (world x, z; y from the still
// surface); in `info` the weight of the breaking shape, the stage, the lip, inside; `still` the water it
// stands for.
vec3 breaker_point(vec2 base, vec2 way, float line_d, float tb, float site_h, float fade, float v, bool rogue, vec3 eye,
		out vec2 still, out vec4 info, out vec4 wa, out vec4 wb, out vec2 sway, out float t_piece, out vec3 sect) {
	float hh;
	float stage;
	float sc;
	float dc;
	float win;
	if (rogue) {
		// (the rogue wave: its crest goes on along its way; it curls as it grows to its highest)
		float grow = pow(sin(3.14159265 * clamp(rogue_b.x / rogue_c.z, 0.0, 1.0)), 1.5);
		hh = rogue_c.w * grow * fade / 0.85;
		stage = (rogue_b.x / rogue_c.z - breaker_rogue.x) / breaker_rogue.y;
		win = breaker_rogue.z * rogue_c.x;
		// (here "s" and "d" are metres along its way from the crest, the crest at 0: d runs against it)
		sc = 0.0;
		dc = 0.0;
	} else {
		vec3 cr = breaker_crest(base, way, line_d, water_clock);
		hh = site_h * (0.92 + 0.18 * sin(cr.z * 0.27 + 1.0)) / 1.1;
		stage = (cr.y - tb) / breaker_a.x;
		sc = cr.x;
		dc = surf_d(sc);
		win = breaker_a.w * surf_a.y;
	}
	float d;
	vec4 b = vec4(0.0);
	float wd = 0.0;
	info = vec4(0.0, stage, 0.0, 0.0);
	// (sect.x: how much this section carries a barrel wave, from well before its face stands up, so the
	// shoulder still to break is glassy too, to the white water settling)
	sect = vec3(smoothstep(-1.2, -0.2, stage) * (1.0 - smoothstep(1.2, 1.5, stage)) * fade, hh, 0.0);
	t_piece = v < breaker_b.z ? 0.0 : 1.0;
	if (v < breaker_b.z) {
		float f = v / breaker_b.z;
		d = rogue ? mix(win, breaker_b.x * hh, f) : surf_d(mix(sc + win, surf_s(dc + breaker_b.x * hh), f));
	} else if (v > breaker_b.w) {
		float f = (v - breaker_b.w) / (1.0 - breaker_b.w);
		d = rogue ? mix(-breaker_b.y * hh, -win, f) : surf_d(mix(surf_s(max(dc - breaker_b.y * hh, 0.25)), max(sc - win, surf_s(0.25)), f));
	} else {
		t_piece = (v - breaker_b.z) / (breaker_b.w - breaker_b.z);
		b = breaker_shape(t_piece, max(stage, 0.0));
		d = dc - b.x * hh;
		wd = breaker_piece_weight(t_piece) * breaker_stage_weight(stage) * fade;
		info = vec4(wd, stage, b.z, b.w);
	}
	still = base + (line_d - d) * way;
	// (how near the crest this water is, a wave's length either side: its glassy water and clear underside)
	sect.z = 1.0 - smoothstep(0.35, 0.6, rogue ? abs(d) / win : abs(surf_s(d) - sc) / surf_a.y * (d < dc ? 0.6 : 1.0));
	float fine = fine_at(still, eye);
	wd *= fine;
	info.x = wd;
	float level;
	vec3 g = surface_at(still, fine, 1.0, eye, wa, wb, sway, level);
	if (rogue && wd > 0.0) {
		// (the rogue wave's breaking shape stands in for its own hump, not on top of it)
		vec2 r_slope;
		vec2 r_shape;
		level -= rogue_at(still, r_slope, r_shape).x;
	}
	vec3 bp = vec3(still.x, level + b.y * hh, still.y);
	return vec3(g.x, mix(g.y, bp.y, wd), g.z);
}

// (Gulp) which mesh this is: 0 the water's rings, 1 a shore breaker's sheet, 2 the rogue wave's sheet
varying float v_kind;
// a breaker: the weight of its breaking shape (0 where it is the plain water), its stage, lip, inside
varying vec4 v_brk;
// a breaker: where along the coast (m) and how far down its breaking piece (0..1), for its foam
varying vec2 v_brk_uv;
// a breaker: how much its section is breaking now, and how high this point is (in its wave's heights)
varying vec3 v_sect;
// a breaker: which way its air side faces (world), worked out from the shape itself, so that which side is
// seen does not hang on the winding of its triangles (a thin fold at a strip's end can twist one)
varying vec3 v_air;

void vertex() {
	// (Gulp: a breaker's sheet, scripts/breakers.gd: its sections' points are worked out here, from the
	// water's sums and the breaking profile)
	if (CUSTOM0.w > 5.0) {
		bool rogue = CUSTOM0.w > 8.0;
		vec2 base;
		vec2 way;
		float line_d;
		float fade = UV.y;
		if (rogue) {
			way = rogue_a.zw;
			vec2 side = vec2(-way.y, way.x);
			float side_off = CUSTOM0.x;
			base = rogue_a.xy + way * rogue_b.y * max(rogue_b.x, 0.0) + side * side_off;
			line_d = 0.0;
			fade = exp(-pow(side_off / rogue_c.y, 2.0)) * smoothstep(0.7, 1.0, 1.0 - abs(side_off) / (1.4 * rogue_c.y) + 0.7);
		} else {
			base = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
			way = UV2;
			line_d = CUSTOM0.x;
		}
		float v = UV.x;
		vec2 still;
		vec4 info;
		vec4 wa;
		vec4 wb;
		vec2 sway;
		float tp;
		vec3 sect;
		vec3 sc2;
		vec3 p = breaker_point(base, way, line_d, CUSTOM0.y, CUSTOM0.z, fade, v, rogue, CAMERA_POSITION_WORLD, still, info, wa, wb, sway, tp, sect);
		// (its facing from the next point down the section: the air on the left going in to the shore)
		float dv = (v < 0.999 ? 0.5 : -0.5) / (breaker_points - 1.0);
		vec2 s2;
		vec4 i2;
		vec4 a2;
		vec4 b2;
		vec2 w2;
		float t2;
		vec3 q = breaker_point(base, way, line_d, CUSTOM0.y, CUSTOM0.z, fade, v + dv, rogue, CAMERA_POSITION_WORLD, s2, i2, a2, b2, w2, t2, sc2);
		vec3 run = (q - p) * sign(dv);
		vec3 n = vec3(0.0, 1.0, 0.0);
		vec2 prof = vec2(dot(run.xz, way), run.y);
		if (length(prof) > 0.00001) {
			prof = normalize(prof);
			n = normalize(vec3(-prof.y * way.x, prof.x, -prof.y * way.y));
		}
		float bend = smoothstep(0.0, 0.25, info.x);
		NORMAL = normalize(mix(vec3(0.0, 1.0, 0.0), n, bend));
		v_air = NORMAL;
		vec3 x_way = vec3(1.0, 0.0, 0.0) - NORMAL * NORMAL.x;
		TANGENT = length(x_way) > 0.1 ? normalize(x_way) : normalize(vec3(0.0, 0.0, 1.0) - NORMAL * NORMAL.z);
		BINORMAL = normalize(cross(NORMAL, TANGENT));
		v_kind = rogue ? 2.0 : 1.0;
		v_brk = info;
		v_brk_uv = vec2(dot(base, vec2(-way.y, way.x)), tp);
		v_sect = vec3(sect.x, p.y / max(sect.y, 0.1), sect.z);
		v_at = still;
		UV = vec2(0.5 + still.x / 26.8, 200.0 - still.y);
		UV2 = vec2(still.x, 1.0);
		v_metres = vec2(still.x, UV.y);
		v_steep = 0.0;
		v_swell = 1.0;
		v_surf_a = wa;
		v_surf_b = wb;
		v_surf_way = sway;
		VERTEX = vec3(p.x, p.y, p.z) - vec3(MODEL_MATRIX[3].x, 0.0, MODEL_MATRIX[3].z);
		v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		POSITION = psx_snap(PROJECTION_MATRIX * MODELVIEW_MATRIX * vec4(VERTEX, 1.0), VIEWPORT_SIZE);
	} else {
	// (Gulp: the mesh goes with the eye: its places on the water come from the world, mapped as the
	// old fixed 400 m mesh's UVs were, so the swell and the foam lie as they did)
	vec3 still = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	UV = vec2(0.5 + still.x / 26.8, 200.0 - still.z);
	UV2 = vec2(still.x, 1.0);
	v_at = still.xz;
	v_steep = 1.0 - clamp(NORMAL.y, 0.0, 1.0);
	v_metres = vec2(UV2.x, UV.y);
	// (none on a waterfall, and none far out to sea, where the mesh is too coarse to bend)
	v_swell = UV2.y * (1.0 - smoothstep(0.1, 0.4, v_steep));
	vec4 wa;
	vec4 wb;
	vec2 sway;
	float level;
	vec3 p = surface_at(still.xz, fine_at(still.xz, CAMERA_POSITION_WORLD), v_swell, CAMERA_POSITION_WORLD, wa, wb, sway, level);
	v_surf_a = wa;
	v_surf_b = wb;
	v_surf_way = sway;
	v_kind = 0.0;
	v_brk = vec4(0.0);
	v_brk_uv = vec2(0.0);
	v_sect = vec3(0.0);
	v_air = vec3(0.0, 1.0, 0.0);
	VERTEX.y += p.y;
	VERTEX.xz += p.xz - still.xz;
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	POSITION = psx_snap(PROJECTION_MATRIX * MODELVIEW_MATRIX * vec4(VERTEX, 1.0), VIEWPORT_SIZE);
	}
}

void fragment() {
	// (Gulp: the water mesh gives way to the breakers' sheets where they stand for it, and the sheets are
	// cut away everywhere else: the two meet along one line of one surface. scripts/breakers.gd)
	float sheet_near = 1.0 - step(breaker_seen, length(v_at - CAMERA_POSITION_WORLD.xz));
	float z_shore = shore_zone(v_at) * sheet_near;
	float z_rogue = rogue_zone(v_at);
	if (v_kind < 0.5) {
		if (z_shore > 0.5 || z_rogue > 0.5) {
			discard;
		}
	} else if (v_kind < 1.5) {
		if (z_shore <= 0.5) {
			discard;
		}
	} else if (z_rogue <= 0.5) {
		discard;
	}
	// (how much of a breaker's own shape there is here: its facing is the mesh's, not the sums')
	float brk_bend = smoothstep(0.0, 0.25, v_brk.x);
	// how much water lies between the surface here and whatever is behind it
	float behind = view_depth(SCREEN_UV, texture(depth_texture, SCREEN_UV).r, INV_PROJECTION_MATRIX);
	float surface = view_depth(SCREEN_UV, FRAGCOORD.z, INV_PROJECTION_MATRIX);
	float water = max(behind - surface, 0.0);
	float depth = clamp(water / depth_range, 0.0, 1.0);

	vec2 p = vec2(v_metres.x * 0.37, UV.y * 0.18 - TIME * flow * 3.0 * foam_speed) * foam_scale;
	float n = smoothstep(0.25, 0.75, texture(foam_texture, p * 0.13).r * 0.6 + texture(foam_texture, p.yx * 0.29 + 0.37).r * 0.4);

	// drifting patches, thicker along the banks (vertex green marks open water, which has
	// none) and in rapids (vertex red)
	float edge = smoothstep(0.36, 0.5, abs(UV.x - 0.5)) * (1.0 - COLOR.g);
	// (a hair over 1 with everything at 0, so that then there is none at all)
	float patches = step(1.001 - foam_amount * 0.5 - edge * edge_foam * 0.6 - COLOR.r * rapid_foam * 0.3, n) * (1.0 - smoothstep(0.2, 0.8, v_surf_b.w));
	// the rim: a hard band wherever the water is only this deep, with a ragged outer edge
	float rim = step(water, rim_width * (1.0 - rim_ragged * 0.8 * (1.0 - n))) * step(0.0001, rim_width);
	float fall = smoothstep(0.35, 0.6, v_steep);
	float streak = step(0.45, vnoise(vec2(UV.x * 40.0, UV.y * 0.5 - TIME * 12.0 * sign(flow))));
	float white = max(max(patches * 0.85, rim), fall * (0.55 + 0.45 * streak));

	// The swell here: its height, and its slope each way.
	vec3 rise = swell_at(v_metres);
	float crest = clamp(rise.x / max(swell_height * swell * 1.4, 0.001), -1.0, 1.0) * v_swell;
	vec3 to_eye = CAMERA_POSITION_WORLD - v_world;
	float far = length(to_eye);
	// looked straight down into, water is paler than looked across
	float tone = depth * (1.0 - view_clear * clamp(to_eye.y / max(far, 0.001), 0.0, 1.0));
	vec3 col = mix(shallow.rgb, deep.rgb, tone);
	// (and a crest is a little paler than a trough)
	col = mix(col, shallow.rgb, max(crest, 0.0) * 0.18);
	// (the colour varies in soft patches: made from the smooth noise, or its grid shows)
	float tint = gnoise(p * 0.7) * 0.6 + gnoise(p * 1.6 + 7.0) * 0.4;
	col = mix(col, shallow.rgb, (tint - 0.5) * 2.0 * colour_ripple * (0.4 + 0.6 * depth));
	col = mix(col, foam_color.rgb, white);
	// The shape of the surface: the slope of the small waves here, turned into a normal, so
	// that the light and the sky are reflected off each one as off real water. (The slope is
	// measured a short step each way; the step is longer the bigger the waves are set, or it
	// would be too short to measure at all.)
	// (in metres across the course, not by the mapping, which is not the same size out to sea)
	vec2 at = vec2(v_metres.x, UV.y - TIME * flow * 2.0);
	// (blocky light: every pixel of a square of the picture takes its shape from the middle
	// of that square. Where that is on the water is reckoned from how the water runs across
	// the screen just here.)
	vec2 shape_at = at;
	vec2 swell_slope = rise.yz;
	if (glint_pixels > 1.0) {
		vec2 to_middle = (floor(FRAGCOORD.xy / glint_pixels) + 0.5) * glint_pixels - FRAGCOORD.xy;
		vec2 shift = dFdx(v_metres) * to_middle.x + dFdy(v_metres) * to_middle.y;
		shape_at += shift;
		swell_slope = swell_at(v_metres + shift).yz;
	}
	float eps = (0.06 + far * 0.003) * 0.55 / max(ripple_scale, 0.005);
	float h0 = wave_h(shape_at);
	float slope_x = (wave_h(shape_at + vec2(eps, 0.0)) - h0) / eps;
	float slope_y = (wave_h(shape_at + vec2(0.0, eps)) - h0) / eps;
	// The salmon's wake is part of the water: two bands of foam that open out behind it into
	// a V, with the water between them churned flat, so that the waves do not run on through
	// it. (The salmon's trail comes in as a string of points: where it was across the water,
	// how far along, and how long ago.)
	float wake_foam = 0.0;
	float wake_flat = 0.0;
	float wake_froth = 0.0;
	vec2 here = vec2((UV.x - 0.5) * across, UV.y);
	if (wake_count > 1 && here.y > wake_span.x && here.y < wake_span.y) {
		// (gaps along the arms, and the bends of the wiggle, stay where they are on the water)
		float gap = step(wake_dashes, fract(here.y / 1.3));
		float bend = wake_wiggle * sin(here.y * 6.2831853 / max(wake_wiggle_length, 0.05));
		for (int i = 0; i < wake_count - 1; i++) {
			vec3 a = wake_pts[i];
			vec3 b = wake_pts[i + 1];
			if (a.z < 0.0 || b.z < 0.0) {
				continue;
			}
			vec2 pa = vec2((a.x - 0.5) * across, a.y);
			vec2 ab = vec2((b.x - 0.5) * across, b.y) - pa;
			// (only the water beside this stretch of the trail, not round its ends)
			float t = dot(here - pa, ab) / max(dot(ab, ab), 0.0001);
			if (t < -0.04 || t > 1.04) {
				continue;
			}
			vec2 off = here - (pa + ab * t);
			float age = mix(a.z, b.z, t);
			float k = clamp(age / wake_life, 0.0, 1.0);
			// (the wiggle pushes one arm out as it pulls the other in, so the two snake together;
			// none of it right at the fish)
			float side = sign(ab.x * off.y - ab.y * off.x);
			float d = max(length(off) - side * bend * smoothstep(0.0, 0.15, age), 0.0);
			// each arm moves out from the middle as it ages, widens, and fades
			float inner = 0.26 + wake_spread * age * (1.0 - 0.3 * k);
			float wide = wake_width * smoothstep(0.0, 0.12, age) * (1.0 - 0.45 * k) + 0.06;
			float fade = pow(1.0 - k, 1.3);
			float arm = smoothstep(inner - 0.1, inner, d) * (1.0 - smoothstep(inner + wide * 0.35, inner + wide, d));
			// (a second pair, further out, thinner and fainter)
			float outer = inner * 1.75 + 0.3;
			float echo = smoothstep(outer - 0.1, outer, d) * (1.0 - smoothstep(outer + wide * 0.2, outer + wide * 0.55, d));
			wake_foam = max(wake_foam, max(arm, echo * wake_echo * 0.85) * fade * gap);
			wake_flat = max(wake_flat, (1.0 - smoothstep(inner * 0.7, inner + wide, d)) * fade);
			wake_froth = max(wake_froth, (1.0 - smoothstep(0.0, 0.2 + inner * 0.55, d)) * fade);
		}
	}
	// (its foam has a ragged edge, like the rest; the froth down the middle is all ragged)
	float wake_white = step(0.4, wake_foam * mix(1.0, 2.0 * n, wake_ragged));
	wake_white = max(wake_white, step(1.0 - wake_churn * 0.75, wake_froth * (0.25 + n)) * step(0.001, wake_churn));
	white = max(white, wake_white);
	col = mix(col, shallow.rgb, wake_flat * wake_calm * (1.0 - white));
	col = mix(col, foam_color.rgb, wake_white);
	// Whitecaps: foam lying on the water in flat white pieces with ragged edges, gathered into
	// drifts with clear water between them. (None far off, where they would only be specks,
	// nor in the wake.) They are cut from the foam picture, laid twice at two sizes so that
	// it is not seen to repeat; a slow, smooth noise gathers them into drifts.
	float near = (1.0 - fall) * (1.0 - smoothstep(150.0, 340.0, far)) * (1.0 - wake_flat);
	vec2 fuv = at / max(whitecap_size, 0.01);
	float sheet = texture(foam_texture, fuv).r * 0.65 + texture(foam_texture, fuv.yx * 2.63 + vec2(0.31, 0.17)).r * 0.35;
	float drift = gnoise(at / max(whitecap_clump_size, 0.01) + 20.0);
	float cap = step(mix(1.02, 0.6, whitecaps), sheet + (drift - 0.5) * whitecap_clump) * step(0.001, whitecaps);
	// Crest foam: on the tops of the swell, wherever the water stands this near the top of
	// its highest wave, with an edge broken by the foam picture. It comes up with each crest
	// and is gone when the crest has passed.
	vec2 cuv = at / max(crest_size, 0.01);
	float broken = texture(foam_texture, cuv + vec2(0.53, 0.11)).r * 0.6 + texture(foam_texture, cuv.yx * 2.2 + vec2(0.07, 0.61)).r * 0.4;
	float top = step(1.0 - crest_amount * 0.5, crest + (broken - 0.5) * crest_ragged) * step(0.001, crest_amount) * step(0.001, v_swell);
	// (none in the surf, which has foam of its own)
	cap = max(cap, top) * near * (1.0 - smoothstep(0.2, 0.8, v_surf_b.w));
	white = max(white, cap);
	col = mix(col, foam_color.rgb, cap);
	// The surf (scripts/surf.gd). The faces of the shoaling waves glow green where they stand up, the
	// water inside the break is churned a sandy green, and the foam comes three ways, each in flat
	// painted pieces like the rest: on a crest steep enough to break, where the surface folds over
	// itself (its Jacobian, 1 - steepness x sin(phase), falls towards 0); the roller down the face of
	// a breaking crest; and the whitewater each broken wave leaves behind it, thinning into lace.
	// (The surf's colours are dimmed with the water's own at night.)
	float lit_water = length(shallow.rgb) / 0.646;
	vec2 surf_slope = vec2(0.0);
	float surf_thick = 0.0;
	if (v_surf_b.w > 0.001) {
		float sw = v_surf_b.w;
		float up = sin(v_surf_a.z);
		float fold = 1.0 - v_surf_b.y * up;
		surf_slope = v_surf_way * (v_surf_a.w * v_surf_b.z * cos(v_surf_a.z) / max(fold, 0.3)) * sw;
		// (how far through the wave's period this water is since its crest went by: 0 to 1)
		float since = fract((1.5707963 - v_surf_a.z) / 6.2831853);
		// (its foam pattern is laid along the crests, drawn out along them, and drifts in with the waves)
		vec2 fp = v_at - v_surf_way * water_clock * 0.25;
		vec2 fl = vec2(dot(fp, v_surf_way), dot(fp, vec2(-v_surf_way.y, v_surf_way.x)));
		float fn = texture(foam_texture, fl * vec2(0.17, 0.1)).r * 0.6 + texture(foam_texture, fl * vec2(0.4, 0.22) + 0.41).r * 0.4;
		// (how far the shoaling has gone: the wave's height over the most the depth here can carry,
		// McCowan's 0.78; it breaks from 0.85 and is broken water, a bore, from 1.4)
		float ratio = v_surf_b.x;
		float brk = smoothstep(0.85, 1.25, ratio);
		float gone = smoothstep(1.2, 1.8, ratio);
		col = mix(col, surf_sandy.rgb * lit_water, sw * brk * 0.5);
		// (the surf is green-teal and thick with stirred sand, not the open blue: the waves read as bodies of water)
		col = mix(col, surf_body.rgb * lit_water, sw * 0.65);
		surf_thick = sw * smoothstep(0.25, 1.2, water);
		// (crests paler, troughs darker, so the swell reads from above the water as well as by its light)
		col *= mix(1.0, mix(0.72, 1.18, up * 0.5 + 0.5), sw);
		// (the face of a wave standing up to break glows green, lit through)
		col = mix(col, surf_glow.rgb * lit_water, sw * smoothstep(0.3, 0.75, v_surf_b.y) * smoothstep(-0.2, 0.8, up) * smoothstep(0.55, 0.95, since + up * 0.3) * 0.8 * (1.0 - gone));
		// the lip: the top of a crest that folds over (its Jacobian falls towards 0) goes white
		float lip = smoothstep(0.45, 0.1, fold) * brk;
		// the bore: broken, the wave rolls in as white water down its front, and leaves it behind
		float bore = gone * (smoothstep(0.55, 0.9, since) + exp(-since * 4.0));
		float trail = brk * exp(-since * 1.6);
		float lace = brk * (1.0 - smoothstep(0.03, 0.09, abs(fn - 0.5))) * (0.35 + 0.65 * exp(-since * 1.2));
		// (and a broken white line along the top of each wave as it stands up to break)
		float crest_line = smoothstep(0.9, 0.985, up) * smoothstep(0.4, 0.75, v_surf_b.y) * (1.0 - brk * 0.6);
		float surf_white = max(step(0.5, lip * (0.6 + 0.8 * fn)), step(0.5, bore * (0.45 + 0.9 * fn)));
		surf_white = max(surf_white, step(0.55, trail * (0.3 + 1.1 * fn)));
		// (inside the break the water is a blanket of foam with holes in it)
		surf_white = max(surf_white, step(0.6, gone * (0.2 + 0.9 * fn)));
		surf_white = max(surf_white, step(0.5, crest_line * (0.35 + 0.9 * fn)));
		surf_white = max(surf_white, step(0.45, lace)) * step(0.3, sw) * (1.0 - fall);
		// (Gulp: none of it on a breaker's own shape, which has its own foam below)
		surf_white *= 1.0 - brk_bend;
		// (and round a breaking barrel the water ahead of it is glassy, as in barrel photographs: the last
		// wave's foam is left further in)
		surf_white *= 1.0 - 0.95 * v_sect.x * v_sect.z;
		white = max(white, surf_white);
		col = mix(col, foam_color.rgb, surf_white);
	}
	// The rogue wave: its face goes dark as it stands up; foam on its breaking crest, streaking down
	// its face, and a broad band left behind it.
	vec2 r_slope;
	vec2 r_shape;
	vec4 rg = rogue_at(v_at, r_slope, r_shape);
	float rogue_face = 0.0;
	if (r_shape.y > 0.01) {
		float an = r_shape.x;
		float crest_n = sech2(an);
		// (its face a dark glassy green-blue wall, lighter towards the lip, where the light comes through)
		float face = r_shape.y * rg.w * smoothstep(0.1, 0.6, crest_n) * smoothstep(-0.4, 0.2, an);
		col = mix(col, mix(deep.rgb * 0.55, surf_body.rgb * lit_water * 0.9, smoothstep(0.5, 0.95, crest_n)), face * 0.85);
		rogue_face = face;
		float rn = texture(foam_texture, vec2(dot(v_at, rogue_a.zw) * 0.05, dot(v_at, vec2(-rogue_a.w, rogue_a.z)) * 0.2)).r;
		float rn2 = texture(foam_texture, v_at * 0.11 + 0.3).r;
		float on_top = rg.z * smoothstep(0.86, 0.97, crest_n) * smoothstep(-0.5, -0.1, an);
		float streak = rg.z * step(0.0, an) * smoothstep(0.12, 0.55, crest_n) * step(0.7, rn);
		float left = rg.z * step(an, -0.6) * exp((an + 0.6) * 0.3);
		float rogue_white = max(step(0.5, on_top * (0.45 + rn2)), max(streak, step(0.6, left * (0.3 + rn2))));
		white = max(white, rogue_white);
		col = mix(col, foam_color.rgb, rogue_white);
	}
	// (Gulp) A breaker (scripts/breakers.gd): the body of a standing wave is green-teal; its thin lip
	// glows green with the light through it, most when the eye looks towards the sun; the inside of the
	// tube is darker, with pale streaks running up its face; foam feathers along the lip's edge as it
	// throws, the curtain goes white where the lip lands, and then it is all white water.
	float brk_glow = 0.0;
	float brk_white = 0.0;
	if (v_brk.x > 0.001) {
		float wd = v_brk.x;
		float st = v_brk.y;
		float thin = v_brk.z;
		float inside = v_brk.w;
		vec2 bu = vec2(v_brk_uv.x * 0.22, v_brk_uv.y * 3.0 - st * 0.4);
		float bn = texture(foam_texture, bu).r * 0.6 + texture(foam_texture, bu * vec2(2.3, 1.7) + 0.37).r * 0.4;
		// (the body: deep green-blue at the foot of the face, rising to a lit green near the top, as in the
		// concept and barrel photographs)
		float up_k = smoothstep(0.0, 0.95, v_sect.y);
		vec3 body = mix(breaker_tube.rgb * 1.3, mix(surf_body.rgb, breaker_lip.rgb, 0.5), up_k) * lit_water;
		col = mix(col, body, wd * 0.85);
		// (its back, seen from out at sea: painted streaks running up it, as in the concept, and the top lit
		// through where the crest thins)
		float back_k = (1.0 - smoothstep(0.28, 0.36, v_brk_uv.y)) * wd;
		float back_streak = smoothstep(0.55, 0.72, texture(foam_texture, vec2(v_brk_uv.x * 0.3, v_brk_uv.y * 0.22 + 0.13)).r);
		col = mix(col, col * 1.3 + breaker_lip.rgb * lit_water * 0.08, back_streak * back_k * 0.45);
		col = mix(col, breaker_lip.rgb * lit_water * 0.85, back_k * smoothstep(0.75, 1.05, v_sect.y) * 0.35);
		// (inside: darker towards the back of the tube, the face streaked with the light coming up it)
		float streaks = smoothstep(0.55, 0.75, texture(foam_texture, vec2(v_brk_uv.x * 0.6, v_brk_uv.y * 0.35 + st * 0.15)).r);
		col = mix(col, breaker_tube.rgb * lit_water, inside * wd * 0.8);
		col = mix(col, surf_glow.rgb * lit_water * 0.8, inside * wd * streaks * 0.2 * (1.0 - smoothstep(0.9, 1.05, st)));
		vec3 to_frag = normalize(v_world - CAMERA_POSITION_WORLD);
		float towards_sun = pow(max(dot(to_frag, normalize(breaker_sun)), 0.0), 2.0);
		brk_glow = wd * smoothstep(0.1, 0.7, thin) * smoothstep(0.0, 0.25, st) * (1.0 - smoothstep(0.9, 1.1, st)) * (0.6 + 0.4 * towards_sun);
		col = mix(col, breaker_lip.rgb * lit_water, brk_glow);
		// (second round: the foam is painted in two tones, a pale lit aqua and white, in strokes broken along
		// the lip by a big slow blotch as well as the fine one, never one hard white line; white water is
		// shaded by the sun on its own shape, so a collapsing mound reads as a heap and not a flat sheet)
		float blotch = texture(foam_texture, vec2(v_brk_uv.x * 0.06 + 0.31, v_brk_uv.y * 0.9 + st * 0.12)).r;
		float lit_side = clamp(dot(normalize(v_air), normalize(breaker_sun)) * 0.5 + 0.5, 0.0, 1.0);
		vec3 foam_lit = mix(breaker_foam_shade.rgb, foam_color.rgb, smoothstep(0.25, 0.8, lit_side)) * lit_water;
		vec3 foam_pale = mix(breaker_lip.rgb, foam_color.rgb, 0.55) * lit_water;
		// the lip's edge feathering as it pitches: a soft pale band, white strokes in it here and there
		float edge = smoothstep(0.78, 1.0, thin) * smoothstep(0.12, 0.38, st) * (1.0 - smoothstep(0.98, 1.08, st));
		float feather = edge * (0.25 + 0.75 * bn) * (0.55 + 0.9 * blotch);
		float pale = smoothstep(0.32, 0.55, feather);
		float stroke = step(0.72, feather);
		// the curtain: white streaks pouring down the falling lip; then the landing and the white water
		float curtain = smoothstep(0.78, 0.97, st) * smoothstep(0.6, 0.95, thin);
		float pour = texture(foam_texture, vec2(v_brk_uv.x * 0.8, v_brk_uv.y * 0.5 + st * 0.6)).r;
		// (the white water: from the landing forward and over the collapsing crest, not down its back, which
		// stays green with a little foam; broken into heaps and holes)
		float ahead = smoothstep(0.3, 0.42, v_brk_uv.y) * (1.0 - smoothstep(0.93, 0.99, v_brk_uv.y));
		// (third pass: none before this section's lip lands, then growing out from where the tip came down, a
		// ragged edge spreading both ways along the piece over the next second or so: foam does not pop up all
		// over the wave at once)
		float since = (st - breaker_contact) * breaker_a.x;
		float spread = (0.03 + 0.42 * since) * (0.7 + 0.6 * bn);
		float grown = step(0.0, since) * (1.0 - smoothstep(spread * 0.75, spread, abs(v_brk_uv.y - 0.529)));
		float crash = grown * smoothstep(0.0, 0.25, since) * (1.0 - 0.35 * inside) * mix(0.25, 1.0, ahead);
		float heap = crash * (0.1 + 0.95 * bn) * (0.45 + 0.85 * blotch);
		pale = max(pale, max(smoothstep(0.4, 0.62, curtain * (0.35 + 0.9 * pour)), smoothstep(0.3, 0.45, heap)));
		stroke = max(stroke, max(step(0.75, curtain * (0.3 + 0.9 * pour) * (0.6 + 0.6 * bn)), step(0.55, heap)));
		pale *= step(0.15, wd);
		stroke *= step(0.15, wd);
		col = mix(col, foam_pale, pale * 0.8);
		col = mix(col, foam_lit, stroke);
		brk_white = max(stroke, pale * 0.6);
		white = max(white, brk_white);
	}
	// and faint pale lines wander over it, like light on the surface
	vec2 lp = at * 0.3 + (vec2(vnoise(at * 0.2 + 1.0), vnoise(at * 0.2 + 7.0)) - 0.5) * 2.0;
	float line = (1.0 - smoothstep(0.0, 0.045, abs(vnoise(lp + vec2(0.0, TIME * 0.12)) - 0.5))) * lines * (1.0 - white)
			* (1.0 - smoothstep(50.0, 160.0, far)) * (1.0 - wake_flat) * (1.0 - brk_bend);
	col = mix(col, mix(col, foam_color.rgb, 0.35), line);
	if (rain > 0.0 && far < 70.0) {
		// one drop, or none, in each square of the water at a time: its ring opens out and fades
		vec2 grid = v_metres / 1.1;
		vec2 sq = floor(grid);
		float when = hash(sq);
		float turn = floor(TIME * 1.6 + when * 7.0);
		float age = fract(TIME * 1.6 + when * 7.0);
		vec2 drop = sq + vec2(0.3 + 0.4 * hash(sq + turn * 3.0), 0.3 + 0.4 * hash(sq + turn * 5.0 + 9.0));
		float ringlet = step(abs(length(grid - drop) - age * 0.36), 0.03) * step(hash(sq + turn), rain * 0.3) * (1.0 - age);
		col = mix(col, foam_color.rgb, ringlet * 0.7 * (1.0 - white) * (1.0 - smoothstep(40.0, 70.0, far)));
	}
	// The water's own two directions in the world, across and along: each corner of the mesh
	// carries them (its tangent), so that they turn smoothly with the course. (They were once
	// worked out from how the surface changes over the screen, which gave every triangle of
	// the mesh directions of its own, and a seam along each of its edges.)
	vec3 across_way = normalize((INV_VIEW_MATRIX * vec4(TANGENT, 0.0)).xyz);
	vec3 along_way = normalize((INV_VIEW_MATRIX * vec4(BINORMAL, 0.0)).xyz);
	vec3 flat_normal = normalize((INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	// (Gulp: a breaker's sheet knows its air side from its shape; the water's rings from their winding)
	bool facing = FRONT_FACING;
	if (v_kind > 0.5) {
		facing = dot(v_air, CAMERA_POSITION_WORLD - v_world) > 0.0;
		flat_normal = normalize(v_air) * (facing ? 1.0 : -1.0);
	}
	// (far off the small waves are smaller than a pixel: they are smoothed away, or they would
	// only be noise; foam is not shiny; and the wake has flattened them. The swell is none
	// of those things: it is the shape of the water itself.)
	// (and in the surf the small ripples give way to the big waves: they hid them)
	float steepness = ripple_height * 0.5 * mix(1.0, 0.12, smoothstep(30.0, 170.0, far)) * (1.0 - white) * (1.0 - 0.85 * wake_flat) * (1.0 - 0.75 * v_surf_b.w);
	// (the surf's and the rogue wave's slopes are in the world's x and z; the water's second way runs to -z)
	vec2 slope = vec2(slope_x, slope_y) * steepness * (1.0 - 0.5 * brk_bend) + (swell_slope * v_swell * (1.0 - 0.6 * v_surf_b.w)
			+ vec2(surf_slope.x + r_slope.x, -(surf_slope.y + r_slope.y))) * (1.0 - brk_bend);
	vec3 wavy = normalize(flat_normal - across_way * slope.x - along_way * slope.y);
	// seen at a low angle water is a mirror, however clear it is seen from above
	float fresnel = pow(1.0 - clamp(dot(wavy, to_eye / max(far, 0.001)), 0.0, 1.0), 5.0);
	ALBEDO = col;
	ALPHA = mix(mix(mix(alpha_shallow, alpha_deep, depth), 1.0, fresnel * 0.9), 0.97, white);
	// (the surf is solid water where it stands thick, clear only in the thin swash)
	ALPHA = mix(ALPHA, 0.94, surf_thick * 0.85);
	ALPHA = mix(ALPHA, 0.97, rogue_face);
	// (a breaker: solid in its body, a little clear in its lit lip, and its lip lit from within)
	ALPHA = mix(ALPHA, 0.95, brk_bend);
	ALPHA = mix(ALPHA, 0.82, brk_glow * (1.0 - brk_white));
	ROUGHNESS = mix(roughness, 0.85, white);
	SPECULAR = specular;
	METALLIC = 0.0;
	EMISSION = foam_color.rgb * fall * 0.15;
	EMISSION += breaker_lip.rgb * lit_water * brk_glow * 0.4;
	// seen from underneath, the surface is a bright ceiling that hides the sky
	// (Gulp: with the eye above the water a back face is the underside of a wave's curling lip or an
	// overhanging wall: drawn as the water it is, not as the bright ceiling seen from under the sea)
	if (!facing && eye_above > 0.5) {
		ALBEDO = mix(col, surf_body.rgb * lit_water * 0.8, 0.5);
		ALPHA = 0.97;
	} else if (!facing) {
		ALBEDO = mix(shallow.rgb, vec3(1.0), 0.2 + 0.4 * white);
		// (Moon Jellies: far off it fades into the dark of the deep water, so that the bright
		// water is a window overhead, as it is to a diver, and has no edge)
		ALPHA = 0.95 * (1.0 - smoothstep(18.0, 60.0, far));
		EMISSION = shallow.rgb * 0.45;
		// (Gulp: under the surf the churned water is a bright white roof, the waves' troughs darker
		// bands between; under a rogue wave the water above goes dark)
		float surf_under = v_surf_b.w * smoothstep(0.85, 1.25, v_surf_b.x);
		ALBEDO = mix(ALBEDO, vec3(1.0), white * surf_under * 0.6) * mix(1.0, 0.75 + 0.25 * sin(v_surf_a.z), v_surf_b.w);
		EMISSION += vec3(0.85, 0.95, 1.0) * white * (0.25 + 0.5 * surf_under);
		EMISSION *= 1.0 - 0.6 * rogue_face;
		// (Gulp: the underside of a breaker seen from under the water: its lip and curtain glow green-white
		// with the light through them; the barrel's body is darker)
		// (second round: the wave's own body from below is lit water, as bright as the surface round it and
		// greener, the lip brightest; under a breaking section the foam roof is mostly taken away, so the
		// curl reads, and what white there is is the curtain and the white water where the lip lands)
		float sect_on = v_sect.x * step(0.5, v_kind);
		ALBEDO = mix(ALBEDO, mix(shallow.rgb, vec3(1.0), 0.2), sect_on * 0.6 * (1.0 - brk_white));
		EMISSION *= 1.0 - 0.5 * sect_on * (1.0 - brk_white);
		// (the thick body a little darker than the surface round it, so its hump shows against the light;
		// the thin lip the brightest thing there, lit through)
		vec3 under_body = mix(mix(shallow.rgb, surf_glow.rgb * lit_water, 0.6) * 0.95, breaker_lip.rgb * lit_water * 1.35, brk_glow);
		ALBEDO = mix(ALBEDO, under_body, brk_bend * (1.0 - brk_white) * 0.85);
		EMISSION = mix(EMISSION, under_body * 1.5, brk_bend * (1.0 - brk_white)) + surf_glow.rgb * lit_water * brk_glow * 0.8;
		ALBEDO = mix(ALBEDO, vec3(1.0), brk_white * 0.7);
		EMISSION += vec3(0.75, 0.85, 0.9) * brk_white * 0.45;
		ALPHA = mix(ALPHA, 0.92, brk_bend);
		// (and the water's surface round a breaking barrel is clearer from below, the tube's floor most, so
		// the lip and the dark inside of the tube over it show through as a curl against the light)
		float tube_floor = smoothstep(0.82, 0.88, v_brk_uv.y) * brk_bend * smoothstep(0.2, 0.45, v_brk.y) * (1.0 - smoothstep(0.95, 1.15, v_brk.y));
		float clear_under = max(v_sect.x * v_sect.z * (1.0 - brk_bend) * step(0.5, v_kind), tube_floor) * (1.0 - brk_white);
		ALPHA = mix(ALPHA, 0.3, clear_under);
		EMISSION *= 1.0 - 0.6 * clear_under;
		ROUGHNESS = 0.9;
	} else {
		NORMAL = normalize((VIEW_MATRIX * vec4(wavy, 0.0)).xyz);
	}
	if (surf_debug > 0) {
		vec3 sd = shore_at(v_at);
		if (surf_debug == 5) {
			// (white, the breaking shape's weight, the glassy water near a breaking crest)
			sd = vec3(white, brk_bend, v_sect.x * v_sect.z);
		}
		if (surf_debug == 4) {
			// (which mesh: the water's rings blue, a shore breaker orange, the rogue's magenta; back faces darker)
			sd = v_kind < 0.5 ? vec3(0.1, 0.3, 1.0) : (v_kind < 1.5 ? vec3(1.0, 0.55, 0.1) : vec3(1.0, 0.2, 0.9));
			ALBEDO = sd * (facing ? 1.0 : 0.35) * (0.6 + 0.4 * brk_bend);
		} else if (surf_debug == 5) {
			ALBEDO = sd;
		} else {
			ALBEDO = surf_debug == 3 ? (facing ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)) : surf_debug == 1 ? vec3(clamp(sd.x / 30.0, 0.0, 1.0), clamp(sd.y / 10.0, 0.0, 1.0), v_surf_b.w) : vec3(v_surf_b.w, v_surf_b.x, fract(v_surf_a.z / 6.2831853));
		}
		ALPHA = 1.0;
		EMISSION = ALBEDO * 0.8;
	}
}
