shader_type spatial;
render_mode unshaded, cull_back;
// The pirate wreck's paint (scripts/pirate_wreck.gd): one picture, textures/pirate_atlas.png, that Blender bakes for
// the low-poly model (tools/build_pirate_wreck.py): colour, the light falling on it and the shadow where parts meet.
// Drawn unlit, so it looks the same on every renderer; the scene's water fog still lies over it. The one program for
// the whole wreck (a browser freezes about a second for each new one): the treasure uses it with `glow` on.

uniform sampler2D atlas : source_color, filter_linear_mipmap, repeat_disable;
// The water's colour over it (and day or night, later: dim it to dim the wreck).
uniform vec3 tint : source_color = vec3(0.9, 0.96, 1.0);
// Gold glints (0 off: the ship; 1: the treasure). Only warm, bright texels glint: the gold, not the chests' wood.
uniform float glow = 0.0;
// Sunlight rippling over what faces up and sees the sky (the model's vertex colour: 1 open, 0 indoors), as on the
// concept art (0 off).
uniform float caustics = 0.35;

varying vec3 world;
varying vec3 world_normal;
varying float sky;

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	sky = COLOR.r;
}

// A cheap net of bright lines drifting with the clock, like light through waves.
float ripple(vec2 p, float t) {
	vec2 a = p * 0.55 + vec2(t * 0.11, t * 0.07);
	vec2 b = p * 0.83 - vec2(t * 0.09, -t * 0.05);
	float s = sin(a.x + sin(a.y * 1.3)) * sin(a.y + sin(a.x * 1.7)) + sin(b.x * 1.1 + sin(b.y)) * sin(b.y * 0.9 + sin(b.x * 1.2));
	return pow(clamp(1.0 - abs(s) * 1.6, 0.0, 1.0), 4.0);
}

void fragment() {
	vec3 paint = texture(atlas, UV).rgb;
	vec3 colour = paint * tint;
	// light rippling on upward faces
	float up = smoothstep(0.2, 0.9, world_normal.y) * sky;
	colour += paint * ripple(world.xz, TIME) * up * caustics;
	// gold: warm and bright in the paint; it keeps its own warmth under the water's colour and catches the light
	float gold = smoothstep(0.1, 0.28, paint.r - paint.b) * smoothstep(0.3, 0.55, paint.r) * min(glow, 1.0);
	float glint = pow(max(sin(dot(world, vec3(9.1, 7.3, 11.7)) + TIME * 1.7) * sin(dot(world, vec3(-6.7, 12.9, 4.1)) - TIME * 1.3), 0.0), 10.0);
	colour = mix(colour, paint * vec3(1.3, 1.08, 0.78), gold) + gold * glint * glow * vec3(2.4, 1.7, 0.7);
	ALBEDO = colour;
}
