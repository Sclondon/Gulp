class_name Hud
extends Control
## What is shown over the sea: along the top, the fish the player grows through (a row of
## outlines, each bigger than the last, lit up to the one it is now), a bar of how far it has
## eaten towards the next, and how long it is; red round the edges while something hunts it;
## and when the run is over, what it got to, how long it was, the longest so far, and a round
## button to start again. Symbols and numbers only.

signal restart
## One of the things the player can become was picked.
signal picked(kind: String)

var player: Player
## How hard it is being hunted (0..1), eased by Main.
var danger := 0.0
## The run is over.
var over := false: set = set_over
## The longest the player has been in any run (metres), and in this one.
var best := 0.0
var reached := 0.0
## The shared sea's high scores, when online: each [name, length, kind], longest first.
var scores: Array = []

var _again: AgainButton
var _clock := 0.0
var _grown := 0.0
var _cards: Array[ChoiceCard] = []


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_again = AgainButton.new()
	_again.focus_mode = Control.FOCUS_NONE
	_again.visible = false
	_again.pressed.connect(func() -> void: restart.emit())
	add_child(_again)


func set_over(to: bool) -> void:
	over = to
	if _again:
		_again.visible = to


## The player has just become the next fish.
func grew() -> void:
	_grown = 1.0


func _process(delta: float) -> void:
	_clock += delta
	_grown = maxf(_grown - delta * 0.8, 0.0)
	var u := minf(size.x, size.y) / 720.0
	_again.size = Vector2(190.0, 190.0) * u
	_again.position = Vector2(size.x * 0.5, size.y * 0.5 + 150.0 * u) - _again.size * 0.5
	_lay_cards(u)
	queue_redraw()


func _draw() -> void:
	if player == null:
		return
	var u := minf(size.x, size.y) / 720.0
	var font := get_theme_default_font()
	var ink := Color(0.85, 0.95, 1.0)
	# Red round the edges while it is hunted.
	if danger > 0.01 and not over:
		var pulse := danger * (0.35 + 0.15 * sin(_clock * 9.0))
		var deep := 90.0 * u
		# (rings one inside the next, fainter towards the middle)
		for k in 12:
			var inset := deep * (k + 0.5) / 12.0
			var faint := pow(1.0 - k / 12.0, 2.0)
			draw_rect(Rect2(Vector2(inset, inset), size - Vector2(inset, inset) * 2.0), Color(1.0, 0.15, 0.1, pulse * faint), false, deep / 12.0 + 1.0)
	# What it is now: an outline that swells as it grows, and a pip for each time it has become
	# something bigger.
	var top := 46.0 * u
	var wide := minf(size.x - 60.0 * u, 620.0 * u)
	var left := (size.x - wide) * 0.5
	var long := (40.0 + 22.0 * clampf(player.progress, 0.0, 1.0)) * u * (1.0 + 0.35 * _grown)
	_fish(Vector2(left + 34.0 * u, top + 26.0 * u), long, Color(0.55, 1.0, 0.8, 1.0), player.length > 2.5)
	for k in player.stage:
		draw_circle(Vector2(left + 84.0 * u + k * 20.0 * u, top + 26.0 * u), 6.0 * u, Color(ink, 0.9))
	# The bar: how far towards the next (or towards full size, at the last).
	var bar := Rect2(left, top + 66.0 * u, wide, 12.0 * u)
	# (a brass-framed sight glass, as the controls are a submarine's fittings)
	draw_rect(bar.grow(4.0 * u), Color(TouchPad.BRASS_DARK, 0.9))
	draw_rect(bar.grow(4.0 * u), Color(TouchPad.BRASS, 0.95), false, 3.0 * u)
	draw_rect(bar, Color(TouchPad.IRON, 0.85))
	draw_rect(Rect2(bar.position, Vector2(bar.size.x * clampf(player.progress, 0.0, 1.0), bar.size.y)), Color(0.45, 0.95, 0.7, 0.95))
	for k in [0.0, 1.0]:
		draw_circle(Vector2(lerpf(bar.position.x - 4.0 * u, bar.end.x + 4.0 * u, k), bar.get_center().y), 5.0 * u, Color(TouchPad.BRASS_LIGHT, 0.95))
	# How long it is, and the longest so far (under a small crown).
	var text_size := int(30.0 * u)
	draw_string(font, Vector2(left, bar.end.y + 38.0 * u), "%.2f m" % player.length, HORIZONTAL_ALIGNMENT_LEFT, -1.0, text_size, ink)
	if best > 0.0:
		var best_text := "%.2f m" % best
		var best_wide := font.get_string_size(best_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, text_size).x
		var at := Vector2(left + wide - best_wide, bar.end.y + 38.0 * u)
		draw_string(font, at, best_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, text_size, Color(1.0, 0.86, 0.45))
		_crown(at + Vector2(-34.0 * u, -11.0 * u), 22.0 * u, Color(1.0, 0.86, 0.45))
	# The high scores of the shared sea: a crown, then name and length, the longest first.
	if not scores.is_empty():
		var small := int(20.0 * u)
		var line := 26.0 * u
		var right := size.x - 16.0 * u
		var from := bar.end.y + 70.0 * u
		_crown(Vector2(right - 22.0 * u, from - 30.0 * u), 22.0 * u, Color(1.0, 0.86, 0.45))
		for k in mini(scores.size(), 5 if not over else 10):
			var row: Array = scores[k]
			var said := "%s  %.2f m" % [String(row[0]), float(row[1])]
			var said_wide := font.get_string_size(said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, small).x
			draw_string(font, Vector2(right - said_wide, from + k * line), said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, small, Color(ink, 0.85 if k > 0 else 1.0))
	if over:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.02, 0.08, 0.6))
		var middle := Vector2(size.x * 0.5, size.y * 0.5 - 150.0 * u)
		_fish(middle, 150.0 * u, Color(0.55, 1.0, 0.8), player.length > 2.5)
		var big := int(54.0 * u)
		var text := "%.2f m" % reached
		var text_wide := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, big).x
		draw_string(font, Vector2(size.x * 0.5 - text_wide * 0.5, size.y * 0.5 - 10.0 * u), text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, big, ink)


## Shows the things the player can become, each a card to press (none: puts them away).
func offer(kinds: Array) -> void:
	for card in _cards:
		card.queue_free()
	_cards.clear()
	for kind: String in kinds:
		var card := ChoiceCard.new()
		card.kind = kind
		card.focus_mode = Control.FOCUS_NONE
		card.pressed.connect(func() -> void: picked.emit(kind))
		add_child(card)
		_cards.append(card)


func _lay_cards(u: float) -> void:
	if _cards.is_empty():
		return
	var many := _cards.size()
	# (side by side where there is room, else one over the next)
	var upright := size.y > size.x * 1.2
	var each := minf(260.0 * u, (size.x - 40.0 * u) / (1.0 if upright else float(many)) - 16.0 * u)
	if upright:
		each = minf(each, (size.y * 0.7) / many - 16.0 * u)
	for k in many:
		var along := (k - (many - 1) * 0.5) * (each + 16.0 * u)
		var middle := size * 0.5 + (Vector2(0.0, along) if upright else Vector2(along, 0.0))
		_cards[k].size = Vector2(each, each)
		_cards[k].position = middle - Vector2(each, each) * 0.5


## The outline of a fish, nose to the right, `long` from nose to tail (the last has a back fin).
func _fish(middle: Vector2, long: float, colour: Color, finned: bool) -> void:
	var points := PackedVector2Array()
	var half := long * 0.5
	for k in 13:
		var a := TAU * k / 12.0
		points.append(middle + Vector2(cos(a) * half * 0.62 + half * 0.2, sin(a) * half * 0.3))
	draw_colored_polygon(points, colour)
	var root := middle + Vector2(-half * 0.36, 0.0)
	draw_colored_polygon(PackedVector2Array([root, middle + Vector2(-half, -half * 0.34), middle + Vector2(-half * 0.8, 0.0), middle + Vector2(-half, half * 0.34)]), colour)
	if finned:
		draw_colored_polygon(PackedVector2Array([middle + Vector2(half * 0.35, -half * 0.26), middle + Vector2(half * 0.02, -half * 0.62), middle + Vector2(-half * 0.1, -half * 0.26)]), colour)


func _crown(at: Vector2, wide: float, colour: Color) -> void:
	var h := wide * 0.7
	draw_colored_polygon(PackedVector2Array([at + Vector2(0.0, h * 0.5), at + Vector2(0.0, -h * 0.5), at + Vector2(wide * 0.25, 0.0), at + Vector2(wide * 0.5, -h * 0.5),
			at + Vector2(wide * 0.75, 0.0), at + Vector2(wide, -h * 0.5), at + Vector2(wide, h * 0.5)]), colour)


## The round button that starts another run: an arrow going round.
class AgainButton:
	extends Button

	func _ready() -> void:
		flat = true
		for state: StringName in [&"normal", &"hover", &"pressed", &"focus", &"disabled"]:
			add_theme_stylebox_override(state, StyleBoxEmpty.new())

	func _process(_delta: float) -> void:
		queue_redraw()

	func _draw() -> void:
		var middle := size * 0.5
		var r := size.x * 0.5
		var ink := Color(0.85, 0.95, 1.0, 1.0 if button_pressed else 0.85)
		draw_circle(middle, r, Color(0.3, 0.6, 1.0, 0.45 if button_pressed else 0.25))
		draw_arc(middle, r - 2.0, 0.0, TAU, 64, ink, r * 0.05, true)
		# (most of a circle, with an arrowhead where it ends)
		draw_arc(middle, r * 0.48, -PI * 0.35, PI * 1.25, 40, ink, r * 0.11, true)
		var end := middle + Vector2.from_angle(-PI * 0.35) * r * 0.48
		var along := Vector2.from_angle(-PI * 0.35 - PI * 0.5)
		draw_colored_polygon(PackedVector2Array([end + along * r * 0.3, end - along.orthogonal() * r * 0.22 - along * r * 0.06, end + along.orthogonal() * r * 0.22 - along * r * 0.06]), ink)


## One thing the player can become: a card with the animal itself turning in it, to press.
class ChoiceCard:
	extends Button

	var kind := ""
	var _turn: Fish

	func _ready() -> void:
		flat = true
		for state: StringName in [&"normal", &"hover", &"pressed", &"focus", &"disabled"]:
			add_theme_stylebox_override(state, StyleBoxEmpty.new())
		var box := SubViewportContainer.new()
		box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		box.stretch = true
		box.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(box)
		var view := SubViewport.new()
		view.own_world_3d = true
		view.transparent_bg = true
		box.add_child(view)
		var sun := DirectionalLight3D.new()
		sun.rotation_degrees = Vector3(-50.0, 30.0, 0.0)
		sun.light_energy = 1.6
		view.add_child(sun)
		var env := Environment.new()
		env.background_mode = Environment.BG_CLEAR_COLOR
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.6, 0.75, 0.9)
		env.ambient_light_energy = 0.9
		var eye := Camera3D.new()
		eye.environment = env
		eye.position = Vector3(0.0, 0.18, 1.05)
		eye.fov = 38.0
		view.add_child(eye)
		eye.look_at(Vector3.ZERO)
		# The animal, a metre long, turning.
		_turn = Fish.new()
		view.add_child(_turn)
		_turn.length = 1.0
		_turn.set_kind(kind)
		_turn.heading = Vector3.RIGHT

	func _process(delta: float) -> void:
		if _turn:
			_turn.heading = _turn.heading.rotated(Vector3.UP, delta * 0.8)
			_turn.pose(delta, 1.0, 0.0)
		queue_redraw()

	func _draw() -> void:
		var ink := Color(0.85, 0.95, 1.0, 1.0 if button_pressed else 0.8)
		var r := size.x * 0.5
		draw_circle(size * 0.5, r, Color(0.02, 0.1, 0.25, 0.75 if button_pressed else 0.6))
		draw_arc(size * 0.5, r - 2.0, 0.0, TAU, 64, Color(0.55, 1.0, 0.8, ink.a), r * 0.04, true)
