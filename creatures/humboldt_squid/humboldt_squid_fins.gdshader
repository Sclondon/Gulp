shader_type spatial;
// The Humboldt squid's two fins: sheets seen from both sides, a very little clear at their edges.
// All of it is worked out in humboldt_squid.gdshaderinc.
render_mode blend_mix, cull_disabled, depth_draw_opaque, depth_prepass_alpha, vertex_lighting;

#define SQUID_FINS
#include "humboldt_squid.gdshaderinc"
