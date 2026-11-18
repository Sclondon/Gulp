extends Node3D
## A cloud of sea sparkle in the dark, and a small dark ball that swims round through it: the specks it passes flash
## blue and fade behind it, a trail of light. Give this to a Node3D at the root of an empty scene and play that scene.

var sparkle: SeaSparkle
var swimmer: MeshInstance3D
var time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.0, 0.004, 0.015)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.5, 0.7)
	env.environment.ambient_light_energy = 0.15
	add_child(env)
	sparkle = SeaSparkle.new()
	add_child(sparkle)
	sparkle.speck_size = 3.0
	sparkle.drift = 0.04
	sparkle.fill(Vector3.ZERO, 0.8, 3000)
	swimmer = MeshInstance3D.new()
	var ball := SphereMesh.new()
	ball.radius = 0.04
	ball.height = 0.08
	swimmer.mesh = ball
	add_child(swimmer)
	var camera := Camera3D.new()
	camera.fov = 50.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.5, 2.2), Vector3.ZERO)


func _process(delta: float) -> void:
	time += delta
	swimmer.position = Vector3(cos(time * 0.7) * 0.55, sin(time * 1.1) * 0.25, sin(time * 0.7) * 0.55)
	sparkle.stir(swimmer.global_position, 0.12)
