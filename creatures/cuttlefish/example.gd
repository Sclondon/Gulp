extends Node3D
## A cuttlefish hovering over sand, arms first, its fin rippling; every few seconds it changes its
## skin (camouflage, passing clouds, the zebra bands, blanched), turns its mantle, spreads its arms
## and strikes with its tentacles, and flashes. Play creatures/cuttlefish/example.tscn.

var cuttle: Cuttlefish
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.2, 0.3)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.65, 0.7)
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1, 6, 2), Vector3.ZERO)
	cuttle = Cuttlefish.new()
	add_child(cuttle)
	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0.55, 0.35, 0.45), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	var act := int(_clock / 4.0) % 5
	var into := fposmod(_clock, 4.0)
	cuttle.cloud = move_toward(cuttle.cloud, 1.0 if act == 1 else 0.0, delta)
	cuttle.zebra = move_toward(cuttle.zebra, 1.0 if act == 2 else 0.0, delta)
	cuttle.blanch = move_toward(cuttle.blanch, 1.0 if act == 3 else 0.0, delta)
	cuttle.curl = 0.5 * sin(_clock * 0.7)
	# hunting: arms open, then the strike
	cuttle.spread = move_toward(cuttle.spread, 0.6 if act == 4 and into < 2.0 else 0.0, delta * 2.0)
	cuttle.strike = clampf(1.0 - absf(into - 2.3) * 6.0, 0.0, 1.0) if act == 4 else 0.0
	if act == 0 and absf(into - 3.0) < delta:
		cuttle.flash()
	cuttle.position = Vector3(0.0, 0.01 * sin(_clock), 0.0)
	cuttle.step(Vector3.ZERO, delta)
