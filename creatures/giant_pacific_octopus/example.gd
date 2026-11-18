extends Node3D
## A giant Pacific octopus jetting round in a ring, mantle first, its arms trailing in a bundle;
## then it settles on the sand, mantle up, its arms spread and curled round it, blushes dark and
## flashes pale; then it swims off again. Play creatures/giant_pacific_octopus/example.tscn.

const GROUND := -1.2

var octopus: GiantPacificOctopus
var _clock := 0.0
var _turn := 0.0
var _settle := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.12, 0.22)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.5, 0.6, 0.7)
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(2, 10, 4), Vector3.ZERO)
	var sand := MeshInstance3D.new()
	sand.mesh = PlaneMesh.new()
	(sand.mesh as PlaneMesh).size = Vector2(12, 12)
	var sand_look := StandardMaterial3D.new()
	sand_look.albedo_color = Color(0.55, 0.5, 0.4)
	sand.material_override = sand_look
	sand.position.y = GROUND
	add_child(sand)
	octopus = GiantPacificOctopus.new()
	add_child(octopus)
	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 1.8, 6.5), Vector3(0, -0.5, 0))


func _process(delta: float) -> void:
	_clock += delta
	# 10 s swimming, 8 s settled, round again
	var settled := fposmod(_clock, 18.0) > 10.0
	_settle = move_toward(_settle, 1.0 if settled else 0.0, delta * 0.5)
	octopus.sit = smoothstep(0.0, 1.0, _settle)
	octopus.blush = clampf(sin(fposmod(_clock, 18.0) - 12.0), 0.0, 1.0) if settled else 0.0
	if settled and absf(fposmod(_clock, 18.0) - 16.0) < delta:
		octopus.flash()
	if not settled:
		# (it goes fastest as it squeezes: a jet)
		_turn += delta * (0.12 + 0.35 * octopus.thrust)
	var swim_at := Vector3(cos(_turn) * 2.0, 0.0, sin(_turn) * 2.0)
	var ahead := Vector3(-sin(_turn), 0.0, cos(_turn))
	# swimming: its mantle leads (its own -Z the way it goes); settled: its mantle up and leaning
	# back, its arms' crown on the sand
	var swim := Basis.looking_at(ahead, Vector3.UP)
	var sit := Basis.looking_at(Vector3(0.0, 1.0, 0.0) - ahead * 0.35, -ahead)
	var basis := swim.slerp(sit, octopus.sit)
	var sit_at := Vector3(swim_at.x, GROUND + 0.22, swim_at.z)
	octopus.global_transform = Transform3D(basis, swim_at.lerp(sit_at, octopus.sit))
	octopus.beat = 2.4 if not settled else 4.0
	octopus.step(Vector3.ZERO, delta)
