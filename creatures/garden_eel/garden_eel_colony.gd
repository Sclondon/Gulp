class_name GardenEelColony
extends MultiMeshInstance3D
## A field of garden eels (see GardenEel for one), drawn cheaply: one MultiMesh of the light colony
## model (about 230 triangles an eel, its eye drawn on the skin), every eel's pose bent in the vertex
## shader from its instance's custom data (how much of it is out of its burrow, its own phase offset,
## how far it curls, how much it sways). Hundreds cost one draw.
##
##     var eels := GardenEelColony.new()
##     add_child(eels)                      # in the tree before plant(): places are world points
##     eels.plant(points_on_the_sand)       # PackedVector3Array
##     # each frame:
##     eels.disturb(player.global_position, 1.5)
##
## Eels within `radius` of a disturbance sink quickly into their burrows, stay down while it lasts
## and a little after (`hide_time`), then come back out over a few seconds (`rise_time`). An eel
## that is eaten: `take(i)` hides it until `restore(i)` (after which it comes back out in its own
## time). The colony runs on a clock of its own (its `_process`), so it needs no driving.
##
## Each eel's head points along `facing` (into the current) give or take `spread` radians; its
## burrow's mouth is the planted point. Positions handed in and out are world positions; the colony
## node is not expected to move after `plant`.

const MESH := "res://creatures/garden_eel/models/garden_eel_colony.glb"
const SHADER := preload("res://creatures/garden_eel/garden_eel_colony.gdshader")

## Seconds one sway takes.
@export var beat := 3.2
## How strongly they sway (1 as they live).
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## The size of every eel (1 life size: 0.4 m long, 0.3 m of it standing above the sand); each eel
## is a little bigger or smaller than this, at random.
@export var eel_scale := 1.0
## Which way their heads point, in the colony's own space (level; into the current).
@export var facing := Vector3(0.0, 0.0, -1.0)
## How far each eel turns from `facing` at random, radians either way.
@export var spread := 0.35
## Seconds an eel takes to sink all the way when disturbed.
@export var sink_time := 0.35
## Seconds it stays down after the last disturbance (each eel a little more or less).
@export var hide_time := 2.5
## Seconds it takes to come all the way out again (each eel a little more or less).
@export var rise_time := 4.0

var _material: ShaderMaterial
var _world := PackedVector3Array()
var _placed: Array[Transform3D] = []
var _out := PackedFloat32Array()
var _hold := PackedFloat32Array()
var _pace := PackedFloat32Array()
var _shape := PackedColorArray()
var _taken := PackedByteArray()
var _clock := 0.0

static var _mesh: Mesh


## The colony model's mesh (one surface, to wear `new_material()`).
static func colony_mesh() -> Mesh:
	if _mesh == null:
		var made := (load(MESH) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_mesh = GardenEel.without_lods(found.mesh)
		made.free()
	return _mesh


## A new material for `colony_mesh()` in a MultiMesh with custom data (see garden_eel_colony.gdshader).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()
	material_override = _material
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _ready() -> void:
	_send(&"sway", sway)


## Plants one eel at each of `places` (world points on the sand: the mouths of their burrows),
## all out. Replaces any planted before. Eel `i` is the one at `places[i]`.
func plant(places: PackedVector3Array) -> void:
	var count := places.size()
	_world = places.duplicate()
	_out = PackedFloat32Array()
	_out.resize(count)
	_out.fill(1.0)
	_hold = PackedFloat32Array()
	_hold.resize(count)
	_pace = PackedFloat32Array()
	_pace.resize(count)
	_shape = PackedColorArray()
	_shape.resize(count)
	_taken = PackedByteArray()
	_taken.resize(count)
	_placed.resize(count)
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	multi.use_custom_data = true
	multi.mesh = colony_mesh()
	multi.instance_count = count
	var ahead := Vector3(facing.x, 0.0, facing.z)
	if ahead.length() < 0.001:
		ahead = Vector3.FORWARD
	var yaw := atan2(-ahead.x, -ahead.z)
	var dice := RandomNumberGenerator.new()
	var inverse := global_transform.affine_inverse() if is_inside_tree() else Transform3D.IDENTITY
	for i in count:
		dice.seed = hash(i * 7919 + 13)
		var size := eel_scale * dice.randf_range(0.82, 1.15)
		var turn := yaw + dice.randf_range(-spread, spread)
		var turned := Basis(Vector3.UP, turn).scaled(Vector3.ONE * size)
		_placed[i] = Transform3D(turned, inverse * places[i])
		multi.set_instance_transform(i, _placed[i])
		_pace[i] = dice.randf_range(0.75, 1.3)
		_shape[i] = Color(1.0, dice.randf(), dice.randf_range(0.85, 1.12), dice.randf_range(0.7, 1.2))
		multi.set_instance_custom_data(i, _shape[i])
	multimesh = multi
	# (curled over and swaying, they reach past the still model's box)
	extra_cull_margin = 0.2 * eel_scale


## How many eels are planted.
func count() -> int:
	return _world.size()


## Every eel within `radius` (metres) of `at` (a world point) sinks into its burrow and stays down
## while this keeps being called, and `hide_time` after. Call it each frame with what frightens them.
func disturb(at: Vector3, radius: float) -> void:
	var near := radius * radius
	for i in _world.size():
		if _world[i].distance_squared_to(at) < near:
			_hold[i] = hide_time * _pace[i]


## The eel nearest `at` (a world point) that is out of its burrow (`is_out`), or with `any` true the
## nearest that has not been taken; -1 if there is none.
func nearest(at: Vector3, any := false) -> int:
	var best := -1
	var best_d := INF
	for i in _world.size():
		if _taken[i] or (not any and _out[i] < 0.5):
			continue
		var d := _world[i].distance_squared_to(at)
		if d < best_d:
			best_d = d
			best = i
	return best


## Where eel `i`'s burrow is (a world point on the sand, as planted).
func place_of(i: int) -> Vector3:
	return _world[i]


## Where eel `i`'s head is now (a world point; not counting its sway).
func head_of(i: int) -> Vector3:
	var local := GardenEel.head_at(_out[i], 2.0 * _shape[i].b)
	return global_transform * (_placed[i] * local)


## Whether eel `i` is out of its burrow (more than half) and not taken.
func is_out(i: int) -> bool:
	return not _taken[i] and _out[i] > 0.5


## How much of eel `i` is out of its burrow, 0..1.
func out_of(i: int) -> float:
	return _out[i]


## Hides eel `i` at once (it has been eaten) until `restore(i)`.
func take(i: int) -> void:
	_taken[i] = 1
	_out[i] = 0.0
	_write(i)


## Lets eel `i` come back: it stays down `hide_time`, then comes out.
func restore(i: int) -> void:
	_taken[i] = 0
	_hold[i] = hide_time * _pace[i]


func _process(delta: float) -> void:
	_clock = fposmod(_clock + delta, maxf(beat, 0.01))
	_material.set_shader_parameter(&"phase", _clock / maxf(beat, 0.01))
	for i in _world.size():
		if _taken[i]:
			continue
		var was := _out[i]
		var now := was
		if _hold[i] > 0.0:
			_hold[i] -= delta
			now = maxf(was - delta / sink_time, 0.0)
		elif was < 1.0:
			now = minf(was + delta / (rise_time * _pace[i]), 1.0)
		if now != was:
			_out[i] = now
			_write(i)


func _write(i: int) -> void:
	var own := _shape[i]
	own.r = _out[i]
	multimesh.set_instance_custom_data(i, own)


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)
