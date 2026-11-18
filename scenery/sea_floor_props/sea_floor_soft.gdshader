shader_type spatial;
// The soft things of the sea floor (SeaFloorProps): sea fans, anemones, soft corals, sponges,
// feather-duster worms. The colour painted on the mesh's points, times the instance's colour and
// a tint; the ALPHA of a point's colour is how far that point sways (0 held fast, 1 a free tip).
// The sway comes from where the point is in the world and from the global `water_clock` (a float
// the game keeps moving, in seconds), so neighbours move together as in a surge and nothing
// keeps a clock of its own. No textures, nothing that needs Forward+; one opaque draw, back
// faces culled.
//
// In GL Compatibility a MultiMesh needs use_colors on and its instances' colours set (white, alpha
// 1, for no tint and the full sway; a lower alpha stills that instance).
render_mode cull_back;

global uniform float water_clock;

uniform vec3 tint : source_color = vec3(1.0);
// Metres a point of full sway moves each way (at the instance's scale 1), and how fast.
uniform float sway = 0.07;
uniform float sway_speed = 1.2;
// How much its edges glow with the light coming through them.
uniform float glow : hint_range(0.0, 1.0) = 0.3;

void vertex() {
	vec3 at = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float t = water_clock * sway_speed;
	// (a slow surge to and fro that everything near shares, and a quicker flutter on top)
	vec3 push = vec3(
		sin(t + at.x * 0.7 + at.z * 0.4) + 0.35 * sin(t * 2.3 + at.z * 5.1 + at.y * 4.0),
		0.2 * sin(t * 1.7 + at.x * 3.0),
		0.6 * cos(t * 0.8 + at.z * 0.6 + at.x * 0.3) + 0.35 * sin(t * 2.7 + at.x * 5.3 + at.y * 3.0));
	float size = length(MODEL_MATRIX[0].xyz);
	// (the push is in the world's directions: turned back into the piece's own)
	VERTEX += (vec4(push, 0.0) * MODEL_MATRIX).xyz / size * (sway * COLOR.a);
}

void fragment() {
	vec3 colour = COLOR.rgb * tint;
	ALBEDO = colour;
	ROUGHNESS = 0.75;
	SPECULAR = 0.2;
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.5);
	EMISSION = colour * rim * glow;
}
