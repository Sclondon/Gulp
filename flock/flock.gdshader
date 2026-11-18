shader_type spatial;
render_mode cull_disabled;
// A Flock's boids, all drawn by one MultiMesh. The instance colour is the boid's own shade
// (multiplied into COLOR with the mesh's vertex colours); its custom data is its pose, which
// the Flock writes as it moves them: x the beat phase (radians, kept by the Flock so a change
// of pace never jumps), y effort (0..2), z glide (0: beating, 1: wings held out), w fright
// (0..1). The mesh faces -z, wings along +x/-x, up +y.
//
// motion 0 flap: everything further out than body_half is a wing, hinged at the body and
// beaten up and down (the outer wing lags, so it bends like a real one). 1 swim: the tail half
// swishes side to side in a wave running back along the body. 2 walk: everything below leg_top
// is a leg, swung fore and aft from the hip in diagonal pairs, and the body bobs.

uniform vec4 colour : source_color = vec4(0.12, 0.11, 0.13, 1.0);
uniform int motion = 0;
uniform float amount = 0.7;
uniform float body_half = 0.06;
uniform float span_half = 0.5;
uniform float length_half = 0.5;
uniform float leg_top = 0.35;
uniform float sheen = 0.25;
uniform float roughness = 0.65;
// Riders (Gulp; a Flock whose rules.riders > 0: a swarm of hundreds or thousands). Its boids are a
// few dozen guides that are not drawn; each instance rides one. An instance's transform is the
// identity, and its custom data is x, y, z its place in the cloud round its guide (m) and w its
// guide's index plus a seed of its own (the fraction; less than 0: not drawn, it has been taken).
// The guides are in lead_at (xyz where, w its fright) and lead_way (xyz its heading, w its beat
// phase); shove pushes riders aside round up to two things (xyz where, w how far). Only motion 1
// (swim) and 3 (none) are used by riders.
uniform int riders = 0;
uniform vec4 lead_at[48];
uniform vec4 lead_way[48];
uniform vec4 shove[2];
uniform float rider_size = 1.0;
uniform float rider_vary = 0.1;
uniform float rider_drift = 0.08;
uniform float rider_fright = 0.8;

void vertex() {
	float phase = INSTANCE_CUSTOM.x;
	float effort = INSTANCE_CUSTOM.y;
	float glide = INSTANCE_CUSTOM.z;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	if (riders > 0) {
		float w = INSTANCE_CUSTOM.w;
		float aw = abs(w);
		int g = int(floor(aw));
		float seed = aw - floor(aw);
		vec4 at = lead_at[g];
		vec4 way = lead_way[g];
		float t = TIME * 0.6 + seed * 61.0;
		vec3 p = at.xyz + INSTANCE_CUSTOM.xyz * (1.0 + at.w * rider_fright)
				+ vec3(sin(t * 1.3), sin(t * 0.9 + 1.7) * 0.6, cos(t * 1.1)) * rider_drift;
		for (int k = 0; k < 2; k++) {
			vec3 d = p - shove[k].xyz;
			float l = length(d);
			if (l < shove[k].w) {
				p += d / max(l, 0.001) * (shove[k].w - l) * 0.9;
			}
		}
		vec3 f = normalize(way.xyz + vec3(sin(t * 1.7), sin(t * 1.1) * 0.3, cos(t * 1.5)) * 0.14);
		vec3 right = cross(f, vec3(0.0, 1.0, 0.0));
		right = length(right) < 0.001 ? vec3(1.0, 0.0, 0.0) : normalize(right);
		vec3 up = cross(right, f);
		float s = w < 0.0 ? 0.0 : rider_size * (1.0 + (fract(seed * 7.31) * 2.0 - 1.0) * rider_vary);
		if (motion == 1) {
			float ph = way.w + seed * 6.2832;
			float wf = clamp((v.z / length_half + 0.35) / 1.35, 0.0, 1.0);
			wf *= wf;
			float wave = sin(ph - v.z / length_half * 2.6);
			v.x += wave * amount * wf * length_half * (1.0 + 0.3 * at.w);
			v.x -= sin(ph) * amount * 0.06 * length_half;
			n.x += wave * amount * wf * 0.8;
		}
		VERTEX = p + (right * v.x + up * v.y - f * v.z) * s;
		NORMAL = normalize(right * n.x + up * n.y - f * n.z);
	} else if (motion == 0) {
		float ax = abs(v.x);
		float beat = sin(phase) * amount * (0.75 + 0.25 * effort);
		if (ax > body_half) {
			float side = sign(v.x);
			float out_d = ax - body_half;
			float tip = clamp(out_d / max(span_half - body_half, 0.001), 0.0, 1.0);
			// held out a little above level when gliding; the tip lags the beat
			float a = mix(beat + sin(phase - 1.1) * amount * 0.45 * tip, 0.1 + 0.08 * tip, glide);
			float c = cos(a);
			float s = sin(a);
			v.x = side * (body_half + out_d * c - v.y * s);
			v.y = out_d * s + v.y * c;
			float nx = n.x * side;
			n.x = side * (nx * c - n.y * s);
			n.y = nx * s + n.y * c;
		}
		// the body rides opposite the wings
		v.y -= sin(phase) * amount * 0.05 * span_half * (1.0 - glide);
	} else if (motion == 1) {
		float w = clamp((v.z / length_half + 0.35) / 1.35, 0.0, 1.0);
		w *= w;
		float wave = sin(phase - v.z / length_half * 2.6);
		v.x += wave * amount * w * length_half * (0.7 + 0.3 * effort);
		v.x -= sin(phase) * amount * 0.06 * length_half;
		n.x += wave * amount * w * 0.8;
	} else if (motion == 2) {
		float stride = clamp(effort, 0.0, 1.5);
		if (v.y < leg_top) {
			float pair = sign(v.x) * sign(v.z + 0.0001);
			v.z += sin(phase) * pair * amount * (leg_top - v.y) * stride;
		}
		v.y += abs(sin(phase)) * 0.04 * leg_top * stride;
	}
	if (riders == 0) {
		VERTEX = v;
		NORMAL = normalize(n);
	}
}

void fragment() {
	ALBEDO = COLOR.rgb * colour.rgb;
	ROUGHNESS = roughness;
	SPECULAR = sheen;
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
}
