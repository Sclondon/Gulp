// What every ink figure shader shares (see scripts/ink_figure.gd): the cut
// between light and shadow, lines that stay one pixel soft at any distance,
// engraver's hatching, stipple, print grain, and the noise they are made from.
// Nothing reads a texture or the screen, so it costs the same on a phone.

// (no sines in the hashes: they come out differently on phone and web GPUs)
float ink_hash(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float ink_hash3(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

vec2 ink_hash22(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

float ink_noise(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(ink_hash(cell), ink_hash(cell + vec2(1.0, 0.0)), f.x),
			mix(ink_hash(cell + vec2(0.0, 1.0)), ink_hash(cell + vec2(1.0, 1.0)), f.x), f.y);
}

float ink_noise3(vec3 p) {
	vec3 cell = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(ink_hash3(cell), ink_hash3(cell + vec3(1, 0, 0)), f.x),
			mix(ink_hash3(cell + vec3(0, 1, 0)), ink_hash3(cell + vec3(1, 1, 0)), f.x), f.y);
	float b = mix(mix(ink_hash3(cell + vec3(0, 0, 1)), ink_hash3(cell + vec3(1, 0, 1)), f.x),
			mix(ink_hash3(cell + vec3(0, 1, 1)), ink_hash3(cell + vec3(1, 1, 1)), f.x), f.y);
	return mix(a, b, f.z);
}

// A hard step at `edge`, softened by exactly one pixel.
float cut(float value, float edge) {
	float pixel = max(fwidth(value), 0.0005);
	return smoothstep(edge - pixel, edge + pixel, value);
}

// Engraver's lines across `phase` (one line to each whole number), each
// covering `cover` (0..1) of the gap: 1 between the lines, 0 on them. Where the
// lines would come closer than a few pixels they give the tone they would make
// instead, so they never shimmer.
float hatch(float phase, float cover) {
	float across = abs(fract(phase) - 0.5) * 2.0;
	float pixel = max(fwidth(phase) * 2.0, 0.0001);
	float lines = smoothstep(cover - pixel, cover + pixel, across);
	return mix(1.0 - cover, lines, clamp(0.45 / pixel - 0.6, 0.0, 1.0));
}

// Stipple: a dot in each cell of a jittered grid (`at` in cells), each dot
// `cover` of its cell, the darker the larger. 1 on paper, 0 on a dot.
float stipple(vec2 at, float cover, float seed) {
	vec2 cell = floor(at);
	float paper = 1.0;
	float pixel = max(fwidth(at.x), 0.0001);
	for (int i = 0; i < 4; i++) {
		vec2 near = cell + vec2(float(i % 2), float(i / 2)) - 0.5 + step(0.5, fract(at)) - 0.5;
		vec2 dot_at = near + ink_hash22(near + seed);
		float size = sqrt(cover) * 0.62 * (0.75 + 0.5 * ink_hash(near + seed + 7.0));
		float gap = distance(at, dot_at);
		paper = min(paper, smoothstep(size - pixel, size + pixel, gap));
	}
	return mix(1.0 - cover, paper, clamp(0.3 / pixel - 0.5, 0.0, 1.0));
}

// Short strokes laid along `along` (a unit 2D direction in the same space as
// `at`): each cell of a jittered grid has one dash, `cover` decides how many of
// them are drawn and how thick. 1 on paper, 0 on a stroke.
float strokes(vec2 at, vec2 along, float cover, float dash, float seed) {
	vec2 across = vec2(-along.y, along.x);
	vec2 cell = floor(at);
	float paper = 1.0;
	float pixel = max(fwidth(at.x), 0.0001);
	for (int i = 0; i < 4; i++) {
		vec2 near = cell + vec2(float(i % 2), float(i / 2)) - 0.5 + step(0.5, fract(at)) - 0.5;
		float pick = ink_hash(near + seed);
		if (pick > cover * 1.3) {
			continue;
		}
		vec2 mid = near + ink_hash22(near + seed);
		vec2 d = at - mid;
		// (each tilted a little its own way)
		float tilt = (ink_hash(near + seed + 3.0) - 0.5) * 0.6;
		vec2 a2 = normalize(along + across * tilt);
		vec2 c2 = vec2(-a2.y, a2.x);
		float t = clamp(dot(d, a2) / dash, -1.0, 1.0);
		// (a stroke tapers to points at both ends)
		float width = (0.05 + 0.12 * cover) * (1.0 - t * t);
		float off = abs(dot(d, c2));
		float ends = abs(dot(d, a2)) - dash;
		paper = min(paper, max(smoothstep(width - pixel, width + pixel, off), step(0.0, ends)));
	}
	return mix(1.0 - cover * 0.6, paper, clamp(0.3 / pixel - 0.5, 0.0, 1.0));
}

// The speckle of a print, fixed to the figure (`at` in metres), never to the
// screen: a little lighter and darker, and the odd dark fleck.
float grain(vec3 at, float amount) {
	float fine = ink_noise3(at * 900.0) - 0.5;
	float fleck = step(0.985, ink_hash3(floor(at * 420.0)));
	return 1.0 + fine * amount - fleck * amount * 1.5;
}

// Ink where a surface turns away from the eye: 1 inside, 0 at the edge.
float ink_edge(vec3 normal, vec3 view, float width) {
	return cut(clamp(dot(normal, view), 0.0, 1.0), width);
}
