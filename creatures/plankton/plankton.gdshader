shader_type spatial;
// The plankton cloud (plankton_cloud.gd): a MultiMesh of specks, each instance one of four kinds
// (a copepod, a diatom chain, a radiolarian, a crab larva), tumbling slowly and drifting about
// where it was put, glittering as a face turns to the eye. The mesh (tools/build_plankton.py)
// holds all four kinds at the origin: UV2.y which kind a point belongs to, UV.x what it is part
// of (0 a body, 1 a spine, antenna or tail, 2 an eye). Each instance's custom data: r its own
// number (0..1, for its tumble, its drift and its size), g which kind it shows (0..3), b how far
// it has grown back (0 gone: eaten, 1 all there), a how big it is (times `speck_size`).
//
// The time is the global shader uniform `water_clock` (seconds). Nothing here needs more than GL
// Compatibility has. The specks are single sheets in places, so both sides are drawn.
render_mode cull_disabled;

global uniform float water_clock;

// How big the specks are (1: as built, a few millimetres across).
uniform float speck_size = 1.0;
// How far each drifts about its place (metres), and how long one sway of the drift takes (s).
uniform float drift = 0.25;
uniform float drift_period = 23.0;
// How fast they tumble (turns a second, about).
uniform float spin = 0.12;
// How bright a face flashes as it turns to the eye.
uniform float glitter = 1.4;

// The colours of each kind: the copepod's amber body and its red eye spot, the diatom's golden
// brown, the radiolarian's glassy white, the crab larva's orange-red; the fine glassy parts.
uniform vec3 copepod : source_color = vec3(0.85, 0.62, 0.32);
uniform vec3 eye_spot : source_color = vec3(0.75, 0.08, 0.04);
uniform vec3 diatom : source_color = vec3(0.62, 0.5, 0.2);
uniform vec3 radiolarian : source_color = vec3(0.86, 0.9, 0.92);
uniform vec3 larva : source_color = vec3(0.86, 0.38, 0.18);
uniform vec3 glass : source_color = vec3(0.82, 0.88, 0.9);

varying float kind;
varying float what;
varying vec3 rest;
varying float own;

float hash1(float n) {
	return fract(sin(n * 127.1) * 43758.5453);
}

vec3 turned(vec3 v, vec3 k, float a) {
	float c = cos(a);
	float s = sin(a);
	return v * c + cross(k, v) * s + k * dot(k, v) * (1.0 - c);
}

void vertex() {
	kind = floor(UV2.y + 0.5);
	what = floor(UV.x + 0.5);
	rest = VERTEX;
	own = INSTANCE_CUSTOM.r;
	float shown = floor(INSTANCE_CUSTOM.g + 0.5);
	float grown = clamp(INSTANCE_CUSTOM.b, 0.0, 1.0);
	// (a point of another kind, or of a speck that has been eaten, is squashed to nothing: its
	// triangles have no area and are not drawn)
	float here = (abs(kind - shown) < 0.5 ? 1.0 : 0.0) * grown;
	float t = water_clock;
	vec3 axis = normalize(vec3(hash1(own * 91.0) - 0.5, hash1(own * 37.0) - 0.5, hash1(own * 53.0) - 0.5) + vec3(0.0, 0.001, 0.0));
	float a = 6.2831853 * (own * 5.0 + t * spin * (0.5 + hash1(own * 13.0)));
	vec3 v = turned(VERTEX, axis, a) * speck_size * INSTANCE_CUSTOM.a * here;
	NORMAL = turned(NORMAL, axis, a);
	float w = 6.2831853 * t / drift_period;
	v += drift * vec3(sin(w + own * 41.0), 0.6 * sin(w * 1.31 + own * 17.0), sin(w * 0.83 + own * 29.0));
	VERTEX = v;
}

void fragment() {
	int k = int(kind + 0.5);
	vec3 c;
	if (k == 0) {
		c = copepod;
		// the red eye spot at the front of its head
		c = mix(c, eye_spot, 1.0 - smoothstep(0.0004, 0.0007, length(rest - vec3(0.0, 0.0004, -0.0014))));
	} else if (k == 1) {
		// the cells: golden brown, a pale band at each join
		float join = abs(fract(rest.z / 0.0012 + 0.5) - 0.5);
		c = mix(diatom * 1.25, diatom, smoothstep(0.04, 0.12, join));
	} else if (k == 2) {
		c = radiolarian;
	} else {
		c = larva;
	}
	if (what > 0.5 && what < 1.5) {
		c = mix(c, glass, 0.6);
	} else if (what > 1.5) {
		c = vec3(0.02, 0.02, 0.025);
	}
	// A face that turns square to the eye flashes (each speck at its own moments as it tumbles).
	vec3 n = normalize(NORMAL);
	float square = abs(dot(n, normalize(VIEW)));
	float flash = smoothstep(0.93, 1.0, square) * glitter;
	ALBEDO = c;
	ROUGHNESS = 0.3;
	SPECULAR = 0.7;
	EMISSION = (c + vec3(0.3)) * flash * (k == 2 || what > 0.5 ? 1.0 : 0.6);
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
}
