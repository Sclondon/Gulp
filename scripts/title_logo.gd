class_name TitleLogo
extends Node3D
## The game's name on the title, spelt in fish (the user, 2026-11-18: "the logo needs to be made up
## of a bunch of our fish models making the letters, trying to eat each other"; the concept
## picture is tools/art_src/concept_fish_logo.jpg): the game's own creatures, nose to tail along
## the strokes of G, U, L and P, each with its mouth open at the tail of the one ahead, swimming
## on the spot, their bodies bent to the letters' curves.
##
## It is drawn in the game's own world (so the fish need no shaders of their own compiled for
## it), held in front of the title's eye: Title puts it there each frame (`hold`). Its own space:
## x along the word, y up, the fish facing +z towards the eye; a letter is about 1 wide and 1.4
## tall; the word is WIDE long.

## Each letter: where it starts along the word, the stroke as points (x, y), and the kinds that
## swim it, first to last (the first is at the stroke's far end: the one being chased).
const LETTERS := [
	{"at": 0.0, "kinds": ["surfperch", "surfperch", "garibaldi", "rockfish", "garibaldi", "rockfish", "kelp_bass", "rockfish", "kelp_bass", "salmon"],
			"stroke": [Vector2(0.52, 0.62), Vector2(0.9, 0.62), Vector2(0.88, 0.22), Vector2(0.55, 0.03), Vector2(0.2, 0.15), Vector2(0.03, 0.5), Vector2(0.05, 0.95), Vector2(0.25, 1.3), Vector2(0.6, 1.38), Vector2(0.9, 1.18)]},
	{"at": 1.3, "kinds": ["surfperch", "garibaldi", "garibaldi", "garibaldi", "garibaldi", "mackerel", "mackerel", "mackerel", "kelp_bass"],
			"stroke": [Vector2(0.95, 1.4), Vector2(0.95, 0.5), Vector2(0.8, 0.14), Vector2(0.5, 0.03), Vector2(0.2, 0.14), Vector2(0.05, 0.5), Vector2(0.05, 1.4)]},
	{"at": 2.6, "kinds": ["mackerel", "kelp_bass", "kelp_bass", "salmon", "salmon"],
			"stroke": [Vector2(0.9, 0.06), Vector2(0.12, 0.06), Vector2(0.1, 0.5), Vector2(0.1, 1.4)]},
	{"at": 3.75, "kinds": ["salmon", "salmon", "tuna", "leopard_shark", "tuna", "tuna"],
			"stroke": [Vector2(0.12, 0.6), Vector2(0.6, 0.62), Vector2(0.92, 0.82), Vector2(0.92, 1.18), Vector2(0.6, 1.38), Vector2(0.1, 1.38), Vector2(0.1, 0.7), Vector2(0.1, 0.0)]},
]
const WIDE := 4.75
## How much deeper than life the fish are drawn.
const DEEP := 1.9
## How long each kind is drawn here (in the logo's units).
const LONG := {"sardine": 0.19, "surfperch": 0.3, "rockfish": 0.36, "garibaldi": 0.36, "mackerel": 0.42, "kelp_bass": 0.5, "salmon": 0.52, "tuna": 0.6, "leopard_shark": 0.72}

var _fish: Array[Node3D] = []
var _clock := 0.0


func _ready() -> void:
	for letter: Dictionary in LETTERS:
		var stroke: Array = letter.stroke
		# (how far along the stroke each fish's middle is: packed nose to tail from its far end back)
		var along := 0.0
		for kind: String in letter.kinds:
			if not Species.has(kind):
				continue
			var long: float = LONG.get(kind, 0.4)
			var middle := along + long * 0.5
			along += long * 0.94
			var here := _on(stroke, middle)
			var ahead := (_on(stroke, middle - 0.05) - _on(stroke, middle + 0.05)).normalized()
			var look := Species.make(kind)
			if look == null:
				continue
			if &"game" in look:
				look.set(&"game", true)
			if &"cartoon_eyes" in look:
				look.set(&"cartoon_eyes", 1.0)
			var holder := Node3D.new()
			# (its nose, -z, along the stroke towards the one ahead; a flank to the eye; upright as
			# near as the stroke lets it)
			var forward := Vector3(ahead.x, ahead.y, 0.0)
			var side := Vector3(0.0, 0.0, 1.0 if forward.x <= 0.0 else -1.0)
			var up := side.cross(forward).normalized()
			if up.y < 0.0 and absf(forward.x) < 0.3:
				side = -side
				up = -up
			# (drawn deeper than life, so the letters are thick enough to read)
			var fit := long / Species.long_of(kind, look)
			holder.basis = Basis(side * fit * 1.3, up * fit * DEEP, -forward * fit)
			holder.position = Vector3(float(letter.at) + here.x, here.y, 0.0)
			look.rotation.y = float(Species.of(kind).get("turn", 0.0))
			holder.add_child(look)
			add_child(holder)
			# (bent to the stroke: which way and how sharply it turns just here, as the fish sees it)
			var before := (_on(stroke, middle + long * 0.4) - _on(stroke, middle + long * 0.4 + 0.05)).normalized()
			var after := (_on(stroke, middle - long * 0.4 - 0.05) - _on(stroke, middle - long * 0.4)).normalized()
			var bend := clampf(before.angle_to(after) * (1.0 if side.z > 0.0 else -1.0), -1.0, 1.0)
			if look.has_method(&"set_shader_parameter") and bool(Species.of(kind).get("curls", true)):
				look.call(&"set_shader_parameter", &"curl", -bend * 0.7)
			_fish.append(look)


# The point a distance along a stroke (it stops at the stroke's end).
func _on(stroke: Array, far: float) -> Vector2:
	var left := maxf(far, 0.0)
	for k in range(1, stroke.size()):
		var a: Vector2 = stroke[k - 1]
		var b: Vector2 = stroke[k]
		var long := a.distance_to(b)
		if left <= long or k == stroke.size() - 1:
			return a.lerp(b, left / maxf(long, 0.001))
		left -= long
	return stroke[-1]


func _process(delta: float) -> void:
	_clock += delta
	for k in _fish.size():
		var look := _fish[k]
		if look.has_method(&"step"):
			look.call(&"step", Vector3.ZERO, delta)
		# (each snaps at the one ahead in its own time)
		var wide := 0.35 + 0.65 * maxf(sin(_clock * 3.2 + k * 1.9), 0.0)
		if &"gape" in look:
			look.set(&"gape", wide)
		elif look.has_method(&"set_shader_parameter"):
			look.call(&"set_shader_parameter", &"gape", 0.07 + wide * 0.55)


## Holds it in front of an eye (the eye's place in the world): across the top of what the eye
## sees, small enough to fit an upright window.
func hold(eye: Transform3D, upright: bool) -> void:
	var far := 6.0
	# (what the eye sees across at that distance: its lens is 60 degrees up and down in a wide
	# window, 72 in an upright one, about 0.46 as wide as tall)
	var across := 2.0 * far * tan(deg_to_rad(36.0)) * 0.46 if upright else 2.0 * far * tan(deg_to_rad(30.0)) * 1.78
	var big := across * (0.88 if upright else 0.6) / WIDE
	var foot := far * tan(deg_to_rad(36.0 if upright else 30.0)) - 1.4 * big - (0.45 if upright else 0.3)
	global_transform = eye * Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * big), Vector3(-WIDE * big * 0.5, foot, -far))
