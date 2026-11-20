shader_type spatial;
// The swim family (GameCommon `godot/motion-families`): fish, sharks, eels, whales, dolphins, seals,
// marine reptiles. One program for all of them: each animal's own numbers are uniforms
// (scripts/motion.gd), its paint is baked (GameCommon `godot/baked-look`). See motion.gdshaderinc for
// the moves every family shares, swim_core.gdshaderinc for the swimming wave.
render_mode cull_back, vertex_lighting;

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
