class_name TouchPad
extends Control
## The on-screen controls: a rusted mad-science console along the bottom of the screen (the user,
## 2026-11-18: "the contols UI should be old timey submarine themed, and there needs to be a
## lever to control speed around the boost button", "There should be a whole control panel on
## the bottom part, that also shows speed and your evolution level and maybe any special ability
## buttons, with and old rusted and e gad frankenstein technology aesthetic").
##
## It is a 3D model (the user: "lets recreate the ui as a 3d model to interact with"):
## PanelModel draws it and moves its parts; this takes the touches and draws what is only light
## or writing over it (the sonar's sweep, blips and compass points, the spark, the fish's length).
##
## - The helm housing (bottom left): a socket with a ball-topped stick that steers, under two
##   electrodes that a spark jumps between while the fish bursts; over it the GROWTH dial: a turn
##   of its needle is the whole way from the first fish to the last, creeping round as it eats,
##   and the fish's length is written on its face (this replaced the bar that was at the top of the
##   screen: the user, "Why is there srill the ui at rhe top? Is that the same as the evo dial!").
## - The engine housing (bottom right): a plunger, held for a burst of speed, and curving round
##   its left a slot with a lever that sets how fast the fish swims, from dead slow (the slot's
##   lower end) to full ahead (its top). The lever stays where it is put. Over it the SPEED dial.
## - The instrument housing (between them): a sonar scope (after a ping, what hunts the fish in red
##   and what it can eat in gold, ahead of it up the screen, with N, E, S and W round its rim), and
##   small dials for DEPTH and for how much BURST is left.
## - The switch box: two knife switches for special abilities. The left one is the SONAR (the user,
##   2026-11-20: "The sonar should be activated with one of the special ability buttons"): thrown,
##   it pings; its handle drops down its slot and creeps back up as it charges again, and its pilot
##   lamp shows green when it is ready (E or a pad's Y does the same). The right one is still kept
##   for an ability that does not exist yet.
## - The valve box: the pause button, and two vacuum tubes that burn brighter while it bursts.
##
## A touch on the sonar switch pings; a touch anywhere else in the lower left takes the helm; a
## touch on the lever's slot takes the lever;
## a touch on the pause button pauses (and any touch then goes on); a touch anywhere else in the
## lower right holds the burst. A mouse works as a finger (the project turns mouse presses into
## touches).

## The pause button was pressed, or (paused) the screen was touched to go on.
signal pause_pressed
## The sonar switch was thrown (Main pings if it has charged).
signal sonar_pressed

const BRASS := Color(0.80, 0.62, 0.26)
const BRASS_LIGHT := Color(1.0, 0.88, 0.55)
const BRASS_DARK := Color(0.33, 0.23, 0.09)
const IRON := Color(0.10, 0.12, 0.14)
## How solid the panel is drawn (the sea shows through it a little).
const SEE := 0.92
## How many times a fish can grow into something bigger (the growth dial's full turn).
const STAGES := 8
## How far the sonar sees (m).
const SONAR_RANGE := Sonar.RANGE

## What the player is asking for: the stick (x right, y up, each -1..1), the burst, and the
## speed (0 dead slow to 1 full ahead).
var stick := Vector2.ZERO
var boost := false
var throttle := 0.7
## Shown on the panel: how much burst is left (0..1), how fast the fish is going (0 still to 1
## flat out, bursting), how deep it is (0 at the surface to 1 at the bottom of the trench), how
## many times it has become something bigger and how far it is towards the next (0..1), how long
## it is (m), which way it is heading (radians round from north, which is the sea's -Z, turning
## towards east, its +X), and what the sonar sees: each a Vector3 of where it is from the fish (x
## to its right, y ahead of it, both in metres) and what it is (z: 0 food, 1 a hunter).
var stamina := 1.0
var speed := 0.0
var depth := 0.0
var level := 0
var progress := 0.0
var length := 0.0
var heading := 0.0
var blips: Array[Vector4] = []
## Seconds since the sonar last pinged (Sonar.age), and how far it has charged again (0 just
## pinged, 1 ready).
var ping_age := INF
var sonar_charge := 1.0
## The landmarks the sonar points to: each [its name in Sonar.LANDMARKS, where it is from the fish
## (x to its right, y ahead, metres)].
var landmarks: Array = []
## How near a hunter that is after the fish has come (0 none near, 1 upon it): the alarm lamp on
## the scope's head flashes, faster the nearer.
var alarm := 0.0
## The game is paused: a veil over the sea and an arrow to go on.
var paused := false

var model: PanelModel
var sonar: Sonar
var _stick_touch := -1
var _boost_touch := -1
var _lever_touch := -1
var _stick_from := Vector2.ZERO


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	model = PanelModel.new()
	add_child(model)
	sonar = Sonar.new()
	add_child(sonar)


## Lets go of everything (the run is over, or the pad is hidden). The lever stays where it is.
func release() -> void:
	_stick_touch = -1
	_boost_touch = -1
	_lever_touch = -1
	stick = Vector2.ZERO
	boost = false
	queue_redraw()


func _process(delta: float) -> void:
	if not visible:
		model.render_target_update_mode = SubViewport.UPDATE_DISABLED
	elif Tier.phone():
		# (a phone draws the panel every other frame: its needles and lever move slowly; CLAUDE.md,
		# "Decision: a phone tier")
		if Engine.get_process_frames() % 2 == 0:
			model.render_target_update_mode = SubViewport.UPDATE_ONCE
	else:
		model.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	if visible:
		_fit()
		model.show_state(stick, boost and stamina > 0.0, throttle,
				[speed + sin(Time.get_ticks_msec() * 0.03) * 0.004, depth, stamina, (level + clampf(progress, 0.0, 1.0)) / STAGES], delta)
		model.show_sonar(1.0 - clampf(sonar_charge, 0.0, 1.0), delta)
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


## Where the pause button is.
func pause_home() -> Vector2:
	_fit()
	return model.point("Pause")


## Where the sonar switch is (its handle at rest, ready).
func sonar_home() -> Vector2:
	_fit()
	return model.point("SwitchA")


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
			if paused or touch.position.distance_to(pause_home()) < 46.0 * unit():
				pause_pressed.emit()
				return
			if touch.position.y < size.y * 0.4:
				return
			if touch.position.distance_to(sonar_home()) < 40.0 * unit():
				sonar_pressed.emit()
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
	var font := get_theme_default_font()
	if paused:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.02, 0.05, 0.1, 0.55))
	draw_texture_rect(model.get_texture(), Rect2(Vector2.ZERO, size), false, Color(1.0, 1.0, 1.0, SEE))
	# The sonar's picture (scripts/sonar.gd) lies over the scope.
	var scope := model.point("Scope")
	sonar.fit(scope, model.point("ScopeEdge").x - scope.x)
	sonar.blips = blips
	sonar.landmarks = landmarks
	sonar.heading = heading
	sonar.age = ping_age
	# The sonar switch's pilot lamp, over the switch: green and breathing when it is ready, a dim red
	# while it charges (its handle creeping back up its slot shows how far).
	if not paused:
		var pilot := model.point("SwitchPilot")
		var wide := 7.0 * unit() * 1.6
		if sonar_charge >= 1.0:
			var breathe := 0.75 + 0.25 * sin(Time.get_ticks_msec() * 0.004)
			for k in 4:
				draw_circle(pilot, wide * (1.0 + k * 0.8), Color(0.35, 1.0, 0.45, breathe * (0.85 if k == 0 else 0.18 / k)))
			draw_circle(pilot - Vector2(wide, wide) * 0.3, wide * 0.3, Color(0.9, 1.0, 0.9, 0.8))
		else:
			draw_circle(pilot, wide, Color(0.55, 0.1, 0.05, 0.85))
	sonar.visible = not paused
	# The alarm lamp: lit red in flashes while a hunter is close.
	if alarm > 0.02 and not paused and model.has("Alarm"):
		var lamp := model.point("Alarm")
		var wide := absf(model.point("AlarmEdge").x - lamp.x)
		var flash := 0.5 + 0.5 * sin(Time.get_ticks_msec() * 0.001 * lerpf(7.0, 22.0, alarm))
		flash = smoothstep(0.35, 0.65, flash)
		for k in 5:
			draw_circle(lamp, wide * (1.0 + k * 0.9), Color(1.0, 0.16, 0.08, flash * (0.75 if k == 0 else 0.22 / k)))
		draw_circle(lamp - Vector2(wide, wide) * 0.3, wide * 0.3, Color(1.0, 0.85, 0.7, flash * 0.7))
	# The fish's length, written on the growth dial's face.
	var high := int(maxf(model.scale_of("Length") * 0.17, 9.0))
	var long := "%.2f m" % length
	var across := font.get_string_size(long, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high).x
	draw_string(font, model.point("Length") + Vector2(-across * 0.5, high * 0.36), long, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, Color(0.12, 0.07, 0.04, 0.95))
	# Paused: an arrow in the middle of the screen to go on.
	if paused:
		var middle := Vector2(size.x * 0.5, size.y * 0.36)
		var big := 70.0 * u
		draw_circle(middle, big + 8.0 * u, Color(0.1, 0.07, 0.03, 0.85))
		draw_circle(middle, big, Color(0.5, 0.38, 0.18))
		draw_colored_polygon(PackedVector2Array([middle + Vector2(-0.3, -0.42) * big, middle + Vector2(0.5, 0.0) * big, middle + Vector2(-0.3, 0.42) * big]), Color(0.12, 0.07, 0.03))


# A spark between the electrodes: a jagged blue-white line that is never the same twice.
func _spark(from: Vector2, to: Vector2) -> void:
	var wide := from.distance_to(to)
	var line := PackedVector2Array()
	for k in 9:
		var share := k / 8.0
		line.append(from.lerp(to, share) + Vector2(0.0, randf_range(-0.12, 0.12) * wide * sin(share * PI) - wide * 0.1 * sin(share * PI)))
	draw_polyline(line, Color(0.45, 0.7, 1.0, 0.5), wide * 0.05, true)
	draw_polyline(line, Color(0.9, 0.97, 1.0, 0.95), wide * 0.018, true)
