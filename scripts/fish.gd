class_name Fish
extends Node3D
## A swimmer of any of the game's kinds, at any length: what the player is, and what the other
## fish (and eels and squids) are (Player and Creature extend this).
##
## Each kind is drawn by its GameCommon creature (creatures/<name>: a model built in Blender, its
## markings and swimming in its own shader), made `length` metres from nose to tail with its
## middle at this node, its nose at -z. Only the shark is still Salmon Run 2's code-built mesh
## (scripts/world/props.gd) under shaders/fish.gdshader: there is no shark model yet.

const Props := preload("res://scripts/world/props.gd")
const SHADER := preload("res://shaders/fish.gdshader")
## How far a fish's body bends into its tightest turn (radians, gills to tail).
const CURL := 0.7

## What it is: a name in Species.ALL.
var kind := ""
## Nose to tail, in metres.
var length := 0.2: set = set_length
## The way it is pointing (a unit vector) and how it is moving (m/s).
var heading := Vector3.FORWARD
var velocity := Vector3.ZERO

# The holder that is scaled to the fish's length, and what is in it: a creature's node, or (the
# shark) a mesh under `_material`.
var _body: Node3D
var _look: Node3D
var _material: ShaderMaterial
# How long the look is as built, and how far its nose is ahead of its own origin.
var _long := 1.0
var _front := 0.5
# The look's own seconds a beat, whether its shader bends into a turn, and whether it is near
# enough to be drawn in full.
var _beat := 0.0
var _curls := false
# Its mouth opens by a shader setting (`gape`) with no property of the node's.
var _mouths := false
var _near := true
var _phase := randf() * TAU
var _bend := 0.0
var _flash := 0.0
var _gape := 0.0
## How wide it wants its mouth (0 shut, 1 wide): set each frame by whoever moves it; it is eased.
var bite := 0.0

static var _meshes := {}


## How fast a fish of a length cruises (m/s): bigger is faster, but not by much.
static func pace(of_length: float) -> float:
	return 2.4 * pow(of_length, 0.35) + 0.4


## The light mesh that a school of sardines is drawn with, many at once (its nose at -z).
static func school_mesh(of_kind := "sardine") -> Mesh:
	return (load("res://creatures/%s/%s.gd" % [of_kind, of_kind]) as GDScript).call(&"school_mesh")


## Makes it a swimmer of a kind.
func set_kind(to: String) -> void:
	kind = to
	if _body == null:
		_body = Node3D.new()
		add_child(_body)
	if _look:
		_body.remove_child(_look)
		_look.queue_free()
	_material = null
	_curls = true
	_near = true
	var made := Species.make(to) if Species.has(to) else null
	if made:
		var entry := Species.of(to)
		_wear(made, Species.long_of(to, made), float(entry.get("front", -1.0)), bool(entry.get("curls", true)))
		made.rotation.y = float(entry.get("turn", 0.0))
	else:
		# (the shark, and any kind whose creature is not installed yet)
		if not _meshes.has("shark"):
			_meshes["shark"] = Props.shark_whole()
		_wear_mesh(_meshes["shark"])
	set_length(length)


func set_length(to: float) -> void:
	length = to
	if _body:
		_body.scale = Vector3.ONE * (length / _long)


## Where its mouth is (world).
func mouth() -> Vector3:
	return global_position + heading * length * 0.42


## A flash over it (it has just grown into something new).
func flash() -> void:
	_flash = 1.0


## Whether it is near enough to be drawn in full (far off, its low model stands in).
func detail(near: bool) -> void:
	if near != _near:
		_near = near
		if _look and &"low" in _look:
			_look.set(&"low", not near)


## Each frame: turned the way it is heading, its tail wagging the harder the more `effort` it
## is making (0 idling, 1 cruising, 2 flat out), its body bent by how hard it is turning (-1..1).
func pose(delta: float, effort: float, turning: float) -> void:
	_bend = lerpf(_bend, clampf(turning, -1.0, 1.0), 1.0 - exp(-6.0 * delta))
	_flash = maxf(_flash - delta * 1.6, 0.0)
	var flat := Vector2(heading.x, heading.z).length()
	if flat > 0.001:
		global_basis = Basis.looking_at(heading, Vector3.UP)
	# (it swells as it becomes something new, and settles)
	_body.scale = Vector3.ONE * (length / _long) * (1.0 + 0.35 * _flash * _flash)
	if _material:
		_phase += delta * (5.0 + 9.0 * effort) / pow(maxf(length, 0.1), 0.25)
		_material.set_shader_parameter(&"wag_phase", _phase)
		_material.set_shader_parameter(&"wag_amp", 0.07 + 0.05 * effort)
		_material.set_shader_parameter(&"bend", _bend)
		_material.set_shader_parameter(&"flash", _flash * 0.6)
		return
	if _look == null or not visible:
		return
	# The creature keeps its own beat: quicker the harder it is swimming.
	if _beat > 0.0:
		_look.set(&"beat", _beat / (0.55 + 0.6 * effort))
	if &"swim" in _look:
		_look.set(&"swim", clampf(0.3 + 0.35 * effort, 0.0, 1.0))
	elif &"sway" in _look:
		_look.set(&"sway", 0.6 + 0.45 * effort)
	if &"wings" in _look:
		# (a flying fish spreads its wings when it bolts)
		_look.set(&"wings", move_toward(_look.get(&"wings"), 1.0 if effort > 1.1 else 0.0, delta * 3.0))
	# (it really moves through the water, so there is no more current to add; what walks is told
	# how fast it goes, to step by)
	_look.call(&"step", velocity if &"walk" in _look else Vector3.ZERO, delta)
	if _curls:
		_look.call(&"set_shader_parameter", &"curl", _bend * CURL)
	_gape = move_toward(_gape, bite, delta * (9.0 if bite > _gape else 4.0))
	if &"gape" in _look:
		_look.set(&"gape", _gape)
	elif _mouths:
		_look.call(&"set_shader_parameter", &"gape", 0.07 + _gape * 0.55)


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


# Puts a creature in the holder: `long` its length as built, `front` how far its nose is ahead
# of its origin (half its length when its origin is its middle).
func _wear(look: Node3D, long: float, front := -1.0, curls := true) -> void:
	_look = look
	_long = long
	_front = long * 0.5 if front < 0.0 else front
	_curls = curls
	_mouths = look is SockeyeSalmon or look is CutthroatTrout or look is FlyingFish
	_beat = float(look.get(&"beat")) if &"beat" in look else 0.0
	# (each starts somewhere else in its beat)
	if &"phase" in look:
		look.set(&"phase", randf())
	# (the game model, where its component has one: built at Twilight Princess weight, and its full
	# model is then never loaded)
	if &"game" in look:
		look.set(&"game", true)
	# (and its cartoon eye, where it has one)
	if &"cartoon_eyes" in look:
		look.set(&"cartoon_eyes", 1.0)
	look.position = Vector3(0.0, 0.0, _front - _long * 0.5)
	_body.add_child(look)
	# (Godot's importer makes coarser stand-ins for far off; a body bent in its shader then bends
	# in straight pieces, so they are never used)
	for mesh: MeshInstance3D in look.find_children("*", "MeshInstance3D", true, false):
		mesh.lod_bias = 64.0


# Puts a code-built mesh in the holder, under the old fish shader.
func _wear_mesh(mesh: Mesh) -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	var body := MeshInstance3D.new()
	body.mesh = mesh
	body.material_override = _material
	body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var box := mesh.get_aabb()
	_long = maxf(box.size.z, 0.001)
	_front = -box.position.z
	_material.set_shader_parameter(&"nose_z", box.position.z)
	_material.set_shader_parameter(&"tail_z", box.end.z)
	body.position = Vector3(0.0, 0.0, _front - _long * 0.5)
	_look = body
	_beat = 0.0
	_body.add_child(body)
