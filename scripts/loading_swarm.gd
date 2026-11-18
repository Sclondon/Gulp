class_name LoadingSwarm
extends Control
## The loading screen (the user, 2026-11-18: "the loading screen needs to be a swarm of sardines
## making up the wayside interactive logo sequence while it loads", then, of a first version drawn
## with flat fish shapes, "it needs to be actual sardines making the wayside logo in the
## loading"): a school of the game's own sardines circles in dark water; as loading goes on
## (`progress`, 0..1) they peel off, each to its own place in the Wayside Interactive logo, taking
## that place's colour, until the whole mark is made of fish holding station and swimming on the
## spot. `finish()` scatters them and fades it out, then `done` is sent and it frees itself.
##
## The places and colours are read from a small copy of the logo
## (textures/loading/wayside_mark_58.png; the full ones are in tools/art_src). The fish are the
## sardine's school model (Sardine.school_mesh, about 220 triangles, its look in its vertex
## colours), some hundreds of them in one MultiMesh, big enough to be seen for what they are, drawn with the schools' own shader
## (flock/flock.gdshader: no new shader program, and the one the game's schools need is compiled
## here first). They are in a small world of their own (a SubViewport, as the control panel is),
## seen straight on by a camera without perspective, a unit of that world being a pixel of the
## screen.

signal done

const LOGO := "res://textures/loading/wayside_mark_58.png"
## The words under the mark ("WAYSIDE INTERACTIVE"), which are too fine to spell in fish: the
## logo's own lettering, shown as the last fish settle.
const WORDS := "res://textures/loading/wayside_words.png"
## A place is kept for every other pixel brighter than this.
const LIT := 0.16
## The sardine model's length (m).
const MODEL_LONG := 0.22
## How far each fish is rolled towards the eye (so its back and its beating tail show).
const ROLL := 0.6

## How much is loaded (0..1): that share of the fish have gone to their places.
var progress := 0.0

var _view: SubViewport
var _eye: Camera3D
var _school: MultiMesh
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
var _big := 1.0
var _words: Texture2D


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var logo := (load(LOGO) as Texture2D).get_image()
	if logo.is_compressed():
		logo.decompress()
	_span = Vector2(logo.get_width(), logo.get_height())
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for y in logo.get_height():
		for x in logo.get_width():
			var colour := logo.get_pixel(x, y)
			# (every other pixel, as on a chequer board: a fish is longer than a pixel)
			if (x + y) % 2 == 0 and colour.a > 0.5 and maxf(colour.r, maxf(colour.g, colour.b)) > LIT:
				_home.append(Vector2(x + 0.5, y + 0.5))
				_tint.append(Color(colour.r, colour.g, colour.b))
				# (the mark fills from its middle outwards, with some shuffle)
				var out := Vector2(x, y).distance_to(_span * 0.5) / _span.y
				_rank.append(clampf(out * 0.9 + rng.randf() * 0.25, 0.0, 0.98))
				_seed.append(rng.randf())
				_at.append(Vector2.ZERO)
				_way.append(0.0)
				_settled.append(0.0)
	_words = load(WORDS)
	_view = SubViewport.new()
	_view.own_world_3d = true
	_view.size = Vector2i(_wide)
	_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_view)
	var air := Environment.new()
	air.background_mode = Environment.BG_COLOR
	air.background_color = Color(0.012, 0.035, 0.07)
	air.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	air.ambient_light_color = Color(0.85, 0.92, 1.0)
	air.ambient_light_energy = 0.75
	var world := WorldEnvironment.new()
	world.environment = air
	_view.add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(-0.9, 0.5, 0.0)
	sun.light_energy = 1.1
	_view.add_child(sun)
	_eye = Camera3D.new()
	_eye.projection = Camera3D.PROJECTION_ORTHOGONAL
	_eye.near = 1.0
	_eye.far = 4000.0
	_view.add_child(_eye)
	_school = MultiMesh.new()
	_school.transform_format = MultiMesh.TRANSFORM_3D
	_school.use_colors = true
	_school.use_custom_data = true
	# (without Godot's automatic far-off versions of the mesh: seen this small it would draw the
	# crudest of them, a few spikes)
	_school.mesh = Sardine.without_lods(Sardine.school_mesh())
	_school.instance_count = _home.size()
	var fish := MultiMeshInstance3D.new()
	fish.multimesh = _school
	var look := ShaderMaterial.new()
	look.shader = load("res://flock/flock.gdshader")
	look.set_shader_parameter(&"colour", Color.WHITE)
	look.set_shader_parameter(&"motion", 1)
	look.set_shader_parameter(&"amount", 0.5)
	look.set_shader_parameter(&"length_half", MODEL_LONG * 0.5)
	look.set_shader_parameter(&"sheen", 0.5)
	look.set_shader_parameter(&"riders", 0)
	fish.material_override = look
	fish.custom_aabb = AABB(Vector3(-5000.0, -5000.0, -500.0), Vector3(10000.0, 10000.0, 1000.0))
	_view.add_child(fish)
	for k in _home.size():
		_at[k] = _circling(k, 0.0)


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
	if _view.size != Vector2i(_wide):
		_view.size = Vector2i(_wide)
	# (a unit of the fish's world is a pixel: x right, y up from the screen's bottom)
	_eye.size = _wide.y
	_eye.keep_aspect = Camera3D.KEEP_HEIGHT
	_eye.position = Vector3(_wide.x * 0.5, -_wide.y * 0.5, 1000.0)
	_shown = move_toward(_shown, progress, delta * 0.9)
	# (the logo sits in the middle, as big as fits with room round it)
	var big := minf(_wide.x * 0.84 / _span.x, _wide.y * 0.62 / _span.y)
	_big = big
	var corner := _wide * Vector2(0.5, 0.42) - _span * big * 0.5
	var long := big * 3.3
	if _leaving >= 0.0:
		_leaving += delta
		modulate.a = clampf(1.0 - (_leaving - 0.35) / 0.45, 0.0, 1.0)
		if _leaving > 0.85:
			done.emit()
			queue_free()
			return
	for k in _home.size():
		var was := _at[k]
		var colour := Color(0.8, 0.88, 0.95)
		var effort := 1.0
		if _leaving >= 0.0:
			# (away from the middle, fast)
			var out := was - _wide * 0.5
			out = out.normalized() if out.length() > 1.0 else Vector2.from_angle(_seed[k] * TAU)
			_at[k] = was + (out + Vector2.from_angle(_seed[k] * TAU) * 0.5) * delta * _wide.length() * 1.5
			colour = colour.lerp(_tint[k] * 1.5, _settled[k])
		else:
			var placed := _shown > _rank[k]
			_settled[k] = move_toward(_settled[k], 1.0 if placed else 0.0, delta * 1.4)
			var home := corner + _home[k] * big + Vector2(sin(_clock * 2.3 + _seed[k] * 30.0), cos(_clock * 1.9 + _seed[k] * 17.0)) * big * 0.12
			var eased := smoothstep(0.0, 1.0, _settled[k])
			_at[k] = was.lerp(_circling(k, _clock).lerp(home, eased), 1.0 - exp(-9.0 * delta))
			colour = colour.lerp(_tint[k] * 1.5, eased)
			effort = lerpf(1.0, 0.45, eased)
		# (it faces the way it goes; in its place, to the right or the left by rows, as fish
		# holding against a current)
		var going := _at[k] - was
		var facing := going.angle() if going.length() > big * 0.03 else (0.0 if int(_home[k].y) % 2 == 0 else PI) + sin(_clock * 1.3 + _seed[k] * 50.0) * 0.12
		_way[k] = lerp_angle(_way[k], facing, 1.0 - exp(-10.0 * delta))
		# (the model's nose is -Z and its back +Y: its nose along the way it goes on the screen,
		# its flank to the eye, rolled a little so the back and the tail's beat show)
		var ahead := Vector3(cos(_way[k]), -sin(_way[k]), 0.0)
		var flank := Vector3(0.0, 0.0, 1.0 if ahead.x >= 0.0 else -1.0)
		var up := (-ahead).cross(flank)
		var lean := Basis(ahead, ROLL * (1.0 if ahead.x >= 0.0 else -1.0))
		var frame := lean * Basis(flank, up, -ahead)
		var scaled := frame.scaled(Vector3.ONE * (long / MODEL_LONG))
		_school.set_instance_transform(k, Transform3D(scaled, Vector3(_at[k].x, -_at[k].y, _seed[k] * 40.0)))
		_school.set_instance_color(k, colour)
		_school.set_instance_custom_data(k, Color(_clock * (11.0 + _seed[k] * 5.0) + _seed[k] * 20.0, effort, 0.0, 0.0))
	queue_redraw()


func _draw() -> void:
	draw_texture_rect(_view.get_texture(), Rect2(Vector2.ZERO, _wide), false)
	# (the lettering, under the mark, as the last of the fish find their places)
	var lit := smoothstep(0.8, 1.0, _shown)
	if lit > 0.0 and _words:
		var across := _span.x * _big * 1.18
		var high := across * _words.get_height() / _words.get_width()
		draw_texture_rect(_words, Rect2(Vector2(_wide.x * 0.5 - across * 0.5, _wide.y * 0.42 + _span.y * _big * 0.5 + high * 0.02), Vector2(across, high)), false, Color(1.0, 1.0, 1.0, lit))
