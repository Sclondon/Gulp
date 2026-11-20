shader_type canvas_item;
// The sonar's picture as a round cathode-ray tube shows it: bulged like the glass (the middle
// bigger, the edge drawn in), scan lines, a soft glow round what is lit, a dark rim, a faint
// flicker and a roll of brightness down it, and a glint on the glass. See scripts/sonar.gd.

uniform float bulge : hint_range(0.0, 0.6) = 0.3;
uniform float lines : hint_range(20.0, 400.0) = 120.0;
uniform vec3 phosphor : source_color = vec3(0.1, 0.5, 0.18);

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r2 = dot(p, p);
	// (the glass: the picture's middle is stretched out, its edge squeezed)
	vec2 q = p * mix(1.0 - bulge, 1.0, r2);
	vec2 at = q * 0.5 + 0.5;
	vec4 lit = texture(TEXTURE, at);
	// (a glow: what is near shines on what is not)
	vec2 px = TEXTURE_PIXEL_SIZE * 2.5;
	vec4 near = (texture(TEXTURE, at + vec2(px.x, 0.0)) + texture(TEXTURE, at - vec2(px.x, 0.0))
			+ texture(TEXTURE, at + vec2(0.0, px.y)) + texture(TEXTURE, at - vec2(0.0, px.y))) * 0.25;
	vec3 colour = lit.rgb * lit.a + near.rgb * near.a * 0.55;
	float shown = clamp(lit.a + near.a * 0.5, 0.0, 1.0);
	// (scan lines, a slow roll, a flicker)
	float scan = 0.82 + 0.18 * sin(UV.y * lines * 3.14159);
	float roll = 0.94 + 0.06 * sin(UV.y * 5.0 - TIME * 1.7);
	float flicker = 0.97 + 0.03 * sin(TIME * 47.0);
	colour *= scan * roll * flicker * 1.25;
	// (the tube's own faint light, brightest in the middle; a dark rim)
	float inside = 1.0 - smoothstep(0.86, 1.0, r2);
	float rim = 1.0 - 0.7 * smoothstep(0.35, 1.0, r2);
	// (dark glass: only a faint light of its own)
	vec3 tube = phosphor * (0.06 + 0.05 * (1.0 - r2)) * scan;
	colour = (colour + tube) * rim;
	// (a glint of the light on the glass, upper left, and a thin one opposite)
	float glint = smoothstep(0.5, 0.0, length(p - vec2(-0.38, -0.42))) * 0.2
			+ smoothstep(0.25, 0.0, length(p - vec2(0.45, 0.5))) * 0.06;
	colour += vec3(glint);
	COLOR = vec4(colour, inside * clamp(shown + 0.45 + glint, 0.0, 1.0));
}
