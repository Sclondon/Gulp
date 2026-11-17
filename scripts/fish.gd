class_name Fish
extends Node3D
## A fish of any of the game's kinds, at any length: what the player is, and what the other
## fish are (Player and Creature extend this).
##
## The meshes are Salmon Run 2's (scripts/world/props.gd, copied whole: its sardine, small
## fish, sockeye at two ages, tuna and shark), all with the nose at -z; each is drawn so that
## it is `length` metres from nose to tail, with its middle at this node. shaders/fish.gdshader
## wags its tail and bends it into a turn.

const Props := preload("res://scripts/world/props.gd")
const SHADER := preload("res://shaders/fish.gdshader")

## What it is: "sardine", "reef", "reef2", "reef3", "smolt", "salmon", "tuna" or "shark".
var kind := ""
## Nose to tail, in metres.
var length := 0.2: set = set_length
## The way it is pointing (a unit vector) and how it is moving (m/s).
var heading := Vector3.FORWARD
var velocity := Vector3.ZERO

var _body: MeshInstance3D
var _material: ShaderMaterial
var _units := 1.0
var _middle := 0.0
var _phase := randf() * TAU
var _bend := 0.0
var _flash := 0.0

static var _meshes := {}


## How fast a fish of a length cruises (m/s): bigger is faster, but not by much.
static func pace(of_length: float) -> float:
	return 2.4 * pow(of_length, 0.35) + 0.4


## The mesh of a kind (made once).
static func mesh_of(of_kind: String) -> Mesh:
	if not _meshes.has(of_kind):
		var made: Mesh
		match of_kind:
			"sardine": made = Props.sardine()
			"reef": made = Props.small_fish(Color(0.2, 0.5, 0.45), Color(0.9, 0.86, 0.6))
			"reef2": made = Props.small_fish(Color(0.45, 0.4, 0.6), Color(0.95, 0.75, 0.8))
			"reef3": made = Props.small_fish(Color(0.3, 0.42, 0.55), Color(0.82, 0.88, 0.92))
			"smolt": made = Props.salmon("smolt")
			"salmon": made = Props.salmon("ocean")
			"tuna": made = Props.tuna()
			"shark": made = Props.shark_whole()
			_: push_error("Fish: no such kind: " + of_kind)
		_meshes[of_kind] = made
	return _meshes[of_kind]


## Makes it a fish of a kind.
func set_kind(to: String) -> void:
	kind = to
	if _body == null:
		_material = ShaderMaterial.new()
		_material.shader = SHADER
		_body = MeshInstance3D.new()
		_body.material_override = _material
		_body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(_body)
	var mesh := mesh_of(to)
	_body.mesh = mesh
	var box := mesh.get_aabb()
	_units = maxf(box.size.z, 0.001)
	_middle = box.position.z + box.size.z * 0.5
	_material.set_shader_parameter(&"nose_z", box.position.z)
	_material.set_shader_parameter(&"tail_z", box.end.z)
	set_length(length)


func set_length(to: float) -> void:
	length = to
	if _body:
		var grown := length / _units
		_body.scale = Vector3.ONE * grown
		_body.position = Vector3(0.0, 0.0, -_middle * grown)


## Where its mouth is (world).
func mouth() -> Vector3:
	return global_position + heading * length * 0.42


## A flash of white over it (it has just grown into something new).
func flash() -> void:
	_flash = 1.0


## Each frame: turned the way it is heading, its tail wagging the harder the more `effort` it
## is making (0 idling, 1 cruising, 2 flat out), its body bent by how hard it is turning (-1..1).
func pose(delta: float, effort: float, turning: float) -> void:
	_phase += delta * (5.0 + 9.0 * effort) / pow(maxf(length, 0.1), 0.25)
	_bend = lerpf(_bend, clampf(turning, -1.0, 1.0), 1.0 - exp(-6.0 * delta))
	_flash = maxf(_flash - delta * 1.6, 0.0)
	_material.set_shader_parameter(&"wag_phase", _phase)
	_material.set_shader_parameter(&"wag_amp", 0.07 + 0.05 * effort)
	_material.set_shader_parameter(&"bend", _bend)
	_material.set_shader_parameter(&"flash", _flash * 0.6)
	var flat := Vector2(heading.x, heading.z).length()
	if flat > 0.001:
		global_basis = Basis.looking_at(heading, Vector3.UP)


## `from` turned towards `to` (unit vectors) by no more than an angle.
static func turned(from: Vector3, to: Vector3, most: float) -> Vector3:
	var angle := from.angle_to(to)
	if angle < 0.0001:
		return to
	var axis := from.cross(to)
	if axis.length() < 0.00001:
		axis = from.cross(Vector3.UP)
		if axis.length() < 0.00001:
			axis = Vector3.RIGHT
	return from.rotated(axis.normalized(), minf(angle, most)).normalized()
