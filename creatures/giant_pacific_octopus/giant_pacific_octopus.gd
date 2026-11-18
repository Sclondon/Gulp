class_name GiantPacificOctopus
extends Node3D
## A giant Pacific octopus (Enteroctopus dofleini): a baggy, wrinkled mantle with papillae on it,
## a head with an eye raised on each side (a gold eye with a level slit of a pupil), the siphon
## out from under the mantle's collar, and eight thick tapering arms joined by a web, each with
## two rows of pale suckers. Brick red to rusty brown with paler mottling. About 1.0 m from the
## mantle's tip to the web's edge, its arms 1.6 m: about 2.3 m in all at `scale` 1.
##
## It swims mantle first, towards its own -Z, by jets: its arms trail behind it, towards +Z, in
## a streamlined bundle. Its back is +Y. The origin is the middle of its head, between its eyes
## (not half way along: its arms are ropes and have no fixed length behind it). From the origin
## the mantle's tip is 0.58 m ahead (-Z), the arms' tips about 1.75 m behind (+Z) when trailing.
##
## Its arms are ropes, exactly as the squids' are (GameCommon's godot/humboldt-squid and
## godot/giant-squid; godot/sea-nettle's README, "Decision: ropes", says why): each of the eight
## is a chain of points simulated here, in the world, hung from the head, and the shader lays the
## arm (and the web between it and the next) along it. `sit` (0..1) moves the arms' rest from
## the trailing bundle to spread out round it and curled at their tips, as on the ground: for
## that, turn it so that its -Z points up (its mantle above its arms) and its arms' crown faces
## the ground; the arms then spread in its own XY plane and sink onto the ground's level by
## their weight. Nothing here knows where the ground is: the ropes do not collide.
##
## How it looks and moves only: whatever moves it puts it where it is each frame and calls
## `step(velocity, delta)`. After putting it somewhere new all at once, `lay_ropes()` hangs its
## arms afresh there (a jump of more than two of its own lengths of mantle in one step does so by
## itself, and so does its being seen again after being hidden).
##
## Nothing in it runs on a clock that only grows: the jet and the stirring of the arms go by
## `phase`. `step` moves `phase` on by delta / beat (set `beat` to 0 and `phase` yourself).
##
## The model is creatures/giant_pacific_octopus/models/giant_pacific_octopus.glb (and _lo, and
## _game: `game`), built
## by tools/build_giant_pacific_octopus.py; giant_pacific_octopus.gdshader pulses the mantle,
## lays the arms and the web along the ropes and draws the skin.

const MODEL := "res://creatures/giant_pacific_octopus/models/giant_pacific_octopus%s.glb"
const SHADER := preload("res://creatures/giant_pacific_octopus/giant_pacific_octopus.gdshader")
## As the model is built (tools/build_giant_pacific_octopus.py): the mantle's tip to the web's
## edge, how deep and how wide the mantle is at its widest (metres, at scale 1).
const LENGTH := 1.03
const DEPTH := 0.42
const WIDTH := 0.4
## As the model is built and the shader has them: keep them in step.
const MANTLE_FROM := -0.03
const MANTLE_LONG := 0.55
const ARMS := 8
const ARM_RING := 0.09
const ARM_Z := 0.13
const ARM_LONG := 1.6
## How far down the arms the web reaches between them (a share of an arm).
const WEB := 0.2
## Points in each arm's rope (which is also how wide the picture is that carries them to the shader).
const ARM_POINTS := 14
## The share of a jet spent breathing in (the rest is the squeeze), as the shader has it.
const SQUEEZE_AT := 0.6

## Seconds a jet takes (a slow breath in, a quicker squeeze). 0: `phase` is yours to set.
@export var beat := 2.4
## 0 swimming, its arms trailing in a bundle; 1 settled, its arms spread round it and curled at
## their tips (see above for which way to turn it).
@export_range(0.0, 1.0) var sit := 0.0
## How flushed it is: 0 its calm brick red and rust with paler mottling, 1 dark red all over
## (roused). Its mottling fades as it darkens.
@export_range(0.0, 1.0) var blush := 0.0
## How wide the bundle of trailing arms is (the tangent of the half angle at their roots).
@export var cone := 0.07
## How much the arms are stirred about as they trail or lie, for 1 as in open water. The stirring
## comes round with each jet.
@export var wander := 1.0
## The ropes' weight: how much the water slows them (/s), how strongly each is drawn back to its
## rest (/s², all of it at the root, a tenth of it at the tip), how fast they sink (m/s², straight
## down in the world).
@export var rope_drag := 4.0
@export var rope_hold := 22.0
@export var rope_sink := 0.25
## Full detail within this of the camera; the low model (no suckers, no papillae) further off.
@export var detail_range := 14.0
## The low model always, wherever the camera is (for many of them, or far off).
@export var low := false
## The game model (about 4,500 triangles, its suckers painted by the shader) near, in place of the
## full one (52,900); the low one still far off. With it the full model is never loaded: each model
## is loaded only when it is first shown.
@export var game := false:
	set(value):
		game = value
		if not _models.is_empty():
			_show(not _models.has("_lo") or not (_models["_lo"] as MeshInstance3D).visible)
## Cartoon eyes (0 its own gold eye with the level slit, 1 the cartoon eye: bigger, a cream white,
## a gold iris, a level bar of a pupil, a highlight, a dark outline, and a heavy, knowing upper lid).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_material.set_shader_parameter(&"cartoon_eyes", value)
## Where its eyes look (-1..1 each way, in each eye's own plane): x towards its arms (+1) or its
## mantle (-1), y up its back. Both eyes look the same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_material.set_shader_parameter(&"eye_look", value)
## Its eyes' lids: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_material.set_shader_parameter(&"blink", value)
## A round tank it is kept inside (as the squids'): its radius (world metres; 0 none) about the
## upright line through `tank_at`. Its arms are put back inside the wall.
var tank := 0.0
var tank_at := Vector3.ZERO
## How far through a jet it is (0..1): it breathes in until SQUEEZE_AT, then squeezes.
var phase := 0.0
## How full of water its mantle is now (0..1), and the push of the squeeze (1 as it starts,
## falling away), for its mover.
var fullness := 0.0
var thrust := 0.0

var _material: ShaderMaterial
# Its models, by suffix ("", "_game", "_lo"), each made when it is first shown.
var _models := {}
var _flash_at := 1.0
var _flash_takes := 0.6
var _ropes := PackedVector3Array()
var _ropes_before := PackedVector3Array()
var _rope_data := PackedFloat32Array()
var _rope_picture: ImageTexture
var _laid := false
var _was_at := Vector3.ZERO

static var _strands := []
static var _game_cache: Mesh


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	# (put off to the end of the frame, so that `game` or `low` set just after it is added is heeded
	# before any model is loaded)
	_first_show.call_deferred()


func _first_show() -> void:
	if _models.is_empty():
		_show(true)


## The model's mesh (the full one, or the low one), as imported.
static func mesh_of(low_model := false) -> Mesh:
	return _load_mesh("_lo" if low_model else "")


## The game model's mesh, as imported, without the thinned LOD meshes Godot's importer makes (its
## arms are bent in the shader: a thinned one would bend in straight pieces).
static func game_mesh() -> Mesh:
	return _load_mesh("_game")


static func _load_mesh(suffix: String) -> Mesh:
	if suffix == "_game" and _game_cache != null:
		return _game_cache
	var scene := load(MODEL % suffix) as PackedScene
	var made := scene.instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := found.mesh
	made.free()
	if suffix == "_game":
		# (made once, shared by every octopus)
		if _game_cache == null:
			_game_cache = _without_lods(mesh)
		mesh = _game_cache
	return mesh


## `mesh` built again from its own arrays, without its LOD meshes.
static func _without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
		plain.surface_set_material(surface, mesh.surface_get_material(surface))
	return plain


## A new material of its shader (each octopus needs its own: its arms' ropes are in it).
static func new_material() -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = SHADER
	return material


func _instance(mesh: Mesh, suffix: String) -> MeshInstance3D:
	var made := MeshInstance3D.new()
	made.mesh = mesh
	made.material_override = _material
	# (its arms may swing anywhere within their length of it)
	made.extra_cull_margin = ARM_LONG * 1.15
	made.name = "Octopus" + suffix
	add_child(made)
	return made


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


## Sets one of the shader's settings (its colours: `skin`, `rust`, `dark`, `pale`, `under`,
## `sucker`, `iris`; `mottle`, how strongly the paler mottling shows) on it.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## How full the mantle is at `x` through a jet (0..1): filling slowly, emptied quickly (the
## shader's `fullness`).
static func fullness_at(x: float) -> float:
	x = fposmod(x, 1.0)
	var through := 0.5 * x / SQUEEZE_AT if x < SQUEEZE_AT else 0.5 + 0.5 * (x - SQUEEZE_AT) / (1.0 - SQUEEZE_AT)
	return 0.5 - 0.5 * cos(through * TAU)


## A flash, once, now: it blanches pale all over and colours again over `seconds` (as one does
## when startled). Not part of `phase`: a picture that must loop should not call it.
func flash(seconds := 0.6) -> void:
	_flash_at = 0.0
	_flash_takes = maxf(seconds, 0.01)


## Each frame, after putting it where it is. Its ropes follow however it has been moved and
## turned since the last step. `velocity` (world, m/s) is how fast it is going through the water:
## where that is more than it has really moved (one held still in a picture, in water that runs
## past it), the ropes are carried off by the difference; give Vector3.ZERO when there is nothing
## to add.
func step(velocity: Vector3, delta: float) -> void:
	delta = minf(delta, 0.05)
	if beat > 0.0:
		var was := phase
		phase = fposmod(phase + delta / beat, 1.0)
		if was < SQUEEZE_AT and phase >= SQUEEZE_AT:
			thrust = 1.0
	fullness = fullness_at(phase)
	thrust = maxf(thrust - delta * 2.0, 0.0)
	_flash_at = minf(_flash_at + delta / _flash_takes, 1.0)
	_material.set_shader_parameter(&"phase", phase)
	_material.set_shader_parameter(&"breathe", 1.0 - 0.6 * sit)
	_material.set_shader_parameter(&"blush", blush)
	_material.set_shader_parameter(&"flash_now", pow(sin(PI * sqrt(_flash_at)), 2.0) if _flash_at < 1.0 else 0.0)
	_material.set_shader_parameter(&"sit", sit)
	if is_inside_tree():
		if not is_visible_in_tree():
			# (unseen, its ropes are not worked out: they are hung afresh when it is next seen)
			_laid = false
		elif not _laid or global_position.distance_to(_was_at) > 2.0 * MANTLE_LONG * _size():
			lay_ropes()
		elif delta > 0.0:
			_swing_ropes(velocity, delta)
			_send_ropes()
	var near := not low
	var camera := get_viewport().get_camera_3d() if is_inside_tree() else null
	if camera and near:
		near = camera.global_position.distance_to(global_position) < detail_range * _size()
	_show(near)


## Shows the model it should wear (near: the full one, or the game one with `game`; else the low
## one), loading it the first time.
func _show(near: bool) -> void:
	var wear := "_lo" if low or not near else ("_game" if game else "")
	if not _models.has(wear):
		_models[wear] = _instance(_load_mesh(wear), wear)
	for suffix: String in _models:
		(_models[suffix] as MeshInstance3D).visible = suffix == wear


## Its arms as built: [root (its own space), length, phase 0..1, which arm, the way out from its
## middle it lies (its own space, a unit)]. Arm 0 is the upper one on its +X side, and they go
## round by way of its back.
static func strands() -> Array:
	var all := []
	for k in ARMS:
		var a := (k + 0.5) * TAU / ARMS
		var out := Vector3(cos(a), sin(a), 0.0)
		all.append([out * ARM_RING + Vector3(0.0, 0.0, ARM_Z), ARM_LONG * (1.0 - 0.05 * sin(a)), fposmod(k * 0.37 + 0.11, 1.0), k, out])
	return all


static func _all() -> Array:
	if _strands.is_empty():
		_strands = strands()
	return _strands


## Where `s` (0 root .. 1 tip) along arm `arm` (0..7) is now, in the world: on its rope, on the
## same curve the shader lays it along.
func arm_point(arm: int, s: float) -> Vector3:
	if not _laid:
		lay_ropes()
	var base := arm * ARM_POINTS
	var f := clampf(s, 0.0, 1.0) * (ARM_POINTS - 1)
	var i := mini(int(f), ARM_POINTS - 2)
	var t := f - i
	var p0 := _ropes[base + maxi(i - 1, 0)]
	var p1 := _ropes[base + i]
	var p2 := _ropes[base + i + 1]
	var p3 := _ropes[base + mini(i + 2, ARM_POINTS - 1)]
	return 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * (p1 - p2) + p3 - p0) * t * t * t)


func _size() -> float:
	return maxf(global_basis.get_scale().x, 0.0001)


## The way an arm's rest runs at `share` (0 root .. 1 tip) along it (its own space, a unit).
## Swimming: back along the bundle, a little open as the mantle fills and drawn in as it jets.
## Settled: out from the crown (first down towards the ground, +Z, then level), its last third
## curling round to one side.
func _rest_way(strand: Array, share: float) -> Vector3:
	var out: Vector3 = strand[4]
	var open := cone * (0.6 + 0.8 * fullness)
	var swim := (Vector3.BACK + out * open * (1.0 - 0.6 * smoothstep(0.0, 0.5, share))).normalized()
	if sit <= 0.0:
		return swim
	var side := Vector3(-out.y, out.x, 0.0)
	# (each arm curls its own way, some more than others)
	var own: float = strand[2]
	var turn := (2.4 + 1.6 * fposmod(own * 3.7, 1.0)) * smoothstep(0.55, 1.0, share) * (1.0 if own < 0.5 else -1.0)
	var flat := out * cos(turn) + side * sin(turn)
	var down := 0.9 * (1.0 - smoothstep(0.0, 0.18, share))
	var spread := (flat + Vector3.BACK * down).normalized()
	return swim.slerp(spread, sit) if sit < 1.0 else spread


## Hangs every arm afresh, at rest where it is now (after putting it somewhere new all at once:
## its ropes would otherwise be dragged there from where it was).
func lay_ropes() -> void:
	var all := _all()
	if _ropes.is_empty():
		_ropes.resize(ARMS * ARM_POINTS)
		_ropes_before.resize(ARMS * ARM_POINTS)
		_rope_data.resize(ARMS * ARM_POINTS * 4)
	var size := _size()
	var turned := global_basis.orthonormalized()
	for k in ARMS:
		var strand: Array = all[k]
		var piece: float = float(strand[1]) * size / (ARM_POINTS - 1)
		var rest := global_transform * (strand[0] as Vector3)
		for i in ARM_POINTS:
			if i > 0:
				rest += turned * _rest_way(strand, (i - 0.5) / (ARM_POINTS - 1)) * piece
			_ropes[k * ARM_POINTS + i] = rest
			_ropes_before[k * ARM_POINTS + i] = rest
	_laid = true
	_was_at = global_position
	_send_ropes()


## A step of the ropes (Verlet), as the squids': each point keeps going as it was, slowed by the
## water, drawn back towards its rest (strongly near its root, hardly at its tip), stirred a
## little, sinking; then each rope is held to its length from its root down.
func _swing_ropes(velocity: Vector3, delta: float) -> void:
	var all := _all()
	var size := _size()
	var keep := exp(-rope_drag * delta)
	var water := Vector3.ZERO
	if velocity != Vector3.ZERO:
		water = (global_position - _was_at) / delta - velocity
	_was_at = global_position
	var carried := water * delta * (1.0 - keep)
	var turned := global_basis.orthonormalized()
	var angle := phase * TAU
	var sink := Vector3.DOWN * rope_sink * size * delta * delta
	# (settled, the arms are held more firmly where they lie)
	var hold := rope_hold * (1.0 + 1.5 * sit)
	for k in ARMS:
		var strand: Array = all[k]
		var base := k * ARM_POINTS
		var long: float = float(strand[1]) * size
		var piece := long / (ARM_POINTS - 1)
		var own: float = float(strand[2]) * TAU
		var rest := global_transform * (strand[0] as Vector3)
		_ropes[base] = rest
		_ropes_before[base] = rest
		for i in range(1, ARM_POINTS):
			var p := _ropes[base + i]
			var share := float(i) / (ARM_POINTS - 1)
			var held := 1.0 - 0.9 * smoothstep(0.0, 0.9, share)
			rest += turned * _rest_way(strand, (i - 0.5) / (ARM_POINTS - 1)) * piece
			var pull := (rest - p) * hold * held
			# (stirred: a slow round that comes back with each jet, each arm at its own time; its
			# tip most, as a living one's tips are never still)
			var stir := turned * Vector3(sin(angle + own + share * 5.0), cos(angle + own * 1.7 + share * 4.0), sin(angle * 2.0 + own) * 0.5) * 0.1 * wander * long * share * share
			var moved := (p - _ropes_before[base + i]) * keep + carried + (pull + stir) * delta * delta + sink
			_ropes_before[base + i] = p
			_ropes[base + i] = p + moved
		for again in 3:
			for i in range(1, ARM_POINTS):
				var from := _ropes[base + i - 1]
				var to := _ropes[base + i] - from
				var gap := to.length()
				if gap > 0.00001:
					_ropes[base + i] = from + to * (piece / gap)
				_ropes[base + i] = _in_tank(_ropes[base + i])


func _in_tank(p: Vector3) -> Vector3:
	if tank <= 0.0:
		return p
	var out := Vector2(p.x - tank_at.x, p.z - tank_at.z)
	var far := out.length()
	if far <= tank:
		return p
	out *= tank / far
	return Vector3(tank_at.x + out.x, p.y, tank_at.z + out.y)


## The ropes to the shader: a picture, a row an arm, each point in the octopus's own space.
func _send_ropes() -> void:
	var to_local := global_transform.affine_inverse()
	var at := 0
	for k in ARMS:
		for i in ARM_POINTS:
			var p := to_local * _ropes[k * ARM_POINTS + i]
			_rope_data[at] = p.x
			_rope_data[at + 1] = p.y
			_rope_data[at + 2] = p.z
			at += 4
	var image := Image.create_from_data(ARM_POINTS, ARMS, false, Image.FORMAT_RGBAF, _rope_data.to_byte_array())
	if _rope_picture == null:
		_rope_picture = ImageTexture.create_from_image(image)
		_material.set_shader_parameter(&"ropes", _rope_picture)
	else:
		_rope_picture.update(image)
