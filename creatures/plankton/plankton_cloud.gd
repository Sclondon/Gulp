class_name PlanktonCloud
extends Node3D
## A drifting cloud of plankton, cheap in the thousands: tiny specks (copepods, diatom chains,
## radiolarians and crab larvae, each a handful of triangles built in Blender) drawn by one
## MultiMesh, each tumbling slowly and drifting about its place, glittering as a face turns to the
## eye. All of the moving is in plankton.gdshader; nothing moves on the CPU but what is eaten.
##
##   var cloud := PlanktonCloud.new()
##   add_child(cloud)
##   cloud.fill(Vector3(0, -6, 0), 3.0, 1500)   # 1500 specks in a ball 3 m in radius (the cloud's own space)
##   # something with a mouth, each frame it feeds:
##   var eaten := cloud.bite(mouth.global_position, 0.3)   # how many specks it took
##   if cloud.amount < 0.2: ...                             # little left
##
## Eaten specks vanish and, `regrow` seconds or so later, drift back in: they grow again out of
## nothing at a new place in the cloud over `grow_in` seconds.
##
## The shader reads the global shader uniform `water_clock` (seconds). If the project declares
## none (Project Settings > Shader Globals), the first cloud adds one and runs it; if it declares
## one, the game sets it (as GameCommon's kelp does: the two share the one clock).

const MODEL := "res://creatures/plankton/models/plankton_specks.glb"
const SHADER := "res://creatures/plankton/plankton.gdshader"
const CLOCK := &"water_clock"
## The kinds of speck, as the mesh holds them (the custom data's green picks one).
enum Kind { COPEPOD, DIATOM, RADIOLARIAN, LARVA }
## How big a speck is as built (metres across, about) and how many triangles each kind has.
const SPECK := 0.009
const TRIANGLES := 73

## How big the specks are: 1 as built (a few millimetres to a centimetre across, spines and all).
@export_range(0.1, 20.0) var speck_size := 1.0:
	set(value):
		speck_size = value
		_send(&"speck_size", value)
		_box()
## How far each speck drifts about its place (metres).
@export_range(0.0, 3.0) var drift := 0.25:
	set(value):
		drift = value
		_send(&"drift", value)
		_box()
## How fast the specks tumble (turns a second, about).
@export_range(0.0, 2.0) var spin := 0.12:
	set(value):
		spin = value
		_send(&"spin", value)
## How much of each kind (copepods, diatom chains, radiolarians, crab larvae): only the shares
## count. Set it before `fill`.
@export var mix := Vector4(4.0, 2.0, 1.5, 1.0)
## About how many seconds an eaten speck is gone before it drifts back in, and how long it takes to
## grow back in.
@export var regrow := 8.0
@export var grow_in := 2.5
## Changes where the specks are and which kind each is.
@export var seed := 1

## How much of the cloud is there, 0 (all eaten) to 1 (all there). Read only.
var amount: float:
	get:
		if _count == 0:
			return 0.0
		return clampf(1.0 - _missing / float(_count), 0.0, 1.0)

static var _mesh: Mesh
static var _shader: Shader
## Whether this component added `water_clock` (and so must run it), and the frame it last did.
static var _runs_clock := false
static var _clock := 0.0
static var _clock_frame := -1

var _material: ShaderMaterial
var _view: MultiMeshInstance3D
var _many: MultiMesh
var _rng := RandomNumberGenerator.new()
var _centre := Vector3.ZERO
var _radius := 0.0
var _count := 0
var _places := PackedVector3Array()
var _custom: Array[Color] = []
## Each eaten speck: [which, the time it comes back, 0 gone / 1 growing back].
var _away: Array = []
var _missing := 0.0
var _time := 0.0


## The specks' mesh: all four kinds at the origin (the shader shows one a speck).
static func mesh_of() -> Mesh:
	if _mesh == null:
		var made := (load(MODEL) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_mesh = found.mesh
		made.free()
	return _mesh


## A new material wearing plankton.gdshader (the top of the shader lists its settings).
static func new_material() -> ShaderMaterial:
	if _shader == null:
		# (the shader names the clock, so the clock must be there before the shader is read; ask
		# the project, and whether another component has added it already)
		if not ProjectSettings.has_setting("shader_globals/" + CLOCK) and not Engine.has_meta(CLOCK):
			RenderingServer.global_shader_parameter_add(CLOCK, RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
			Engine.set_meta(CLOCK, true)
			_runs_clock = true
		_shader = load(SHADER)
	var made := ShaderMaterial.new()
	made.shader = _shader
	return made


func _init() -> void:
	_material = new_material()
	_many = MultiMesh.new()
	_many.transform_format = MultiMesh.TRANSFORM_3D
	_many.use_custom_data = true
	_view = MultiMeshInstance3D.new()
	_view.multimesh = _many
	_view.material_override = _material
	_view.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_view.name = "Specks"
	add_child(_view)


## Fills the cloud (taking up whatever was in it before): `count` specks scattered through a ball
## `radius` metres round `centre` (in this node's own space), thicker towards its middle.
func fill(centre: Vector3, radius: float, count: int) -> void:
	_rng.seed = seed
	_centre = centre
	_radius = maxf(radius, 0.01)
	_count = maxi(count, 0)
	_away.clear()
	_missing = 0.0
	_places.resize(_count)
	_custom.resize(_count)
	_many.mesh = mesh_of()
	_many.instance_count = _count
	for i in _count:
		_places[i] = _somewhere()
		_custom[i] = Color(_rng.randf(), float(_pick_kind()), 1.0, _rng.randf_range(0.7, 1.3))
		_many.set_instance_transform(i, Transform3D(Basis.IDENTITY, _places[i]))
		_many.set_instance_custom_data(i, _custom[i])
	_send(&"speck_size", speck_size)
	_send(&"drift", drift)
	_send(&"spin", spin)
	_box()


## Something ate here: hides every speck within `reach` metres of `at` (a place in the world) and
## returns how many. (Measured from where each speck's drift is centred: it may be up to `drift`
## off that.) They drift back in later on their own.
func bite(at: Vector3, reach: float) -> int:
	if _count == 0:
		return 0
	var here := to_local(at)
	var scaled := reach / maxf(global_basis.get_scale().x, 0.0001)
	if here.distance_to(_centre) > _radius + scaled:
		return 0
	var limit := scaled * scaled
	var taken := 0
	for i in _count:
		if _custom[i].b <= 0.0:
			continue
		if _places[i].distance_squared_to(here) <= limit:
			_missing += _custom[i].b
			_custom[i].b = 0.0
			_many.set_instance_custom_data(i, _custom[i])
			_away.append([i, _time + regrow * _rng.randf_range(0.6, 1.4), 0])
			taken += 1
	return taken


## How many specks the cloud has, and how many triangles one draw of it sends (every kind's, of
## which a speck shows one).
func counts() -> Dictionary:
	return {"specks": _count, "away": _away.size(), "triangles": _count * TRIANGLES}


## Sets one of the shader's settings (`glitter`, `drift_period`, and the colours `copepod`,
## `eye_spot`, `diatom`, `radiolarian`, `larva`, `glass`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


func material() -> ShaderMaterial:
	return _material


func _process(delta: float) -> void:
	if _runs_clock and _clock_frame != Engine.get_process_frames():
		_clock_frame = Engine.get_process_frames()
		_clock += delta
		RenderingServer.global_shader_parameter_set(CLOCK, _clock)
	_time += delta
	if _away.is_empty():
		return
	var still: Array = []
	for one: Array in _away:
		var i: int = one[0]
		if _time < one[1]:
			still.append(one)
			continue
		if one[2] == 0:
			# (it comes back somewhere else in the cloud)
			one[2] = 1
			_places[i] = _somewhere()
			_many.set_instance_transform(i, Transform3D(Basis.IDENTITY, _places[i]))
		var grown := clampf((_time - float(one[1])) / maxf(grow_in, 0.01), 0.0, 1.0)
		_missing -= grown - _custom[i].b
		_custom[i].b = grown
		_many.set_instance_custom_data(i, _custom[i])
		if grown < 1.0:
			still.append(one)
	_away = still
	if _away.is_empty():
		_missing = 0.0


func _somewhere() -> Vector3:
	# (a point in the ball, more of them towards its middle)
	var way := Vector3(_rng.randfn(), _rng.randfn(), _rng.randfn()).normalized()
	return _centre + way * _radius * pow(_rng.randf(), 0.6)


func _pick_kind() -> int:
	var total := maxf(mix.x + mix.y + mix.z + mix.w, 0.0001)
	var r := _rng.randf() * total
	for k in 4:
		r -= mix[k]
		if r <= 0.0:
			return k
	return 3


func _box() -> void:
	if _many == null:
		return
	var grow := _radius + drift + SPECK * speck_size * 1.3
	_many.custom_aabb = AABB(_centre - Vector3.ONE * grow, Vector3.ONE * grow * 2.0)


func _send(setting: StringName, value: Variant) -> void:
	if _material != null:
		_material.set_shader_parameter(setting, value)
