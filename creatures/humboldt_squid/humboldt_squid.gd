class_name HumboldtSquid
extends Node3D
## A Humboldt or jumbo squid (Dosidicus gigas, "diablo rojo"): a stout muscular barrel of a
## mantle 1.2 m long, two big fins that together are a diamond across its back end, a head as
## wide as the mantle with an eye on each side and the siphon under it, eight thick suckered
## arms and two tentacles only a little longer, ending in broad clubs: about 2.5 m in all. It
## swims mantle first, towards its own -Z; its arms and tentacles trail behind it, towards +Z;
## its back is +Y. The origin is the middle of its head, between its eyes. `scale` it for a
## smaller or bigger one.
##
## IT CHANGES COLOUR (the user, 2026-11-17: "And the humbolt should color change"). Its skin is
## pale under a sheet of red colour cells that open (deep red) and shut to specks (white to
## pink). Calm, paler and redder patches run through it in slow waves (the flicker); and it
## flashes, the whole body to white and back to red, or as a wave from its mantle's tip to its
## arms' tips. All of it goes by `colour_phase` (0..1, one round of its colours): `flashes` a
## round and `flicker_rounds` a round are whole numbers, so a round comes back exactly to where
## it began. `flash()` flashes once, now, whatever the round is doing.
##
## Its mantle breathes in slowly and squeezes quickly (a jet: `beat` seconds), its fins flap,
## and its arms open a little as it fills and close as it jets (`bell`: into a wide fan).
##
## Its arms and tentacles are ropes, as the giant squid's and the sea nettle's are (GameCommon's
## godot/sea-nettle: its README's "Decision: ropes" says why and how): each of the ten is a
## chain of points simulated here, in the world, hung from the head. So they are dragged after
## it however it is moved or turned, lag behind and swing through; and they are heavy (much
## drag, no flicking: `rope_drag`, `rope_hold`, `rope_sink`). The arms' rest is a tight cone
## trailing behind the head (`cone`), as a living one holds them.
##
## How it looks and moves only: whatever moves it puts it where it is each frame and calls
## `step(velocity, delta)`. After putting it somewhere new all at once, `lay_ropes()` hangs
## its arms afresh there (a jump of more than two of its own lengths of mantle in one step
## does so by itself, and so does its being seen again after being hidden).
##
## Nothing in it runs on a clock that only grows: the jet, the fins, the arms' opening and the
## stirring of the ropes go by `phase`, its colours by `colour_phase`. `step` moves `phase` on by
## delta / beat (set `beat` to 0 and `phase` yourself to drive it), and `colour_phase` by
## delta / colour_beat (0: it is `phase`; less than 0: it is yours to set).
##
## This is the giant squid's code (godot/giant-squid), copied and changed: components here
## stand alone, each game owning its copy, so nothing is shared between the two.
##
## The model is creatures/humboldt_squid/models/humboldt_squid.glb (and _lo, and _game), built by
## tools/build_humboldt_squid.py; humboldt_squid.gdshaderinc pulses the mantle, lays the strands
## along their ropes and draws the skin and its colour.

const MODEL := "res://creatures/humboldt_squid/models/humboldt_squid%s.glb"
const BODY := preload("res://creatures/humboldt_squid/humboldt_squid_body.gdshader")
const FINS := preload("res://creatures/humboldt_squid/humboldt_squid_fins.gdshader")
## As the model is built (tools/build_humboldt_squid.py) and the shader has them: keep them in step.
const MANTLE_FROM := -0.1
const MANTLE_LONG := 1.2
const ARMS := 8
const ARM_RING := 0.088
const ARM_Z := 0.17
const ARM_LONG := 0.72
const TENTACLES := 2
const TENTACLE_LONG := 1.0
## The ropes, as the shader has them: how many points an arm's has and a tentacle's (which is
## also how wide the picture is that carries them to the shader, a row a strand).
const ARM_POINTS := 8
const TENTACLE_POINTS := 10
## The share of a jet spent breathing in (the rest is the squeeze), as the shader has it.
const SQUEEZE_AT := 0.62

## Seconds a jet takes (a slow breath in, a quicker squeeze). 0: `phase` is yours to set.
@export var beat := 2.0
## Seconds a round of its colours takes. 0: the same as a jet (`colour_phase` is `phase`). Less
## than 0: `colour_phase` is yours to set.
@export var colour_beat := 0.0
## How red it is when calm (0 pale all over, 1 deep red all over).
@export_range(0.0, 1.0) var redness := 0.82
## Flashes in a round of its colours (a whole number, so that a round comes back to where it
## began; 0 none). A living one flashes 2 to 4 times a second when roused: with a round of 2 s,
## that is 4 to 8.
@export var flashes := 1
## How pale a flash goes (1: right to white).
@export_range(0.0, 1.0) var flash_strength := 1.0
## The share of a flash's turn it spends going pale and coming back; the rest of the turn it is
## red (1: no rest, one smooth swing after another).
@export_range(0.05, 1.0) var flash_share := 0.3
## How much a flash is a wave running from the mantle's tip to the arms' tips, and not the whole
## body at once (0 all at once; 1 the wave takes a whole turn to cross it).
@export_range(0.0, 1.0) var flash_wave := 0.2
## The calm flicker: how strong the slow waves of paler and redder patches are (0 none), and how
## many times they come round in a round of its colours (a whole number).
@export_range(0.0, 1.0) var flicker := 0.3
@export var flicker_rounds := 2
## How wide the arms' rest is spread behind the head (the tangent of the cone's half angle at
## the arms' roots; they draw together further back).
@export var cone := 0.16
## Swims like a jellyfish: how far its arms spread out into a bell as the mantle fills (0 not at
## all: the tight cone only; 1 wide open, like an umbrella), to be swept shut behind it as it jets.
@export var bell := 0.0
## Cartoon eyes (0 the dark eye with its silver ring of the real animal; 1 the cartoon eye: bigger,
## a white, a fiery amber iris, a big round pupil, a highlight, a dark outline, and a lid slanted
## down towards its arms in a scowl: the "red devil"). Sent to the shader every step.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0
## How much the ropes are stirred about as they trail, for 1 as it hangs in open water. The
## stirring comes round with each jet.
@export var wander := 1.0
## The ropes' weight. How much the water slows them (/s: the more, the less they flick and the
## further they are left behind); how strongly each is drawn back to its rest (/s², all of it
## at the root, a tenth of it at the tip); how fast they sink (m/s², straight down in the
## world); and how much more loosely the two tentacles are held than the arms.
@export var rope_drag := 5.0
@export var rope_hold := 26.0
@export var rope_sink := 0.08
@export var tentacle_loose := 0.5
## How many times the fins flap in a jet (a whole number comes round with it).
@export var fin_ripples := 2
## Full detail within this of the camera; the low model (no sucker cups) further off.
@export var detail_range := 18.0
## The game model (about 4,100 triangles, its sucker cups painted by the shader) near, in place of
## the full one (54,900); the low one still far off. With it the full model is never loaded: each
## model is loaded only when it is first shown.
@export var game := false:
	set(value):
		game = value
		if not _models.is_empty():
			_show(not _models.has("_lo") or not (_models["_lo"] as MeshInstance3D).visible)
## Where its eyes look (-1..1 each way, in each eye's own plane): x towards its arms (+1) or its
## mantle (-1), y up its back. Both eyes look the same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		set_shader_parameter(&"eye_look", value)
## Its eyes' lids: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		set_shader_parameter(&"blink", value)
## A light of its own (0 none): for dark water.
var glow := 0.0
## A round tank it is kept inside (the user, 2026-11-17, of a tube of water it swam in: "make sure
## the squid and eel dont clip out the sides of the tank"): the tank's radius (world metres; 0
## none) about the upright line through `tank_at`. Its ropes are put back inside the wall.
var tank := 0.0
var tank_at := Vector3.ZERO
## How far through a jet it is (0..1): it breathes in until SQUEEZE_AT, then squeezes.
var phase := 0.0
## How far through a round of its colours it is (0..1).
var colour_phase := 0.0
## How full of water its mantle is now (0..1), and the push of the squeeze (1 as it starts,
## falling away), for its mover.
var fullness := 0.0
var thrust := 0.0

# Its models, by suffix ("", "_game", "_lo"), each made when it is first shown.
var _models := {}
var _materials: Array[ShaderMaterial] = []
# A flash of its own (`flash()`): how far through it (0..1; 1 none), and how long it takes.
var _flash_at := 1.0
var _flash_takes := 0.4
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
static var _game_cache: Mesh


func _ready() -> void:
	for shader: Shader in [BODY, FINS]:
		var material := ShaderMaterial.new()
		material.shader = shader
		_materials.append(material)
	_materials[1].render_priority = 1
	for setting in [&"cartoon_eyes", &"eye_look", &"blink"]:
		set_shader_parameter(setting, get(setting))
	# (the first model is put off to the end of the frame, so that `game` set just after it is added
	# is heeded before any model is loaded)
	_first_show.call_deferred()


func _first_show() -> void:
	if _models.is_empty():
		_show(true)


## Shows the model it should wear (near: the full one, or the game one with `game`; else the low
## one), loading it the first time.
func _show(near: bool) -> void:
	var wear := "_lo" if not near else ("_game" if game else "")
	if not _models.has(wear):
		_models[wear] = _mesh_of(wear)
	for suffix: String in _models:
		(_models[suffix] as MeshInstance3D).visible = suffix == wear


## The game model's mesh, as imported, without the thinned LOD meshes Godot's importer makes (its
## mantle and strands are bent in the shader: a thinned one would bend in straight pieces). Two
## surfaces: the body, and the fins (their material's resource_name is "squid_fins").
static func game_mesh() -> Mesh:
	if _game_cache == null:
		var made := (load(MODEL % "_game") as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		var plain := ArrayMesh.new()
		for surface in found.mesh.get_surface_count():
			plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, found.mesh.surface_get_arrays(surface))
			plain.surface_set_material(surface, found.mesh.surface_get_material(surface))
		made.free()
		_game_cache = plain
	return _game_cache


func _mesh_of(suffix: String) -> MeshInstance3D:
	var made: Node = null
	var mesh := MeshInstance3D.new()
	if suffix == "_game":
		mesh.mesh = game_mesh()
	else:
		made = (load(MODEL % suffix) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		mesh.mesh = found.mesh
	for surface in mesh.mesh.get_surface_count():
		var named := mesh.mesh.surface_get_material(surface)
		var fins := named != null and named.resource_name == "squid_fins"
		mesh.set_surface_override_material(surface, _materials[1 if fins else 0])
	# (its ropes may swing anywhere within their length of it)
	mesh.extra_cull_margin = TENTACLE_LONG * 1.1
	mesh.name = "Squid" + suffix
	if made:
		made.free()
	add_child(mesh)
	return mesh


## How full the mantle is at `x` through a jet (0..1): filling slowly, emptied quickly (the
## shader's `fullness`).
static func fullness_at(x: float) -> float:
	x = fposmod(x, 1.0)
	var through := 0.5 * x / SQUEEZE_AT if x < SQUEEZE_AT else 0.5 + 0.5 * (x - SQUEEZE_AT) / (1.0 - SQUEEZE_AT)
	return 0.5 - 0.5 * cos(through * TAU)


## A flash, once, now: the whole body to white and back over `seconds`, whatever the round of
## its colours is doing. (It is not part of the round: a picture that must loop should not call it.)
func flash(seconds := 0.4) -> void:
	_flash_at = 0.0
	_flash_takes = maxf(seconds, 0.01)


## Each frame, after putting it where it is. Its ropes follow however it has been moved and
## turned since the last step. `velocity` (world, m/s) is how fast it is going through the
## water: where that is more than it has really moved (a squid held still in a picture, in
## water that runs past it), the ropes are carried off by the difference; give Vector3.ZERO
## when there is nothing to add.
func step(velocity: Vector3, delta: float) -> void:
	delta = minf(delta, 0.05)
	if beat > 0.0:
		var was := phase
		phase = fposmod(phase + delta / beat, 1.0)
		if was < SQUEEZE_AT and phase >= SQUEEZE_AT:
			thrust = 1.0
	if colour_beat > 0.0:
		colour_phase = fposmod(colour_phase + delta / colour_beat, 1.0)
	elif colour_beat == 0.0:
		colour_phase = phase
	fullness = fullness_at(phase)
	thrust = maxf(thrust - delta * 2.5, 0.0)
	_flash_at = minf(_flash_at + delta / _flash_takes, 1.0)
	set_shader_parameter(&"phase", phase)
	set_shader_parameter(&"fin_ripples", float(fin_ripples))
	set_shader_parameter(&"glow", glow)
	set_shader_parameter(&"colour_phase", colour_phase)
	set_shader_parameter(&"redness", redness)
	set_shader_parameter(&"flashes", float(flashes))
	set_shader_parameter(&"flash_strength", flash_strength if flashes > 0 else 0.0)
	set_shader_parameter(&"flash_share", flash_share)
	set_shader_parameter(&"flash_wave", flash_wave)
	set_shader_parameter(&"flicker", flicker)
	set_shader_parameter(&"flicker_rounds", float(flicker_rounds))
	set_shader_parameter(&"flash_now", pow(sin(PI * _flash_at), 2.0))
	set_shader_parameter(&"cartoon_eyes", cartoon_eyes)
	if is_inside_tree():
		if not is_visible_in_tree():
			# (unseen, its ropes are not worked out: they are hung afresh when it is next seen)
			_laid = false
		elif not _laid or global_position.distance_to(_was_at) > 2.0 * MANTLE_LONG * _size():
			lay_ropes()
		elif delta > 0.0:
			_swing_ropes(velocity, delta)
			_send_ropes()
	var camera := get_viewport().get_camera_3d() if is_inside_tree() else null
	if camera:
		_show(camera.global_position.distance_to(global_position) < detail_range)


## Sets one of the shader's settings (its colours: `skin`, `deep`, `pale`, `cup`, `silver`; how
## big its colour cells are: `cell`; how clear its fins' edges are: `fin_alpha`) on every part of it.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	for material in _materials:
		material.set_shader_parameter(setting, value)


## Its strands as built: [root (its own space), length, phase 0..1, an arm or not (a tentacle),
## which strand, the way out from its middle it lies (its own space, a unit)], arms first: arm 0
## is the upper one on its +X side, and they go round by way of its back.
static func strands() -> Array:
	var all := []
	for k in ARMS:
		var a := (k + 0.5) * TAU / ARMS
		var out := Vector3(cos(a), sin(a), 0.0)
		all.append([out * ARM_RING + Vector3(0.0, 0.0, ARM_Z), ARM_LONG - 0.08 * sin(a), fposmod(k * 0.37 + 0.11, 1.0), true, k, out])
	for k in range(ARMS, ARMS + TENTACLES):
		var side := 1.0 if k == ARMS else -1.0
		all.append([Vector3(side * 0.032, -0.02, ARM_Z + 0.015), TENTACLE_LONG * (1.0 if side > 0.0 else 0.96), fposmod(k * 0.37 + 0.11, 1.0), false, k, Vector3(side, 0.0, 0.0)])
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
	var k: int = strand[4]
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


func _size() -> float:
	return maxf(global_basis.get_scale().x, 0.0001)


## The way a strand's rope leaves the head, and the way it runs further back (its own space,
## units): an arm leaves along the cone, opened a little as the mantle fills and closed as it
## jets, and runs nearly straight back; a tentacle runs straight back from the first.
func _rope_ways(strand: Array) -> Array[Vector3]:
	var out: Vector3 = strand[5]
	if not strand[3]:
		return [Vector3(out.x * 0.04, -0.03, 1.0).normalized(), Vector3(out.x * 0.02, -0.02, 1.0).normalized()]
	var open := cone * (0.75 + 0.5 * fullness) + bell * 1.5 * fullness
	# (opened into a bell, the arms curve: out from the head, then back at their tips)
	return [(Vector3.BACK + out * open).normalized(), (Vector3.BACK + out * open * (0.3 + 0.35 * bell)).normalized()]


## Hangs every arm and tentacle afresh, at rest behind the head where it is now (after putting
## it somewhere new all at once: its ropes would otherwise be dragged there from where it was).
func lay_ropes() -> void:
	var all := _all()
	if _rope_from.is_empty():
		var total := 0
		for strand: Array in all:
			_rope_from.append(total)
			total += ARM_POINTS if strand[3] else TENTACLE_POINTS
		_ropes.resize(total)
		_ropes_before.resize(total)
		_rope_data.resize(TENTACLE_POINTS * all.size() * 4)
	var size := _size()
	var turned := global_basis.orthonormalized()
	for k in all.size():
		var strand: Array = all[k]
		var count := ARM_POINTS if strand[3] else TENTACLE_POINTS
		var ways := _rope_ways(strand)
		var piece: float = float(strand[1]) * size / (count - 1)
		var rest := global_transform * (strand[0] as Vector3)
		for i in count:
			if i > 0:
				rest += turned * ways[0].lerp(ways[1], smoothstep(0.0, 0.5, float(i) / (count - 1))).normalized() * piece
			_ropes[_rope_from[k] + i] = rest
			_ropes_before[_rope_from[k] + i] = rest
	_laid = true
	_was_at = global_position
	_send_ropes()


## A step of the ropes (Verlet): each point keeps going as it was, slowed by the water, drawn
## back towards its rest behind the head (strongly near its root, hardly at its tip), stirred
## a little, sinking; then each rope is held to its length from its root down. The water
## stands still in the world, but for `velocity` more than the squid has really moved: that
## much runs past it the other way and carries the ropes with it.
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
	for k in all.size():
		var strand: Array = all[k]
		var arm: bool = strand[3]
		var count := ARM_POINTS if arm else TENTACLE_POINTS
		var base := _rope_from[k]
		var ways := _rope_ways(strand)
		var long: float = float(strand[1]) * size
		var piece := long / (count - 1)
		var own: float = float(strand[2]) * TAU
		var hold := rope_hold * (1.0 if arm else tentacle_loose)
		var rest := global_transform * (strand[0] as Vector3)
		_ropes[base] = rest
		_ropes_before[base] = rest
		for i in range(1, count):
			var p := _ropes[base + i]
			var share := float(i) / (count - 1)
			var held := 1.0 - 0.9 * smoothstep(0.0, 0.9, share)
			rest += turned * ways[0].lerp(ways[1], smoothstep(0.0, 0.5, share)).normalized() * piece
			var pull := (rest - p) * hold * held
			# (stirred: a slow round that comes back with each jet, each strand at its own time)
			var stir := turned * Vector3(sin(angle + own + share * 4.0), cos(angle + own * 1.7 + share * 3.0), 0.0) * 0.12 * wander * long * share
			var moved := (p - _ropes_before[base + i]) * keep + carried + (pull + stir) * delta * delta + sink
			_ropes_before[base + i] = p
			_ropes[base + i] = p + moved
		# held to length, from the root down (three times over, so that it settles)
		for again in 3:
			for i in range(1, count):
				var from := _ropes[base + i - 1]
				var to := _ropes[base + i] - from
				var gap := to.length()
				if gap > 0.00001:
					_ropes[base + i] = from + to * (piece / gap)
				_ropes[base + i] = _in_tank(_ropes[base + i])


## `p` (world), put back inside the round tank if it is outside it (see `tank`).
func _in_tank(p: Vector3) -> Vector3:
	if tank <= 0.0:
		return p
	var out := Vector2(p.x - tank_at.x, p.z - tank_at.z)
	var far := out.length()
	if far <= tank:
		return p
	out *= tank / far
	return Vector3(tank_at.x + out.x, p.y, tank_at.z + out.y)

## The ropes to the shader: a picture, a row a strand, each point in the squid's own space.
func _send_ropes() -> void:
	var to_local := global_transform.affine_inverse()
	var all := _all()
	for k in all.size():
		var count := ARM_POINTS if all[k][3] else TENTACLE_POINTS
		var base := _rope_from[k]
		var at := k * TENTACLE_POINTS * 4
		for i in count:
			var p := to_local * _ropes[base + i]
			_rope_data[at] = p.x
			_rope_data[at + 1] = p.y
			_rope_data[at + 2] = p.z
			at += 4
	var image := Image.create_from_data(TENTACLE_POINTS, all.size(), false, Image.FORMAT_RGBAF, _rope_data.to_byte_array())
	if _rope_picture == null:
		_rope_picture = ImageTexture.create_from_image(image)
		set_shader_parameter(&"ropes", _rope_picture)
	else:
		_rope_picture.update(image)
