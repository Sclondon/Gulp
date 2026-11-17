class_name Hud
extends Control
## What is shown over the sea: along the top, the fish the player grows through (a row of
## outlines, each bigger than the last, lit up to the one it is now), a bar of how far it has
## eaten towards the next, and how long it is; red round the edges while something hunts it;
## and when the run is over, what it got to, how long it was, the longest so far, and a round
## button to start again. Symbols and numbers only.

signal restart

var player: Player
## How hard it is being hunted (0..1), eased by Main.
var danger := 0.0
## The run is over.
var over := false: set = set_over
## The longest the player has been in any run (metres), and in this one.
var best := 0.0
var reached := 0.0

var _again: AgainButton
var _clock := 0.0
var _grown := 0.0


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
	queue_redraw()


func _draw() -> void:
	if player == null:
		return
	var u := minf(size.x, size.y) / 720.0
	var font := get_theme_default_font()
	var ink := Color(0.85, 0.95, 1.0)
	var stages := Player.STAGES.size()
	# Red round the edges while it is hunted.
	if danger > 0.01 and not over:
		var pulse := danger * (0.35 + 0.15 * sin(_clock * 9.0))
		var deep := 90.0 * u
		# (rings one inside the next, fainter towards the middle)
		for k in 12:
			var inset := deep * (k + 0.5) / 12.0
			var faint := pow(1.0 - k / 12.0, 2.0)
			draw_rect(Rect2(Vector2(inset, inset), size - Vector2(inset, inset) * 2.0), Color(1.0, 0.15, 0.1, pulse * faint), false, deep / 12.0 + 1.0)
	# The row of fish, each bigger than the last.
	var top := 46.0 * u
	var wide := minf(size.x - 60.0 * u, 620.0 * u)
	var left := (size.x - wide) * 0.5
	var x := left
	var gap := (wide - _row_width(u)) / (stages - 1)
	for k in stages:
		var long := _outline_length(k, u)
		var middle := Vector2(x + long * 0.5, top + 26.0 * u)
		var now := k == player.stage
		var colour := Color(ink, 0.9) if k < player.stage else (Color(0.55, 1.0, 0.8, 1.0) if now else Color(ink, 0.25))
		var swell := 1.0 + (0.35 * _grown if now else 0.0)
		_fish(middle, long * swell, colour, k == stages - 1)
		if now:
			draw_line(middle + Vector2(-long * 0.5, 24.0 * u), middle + Vector2(long * 0.5, 24.0 * u), colour, 3.0 * u, true)
		x += long + gap
	# The bar: how far towards the next (or towards full size, at the last).
	var bar := Rect2(left, top + 66.0 * u, wide, 12.0 * u)
	draw_rect(bar, Color(0.0, 0.05, 0.15, 0.55))
	draw_rect(Rect2(bar.position, Vector2(bar.size.x * clampf(player.progress, 0.0, 1.0), bar.size.y)), Color(0.55, 1.0, 0.8, 0.9))
	draw_rect(bar, Color(ink, 0.5), false, 2.0 * u)
	# How long it is, and the longest so far (under a small crown).
	var text_size := int(30.0 * u)
	draw_string(font, Vector2(left, bar.end.y + 38.0 * u), "%.2f m" % player.length, HORIZONTAL_ALIGNMENT_LEFT, -1.0, text_size, ink)
	if best > 0.0:
		var best_text := "%.2f m" % best
		var best_wide := font.get_string_size(best_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, text_size).x
		var at := Vector2(left + wide - best_wide, bar.end.y + 38.0 * u)
		draw_string(font, at, best_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, text_size, Color(1.0, 0.86, 0.45))
		_crown(at + Vector2(-34.0 * u, -11.0 * u), 22.0 * u, Color(1.0, 0.86, 0.45))
	if over:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.02, 0.08, 0.6))
		var middle := Vector2(size.x * 0.5, size.y * 0.5 - 150.0 * u)
		_fish(middle, _outline_length(player.stage, u) * 3.0, Color(0.55, 1.0, 0.8), player.stage == stages - 1)
		var big := int(54.0 * u)
		var text := "%.2f m" % reached
		var text_wide := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, big).x
		draw_string(font, Vector2(size.x * 0.5 - text_wide * 0.5, size.y * 0.5 - 10.0 * u), text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, big, ink)


func _outline_length(k: int, u: float) -> float:
	return (34.0 + 17.0 * k) * u


func _row_width(u: float) -> float:
	var sum := 0.0
	for k in Player.STAGES.size():
		sum += _outline_length(k, u)
	return sum


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
