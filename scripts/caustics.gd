class_name Caustics
extends MeshInstance3D
## Caustics on everything under the water: the floor, rocks, kit, plants, wrecks, the docks' piles,
## the animals and the player's fish (the user, 2026-11-18: "The caustics need to appear on fish and
## props etc"). One full-screen quad drawn with shaders/caustics.gdshader, first among the
## see-through things, reading the depth buffer: one program for every surface, nothing added to
## the 150-odd materials. CLAUDE.md, "Decision: caustics as one pass over the picture".
## Sea makes it and sets its strength and the water's fog from `_look`.

var look: ShaderMaterial


func _init() -> void:
	name = "Caustics"
	var quad := QuadMesh.new()
	quad.size = Vector2(2.0, 2.0)
	mesh = quad
	look = ShaderMaterial.new()
	look.shader = preload("res://shaders/caustics.gdshader")
	# (first among the see-through things: after the solid ones, before the water's surface, the
	# jellies, the bubbles and the shafts, which it would otherwise paint over)
	look.render_priority = Material.RENDER_PRIORITY_MIN
	look.set_shader_parameter(&"caustic_tex", Sea.caustic_texture())
	look.set_shader_parameter(&"caustic_surface", Sea.SURFACE)
	material_override = look
	# (never culled: the vertex shader puts it over the whole view)
	custom_aabb = AABB(Vector3(-1e5, -1e5, -1e5), Vector3(2e5, 2e5, 2e5))
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# (`-- --no-caustics`: without it, to compare pictures and costs)
	visible = not OS.get_cmdline_user_args().has("--no-caustics")


## The strength by the hour (0 is none: then it draws nothing but the quad), and the water's fog.
func set_light(strength: float, fog: Color, density: float) -> void:
	look.set_shader_parameter(&"caustics", strength)
	look.set_shader_parameter(&"fog_colour", fog)
	look.set_shader_parameter(&"fog_density", density)
