class_name LoadingSwarm
extends Control
## The loading screen (the user, 2026-11-18: "the loading screen needs to be a swarm of sardines
## making up the wayside interactive logo sequence while it loads"): a school of sardines circles
## in dark water; as loading goes on (`progress`, 0..1) they peel off a few at a time, each to its
## own place in the Wayside Interactive logo, taking that place's colour, until the whole mark is
## made of fish holding station and shimmering. `finish()` scatters them and fades it out, then
## `done` is sent and it frees itself.
##
## The places and colours are read from a small copy of the logo
## (textures/loading/wayside_stacked_small.png; the full one is in tools/art_src). The fish are
## one MultiMesh of a flat fish shape (a sprite's worth of triangles, made here: this is a drawing
## on the screen, not a model), moved on the CPU: about 2,800 of them.

signal done

const LOGO := "res://textures/loading/wayside_stacked_small.png"
## A place is kept for every pixel brighter than this.
const LIT := 0.16

## How much is loaded (0..1): that share of the fish have gone to their places.
var progress := 0.0

var _fish: MultiMeshInstance2D
var _home := PackedVector2Array()
var _tint := PackedColorArray()
var _at := PackedVector2Array()
var _way := PackedFloat32Array()
var _rank := PackedFloat32Array()
var _seed := PackedFloat32Array()
var _settled := PackedFloat32Array()
var _span := Vector2.ONE
var _clock := 0.0
var _leaving := -1.0
var _shown := 0.0
# The screen's size (its own `size` is not to be trusted before it is laid out).
var _wide := Vector2(1280.0, 720.0)


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var picture := load(LOGO) as Texture2D
	var logo := picture.get_image()
	if logo.is_compressed():
		logo.decompress()
	_span = Vector2(logo.get_width(), logo.get_height())
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for y in logo.get_height():
		for x in logo.get_width():
			var colour := logo.get_pixel(x, y)
			# (every other pixel, as on a chequer board: a fish is wider than a pixel)
			if (x + y) % 2 == 0 and colour.a > 0.5 and maxf(colour.r, maxf(colour.g, colour.b)) > LIT:
				_home.append(Vector2(x + 0.5, y + 0.5))
				_tint.append(Color(colour.r, colour.g, colour.b))
				# (the mark fills from its middle outwards, with some shuffle)
				var out := Vector2(x, y).distance_to(_span * Vector2(0.5, 0.4)) / _span.y
				_rank.append(clampf(out * 0.9 + rng.randf() * 0.25, 0.0, 0.98))
				_seed.append(rng.randf())
				_at.append(Vector2.ZERO)
				_way.append(0.0)
				_settled.append(0.0)
	var count := _home.size()
	var school := MultiMesh.new()
	school.transform_format = MultiMesh.TRANSFORM_2D
	school.use_colors = true
	school.mesh = _shape()
	school.instance_count = count
	_fish = MultiMeshInstance2D.new()
	_fish.multimesh = school
	add_child(_fish)
	for k in count:
		_at[k] = _circling(k, 0.0)


# A fish seen from the side, a unit long, nose to +x: a body and a forked tail.
func _shape() -> ArrayMesh:
	var points := PackedVector2Array([
		Vector2(0.5, 0.0), Vector2(0.2, 0.17), Vector2(-0.15, 0.13), Vector2(-0.32, 0.03),
		Vector2(-0.5, 0.2), Vector2(-0.43, 0.0), Vector2(-0.5, -0.2), Vector2(-0.32, -0.03),
		Vector2(-0.15, -0.13), Vector2(0.2, -0.17)])
	var corners := PackedVector2Array()
	for k in range(1, points.size() - 1):
		corners.append(points[0])
		corners.append(points[k])
		corners.append(points[k + 1])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = corners
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


# Where a fish is while it circles with the school: a wide ring turning round the middle, each
# fish on its own lap and depth of the ring.
func _circling(k: int, time: float) -> Vector2:
	var middle := _wide * 0.5
	var reach := minf(_wide.x, _wide.y) * (0.3 + 0.16 * sin(_seed[k] * 40.0 + time * 0.6))
	var turn := _seed[k] * TAU * 3.0 + time * (0.9 + 0.4 * fmod(_seed[k] * 7.0, 1.0))
	return middle + Vector2(cos(turn) * 1.25, sin(turn) * 0.8) * reach


## The loading is over: the fish scatter and the screen clears.
func finish() -> void:
	if _leaving < 0.0:
		_leaving = 0.0


func _process(delta: float) -> void:
	_clock += delta
	_wide = get_viewport_rect().size
	_shown = move_toward(_shown, progress, delta * 0.9)
	# (the logo sits in the middle, as big as fits with room round it)
	var big := minf(_wide.x * 0.8 / _span.x, _wide.y * 0.74 / _span.y)
	var corner := _wide * 0.5 - _span * big * 0.5
	var long := big * 2.3
	var school := _fish.multimesh
	if _leaving >= 0.0:
		_leaving += delta
		modulate.a = clampf(1.0 - (_leaving - 0.35) / 0.45, 0.0, 1.0)
		if _leaving > 0.85:
			done.emit()
			queue_free()
			return
	for k in _home.size():
		var was := _at[k]
		var to: Vector2
		var colour := Color(0.62, 0.74, 0.82)
		if _leaving >= 0.0:
			# (away from the middle, fast)
			var out := (was - _wide * 0.5)
			out = out.normalized() if out.length() > 1.0 else Vector2.from_angle(_seed[k] * TAU)
			to = was + (out + Vector2.from_angle(_seed[k] * TAU) * 0.5) * delta * _wide.length() * 1.5
			_at[k] = to
			colour = colour.lerp(_tint[k], _settled[k])
		else:
			var placed := _shown > _rank[k]
			_settled[k] = move_toward(_settled[k], 1.0 if placed else 0.0, delta * 1.4)
			var home := corner + _home[k] * big + Vector2(sin(_clock * 2.3 + _seed[k] * 30.0), cos(_clock * 1.9 + _seed[k] * 17.0)) * big * 0.14
			var eased := smoothstep(0.0, 1.0, _settled[k])
			to = _circling(k, _clock).lerp(home, eased)
			_at[k] = was.lerp(to, 1.0 - exp(-9.0 * delta))
			colour = colour.lerp(_tint[k], eased)
		# (it faces the way it goes; in its place, to the right, with a shimmer of its tail)
		var going := _at[k] - was
		var facing := going.angle() if going.length() > big * 0.02 else sin(_clock * 6.0 + _seed[k] * 50.0) * 0.25
		_way[k] = lerp_angle(_way[k], facing, 1.0 - exp(-10.0 * delta))
		var squash := 1.0 + 0.12 * sin(_clock * 9.0 + _seed[k] * 60.0)
		school.set_instance_transform_2d(k, Transform2D(_way[k], Vector2(long, long * squash), 0.0, _at[k]))
		school.set_instance_color(k, colour)
	queue_redraw()


func _draw() -> void:
	# (dark water, a little lighter towards the top)
	draw_rect(Rect2(Vector2.ZERO, _wide), Color(0.012, 0.035, 0.07))
	draw_rect(Rect2(Vector2.ZERO, Vector2(_wide.x, _wide.y * 0.5)), Color(0.02, 0.07, 0.12, 0.5))
