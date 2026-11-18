extends Node3D
## A sea nettle drifting through the air over a grey floor, slowly round in a
## circle, beside a post as tall as a person. Its strands swing back as it
## goes; it says when anything touches the post. Give it to a Node3D at the
## root of an empty scene and play that scene.

var jelly: SeaNettle
var post: MeshInstance3D
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.55, 0.6, 0.62)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.5, 0.52, 0.55)
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.shadow_enabled = true
	add_child(sun)
	sun.look_at_from_position(Vector3(2, 10, 4), Vector3.ZERO)
	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(40, 40)
	floor.mesh = plane
	add_child(floor)
	post = MeshInstance3D.new()
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.22
	capsule.height = 1.7
	post.mesh = capsule
	post.position = Vector3(3.0, 0.85, 0.0)
	add_child(post)
	jelly = SeaNettle.new()
	add_child(jelly)
	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 4, 14), Vector3(0, 3.5, 0))


func _process(delta: float) -> void:
	_clock += delta
	var was := jelly.global_position
	jelly.global_position = Vector3(cos(_clock * 0.12) * 3.0, 5.8 + 0.4 * sin(_clock * 0.5), sin(_clock * 0.12) * 3.0)
	jelly.step((jelly.global_position - was) / delta, delta)
	if jelly.touches(post.global_position - Vector3.UP * 0.85, post.global_position + Vector3.UP * 0.85, 0.22):
		jelly.sting(post.global_position)
