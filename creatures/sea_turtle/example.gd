extends Node3D
## A green sea turtle flying on the spot in blue water, seen from its side and a little above, with the cartoon eye:
## it opens its beak now and then, blinks, banks into a slow turn and out again. Give this to a Node3D at the root of
## an empty scene and play that scene. (Set `type` to see the others.)

@export var type := SeaTurtle.Type.GREEN

var turtle: SeaTurtle
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.16, 0.34)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.9)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	turtle = SeaTurtle.new()
	turtle.type = type
	turtle.cartoon_eyes = 1.0
	add_child(turtle)
	# (its beak is at -Z: turned a quarter, it faces the left of the picture)
	turtle.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	var size := SeaTurtle.LENGTHS[type] as float
	camera.look_at_from_position(Vector3(0.3, 1.2, 3.2) * size, Vector3.ZERO)


func _process(delta: float) -> void:
	_clock += delta
	turtle.step(Vector3.ZERO, delta)
	# (it opens its beak for a moment every few seconds, and blinks)
	turtle.gape = clampf(sin(_clock * 1.1) * 4.0 - 3.0, 0.0, 1.0)
	turtle.blink = clampf(sin(_clock * 2.3) * 12.0 - 11.0, 0.0, 1.0)
	# (a slow turn one way and the other)
	turtle.curl = 0.5 * sin(_clock * 0.4)
