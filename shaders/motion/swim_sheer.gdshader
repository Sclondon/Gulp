shader_type spatial;
// The swim family, see-through (GameCommon `godot/motion-families`): fins drawn as clear membranes
// (the flying fish's wings). As swim.gdshader, blended by its paint's alpha.
render_mode blend_mix, cull_back, depth_draw_always, vertex_lighting;

#define MOTION_SHEER
#include "res://shaders/motion/motion.gdshaderinc"
#include "res://shaders/motion/swim_core.gdshaderinc"

void vertex() {
	bake_uv = CUSTOM0.xy;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float side = VERTEX.x >= 0.0 ? 1.0 : -1.0;
	motion_ops(v, n, NORMAL, side, CUSTOM0, CUSTOM1, CUSTOM2, CUSTOM3, false);
	swim_core(v, n);
	motion_ops(v, n, NORMAL, side, CUSTOM0, CUSTOM1, CUSTOM2, CUSTOM3, true);
	VERTEX = v;
	NORMAL = normalize(n);
}

#include "res://shaders/motion/motion_paint.gdshaderinc"
