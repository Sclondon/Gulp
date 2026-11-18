shader_type spatial;
// The crinoids (crinoid.gd): their colours, the pinnules drawn on cards, and all of their moving. What
// each point is comes from the model (tools/build_crinoid.py): UV2.y the part (0 the cup, 1 an arm's stem,
// 2 a pinnule strip, 3 a cirrus on the cup, 4 a card of pinnules on an arm's +X side, 5 on its other side,
// 6 the stalk, 7 a cirrus on the stalk, 8 the holdfast), UV2.x which arm (k / n). UV: on an arm's stem x how
// far along it; on a pinnule x where along its arm it stands, y from its root to its tip; on a card x how far
// along the arm, y how far out (of `card_width`); on a cirrus y root to tip; on the stalk y how high.
//
// Each arm bends about its root on the cup, from where each point is: it sways with the current (the
// global `water_clock`, seconds, so that every crinoid in the sea sways with the same water, each a little
// out of step by where it stands), `furl` rolls every arm up and in until it is a ball, and `swim` has
// the arms beat down in turn (half of them, then the other half) as a feather star swims, on `phase`.
// A sea lily's stalk leans and sways with the current too, carrying its crown.
// The cards draw the very pinnules the full model has as strips (the same places, lengths and angles: the
// build script's PIN_* numbers), cut out with an alpha scissor.
// Drawn from both sides (the strips and cards are single sheets). Nothing here needs more than GL
// Compatibility has.
render_mode cull_disabled;

global uniform float water_clock;

// How far through a swimming stroke (0..1, it wraps). Set by Crinoid.
uniform float phase = 0.0;
// How much the current sways it (1 as it lives, 0 still).
uniform float sway = 1.0;
// 0 its arms spread, 1 every arm rolled up and in, the whole animal a ball.
uniform float furl : hint_range(0.0, 1.0) = 0.0;
// 0 still, 1 swimming: its arms beating down in turn.
uniform float swim : hint_range(0.0, 1.0) = 0.0;
// The kind's shape, as the model is built: an arm's length, how many arms, how steeply they rise from the
// cup (radians), where they leave it (radius and height), the stalk's height (0: none).
uniform float arm_length = 0.15;
uniform float arms = 10.0;
uniform float arm_rise = 0.6;
uniform float root_radius = 0.0065;
uniform float root_height = 0.0205;
uniform float stalk_height = 0.0;
// How its arms lie at rest (radians, + up and in): along the whole arm and in its outer half.
uniform float rest_bend = -0.55;
uniform float tip_bend = -0.45;
// The pinnules, as the build script makes them (PIN_GAP, PIN_ANGLE, the longest, where the first stands,
// and the card's width).
uniform float pin_gap = 0.0028;
uniform float pin_angle = 0.8;
uniform float pin_length = 0.016;
uniform float pin_from = 0.0075;
uniform float card_width = 0.0119;

// The colours: an arm, the bands across it (and across the comb of pinnules), the pinnules and their tips,
// the cup, the cirri, the stalk; how strongly it is banded, and how many bands along an arm.
uniform vec3 arm_colour : source_color = vec3(0.95, 0.75, 0.1);
uniform vec3 band_colour : source_color = vec3(0.7, 0.45, 0.05);
uniform vec3 pinnule : source_color = vec3(1.0, 0.85, 0.25);
uniform vec3 pinnule_tip : source_color = vec3(1.0, 0.95, 0.6);
uniform vec3 cup_colour : source_color = vec3(0.8, 0.6, 0.1);
uniform vec3 cirri_colour : source_color = vec3(0.75, 0.55, 0.15);
uniform vec3 stalk_colour : source_color = vec3(0.85, 0.7, 0.35);
uniform float bands = 0.3;
uniform float band_count = 9.0;

varying float part;

// One arc of a bend in a plane (as the sea stars'): `a` along, `b` out of the line it bends about; from
// `from` on, laid round a circle of curvature `k` (more than 0: towards +b). The normal turns with it.
void arc(inout float a, inout float b, inout float na, inout float nb, float from, float k) {
	if (a <= from || abs(k) < 0.001) {
		return;
	}
	float f = k * (a - from);
	float c = cos(f);
	float s = sin(f);
	float a2 = from + s / k - b * s;
	b = (1.0 - c) / k + b * c;
	a = a2;
	float n2 = na * c - nb * s;
	nb = na * s + nb * c;
	na = n2;
}

float pin_profile(float t) {
	return min(1.0, (t + 0.02) / 0.15) * (1.0 - 0.55 * t);
}

void vertex() {
	part = UV2.y;
	int p = int(part + 0.5);
	vec3 world = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float place = dot(world.xz, vec2(0.71, 0.53)) * 1.7;
	float clock = water_clock * 0.9 - place;
	if (p == 1 || p == 2 || p == 4 || p == 5) {
		float angle = TAU * UV2.x;
		vec3 out_way = vec3(sin(angle), 0.0, -cos(angle));
		vec3 f = out_way * cos(arm_rise) + vec3(0.0, sin(arm_rise), 0.0);
		vec3 n = -out_way * sin(arm_rise) + vec3(0.0, cos(arm_rise), 0.0);
		vec3 s = vec3(cos(angle), 0.0, sin(angle));
		vec3 root = out_way * root_radius + vec3(0.0, root_height, 0.0);
		vec3 rel = VERTEX - root;
		float a = dot(rel, f);
		float b = dot(rel, n);
		float c = dot(rel, s);
		float na = dot(NORMAL, f);
		float nb = dot(NORMAL, n);
		float nc = dot(NORMAL, s);
		float own = UV2.x * arms * 1.7;
		float t = clock + own;
		// swimming: half the arms half a stroke behind the others; a quick beat down with the arm
		// straight, then a slow recovery up with it curled
		int k = int(UV2.x * arms + 0.5);
		float u = fract(phase + 0.5 * float(k % 2) + 0.03 * float(k / 2));
		float beat_down = u < 0.35 ? smoothstep(0.0, 0.35, u) : 1.0 - smoothstep(0.35, 1.0, u);
		float stroke = mix(0.5, -0.95, beat_down) * swim;
		float recovering = u < 0.35 ? 0.0 : sin(PI * (u - 0.35) / 0.65);
		float rest = 1.0 - furl;
		float whole = rest_bend * rest + furl * 2.7 + sway * 0.28 * sin(t) + swim * 1.4 * recovering;
		float outer = tip_bend * rest + furl * 2.7 + sway * 0.3 * sin(t * 1.3 - 1.0) + swim * 0.9 * recovering;
		arc(a, b, na, nb, 0.5 * arm_length, outer / (0.5 * arm_length));
		arc(a, b, na, nb, 0.0, whole / arm_length);
		arc(a, c, na, nc, 0.0, sway * 0.16 * sin(t * 0.7 + 2.0) * rest / arm_length);
		// (the whole arm turned about its root by the stroke)
		float cs = cos(stroke);
		float sn = sin(stroke);
		float a2 = a * cs - b * sn;
		b = a * sn + b * cs;
		a = a2;
		float na2 = na * cs - nb * sn;
		nb = na * sn + nb * cs;
		na = na2;
		VERTEX = root + f * a + n * b + s * c;
		NORMAL = f * na + n * nb + s * nc;
	}
	if (stalk_height > 0.0) {
		// the stalk leans with the current and sways, carrying the crown
		vec2 way = normalize(vec2(1.0, 0.35));
		float y = VERTEX.y;
		float across = dot(VERTEX.xz, way);
		float ny = NORMAL.y;
		float nacross = dot(NORMAL.xz, way);
		float bend = sway * (0.32 + 0.14 * sin(clock * 0.7)) * (1.0 - 0.6 * furl);
		arc(y, across, ny, nacross, 0.0, bend / stalk_height);
		vec2 rest_xz = VERTEX.xz - way * dot(VERTEX.xz, way);
		VERTEX = vec3(rest_xz.x + way.x * across, y, rest_xz.y + way.y * across);
		vec2 nrest = NORMAL.xz - way * dot(NORMAL.xz, way);
		NORMAL = vec3(nrest.x + way.x * nacross, ny, nrest.y + way.y * nacross);
	}
}

float banded(float t) {
	return bands * smoothstep(0.25, 0.6, sin(t * band_count * TAU));
}

void fragment() {
	int p = int(part + 0.5);
	vec3 c = arm_colour;
	float alpha = 1.0;
	float rough = 0.6;
	if (p == 1) {
		// an arm: its joints fine dark lines, and its bands
		float joints = smoothstep(0.85, 1.0, abs(sin(UV.x * arm_length / 0.0016 * PI)));
		c = mix(arm_colour, band_colour, banded(UV.x));
		c *= 1.0 - 0.25 * joints;
	} else if (p == 2 || p == 4 || p == 5) {
		float along = UV.y;
		float at = UV.x;
		if (p != 2) {
			// a card: which pinnule (if any) this point of it is on
			float sinb = sin(pin_angle);
			float s = UV.x * arm_length;
			float q = UV.y * card_width;
			float off = p == 4 ? 0.0 : 0.5 * pin_gap;
			float u = s - q * cos(pin_angle) / sinb - pin_from - off;
			float j = floor(u / pin_gap + 0.5);
			float d = abs(u - j * pin_gap) * sinb;
			float sj = pin_from + off + j * pin_gap;
			float lp = pin_length * pin_profile(sj / arm_length);
			along = q / max(lp * sinb, 0.00001);
			at = sj / arm_length;
			float half_width = along < 0.5 ? mix(0.00034, 0.00026, along * 2.0) : mix(0.00026, 0.00008, along * 2.0 - 1.0);
			// (far off a pinnule is kept about a pixel wide, so that the comb fills in, not flickers)
			// (seen orthographically a pixel is the same size at any distance)
			float depth = PROJECTION_MATRIX[3][3] > 0.5 ? 1.0 : length(VERTEX);
			float pixel = depth * 2.0 / (abs(PROJECTION_MATRIX[1][1]) * VIEWPORT_SIZE.y);
			half_width = max(half_width, pixel * 0.55);
			bool on = j >= 0.0 && sj <= arm_length * 0.985 && along <= 1.0 && d <= half_width;
			alpha = on ? 1.0 : 0.0;
		}
		c = mix(pinnule, pinnule_tip, smoothstep(0.45, 1.0, along));
		c = mix(c, band_colour, banded(at) * (1.0 - 0.5 * smoothstep(0.6, 1.0, along)));
		rough = 0.5;
	} else if (p == 0) {
		c = cup_colour;
	} else if (p == 3 || p == 7) {
		// a cirrus: jointed
		float joints = smoothstep(0.8, 1.0, abs(sin(UV.y * 14.0 * PI)));
		c = cirri_colour * (1.0 - 0.3 * joints);
	} else {
		// the stalk: columnals, with a darker node every whorl
		float h = UV.y * stalk_height;
		float joints = smoothstep(0.85, 1.0, abs(sin(h / 0.004 * PI)));
		c = stalk_colour * (1.0 - 0.25 * joints);
		rough = 0.7;
	}
	ALBEDO = c;
	ALPHA = alpha;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ROUGHNESS = rough;
	SPECULAR = 0.4;
}
