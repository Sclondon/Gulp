shader_type spatial;
// The radial family (GameCommon `godot/motion-families`): animals of arms and stalks round a middle,
// each arm bending along itself (the moves' bend, type 5, in each arm's own frame from its point and way
// in the model): starfish, feather stars and sea lilies, anemones, nudibranchs and sea slugs, pyrosomes.
// Drawn from both sides (thin arms and frills). Only the shared moves (motion.gdshaderinc).
render_mode cull_disabled, vertex_lighting;

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
