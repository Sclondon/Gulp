class_name FriedEggJelly
extends Node3D
## A fried egg jelly (after Cotylorhiza tuberculata): a pale, flat, clear bell 0.4 m across, its rim cut in
## sixteen small scallops, with a raised yolk-yellow dome in its middle; under it eight short oral arms,
## each a frilly cream bunch with club-like stalks sticking out of it, their tips purple. Slow and harmless
## (`STINGS` is false: `touches` still says where its arms are, for bumping into it). A faint glow (`glow`).
##
## Its arms are ropes (after GameCommon's sea nettle): each a short chain of points simulated here, in the
## world, hung from under the bell, so they are dragged after it however it is moved or turned and swing
## back under it slowly; each arm's frills and clubs all follow its rope.
##
## How it looks and moves only. Whatever moves it puts it where it is each frame (**the origin is the
## middle of its bell's rim**; up is +Y; it has no front) and calls `step(velocity, delta)`. After putting
## it somewhere new all at once, `lay_ropes()` hangs its arms afresh there (a jump of more than two of its
## own metres in one step does so by itself, and so does being shown again).
##
## Three models: the full one, the game one (`game`: 1,568 triangles) and the low one (`low`: far
## off, crowds, phones; its arms are not ropes: the shader hangs them and leans them back as it goes). Each
## is loaded only when first shown, so a game that sets `game` before adding the node never loads the full
## one. Models: creatures/fried_egg_jelly/models/, built by tools/build_fried_egg_jelly.py.

const MODEL := "res://creatures/fried_egg_jelly/models/fried_egg_jelly%s.glb"
const BELL_SHADER := preload("res://creatures/fried_egg_jelly/fried_egg_jelly.gdshader")
const STRAND_SHADER := preload("res://creatures/fried_egg_jelly/fried_egg_jelly_strands.gdshader")
## Its size at scale 1 (metres): the bell across (LENGTH and WIDTH: a jelly's "length" for eating) and how
## high it stands (the yolk's top above the rim).
const LENGTH := 0.4
const WIDTH := 0.4
const DEPTH := 0.12
## How far its arms reach below its origin at rest, hanging straight (metres, scale 1).
const REACH := 0.21
## How far from an arm's rope its frills and clubs reach (metres, scale 1): the sting test's reach.
const ARM_REACH := 0.07
## It is harmless: a game may let it be bumped or eaten rather than sting.
const STINGS := false
## As the model is built (tools/build_fried_egg_jelly.py): keep them in step.
const RADIUS := 0.2
const ARMS := 8
const ARM_LONG := 0.17
const ARM_AT := 0.045
const ARM_Y := -0.02
## The beat of the bell, as the shader has it (CONTRACT, DROP, LAG there): how much the rim draws in (a
## share of its reach) and down (metres), and how much later the beat reaches the rim than the middle.
const CONTRACT := 0.06
const DROP := 0.015
const LAG := 0.25
## The ropes, as the strand shader has them: points on an arm's, and how wide the picture is that
## carries them (a row an arm; its last column holds the arm's root at rest).
const ARM_POINTS := 6
const ROPE_ROW := 7
const SURFACES: Array[String] = ["fried_egg_strands", "fried_egg_bell"]
## The bell's parts (vertex colour red) in the order they are drawn: its underside, then its top.
const BELL_ORDER: Array[float] = [0.25, 0.0]

## Seconds a beat of its bell takes (slow and gentle). Everything the bell does runs on `phase`.
@export var beat := 3.2
## How far out past its resting shape the bell opens between beats, as a share of how far it draws in.
@export var open := 0.25:
	set(value):
		open = value
		_send(&"open", value)
## The low model: far off, crowds, phones. Its arms are not ropes.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight); `low` still wins.
@export var game := false:
	set(value):
		game = value
		_show()
## How much its strands are stirred about as they hang (0 still).
@export var wander := 1.0
## The ropes' weight: how much the water slows them (/s), how strongly each is drawn back to hang straight
## under the bell (/s², all of it at the root, a tenth at the tip), how fast they sink (m/s²).
@export var rope_drag := 5.0
@export var rope_hold := 30.0
@export var rope_sink := 0.05
## How far through a beat of its bell it is (0..1). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)
## How much it glows (0 by day, 1 at night).
var glow := 0.0:
	set(value):
		glow = value
		_send_glow()
## How far its bell is drawn in now (0..1), and the push of the beat (1 as a beat starts, dying away):
## for whatever moves it.
var pulse := 0.0
var thrust := 0.0

static var _meshes := {}

var _strand_material: ShaderMaterial
var _bell_material: ShaderMaterial
var _shown := {}
var _trail := Vector3.ZERO
var _moving := Vector3.ZERO
var _flash := 0.0
var _ropes := PackedVector3Array()
var _ropes_before := PackedVector3Array()
var _rope_from := PackedInt32Array()
var _rope_data := PackedFloat32Array()
var _rope_picture: ImageTexture
var _laid := false
var _was_at := Vector3.ZERO

static var _strands := []


## The full model's mesh, or the low one's (two surfaces, named as SURFACES: wear `new_materials()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at("_lo" if low_wanted else "")


## The game model's mesh, as `mesh_of`'s.
static func game_mesh() -> Mesh:
	return _mesh_at("_game")


## New materials for the meshes: [strands, bell] (surface 0, surface 1). On their own (with no node to lay
## the ropes) they draw the strands as the low model does: hanging, leaning back by `trail`.
static func new_materials() -> Array[ShaderMaterial]:
	var strands := ShaderMaterial.new()
	strands.shader = STRAND_SHADER
	strands.render_priority = 0
	var bell := ShaderMaterial.new()
	bell.shader = BELL_SHADER
	bell.render_priority = 1
	return [strands, bell]


static func _mesh_at(suffix: String) -> Mesh:
	if not _meshes.has(suffix):
		var made := (load(MODEL % suffix) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		var plain := ArrayMesh.new()
		# (rebuilt without the importer's automatic LODs: the shaders bend it, and a thinned copy bends in
		# straight pieces; the strands first, then the bell, its triangles sorted into drawing order)
		for want in SURFACES:
			for surface in found.mesh.get_surface_count():
				var named := found.mesh.surface_get_material(surface)
				if (named.resource_name if named else "") != want:
					continue
				var arrays := found.mesh.surface_get_arrays(surface)
				if want == SURFACES[1]:
					arrays[Mesh.ARRAY_INDEX] = _in_order(arrays)
				plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
				plain.surface_set_name(plain.get_surface_count() - 1, want)
		_meshes[suffix] = plain
		made.free()
	return _meshes[suffix]


# (clear jelly is not sorted triangle by triangle: within the bell, its underside is drawn before its top)
static func _in_order(arrays: Array) -> PackedInt32Array:
	var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var colours: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
	var out := PackedInt32Array()
	for part in BELL_ORDER:
		for i in range(0, index.size(), 3):
			if absf(colours[index[i]].r - part) < 0.06:
				out.append(index[i])
				out.append(index[i + 1])
				out.append(index[i + 2])
	if out.size() != index.size():
		push_warning("FriedEggJelly: a part of the bell is not in BELL_ORDER")
	return out


func _init() -> void:
	var made := new_materials()
	_strand_material = made[0]
	_bell_material = made[1]


func _ready() -> void:
	_show()
	_send(&"phase", phase)
	_send(&"open", open)
	_send_glow()


## Each frame, after putting it where it is. Its ropes follow however it has been moved and turned since
## the last step. `velocity` (world, m/s) is how fast it is going through the water: where that is more
## than it has really moved (one held still in water that runs past), the ropes are carried off by the
## difference; give Vector3.ZERO when there is nothing to add. The low model leans its strands back by it.
func step(velocity: Vector3, delta: float) -> void:
	delta = minf(delta, 0.05)
	_moving = _moving.lerp(velocity, 1.0 - exp(-1.6 * delta))
	var back := -(global_basis.orthonormalized().inverse() * _moving) * 0.4 / _size()
	_trail = _trail.lerp(back.limit_length(0.85), 1.0 - exp(-2.2 * delta))
	var was := phase
	phase += delta / maxf(beat, 0.05)
	if phase < was:
		thrust = 1.0
	pulse = _squeeze(phase)
	thrust = maxf(thrust - delta * 1.5, 0.0)
	_flash = maxf(_flash - delta * 3.0, 0.0)
	_send(&"trail", _trail)
	_send_glow()
	if not is_inside_tree():
		return
	if low or not is_visible_in_tree():
		# (no ropes: they are hung afresh when they are next wanted)
		_laid = false
	elif not _laid or global_position.distance_to(_was_at) > 2.0 * _size():
		lay_ropes()
	elif delta > 0.0:
		_swing_ropes(velocity, delta)
		_send_ropes()


## Sets one of the shaders' settings on both: colours (bell: `white`, `groove`, `yolk`, `yolk_deep`,
## `under`; arms: `frill`, `frill_edge`, `club`, `purple`), how clear (`bell_alpha`, `under_alpha`,
## `arm_alpha`), `self_light` (how much it shows by its own colour in dim water), `line_width` (the clubs'
## width, for 1 as built), `min_angle` (the least a club is drawn wide, as seen: radians).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_strand_material.set_shader_parameter(setting, value)
	_bell_material.set_shader_parameter(setting, value)


## Its two materials: [strands, bell].
func materials() -> Array[ShaderMaterial]:
	return [_strand_material, _bell_material]


## Something touched it: it flashes (it does not sting).
func sting(_at: Vector3) -> void:
	_flash = 1.0


func _send(setting: StringName, value: Variant) -> void:
	if _strand_material:
		_strand_material.set_shader_parameter(setting, value)
		_bell_material.set_shader_parameter(setting, value)


func _send_glow() -> void:
	_send(&"glow", maxf(glow, _flash))


# (shows the model asked for, loading it the first time it is shown)
func _show() -> void:
	if not is_node_ready():
		return
	var wanted := "_lo" if low else "_game" if game else ""
	if not _shown.has(wanted):
		var mesh := MeshInstance3D.new()
		mesh.mesh = _mesh_at(wanted)
		mesh.set_surface_override_material(0, _strand_material)
		mesh.set_surface_override_material(1, _bell_material)
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		# (its strands may swing anywhere within their length of it)
		mesh.extra_cull_margin = REACH * 1.1
		mesh.name = "Jelly" + wanted
		add_child(mesh)
		_shown[wanted] = mesh
	for suffix: String in _shown:
		(_shown[suffix] as MeshInstance3D).visible = suffix == wanted
	_send(&"roped", not low)
	if not low:
		_laid = false


## Its arms as built: [root (its own space, at rest), length, phase 0..1, an arm (always), which rope].
static func strands() -> Array:
	var all := []
	for k in ARMS:
		var a := (k + 0.5) * TAU / ARMS
		all.append([Vector3(cos(a) * ARM_AT, ARM_Y, sin(a) * ARM_AT), ARM_LONG * (1.0 + 0.1 * sin(k * 2.1 + 0.4)), fposmod(k * 0.37 + 0.11, 1.0), true, k])
	return all


static func _all() -> Array:
	if _strands.is_empty():
		_strands = strands()
	return _strands


static func _points(_strand: Array) -> int:
	return ARM_POINTS


## Where `s` (0 root .. 1 tip) along strand `strand` (of `strands()`) is now, in the world: on its rope (or,
## for the low model, where the shader hangs it, less its sway).
func strand_point(strand: Array, s: float) -> Vector3:
	s = clampf(s, 0.0, 1.0)
	var long: float = strand[1]
	if low:
		var bend := s * s * long
		return global_transform * (_bell_move(strand[0]) - Vector3(0.0, s * long, 0.0) + Vector3(_trail.x, 0.0, _trail.z) * bend * 0.8)
	if not _laid:
		lay_ropes()
	var k: int = strand[4]
	var count := _points(strand)
	var base := _rope_from[k]
	var f := s * (count - 1)
	var i := mini(int(f), count - 2)
	var t := f - i
	var p0 := _ropes[base + maxi(i - 1, 0)]
	var p1 := _ropes[base + i]
	var p2 := _ropes[base + i + 1]
	var p3 := _ropes[base + mini(i + 2, count - 1)]
	return 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * (p1 - p2) + p3 - p0) * t * t * t)


## How far the bell is drawn in, through a beat (0..1): quickly in, slowly let go (`squeeze` in the shader).
static func _squeeze(x: float) -> float:
	x = fposmod(x, 1.0)
	return smoothstep(0.0, 0.25, x) * (1.0 - smoothstep(0.3, 1.0, x))


## Where a point of the bell at rest (its own space) is now, as the beat moves it (`bell_move` in the shader).
func _bell_move(p: Vector3) -> Vector3:
	var reach := Vector2(p.x, p.z).length()
	var rim := smoothstep(0.15 * RADIUS, RADIUS, reach)
	var k := _squeeze(phase - LAG * rim) * (1.0 + open) - open
	var by := 1.0 - CONTRACT * k * rim
	return Vector3(p.x * by, p.y - DROP * k * rim * rim, p.z * by)


func _size() -> float:
	return maxf(global_basis.get_scale().x, 0.0001)


## Hangs every strand afresh, straight down from the bell where it is now (after putting it somewhere new
## all at once: its ropes would otherwise be dragged there from where it was).
func lay_ropes() -> void:
	var all := _all()
	if _rope_from.is_empty():
		var total := 0
		for strand: Array in all:
			_rope_from.append(total)
			total += _points(strand)
		_ropes.resize(total)
		_ropes_before.resize(total)
		_rope_data.resize(ROPE_ROW * all.size() * 4)
	var size := _size()
	var down := global_basis.orthonormalized() * Vector3.DOWN
	for k in all.size():
		var strand: Array = all[k]
		var count := _points(strand)
		var root := global_transform * _bell_move(strand[0])
		var piece: float = float(strand[1]) * size / (count - 1)
		for i in count:
			_ropes[_rope_from[k] + i] = root + down * piece * i
			_ropes_before[_rope_from[k] + i] = root + down * piece * i
	_laid = true
	_was_at = global_position
	_send_ropes()


## A step of the ropes (Verlet): each point keeps going as it was, slowed by the water, drawn back towards
## hanging straight down from the bell (strongly near its root, hardly at its tip), stirred a little,
## sinking; then each rope is held to its length from its root down.
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
	var beat_angle := phase * TAU
	var sink := Vector3.DOWN * rope_sink * size * delta * delta
	for k in all.size():
		var strand: Array = all[k]
		var count := _points(strand)
		var base := _rope_from[k]
		var root := global_transform * _bell_move(strand[0])
		var piece: float = float(strand[1]) * size / (count - 1)
		var own: float = float(strand[2]) * TAU
		_ropes[base] = root
		_ropes_before[base] = root
		for i in range(1, count):
			var p := _ropes[base + i]
			var share := float(i) / (count - 1)
			var held := 1.0 - 0.9 * smoothstep(0.0, 0.9, share)
			var pull := (root + down * piece * i - p) * rope_hold * held
			# (stirred: a slow round that comes back with each beat, each strand at its own time)
			var stir := turned * Vector3(sin(beat_angle + own + share * 4.0), 0.0, cos(beat_angle + own * 1.7 + share * 3.0)) * 0.3 * wander * size * share
			var moved := (p - _ropes_before[base + i]) * keep + carried + (pull + stir) * delta * delta + sink
			_ropes_before[base + i] = p
			_ropes[base + i] = p + moved
		for again in 3:
			for i in range(1, count):
				var from := _ropes[base + i - 1]
				var to := _ropes[base + i] - from
				var long := to.length()
				if long > 0.00001:
					_ropes[base + i] = from + to * (piece / long)


## The ropes to the strand shader: a picture, a row a strand, each point in the jelly's own space; the
## last column holds the strand's root at rest.
func _send_ropes() -> void:
	var to_local := global_transform.affine_inverse()
	var all := _all()
	for k in all.size():
		var count := _points(all[k])
		var base := _rope_from[k]
		var at := k * ROPE_ROW * 4
		for i in count:
			var p := to_local * _ropes[base + i]
			_rope_data[at + i * 4] = p.x
			_rope_data[at + i * 4 + 1] = p.y
			_rope_data[at + i * 4 + 2] = p.z
		var root: Vector3 = all[k][0]
		_rope_data[at + (ROPE_ROW - 1) * 4] = root.x
		_rope_data[at + (ROPE_ROW - 1) * 4 + 1] = root.y
		_rope_data[at + (ROPE_ROW - 1) * 4 + 2] = root.z
	var image := Image.create_from_data(ROPE_ROW, all.size(), false, Image.FORMAT_RGBAF, _rope_data.to_byte_array())
	if _rope_picture == null:
		_rope_picture = ImageTexture.create_from_image(image)
		_send(&"ropes", _rope_picture)
	else:
		_rope_picture.update(image)


## Whether anything on the line from `a` to `b` (world) is within reach of its arms, `radius` more (a
## swimmer's body: nose to tail, and how thick). It does not sting (`STINGS`): this is for bumping.
func touches(a: Vector3, b: Vector3, radius := 0.25) -> bool:
	var size := _size()
	for strand: Array in _all():
		var reach: float = ARM_REACH * size + radius
		var last := strand_point(strand, 0.0)
		for k in range(1, 7):
			var here := strand_point(strand, k / 6.0)
			var pair := Geometry3D.get_closest_points_between_segments(a, b, last, here)
			if pair[0].distance_to(pair[1]) < reach:
				return true
			last = here
	return false


## How low its lowest strand hangs now, under its origin (metres, world).
func lowest() -> float:
	var lowest_y := INF
	for strand: Array in _all():
		lowest_y = minf(lowest_y, strand_point(strand, 1.0).y)
	return global_position.y - lowest_y
