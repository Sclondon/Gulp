class_name Submarine
extends Node3D
## An old-time submarine, about 9 m long: a stubby riveted hull of dark rusted iron plates with a
## tarnished brass band at the bow, a big round glass dome in a brass frame, two round portholes a
## side glowing warm, a small conning tower with a hatch, a periscope and a short antenna, two
## jointed grabbing arms under the bow, three searchlights, a caged propeller and fin rudders at the
## stern, and a ballast tank strapped to each side with copper pipes. Nobody is seen inside (the
## dome is dark glass with a glint).
##
## How it looks and moves its parts only: whatever drives it puts it where it is and turns it the
## way it goes, as with GameCommon's sea creatures. Its bow points along its own -Z (Godot's
## forward), up is +Y; its origin is on the hull's middle line, half way along. No bubbles (the
## game's job) and no sound.
##
## Driven like a big animal: call `step(velocity, delta)` each frame. The propeller turns with its
## speed (`phase`, one `beat`, `prop_turns` turns a beat, so a picture of it loops), and, with
## `auto_steer` on, the rudder and the diving planes follow how it is turning and climbing. Or set
## any part yourself: `rudder`, `planes`, `reach`, `grip` (or each arm's), `periscope_turn`,
## `periscope_raise`, `lights`, `beams`.
##
## The model is creatures/submarine/models/submarine.glb, built by tools/build_submarine.py (Blender,
## its paint baked into textures/submarine_atlas.png, where it glows into submarine_glow.png). It is
## drawn with Godot's own StandardMaterial3D (no shader of its own): the paint lit by the scene, the
## glass glossy and glowing by `lights`, the beams additive.

const MODEL := "res://creatures/submarine/models/submarine.glb"
const ATLAS := "res://creatures/submarine/textures/submarine_atlas.png"
const GLOW := "res://creatures/submarine/textures/submarine_glow.png"
## As the model is built (metres, at scale 1): from the back of the propeller's cage to the front
## of the dome; the hull's depth and width (without the tower, the tanks, the fins or the arms).
const LENGTH := 9.05
const DEPTH := 2.92
const WIDTH := 2.92
## Everything, as built and at rest: the box round it all (the arms hang below, the periscope and
## the antenna stand above, the tanks stand out to the sides), in its own space.
const BOX := AABB(Vector3(-2.2, -2.25, -4.69), Vector3(4.39, 5.48, 9.23))
## How far the parts turn at 1 (radians): the rudder, the planes; the shoulder and the elbow at full
## reach; each finger at a full grip. (The arms' and the fingers' are in the build script too, which
## checks them for clipping: change both.)
const RUDDER_TURN := 0.5
const PLANES_TURN := 0.4
const REACH_SHOULDER := 0.75
const REACH_ELBOW := -1.15
const GRIP_TURN := 0.22
## How far the periscope slides up at `periscope_raise` 1 (metres; the build script bakes its paint
## raised this far, so keep the two the same).
const PERISCOPE_LIFT := 0.45
## The searchlights' lenses (in its own space) and the way each one shines.
const LAMPS := {
	&"Top": [Vector3(0.0, 1.6, -2.95), Vector3(0.0, -0.08, -1.0)],
	&"Left": [Vector3(-0.42, -1.56, -3.25), Vector3(-0.08, -0.28, -1.0)],
	&"Right": [Vector3(0.42, -1.56, -3.25), Vector3(0.08, -0.28, -1.0)],
}

## Seconds one beat takes (at `throttle` 1): the propeller turns `prop_turns` times in a beat.
@export var beat := 2.0
## How many times the propeller turns in a beat (a whole number, so a beat loops).
@export var prop_turns := 3
## How hard the engine is going: 0 stopped, 1 cruising, up to 2 flat out. `step` moves `phase` on by
## delta / beat times this; with `auto_steer` on, `step` sets it from its speed.
@export_range(0.0, 2.0) var throttle := 1.0
## Its cruising speed (metres a second): `step` with `auto_steer` takes this speed as throttle 1.
@export var cruise_speed := 2.0
## `step` sets the throttle, the rudder and the planes from how it is moving and turning.
@export var auto_steer := true
## The rudder: -1 hard to port (it turns left), 1 hard to starboard.
@export_range(-1.0, 1.0) var rudder := 0.0:
	set(value):
		rudder = clampf(value, -1.0, 1.0)
		_pose()
## The diving planes: -1 nose down (diving), 1 nose up (climbing).
@export_range(-1.0, 1.0) var planes := 0.0:
	set(value):
		planes = clampf(value, -1.0, 1.0)
		_pose()
## Both arms: 0 as built (hanging forward under the bow), 1 reaching straight out ahead.
@export_range(0.0, 1.0) var reach := 0.0:
	set(value):
		reach = clampf(value, 0.0, 1.0)
		reach_left = reach
		reach_right = reach
## Both claws: 0 open, 1 shut.
@export_range(0.0, 1.0) var grip := 0.0:
	set(value):
		grip = clampf(value, 0.0, 1.0)
		grip_left = grip
		grip_right = grip
@export_range(0.0, 1.0) var reach_left := 0.0:
	set(value):
		reach_left = clampf(value, 0.0, 1.0)
		_pose()
@export_range(0.0, 1.0) var reach_right := 0.0:
	set(value):
		reach_right = clampf(value, 0.0, 1.0)
		_pose()
@export_range(0.0, 1.0) var grip_left := 0.0:
	set(value):
		grip_left = clampf(value, 0.0, 1.0)
		_pose()
@export_range(0.0, 1.0) var grip_right := 0.0:
	set(value):
		grip_right = clampf(value, 0.0, 1.0)
		_pose()
## The periscope turned about its upright: in half turns (1 looks straight back), 0 ahead.
@export_range(-1.0, 1.0) var periscope_turn := 0.0:
	set(value):
		periscope_turn = clampf(value, -1.0, 1.0)
		_pose()
## The periscope slid up out of the tower: 0 as built, 1 PERISCOPE_LIFT higher.
@export_range(0.0, 1.0) var periscope_raise := 0.0:
	set(value):
		periscope_raise = clampf(value, 0.0, 1.0)
		_pose()
## The portholes', the lamps' lenses' and the valve tubes' glow: 0 dark glass, 1 lit (warm), more
## brighter still.
@export_range(0.0, 3.0) var lights := 1.0:
	set(value):
		lights = maxf(value, 0.0)
		_light()
## The searchlights' beams: 0 none, 1 as built. (They show only while `lights` is more than 0 too.)
@export_range(0.0, 2.0) var beams := 1.0:
	set(value):
		beams = maxf(value, 0.0)
		_light()
## The beams' colour, times the cones' own (a warm white, brightest at the lamp).
@export var beam_colour := Color(1.0, 1.0, 1.0)
## How far through a beat it is, 0 to 1 (only the fraction counts): the propeller's turn. `step`
## moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_pose()

static var _scene: PackedScene
static var _paint: StandardMaterial3D
static var _glass_base: StandardMaterial3D

var _model: Node3D
var _parts := {}
var _rest := {}
var _glass: StandardMaterial3D
var _beam: StandardMaterial3D
var _last_place := Vector3.ZERO
var _last_basis := Basis.IDENTITY
var _stepped := false


## The painted material every opaque part wears (one for all submarines).
static func paint_material() -> StandardMaterial3D:
	if _paint == null:
		_paint = StandardMaterial3D.new()
		_paint.albedo_texture = load(ATLAS)
		_paint.roughness = 0.62
		_paint.metallic_specular = 0.45
		_paint.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	return _paint


## A new glass material (the dome, the portholes, the lenses, the valve tubes): the same picture,
## glossy, glowing where submarine_glow.png says by `energy`.
static func new_glass_material(energy := 1.0) -> StandardMaterial3D:
	var made := StandardMaterial3D.new()
	made.albedo_texture = load(ATLAS)
	made.roughness = 0.08
	made.metallic_specular = 0.9
	made.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	made.emission_enabled = true
	# (the glow is the picture alone: StandardMaterial3D adds `emission` to it, so that is black)
	made.emission = Color.BLACK
	made.emission_operator = BaseMaterial3D.EMISSION_OP_ADD
	made.emission_texture = load(GLOW)
	made.emission_energy_multiplier = energy
	return made


## A new material for the beams: additive, unlit, its colour from the cones' vertex colours times
## `colour`, both faces, not fogged (fog would light the whole cone).
static func new_beam_material(colour: Color) -> StandardMaterial3D:
	var made := StandardMaterial3D.new()
	made.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	made.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	made.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	made.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
	made.cull_mode = BaseMaterial3D.CULL_DISABLED
	made.vertex_color_use_as_albedo = true
	made.albedo_color = colour
	made.disable_receive_shadows = true
	made.disable_fog = true
	return made


func _ready() -> void:
	if _scene == null:
		_scene = load(MODEL)
	_model = _scene.instantiate()
	add_child(_model)
	_glass = new_glass_material()
	_beam = new_beam_material(beam_colour)
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		_parts[StringName(mesh.name)] = mesh
		_rest[StringName(mesh.name)] = mesh.transform
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		for surface in mesh.mesh.get_surface_count():
			var named := mesh.mesh.surface_get_material(surface).resource_name if mesh.mesh.surface_get_material(surface) else ""
			if named == "SubGlass":
				mesh.set_surface_override_material(surface, _glass)
			elif named == "SubBeam":
				mesh.set_surface_override_material(surface, _beam)
				mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			else:
				mesh.set_surface_override_material(surface, paint_material())
	# (the arms swing below and ahead of where they hang as built)
	for named: StringName in [&"ArmLeft", &"ArmRight", &"ForearmLeft", &"ForearmRight"]:
		if _parts.has(named):
			_parts[named].extra_cull_margin = 1.5
	_last_place = global_position
	_last_basis = global_basis
	_pose()
	_light()


## Each frame: the propeller turns on with the throttle; with `auto_steer`, the throttle follows its
## speed (from `velocity`, or, when that is zero, from how far it has really moved since the last
## step) and the rudder and the planes follow how it is turning and climbing.
func step(velocity: Vector3, delta: float) -> void:
	if delta <= 0.0:
		return
	if auto_steer and is_inside_tree():
		var moved := velocity
		if moved == Vector3.ZERO and _stepped:
			moved = (global_position - _last_place) / delta
		var ahead := -global_basis.z
		var was_ahead := -_last_basis.z
		var speed := moved.length()
		var settle := 1.0 - exp(-3.0 * delta)
		throttle = lerpf(throttle, clampf(speed / maxf(cruise_speed, 0.01), 0.0, 2.0), settle)
		if _stepped:
			# (turning left is a positive turn about up; the rudder then swings to port, -1)
			var flat_now := Vector2(ahead.x, ahead.z)
			var flat_was := Vector2(was_ahead.x, was_ahead.z)
			var yaw := 0.0
			if flat_now.length() > 0.01 and flat_was.length() > 0.01:
				yaw = -flat_was.angle_to(flat_now) / delta
			var climb := 0.0
			if speed > 0.05:
				climb = moved.normalized().y
			rudder = lerpf(rudder, clampf(-yaw * 2.0, -1.0, 1.0), settle)
			planes = lerpf(planes, clampf(climb * 3.0 + (ahead.y - was_ahead.y) / delta, -1.0, 1.0), settle)
		_last_place = global_position
		_last_basis = global_basis
		_stepped = true
	phase += delta / maxf(beat, 0.01) * throttle


## A part by its node name (Hull, Propeller, Rudder, Planes, Periscope, ArmLeft, ForearmLeft,
## ClawLeftUpper, ClawLeftLower, and the same on the right, BeamTop, BeamLeft, BeamRight), or null.
func part(named: StringName) -> MeshInstance3D:
	return _parts.get(named)


## The glass material (to tint its glow, for instance): the portholes, the lenses, the dome.
func glass_material() -> StandardMaterial3D:
	return _glass


func _pose() -> void:
	if _parts.is_empty():
		return
	_turn(&"Propeller", Basis(Vector3.BACK, phase * TAU * prop_turns))
	_turn(&"Rudder", Basis(Vector3.UP, rudder * RUDDER_TURN))
	# (climbing, their trailing edges lift: the stern is pushed down and the bow up)
	_turn(&"Planes", Basis(Vector3.RIGHT, -planes * PLANES_TURN))
	_turn(&"Periscope", Basis(Vector3.UP, periscope_turn * PI), Vector3.UP * periscope_raise * PERISCOPE_LIFT)
	for side: String in ["Left", "Right"]:
		var r: float = reach_left if side == "Left" else reach_right
		var g: float = grip_left if side == "Left" else grip_right
		_turn(StringName("Arm" + side), Basis(Vector3.RIGHT, REACH_SHOULDER * r))
		_turn(StringName("Forearm" + side), Basis(Vector3.RIGHT, REACH_ELBOW * r))
		_turn(StringName("Claw" + side + "Upper"), Basis(Vector3.RIGHT, -GRIP_TURN * g))
		_turn(StringName("Claw" + side + "Lower"), Basis(Vector3.RIGHT, GRIP_TURN * g))


func _turn(named: StringName, turn: Basis, shift := Vector3.ZERO) -> void:
	var mesh: MeshInstance3D = _parts.get(named)
	if mesh:
		var rest: Transform3D = _rest[named]
		mesh.transform = Transform3D(rest.basis * turn, rest.origin + shift)


func _light() -> void:
	if _glass:
		_glass.emission_energy_multiplier = 1.3 * lights
	if _beam:
		var on := beams * minf(lights, 1.0)
		_beam.albedo_color = Color(beam_colour.r * on, beam_colour.g * on, beam_colour.b * on)
	for named: StringName in [&"BeamTop", &"BeamLeft", &"BeamRight"]:
		if _parts.has(named):
			_parts[named].visible = beams * lights > 0.001
