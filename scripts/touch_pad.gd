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
## They are pictures (textures/controls/*.png), rendered from brass models built in Blender by
## tools/build_controls.py, and drawn see-through (`SEE`) so the sea shows behind them (the user:
## "The controls should still be see through", "can you generate images for the controls ? Rather
## than shapes"). Only what changes is drawn here: the gauge's level and the lit orders.
##
## They sit in a panel across the bottom of the screen (the user, 2026-11-18: "There should be a
## whole control panel on the bottom part, that also shows speed and your evolution level and
## maybe any special ability buttons, with and old rusted and e gad frankenstein technology
## aesthetic"): rusted riveted iron, humped up round the helm and round the engine fittings and
## low between them, with a speed gauge, a rack of vacuum tubes that light one for each time the
## fish has become something bigger, a copper coil, a pair of electrodes that sparks climb while
## it bursts, and (where the screen is wide enough) two sockets bolted shut, kept for special
## abilities that do not exist yet.
##
## All are always drawn. A touch anywhere in the lower left takes the helm (it moves under the
## thumb); a touch on the arc takes the lever; a touch anywhere else in the lower right holds the
## burst. A mouse works as a finger (the project turns mouse presses into touches).

const BRASS := Color(0.80, 0.62, 0.26)
const BRASS_LIGHT := Color(1.0, 0.88, 0.55)
const BRASS_DARK := Color(0.33, 0.23, 0.09)
const IRON := Color(0.10, 0.12, 0.14)
const GLASS := Color(0.75, 0.95, 0.9)
const ART := "res://textures/controls/%s.png"
## How solid the fittings are drawn: at rest, and the part under a finger.
const SEE := 0.58
const SEE_HELD := 0.9
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
## Shown on the panel: how fast the fish is going (0 still to 1 flat out, bursting), and how many
## times it has become something bigger (a vacuum tube lights for each).
var speed := 0.0
var level := 0
## How many tubes the panel has.
const TUBES := 7
## How solid the rusted panel itself is drawn (the sea shows through it).
const PANEL_SEE := 0.5

var _stick_touch := -1
var _boost_touch := -1
var _lever_touch := -1
var _stick_from := Vector2.ZERO
var _art := {}


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	# (the rust picture is laid over the panel again and again)
	texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED


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
	_draw_panel(u)
	# The helm: its plate, and the stick's brass ball where the thumb has pushed it.
	var home := _stick_from if _stick_touch != -1 else stick_home()
	_stamp("helm_plate", home, 240.0 * u, SEE)
	var knob := home + Vector2(stick.x, -stick.y) * 105.0 * u * 0.58
	draw_line(home, knob, Color(BRASS_DARK, SEE), 14.0 * u, true)
	_stamp("helm_knob", knob, 90.0 * u, SEE_HELD if _stick_touch != -1 else SEE + 0.15)
	# The speed lever: its track round the burst button, the orders lit up to where the handle is,
	# and the handle, turned to reach in to the hub.
	var at := boost_home()
	_stamp("lever_arc", at, 420.0 * u, SEE)
	for k in 5:
		var share := k / 4.0
		if throttle >= share - 0.02:
			var way := Vector2.from_angle(lerpf(SLOW_AT, FULL_AT, share))
			var near := lever_radius() + 23.0 * u
			draw_line(at + way * near, at + way * (near + (9.0 + 5.0 * k) * u), Color(BRASS_LIGHT, 0.9), (3.2 + 0.8 * k) * u, true)
	var grip := lever_at(throttle)
	_stamp("lever_handle", grip, 200.0 * u, SEE_HELD if _lever_touch != -1 else SEE + 0.2, (grip - at).angle())
	# The burst: its plate, the gauge's level in the plate's channel, and the plunger's cap (sunk
	# and lit while it is held).
	_stamp("burst_plate", at, 200.0 * u, SEE)
	if stamina > 0.01:
		draw_arc(at, 70.0 * u, -PI * 0.5, -PI * 0.5 + TAU * stamina, 64, Color(0.45, 0.95, 0.7, 0.85), 9.0 * u, true)
	_stamp("burst_cap", at, (124.0 if boost else 130.0) * u, SEE_HELD if boost else SEE + 0.12)
	if boost:
		draw_circle(at, 58.0 * u, Color(GLASS, 0.18))


# Where the panel's instruments go: between the helm's hump and the engine's.
func gauge_home() -> Vector2:
	var u := unit()
	return Vector2(lerpf(stick_home().x + 118.0 * u, boost_home().x - 178.0 * u, 0.5), size.y - (84.0 if is_wide() else 146.0) * u)


## Whether there is room between the helm and the engine fittings to lay the instruments side by
## side (a landscape screen): the panel is then lower in the middle, to leave the fish in view.
func is_wide() -> bool:
	return boost_home().x - stick_home().x > 620.0 * unit()


# How high the panel's top edge is at a place along the screen (a y): a hump round the helm, a
# bigger one round the burst button and its lever, and a low run between and beyond.
func panel_top(x: float) -> float:
	var u := unit()
	var top := size.y - (158.0 if is_wide() else 205.0) * u
	var helm := stick_home()
	var across := absf(x - helm.x)
	if across < 150.0 * u:
		top = minf(top, helm.y - sqrt(pow(150.0 * u, 2.0) - across * across))
	var engine := boost_home()
	across = absf(x - engine.x)
	if across < 222.0 * u:
		top = minf(top, engine.y - sqrt(pow(222.0 * u, 2.0) - across * across))
	return top


# The panel: the rusted plate (see-through), its riveted rim, and the instruments on it.
func _draw_panel(u: float) -> void:
	var rust: Texture2D = _picture("rust_plate")
	var points := PackedVector2Array()
	var uvs := PackedVector2Array()
	var steps := 72
	for k in steps + 1:
		var x := size.x * k / steps
		points.append(Vector2(x, panel_top(x)))
	points.append(Vector2(size.x, size.y))
	points.append(Vector2(0.0, size.y))
	for p in points:
		uvs.append(p / (400.0 * u))
	draw_colored_polygon(points, Color(1.0, 1.0, 1.0, PANEL_SEE), uvs, rust)
	# its rim: a dark line and a worn bright one, and a rivet every so often under it
	var rim := points.slice(0, steps + 1)
	draw_polyline(rim, Color(IRON, 0.85), 7.0 * u, true)
	draw_polyline(rim, Color(0.55, 0.3, 0.12, 0.8), 2.5 * u, true)
	var along := 0.0
	for k in range(1, rim.size()):
		along += rim[k].distance_to(rim[k - 1])
		if along > 58.0 * u:
			along = 0.0
			var inward := (rim[k] - rim[k - 1]).orthogonal().normalized()
			if inward.y < 0.0:
				inward = -inward
			_stamp("rivet", rim[k] + inward * 15.0 * u, 26.0 * u, 0.9)
	# The speed gauge, and its needle: from dead still at the lower left round to flat out.
	var at := gauge_home()
	var wide := is_wide()
	var big := 1.0
	_stamp("gauge_face", at, 130.0 * u * big, 0.92)
	var turn := lerpf(deg_to_rad(135.0), deg_to_rad(405.0), clampf(speed, 0.0, 1.0)) + sin(Time.get_ticks_msec() * 0.03) * 0.012
	var way := Vector2.from_angle(turn)
	draw_line(at - way * 9.0 * u * big, at + way * 43.0 * u * big, Color(0.5, 0.05, 0.03, 0.95), 3.5 * u * big, true)
	draw_circle(at, 6.0 * u * big, Color(BRASS_DARK, 1.0))
	# The tubes: a rack under the gauge, lit one for each time it has grown into something new.
	var rack := 18.0 * u * big
	for k in TUBES:
		var where := at + (Vector2(-175.0 * u + (k - (TUBES - 1) * 0.5) * rack, 6.0 * u) if wide else Vector2((k - (TUBES - 1) * 0.5) * rack, 78.0 * u))
		var lit := k < level
		if lit:
			var flicker := 0.75 + 0.25 * sin(Time.get_ticks_msec() * 0.011 + k * 1.7)
			draw_circle(where, 15.0 * u * big, Color(1.0, 0.5, 0.12, 0.22 * flicker))
		_stamp("tube_on" if lit else "tube_off", where, 44.0 * u * big, 0.95)
	# Mad-science furniture: a coil by the helm, and electrodes over the engine that sparks climb
	# while it bursts.
	_stamp("coil", Vector2(44.0 * u, size.y - 42.0 * u), 70.0 * u, 0.85)
	var poles := Vector2(boost_home().x + 96.0 * u, boost_home().y - 152.0 * u)
	_stamp("electrodes", poles, 110.0 * u, 0.9)
	if boost and stamina > 0.0:
		_spark(poles, u)
	# Where special abilities will go: two sockets bolted shut, if there is room for them.
	if wide:
		for k in 2:
			_stamp("socket", at + Vector2((125.0 + 88.0 * k) * u, 4.0 * u), 80.0 * u, 0.85)


# A spark between the electrodes, climbing: a jagged blue-white line that is never the same twice.
func _spark(poles: Vector2, u: float) -> void:
	var climb := fmod(Time.get_ticks_msec() * 0.0016, 1.0)
	var y := lerpf(22.0, -42.0, climb) * u
	var half := lerpf(15.0, 33.0, climb) * u
	var line := PackedVector2Array()
	for k in 9:
		var share := k / 8.0
		var jag := Vector2(0.0, randf_range(-7.0, 7.0) * u * sin(share * PI))
		line.append(poles + Vector2(lerpf(-half, half, share), y) + jag)
	draw_polyline(line, Color(0.55, 0.75, 1.0, 0.5), 6.0 * u, true)
	draw_polyline(line, Color(0.92, 0.97, 1.0, 0.95), 2.0 * u, true)


func _picture(named: String) -> Texture2D:
	if not _art.has(named):
		_art[named] = load(ART % named)
	return _art[named]


# One of the pictures, its middle at a place, `wide` across, so solid, turned.
func _stamp(named: String, at: Vector2, wide: float, solid: float, turn := 0.0) -> void:
	draw_set_transform(at, turn)
	draw_texture_rect(_picture(named), Rect2(Vector2(-wide, -wide) * 0.5, Vector2(wide, wide)), false, Color(1.0, 1.0, 1.0, solid))
	draw_set_transform(Vector2.ZERO)
