class_name ChannelCatfish
extends Node3D
## A channel catfish (Ictalurus punctatus), 0.6 m long: a long scaleless body, a broad head
## flattened into a wedge with a wide mouth under an overhanging snout, small eyes, eight
## barbels (a long one at each corner of the mouth, four across the chin, a short one at each
## rear nostril), a tall dorsal fin with a spine up its front, the small fleshy adipose fin, a
## deeply forked tail, a long round-edged anal fin, and a pair each of pectoral and pelvic fins.
## A slate-olive back, silvery sides scattered with small dark spots, a white belly: all drawn
## by its shader (no texture files).
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## the line through the middle of its tail wrist, half way along, so it reaches 0.3 m ahead
## and 0.3 m behind. `scale` it (evenly) for a bigger or smaller one. No sound.
##
## It swims by a slow wave down its whole body, drawn by the shader (no bones): the head
## swinging a little, the tail widest. Its mouth opens (`gape`): the lower jaw swings down
## under the snout, and the chin's four barbels go with it.
##
## Its barbels are ropes, as the sea nettle's strands are (GameCommon's godot/sea-nettle: its
## README's "Decision: ropes" says why and how): each is a short chain of points simulated
## here, in the world, rooted on the head where the body's wave has put it. So they trail
## behind however it is moved or turned, lag the head's swing and swing through; they are
## heavy (much drag, no flicking: `barbel_drag`, `barbel_hold`), and they lie along the head
## and chin, not through them.
##
## Everything that comes round runs on `phase`, 0 to 1 through one `beat`, in which its tail
## beats `tail_beats` times (a whole number), so its motion comes round again exactly every
## beat: the same names and meanings as GameCommon's yellowfin tuna and cutthroat trout.
## Call `step(velocity, delta)` each frame after placing it: it moves `phase` on by
## delta / beat and swings the barbels. For a picture that must loop, set `beat` to 0, set
## `phase` yourself each frame (frame / frames in a beat) and still call `step`, which then
## only swings the barbels; `settle` runs them in beforehand. (One whose `step` is never
## called carries its barbels stiffly, at rest.)
##
## The model is creatures/channel_catfish/models/channel_catfish.glb (and _lo), built by
## tools/build_channel_catfish.py; channel_catfish.gdshader draws its markings, swims it and
## lays its barbels along their ropes.

const MODEL := "res://creatures/channel_catfish/models/channel_catfish%s.glb"
const SHADER := preload("res://creatures/channel_catfish/channel_catfish.gdshader")
## As the model is built (tools/build_channel_catfish.py): from the tip of its snout to the
## tips of its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.6
const DEPTH := 0.111
const WIDTH := 0.094
## How many points a barbel's rope has, as the shader has it.
const POINTS := 8
## The eight barbels, as the model has them (the build script prints these lines): where each
## is rooted, the way it leaves the head, the way it runs further out, how long it is and how
## thick at its root (its own space, metres). 0 and 1 the long ones at the corners of the
## mouth (its left, its right), 2 and 3 the outer chin ones, 4 and 5 the inner chin ones, 6
## and 7 the short ones at the nostrils.
const BARBELS := [
	[Vector3(0.03254, -0.02794, -0.26981), Vector3(0.800, -0.300, 0.520), Vector3(0.382, -0.623, 0.683), 0.115, 0.0021],
	[Vector3(-0.03254, -0.02794, -0.26981), Vector3(-0.800, -0.300, 0.520), Vector3(-0.382, -0.623, 0.683), 0.115, 0.0021],
	[Vector3(0.01350, -0.03422, -0.27560), Vector3(0.320, -0.849, 0.420), Vector3(0.158, -0.592, 0.790), 0.052, 0.0013],
	[Vector3(-0.01350, -0.03422, -0.27560), Vector3(-0.320, -0.849, 0.420), Vector3(-0.158, -0.592, 0.790), 0.052, 0.0013],
	[Vector3(0.00480, -0.03341, -0.27860), Vector3(0.100, -0.902, 0.421), Vector3(0.050, -0.599, 0.799), 0.036, 0.0011],
	[Vector3(-0.00480, -0.03341, -0.27860), Vector3(-0.100, -0.902, 0.421), Vector3(-0.050, -0.599, 0.799), 0.036, 0.0011],
	[Vector3(0.01250, -0.00179, -0.27300), Vector3(0.411, 0.874, -0.257), Vector3(0.508, 0.609, 0.609), 0.024, 0.0010],
	[Vector3(-0.01250, -0.00179, -0.27300), Vector3(-0.411, 0.874, -0.257), Vector3(-0.508, 0.609, 0.609), 0.024, 0.0010],
]
## The front of the body's outline, as the model has it (metres behind the snout; the height
## of its back, of its belly, half its width, the height it is widest at): what the barbels
## lie against.
const OUTLINE := [
	[0, -0.02, -0.02, 0, -0.02],
	[0.0015, -0.0145, -0.025, 0.0125, -0.0205],
	[0.005, -0.0112, -0.0285, 0.0205, -0.021],
	[0.012, -0.007, -0.032, 0.0282, -0.0215],
	[0.024, -0.0015, -0.0365, 0.0342, -0.022],
	[0.042, 0.005, -0.0415, 0.0388, -0.022],
	[0.066, 0.0135, -0.0465, 0.043, -0.021],
	[0.09, 0.0215, -0.0505, 0.0456, -0.019],
	[0.132, 0.034, -0.0555, 0.047, -0.014],
	[0.18, 0.0455, -0.0595, 0.0442, -0.008],
	[0.24, 0.0508, -0.06, 0.0398, -0.0035],
]
## The lower jaw, as the shader has it: where it hinges (metres behind the snout, metres up: the
## corners of the mouth), where it ends at the belly (metres behind the snout), and how far it
## swings down for `gape` 1 (radians). The chin's barbels (2 to 5) are rooted on it.
const HINGE := Vector2(0.031, -0.02794)
const MOUTH_TO := 0.031
const JAW_BACK := 0.043
const GAPE_TURN := 0.55
## The sharpest a barbel may bend from one piece to the next (radians): a barbel has a
## stiff core, so it curves and never kinks (but where the head turns it aside, that wins).
const BEND := 0.4
## The furthest a barbel may swing, at its root, from the way it leaves the head at rest.
const ROOT_BEND := 0.55

## Seconds one beat takes: everything it does comes round again each beat. 0, and `step`
## leaves `phase` to the caller.
@export var beat := 3.0
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it swims: 1 a catfish cruising slowly (its tail tips swing about 0.05 m either
## way, its snout 7 mm), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How long the wave along its body is, in body lengths.
@export var wave := 0.95:
	set(value):
		wave = maxf(value, 0.1)
		_send(&"wave", wave)
## How far its mouth is open: 0 shut (as it always was before 2026-11-17), 1 wide open (its
## lower jaw swung down about the corners of the mouth, the front of the lower lip about 0.013 m,
## the chin's barbels with it; the inside of the mouth is dark).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
		if not _swings and _laid:
			lay_ropes()
## The low model (about a twelfth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 2,960 triangles, spent on the outline, the eye, the mouth and the
## fins' edges; its barbels the same ropes) in place of the full one; `low` still shows the
## low model. Each model is loaded only when it is first shown, so with `game` on the full
## model is never loaded and a game's web export can leave its .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as it was, 1 the cartoon eye: bigger, a white, a pale gold
## iris, a level bar of a pupil, a highlight, a heavy sleepy lid). Gulp sets it to 1.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where the cartoon eye's pupil looks: x forward (towards the snout), y up, -1..1.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## 0 open, 1 shut: the eye squashes and a lid closes over it (a fish has no lids:
## this is for a game that wants one).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How much the barbels stir of themselves as they trail, for 1 as a catfish feeling its way.
## The stirring comes round with each beat.
@export var wander := 1.0
## The barbels' weight. How much the water slows them (/s: the more, the less they flick and
## the further they are left behind); how strongly each is drawn back to its rest (/s², all
## of it at the root, a quarter of it at the tip: a barbel is held out, not hung); how fast they
## sink (m/s², straight down in the world).
## How long the barbels are, for 1 as the model (and a real catfish) has them. More than 1 is for
## small or pixelled pictures, where real ones are too short and fine to be seen.
@export var barbel_long := 1.0
@export var barbel_drag := 8.0
@export var barbel_hold := 45.0
@export var barbel_sink := 0.04
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()
		if not _swings and _laid:
			lay_ropes()

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
static var _meshes := {}
# The ropes: every barbel's points one after another (world), where each was a step ago, and
# the picture that carries them to the shader (a row of points a barbel, then a row a barbel
# of which way is "side" at each point).
var _ropes := PackedVector3Array()
var _ropes_before := PackedVector3Array()
var _rope_data := PackedFloat32Array()
var _rope_picture: ImageTexture
var _laid := false
var _swings := false
var _was_at := Vector3.ZERO


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER


func _ready() -> void:
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"wave", wave)
	_send(&"gape", gape)
	lay_ropes()


## Each frame, after putting it where it is: moves it on through its beat (unless `beat` is
## 0: then `phase` is the caller's to set) and swings its barbels, which follow however it has
## been moved and turned since the last step. `velocity` (world, m/s) is how fast it is going
## through the water: where that is more than it has really moved (one held on the spot in a
## picture, in water that runs past it), the barbels are carried back by the difference; give
## Vector3.ZERO when there is nothing to add.
func step(velocity: Vector3, delta: float) -> void:
	delta = minf(delta, 0.05)
	_swings = true
	if beat > 0.0:
		phase += delta / beat
	if not is_inside_tree():
		return
	if not is_visible_in_tree():
		# (unseen, its barbels are not worked out: they are laid afresh when it is next seen)
		_laid = false
	elif not _laid or global_position.distance_to(_was_at) > 2.0 * LENGTH * _size():
		lay_ropes()
	elif delta > 0.0:
		_swing_ropes(velocity, delta)
		_send_ropes()


## For a picture that loops: runs the barbels in, so that the first frame is already in the
## round the rest will keep to. Call it once, after placing the catfish and setting `phase` to
## the first frame's, with the `velocity` and `delta` each frame's `step` will be given and how
## far `phase` moves on each frame; it works through `beats` beats that end one frame before
## `phase` (so the next `step` is the first frame's). It takes the catfish to stay where it is;
## for one that is moved through the loop, run the loop once through before the first frame.
func settle(velocity: Vector3, delta: float, phase_step: float, beats := 4.0) -> void:
	if not is_inside_tree() or phase_step <= 0.0:
		return
	var to := phase
	_swings = true
	lay_ropes()
	for i in range(maxi(roundi(beats / phase_step), 1), 0, -1):
		phase = to - i * phase_step
		_swing_ropes(velocity, minf(delta, 0.05))
	phase = to
	_send_ropes()


## Lays every barbel afresh, at rest on the head where it is now (after putting the catfish
## somewhere new all at once: its barbels would otherwise be dragged there from where it was).
func lay_ropes() -> void:
	if not is_inside_tree():
		return
	if _ropes.is_empty():
		_ropes.resize(BARBELS.size() * POINTS)
		_ropes_before.resize(BARBELS.size() * POINTS)
		_rope_data.resize(BARBELS.size() * 2 * POINTS * 4)
	var size := _size()
	for k in BARBELS.size():
		var barbel: Array = BARBELS[k]
		var piece: float = float(barbel[3]) * barbel_long * size / (POINTS - 1)
		var held := _held(barbel, k >= 2 and k <= 5)
		var rest: Vector3 = held[0]
		for i in POINTS:
			if i > 0:
				rest += _rest_way(held, float(i) / (POINTS - 1)) * piece
			_ropes[k * POINTS + i] = rest
			_ropes_before[k * POINTS + i] = rest
	_laid = true
	_was_at = global_position
	_send_ropes()


## Where `s` (0 root .. 1 tip) along barbel `which` (0 to 7: see BARBELS) is now, in the world:
## on its rope, on the same curve the shader lays it along.
func barbel_point(which: int, s: float) -> Vector3:
	if not _laid:
		lay_ropes()
	var base := which * POINTS
	var f := clampf(s, 0.0, 1.0) * (POINTS - 1)
	var i := mini(int(f), POINTS - 2)
	var t := f - i
	var p0 := _ropes[base + maxi(i - 1, 0)]
	var p1 := _ropes[base + i]
	var p2 := _ropes[base + i + 1]
	var p3 := _ropes[base + mini(i + 2, POINTS - 1)]
	return 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * (p1 - p2) + p3 - p0) * t * t * t)


## How far outside the skin of the head and chest the point `at` (world) is, in the
## catfish's own metres (less than 0: inside it). What keeps the barbels out of the head.
func clear_of_body(at: Vector3) -> float:
	var p := _unbent(global_transform.affine_inverse() * at)
	var shape := _shape_at(p.z + LENGTH * 0.5)
	return (_roundness(p, shape, 0.0) - 1.0) * minf(shape[2], shape[0] - shape[1])


## Sets one of the shader's settings: its colours (`back`, `back_blue`, `side`, `belly`,
## `spot`, `lip`, `fin`, `fin_edge`, `fin_pale`, `barbel`, `barbel_chin`, `iris`, `mouth_inside`)
## and `spots_show` (how strongly its spots show: 0 a big old slate one). (`sway`, `wave` and
## `gape` given here set the node's own, so that its barbels keep up.)
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	if setting == &"sway" or setting == &"wave" or setting == &"gape":
		set(setting, value)
	else:
		_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if not is_inside_tree():
		return
	# (each model is made only when it is first shown)
	if low:
		if _low == null:
			_low = _mesh_of("_lo")
	elif game:
		if _game == null:
			_game = _mesh_of("_game")
	elif _full == null:
		_full = _mesh_of("")
	if _full:
		_full.visible = not low and not game
	if _low:
		_low.visible = low
	if _game:
		_game.visible = game and not low


## The game model's mesh, for a game that draws meshes itself (with `material()`'s shader,
## which lays the barbels along the ropes this node works out). Loaded once and kept,
## without the importer's thinned LOD meshes.
static func game_mesh() -> Mesh:
	return _load_mesh("_game")


static func _load_mesh(suffix: String) -> Mesh:
	var path := MODEL % suffix
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if suffix == "_game" else found.mesh
		made.free()
	return _meshes[path]


## The mesh without the thinned LOD meshes Godot's importer makes: the shader bends the
## fish, and a thinned mesh far off would bend in straight pieces.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


func _mesh_of(suffix: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = _load_mesh(suffix)
	mesh.material_override = _material
	# (its tail and its barbels swing out past the still model's box)
	mesh.extra_cull_margin = LENGTH * 0.4
	mesh.name = "Catfish" + suffix
	add_child(mesh)
	return mesh


func _size() -> float:
	return maxf(global_basis.get_scale().x, 0.0001)


## How far to one side the middle line of the body is, `xm` metres behind the snout (its own
## metres): the shader's `side_at`.
func _side_at(xm: float) -> float:
	var s := xm / LENGTH
	var reach := LENGTH * (0.012 - 0.04 * s + 0.118 * s * s)
	return sway * reach * sin(TAU * (fposmod(phase * tail_beats, 1.0) - s / wave))


## How far the body's line is turned at `xm` (radians, about its back): the shader's `turn`
## (which takes the slope across 8 mm; this is the slope itself).
func _turn_at(xm: float) -> float:
	var s := xm / LENGTH
	var angle := TAU * (fposmod(phase * tail_beats, 1.0) - s / wave)
	return atan(sway * ((-0.04 + 0.236 * s) * sin(angle) - (0.012 - 0.04 * s + 0.118 * s * s) * TAU / wave * cos(angle)))


## A point of the still model (its own space) where the body's wave has it now, as the shader
## puts it; and back again.
func _bent(p: Vector3) -> Vector3:
	var xm := p.z + LENGTH * 0.5
	var turn := _turn_at(xm)
	return Vector3(_side_at(xm) + p.x * cos(turn), p.y, p.z - p.x * sin(turn))


func _unbent(p: Vector3) -> Vector3:
	var xm := p.z + LENGTH * 0.5
	var turn := _turn_at(xm)
	var x := (p.x - _side_at(xm)) / cos(turn)
	return Vector3(x, p.y, p.z + x * sin(turn))


## A barbel's root and the frame its rest is in, now (world): [root, the basis that turns its
## ways from the still model's to the world's]. One `on_jaw` (the chin's) goes down with the
## lower jaw as the mouth opens, as the shader swings the jaw.
func _held(barbel: Array, on_jaw := false) -> Array:
	var root: Vector3 = barbel[0]
	var jaw := Basis.IDENTITY
	if on_jaw and gape > 0.0:
		var xm := root.z + LENGTH * 0.5
		jaw = Basis(Vector3.RIGHT, -gape * GAPE_TURN * (1.0 - smoothstep(MOUTH_TO - 0.005, JAW_BACK, xm)))
		var hinge := Vector3(0.0, HINGE.y, HINGE.x - LENGTH * 0.5)
		root = hinge + jaw * (root - hinge)
	var turned := global_basis.orthonormalized() * Basis(Vector3.UP, _turn_at(root.z + LENGTH * 0.5)) * jaw
	return [global_transform * _bent(root), turned, barbel]


## The way a barbel's rest runs `share` (0 root .. 1 tip) along it (world, a unit): the way it
## leaves the head, turning to the way it trails further out.
func _rest_way(held: Array, share: float) -> Vector3:
	var barbel: Array = held[2]
	return (held[1] as Basis) * (barbel[1] as Vector3).lerp(barbel[2], smoothstep(0.0, 0.6, share)).normalized()


## The body's outline at `xm` metres behind the snout: [the height of its back, of its belly,
## half its width, the height it is widest at] (its own metres).
func _shape_at(xm: float) -> PackedFloat64Array:
	xm = clampf(xm, 0.0, OUTLINE[-1][0])
	var i := 0
	while i < OUTLINE.size() - 2 and xm > OUTLINE[i + 1][0]:
		i += 1
	var a: Array = OUTLINE[i]
	var b: Array = OUTLINE[i + 1]
	var t: float = (xm - a[0]) / (b[0] - a[0])
	return PackedFloat64Array([lerpf(a[1], b[1], t), lerpf(a[2], b[2], t), lerpf(a[3], b[3], t), lerpf(a[4], b[4], t), xm])


## How far out from the body's middle `p` (the still model's space) is, as a share of the way
## to its skin there, the skin taken `margin` further out (1 on it, less inside). The
## cross-section is the model's: a flattened, squarish egg.
func _roundness(p: Vector3, shape: PackedFloat64Array, margin: float) -> float:
	var square := smoothstep(0.05, 0.22, shape[4])
	var above: bool = p.y >= shape[3]
	var power := 2.0 / ((0.8 + 0.16 * square) if above else (0.62 + 0.3 * square))
	var high: float = ((shape[0] - shape[3]) if above else (shape[3] - shape[1])) + margin
	var u := absf(p.x) / (shape[2] + margin)
	var v: float = absf(p.y - shape[3]) / maxf(high, 0.0005)
	return pow(pow(u, power) + pow(v, power), 1.0 / power)


## A step of the ropes (Verlet): each point keeps going as it was, slowed by the water, drawn
## back towards its rest on the head (four times as strongly at its root as at its tip), stirred a
## little, sinking; then each rope is held to its length from its root out, kept from kinking
## and kept outside the head. The water stands still in the world, but for `velocity` more than
## the catfish has really moved: that much runs past it the other way and carries them with it.
func _swing_ropes(velocity: Vector3, delta: float) -> void:
	var size := _size()
	var keep := exp(-barbel_drag * delta)
	var water := Vector3.ZERO
	if velocity != Vector3.ZERO:
		water = (global_position - _was_at) / delta - velocity
	_was_at = global_position
	var carried := water * delta * (1.0 - keep)
	var angle := phase * TAU
	var sink := Vector3.DOWN * barbel_sink * size * delta * delta
	var to_local := global_transform.affine_inverse()
	for k in BARBELS.size():
		var barbel: Array = BARBELS[k]
		var base := k * POINTS
		var long: float = float(barbel[3]) * barbel_long
		var piece: float = long * size / (POINTS - 1)
		var held := _held(barbel, k >= 2 and k <= 5)
		var rest: Vector3 = held[0]
		var turned: Basis = held[1]
		var own := k * 2.399
		_ropes[base] = rest
		_ropes_before[base] = rest
		for i in range(1, POINTS):
			var p := _ropes[base + i]
			var share := float(i) / (POINTS - 1)
			rest += _rest_way(held, share) * piece
			var pull := (rest - p) * barbel_hold * (1.0 - 0.75 * smoothstep(0.0, 0.9, share))
			# (stirred: a slow feeling about that comes back with each beat, each barbel at its own time)
			var stir := turned * Vector3(sin(angle + own + share * 3.0), cos(angle * 2.0 + own * 1.7 + share * 2.0), 0.0) * 1.6 * long * wander * size * share
			var moved := (p - _ropes_before[base + i]) * keep + carried + (pull + stir) * delta * delta + sink
			_ropes_before[base + i] = p
			_ropes[base + i] = p + moved
		# Held to length from the root out (twice over, so that it settles), kept from
		# kinking and kept out of the head. A point moved for those last two is put there,
		# not thrown there: it gets no speed from it.
		for again in 2:
			var before := _rest_way(held, 0.0)
			for i in range(1, POINTS):
				var from := _ropes[base + i - 1]
				var way := _ropes[base + i] - from
				var far := way.length()
				way = way / far if far > 0.000001 else before
				var put := from + way * piece
				var thrown := put
				var over := way.angle_to(before) - (BEND if i > 1 else ROOT_BEND)
				if over > 0.0:
					var about := way.cross(before)
					if about.length() > 0.00001:
						way = way.rotated(about.normalized(), over)
						put = from + way * piece
				for tries in 3 * again:
					var clear := _outside(put, to_local, 0.0012 + float(barbel[4]))
					if clear == put or clear.distance_to(from) < 0.000001:
						break
					way = (clear - from).normalized()
					put = from + way * piece
				_ropes_before[base + i] += put - thrown
				_ropes[base + i] = put
				before = way


## `at` (world), moved out to the skin of the head and chest if it is inside it (`margin`
## clear of it, in its own metres).
func _outside(at: Vector3, to_local: Transform3D, margin: float) -> Vector3:
	var bent := to_local * at
	if bent.z > OUTLINE[-1][0] - LENGTH * 0.5 or bent.z < -LENGTH * 0.5 - 0.02:
		return at
	var p := _unbent(bent)
	var shape := _shape_at(p.z + LENGTH * 0.5)
	var share := _roundness(p, shape, margin)
	if share >= 1.0 or share < 0.0001:
		return at
	# (straight out from the middle of the body's cross-section there)
	var out := Vector3(p.x, p.y - shape[3], 0.0) * (1.0 / share - 1.0)
	return global_transform * _bent(p + out)


## The ropes to the shader: a picture, a row a barbel of its points, then a row a barbel of
## which way is "side" at each point (carried along the rope with the least turning), in the
## catfish's own space.
func _send_ropes() -> void:
	var to_local := global_transform.affine_inverse()
	var turn_back := global_basis.orthonormalized().inverse()
	for k in BARBELS.size():
		var base := k * POINTS
		var at := k * POINTS * 4
		var side_at := (BARBELS.size() + k) * POINTS * 4
		var before := (_ropes[base + 1] - _ropes[base]).normalized()
		var side := before.cross(global_basis.y if k < 2 else global_basis.x).normalized()
		for i in POINTS:
			var p := to_local * _ropes[base + i]
			_rope_data[at] = p.x
			_rope_data[at + 1] = p.y
			_rope_data[at + 2] = p.z
			at += 4
			var way := (_ropes[mini(base + i + 1, base + POINTS - 1)] - _ropes[maxi(base + i - 1, base)]).normalized()
			var axis := before.cross(way)
			side = side + axis.cross(side) + axis.cross(axis.cross(side)) / (1.0 + maxf(before.dot(way), -0.98))
			side = (side - way * side.dot(way)).normalized()
			before = way
			var s := turn_back * side
			_rope_data[side_at] = s.x
			_rope_data[side_at + 1] = s.y
			_rope_data[side_at + 2] = s.z
			side_at += 4
	var image := Image.create_from_data(POINTS, BARBELS.size() * 2, false, Image.FORMAT_RGBAF, _rope_data.to_byte_array())
	if _rope_picture == null:
		_rope_picture = ImageTexture.create_from_image(image)
		_send(&"ropes", _rope_picture)
	else:
		_rope_picture.update(image)
