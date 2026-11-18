class_name PanelModel
extends SubViewport
## The control panel as a 3D model (the user, 2026-11-18: "lets recreate the ui as a 3d model to
## interact with"): models/control_panel.glb (built by tools/build_panel.py, which says what is in
## it) in a little world of its own, drawn clear-backed over the game by TouchPad, which also
## takes the touches. This places the three housings along the bottom of the screen and moves
## their parts: the stick leans, the plunger sinks and glows, the lever swings round the plunger
## in its slot, the needles turn.
##
## Decision (Claude's pick, 2026-11-18): a SubViewport with its own World3D and a clear background,
## shown as a texture by a Control. It is the usual way in Godot to put 3D things in a 2D
## interface (the alternatives: a second camera on its own render layer, which the game's
## half-size dithered picture would also shrink and dither; or parenting the model to the game's
## camera, which the water's fog and light would tint). The model is painted by an unshaded shader
## (shaders/panel.gdshader), so the little world needs no lights.
##
## The camera looks straight at the housings' faces from far off with a narrow lens: the faces sit
## where a flat panel would, to the pixel, and only what stands out of them (the stick, the lever,
## the posts) leans with the view. `to_screen` is that camera's sum, so touches can be matched to
## parts without asking the engine.

const MODEL := "res://models/control_panel.glb"
## These are tools/build_panel.py's numbers (its PANEL line): change both.
const SIDE_WIDE := 2.2
const SIDE_TALL := 3.5
const WELL_Z := 1.05
const SLOT_FROM := 162.0
const SLOT_TO := 74.0
const GAUGE_WIDE := 3.3
const GAUGE_TALL := 3.0
const SWING := 2.2
## Metres of the model to one of TouchPad's layout units.
const METRE := 100.0
## The camera's lens (degrees, up and down).
const LENS := 24.0
## How far the stick leans, pushed right over (radians), and how far the plunger sinks (m).
const STICK_LEAN := 0.55
const PLUNGER_SINK := 0.12
## How much of the instrument housing's foot (its switches) is under the screen's edge on a wide
## screen, where it would otherwise stand over the fish (m).
const GAUGE_SUNK := 1.08
## How much smaller the side housings are on an upright phone, so the instruments fit between.
const SIDE_UPRIGHT := 0.8

const PAINTS := {
	"iron": {"base": Color(0.5, 0.25, 0.1), "patch_a": Color(0.3, 0.14, 0.07), "patch_b": Color(0.33, 0.42, 0.3), "patches": 0.9, "patch_size": 1.3, "dents": 1.0},
	"brass": {"base": Color(0.78, 0.52, 0.17), "patch_a": Color(0.6, 0.37, 0.12), "patch_b": Color(0.5, 0.45, 0.22), "patches": 0.35, "patch_size": 1.1, "shine": 0.8, "dents": 0.5},
	"copper": {"base": Color(0.8, 0.4, 0.2), "shine": 0.8},
	"wood": {"base": Color(0.42, 0.28, 0.16), "patch_a": Color(0.3, 0.19, 0.1), "patch_b": Color(0.48, 0.36, 0.22), "patches": 0.6, "patch_size": 0.5},
	"rubber": {"base": Color(0.1, 0.1, 0.11), "shine": 0.15},
	"dark": {"base": Color(0.04, 0.03, 0.03)},
	"paper": {"base": Color(0.9, 0.8, 0.58), "patch_a": Color(0.8, 0.68, 0.45), "patch_b": Color(0.8, 0.68, 0.45), "patches": 0.4, "patch_size": 0.8},
	"ink": {"base": Color(0.14, 0.08, 0.05)},
	"red": {"base": Color(0.72, 0.13, 0.09), "patch_a": Color(0.5, 0.16, 0.1), "patch_b": Color(0.5, 0.16, 0.1), "patches": 0.4, "patch_size": 0.7, "shine": 0.2},
	"orange": {"base": Color(0.9, 0.5, 0.12)},
	"green": {"base": Color(0.42, 0.55, 0.2)},
	"steel": {"base": Color(0.5, 0.48, 0.43), "patch_a": Color(0.45, 0.3, 0.18), "patch_b": Color(0.4, 0.4, 0.36), "patches": 0.5, "patch_size": 0.9, "shine": 0.4},
	"screen": {"base": Color(0.04, 0.22, 0.07), "shine": 0.5},
	"lamp": {"base": Color(0.42, 0.26, 0.16), "shine": 0.5},
}

var helm: Node3D
var engine: Node3D
var gauges: Node3D
var _stick: Node3D
var _plunger: Node3D
var _lever: Node3D
var _needles: Array[Node3D] = []
var _lamp: ShaderMaterial
var _camera: Camera3D
var _for_size := Vector2.ZERO
var _unit := 1.0
var _grip := Vector3.ZERO
var _points := {}


static var _paints := {}


## The panel's paints by material name (made once; shared by everything painted with them).
static func paints() -> Dictionary:
	if _paints.is_empty():
		var noise := NoiseTexture2D.new()
		noise.width = 256
		noise.height = 256
		noise.seamless = true
		noise.noise = FastNoiseLite.new()
		noise.noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
		noise.noise.frequency = 0.012
		noise.noise.fractal_octaves = 3
		for named: String in PAINTS:
			var paint := ShaderMaterial.new()
			paint.shader = load("res://shaders/panel.gdshader")
			paint.set_shader_parameter(&"noise", noise)
			for key: String in PAINTS[named]:
				paint.set_shader_parameter(key, PAINTS[named][key])
			_paints[named] = paint
	return _paints


## Paints any model built with the panel's material names (the computer on the boat, the helmet).
## Its lamps are lit if `lit`.
static func paint(model: Node3D, lit := false) -> void:
	var all := paints()
	var lamp: ShaderMaterial = null
	for mesh: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		for surface in mesh.mesh.get_surface_count():
			var named: String = mesh.mesh.surface_get_material(surface).resource_name
			if named == "lamp" and lit:
				if lamp == null:
					lamp = (all[named] as ShaderMaterial).duplicate()
					lamp.set_shader_parameter(&"base", Color(1.0, 0.5, 0.1))
					lamp.set_shader_parameter(&"glow", Color(0.35, 0.12, 0.0))
				mesh.set_surface_override_material(surface, lamp)
			elif all.has(named):
				mesh.set_surface_override_material(surface, all[named])


func _init() -> void:
	own_world_3d = true
	transparent_bg = true
	msaa_3d = Viewport.MSAA_2X
	render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_camera = Camera3D.new()
	_camera.fov = LENS
	_camera.near = 1.0
	_camera.far = 200.0
	add_child(_camera)
	var world := WorldEnvironment.new()
	world.environment = Environment.new()
	world.environment.background_mode = Environment.BG_CLEAR_COLOR
	add_child(world)
	var paints := PanelModel.paints()
	var model: Node3D = (load(MODEL) as PackedScene).instantiate()
	add_child(model)
	helm = model.find_child("Helm")
	engine = model.find_child("Engine")
	gauges = model.find_child("Gauges")
	_stick = model.find_child("Stick")
	_plunger = model.find_child("Plunger")
	_lever = model.find_child("Lever")
	_grip = (model.find_child("Grip") as Node3D).position
	for named: String in ["SparkA", "SparkB", "Scope", "ScopeEdge"]:
		_points[named] = (model.find_child(named) as Node3D).position
	for named: String in ["NeedleSpeed", "NeedleDepth", "NeedleBurst", "NeedleEvolve"]:
		_needles.append(model.find_child(named))
	for mesh: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		for surface in mesh.mesh.get_surface_count():
			var named: String = mesh.mesh.surface_get_material(surface).resource_name
			if named == "lamp":
				_lamp = (paints[named] as ShaderMaterial).duplicate()
				mesh.set_surface_override_material(surface, _lamp)
			elif paints.has(named):
				mesh.set_surface_override_material(surface, paints[named])


## Lays the housings out for a screen (pixels) and a layout unit (pixels): the helm in the lower
## left corner, the engine in the lower right, the instruments between them.
func lay_out(screen: Vector2, unit: float) -> void:
	if screen == _for_size or screen.x < 2.0 or screen.y < 2.0:
		return
	_for_size = screen
	_unit = unit
	size = Vector2i(screen)
	var wide := screen.x / (unit * METRE)
	var tall := screen.y / (unit * METRE)
	_camera.position = Vector3(0.0, tall * 0.5, _far())
	var upright := wide < 11.5
	var side := SIDE_UPRIGHT if upright else 1.0
	helm.scale = Vector3.ONE * side
	engine.scale = Vector3.ONE * side
	helm.position = Vector3(-wide * 0.5 + SIDE_WIDE * 0.5 * side + 0.08, -0.06, 0.0)
	engine.position = Vector3(wide * 0.5 - SIDE_WIDE * 0.5 * side - 0.08, -0.06, 0.0)
	gauges.position = Vector3(0.0, -0.06 if upright else -GAUGE_SUNK, 0.0)


func _far() -> float:
	return (_for_size.y / (_unit * METRE)) * 0.5 / tan(deg_to_rad(LENS) * 0.5)


## Where a place in the little world (m) is on the screen (pixels).
func to_screen(at: Vector3) -> Vector2:
	var eye := _camera.position
	var near := eye.z / maxf(eye.z - at.z, 0.01)
	return Vector2(_for_size.x * 0.5 + (at.x - eye.x) * near * _unit * METRE, _for_size.y * 0.5 - (at.y - eye.y) * near * _unit * METRE)


# A place given in a housing's own metres, in the little world's.
func _in(housing: Node3D, at: Vector3) -> Vector3:
	return housing.position + at * housing.scale.x


## The middle of the helm's socket, of the plunger, and the scope's middle and edge; the tips of
## the two electrodes: all on the screen.
func stick_home() -> Vector2:
	return to_screen(_in(helm, Vector3(0.0, WELL_Z, 0.0)))


func boost_home() -> Vector2:
	return to_screen(_in(engine, Vector3(0.0, WELL_Z, 0.0)))


func point(named: String) -> Vector2:
	return to_screen(_in(helm if named.begins_with("Spark") else gauges, _points[named]))


# How far round the lever is turned (radians, from standing at the top of its arc) for a speed.
func _lever_turn(speed: float) -> float:
	return deg_to_rad(lerpf(SLOT_FROM, SLOT_TO, clampf(speed, 0.0, 1.0)) - 90.0)


## Where the lever's grip is on the screen for a speed (0 dead slow to 1 full ahead).
func lever_at(speed: float) -> Vector2:
	var local := _lever.position + Basis(Vector3.BACK, _lever_turn(speed)) * _grip
	return to_screen(_in(engine, local))


## Moves the parts: the stick (x right, y up, -1..1), the plunger held or not, the lever's speed,
## and the four needles (0..1: speed, depth, burst left, how far it has grown).
func show_state(stick: Vector2, held: bool, speed: float, needles: Array[float], delta: float) -> void:
	var ease := 1.0 - exp(-22.0 * delta)
	_stick.rotation.x = lerpf(_stick.rotation.x, -stick.y * STICK_LEAN, ease)
	_stick.rotation.y = lerpf(_stick.rotation.y, stick.x * STICK_LEAN, ease)
	_plunger.position.z = lerpf(_plunger.position.z, -PLUNGER_SINK if held else 0.0, ease)
	_lamp.set_shader_parameter(&"base", Color(1.0, 0.5, 0.1) if held else Color(0.42, 0.26, 0.16))
	_lamp.set_shader_parameter(&"glow", Color(0.35, 0.12, 0.0) if held else Color.BLACK)
	_lever.rotation.z = lerpf(_lever.rotation.z, _lever_turn(speed), ease)
	for k in _needles.size():
		_needles[k].rotation.z = lerpf(_needles[k].rotation.z, lerpf(SWING, -SWING, clampf(needles[k], 0.0, 1.0)), ease)
