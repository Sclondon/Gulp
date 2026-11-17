class_name TouchPad
extends Control
## The on-screen controls: a stick (bottom left) that steers, and a round button (bottom right)
## that gives a burst of speed while it is held, ringed by how much burst is left.
##
## Both are always drawn. A touch anywhere in the lower left of the screen takes the stick (it
## moves under the thumb); a touch anywhere in the lower right holds the burst. A mouse works
## as a finger (the project turns mouse presses into touches).

## What the player is asking for: the stick (x right, y up, each -1..1) and the burst.
var stick := Vector2.ZERO
var boost := false
## Shown round the burst button (0..1).
var stamina := 1.0

var _stick_touch := -1
var _boost_touch := -1
var _stick_from := Vector2.ZERO


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


## Lets go of everything (the run is over, or the pad is hidden).
func release() -> void:
	_stick_touch = -1
	_boost_touch = -1
	stick = Vector2.ZERO
	boost = false
	queue_redraw()


func _process(_delta: float) -> void:
	if visible:
		queue_redraw()


## One unit of the layout: the controls are sized by the shorter side of the screen.
func unit() -> float:
	return minf(size.x, size.y) / 720.0


func stick_home() -> Vector2:
	return Vector2(165.0 * unit(), size.y - 190.0 * unit())


func boost_home() -> Vector2:
	return Vector2(size.x - 150.0 * unit(), size.y - 190.0 * unit())


func _input(event: InputEvent) -> void:
	if not visible:
		return
	var reach := 105.0 * unit()
	if event is InputEventScreenTouch:
		var touch := event as InputEventScreenTouch
		if touch.pressed:
			if touch.position.y < size.y * 0.4:
				return
			if touch.position.x < size.x * 0.5 and _stick_touch == -1:
				_stick_touch = touch.index
				# (a touch on the stick itself pushes it; one elsewhere puts the stick there)
				_stick_from = stick_home() if touch.position.distance_to(stick_home()) < reach * 1.3 else touch.position
				_push(touch.position)
			elif touch.position.x >= size.x * 0.5 and _boost_touch == -1:
				_boost_touch = touch.index
				boost = true
		elif touch.index == _stick_touch:
			_stick_touch = -1
			stick = Vector2.ZERO
		elif touch.index == _boost_touch:
			_boost_touch = -1
			boost = false
	elif event is InputEventScreenDrag and (event as InputEventScreenDrag).index == _stick_touch:
		_push((event as InputEventScreenDrag).position)


func _push(at: Vector2) -> void:
	var pushed := (at - _stick_from) / (105.0 * unit())
	stick = Vector2(pushed.x, -pushed.y).limit_length(1.0)


func _draw() -> void:
	var u := unit()
	var ink := Color(0.8, 0.92, 1.0, 0.5)
	var soft := Color(0.35, 0.6, 1.0, 0.12)
	# The stick: a ring with an arrowhead each way, and the knob.
	var home := _stick_from if _stick_touch != -1 else stick_home()
	var reach := 105.0 * u
	draw_circle(home, reach, soft)
	draw_arc(home, reach, 0.0, TAU, 64, ink, 3.0 * u, true)
	for k in 4:
		var way := Vector2.RIGHT.rotated(k * PI * 0.5)
		var tip := home + way * reach * 0.86
		var across := way.orthogonal() * reach * 0.13
		draw_colored_polygon(PackedVector2Array([tip, tip - way * reach * 0.17 + across, tip - way * reach * 0.17 - across]), ink)
	var knob := home + Vector2(stick.x, -stick.y) * reach * 0.62
	draw_circle(knob, reach * 0.42, Color(0.8, 0.92, 1.0, 0.55 if _stick_touch != -1 else 0.3))
	# The burst: a round button with a double arrowhead, ringed by what is left of it.
	var at := boost_home()
	var r := 88.0 * u
	draw_circle(at, r, Color(0.35, 0.6, 1.0, 0.3 if boost else 0.12))
	draw_arc(at, r, 0.0, TAU, 64, Color(ink, 0.25), 3.0 * u, true)
	if stamina > 0.01:
		draw_arc(at, r, -PI * 0.5, -PI * 0.5 + TAU * stamina, 64, Color(0.6, 1.0, 0.85, 0.85), 7.0 * u, true)
	for k in 2:
		var x := (k - 0.5) * r * 0.5 - r * 0.08
		draw_polyline(PackedVector2Array([at + Vector2(x - r * 0.16, -r * 0.34), at + Vector2(x + r * 0.2, 0.0), at + Vector2(x - r * 0.16, r * 0.34)]),
				Color(ink, 0.9 if boost else 0.6), 7.0 * u, true)
