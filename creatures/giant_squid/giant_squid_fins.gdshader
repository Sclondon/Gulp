shader_type spatial;
// The giant squid's two fins: thin sheets seen from both sides, a little clear towards their
// edges. All of it is worked out in giant_squid.gdshaderinc.
render_mode blend_mix, cull_disabled, depth_draw_opaque, depth_prepass_alpha, vertex_lighting;

#define SQUID_FINS
#include "giant_squid.gdshaderinc"
