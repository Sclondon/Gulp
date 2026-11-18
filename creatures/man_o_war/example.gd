extends Node3D
## A Portuguese man o' war blown slowly round in a circle on the surface of dark blue water, beside a post as
## long as a big fish just under the surface. Its tentacles trail back as it goes; it says when they touch the
## post. Give it to a Node3D at the root of an empty scene and play that scene. `-- --game` shows the game
## model, `-- --low` the low.

const SURFACE := 4.0

var jelly: ManOWar
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
	# the water's surface, seen through
	var water := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(30, 30)
	water.mesh = plane
	var clear := StandardMaterial3D.new()
	clear.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	clear.albedo_color = Color(0.3, 0.55, 0.8, 0.25)
	clear.cull_mode = BaseMaterial3D.CULL_DISABLED
	water.material_override = clear
	water.position.y = SURFACE
	add_child(water)
	post = MeshInstance3D.new()
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.15
	capsule.height = 1.5
	post.mesh = capsule
	post.rotation.z = PI * 0.5
	post.position = Vector3(2.0, SURFACE - 1.5, 0.0)
	add_child(post)
	jelly = ManOWar.new()
	jelly.game = "--game" in OS.get_cmdline_user_args()
	jelly.low = "--low" in OS.get_cmdline_user_args()
	add_child(jelly)
	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0, SURFACE + 1.0, 8), Vector3(0, SURFACE - 1.5, 0))


func _process(delta: float) -> void:
	_clock += delta
	var was := jelly.global_position
	# (its origin on the water's surface; turned to face the way it is blown)
	jelly.global_position = Vector3(cos(_clock * 0.15) * 2.0, SURFACE, sin(_clock * 0.15) * 2.0)
	var going := (jelly.global_position - was) / maxf(delta, 0.0001)
	if going.length() > 0.01:
		jelly.look_at(jelly.global_position + going, Vector3.UP)
	jelly.step(going, delta)
	if jelly.touches(post.global_position - Vector3.RIGHT * 0.75, post.global_position + Vector3.RIGHT * 0.75, 0.15):
		jelly.sting(post.global_position)
		_stung += 1
	if Engine.get_process_frames() % 120 == 0:
		print("MAN O WAR at %s, tentacles down %.2f m, stung %d frames" % [jelly.global_position, jelly.lowest(), _stung])
