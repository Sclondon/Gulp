shader_type spatial;
// GameCommon's sea turtles (sea_turtle.gd): the shell's plates and pattern, the scales, the beak and the eyes drawn
// here (no texture files); the fore flippers' stroke, the hind flippers' steering, the beak opening, the head
// turning and drawn in, the banking and pitching. One shader for all four types: SeaTurtle sets each type's numbers
// (its TYPES and EYES).
//
// What each point is comes from the model (tools/build_sea_turtle.py): COLOR.r what it is made of, as a tenth (0 the
// skin of the head and neck, 1 an eye, 2 a claw, 3 the tongue, 4 the carapace, 5 the plastron and the rim's
// underside, 6 the skin of a flipper); COLOR.g on the head how far inside the mouth it is, on the shell how far round
// the rim its nearest rim point is (0 front middle, 1 back middle); COLOR.b on a flipper how far along it, on an eye
// 0 its middle to 1 its rim, on the head and jaw how far from the line of the mouth (0.5 + 1.25 x head lengths);
// UV2.y what moves it, as an eighth (0 nothing, 1 the lower jaw, 2 and 3 the left and right fore flippers, 4 and 5
// the left and right hind flippers, 6 the head and neck); for a moving part UV.x, UV.y and UV2.x its hinge (z, y, x,
// as metres / 4 plus a half); on the shell UV.x half the shell's width there and UV.y how far from the rim, in shell
// lengths (seen from above).
//
// Everything that moves is a function of `phase` alone, so a picture of it loops exactly. Nothing here needs more
// than GL Compatibility has.
render_mode cull_back;

const float TURN = 6.2831853;
const float SPAN_M = 4.0;

// How far through a stroke it is (0..1, it wraps). Set by SeaTurtle.
uniform float phase = 0.0;
// How hard it strokes: 1 cruising, 0 its flippers held still.
uniform float sway = 1.0;
// Turning: more than 0 turns it to its left (+X). It banks (rolls its left side down by half of `curl`, radians),
// turns its head into the turn (0.45 of it at the head) and swings its hind flippers' tips round to its left (0.6 of
// it), as a rudder.
uniform float curl = 0.0;
// Diving and rising: more than 0 its tail comes up and its nose goes down. It pitches (0.4 of `arch`, radians), its
// head bends down a little more (0.3 of it) and its hind flippers lift (0.5 of it).
uniform float arch = 0.0;
// The beak: 0 shut, 1 wide open.
uniform float gape = 0.0;
// Drawn in: 0 out, 1 its head and neck drawn back as far as a sea turtle can (a little) and dipped, its fore flippers
// swept back along its sides, its hind flippers drawn in; it strokes more weakly.
uniform float tuck = 0.0;

// This type's model (SeaTurtle.TYPES; the build script prints them): its shell's length, where the tip of its beak
// is, its head's length, where its neck bends (from the head back to the shell), the neck's pivot, how far the head
// draws back, where the corner of the mouth is, how far the jaw opens, the way a fore flipper runs out.
uniform float shell_length = 1.1;
uniform float nose_z = -0.71;
uniform float head_length = 0.165;
uniform float neck_front = -0.55;
uniform float neck_back = -0.46;
uniform vec3 neck_pivot = vec3(0.0, -0.044, -0.55);
uniform float tuck_back = 0.07;
uniform float mouth_corner = -0.64;
uniform float jaw_open = 0.55;
uniform vec3 fore_span = vec3(0.95, -0.11, 0.29);
// The shell's plates (as the build script lays them out: its `scute`): 1 a hard shell of plates, 0 none (the
// leatherback); the middle row's half width as a share of the shell's; the rim plates' ring, how wide (shell
// lengths); how many rim plates a side; the rim's length a side (shell lengths); where the middle row's seams and the
// side plates' seams are (by how far back, 0..1; 2 none); how the side seams fan out; the plastron's seams.
uniform float hard_shell = 1.0;
uniform float plate_vw = 0.3;
uniform float plate_mw = 0.062;
uniform float plate_nm = 12.5;
uniform float rim_len = 1.46;
uniform vec4 vert_seams = vec4(0.25, 0.43, 0.6, 0.77);
uniform vec4 side_seams = vec4(0.31, 0.52, 0.73, 2.0);
uniform float plate_slant = 0.9;
uniform vec4 plastron_seams = vec4(0.16, 0.34, 0.6, 0.82);
// How its plates are patterned: 0 a green's starbursts, 1 a hawksbill's tortoiseshell, 2 a loggerhead's plain
// reddish brown, 3 a leatherback's white speckles.
uniform int pattern = 0;

// Colours: the shell's base, its dark and light streaks, its seams; the plastron; the skin's scales above, their
// pale edges, the skin below; the beak; the inside of the mouth; the claws.
uniform vec3 shell_base : source_color = vec3(0.33, 0.27, 0.13);
uniform vec3 shell_dark : source_color = vec3(0.12, 0.08, 0.04);
uniform vec3 shell_light : source_color = vec3(0.62, 0.52, 0.24);
uniform vec3 seam : source_color = vec3(0.7, 0.62, 0.38);
uniform vec3 plastron : source_color = vec3(0.86, 0.8, 0.58);
uniform vec3 scale_dark : source_color = vec3(0.2, 0.14, 0.08);
uniform vec3 scale_edge : source_color = vec3(0.78, 0.7, 0.45);
uniform vec3 skin_under : source_color = vec3(0.8, 0.74, 0.55);
uniform vec3 beak : source_color = vec3(0.6, 0.52, 0.34);
uniform vec3 mouth_inside : source_color = vec3(0.62, 0.38, 0.36);
uniform vec3 claw_colour : source_color = vec3(0.5, 0.45, 0.32);
// How big the scales on its head are (metres; those on the neck and flippers are smaller), and how much they show
// (0: smooth skin, the leatherback's).
uniform float scale_size = 0.022;
uniform float scales = 1.0;
// White speckles (the leatherback's), and its pink spot on top of its head.
uniform float speckles = 0.0;
uniform float pink_spot = 0.0;

// The cartoon eye: 0 the eye as it is, 1 the cartoon one (bigger, a clean white, an iris, a big round pupil, a
// highlight, and heavy lids: old and kind). Where both eyes look (x towards its beak, y up, -1..1); its lids (0 open,
// 1 shut: they work with either eye).
uniform float cartoon_eyes = 0.0;
uniform vec2 eye_look = vec2(0.0);
uniform float blink = 0.0;
// This type's eye (SeaTurtle.EYES; the build script prints where it is): its middle on the skin, the way it faces,
// the way to the beak and up across it, its radius, how far its rim lies below a flat across it, how much bigger the
// cartoon eye is; its iris's colour and size, the pupil's size; where its upper lid hangs (1 at the top of the eye,
// 0 its middle), how much it droops towards the back, where the lower lid comes up to (-1 the bottom).
uniform vec3 eye_mid = vec3(0.04, -0.019, -0.654);
uniform vec3 eye_out = vec3(0.8975, 0.389, -0.2078);
uniform vec3 eye_ahead = vec3(-0.1906, -0.0826, -0.9782);
uniform vec3 eye_up = vec3(-0.3976, 0.9175, 0.0);
uniform float eye_r = 0.014;
uniform float eye_sag = 0.002;
uniform float eye_grow = 1.7;
uniform vec3 iris : source_color = vec3(0.3, 0.18, 0.08);
uniform float iris_size = 0.62;
uniform float pupil_size = 0.5;
uniform float lid_top = 0.35;
uniform float lid_droop = 0.15;
uniform float lid_low = -0.8;

varying vec3 rest;
varying vec3 rest_normal;
varying float kind;
varying vec2 extra;
varying vec2 shell_at;
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

vec3 turned(vec3 p, vec3 axis, float a) {
	return p * cos(a) + cross(axis, p) * sin(a) + axis * dot(axis, p) * (1.0 - cos(a));
}

void vertex() {
	kind = floor(COLOR.r * 10.0 + 0.5);
	extra = COLOR.gb;
	shell_at = UV;
	int group = int(UV2.y * 8.0 + 0.5);
	moved = float(group);
	vec3 hinge = (vec3(UV2.x, UV.y, UV.x) - 0.5) * SPAN_M;
	vec3 v = VERTEX;
	vec3 n = NORMAL;
	rest = v;
	rest_normal = n;
	float go = clamp(sway, 0.0, 1.5) * (1.0 - 0.5 * clamp(tuck, 0.0, 1.0));
	float tk = clamp(tuck, 0.0, 1.0);
	if (kind == 1.0 && cartoon_eyes > 0.0) {
		// The cartoon eye: the dome made bigger about its own middle, its rim kept down on the skin of the head.
		float g = mix(1.0, eye_grow, clamp(cartoon_eyes, 0.0, 1.0));
		vec3 p = vec3(abs(v.x), v.yz) - eye_mid;
		float o = dot(p, eye_out) * g - (g * g - g) * eye_sag * extra.y * extra.y;
		p = eye_mid + (eye_ahead * dot(p, eye_ahead) + eye_up * dot(p, eye_up)) * g + eye_out * o;
		v = vec3(v.x < 0.0 ? -p.x : p.x, p.yz);
	}
	if (group == 1) {
		// The lower beak swings down about its hinge; the skin between the corner of the mouth and the hinge
		// stretches.
		float a = -clamp(gape, 0.0, 1.0) * jaw_open * (1.0 - smoothstep(mouth_corner, hinge.z, v.z));
		v = hinge + turned(v - hinge, vec3(1.0, 0.0, 0.0), a);
		n = turned(n, vec3(1.0, 0.0, 0.0), a);
	}
	if (group == 1 || group == 6) {
		// The head and neck: turned into a turn and bent down in a dive, more towards the head; drawn back.
		float w = 1.0 - smoothstep(neck_front, neck_back, rest.z);
		float yaw = -curl * 0.45 * w;
		float pitch = -(arch * 0.3 + tk * 0.25) * w;
		vec3 d = turned(v - neck_pivot, vec3(0.0, 1.0, 0.0), yaw);
		n = turned(n, vec3(0.0, 1.0, 0.0), yaw);
		d = turned(d, vec3(1.0, 0.0, 0.0), pitch);
		n = turned(n, vec3(1.0, 0.0, 0.0), pitch);
		v = neck_pivot + d + vec3(0.0, -0.12, 1.0) * tk * tuck_back;
	} else if (group == 2 || group == 3) {
		// A fore flipper's stroke: from high and forward, down and back in a strong stroke (phase 0 to 0.5), the
		// blade flat to the water, its leading edge a little down; then up and forward again feathered (0.5 to 1),
		// turned edge on, its leading edge up. Its tip lags its root. `tuck` sweeps it back along the side.
		float side = group == 2 ? 1.0 : -1.0;
		float along = extra.y;
		float w = TURN * (phase - 0.07 * along);
		float flap = go * (0.6 * cos(w) - 0.05) - 0.15 * tk;
		float sweep = go * (0.05 - 0.42 * cos(w - 0.5)) + 0.55 * tk;
		float feather = smoothstep(-0.3, 0.7, -sin(w - 0.25));
		float twist = go * (-0.18 + 1.25 * feather) * smoothstep(0.0, 0.35, along);
		vec3 span = vec3(side * fore_span.x, fore_span.y, fore_span.z);
		vec3 d = turned(v - hinge, span, side * twist);
		n = turned(n, span, side * twist);
		d = turned(d, vec3(0.0, 0.0, 1.0), side * flap);
		n = turned(n, vec3(0.0, 0.0, 1.0), side * flap);
		d = turned(d, vec3(0.0, 1.0, 0.0), -side * sweep);
		n = turned(n, vec3(0.0, 1.0, 0.0), -side * sweep);
		v = hinge + d;
	} else if (group == 4 || group == 5) {
		// The hind flippers trail, tipping up and down a little with the stroke; they steer (`curl`, `arch`) and
		// draw in (`tuck`).
		float side = group == 4 ? 1.0 : -1.0;
		float lift = -go * 0.14 * sin(TURN * (phase - 0.3)) * smoothstep(0.0, 0.6, extra.y) - clamp(arch, -2.0, 2.0) * 0.5;
		float steer = clamp(curl, -2.0, 2.0) * 0.6 - side * 0.3 * tk;
		vec3 d = turned(v - hinge, vec3(1.0, 0.0, 0.0), lift);
		n = turned(n, vec3(1.0, 0.0, 0.0), lift);
		d = turned(d, vec3(0.0, 1.0, 0.0), steer);
		n = turned(n, vec3(0.0, 1.0, 0.0), steer);
		v = hinge + d;
	}
	// The ride: it rises a little with each power stroke.
	v.y += go * 0.008 * shell_length * sin(TURN * (phase - 0.15));
	// Pitched (`arch`), then banked (`curl`), about its origin.
	float pitch = -clamp(arch, -2.0, 2.0) * 0.4;
	v = turned(v, vec3(1.0, 0.0, 0.0), pitch);
	n = turned(n, vec3(1.0, 0.0, 0.0), pitch);
	float bank = -clamp(curl, -2.0, 2.0) * 0.5;
	v = turned(v, vec3(0.0, 0.0, 1.0), bank);
	n = turned(n, vec3(0.0, 0.0, 1.0), bank);
	VERTEX = v;
	NORMAL = n;
}

// Scales: (how far to the nearest cell's edge, roughly; which cell it is).
vec2 cells(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	float d1 = 8.0;
	float d2 = 8.0;
	float id = 0.0;
	for (int z = -1; z <= 1; z++) {
		for (int y = -1; y <= 1; y++) {
			for (int x = -1; x <= 1; x++) {
				vec3 g = vec3(float(x), float(y), float(z));
				vec3 h = hash3(i + g);
				vec3 r = g + 0.15 + h * 0.7 - f;
				float d = dot(r, r);
				if (d < d1) {
					d2 = d1;
					d1 = d;
					id = h.z;
				} else if (d < d2) {
					d2 = d;
				}
			}
		}
	}
	return vec2(sqrt(d2) - sqrt(d1), id);
}

// The plate at a place on the carapace (as the build script has it, `scute`): s how far back, a how far out, w the
// shell's half width there, e how far from the rim (shell lengths), p how far round the rim. Returns (how far to its
// nearest seam, how far from its front edge to its rear one, which plate, which row: 0 the rim, 1 the middle, 2 the
// sides); `local` is where it is from the plate's growing point.
vec4 scute(float s, float a, float w, float e, float p, out vec2 local) {
	if (e < plate_mw) {
		float q = p * plate_nm + 0.5;
		float fr = fract(q);
		float seg = rim_len / plate_nm;
		local = vec2((fr - 0.8) * seg, e - plate_mw * 0.15);
		return vec4(min(plate_mw - e, min(fr, 1.0 - fr) * seg), fr, floor(q), 0.0);
	}
	float vw = plate_vw * w;
	if (a < vw) {
		float b0 = 0.0;
		float b1 = vert_seams.x;
		float k = 0.0;
		if (s >= vert_seams.x) { b0 = vert_seams.x; b1 = vert_seams.y; k = 1.0; }
		if (s >= vert_seams.y) { b0 = vert_seams.y; b1 = vert_seams.z; k = 2.0; }
		if (s >= vert_seams.z) { b0 = vert_seams.z; b1 = vert_seams.w; k = 3.0; }
		if (s >= vert_seams.w) { b0 = vert_seams.w; b1 = 1.0; k = 4.0; }
		local = vec2(a, s - (b0 + 0.68 * (b1 - b0)));
		return vec4(min(min(vw - a, e - plate_mw), min(s - b0, b1 - s)), (s - b0) / (b1 - b0), 20.0 + k, 1.0);
	}
	float cs = 0.5 + (s - 0.5) / (1.0 + plate_slant * (a / max(w, 1e-6) - plate_vw));
	float c0 = 0.0;
	float c1 = side_seams.x;
	float k = 0.0;
	if (cs >= side_seams.x) { c0 = side_seams.x; c1 = side_seams.y < 1.5 ? side_seams.y : 1.0; k = 1.0; }
	if (side_seams.y < 1.5 && cs >= side_seams.y) { c0 = side_seams.y; c1 = side_seams.z < 1.5 ? side_seams.z : 1.0; k = 2.0; }
	if (side_seams.z < 1.5 && cs >= side_seams.z) { c0 = side_seams.z; c1 = side_seams.w < 1.5 ? side_seams.w : 1.0; k = 3.0; }
	if (side_seams.w < 1.5 && cs >= side_seams.w) { c0 = side_seams.w; c1 = 1.0; k = 4.0; }
	local = vec2(a - vw - 0.12 * (w - vw), cs - (c0 + 0.62 * (c1 - c0)));
	return vec4(min(min(a - vw, e - plate_mw), min(cs - c0, c1 - cs)), (cs - c0) / (c1 - c0), 40.0 + k, 2.0);
}

void fragment() {
	// (where on the eye, in its own flat: x towards the beak, y up, 1 at its rim; and where the cartoon eye's
	// highlight goes: towards a light above and a little to the left of the onlooker, however the turtle is turned)
	vec2 eye_q = vec2(dot(vec3(abs(rest.x), rest.yz) - eye_mid, eye_ahead), dot(vec3(abs(rest.x), rest.yz) - eye_mid, eye_up)) / eye_r;
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
	float L = shell_length;
	float s = (rest.z + 0.5 * L) / L;
	vec3 c;
	float rough = 0.5;
	float spec = 0.5;
	vec3 glow = vec3(0.0);
	if (k == 4) {
		// The carapace.
		float a = abs(rest.x) / L;
		float w = shell_at.x;
		float e = shell_at.y;
		float grain = noise3(rest * vec3(90.0, 30.0, 90.0));
		if (hard_shell > 0.5) {
			vec2 local;
			vec4 sc = scute(s, a, w, e, extra.x, local);
			float id = sc.z;
			float ang = atan(local.y, local.x);
			float r = length(local);
			vec3 h = hash3(vec3(id, sc.w, 3.0));
			vec2 round_ = vec2(cos(ang), sin(ang));
			if (pattern == 0) {
				// A green's starburst: streaks of dark brown and olive-yellow rayed out from each plate's growing
				// point.
				vec2 wob = round_ + vec2(noise3(rest * 14.0), noise3(rest * 14.0 + 9.0)) * 0.9;
				float rays = 0.55 * noise3(vec3(wob * 5.0, id * 1.7)) + 0.45 * noise3(vec3(wob * 11.0, id * 2.3 + r * 9.0));
				c = mix(shell_dark, shell_base, smoothstep(0.3, 0.55, rays));
				c = mix(c, shell_light, smoothstep(0.55, 0.75, rays) * smoothstep(0.01, 0.07, r) * 0.85);
				c = mix(c, shell_dark, (1.0 - smoothstep(0.0, 0.03, r)) * 0.35);
				c = mix(c, shell_base, 0.25);
			} else if (pattern == 1) {
				// A hawksbill's tortoiseshell: amber, flamed and blotched with dark brown, rayed from each plate's
				// growing point.
				float flame = noise3(vec3(round_ * 2.6, id * 1.3) + vec3(0.0, 0.0, r * 14.0));
				flame = 0.65 * flame + 0.35 * noise3(rest * 38.0 + id);
				c = mix(shell_light, shell_base, smoothstep(0.3, 0.45, flame));
				c = mix(c, shell_dark, smoothstep(0.5, 0.6, flame));
				c = mix(c, shell_light * 1.1, smoothstep(0.25, 0.15, flame) * 0.6);
			} else {
				// A loggerhead's: plain reddish brown, a faint grain rayed from each growing point, paler at the
				// plates' edges.
				float rays = noise3(vec3(round_ * 6.0, id * 2.1 + r * 4.0));
				c = mix(shell_base, shell_dark, smoothstep(0.45, 0.75, rays) * 0.6);
				c = mix(c, shell_light, (1.0 - smoothstep(0.0, 0.03, sc.x)) * 0.45);
			}
			c *= 0.88 + 0.24 * grain * (0.9 + 0.2 * h.x);
			// growth rings and the seams
			c *= 0.95 + 0.05 * sin(r * 160.0 + h.y * 6.0);
			float line = 1.0 - smoothstep(0.0015, 0.0045, sc.x);
			c = mix(c, seam, line * 0.85);
			rough = mix(0.38, 0.6, line);
			spec = 0.55;
		} else {
			// The leatherback's leathery back: blue-black, speckled with white, the ridges a little paler.
			float dots = smoothstep(0.8, 0.86, noise3(rest * 130.0)) * 0.9 + smoothstep(0.84, 0.9, noise3(rest * 55.0 + 5.0)) * 0.7;
			c = shell_base * (0.85 + 0.3 * grain);
			c = mix(c, shell_light, clamp(dots * speckles, 0.0, 1.0));
			c = mix(c, shell_dark, smoothstep(0.55, 0.8, noise3(rest * 6.0)) * 0.4);
			rough = 0.32;
			spec = 0.6;
		}
		c += vec3(0.05, 0.05, 0.05) * glance * glance;
	} else if (k == 5) {
		// The plastron and the rim's underside: pale, its plates' seams faint.
		float a = abs(rest.x) / L;
		float e = shell_at.y;
		float grain = noise3(rest * vec3(60.0, 20.0, 60.0));
		c = plastron * (0.9 + 0.15 * grain);
		if (hard_shell > 0.5) {
			float q = extra.x * plate_nm + 0.5;
			float rim_seam = min(fract(q), 1.0 - fract(q)) * rim_len / plate_nm;
			float line = 1.0 - smoothstep(0.0015, 0.004, a);
			line = max(line, 1.0 - smoothstep(0.0015, 0.004, min(min(abs(s - plastron_seams.x), abs(s - plastron_seams.y)), min(abs(s - plastron_seams.z), abs(s - plastron_seams.w)))));
			line *= step(plate_mw * 1.6, e);
			line = max(line, (1.0 - smoothstep(0.0015, 0.004, rim_seam)) * step(e, plate_mw * 1.3));
			c = mix(c, c * 0.6, line);
			// (the rim's underside takes a little of the carapace's colour)
			c = mix(c, shell_base, (1.0 - smoothstep(0.0, plate_mw, e)) * 0.25);
		} else {
			float blot = smoothstep(0.45, 0.65, noise3(rest * 9.0));
			c = mix(c, shell_base, blot * 0.55);
			c = mix(c, shell_light, smoothstep(0.78, 0.84, noise3(rest * 60.0)) * 0.6);
		}
		rough = 0.5;
	} else if (k == 0 || k == 6) {
		// Skin: the head, neck and jaw (0), the flippers (6). Scales: big plates on top of the head, smaller on the
		// neck and flippers; dark middles, pale edges; paler underneath.
		float head_x = (rest.z - nose_z) / head_length;
		float up = rest_normal.y;
		// (two sizes of scale, blended where they meet: a size that changed from point to point would smear them)
		vec2 cell = cells(rest / (scale_size * (k == 0 ? 0.6 : 0.55)) + 11.0);
		float edge_line = 1.0 - smoothstep(0.03, 0.09, cell.x);
		if (k == 0) {
			float big = smoothstep(0.25, 0.6, up) * (1.0 - smoothstep(0.95, 1.15, head_x));
			if (big > 0.01) {
				vec2 big_cell = cells(rest / (scale_size * 1.5));
				edge_line = mix(edge_line, 1.0 - smoothstep(0.02, 0.06, big_cell.x), big);
				cell.y = mix(cell.y, big_cell.y, step(0.5, big));
			}
		}
		float below = smoothstep(0.1, -0.5, up);
		vec3 top_c = scale_dark * (0.8 + 0.4 * cell.y);
		c = mix(top_c, scale_edge, edge_line * scales);
		c = mix(c, mix(skin_under, skin_under * 0.85, edge_line * scales), below);
		if (scales < 0.5) {
			// (smooth skin: dark above, blotched paler below, speckled)
			c = mix(scale_dark, skin_under, below * smoothstep(0.3, 0.55, 0.6 * noise3(rest * 30.0) + 0.4 * noise3(rest * 9.0)));
			c = mix(c, shell_light, smoothstep(0.8, 0.86, noise3(rest * 140.0)) * speckles);
		}
		if (k == 0) {
			// The beak: horny, over the edges of both jaws; its edge darker.
			float from_mouth = (extra.y - 0.5) / 1.25;
			float depth = 0.1 * (1.0 - smoothstep(0.55, 1.0, head_x / 0.46)) + 0.04 * (1.0 - smoothstep(0.0, 0.12, head_x));
			float horn = (1.0 - smoothstep(depth - 0.01, depth + 0.01, from_mouth)) * step(extra.x, 0.5);
			c = mix(c, beak * (0.9 + 0.2 * noise3(rest * 150.0)), horn);
			c = mix(c, beak * 0.4, horn * (1.0 - smoothstep(0.0, 0.02, from_mouth)));
			// the nostrils
			vec2 nose = vec2(abs(rest.x) / head_length - 0.06, head_x - 0.045);
			float nostril = (1.0 - smoothstep(0.012, 0.022, length(nose))) * step(0.2, from_mouth) * step(0.0, -rest_normal.z);
			c = mix(c, vec3(0.02), nostril);
			// the leatherback's pink spot on top of its head
			float spot = (1.0 - smoothstep(0.08, 0.14, length(vec2(rest.x / head_length, head_x - 0.62)))) * smoothstep(0.5, 0.8, up);
			c = mix(c, vec3(0.75, 0.45, 0.45), spot * pink_spot);
			// inside the mouth: pink, dark down the throat
			float lined = smoothstep(0.55, 1.0, extra.x);
			vec3 lining = mix(mouth_inside, mouth_inside * 0.25, smoothstep(mouth_corner - 0.02, mouth_corner + 0.03, rest.z));
			c = mix(c, lining, lined);
			glow = lining * 0.1 * lined;
			rough = mix(0.55, 0.3, max(horn, lined));
		} else {
			// (a flipper's trailing edge is paler)
			rough = 0.5;
		}
		c += vec3(0.04) * glance * glance;
	} else if (k == 1) {
		// An eye: dark and wet, a little brown towards its rim.
		float r = extra.y;
		c = mix(vec3(0.005, 0.004, 0.004), iris * 0.4, smoothstep(0.45, 0.8, r) * 0.8);
		c = mix(c, scale_dark, smoothstep(0.88, 1.0, r));
		rough = 0.06;
		spec = 0.8;
		vec2 q = eye_q;
		float toon = clamp(cartoon_eyes, 0.0, 1.0);
		if (toon > 0.0) {
			// The cartoon eye, a sea turtle's: old and kind. A warm iris, a big round pupil, a clean white, a soft
			// highlight that stays put, a dark rim.
			float far = max(length(q), r);
			vec2 at = q - clamp(eye_look, vec2(-1.0), vec2(1.0)) * 0.28;
			float d = length(at);
			vec3 e = vec3(0.95, 0.93, 0.88);
			e = mix(e, iris * (0.55 + 0.75 * smoothstep(iris_size, 0.1, d)), 1.0 - smoothstep(iris_size - 0.03, iris_size + 0.01, d));
			e = mix(e, vec3(0.01, 0.008, 0.008), 1.0 - smoothstep(pupil_size * iris_size - 0.03, pupil_size * iris_size + 0.01, d));
			e = mix(e, vec3(0.04, 0.03, 0.02), smoothstep(0.86, 0.93, far));
			float shine = 1.0 - smoothstep(0.12, 0.16, length(q - eye_spot * 0.85));
			shine = max(shine, 1.0 - smoothstep(0.045, 0.065, length(q + eye_spot * 0.6)));
			e = mix(e, vec3(1.0), shine);
			glow = mix(glow, vec3(0.7) * shine, toon);
			c = mix(c, e, toon);
			rough = mix(rough, 0.12, toon);
			spec = mix(spec, 0.5, toon);
		}
		// The lids: the upper one hangs heavy (lower towards the back of the eye: x below 0), the lower one comes
		// up a little; they meet just below the middle when it blinks. A crease above the upper lid.
		float shut = clamp(blink, 0.0, 1.0);
		float hang = mix(1.3, lid_top, toon) - lid_droop * toon * clamp(-q.x, 0.0, 1.0);
		float top = mix(hang, -0.12, shut) - mix(0.2, 0.12, shut) * q.x * q.x;
		float bottom = mix(mix(-1.3, lid_low, toon), -0.12, shut) + mix(0.18, -0.12, shut) * q.x * q.x;
		float lid = max(smoothstep(top - 0.03, top + 0.03, q.y), 1.0 - smoothstep(bottom - 0.03, bottom + 0.03, q.y));
		float lash = 1.0 - smoothstep(0.03, 0.09, min(abs(q.y - top), abs(q.y - bottom)));
		float crease = (1.0 - smoothstep(0.02, 0.06, abs(q.y - top - 0.22 - 0.05 * q.x * q.x))) * toon * (1.0 - shut);
		// (the heavy lid's shadow on the eye under it)
		c *= mix(1.0, 0.55 + 0.45 * smoothstep(top - 0.3, top - 0.02, top - q.y), toon * (1.0 - lid));
		c = mix(c, scale_dark * 0.9 + scale_edge * 0.1, lid);
		c = mix(c, scale_dark * 0.5, crease * lid);
		c = mix(c, vec3(0.03, 0.02, 0.015), lash * max(lid, toon) * step(length(q), 1.05));
		glow *= 1.0 - lid;
		rough = mix(rough, 0.55, lid);
	} else if (k == 2) {
		c = claw_colour * (0.8 + 0.3 * noise3(rest * 300.0));
		rough = 0.35;
	} else {
		c = mouth_inside * (0.85 + 0.3 * noise3(rest * 600.0));
		glow = c * 0.1;
		rough = 0.25;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = spec;
	EMISSION = glow;
}
