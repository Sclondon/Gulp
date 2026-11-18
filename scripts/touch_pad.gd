class_name TouchPad
extends Control
## The on-screen controls: a rusted mad-science console along the bottom of the screen, in three
## housings (the user, 2026-11-18: "the contols UI should be old timey submarine themed, and
## there needs to be a lever to control speed around the boost button", "There should be a whole
## control panel on the bottom part, that also shows speed and your evolution level and maybe any
## special ability buttons, with and old rusted and e gad frankenstein technology aesthetic").
##
## It is a 3D model (the user, after two rounds of generated pictures: "lets recreate the ui as a
## 3d model to interact with"): PanelModel draws it and moves its parts; this takes the touches
## and draws what is only light over it (the sonar's sweep and blips, the spark).
##
## - The helm housing (bottom left): a socket with a ball-topped stick that steers, under two
##   electrodes that a spark jumps between while the fish bursts.
## - The engine housing (bottom right): a plunger, held for a burst of speed, and curving round
##   it a slot with a lever that sets how fast the fish swims, from dead slow (the slot's lower
##   left end) to full ahead (its upper right end). The lever stays where it is put.
## - The instrument housing (between them): a sonar scope (what hunts the fish in red, what it
##   can eat in green, ahead of it up the screen), dials for speed, depth and how much burst is
##   left (left to right), a rack of vacuum tubes that light one for each time the fish has become
##   something bigger, and two switches kept for special abilities that do not exist yet (hidden
##   under the screen's edge on a wide screen).
##
## The two rounds of generated pictures the model follows are in tools/art_src and, retired,
## textures/panel.
##
## A touch anywhere in the lower left takes the helm; a touch on the lever's slot takes the lever;
## a touch anywhere else in the lower right holds the burst. A mouse works as a finger (the
## project turns mouse presses into touches).

const BRASS := Color(0.80, 0.62, 0.26)
const BRASS_LIGHT := Color(1.0, 0.88, 0.55)
const BRASS_DARK := Color(0.33, 0.23, 0.09)
const IRON := Color(0.10, 0.12, 0.14)
## How solid the panel is drawn (the sea shows through it a little).
const SEE := 0.9
## How many times a fish can grow into something bigger (the evolution dial's full turn).
const STAGES := 8
## How far the sonar sees (m).
const SONAR_RANGE := 30.0

## What the player is asking for: the stick (x right, y up, each -1..1), the burst, and the
## speed (0 dead slow to 1 full ahead).
var stick := Vector2.ZERO
var boost := false
var throttle := 0.7
## Shown on the panel: how much burst is left (0..1), how fast the fish is going (0 still to 1
## flat out, bursting), how deep it is (0 at the surface to 1 at the bottom of the trench), how
## many times it has become something bigger, and what the sonar sees: each a Vector3 of where it
## is from the fish (x to its right, y ahead of it, both in metres) and what it is (z: 0 food,
## 1 a hunter).
var stamina := 1.0
var speed := 0.0
var depth := 0.0
var level := 0
var blips: Array[Vector3] = []

var model: PanelModel
var _stick_touch := -1
var _boost_touch := -1
var _lever_touch := -1
var _stick_from := Vector2.ZERO


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	model = PanelModel.new()
	add_child(model)


## Lets go of everything (the run is over, or the pad is hidden). The lever stays where it is.
func release() -> void:
	_stick_touch = -1
	_boost_touch = -1
	_lever_touch = -1
	stick = Vector2.ZERO
	boost = false
	queue_redraw()


func _process(delta: float) -> void:
	model.render_target_update_mode = SubViewport.UPDATE_ALWAYS if visible else SubViewport.UPDATE_DISABLED
	if visible:
		_fit()
		model.show_state(stick, boost and stamina > 0.0, throttle, [speed + sin(Time.get_ticks_msec() * 0.03) * 0.004, depth, stamina, float(level) / STAGES], delta)
		queue_redraw()


## One unit of the layout: the controls are sized by the shorter side of the screen.
func unit() -> float:
	return minf(size.x, size.y) / 720.0


# Keeps the model laid out for the screen as it is now.
func _fit() -> void:
	model.lay_out(size, unit())


func stick_home() -> Vector2:
	_fit()
	return model.stick_home()


func boost_home() -> Vector2:
	_fit()
	return model.boost_home()


## Where the lever's handle is for a speed (0..1): a point along its slot.
func lever_at(at_speed: float) -> Vector2:
	_fit()
	return model.lever_at(at_speed)


func _input(event: InputEvent) -> void:
	if not visible:
		return
	var reach := 100.0 * unit()
	if event is InputEventScreenTouch:
		var touch := event as InputEventScreenTouch
		if touch.pressed:
			if touch.position.y < size.y * 0.4:
				return
			if touch.position.x < size.x * 0.5 and _stick_touch == -1:
				_stick_touch = touch.index
				# (a touch on the helm itself pushes it from its middle; one elsewhere, from there)
				_stick_from = stick_home() if touch.position.distance_to(stick_home()) < reach * 1.3 else touch.position
				_push(touch.position)
			elif touch.position.x >= size.x * 0.5:
				if _lever_near(touch.position) < 46.0 * unit() and _lever_touch == -1:
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
	var pushed := (at - _stick_from) / (100.0 * unit())
	stick = Vector2(pushed.x, -pushed.y).limit_length(1.0)


# How far a place is from the lever's slot.
func _lever_near(at: Vector2) -> float:
	var near := INF
	for k in 25:
		near = minf(near, at.distance_to(lever_at(k / 24.0)))
	return near


# Puts the lever at the point of its slot nearest a place.
func _pull(at: Vector2) -> void:
	var best := 0.0
	var near := INF
	for k in 49:
		var far := at.distance_to(lever_at(k / 48.0))
		if far < near:
			near = far
			best = k / 48.0
	throttle = best


func _draw() -> void:
	var u := unit()
	draw_texture_rect(model.get_texture(), Rect2(Vector2.ZERO, size), false, Color(1.0, 1.0, 1.0, SEE))
	# The sonar: a sweep going round, a ring, and what is about (hunters red, food green).
	var scope := model.point("Scope")
	var r := model.point("ScopeEdge").x - scope.x
	var sweep := Time.get_ticks_msec() * 0.0022
	for k in 14:
		var way := Vector2.from_angle(sweep - k * 0.06)
		draw_line(scope, scope + way * r * 0.95, Color(0.4, 1.0, 0.45, 0.5 * (1.0 - k / 14.0)), 2.5 * u, true)
	draw_arc(scope, r * 0.5, 0.0, TAU, 32, Color(0.4, 1.0, 0.45, 0.22), 1.5 * u, true)
	draw_circle(scope, 3.0 * u, Color(0.6, 1.0, 0.6, 0.9))
	for blip in blips:
		var off := Vector2(blip.x, -blip.y) / SONAR_RANGE
		if off.length() > 0.95:
			continue
		# (each brightens as the sweep passes it, and fades)
		var lag := fposmod(sweep - off.angle(), TAU) / TAU
		var bright := 0.45 + 0.55 * (1.0 - lag)
		var colour := Color(1.0, 0.25, 0.15) if blip.z > 0.5 else Color(0.5, 1.0, 0.5)
		draw_circle(scope + off * r, (5.0 if blip.z > 0.5 else 3.5) * u, Color(colour, bright))
	if boost and stamina > 0.0:
		_spark(model.point("SparkA"), model.point("SparkB"))


# A spark between the electrodes: a jagged blue-white line that is never the same twice.
func _spark(from: Vector2, to: Vector2) -> void:
	var wide := from.distance_to(to)
	var line := PackedVector2Array()
	for k in 9:
		var share := k / 8.0
		line.append(from.lerp(to, share) + Vector2(0.0, randf_range(-0.16, 0.16) * wide * sin(share * PI)))
	draw_polyline(line, Color(0.45, 0.7, 1.0, 0.5), wide * 0.07, true)
	draw_polyline(line, Color(0.9, 0.97, 1.0, 0.95), wide * 0.025, true)
