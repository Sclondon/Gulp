extends Node3D
## A silver arowana cruising just under a calm surface, seen from its side, leaping now and then
## (an arc out of the water, its body arching, its mouth snapping open at the top). Give this to
## a Node3D at the root of an empty scene and play that scene.

var arowana: Arowana
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.1, 0.18, 0.16)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.7, 0.78, 0.75)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	# the surface: a thin pale sheet
	var surface := MeshInstance3D.new()
	var sheet := PlaneMesh.new()
	sheet.size = Vector2(8.0, 3.0)
	surface.mesh = sheet
	surface.position.y = 0.12
	var water := StandardMaterial3D.new()
	water.albedo_color = Color(0.5, 0.65, 0.6, 0.25)
	water.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	water.cull_mode = BaseMaterial3D.CULL_DISABLED
	surface.material_override = water
	add_child(surface)
	arowana = Arowana.new()
	add_child(arowana)
	var camera := Camera3D.new()
	camera.fov = 45.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.25, 2.6), Vector3(0.0, 0.2, 0.0))


func _process(delta: float) -> void:
	_time += delta
	# six seconds cruising, then a leap of one second
	var t := fmod(_time, 7.0)
	var leap := clampf(t - 6.0, 0.0, 1.0)
	var rise := sin(leap * PI)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture; pitched along the arc)
	var pitch := cos(leap * PI) * 0.7 if leap > 0.0 else 0.0
	arowana.rotation = Vector3(0.0, PI * 0.5, 0.0)
	arowana.rotate_object_local(Vector3.RIGHT, pitch)
	arowana.position = Vector3(0.6 - leap * 1.2, rise * 0.55, 0.0)
	arowana.arch = lerpf(-0.5, 0.6, leap) * rise
	arowana.gape = clampf(1.0 - absf(leap - 0.5) / 0.2, 0.0, 1.0)
	arowana.sway = 0.4 if leap > 0.0 else 1.0
	arowana.step(Vector3.ZERO, delta)
