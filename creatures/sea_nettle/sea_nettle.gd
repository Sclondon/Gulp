class_name SeaNettle
extends Node3D
## A sea nettle (Chrysaora fuscescens), huge, that drifts through the air: a
## peach and amber bell 1.8 m across, marked with rust, that folds shut and open
## as it beats; four bushy, deeply ruffled oral arms about 4.2 m long and
## twenty-four hair-fine maroon tentacles about 5 m, three to each eighth of its
## rim, hanging under it and dragged along behind it as it goes.
## Translucent; a faint glow at night (`glow`).
##
## Its arms and tentacles are ropes (the user, 2026-11-17: "the sea nettle tendrils
## need to be ropes and the nettle part as well"): each of the twenty-eight is a
## chain of points simulated here, in the world, hung from the bell. So they are
## dragged after it however it is moved, turned or beaten, lag behind and swing
## through; and they are heavy (much drag, no flicking: `rope_drag`, `rope_hold`,
## `rope_sink`). After GameCommon's rope (godot/rope) and Moon Jellies' moon
## jelly: Verlet points on the CPU, sent to the vertex shader, which lays the
## still mesh along a smooth curve through them.
##
## How it looks and moves only: whatever moves it puts it where it is each frame
## (the origin is the middle of its bell's rim) and calls `step(velocity, delta)`;
## `touches(a, b, radius)` says whether anything between two points is in its
## strands (a sting), and `sting(at)` crackles. After putting it somewhere new
## all at once, `lay_ropes()` hangs its strands afresh there (a jump of more than
## two of its own metres in one step does so by itself, and so does its being seen
## again after being hidden).
##
## The model is creatures/sea_nettle/models/sea_nettle.glb (and _lo), built by
## tools/build_sea_nettle.py; its shader (sea_nettle.gdshader) folds the bell and
## lays the strands along their ropes; `strand_point` reads the same ropes, for
## stinging.

const MODEL := "res://creatures/sea_nettle/models/sea_nettle%s.glb"
const SHADER := preload("res://creatures/sea_nettle/sea_nettle.gdshader")
## As the model is built (tools/build_sea_nettle.py): keep them in step.
const RADIUS := 0.9
const ARMS := 4
const ARM_LONG := 4.2
const TENTACLE_LONG := 5.0
const GROUPS := 8
const LAPPETS := 32
## The fold of the bell as it beats, as the shader has it (SWING, LAG, HINGE there): how far
## the rim swings in and down (radians), how much later the beat reaches the rim than the middle (a share
## of a beat), and the ring it folds about (how far from its axis, how high).
const SWING := 0.35
const LAG := 0.15
const HINGE := Vector2(0.18, 0.66)
## The ropes, as the shader has them (ARM_POINTS, TENTACLE_POINTS there): how many points an
## oral arm's has and a tentacle's, and how wide the picture is that carries them to the shader
## (a row a strand).
const ARM_POINTS := 12
const TENTACLE_POINTS := 9
const ROPE_ROW := 12
## The model's surfaces in the order they are drawn (jelly is clear, so what is behind goes
## first): the far wall of the bell, its underside, the arms and tentacles, its near wall.
const SURFACES: Array[String] = ["nettle_far", "nettle_under", "nettle_strands", "nettle_near"]
## How far from a strand's middle it stings (metres, at size 1): an oral arm is
## a broad frilled curtain, a tentacle a fine line.
const ARM_REACH := 0.32
const TENTACLE_REACH := 0.1

## Seconds a beat of its bell takes, drifting and hunting (it beats faster after someone).
@export var beat := 1.7
@export var beat_hunting := 1.05
## How far out past its resting shape the bell opens between beats, as a share of its swing in:
## 0.3 a dome that eases a little, 1.5 and it opens right out into a shallow saucer.
@export var open := 0.3
## How far its rim swings in and down as it beats (radians; SWING, the usual, is a gentle fold: the diorama
## makes it deeper).
@export var swing := SWING
## How much its strands are stirred about as they hang, for 1 as it drifts in the open (less,
## and its arms keep together in one plume). The stirring comes round with each beat.
@export var wander := 1.0
## How many bends the stirring puts along a strand, for 1 as it drifts (more: they wave rather than sway).
@export var stir_waves := 1.0
## The ropes' weight. How much what they hang in slows them (/s: the more, the less they flick
## and the further they are left behind); how strongly each is drawn back to hang straight out
## under the bell (/s², all of it at the root, a tenth of it at the tip); how fast they sink
## (m/s², straight down in the world whichever way up it is).
@export var rope_drag := 5.0
@export var rope_hold := 22.0
@export var rope_sink := 0.15
## Full detail within this of the camera; the low model further off.
@export var detail_range := 28.0
@export var volume_db := -6.0
## After someone (it beats faster), and how much it glows (0 by day, 1 at night).
var hunting := false
var glow := 0.0
## How far through a beat its bell is drawn in now (0..1), and the push of the beat (for its mover).
var pulse := 0.0
var thrust := 0.0

var _full: MeshInstance3D
var _low: MeshInstance3D
var _materials: Array[ShaderMaterial] = []
var _beat_at := 0.0
var _trail := Vector3.ZERO
var _moving := Vector3.ZERO
var _flash := 0.0
var _voice: AudioStreamPlayer3D
# The ropes: every strand's points one after another (world), where each was a step ago, where
# each strand's first point is in those, and the picture that carries them to the shader.
var _ropes := PackedVector3Array()
var _ropes_before := PackedVector3Array()
var _rope_from := PackedInt32Array()
var _rope_data := PackedFloat32Array()
var _rope_picture: ImageTexture
var _laid := false
var _was_at := Vector3.ZERO

static var _strands := []


func _ready() -> void:
	_beat_at = randf()
	for at in SURFACES.size():
		var material := ShaderMaterial.new()
		material.shader = SHADER
		material.render_priority = at - 2
		_materials.append(material)
	_full = _mesh_of("")
	_low = _mesh_of("_lo")
	_low.visible = false
	if DisplayServer.get_name() != "headless":
		_voice = AudioStreamPlayer3D.new()
		_voice.volume_db = volume_db
		_voice.unit_size = 5.0
		_voice.max_distance = 35.0
		add_child(_voice)


func _mesh_of(suffix: String) -> MeshInstance3D:
	var scene := load(MODEL % suffix) as PackedScene
	var made := scene.instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := MeshInstance3D.new()
	mesh.mesh = found.mesh
	for surface in mesh.mesh.get_surface_count():
		var named := mesh.mesh.surface_get_material(surface)
		var at := SURFACES.find(named.resource_name if named else "")
		mesh.set_surface_override_material(surface, _materials[at if at >= 0 else 2])
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# (its ropes may swing anywhere within their length of it)
	mesh.extra_cull_margin = TENTACLE_LONG * 1.2
	mesh.name = "Jelly" + suffix
	made.free()
	add_child(mesh)
	return mesh


## Each frame, after putting it where it is. Its ropes follow however it has been moved and
## turned since the last step. `velocity` (world, m/s) is how fast it is going through what it
## hangs in: where that is more than it has really moved (a nettle held still in a picture, in
## water that runs past it), the ropes are carried off by the difference; give Vector3.ZERO when
## there is nothing to add.
func step(velocity: Vector3, delta: float) -> void:
	delta = minf(delta, 0.05)
	_moving = _moving.lerp(velocity, 1.0 - exp(-1.6 * delta))
	# (the bell leans a little into the way it goes)
	var back := -(global_basis.orthonormalized().inverse() * _moving) * 0.32 / maxf(scale.x, 0.01)
	_trail = _trail.lerp(back.limit_length(0.85), 1.0 - exp(-2.2 * delta))
	var period := beat_hunting if hunting else beat
	var was := _beat_at
	_beat_at = fposmod(_beat_at + delta / period, 1.0)
	if _beat_at < was:
		_beat()
	# (drawn in quickly, let go slowly)
	pulse = smoothstep(0.0, 0.22, _beat_at) * (1.0 - smoothstep(0.28, 1.0, _beat_at))
	thrust = maxf(thrust - delta * 2.5, 0.0)
	_flash = maxf(_flash - delta * 3.0, 0.0)
	set_shader_parameter(&"beat", _beat_at)
	set_shader_parameter(&"open", open)
	set_shader_parameter(&"swing", swing)
	set_shader_parameter(&"trail", _trail)
	set_shader_parameter(&"glow", maxf(glow, _flash))
	if is_inside_tree():
		if not is_visible_in_tree():
			# (unseen, its ropes are not worked out: they are hung afresh when it is next seen)
			_laid = false
		elif not _laid or global_position.distance_to(_was_at) > 2.0 * _size():
			lay_ropes()
		elif delta > 0.0:
			_swing_ropes(velocity, delta)
			_send_ropes()
	var camera := get_viewport().get_camera_3d() if is_inside_tree() else null
	if camera:
		var near := camera.global_position.distance_to(global_position) < detail_range
		_full.visible = near
		_low.visible = not near


## Sets one of the shader's settings (its colours, say: `amber`, `peach`, `rust`, `under`, `frill`,
## `frill_pale`, `maroon`; how clear it is: `bell_alpha`, `under_alpha`, `membrane_alpha`,
## `ruffle_alpha`; how thick its tentacles are: `tentacle_width`) on every part of it.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	for material in _materials:
		material.set_shader_parameter(setting, value)


func _beat() -> void:
	thrust = 1.0
	if _voice and is_inside_tree():
		_voice.stream = SeaNettleSound.pulse()
		_voice.pitch_scale = randf_range(0.85, 1.1)
		_voice.volume_db = volume_db - (6.0 if not hunting else 2.0)
		_voice.play()


## It stings: its strands crackle and flash.
func sting(_at: Vector3) -> void:
	_flash = 1.0
	if _voice and is_inside_tree():
		_voice.stream = SeaNettleSound.sting()
		_voice.pitch_scale = randf_range(0.9, 1.15)
		_voice.volume_db = volume_db + 2.0
		_voice.play()


## Its strands as built: [root (its own space), length, phase 0..1, an arm or not, which strand],
## arms first.
static func strands() -> Array:
	var all := []
	for k in ARMS:
		var a := PI * 0.25 + k * PI * 0.5
		all.append([Vector3(cos(a) * 0.12, -0.05, sin(a) * 0.12), ARM_LONG * (1.0 + 0.1 * sin(k * 2.1 + 0.4)), fposmod(k * 0.37 + 0.11, 1.0), true, k])
	for i in GROUPS * 3:
		var g := i / 3
		var j := i % 3
		var a := g * TAU / GROUPS + PI / GROUPS + (j - 1) * TAU / LAPPETS
		all.append([Vector3(cos(a) * RADIUS * 0.96, 0.02, sin(a) * RADIUS * 0.96), TENTACLE_LONG * (1.0 + 0.12 * sin(i * 2.3 + 1.0)), fposmod(i * 0.618, 1.0), false, ARMS + i])
	return all


static func _all() -> Array:
	if _strands.is_empty():
		_strands = strands()
	return _strands


## Where `s` (0 root .. 1 tip) along strand `strand` (of `strands()`) is now, in the world: on
## its rope, on the same curve the shader lays it along.
func strand_point(strand: Array, s: float) -> Vector3:
	if not _laid:
		lay_ropes()
	var k: int = strand[4] if strand.size() > 4 else _all().find(strand)
	var count := ARM_POINTS if strand[3] else TENTACLE_POINTS
	var base := _rope_from[k]
	var f := clampf(s, 0.0, 1.0) * (count - 1)
	var i := mini(int(f), count - 2)
	var t := f - i
	var p0 := _ropes[base + maxi(i - 1, 0)]
	var p1 := _ropes[base + i]
	var p2 := _ropes[base + i + 1]
	var p3 := _ropes[base + mini(i + 2, count - 1)]
	return 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * (p1 - p2) + p3 - p0) * t * t * t)


## How far the bell is drawn in, through a beat (0..1): quickly in, slowly let go.
static func _squeeze(x: float) -> float:
	x = fposmod(x, 1.0)
	return smoothstep(0.0, 0.22, x) * (1.0 - smoothstep(0.28, 1.0, x))


## How far a point of the bell `reach` from its axis is turned in and down now (the shader's
## `fold_turn`).
func _fold_turn(reach: float) -> float:
	var rim := smoothstep(HINGE.x, RADIUS, reach)
	return swing * (_squeeze(_beat_at - LAG * rim) * (1.0 + open) - open) * rim


## Where a point of the bell at rest (its own space) is now, as the beat has folded it (the
## shader's `fold`): a strand hangs from there.
func _fold(p: Vector3) -> Vector3:
	var reach := Vector2(p.x, p.z).length()
	var turn := _fold_turn(reach)
	var arm := Vector2(reach, p.y) - HINGE
	var swung := Vector2(arm.x * cos(turn) + arm.y * sin(turn), arm.y * cos(turn) - arm.x * sin(turn))
	var by := (HINGE.x + swung.x) / maxf(reach, 0.0001)
	return Vector3(p.x * by, HINGE.y + swung.y, p.z * by)


func _size() -> float:
	return maxf(global_basis.get_scale().x, 0.0001)


## Where a strand's rope is hung (world), and the way it leaves the bell (world, a unit): an
## arm straight out under the bell; a tentacle the way the rim points, swung in as the bell
## closes and out as it opens (further along, every strand's rest is straight out under the bell).
func _rope_root(strand: Array) -> Vector3:
	return global_transform * _fold(strand[0] as Vector3)


func _rope_way(strand: Array) -> Vector3:
	var root: Vector3 = strand[0]
	var way := Vector3.DOWN
	if not strand[3]:
		var turn := 0.5 * _fold_turn(Vector2(root.x, root.z).length())
		way = Vector3.DOWN * cos(turn) - Vector3(root.x, 0.0, root.z).normalized() * sin(turn)
	return global_basis.orthonormalized() * way


## Hangs every strand afresh, straight out from the bell where it is now (after putting it
## somewhere new all at once: its ropes would otherwise be dragged there from where it was).
func lay_ropes() -> void:
	var all := _all()
	if _rope_from.is_empty():
		var total := 0
		for strand: Array in all:
			_rope_from.append(total)
			total += ARM_POINTS if strand[3] else TENTACLE_POINTS
		_ropes.resize(total)
		_ropes_before.resize(total)
		_rope_data.resize(ROPE_ROW * all.size() * 4)
	var size := _size()
	for k in all.size():
		var strand: Array = all[k]
		var count := ARM_POINTS if strand[3] else TENTACLE_POINTS
		var root := _rope_root(strand)
		var way := _rope_way(strand)
		var piece: float = float(strand[1]) * size / (count - 1)
		var down := global_basis.orthonormalized() * Vector3.DOWN
		var rest := root
		for i in count:
			if i > 0:
				rest += way.lerp(down, smoothstep(0.0, 0.4, float(i) / (count - 1))).normalized() * piece
			_ropes[_rope_from[k] + i] = rest
			_ropes_before[_rope_from[k] + i] = rest
	_laid = true
	_was_at = global_position
	_send_ropes()


## A step of the ropes (Verlet): each point keeps going as it was, slowed by what it hangs in,
## drawn back towards hanging straight out from the bell (strongly near its root, hardly at its
## tip), stirred a little, sinking; then each rope is held to its length from its root down.
## What it hangs in stands still in the world, but for `velocity` more than the nettle has
## really moved: that much runs past it the other way and carries the ropes with it.
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
	var down := turned * Vector3.DOWN
	var beat_angle := _beat_at * TAU
	var sink := Vector3.DOWN * rope_sink * size * delta * delta
	for k in all.size():
		var strand: Array = all[k]
		var count := ARM_POINTS if strand[3] else TENTACLE_POINTS
		var base := _rope_from[k]
		var root := _rope_root(strand)
		var way := _rope_way(strand)
		var piece: float = float(strand[1]) * size / (count - 1)
		var phase: float = float(strand[2]) * TAU
		_ropes[base] = root
		_ropes_before[base] = root
		var rest := root
		for i in range(1, count):
			var p := _ropes[base + i]
			var share := float(i) / (count - 1)
			var held := 1.0 - 0.9 * smoothstep(0.0, 0.9, share)
			# (its rest: the way it leaves the bell, easing to straight out under it by two fifths along)
			rest += way.lerp(down, smoothstep(0.0, 0.4, share)).normalized() * piece
			var pull := (rest - p) * rope_hold * held
			# (stirred: a slow round that comes back with each beat, each strand at its own time)
			var stir := turned * Vector3(sin(beat_angle + phase + share * 4.0 * stir_waves), 0.0, cos(beat_angle + phase * 1.7 + share * 3.0 * stir_waves)) * 0.3 * wander * size * share
			var moved := (p - _ropes_before[base + i]) * keep + carried + (pull + stir) * delta * delta + sink
			_ropes_before[base + i] = p
			_ropes[base + i] = p + moved
		# held to length, from the root down (three times over, so that it settles)
		for again in 3:
			for i in range(1, count):
				var from := _ropes[base + i - 1]
				var to := _ropes[base + i] - from
				var long := to.length()
				if long > 0.00001:
					_ropes[base + i] = from + to * (piece / long)


## The ropes to the shader: a picture, a row a strand, each point in the nettle's own space.
func _send_ropes() -> void:
	var to_local := global_transform.affine_inverse()
	var all := _all()
	for k in all.size():
		var count := ARM_POINTS if all[k][3] else TENTACLE_POINTS
		var base := _rope_from[k]
		var at := k * ROPE_ROW * 4
		for i in count:
			var p := to_local * _ropes[base + i]
			_rope_data[at] = p.x
			_rope_data[at + 1] = p.y
			_rope_data[at + 2] = p.z
			at += 4
	var image := Image.create_from_data(ROPE_ROW, all.size(), false, Image.FORMAT_RGBAF, _rope_data.to_byte_array())
	if _rope_picture == null:
		_rope_picture = ImageTexture.create_from_image(image)
		set_shader_parameter(&"ropes", _rope_picture)
	else:
		_rope_picture.update(image)


## Whether anything on the line from `a` to `b` (world) is within its strands' sting,
## `radius` more (a player's body: feet to head, and how thick).
func touches(a: Vector3, b: Vector3, radius := 0.25) -> bool:
	var size := _size()
	for strand: Array in _all():
		var reach: float = (ARM_REACH if strand[3] else TENTACLE_REACH) * size + radius
		var last := strand_point(strand, 0.0)
		for k in range(1, 6):
			var here := strand_point(strand, k / 5.0)
			if _segments_near(a, b, last, here, reach):
				return true
			last = here
	return false


## How low its lowest strand hangs now, under its origin (metres, world).
func lowest() -> float:
	var low := INF
	for strand: Array in _all():
		low = minf(low, strand_point(strand, 1.0).y)
	return global_position.y - low


static func _segments_near(a: Vector3, b: Vector3, c: Vector3, d: Vector3, reach: float) -> bool:
	var pair := Geometry3D.get_closest_points_between_segments(a, b, c, d)
	return pair[0].distance_to(pair[1]) < reach
