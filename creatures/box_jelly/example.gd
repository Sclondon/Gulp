extends Node3D
## A box jelly swimming steadily round in a circle in dark blue water, beside a post as long as a
## big fish. Its tentacles trail back as it goes; it says when its strands touch the post. Give it to a Node3D
## at the root of an empty scene and play that scene. `-- --game` shows the game model, `-- --low` the low.

var jelly: BoxJelly
var post: MeshInstance3D
var _clock := 0.0
var _stung := 0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.02, 0.1, 0.24)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.45, 0.6, 0.85)
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(2, 10, 4), Vector3.ZERO)
	post = MeshInstance3D.new()
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.1
	capsule.height = 0.8
	post.mesh = capsule
	post.rotation.z = PI * 0.5
	post.position = Vector3(1.5, 1.2, 0.0)
	add_child(post)
	jelly = BoxJelly.new()
	jelly.game = "--game" in OS.get_cmdline_user_args()
	jelly.low = "--low" in OS.get_cmdline_user_args()
	add_child(jelly)
	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 2, 5), Vector3(0, 1.4, 0))


func _process(delta: float) -> void:
	_clock += delta
	var was := jelly.global_position
	jelly.global_position = Vector3(cos(_clock * 0.5) * 1.5, 2.2 + 0.1 * sin(_clock * 0.9), sin(_clock * 0.5) * 1.5)
	jelly.step((jelly.global_position - was) / maxf(delta, 0.0001), delta)
	if jelly.touches(post.global_position - Vector3.RIGHT * 0.4, post.global_position + Vector3.RIGHT * 0.4, 0.2):
		jelly.sting(post.global_position)
		_stung += 1
	if Engine.get_process_frames() % 120 == 0:
		print("BOX JELLY at %s, strands down %.2f m, stung %d frames" % [jelly.global_position, jelly.lowest(), _stung])
