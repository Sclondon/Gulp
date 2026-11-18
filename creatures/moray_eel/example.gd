extends Node3D
## A moray eel swimming slowly round in a circle over a grey floor, its body
## trailing after its head and settling behind it. Give it to a Node3D at the
## root of an empty scene and play that scene.

var eel: MorayEel
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.12, 0.3, 0.42)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.5, 0.6, 0.65)
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.shadow_enabled = true
	add_child(sun)
	sun.look_at_from_position(Vector3(2, 10, 4), Vector3.ZERO)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(20, 20)
	ground.mesh = plane
	add_child(ground)
	eel = MorayEel.new()
	add_child(eel)
	_place()
	eel.lay_ropes()
	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 2.6, 3.6), Vector3(0, 0.5, 0))


## Round a circle 1.2 m out, its snout the way it goes, rising and sinking a little.
func _place() -> void:
	var angle := _clock * 0.5
	var at := Vector3(cos(angle) * 1.2, 0.6 + 0.1 * sin(_clock * 0.7), sin(angle) * 1.2)
	var ahead := Vector3(-sin(angle), 0.07 * cos(_clock * 0.7), cos(angle))
	eel.look_at_from_position(at, at + ahead)


func _process(delta: float) -> void:
	_clock += delta
	var was := eel.global_position
	_place()
	eel.step((eel.global_position - was) / delta, delta)
