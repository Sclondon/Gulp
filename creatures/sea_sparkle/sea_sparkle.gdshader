shader_type spatial;
// The sea sparkle (sea_sparkle.gd): a MultiMesh of specks, each one cell of Noctiluca, tumbling slowly and drifting
// about where it was put, glowing dimly, and flashing bright blue when something stirs the water round it. The mesh
// (tools/build_sea_sparkle.py) is one speck at the origin: UV2.y its part (0 the cell, 1 the tentacle), UV.x how far
// from the cell's middle. Each instance's custom data: r its own number (0..1, for its tumble, its drift and its
// glow), g when it was last stirred (on the cloud's own clock, `clock`, in seconds), b how hard (0..1), a its size
// (times `speck_size`). Its transform is only a place (the shader turns it).
//
// The time is `clock`, set by the cloud each frame: its own clock, which runs from 0 to PERIOD seconds and starts
// again, so that it stays small enough to be kept exactly. Every motion here comes round in whole turns in a PERIOD,
// so nothing jumps when it starts again. What lights up (EMISSION): every speck, dimly, each a little brighter or
// dimmer than the next and slowly breathing; and a stirred speck bright blue, at once, fading over `fade` seconds.
// Nothing here needs more than GL Compatibility has. One opaque draw, back faces culled.
render_mode cull_back;

// As the cloud has it (PERIOD in sea_sparkle.gd).
const float PERIOD = 64.0;

// The cloud's clock (seconds, 0..PERIOD). Set by SeaSparkle.
uniform float clock = 0.0;
// How big the specks are (1: as built, 4 mm across).
uniform float speck_size = 1.0;
// How far each drifts about its place (metres).
uniform float drift = 0.15;
// How fast they tumble (turns a second, about).
uniform float spin = 0.1;
// How long a flash takes to fade (seconds).
uniform float fade = 1.4;
// How brightly they glow at rest and when stirred (0 none, 1 as made, 2 twice as bright).
uniform float glow : hint_range(0.0, 2.0) = 1.0;
uniform float rest_glow = 0.12;
uniform float flash_glow = 2.2;
// The cell's clear pale colour, its dim glow, its flash.
uniform vec3 cell : source_color = vec3(0.62, 0.72, 0.78);
uniform vec3 rest_colour : source_color = vec3(0.3, 0.6, 0.85);
uniform vec3 flash_colour : source_color = vec3(0.1, 0.36, 1.0);

varying float own;
varying float lit;
varying float part;
varying float rim;

float hash1(float n) {
	return fract(sin(n * 127.1) * 43758.5453);
}

vec3 turned(vec3 v, vec3 k, float a) {
	float c = cos(a);
	float s = sin(a);
	return v * c + cross(k, v) * s + k * dot(k, v) * (1.0 - c);
}

void vertex() {
	own = INSTANCE_CUSTOM.r;
	part = UV2.y;
	rim = UV.x;
	float t = clock;
	// The flash: how long since it was stirred, how hard; quick to light, fading over `fade`.
	float age = t - INSTANCE_CUSTOM.g;
	float stirred = clamp(INSTANCE_CUSTOM.b, 0.0, 1.0);
	lit = age < 0.0 ? 0.0 : stirred * smoothstep(0.0, 0.06, age) * exp(-age * 3.0 / max(fade, 0.01));
	// It tumbles a whole number of turns in a PERIOD about an axis of its own.
	vec3 axis = normalize(vec3(hash1(own * 91.0) - 0.5, hash1(own * 37.0) - 0.5, hash1(own * 53.0) - 0.5) + vec3(0.0, 0.001, 0.0));
	float turns = floor(PERIOD * spin * (0.5 + hash1(own * 13.0)) + 0.5);
	float a = 6.2831853 * (own * 5.0 + turns * t / PERIOD);
	// (a flashing speck swells a little)
	vec3 v = turned(VERTEX, axis, a) * speck_size * INSTANCE_CUSTOM.a * (1.0 + 0.35 * lit);
	NORMAL = turned(NORMAL, axis, a);
	// It drifts about its place, in whole sways in a PERIOD (three, four and two, each on its own timing).
	float w = 6.2831853 * t / PERIOD;
	v += drift * vec3(sin(3.0 * w + own * 41.0), 0.6 * sin(4.0 * w + own * 17.0), sin(2.0 * w + own * 29.0));
	VERTEX = v;
}

void fragment() {
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	// (each speck breathes a little at rest, two breaths in a PERIOD... and a little more, by its own number)
	float breathe = 0.75 + 0.25 * sin(6.2831853 * (floor(2.0 + own * 4.0) * clock / PERIOD + own * 7.0));
	float rest = rest_glow * (0.6 + 0.8 * own) * breathe;
	vec3 c = mix(cell, vec3(0.9, 0.95, 1.0), 0.4 * glance);
	c = mix(c, cell * 0.8, step(0.5, part));
	ALBEDO = c * 0.5;
	ROUGHNESS = 0.2;
	SPECULAR = 0.6;
	// (brightest through its middle, as light in a clear ball; the tentacle dimmer)
	float body = mix(1.0, 0.6, glance) * mix(1.0, 0.5, step(0.5, part));
	EMISSION = (rest_colour * rest + flash_colour * lit * flash_glow) * body * glow;
}
