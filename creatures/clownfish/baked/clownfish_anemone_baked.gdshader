shader_type spatial;
// The clownfish's host anemone (clownfish_anemone.gd): its tentacles sway in the water and every colour is
// drawn here: no texture files. What each point is comes from the model
// (tools/build_clownfish_anemone.py): COLOR.r the part, as a tenth (0 the column and its foot, 1 the oral
// disc, 2 a tentacle). On the column and the disc UV.x is how far out from the middle (0 the middle, 1 the
// disc's margin, more than 1 down the column's side to its foot), UV.y how far round. On a tentacle UV.x
// is how far along it (0 its root, 1 its tip), UV2 where its root is (x, z, metres, the anemone's own
// space), COLOR.g a number of its own (0..1), COLOR.b how far out on the disc it stands (0 the middle, 1
// the margin). Nothing here needs more than GL Compatibility has. One opaque draw, back faces culled.
//
// The sway runs on the project's global shader uniform `water_clock` (seconds; it must be declared in
// Project Settings > Shader Globals) and on where each tentacle's root is in the world, so neighbouring
// anemones do not sway in step. It has no clock of its own: hold water_clock still and it stands still.
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


global uniform float water_clock;

// How far the tentacles sway (1: their tips about 15 mm either way), and how fast (1 a sway about every
// six seconds).
uniform float sway = 1.0;
uniform float sway_speed = 1.0;
// A steady lean of every tentacle's tip with the current (metres at the tip, in the anemone's own x and z).
uniform vec2 current = vec2(0.0, 0.0);

// The colours: the column (and its foot), the oral disc and its fine lines, the mouth's lips, the
// tentacles at their roots, along them and at their tips.
uniform vec3 column : source_color = vec3(0.62, 0.1, 0.36);
uniform vec3 column_dark : source_color = vec3(0.4, 0.05, 0.24);
uniform vec3 disc : source_color = vec3(0.56, 0.5, 0.28);
uniform vec3 disc_lines : source_color = vec3(0.42, 0.36, 0.2);
uniform vec3 lips : source_color = vec3(0.86, 0.6, 0.5);
uniform vec3 tentacle_root : source_color = vec3(0.42, 0.38, 0.18);
uniform vec3 tentacle : source_color = vec3(0.6, 0.6, 0.3);
uniform vec3 tentacle_tip : source_color = vec3(0.86, 0.88, 0.56);
// How far out the mouth's lips are (as UV.x on the disc: the mouth's lips are 0.035 m out on a 0.2 m disc).
uniform float mouth_out = 0.175;

varying float part;
varying float along;
varying float own;


void vertex() {
	bake_uv = CUSTOM0.xy;

	part = floor(COLOR.r * 10.0 + 0.5);
	along = UV.x;
	own = COLOR.g;
	if (part == 2.0) {
		vec3 root = (MODEL_MATRIX * vec4(UV2.x, 0.0, UV2.y, 1.0)).xyz;
		float k = water_clock * sway_speed * 1.05 + dot(root.xz, vec2(3.1, 2.3)) + own * 2.0;
		float bend = UV.x * UV.x;
		// (two slow waves crossing, so that the tips trace loops; those at the margin sway more)
		vec3 push = vec3(sin(k), 0.0, cos(k * 0.83 + 1.7)) * (0.015 * sway * (0.6 + 0.6 * COLOR.b));
		push.xz += current;
		VERTEX += bend * push;
		// (a tip pushed aside sinks a little, so that the tentacle keeps about its length)
		VERTEX.y -= bend * 0.4 * length(push.xz);
	}
}


void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

