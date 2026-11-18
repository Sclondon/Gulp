shader_type spatial;
render_mode diffuse_lambert, specular_disabled, cull_back;
// The reef wreck's paint (tools/build_wreck.py, tools/WRECK.md): one picture a half, baked in Blender
// as colour times how open each spot is to the sea (dark inside, light on top). Drawn lit, so the
// sea's light, its fog and anything that glows near it reach it as they reach everything else.
// `tint` dims or tints it (day and night); `lift` raises the darkest paint a little, so that the
// insides of rooms read when a fish is in them.

uniform sampler2D atlas : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec3 tint : source_color = vec3(1.0);
uniform float brightness = 1.1;
// 0: the paint as baked; 1: its dark half lifted a lot (a power curve: dark inside, but readable).
uniform float lift = 0.3;

void fragment() {
	vec3 paint = texture(atlas, UV).rgb;
	paint = pow(max(paint, vec3(0.0)), vec3(1.0 - 0.45 * lift));
	ALBEDO = paint * tint * brightness;
	ROUGHNESS = 1.0;
	METALLIC = 0.0;
}
