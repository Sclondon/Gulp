extends Node3D
## A humpback anglerfish hanging in the dark of the deep, seen from its side: its lure glows, its rod sways and
## flicks now and then, and every few seconds it snaps its mouth open. Give this to a Node3D at the root of an
## empty scene and play that scene.

var fish: DeepAnglerfish
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.0, 0.004, 0.012)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.5, 0.7)
	env.environment.ambient_light_energy = 0.15
	add_child(env)
	fish = DeepAnglerfish.new()
	add_child(fish)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	fish.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	# a real light at the lure, so that what is near it shows (the bulb itself glows without it)
	var lamp := OmniLight3D.new()
	lamp.light_color = Color(0.55, 0.82, 1.0)
	lamp.omni_range = 0.5
	lamp.light_energy = 1.2
	lamp.position = DeepAnglerfish.LURE_AT
	fish.add_child(lamp)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.05, 0.04, 0.62), Vector3(0.0, 0.03, 0.0))


func _process(delta: float) -> void:
	_time += delta
	fish.step(Vector3.ZERO, delta)
	# a flick of the rod every other few seconds, and a snap of the jaws now and then
	fish.flick = 1.0 if fmod(_time, 6.0) < 1.6 else 0.0
	var snap := fmod(_time, 5.0)
	fish.gape = clampf(1.0 - absf(snap - 0.3) / 0.3, 0.0, 1.0) if snap < 0.9 else 0.0
