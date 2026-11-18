shader_type spatial;
render_mode cull_disabled, specular_disabled, blend_mix;
// A fishing net: diamonds of thin strands, see-through between them (scripts/fishers.gd). Where each
// point is on the net, in metres, makes the pattern: for a curtain (NetPanel, `panel` on) from its
// local place scaled by its node (x along it from its left end, y down from its top); for the trawl
// from its UVs (in metres round and along). Close up the strands are sharp; far off, where they would
// shimmer, the net fades to a faint sheet (`far_alpha`), so that it can still be seen in time.
// `holes` are torn places (along, down, radius; a radius of 0 is none), only on a curtain.

uniform vec4 colour : source_color = vec4(0.72, 0.8, 0.72, 1.0);
// Across one diamond, and a strand's width (m).
uniform float mesh = 0.16;
uniform float strand = 0.012;
uniform bool panel = true;
uniform float fade_near = 6.0;
uniform float fade_far = 26.0;
uniform float far_alpha = 0.2;
// How far a curtain billows at its foot (m).
uniform float sway = 0.0;
uniform vec4 holes[6];

varying vec2 at;

void vertex() {
	if (panel) {
		vec2 size = vec2(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz));
		at = vec2((VERTEX.x + 0.5) * size.x, -VERTEX.y * size.y);
		// (pinned along its top, swaying more towards its foot)
		VERTEX.z += sway * -VERTEX.y * sin(at.x * 0.3 + TIME * 0.5) / max(length(MODEL_MATRIX[2].xyz), 0.0001);
	} else {
		at = UV;
	}
}

void fragment() {
	vec2 d = vec2(at.x + at.y, at.x - at.y) / (mesh * 1.41421);
	vec2 f = abs(fract(d) - 0.5) * 2.0;
	// (0 on a strand's middle line, rising across the diamond)
	float e = min(1.0 - f.x, 1.0 - f.y);
	float w = strand / mesh * 2.0;
	float aa = max(fwidth(e), 0.0001);
	float line = 1.0 - smoothstep(w - aa, w + aa, e);
	// Far off (or where a strand is thinner than a pixel), the net becomes a faint even sheet.
	float far = smoothstep(fade_near, fade_far, length(VERTEX));
	float thin = smoothstep(w * 0.8, w * 2.5, aa);
	float alpha = mix(line, far_alpha, max(far, thin));
	if (panel) {
		for (int i = 0; i < 6; i++) {
			vec4 hole = holes[i];
			if (hole.z > 0.0) {
				vec2 off = at - hole.xy;
				// (ragged round its edge)
				float r = hole.z * (0.85 + 0.15 * sin(atan(off.y, off.x) * 7.0 + hole.x * 3.0));
				if (length(off) < r) {
					alpha = 0.0;
				}
			}
		}
	}
	if (alpha < 0.03) {
		discard;
	}
	ALBEDO = colour.rgb;
	ALPHA = alpha * colour.a;
	ROUGHNESS = 0.9;
}
