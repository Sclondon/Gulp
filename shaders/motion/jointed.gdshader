shader_type spatial;
// The jointed family (GameCommon `godot/motion-families`): animals that move by parts turning on hinges
// and joints and nothing swimming through the whole body: crabs, lobsters, shrimps and prawns (legs on a
// stride), shells (valves on a hinge), ammonites, urchins, the round stingray's rippling rim. Only the
// moves every family shares (motion.gdshaderinc); the animal's numbers are uniforms (scripts/motion.gd).
render_mode cull_back, vertex_lighting;

#define MOTION_LEGS
#include "res://shaders/motion/motion.gdshaderinc"

void vertex() {
	bake_uv = CUSTOM0.xy;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	float side = VERTEX.x >= 0.0 ? 1.0 : -1.0;
	motion_ops(v, n, NORMAL, side, CUSTOM0, CUSTOM1, CUSTOM2, CUSTOM3, false);
	motion_ops(v, n, NORMAL, side, CUSTOM0, CUSTOM1, CUSTOM2, CUSTOM3, true);
	VERTEX = v;
	NORMAL = normalize(n);
}

#include "res://shaders/motion/motion_paint.gdshaderinc"
