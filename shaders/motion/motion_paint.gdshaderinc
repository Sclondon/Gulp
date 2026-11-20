// The family shaders' fragment (GameCommon `godot/motion-families`): the animal's baked paint
// (GameCommon `godot/baked-look`), its glow where it has one; where the bake cut the back of the mouth
// away (alpha under a half) the point is dropped while the mouth is open (or always, for `cut_always`:
// the see-through gaps of a two-sided sheet).

uniform bool cut_always = false;

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
	ROUGHNESS = baked_roughness;
	SPECULAR = baked_specular;
}
