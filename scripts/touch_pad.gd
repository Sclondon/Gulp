class_name TouchPad
extends Control
## The on-screen controls, as the brass fittings of an old submarine (the user, 2026-11-18: "the
## contols UI should be old timey submarine themed, and there needs to be a lever to control
## speed around the boost button instead of just swimming same speed all the time"):
##
## - The helm (bottom left): a riveted brass plate with a ball-topped stick that steers.
## - The burst (bottom right): a round brass plunger, held for a burst of speed, with a pressure
##   gauge round it showing how much burst is left.
## - The speed lever: an engine-order arc round the burst button, from dead slow (at its left
##   end) to full ahead (at its top), with a brass handle that stays where it is put.
##
## All are always drawn. A touch anywhere in the lower left takes the helm (it moves under the
## thumb); a touch on the arc takes the lever; a touch anywhere else in the lower right holds the
## burst. A mouse works as a finger (the project turns mouse presses into touches).

const BRASS := Color(0.80, 0.62, 0.26)
const BRASS_LIGHT := Color(1.0, 0.88, 0.55)
const BRASS_DARK := Color(0.33, 0.23, 0.09)
const IRON := Color(0.10, 0.12, 0.14)
const GLASS := Color(0.75, 0.95, 0.9)
## The lever's arc round the burst button: where dead slow and full ahead are (radians, as the
## screen has them: 0 to the right, a quarter turn back is straight up).
const SLOW_AT := PI * 1.03
const FULL_AT := PI * 1.52

## What the player is asking for: the stick (x right, y up, each -1..1), the burst, and the
## speed (0 dead slow to 1 full ahead).
var stick := Vector2.ZERO
var boost := false
var throttle := 0.7
## Shown on the gauge round the burst button (0..1).
var stamina := 1.0

var _stick_touch := -1
var _boost_touch := -1
var _lever_touch := -1
var _stick_from := Vector2.ZERO


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


## Lets go of everything (the run is over, or the pad is hidden). The lever stays where it is.
func release() -> void:
	_stick_touch = -1
	_boost_touch = -1
	_lever_touch = -1
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
	return Vector2(size.x - 150.0 * unit(), size.y - 175.0 * unit())


## How far from the burst button's middle the lever's arc runs.
func lever_radius() -> float:
	return 150.0 * unit()


## Where the lever's handle is for a speed (0..1).
func lever_at(speed: float) -> Vector2:
	return boost_home() + Vector2.from_angle(lerpf(SLOW_AT, FULL_AT, speed)) * lever_radius()


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
				# (a touch on the helm itself pushes it; one elsewhere puts the helm there)
				_stick_from = stick_home() if touch.position.distance_to(stick_home()) < reach * 1.3 else touch.position
				_push(touch.position)
			elif touch.position.x >= size.x * 0.5:
				if _on_lever(touch.position) and _lever_touch == -1:
					_lever_touch = touch.index
					_pull(touch.position)
				elif _boost_touch == -1:
					_boost_touch = touch.index
					boost = true
		elif touch.index == _stick_touch:
			_stick_touch = -1
			stick = Vector2.ZERO
		elif touch.index == _boost_touch:
			_boost_touch = -1
			boost = false
		elif touch.index == _lever_touch:
			_lever_touch = -1
	elif event is InputEventScreenDrag:
		var drag := event as InputEventScreenDrag
		if drag.index == _stick_touch:
			_push(drag.position)
		elif drag.index == _lever_touch:
			_pull(drag.position)


func _push(at: Vector2) -> void:
	var pushed := (at - _stick_from) / (105.0 * unit())
	stick = Vector2(pushed.x, -pushed.y).limit_length(1.0)


# Whether a touch is on the lever's arc (the band round the burst button, between its ends and
# a thumb's width past each).
func _on_lever(at: Vector2) -> bool:
	var from := at - boost_home()
	var far := from.length()
	if far < lever_radius() - 38.0 * unit() or far > lever_radius() + 46.0 * unit():
		return false
	var turn := fposmod(from.angle(), TAU)
	return turn > SLOW_AT - 0.3 and turn < FULL_AT + 0.3


func _pull(at: Vector2) -> void:
	var turn := fposmod((at - boost_home()).angle(), TAU)
	throttle = clampf(inverse_lerp(SLOW_AT, FULL_AT, turn), 0.0, 1.0)


func _draw() -> void:
	var u := unit()
	_draw_helm(u)
	_draw_lever(u)
	_draw_burst(u)


# A round brass plate: a dark rim, the brass, a bright edge towards the light, rivets round it.
func _plate(at: Vector2, r: float, rivets: int, see := 0.82) -> void:
	draw_circle(at, r + 5.0 * unit(), Color(IRON, 0.55))
	draw_circle(at, r, Color(BRASS_DARK, see))
	draw_arc(at, r - 4.0 * unit(), 0.0, TAU, 64, Color(BRASS, see), 8.0 * unit(), true)
	draw_arc(at, r - 4.0 * unit(), PI * 1.05, PI * 1.6, 24, Color(BRASS_LIGHT, see * 0.8), 3.0 * unit(), true)
	for k in rivets:
		var way := Vector2.from_angle(TAU * (k + 0.5) / rivets)
		draw_circle(at + way * (r - 4.0 * unit()), 3.6 * unit(), Color(BRASS_DARK, see))
		draw_circle(at + way * (r - 4.0 * unit()) - Vector2(1.0, 1.0) * unit(), 2.0 * unit(), Color(BRASS_LIGHT, see))


# The helm: the plate, an engraved arrowhead each way, the stick's shaft and its brass ball.
func _draw_helm(u: float) -> void:
	var home := _stick_from if _stick_touch != -1 else stick_home()
	var reach := 105.0 * u
	_plate(home, reach, 12, 0.6)
	draw_circle(home, reach * 0.74, Color(IRON, 0.45))
	draw_arc(home, reach * 0.74, 0.0, TAU, 48, Color(BRASS, 0.7), 2.5 * u, true)
	for k in 4:
		var way := Vector2.RIGHT.rotated(k * PI * 0.5)
		var tip := home + way * reach * 0.68
		var across := way.orthogonal() * reach * 0.1
		draw_colored_polygon(PackedVector2Array([tip, tip - way * reach * 0.14 + across, tip - way * reach * 0.14 - across]), Color(BRASS_LIGHT, 0.75))
	var knob := home + Vector2(stick.x, -stick.y) * reach * 0.58
	# (the shaft, from its boot in the middle to the ball)
	draw_circle(home, reach * 0.2, Color(IRON, 0.8))
	draw_line(home, knob, Color(BRASS_DARK, 0.95), reach * 0.16, true)
	draw_line(home, knob, Color(BRASS, 0.95), reach * 0.08, true)
	var held := _stick_touch != -1
	draw_circle(knob, reach * 0.36, Color(BRASS_DARK, 0.95))
	draw_circle(knob, reach * 0.32, Color(BRASS, 1.0 if held else 0.9))
	draw_circle(knob - Vector2(reach, reach) * 0.1, reach * 0.11, Color(BRASS_LIGHT, 0.9))


# The speed lever: a slotted brass arc with a tick for each order, growing from dead slow to full
# ahead, and the handle.
func _draw_lever(u: float) -> void:
	var at := boost_home()
	var r := lever_radius()
	draw_arc(at, r, SLOW_AT - 0.08, FULL_AT + 0.08, 40, Color(IRON, 0.6), 40.0 * u, true)
	draw_arc(at, r, SLOW_AT - 0.08, FULL_AT + 0.08, 40, Color(BRASS_DARK, 0.85), 32.0 * u, true)
	draw_arc(at, r + 14.0 * u, SLOW_AT - 0.08, FULL_AT + 0.08, 40, Color(BRASS, 0.9), 3.0 * u, true)
	draw_arc(at, r - 14.0 * u, SLOW_AT - 0.08, FULL_AT + 0.08, 40, Color(BRASS, 0.9), 3.0 * u, true)
	# (the slot the handle runs in)
	draw_arc(at, r, SLOW_AT, FULL_AT, 40, Color(IRON, 0.9), 7.0 * u, true)
	# the orders: five ticks, each longer and brighter than the last, lit up to the lever
	for k in 5:
		var share := k / 4.0
		var way := Vector2.from_angle(lerpf(SLOW_AT, FULL_AT, share))
		var long := (9.0 + 5.0 * k) * u
		var lit := throttle >= share - 0.02
		draw_line(at + way * (r + 22.0 * u), at + way * (r + 22.0 * u + long), Color(BRASS_LIGHT if lit else BRASS_DARK, 0.95), (3.0 + 0.8 * k) * u, true)
	# the handle: an arm from the hub's rim, and a brass grip
	var grip := lever_at(throttle)
	var way_out := (grip - at).normalized()
	draw_line(at + way_out * 92.0 * u, grip, Color(BRASS_DARK, 0.95), 12.0 * u, true)
	draw_line(at + way_out * 92.0 * u, grip, Color(BRASS, 0.95), 6.0 * u, true)
	draw_circle(grip, 25.0 * u, Color(IRON, 0.7))
	draw_circle(grip, 22.0 * u, Color(BRASS_DARK, 1.0))
	draw_circle(grip, 18.0 * u, Color(BRASS_LIGHT if _lever_touch != -1 else BRASS, 1.0))
	draw_circle(grip - Vector2(6.0, 6.0) * u, 5.0 * u, Color(BRASS_LIGHT, 0.9))


# The burst: a brass plunger with a double arrowhead, in a pressure gauge that shows what is left.
func _draw_burst(u: float) -> void:
	var at := boost_home()
	var r := 88.0 * u
	_plate(at, r, 10)
	# the gauge: a glass ring, green where there is burst left, a red stop at empty
	draw_arc(at, r - 15.0 * u, 0.0, TAU, 64, Color(IRON, 0.85), 11.0 * u, true)
	if stamina > 0.01:
		draw_arc(at, r - 15.0 * u, -PI * 0.5, -PI * 0.5 + TAU * stamina, 64, Color(0.45, 0.95, 0.7, 0.95), 8.0 * u, true)
	draw_line(at + Vector2(0.0, -(r - 22.0 * u)), at + Vector2(0.0, -(r - 8.0 * u)), Color(0.95, 0.25, 0.15, 0.95), 4.0 * u, true)
	# the plunger: sunk a little while it is held
	var cap := r - 26.0 * u - (4.0 * u if boost else 0.0)
	draw_circle(at, cap + 3.0 * u, Color(BRASS_DARK, 1.0))
	draw_circle(at, cap, Color(BRASS, 1.0) if not boost else Color(BRASS.darkened(0.15), 1.0))
	draw_arc(at, cap - 4.0 * u, PI * 1.05, PI * 1.6, 20, Color(BRASS_LIGHT, 0.0 if boost else 0.9), 3.0 * u, true)
	for k in 2:
		var x := (k - 0.5) * cap * 0.55 - cap * 0.08
		draw_polyline(PackedVector2Array([at + Vector2(x - cap * 0.18, -cap * 0.36), at + Vector2(x + cap * 0.22, 0.0), at + Vector2(x - cap * 0.18, cap * 0.36)]),
				Color(IRON if not boost else GLASS, 0.9), 7.0 * u, true)
