extends Node3D
## A cloud of plankton in blue water, and a mouth (a small dark ball) that swims through it in a
## circle, eating as it goes: the specks it takes vanish and later drift back in. The number in
## the corner is how much of the cloud is left. Give this to a Node3D at the root of an empty
## scene and play that scene. (If the project declares no `water_clock` shader global, the cloud
## adds one and runs it.)

var cloud: PlanktonCloud
var mouth: MeshInstance3D
var label: Label
var time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.02, 0.12, 0.26)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.9)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	cloud = PlanktonCloud.new()
	add_child(cloud)
	cloud.speck_size = 3.0
	cloud.drift = 0.08
	cloud.fill(Vector3.ZERO, 0.8, 1500)
	mouth = MeshInstance3D.new()
	var ball := SphereMesh.new()
	ball.radius = 0.06
	ball.height = 0.12
	mouth.mesh = ball
	add_child(mouth)
	var camera := Camera3D.new()
	camera.fov = 50.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.4, 2.4), Vector3.ZERO)
	label = Label.new()
	label.position = Vector2(16, 16)
	add_child(label)


func _process(delta: float) -> void:
	time += delta
	mouth.position = Vector3(cos(time * 0.6) * 0.55, sin(time * 0.9) * 0.2, sin(time * 0.6) * 0.55)
	cloud.bite(mouth.global_position, 0.12)
	label.text = "%d%%" % roundi(cloud.amount * 100.0)
