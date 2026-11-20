// The family shaders' fragment (GameCommon `godot/motion-families`): the animal's baked paint
// (GameCommon `godot/baked-look`), its glow where it has one; where the bake cut the back of the mouth
// away (alpha under a half) the point is dropped while the mouth is open (or always, for `cut_always`:
// the see-through gaps of a two-sided sheet).

uniform bool cut_always = false;
// A thin light round the animal's outline (a game's own mark: Gulp's FoodMarks lights what the player
// can eat gold and what can eat it red): rgb its colour, a how strong (0, none, as built).
uniform vec4 mark_rim = vec4(0.0);

void fragment() {
	// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)
	vec4 paint = texture(baked_paint, bake_uv, -1.0);
#ifdef MOTION_SHEER
	ALPHA = paint.a;
#else
	if (paint.a < 0.5 && (gape > 0.0 || cut_always)) {
		discard;
	}
#endif
	ALBEDO = paint.rgb;
	EMISSION = texture(baked_glow, bake_uv).rgb * baked_glow_scale;
	// (the mark: brightest where the surface turns away from the eye, nothing face on)
	float edge = 1.0 - abs(dot(normalize(NORMAL), normalize(VIEW)));
	EMISSION += mark_rim.rgb * (mark_rim.a * smoothstep(0.25, 0.85, edge));
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}
