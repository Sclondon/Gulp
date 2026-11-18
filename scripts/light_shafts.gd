class_name LightShafts
extends MultiMeshInstance3D
## Shafts of light from the surface that stand in the sea (tools/WATER_FX.md): the user
## (2026-11-18), "the god rays need to be in 3d space on just on the screen overlay".
##
## A few dozen long soft strips (shaders/light_shaft.gdshader), one MultiMesh, one draw. They hang
## from the surface round the eye on a grid of `CELL`-metre squares of the world: each square
## has its own shaft (or none), always in the same place, so as the eye swims among them they
## stay where they are and the near ones pass the far ones. When the eye has crossed into
## another square they are laid out again round it (a few dozen sums, a few times a second at
## most). They slant the way the light comes down through the water, from the sun or the moon
## (Day), and reach down to the floor.

const CELL := 5.0
## Squares each way from the eye's (7 by 7 of them).
const REACH := 3
const LONGEST := 40.0

## What they hang round (the camera).
var eye: Node3D
## How bright they are (Sea sets it from the time of day and how deep the eye is).
var strength := 0.0: set = _set_strength
var colour := Color(0.6, 0.85, 1.0): set = _set_colour
## The way the light runs down through the water.
var slant := Vector3(0.0, -1.0, 0.0)

var _material: ShaderMaterial
var _laid := Vector2i(1 << 20, 0)
var _laid_slant := Vector3.ZERO


func _init() -> void:
	name = "LightShafts"
	_material = ShaderMaterial.new()
	_material.shader = preload("res://shaders/light_shaft.gdshader")
	_material.set_shader_parameter(&"surface", Sea.SURFACE)
	var quad := QuadMesh.new()
	quad.size = Vector2(1.0, 1.0)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = quad
	mm.instance_count = (REACH * 2 + 1) * (REACH * 2 + 1)
	multimesh = mm
	material_override = _material
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# (the shader puts each strip where it is: the box it might be in, round this node)
	custom_aabb = AABB(Vector3(-CELL * (REACH + 1) - LONGEST, -LONGEST - 2.0, -CELL * (REACH + 1) - LONGEST), Vector3((CELL * (REACH + 1) + LONGEST) * 2.0, LONGEST + 4.0, (CELL * (REACH + 1) + LONGEST) * 2.0))
	top_level = true


func _process(_delta: float) -> void:
	if eye == null:
		return
	var at := eye.global_position
	# (laid round where the shafts through the eye's depth leave the surface, so that the ones
	# round the eye are the ones it is among)
	var down := maxf(Sea.SURFACE - at.y, 0.0)
	var up := Vector2(slant.x, slant.z) * (down / maxf(-slant.y, 0.2))
	var middle := Vector2(at.x, at.z) - up
	var square := Vector2i(floori(middle.x / CELL), floori(middle.y / CELL))
	if square != _laid or slant.distance_to(_laid_slant) > 0.02:
		_lay(square)


## Lays a shaft in each square round one (or none, by its own chance).
func _lay(square: Vector2i) -> void:
	_laid = square
	_laid_slant = slant
	_material.set_shader_parameter(&"slant", slant)
	global_transform = Transform3D(Basis.IDENTITY, Vector3((square.x + 0.5) * CELL, Sea.SURFACE, (square.y + 0.5) * CELL))
	var mm := multimesh
	var i := 0
	for dz in range(-REACH, REACH + 1):
		for dx in range(-REACH, REACH + 1):
			var cx := square.x + dx
			var cz := square.y + dz
			var rng := RandomNumberGenerator.new()
			rng.seed = hash(Vector2i(cx, cz))
			var top := Vector3((cx + rng.randf_range(0.1, 0.9)) * CELL, Sea.SURFACE, (cz + rng.randf_range(0.1, 0.9)) * CELL)
			var wide := rng.randf_range(0.5, 2.3)
			var long := 0.0
			if rng.randf() < 0.75:
				# (down to the floor: where along the slant it meets it, near enough)
				long = LONGEST
				for attempt in 2:
					var foot := top + slant * long
					long = clampf((Sea.SURFACE - Sea.ground(foot.x, foot.z)) / maxf(-slant.y, 0.2), 0.0, LONGEST)
			mm.set_instance_transform(i, Transform3D(Basis.IDENTITY, top - global_position))
			mm.set_instance_custom_data(i, Color(long, wide if long > 0.0 else 0.0, rng.randf(), 0.0))
			i += 1


func _set_strength(to: float) -> void:
	strength = to
	if _material:
		_material.set_shader_parameter(&"strength", to)


func _set_colour(to: Color) -> void:
	colour = to
	if _material:
		_material.set_shader_parameter(&"colour", to)
