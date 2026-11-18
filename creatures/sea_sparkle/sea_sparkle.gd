class_name SeaSparkle
extends Node3D
## A cloud of sea sparkle (Noctiluca scintillans), cheap in the thousands: tiny glowing specks, each one clear round
## cell with a short tentacle, drawn by one MultiMesh, tumbling slowly and drifting about their places, glowing dimly
## until something moves through them: then the specks round it flash bright blue and fade over a second or two.
## All of the moving and the glowing is in sea_sparkle.gdshader; the CPU only marks the specks that are stirred.
##
##   var sparkle := SeaSparkle.new()
##   add_child(sparkle)
##   sparkle.fill(Vector3(0, -40, 0), 4.0, 3000)       # 3000 specks in a ball 4 m in radius (the cloud's own space)
##   # each frame something swims through it:
##   sparkle.stir(fish.global_position, 0.5)            # the specks within 0.5 m of it flash
##
## The cloud keeps a clock of its own (`clock`, which runs from 0 to PERIOD seconds and starts again, so that the
## numbers handed to the shader stay small enough to be kept exactly in a MultiMesh's custom data). Each speck's
## custom data holds when it was last stirred and how hard. No sound.

const MODEL := "res://creatures/sea_sparkle/models/sea_sparkle_speck%s.glb"
const SHADER := "res://creatures/sea_sparkle/sea_sparkle.gdshader"
## How wide a speck is as built (metres; `speck_size` scales it), and how many triangles each of the two specks has.
const SPECK := 0.004
const TRIANGLES := 83
const TRIANGLES_LOW := 20
## The clock's round (seconds): as the shader has it.
const PERIOD := 64.0
## (a stirred-time long before any clock: never stirred)
const NEVER := -1000.0

## How big the specks are: 1 as built (4 mm across: bigger than life, a real one is about 1 mm).
@export_range(0.1, 20.0) var speck_size := 1.0:
	set(value):
		speck_size = value
		_send(&"speck_size", value)
		_box()
## How far each speck drifts about its place (metres).
@export_range(0.0, 3.0) var drift := 0.15:
	set(value):
		drift = value
		_send(&"drift", value)
		_box()
## How fast the specks tumble (turns a second, about).
@export_range(0.0, 2.0) var spin := 0.1:
	set(value):
		spin = value
		_send(&"spin", value)
## How long a flash takes to fade (seconds).
@export_range(0.1, 10.0) var fade := 1.4:
	set(value):
		fade = value
		_send(&"fade", value)
## How brightly the specks glow, at rest and when stirred (0 none, 1 as made, 2 twice as bright).
@export_range(0.0, 2.0) var glow := 1.0:
	set(value):
		glow = clampf(value, 0.0, 2.0)
		_send(&"glow", glow)
## The lighter speck (20 triangles, no tentacle, in place of 83), for a cloud far off or a very big one. Set it
## before `fill`.
@export var low := false
## Changes where the specks are.
@export var seed := 1

## The cloud's own clock (seconds, 0 to PERIOD, then round again). Read only.
var clock: float:
	get:
		return _clock

static var _meshes := {}
static var _shader: Shader

var _material: ShaderMaterial
var _view: MultiMeshInstance3D
var _many: MultiMesh
var _rng := RandomNumberGenerator.new()
var _centre := Vector3.ZERO
var _radius := 0.0
var _count := 0
var _places := PackedVector3Array()
var _custom: Array[Color] = []
## The specks stirred since the clock last came round: their numbers.
var _lit := {}
var _clock := 0.0


## A speck's mesh (the 83-triangle one, or with `low_wanted` the 20-triangle one), at the origin: for a game drawing
## its own MultiMesh (with `new_material()`; see the top of the shader for the custom data it reads).
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## A new material wearing sea_sparkle.gdshader (the top of the shader lists its settings; set `clock` each frame).
static func new_material() -> ShaderMaterial:
	if _shader == null:
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


## Fills the cloud (taking up whatever was in it before): `count` specks scattered through a ball `radius` metres
## round `centre` (in this node's own space), thicker towards its middle, none of them stirred.
func fill(centre: Vector3, radius: float, count: int) -> void:
	_rng.seed = seed
	_centre = centre
	_radius = maxf(radius, 0.01)
	_count = maxi(count, 0)
	_lit.clear()
	_places.resize(_count)
	_custom.resize(_count)
	_many.instance_count = 0
	_many.mesh = mesh_of(low)
	_many.instance_count = _count
	for i in _count:
		var way := Vector3(_rng.randfn(), _rng.randfn(), _rng.randfn()).normalized()
		_places[i] = _centre + way * _radius * pow(_rng.randf(), 0.6)
		_custom[i] = Color(_rng.randf(), NEVER, 0.0, _rng.randf_range(0.7, 1.3))
		_many.set_instance_transform(i, Transform3D(Basis.IDENTITY, _places[i]))
		_many.set_instance_custom_data(i, _custom[i])
	for setting in [&"speck_size", &"drift", &"spin", &"fade", &"glow"]:
		_send(setting, get(setting))
	_box()


## Something moved through the water here: every speck within `radius` metres of `at` (a place in the world) flashes,
## the nearest hardest, and fades over `fade` seconds. Returns how many flashed. (Measured from where each speck's
## drift is centred: it may be up to `drift` off that.) A speck already flashing is lit again, as hard as it is now
## stirred or harder. It is a loop over all the specks (skipped at once when the stir is outside the cloud's ball).
func stir(at: Vector3, radius: float) -> int:
	if _count == 0:
		return 0
	var here := to_local(at)
	var reach := radius / maxf(global_basis.get_scale().x, 0.0001)
	if here.distance_to(_centre) > _radius + reach:
		return 0
	var limit := reach * reach
	var lit := 0
	for i in _count:
		var d := _places[i].distance_squared_to(here)
		if d > limit:
			continue
		var hard := 1.0 - 0.5 * sqrt(d) / maxf(reach, 0.0001)
		var age := _clock - _custom[i].g
		var now := _custom[i].b * exp(-age * 3.0 / fade) if age >= 0.0 and age < fade * 4.0 else 0.0
		_custom[i].g = _clock
		_custom[i].b = clampf(maxf(hard, now), 0.0, 1.0)
		_many.set_instance_custom_data(i, _custom[i])
		_lit[i] = true
		lit += 1
	return lit


## How many specks the cloud has, how many were stirred since its clock last came round, and how many triangles one
## draw of it sends.
func counts() -> Dictionary:
	return {"specks": _count, "stirred": _lit.size(), "triangles": _count * (TRIANGLES_LOW if low else TRIANGLES)}


## Sets one of the shader's settings (`rest_glow`, `flash_glow`, and the colours `cell`, `rest_colour`,
## `flash_colour`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


func material() -> ShaderMaterial:
	return _material


func _process(delta: float) -> void:
	_clock += delta
	if _clock >= PERIOD:
		_clock -= PERIOD
		# (the clock came round: what was stirred is now a PERIOD further back; what is long dark is never stirred)
		var still := {}
		for i: int in _lit:
			_custom[i].g -= PERIOD
			if _clock - _custom[i].g > fade * 4.0:
				_custom[i].g = NEVER
				_custom[i].b = 0.0
			else:
				still[i] = true
			_many.set_instance_custom_data(i, _custom[i])
		_lit = still
	_send(&"clock", _clock)


func _box() -> void:
	if _many == null:
		return
	var grow := _radius + drift + SPECK * speck_size * 1.5
	_many.custom_aabb = AABB(_centre - Vector3.ONE * grow, Vector3.ONE * grow * 2.0)


func _send(setting: StringName, value: Variant) -> void:
	if _material != null:
		_material.set_shader_parameter(setting, value)
