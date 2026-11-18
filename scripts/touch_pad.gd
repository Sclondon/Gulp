class_name TouchPad
extends Control
## The on-screen controls: a rusted mad-science console across the bottom of the screen, in
## three housings (the user, 2026-11-18: "the contols UI should be old timey submarine themed,
## and there needs to be a lever to control speed around the boost button", "There should be a
## whole control panel on the bottom part, that also shows speed and your evolution level and
## maybe any special ability buttons, with and old rusted and e gad frankenstein technology
## aesthetic", and of the first panel: "too much wasted space and also just kinda meh and plain
## needs an overhaul").
##
## - The helm housing (bottom left): a brass socket with a ball-topped stick that steers, under
##   a pair of electrodes that a spark jumps between while the fish bursts.
## - The engine housing (bottom right): a glowing plunger, held for a burst of speed, and over
##   it a curved slot with a brass lever that sets how fast the fish swims, from dead slow (the
##   slot's lower left end) to full ahead (its upper right end). The lever stays where it is put.
## - The instrument housing (between them): a sonar scope (what hunts the fish in red, what it
##   can eat in green, ahead of it up the screen), dials for speed, depth and how much burst is
##   left, a rack of vacuum tubes that light one for each time the fish has become something
##   bigger, and two knife switches kept for special abilities that do not exist yet.
##
## The pictures (textures/panel/*.png) are the second round: the user of the first, "the non
## interactive parts are a little too busy, and it looks a little too obviopusly ai- lets do
## another round using the current art as the concept" (2026-11-18), so the first round's two
## sheets were given back to be redrawn plainer and hand-painted (the first round's pictures are
## retired in textures/panel/retired_1). They were generated with ChatGPT's image generation, at the
## user's request ("What ai image tool would be best for this job? Use rhat"), as three housings
## with their moving parts taken out and a sheet of the moving parts, and cut apart by
## tools/cut_art.gd; the originals are in tools/art_src. Everything that moves is drawn here over
## them. The numbers below that say where things are in each picture were read off the pictures.
##
## A touch anywhere in the lower left takes the helm (it moves under the thumb); a touch on the
## lever's slot takes the lever; a touch anywhere else in the lower right holds the burst. A
## mouse works as a finger (the project turns mouse presses into touches).

const ART := "res://textures/panel/%s.png"
const BRASS := Color(0.80, 0.62, 0.26)
const BRASS_LIGHT := Color(1.0, 0.88, 0.55)
const BRASS_DARK := Color(0.33, 0.23, 0.09)
const IRON := Color(0.10, 0.12, 0.14)
## How solid the housings are drawn (the sea shows through them a little).
const SEE := 0.86
## Each housing's picture: its size, and how many layout units a pixel of it is.
const HELM_SIZE := Vector2(383.0, 645.0)
const GAUGE_SIZE := Vector2(719.0, 680.0)
const ENGINE_SIZE := Vector2(371.0, 644.0)
const SIDE_SCALE := 0.6
const GAUGE_SCALE := 0.5
## How much of each side housing's foot hangs off the bottom of the screen (pixels of its picture).
const HELM_SUNK := 70.0
const ENGINE_SUNK := 70.0
## Where things are in the helm housing's picture: the socket's middle, and the electrodes' gap.
const HELM_WELL := Vector2(192.0, 414.0)
const HELM_SPARK := Vector2(194.0, 78.0)
## In the engine housing's picture: the plunger's recess, and the lever's slot as a curve from
## dead slow through a bend to full ahead.
const ENGINE_WELL := Vector2(193.0, 445.0)
const SLOT := [Vector2(58.0, 283.0), Vector2(118.0, 200.0), Vector2(258.0, 190.0)]
## In the instrument housing's picture: the scope, the three dials, the tubes.
const SCOPE := Vector2(307.0, 132.0)
const SCOPE_RADIUS := 92.0
const DIAL_SPEED := Vector2(105.0, 181.0)
const DIAL_DEPTH := Vector2(505.0, 177.0)
const DIAL_BURST := Vector2(640.0, 181.0)
const TUBE_XS := [143.0, 208.0, 274.0, 341.0, 407.0, 474.0, 540.0, 607.0]
const TUBE_Y := 342.0
## How many tubes the panel has.
const TUBES := 8
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

var _stick_touch := -1
var _boost_touch := -1
var _lever_touch := -1
var _stick_from := Vector2.ZERO
var _art := {}


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


## Whether the screen is wide enough to stand the three housings side by side; if not (a phone
## held upright) the instruments stand behind and above the gap between the other two.
func is_wide() -> bool:
	return size.x > 1150.0 * unit()


# Where each housing's picture is drawn: its top left corner.
func _helm_at() -> Vector2:
	return Vector2(0.0, size.y - (HELM_SIZE.y - HELM_SUNK) * SIDE_SCALE * unit())


func _engine_at() -> Vector2:
	return Vector2(size.x - ENGINE_SIZE.x * SIDE_SCALE * unit(), size.y - (ENGINE_SIZE.y - ENGINE_SUNK) * SIDE_SCALE * unit())


func _gauge_at() -> Vector2:
	var u := unit()
	var across := (size.x - GAUGE_SIZE.x * GAUGE_SCALE * u) * 0.5
	# (side by side: sunk until only its instruments stand above the screen's edge; upright: raised
	# so that they clear the two housings in front of it)
	return Vector2(across, size.y - (455.0 if is_wide() else 910.0) * GAUGE_SCALE * u)


func stick_home() -> Vector2:
	return _helm_at() + HELM_WELL * SIDE_SCALE * unit()


func boost_home() -> Vector2:
	return _engine_at() + ENGINE_WELL * SIDE_SCALE * unit()


## Where the lever's handle is for a speed (0..1): a point along its slot.
func lever_at(at_speed: float) -> Vector2:
	var t := clampf(at_speed, 0.0, 1.0)
	var a: Vector2 = SLOT[0]
	var b: Vector2 = SLOT[1]
	var c: Vector2 = SLOT[2]
	return _engine_at() + a.lerp(b, t).lerp(b.lerp(c, t), t) * SIDE_SCALE * unit()


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
				# (a touch on the helm itself pushes it; one elsewhere puts the helm there)
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
	_draw_gauges(u)
	_draw_helm(u)
	_draw_engine(u)


# The instrument housing, and what moves on it.
func _draw_gauges(u: float) -> void:
	var at := _gauge_at()
	var s := GAUGE_SCALE * u
	draw_texture_rect(_picture("gauge_module"), Rect2(at, GAUGE_SIZE * s), false, Color(1.0, 1.0, 1.0, SEE))
	# The tubes: lit one for each time the fish has grown into something new.
	for k in mini(level, TUBES):
		var where := at + Vector2(TUBE_XS[k], TUBE_Y) * s
		var flicker := 0.8 + 0.2 * sin(Time.get_ticks_msec() * 0.011 + k * 1.7)
		# (the housing's own dark tube, with a glow and a hot filament drawn in it)
		draw_circle(where, 44.0 * s, Color(1.0, 0.5, 0.12, 0.22 * flicker))
		draw_circle(where, 26.0 * s, Color(1.0, 0.6, 0.15, 0.3 * flicker))
		draw_line(where + Vector2(0.0, -34.0) * s, where + Vector2(0.0, 34.0) * s, Color(1.0, 0.75, 0.3, 0.9 * flicker), 5.0 * s, true)
	# The sonar: a sweep going round, a ring, and what is about (hunters red, food green).
	var scope := at + SCOPE * s
	var r := SCOPE_RADIUS * s
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
	# The dials' needles: speed, depth, and how much burst is left.
	_needle(at + DIAL_SPEED * s, speed, s, true)
	_needle(at + DIAL_DEPTH * s, depth, s, false)
	_needle(at + DIAL_BURST * s, stamina, s, false)


# A dial's needle, from its lower left stop (0) round over the top to its lower right stop (1).
func _needle(hub: Vector2, value: float, s: float, trembles: bool) -> void:
	var turn := lerpf(-2.2, 2.2, clampf(value, 0.0, 1.0))
	if trembles:
		turn += sin(Time.get_ticks_msec() * 0.03) * 0.015
	# (the needle's picture, 95 by 332, points straight up, 99 by 349, its hub 300 pixels down it)
	var long := 54.0 * s
	var wide := long * 99.0 / 300.0
	draw_set_transform(hub, turn)
	draw_texture_rect(_picture("needle"), Rect2(Vector2(-wide * 0.5, -long), Vector2(wide, long * 349.0 / 300.0)), false)
	draw_set_transform(Vector2.ZERO)


# The helm housing, the spark over it while the fish bursts, and the stick.
func _draw_helm(u: float) -> void:
	var at := _helm_at()
	var s := SIDE_SCALE * u
	draw_texture_rect(_picture("helm_module"), Rect2(at, HELM_SIZE * s), false, Color(1.0, 1.0, 1.0, SEE))
	if boost and stamina > 0.0:
		_spark(at + HELM_SPARK * s, 110.0 * s)
	var home := _stick_from if _stick_touch != -1 else stick_home()
	var knob := home + Vector2(stick.x, -stick.y) * 62.0 * u
	# (the shaft, from the boot in the socket up to the ball)
	draw_line(home, knob, Color(IRON, 0.95), 22.0 * u, true)
	draw_line(home, knob, Color(BRASS_DARK, 0.95), 13.0 * u, true)
	# (the ball's picture: its middle is 125 pixels down a picture 278 by 345)
	var ball := 150.0 * s
	draw_texture_rect(_picture("knob"), Rect2(knob - Vector2(ball * 0.5, ball * 128.0 / 265.0), Vector2(ball, ball * 340.0 / 265.0)), false,
			Color(1.0, 1.0, 1.0, 1.0 if _stick_touch != -1 else 0.92))


# The engine housing, the plunger in its recess, and the lever in its slot.
func _draw_engine(u: float) -> void:
	var at := _engine_at()
	var s := SIDE_SCALE * u
	draw_texture_rect(_picture("engine_module"), Rect2(at, ENGINE_SIZE * s), false, Color(1.0, 1.0, 1.0, SEE))
	# The plunger: dim at rest, sunk and glowing while it is held.
	var well := boost_home()
	var wide := (222.0 if boost else 232.0) * s
	_stamp("plunger_lit" if boost else "plunger", well, Vector2(wide, wide * 337.0 / 348.0), 1.0)
	if boost:
		draw_circle(well, 120.0 * s, Color(1.0, 0.55, 0.15, 0.16))
	# The lever: its picture's pivot boss (58, 310 in a picture 298 by 371) rides in the slot, the
	# grip standing up and out of it.
	var grip := lever_at(throttle)
	var big := 0.62 * s
	draw_texture_rect(_picture("lever"), Rect2(grip - Vector2(55.0, 318.0) * big, Vector2(296.0, 375.0) * big), false,
			Color(1.0, 1.0, 1.0, 1.0 if _lever_touch != -1 else 0.95))


# A spark between the electrodes: a jagged blue-white line that is never the same twice.
func _spark(at: Vector2, wide: float) -> void:
	var lift := (fmod(Time.get_ticks_msec() * 0.004, 1.0) - 0.5) * wide * 0.5
	var line := PackedVector2Array()
	for k in 9:
		var share := k / 8.0
		line.append(at + Vector2(lerpf(-wide, wide, share) * 0.5, lift + randf_range(-0.09, 0.09) * wide * sin(share * PI)))
	draw_polyline(line, Color(0.45, 0.7, 1.0, 0.5), wide * 0.07, true)
	draw_polyline(line, Color(0.9, 0.97, 1.0, 0.95), wide * 0.025, true)


func _picture(named: String) -> Texture2D:
	if not _art.has(named):
		_art[named] = load(ART % named)
	return _art[named]


# One of the pictures, its middle at a place, of a size, so solid.
func _stamp(named: String, at: Vector2, of_size: Vector2, solid: float) -> void:
	draw_texture_rect(_picture(named), Rect2(at - of_size * 0.5, of_size), false, Color(1.0, 1.0, 1.0, solid))
