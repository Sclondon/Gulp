shader_type spatial;
render_mode unshaded;
// The control panel's paint: one picture (textures/panel/panel_atlas.png) that Blender bakes for
// the low-poly model: colour, light from the upper left, and the shadows where parts meet
// (tools/build_panel.py; the user: "make it low poly twilight princess style"). Drawn unlit, so
// it needs no lights and looks the same on every renderer. On top of the picture: a little light
// that follows a part as it moves (the stick, the lever), and a shine on polished metal.

uniform sampler2D atlas : source_color, filter_linear_mipmap;
uniform vec3 tint : source_color = vec3(1.0);
// Polished metal (0 dull, 1 brass): a highlight, and brighter above than below.
uniform float shine = 0.0;
// Light of its own (the plunger held).
uniform vec3 glow : source_color = vec3(0.0);

void fragment() {
	vec3 colour = texture(atlas, UV).rgb * tint;
	vec3 n = normalize(NORMAL);
	vec3 light = normalize(vec3(-0.5, 0.62, 0.6));
	float d = dot(n, light);
	float lit = mix(1.0, 0.72 + 0.5 * clamp(d * 0.5 + 0.5, 0.0, 1.0), 0.6);
	vec3 half_way = normalize(light + vec3(0.0, 0.0, 1.0));
	float spark = pow(max(dot(n, half_way), 0.0), 28.0) * shine;
	float mirror = mix(1.0, mix(0.85, 1.2, smoothstep(-0.5, 0.8, n.y * 0.6 + d * 0.5)), shine);
	ALBEDO = colour * lit * mirror * 1.1 + spark * mix(vec3(1.0), colour * 3.0, 0.5) * 0.7 + glow;
}
