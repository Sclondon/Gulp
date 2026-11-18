class_name PanelModel
extends SubViewport
## The control panel as a 3D model (the user, 2026-11-18: "lets recreate the ui as a 3d model to
## interact with"): models/control_panel.glb (built by tools/build_panel.py, which says what is in
## it) in a little world of its own, drawn clear-backed over the game by TouchPad, which also
## takes the touches. This places the five housings along the bottom of the screen and moves
## their parts: the stick leans, the plunger sinks and glows, the lever swings round the plunger
## in its slot, the needles turn, the tubes glow.
##
## Decision (Claude's pick, 2026-11-18): a SubViewport with its own World3D and a clear background,
## shown as a texture by a Control. It is the usual way in Godot to put 3D things in a 2D
## interface (the alternatives: a second camera on its own render layer, which the game's
## half-size dithered picture would also shrink and dither; or parenting the model to the game's
## camera, which the water's fog and light would tint). The model is low-poly with one baked picture for
## its paint (tools/build_panel.py bakes it), drawn by an unshaded shader (shaders/panel.gdshader),
## so the little world needs no lights.
##
## The camera looks straight at the housings' faces from far off with a narrow lens: the faces sit
## where a flat panel would, to the pixel, and only what stands out of them (the stick, the lever,
## the posts) leans with the view. `to_screen` is that camera's sum, so touches can be matched to
## parts without asking the engine.

const MODEL := "res://models/control_panel.glb"
## These are tools/build_panel.py's numbers (its PANEL line): change both.
const SIDE_WIDE := 2.6
const SIDE_TALL := 3.9
const SLOT_FROM := 200.0
const SLOT_TO := 108.0
const GAUGE_WIDE := 3.3
const GAUGE_TALL := 2.3
const SMALL_WIDE := 1.5
const SMALL_TALL := 1.1
const SWING := 2.2
## Metres of the model to one of TouchPad's layout units.
const METRE := 100.0
## The camera's lens (degrees, up and down).
const LENS := 24.0
## How far the stick leans, pushed right over (radians), and how far the plunger sinks (m).
const STICK_LEAN := 0.55
const PLUNGER_SINK := 0.14
## The gap left between housings standing side by side (m).
const GAP := 0.1

## How each material of the model is drawn over the baked picture: its shine, and a tint.
const PAINTS := {
	"iron": {},
	# (the user, 2026-11-18: "the controls needs a slightly more brass metallic look")
	"brass": {"shine": 0.62, "tint": Color(1.34, 1.1, 0.66)},
	"copper": {"shine": 0.55, "tint": Color(1.3, 0.95, 0.72)},
	"rubber": {"shine": 0.12},
	"dark": {},
	"paper": {},
	"ink": {},
	"red": {"shine": 0.15},
	"orange": {},
	"green": {},
	"steel": {"shine": 0.3},
	"screen": {"shine": 0.3},
	"lamp": {"shine": 0.3},
	"ember": {},
	"wood": {},
}
const ATLAS := "res://textures/panel/panel_atlas.png"

var helm: Node3D
var engine: Node3D
var gauges: Node3D
var switches: Node3D
var aux: Node3D
## Whether the housings stand in one row (a wide screen) or the two small boxes stand on top of
## the instruments (an upright one).
var in_a_row := true
var _stick: Node3D
var _plunger: Node3D
var _lever: Node3D
var _needles: Array[Node3D] = []
var _lamp: ShaderMaterial
var _glass: ShaderMaterial
var _camera: Camera3D
var _for_size := Vector2.ZERO
var _unit := 1.0
var _grip := Vector3.ZERO
var _points := {}

static var _paints := {}


## The panel's paints by material name (made once; shared by everything painted with them).
static func paints() -> Dictionary:
	if _paints.is_empty():
		for named: String in PAINTS:
			var paint := ShaderMaterial.new()
			paint.shader = load("res://shaders/panel.gdshader")
			paint.set_shader_parameter(&"atlas", load(ATLAS))
			for key: String in PAINTS[named]:
				paint.set_shader_parameter(key, PAINTS[named][key])
			_paints[named] = paint
	return _paints


## Paints any model built with the panel's material names (the computer on the boat, the helmet).
## Its lamps are lit if `lit`. `atlas`: its own baked picture, if it is not the panel's.
static func paint(model: Node3D, lit := false, atlas := "") -> void:
	var all := paints()
	if atlas != "":
		all = {}
		for named: String in paints():
			all[named] = (paints()[named] as ShaderMaterial).duplicate()
			all[named].set_shader_parameter(&"atlas", load(atlas))
	var lamp: ShaderMaterial = null
	for mesh: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		for surface in mesh.mesh.get_surface_count():
			var named: String = mesh.mesh.surface_get_material(surface).resource_name
			if named == "glass":
				mesh.set_surface_override_material(surface, glass_paint())
			elif named == "lamp" and lit:
				if lamp == null:
					lamp = (all[named] as ShaderMaterial).duplicate()
					lamp.set_shader_parameter(&"tint", Color(3.2, 1.6, 0.6))
					lamp.set_shader_parameter(&"glow", Color(0.3, 0.1, 0.0))
				mesh.set_surface_override_material(surface, lamp)
			elif all.has(named):
				mesh.set_surface_override_material(surface, all[named])


## A vacuum tube's clear glass.
static func glass_paint() -> ShaderMaterial:
	var glass := ShaderMaterial.new()
	glass.shader = load("res://shaders/panel_glass.gdshader")
	return glass


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
	var model: Node3D = (load(MODEL) as PackedScene).instantiate()
	add_child(model)
	PanelModel.paint(model)
	helm = model.find_child("Helm")
	engine = model.find_child("Engine")
	gauges = model.find_child("Gauges")
	switches = model.find_child("Switches")
	aux = model.find_child("Aux")
	_stick = model.find_child("Stick")
	_plunger = model.find_child("Plunger")
	_lever = model.find_child("Lever")
	_grip = (model.find_child("Grip") as Node3D).position
	for named: String in ["SparkA", "SparkB", "Length", "Scope", "ScopeEdge", "Pause"]:
		_points[named] = (model.find_child(named) as Node3D).position
	for named: String in ["NeedleSpeed", "NeedleDepth", "NeedleBurst", "NeedleEvolve"]:
		_needles.append(model.find_child(named))
	# (the plunger's lamp and the tubes' glass are this panel's own, to light by themselves)
	for mesh: MeshInstance3D in _plunger.find_children("*", "MeshInstance3D", true, false) + [_plunger]:
		for surface in mesh.mesh.get_surface_count():
			if mesh.mesh.surface_get_material(surface).resource_name == "lamp":
				_lamp = (paints()["lamp"] as ShaderMaterial).duplicate()
				mesh.set_surface_override_material(surface, _lamp)
	var tubes := model.find_child("TubeGlass") as MeshInstance3D
	_glass = tubes.get_surface_override_material(0)


## Lays the housings out for a screen (pixels) and a layout unit (pixels): the helm in the lower
## left corner, the engine in the lower right, the instruments between them; the switch box and
## the valve box either side of the instruments where there is room, and under them where
## there is not (an upright phone), the side housings then made smaller to fit.
func lay_out(screen: Vector2, unit: float) -> void:
	if screen == _for_size or screen.x < 2.0 or screen.y < 2.0:
		return
	_for_size = screen
	_unit = unit
	size = Vector2i(screen)
	var wide := screen.x / (unit * METRE)
	var tall := screen.y / (unit * METRE)
	_camera.position = Vector3(0.0, tall * 0.5, _far())
	in_a_row = wide >= SIDE_WIDE * 2.0 + GAUGE_WIDE + SMALL_WIDE * 2.0 + GAP * 6.0
	var side := 1.0 if in_a_row else clampf((wide - GAUGE_WIDE - GAP * 4.0) / (SIDE_WIDE * 2.0), 0.5, 1.0)
	var foot := -0.04
	helm.scale = Vector3.ONE * side
	engine.scale = Vector3.ONE * side
	helm.position = Vector3(-wide * 0.5 + SIDE_WIDE * 0.5 * side + GAP, foot, 0.0)
	engine.position = Vector3(wide * 0.5 - SIDE_WIDE * 0.5 * side - GAP, foot, 0.0)
	gauges.position = Vector3(0.0, foot, 0.0)
	if in_a_row:
		switches.position = Vector3(-(GAUGE_WIDE + SMALL_WIDE) * 0.5 - GAP, foot, 0.0)
		aux.position = Vector3((GAUGE_WIDE + SMALL_WIDE) * 0.5 + GAP, foot, 0.0)
	else:
		# (under the instruments, as in the concept: the user, "These go under the sonar")
		switches.position = Vector3(-SMALL_WIDE * 0.5 - GAP * 0.5, foot, 0.0)
		aux.position = Vector3(SMALL_WIDE * 0.5 + GAP * 0.5, foot, 0.0)
		gauges.position = Vector3(0.0, foot + SMALL_TALL + 0.03, 0.0)


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


## The middle of the helm's socket and of the plunger, on the screen.
func stick_home() -> Vector2:
	return to_screen(_in(helm, Vector3(_stick.position.x, _stick.position.y, 0.0)))


func boost_home() -> Vector2:
	return to_screen(_in(engine, Vector3(_plunger.position.x, _plunger.position.y, 0.0)))


## A named place on the screen: "SparkA", "SparkB" (the electrodes' tips), "Length" (on the growth
## dial's face, under its hub), "Scope", "ScopeEdge", "Pause" (the pause button).
func point(named: String) -> Vector2:
	var housing := gauges
	if named.begins_with("Spark") or named == "Length":
		housing = helm
	elif named == "Pause":
		housing = aux
	return to_screen(_in(housing, _points[named]))


## How big things on a housing's face are on the screen: pixels to a metre of the model there.
func scale_of(named: String) -> float:
	return _unit * METRE * (helm.scale.x if named == "Length" else 1.0)


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
	_lamp.set_shader_parameter(&"tint", Color(3.2, 1.6, 0.6) if held else Color.WHITE)
	_lamp.set_shader_parameter(&"glow", Color(0.3, 0.1, 0.0) if held else Color.BLACK)
	_lever.rotation.z = lerpf(_lever.rotation.z, _lever_turn(speed), ease)
	for k in _needles.size():
		_needles[k].rotation.z = lerpf(_needles[k].rotation.z, lerpf(SWING, -SWING, clampf(needles[k], 0.0, 1.0)), ease)
	# (the tubes burn brighter while it bursts)
	_glass.set_shader_parameter(&"lit", (0.75 if held else 0.45) + 0.06 * sin(Time.get_ticks_msec() * 0.013))
