shader_type spatial;
// The sea urchins (sea_urchin.gd): their colours, and all of their moving. What each point is comes from
// the model (tools/build_sea_urchin.py): UV2.y the part (0 the test, 1 a spine, 2 a tube foot, 3 a tooth,
// 4 a short spine), UV the place on the test (phi / tau, theta / pi) of the point or of the root of the
// spine or foot it belongs to, UV2.x from a spine's or foot's root (0) to its tip (1).
//
// Every spine is turned about its own root here: it sways a little, each in its own time, on `phase`,
// and all lean towards `threat` (a direction in the urchin's own space; its length says how alarmed it
// is, 0..1), the spines on that side tipping in towards it. The tube feet wave as threads, bending more
// towards their tips. The test is a sum this shader and the build script share (`test_point`,
// `spine_way`), so a spine's root and its resting way come from its UV: change the build script's
// numbers and these together. All of it is a function of `phase` alone, so a picture of it loops exactly.
// Nothing here needs more than GL Compatibility has; it runs the same under Forward+.
render_mode cull_back, vertex_lighting;

// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of
// its component's shader: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).
varying vec2 bake_uv;
uniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;
uniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;
uniform float baked_glow_scale = 1.0;
uniform float baked_roughness = 0.5;
uniform float baked_specular = 0.5;


// How far through a beat (0..1, it wraps). Set by SeaUrchin.
uniform float phase = 0.0;
// How much its spines sway and its feet wave (1 as it lives, 0 still).
uniform float sway = 1.0;
// Where the danger is, in its own space; its length is how alarmed it is (0 calm, 1 every spine on
// that side tipped in towards it as far as `lean` lets).
uniform vec3 threat = vec3(0.0);
// How far the spines lean towards a threat at its strongest (1: about 45 degrees).
uniform float lean = 1.0;
// The kind's test, as the model is built (metres): its radius, how far it reaches above and below its
// middle, how high its middle stands, how much a spine beneath the middle is tipped out, how deep a
// spine's root is sunk.
uniform float test_radius = 0.04;
uniform float test_top = 0.024;
uniform float test_bottom = 0.015;
uniform float test_middle = 0.021;
uniform float below_lean = 0.55;
uniform float sink = 0.002;

// The test, its five double rows of pores (the ambulacra), and the soft skin round its mouth.
uniform vec3 test_colour : source_color = vec3(0.32, 0.16, 0.3);
uniform vec3 pores : source_color = vec3(0.45, 0.3, 0.42);
uniform vec3 mouth_skin : source_color = vec3(0.2, 0.12, 0.15);
// A spine: at its root, along it, at its tip, and the colour of its bands (how many and how strong).
uniform vec3 spine_root : source_color = vec3(0.7, 0.55, 0.65);
uniform vec3 spine : source_color = vec3(0.42, 0.1, 0.42);
uniform vec3 spine_tip : source_color = vec3(0.62, 0.3, 0.62);
uniform vec3 band : source_color = vec3(0.6, 0.4, 0.6);
uniform float bands = 0.0;
uniform float band_count = 6.0;
// The short spines between a slate pencil's thick ones, its tube feet, its teeth.
uniform vec3 short_spine : source_color = vec3(0.55, 0.42, 0.3);
uniform vec3 foot : source_color = vec3(0.42, 0.12, 0.42);
uniform vec3 tooth : source_color = vec3(0.92, 0.9, 0.82);
// How glossy its spines are (0 dull).
uniform float gloss = 0.5;
// How much the small knobs where spines stood show on the test (0: none; the test reads as a dense coat of
// spine roots instead).
uniform float knob_amount = 1.0;

varying float part;
varying float along;

vec3 test_point(float th, float ph) {
	float c = cos(th);
	float rho = test_radius * sin(th);
	return vec3(rho * cos(ph), test_middle + (c > 0.0 ? test_top : test_bottom) * c, rho * sin(ph));
}

vec3 spine_way(float th, float ph) {
	float t = th < PI * 0.5 ? th : PI * 0.5 + (th - PI * 0.5) * (1.0 - below_lean);
	return vec3(sin(t) * cos(ph), cos(t), sin(t) * sin(ph));
}

float hash2(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

// `v` turned about the unit axis `k` by the angle whose cosine and sine are c and s.
vec3 turned(vec3 v, vec3 k, float c, float s) {
	return v * c + cross(k, v) * s + k * dot(k, v) * (1.0 - c);
}

void vertex() {
	bake_uv = CUSTOM0.xy;

	part = UV2.y;
	along = UV2.x;
	int p = int(part + 0.5);
	if (p == 1 || p == 2 || p == 4) {
		float th = UV.y * PI;
		float ph = UV.x * TAU;
		vec3 d = spine_way(th, ph);
		vec3 root = test_point(th, ph) - d * sink;
		vec3 e1 = normalize(cross(d, abs(d.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
		vec3 e2 = cross(d, e1);
		float h1 = hash2(UV * 917.0);
		float h2 = hash2(UV * 613.0 + 7.0);
		float t = TAU * phase;
		float amp = sway * (p == 2 ? 0.55 : (p == 4 ? 0.04 : 0.07));
		vec3 w = d + amp * (e1 * sin(t + h1 * TAU) + e2 * cos(t + h2 * TAU));
		float alarm = length(threat);
		if (alarm > 0.001 && p != 2) {
			vec3 tn = threat / alarm;
			float facing = smoothstep(-0.35, 0.7, dot(d, tn));
			w += (tn - d * dot(d, tn)) * min(alarm, 1.0) * lean * facing;
		}
		w = normalize(w);
		vec3 axis = cross(d, w);
		float s = length(axis);
		if (s > 0.00001) {
			axis /= s;
			float angle = atan(s, dot(d, w));
			// (a tube foot bends along its length; a spine turns whole)
			if (p == 2) {
				angle *= along;
			}
			float c = cos(angle);
			float sn = sin(angle);
			VERTEX = root + turned(VERTEX - root, axis, c, sn);
			NORMAL = turned(NORMAL, axis, c, sn);
		}
	}
}

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
	ALBEDO = paint.rgb;
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}

