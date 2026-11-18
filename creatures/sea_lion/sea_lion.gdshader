shader_type spatial;
// The California sea lion (sea_lion.gd): its coat and face drawn here (no texture files), its
// fore flippers' stroke, its jaw and a bull's crest. What each point is comes from the model
// (tools/build_sea_lion.py): COLOR.r what it is made of, as a tenth (0 fur, 1 an eye, 2 a tooth,
// 3 the tongue, 4 a whisker, 5 bare hide, 6 a claw); COLOR.g how far inside the mouth it is;
// COLOR.b how far along its flipper it is (on an eye, 0 its middle to 1 its rim; on the head and
// jaw, how much it is the lips' edge); UV2.y what moves it, as an eighth (0 nothing, 1 the lower
// jaw, 2 and 3 the left and right fore flippers, 4 and 5 the left and right hind flippers);
// UV.x, UV.y and UV2.x its hinge (z, y, x in body lengths, plus a half).
//
// It swims as sea lions do: it flies. The long fore flippers are lifted out and forward, then
// swept down and back to its belly in a strong stroke, twisting as they go; the body rides the
// stroke a little; the hind flippers trail and steer. All of it is a function of `phase` alone,
// so a picture of it loops exactly. Nothing here needs more than GL Compatibility has.
render_mode cull_back;

// Kept in step with the model.
const float LENGTH = 2.2;
const float HALF = 1.1;
// The corner of the mouth and the jaw's hinge (metres behind the nose).
const float CORNER = 0.125;
const float HINGE_X = 0.192;
// The way a fore flipper runs out from its root (its left one).
const vec3 SPAN = vec3(0.767, -0.307, 0.563);
const float TURN = 6.2831853;
// The left eye, as the model is built (the build script prints its EYE line): its middle on the
// skin, the way it faces, the way to the nose and up across it, its radius and how far its rim
// lies below a flat across it. The cartoon eye is EYE_GROW times as big.
const vec3 EYE_MID = vec3(0.0528, 0.0447, -0.9320);
const vec3 EYE_OUT = vec3(0.8190, 0.4546, -0.3500);
const vec3 EYE_AHEAD = vec3(-0.3060, -0.1699, -0.9368);
const vec3 EYE_UP = vec3(-0.4853, 0.8743, 0.0);
const float EYE_R = 0.0145;
const float EYE_SAG = 0.00159;
const float EYE_GROW = 1.85;

// How far through a stroke it is (0..1, it wraps). Set by SeaLion.
uniform float phase = 0.0;
// How hard it strokes: 1 a sea lion cruising, 0 its flippers held still.
uniform float sway = 1.0;
// Gliding: how far the fore flippers are folded back along its sides (0 out like wings, 1 back).
uniform float fold = 0.0;
// Turning: how far the body is bent round to one side behind the head, in radians from the neck
// to the hind flippers (more than 0 and its tail comes round to +X, its left).
uniform float curl = 0.0;
// Diving and rising: the same, up (more than 0: its tail comes up) or down.
uniform float arch = 0.0;
// The mouth: 0 shut, 1 wide open.
uniform float gape = 0.0;
// A bull's forehead bump: 0 none (a cow or a young one), 1 a full grown bull's.
uniform float crest = 0.0;

// The coat, the paler chest and belly, the muzzle, the pale top of a bull's crest.
uniform vec3 coat : source_color = vec3(0.19, 0.105, 0.055);
uniform vec3 coat_pale : source_color = vec3(0.36, 0.23, 0.13);
uniform vec3 muzzle : source_color = vec3(0.33, 0.25, 0.19);
uniform vec3 crest_pale : source_color = vec3(0.5, 0.38, 0.25);
// The bare hide of its flippers, its nose and lips, the inside of its mouth, its teeth, whiskers.
uniform vec3 hide : source_color = vec3(0.06, 0.054, 0.052);
uniform vec3 nose : source_color = vec3(0.03, 0.027, 0.028);
uniform vec3 mouth_inside : source_color = vec3(0.62, 0.3, 0.3);
uniform vec3 tooth : source_color = vec3(0.9, 0.86, 0.72);
uniform vec3 whiskers : source_color = vec3(0.6, 0.55, 0.45);
// How wet it looks: 1 just out of a dive (dark and shining), 0 dry fur (paler, dull).
uniform float wet = 0.8;
// The cartoon eye (0 the eye as it is, 1 the cartoon one: bigger, bright and eager, a warm brown
// iris with a pear-shaped pupil, the white showing round it, the upper lid raised towards the
// front); where both eyes look (x towards its nose, y up, -1..1); its lids (0 open, 1 shut: they
// work with either eye).
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
uniform vec3 iris : source_color = vec3(0.36, 0.2, 0.08);

varying vec3 rest;
varying vec3 rest_normal;
varying float kind;
varying vec2 extra;
varying float moved;

vec3 hash3(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.xxy + p.yxx) * p.zyx);
}

float noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(hash3(i).x, hash3(i + vec3(1.0, 0.0, 0.0)).x, f.x);
	float b = mix(hash3(i + vec3(0.0, 1.0, 0.0)).x, hash3(i + vec3(1.0, 1.0, 0.0)).x, f.x);
	float c = mix(hash3(i + vec3(0.0, 0.0, 1.0)).x, hash3(i + vec3(1.0, 0.0, 1.0)).x, f.x);
	float d = mix(hash3(i + vec3(0.0, 1.0, 1.0)).x, hash3(i + vec3(1.0, 1.0, 1.0)).x, f.x);
	return mix(mix(a, b, f.y), mix(c, d, f.y), f.z);
}

// How far the middle line of the body is lifted, `xm` metres behind the nose: it rides its
// stroke, the chest rising as the flippers come down, the hips following.
float up_at(float xm) {
	float s = xm / LENGTH;
	float reach = LENGTH * (0.006 + 0.022 * s * s);
	return sway * (1.0 - fold) * reach * sin(TURN * (phase - 0.1 - s * 0.55));
}

vec3 turned(vec3 p, vec3 axis, float a) {
	return p * cos(a) + cross(axis, p) * sin(a) + axis * dot(axis, p) * (1.0 - cos(a));
}

// The body behind the head laid round an arc: to one side (`curl`) and up or down (`arch`).
void bend(inout vec3 v, inout vec3 n, float sideways, float upward) {
	float from = -0.25 * LENGTH;
	float d = v.z - from;
	if (d <= 0.0) {
		return;
	}
	if (abs(sideways) > 0.001) {
		float k = sideways / (0.75 * LENGTH);
		float a = d * k;
		float r = 1.0 / k;
		n = vec3(n.x * cos(a) + n.z * sin(a), n.y, -n.x * sin(a) + n.z * cos(a));
		v = vec3(r + (v.x - r) * cos(a), v.y, from + (r - v.x) * sin(a));
		d = v.z - from;
	}
	if (abs(upward) > 0.001 && d > 0.0) {
		float k = upward / (0.75 * LENGTH);
		float a = d * k;
		float r = 1.0 / k;
		n = vec3(n.x, n.y * cos(a) + n.z * sin(a), -n.y * sin(a) + n.z * cos(a));
		v = vec3(v.x, r + (v.y - r) * cos(a), from + (r - v.y) * sin(a));
	}
}

void vertex() {
	kind = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	int group = int(UV2.y * 8.0 + 0.5);
	moved = float(group);
	vec3 hinge = (vec3(UV2.x, UV.y, UV.x) - 0.5) * LENGTH;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	rest = v;
	rest_normal = n;
	if (kind == 1.0 && cartoon_eyes > 0.0) {
		// The cartoon eye: the dome made bigger about its own middle, its rim kept down on the
		// skin of the head (which curves away under a bigger eye).
		float g = mix(1.0, EYE_GROW, clamp(cartoon_eyes, 0.0, 1.0));
		vec3 p = vec3(abs(v.x), v.yz) - EYE_MID;
		float o = dot(p, EYE_OUT) * g - (g * g - g) * EYE_SAG * extra.y * extra.y;
		p = EYE_MID + (EYE_AHEAD * dot(p, EYE_AHEAD) + EYE_UP * dot(p, EYE_UP)) * g + EYE_OUT * o;
		v = vec3(v.x < 0.0 ? -p.x : p.x, p.yz);
	}
	if (group == 0) {
		// A bull's crest: the top of the skull raised in a bump over the forehead.
		float xm = v.z + HALF;
		float bump = exp(-pow((xm - 0.225) / 0.065, 2.0)) * exp(-pow(v.x / 0.065, 2.0)) * smoothstep(0.2, 0.95, n.y) * step(kind, 0.5);
		v.y += clamp(crest, 0.0, 1.0) * 0.048 * bump;
	} else if (group == 1) {
		// The lower jaw swings down about its hinge; the skin between the corner of the mouth
		// and the hinge stretches.
		float a = -clamp(gape, 0.0, 1.0) * 0.7 * (1.0 - smoothstep(CORNER, HINGE_X, v.z + HALF));
		v = hinge + turned(v - hinge, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	} else if (group <= 3) {
		// A fore flipper's stroke: up and forward, then down and back to the belly, its tip a
		// little behind its root; it twists, leading edge down, as it comes down. `fold` lays it
		// back along the body instead.
		float side = group == 2 ? 1.0 : -1.0;
		float along = extra.y;
		float w = TURN * (phase - 0.09 * along);
		float go = clamp(sway, 0.0, 1.5) * (1.0 - fold);
		float flap = go * (0.62 * cos(w) - 0.28) - 0.3 * fold;
		float sweep = go * (0.3 - 0.5 * cos(w - 0.9)) + 0.85 * fold;
		float twist = go * 0.55 * sin(w) * smoothstep(0.0, 0.5, along);
		vec3 span = vec3(side * SPAN.x, SPAN.y, SPAN.z);
		vec3 d = turned(v - hinge, span, side * twist);
		n = turned(n, span, side * twist);
		d = turned(d, vec3(0.0, 0.0, 1.0), side * flap);
		n = turned(n, vec3(0.0, 0.0, 1.0), side * flap);
		d = turned(d, vec3(0.0, 1.0, 0.0), -side * sweep);
		n = turned(n, vec3(0.0, 1.0, 0.0), -side * sweep);
		v = hinge + d;
	} else {
		// The hind flippers trail, tipping up and down a little behind the body's ride.
		float a = clamp(sway, 0.0, 1.5) * (1.0 - fold) * 0.22 * sin(TURN * (phase - 0.75)) * smoothstep(0.0, 0.6, extra.y);
		v = hinge + turned(v - hinge, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	}
	// The ride: each cross-section moved to the body's line and turned to stay square to it.
	float xm = v.z + HALF;
	float zc = clamp(xm, 0.0, LENGTH);
	float g = up_at(zc);
	float pitch = atan((up_at(zc + 0.01) - up_at(zc - 0.01)) / 0.02);
	vec3 o = vec3(v.x, v.y, xm - zc);
	v = vec3(o.x, g + o.y * cos(pitch) + o.z * sin(pitch), zc - HALF - o.y * sin(pitch) + o.z * cos(pitch));
	n = vec3(n.x, n.y * cos(pitch) + n.z * sin(pitch), -n.y * sin(pitch) + n.z * cos(pitch));
	bend(v, n, curl, arch);
	VERTEX = v;
	NORMAL = n;
}

float to_segment(vec2 p, vec2 a, vec2 b) {
	vec2 d = b - a;
	return length(p - a - d * clamp(dot(p - a, d) / dot(d, d), 0.0, 1.0));
}

void fragment() {
	// (where on the eye, in its own flat: x towards the nose, y up, 1 at its rim; and where the
	// cartoon eye's highlight goes: towards a light above and a little to the left of the
	// onlooker, however the animal is turned. Worked out for every point, so that the screen
	// slopes it needs are sound at the eye's edge.)
	vec2 eye_q = vec2(dot(vec3(abs(rest.x), rest.yz) - EYE_MID, EYE_AHEAD), dot(vec3(abs(rest.x), rest.yz) - EYE_MID, EYE_UP)) / EYE_R;
	vec2 eye_spot = vec2(0.24, 0.32);
	{
		vec2 qx = dFdx(eye_q);
		vec2 qy = dFdy(eye_q);
		vec3 jx = dFdx(VERTEX);
		vec3 jy = dFdy(VERTEX);
		float det = qx.x * qy.y - qx.y * qy.x;
		if (abs(det) > 1e-9) {
			vec3 light = normalize(vec3(-0.35, 0.85, 0.4));
			vec2 t = vec2(dot(light, normalize(jx * qy.y - jy * qx.y) * sign(det)), dot(light, normalize(jy * qx.x - jx * qy.x) * sign(det)));
			eye_spot = t / max(length(t), 0.001) * 0.4;
		}
	}
	int k = int(kind + 0.5);
	float glance = 1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	float xm = rest.z + HALF;
	float shine = clamp(wet, 0.0, 1.0);
	vec3 c;
	float rough = 0.5;
	float spec = 0.5;
	vec3 glow = vec3(0.0);
	if (k == 0) {
		// The coat: short sleek hairs lying back along the body.
		float hair = 0.6 * noise3(rest * vec3(480.0, 480.0, 80.0)) + 0.4 * noise3(rest * vec3(1000.0, 1000.0, 180.0) + 7.0);
		float cloud = noise3(rest * 7.0);
		float up = rest_normal.y;
		c = mix(coat, coat_pale, smoothstep(0.0, -0.9, up + (cloud - 0.5) * 0.4) * 0.55);
		c = mix(c, coat_pale, (cloud - 0.5) * 0.3 + 0.1);
		// The face: a paler, greyer muzzle; a bull's crest goes pale on top.
		float snout = (1.0 - smoothstep(0.05, 0.16, xm)) * smoothstep(0.9, -0.3, up);
		c = mix(c, muzzle, snout * 0.7);
		float top = exp(-pow((xm - 0.235) / 0.07, 2.0)) * exp(-pow(rest.x / 0.055, 2.0)) * smoothstep(0.3, 0.95, up);
		c = mix(c, crest_pale, top * clamp(crest, 0.0, 1.0) * 0.7);
		c *= 0.86 + 0.28 * hair;
		// The nose: a black pad on the tip of the muzzle, a slit of a nostril on each side.
		vec2 face = vec2(abs(rest.x), rest.y);
		float pad = (1.0 - smoothstep(0.8, 1.0, length((face - vec2(0.0, 0.0065)) / vec2(0.0125, 0.0095)))) * (1.0 - smoothstep(0.01, 0.016, xm));
		c = mix(c, nose, pad);
		float slit = to_segment(face, vec2(0.003, 0.004), vec2(0.008, 0.0105));
		c = mix(c, vec3(0.0), (1.0 - smoothstep(0.0009, 0.002, slit)) * (1.0 - smoothstep(0.01, 0.016, xm)));
		c = mix(c, nose, (1.0 - smoothstep(0.0006, 0.0016, abs(rest.x))) * (1.0 - smoothstep(0.004, 0.012, xm)) * (1.0 - smoothstep(-0.004, 0.0, rest.y)) * 0.8);
		// The lips' dark edge, and the inside of the mouth: pink, dark down the throat.
		float lip_edge = moved < 1.5 ? extra.y : 0.0;
		float lined = smoothstep(0.55, 1.0, extra.x);
		vec3 lining = mix(mouth_inside, mouth_inside * 0.25, smoothstep(CORNER - 0.02, CORNER + 0.02, xm));
		c = mix(c, lining, lined);
		c = mix(c, nose * 0.8, smoothstep(0.3, 0.9, lip_edge) * 0.92);
		glow = lining * 0.12 * lined;
		// (wet fur is dark and shines; where light glances off it, a sheen)
		c *= mix(1.25, 0.7, shine * (1.0 - lined));
		c += vec3(0.09, 0.08, 0.07) * glance * glance * shine;
		rough = mix(0.8, 0.42 + 0.14 * hair, shine);
		spec = mix(0.25, 0.45, shine);
		rough = mix(rough, 0.22, max(pad, lined));
	} else if (k == 1) {
		// An eye: dark and wet; a little brown shows towards its rim.
		float r = extra.y;
		c = mix(vec3(0.004, 0.004, 0.005), vec3(0.09, 0.05, 0.02), smoothstep(0.45, 0.8, r) * 0.8);
		c = mix(c, nose, smoothstep(0.86, 1.0, r));
		rough = 0.06;
		spec = 0.8;
		vec2 q = eye_q;
		float toon = clamp(cartoon_eyes, 0.0, 1.0);
		if (toon > 0.0) {
			// The cartoon eye, a sea lion's: bright and eager. A warm brown iris with a
			// pear-shaped pupil (round below, narrowing upwards), a clean white round it that
			// shows as it looks about, a highlight towards the light that stays put, a dark rim.
			float far = max(length(q), r);
			vec2 at = q - clamp(eye_look, vec2(-1.0), vec2(1.0)) * 0.3;
			float d = length(at);
			vec3 e = vec3(0.95, 0.94, 0.9);
			e = mix(e, iris * (0.5 + 0.7 * smoothstep(0.6, 0.15, d)), 1.0 - smoothstep(0.6, 0.64, d));
			float pear = min(d / 0.3, length((at - vec2(0.0, 0.17)) / vec2(0.15, 0.3)));
			e = mix(e, vec3(0.008, 0.007, 0.008), 1.0 - smoothstep(0.9, 1.0, pear));
			e = mix(e, vec3(0.03, 0.02, 0.015), smoothstep(0.86, 0.92, far));
			float shine = 1.0 - smoothstep(0.13, 0.17, length(q - eye_spot * 0.9));
			shine = max(shine, 1.0 - smoothstep(0.05, 0.07, length(q + eye_spot * 0.65)));
			e = mix(e, vec3(1.0), shine);
			glow = mix(glow, vec3(0.8) * shine, toon);
			c = mix(c, e, toon);
			rough = mix(rough, 0.12, toon);
			spec = mix(spec, 0.5, toon);
		}
		// The lids: the upper one comes down in an arch, the lower one up a little, and they meet
		// just below the middle. The cartoon eye's upper lid sits high, higher towards the front
		// (an eager, raised look).
		float shut = clamp(blink, 0.0, 1.0);
		float top = mix(mix(1.3, 0.86, toon) + 0.12 * toon * q.x, -0.12, shut) - mix(0.22, 0.15, shut) * q.x * q.x;
		float bottom = mix(-1.3, -0.12, shut) + mix(0.15, -0.15, shut) * q.x * q.x;
		float lid = max(smoothstep(top - 0.03, top + 0.03, q.y), 1.0 - smoothstep(bottom - 0.03, bottom + 0.03, q.y));
		float lash = 1.0 - smoothstep(0.03, 0.09, min(abs(q.y - top), abs(q.y - bottom)));
		c = mix(c, coat * 0.8, lid);
		c = mix(c, vec3(0.02), lash * max(lid, toon) * step(length(q), 1.05));
		glow *= 1.0 - lid;
		rough = mix(rough, 0.6, lid);
	} else if (k == 2) {
		c = mix(tooth * vec3(0.85, 0.72, 0.5), tooth, smoothstep(0.0, 0.5, extra.y));
		rough = 0.25;
	} else if (k == 3) {
		c = mouth_inside * (0.85 + 0.3 * noise3(rest * 600.0));
		glow = c * 0.1;
		rough = 0.25;
	} else if (k == 4) {
		c = whiskers;
		rough = 0.4;
	} else {
		// Bare hide: black, creased across; the hind flippers ridged along their toes.
		float crease = noise3(rest * vec3(60.0, 60.0, 260.0));
		c = hide * (0.7 + 0.6 * crease);
		c += vec3(0.05, 0.05, 0.055) * glance * glance * shine;
		rough = mix(0.7, 0.42 + 0.2 * crease, shine);
		spec = mix(0.3, 0.45, shine);
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = glow;
}
