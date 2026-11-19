class_name Sonar
extends TextureRect
## The sonar scope's picture, as an old cathode-ray tube shows it (the user, 2026-11-18: "the
## sonar needs a bubble crt effect and filter, and should show icons to landmarks on the map";
## before that, "The sonar radar needs caridnal direction indicators as well"). The sweep, the
## blips, the compass points and the landmarks are drawn flat into a small picture of their own
## (Face, in a SubViewport), and this shows that picture through shaders/sonar_crt.gdshader:
## bulged like the tube's glass, with scan lines, a glow round what is lit, a dark rim, a flicker
## and a glint. TouchPad lays it over the scope of the panel's model and feeds it.
##
## Ahead of the fish is up. What hunts it is red, what it can eat green. A landmark is a small
## sign for a part of the sea (LANDMARKS: the river mouth, the sea grass, the sand, the kelp, the
## reef, the open sea, the trench; and the boat, whose net the fish is sold into), where it lies from the fish; one further off than the scope
## sees is held at the rim, on its bearing, so the scope always points the way to each.

const SIZE := 256
## How far the scope sees (m).
const RANGE := 30.0
## A sign for each kind of landmark, as strokes in a square from -1 to 1 (y up), and its colour.
const LANDMARKS := {
	"river": {"strokes": [[Vector2(-0.9, 0.4), Vector2(-0.3, 0.7), Vector2(0.3, 0.1), Vector2(0.9, 0.4)], [Vector2(-0.9, -0.3), Vector2(-0.3, 0.0), Vector2(0.3, -0.6), Vector2(0.9, -0.3)]], "colour": Color(0.5, 0.85, 1.0)},
	"grass": {"strokes": [[Vector2(-0.6, -0.8), Vector2(-0.8, 0.5)], [Vector2(0.0, -0.8), Vector2(0.0, 0.9)], [Vector2(0.6, -0.8), Vector2(0.8, 0.5)]], "colour": Color(0.55, 1.0, 0.5)},
	"sand": {"strokes": [[Vector2(-0.9, -0.5), Vector2(-0.3, 0.2), Vector2(0.3, -0.2), Vector2(0.9, 0.4)], [Vector2(-0.5, -0.8), Vector2(0.5, -0.8)]], "colour": Color(1.0, 0.9, 0.55)},
	"kelp": {"strokes": [[Vector2(0.0, -0.9), Vector2(0.25, -0.3), Vector2(-0.25, 0.3), Vector2(0.0, 0.9)], [Vector2(0.2, -0.4), Vector2(0.75, -0.1)], [Vector2(-0.2, 0.2), Vector2(-0.75, 0.5)]], "colour": Color(0.75, 0.95, 0.35)},
	# (the reef is the sunken liner's now: a hull with two funnels)
	"reef": {"strokes": [[Vector2(-0.9, 0.0), Vector2(0.9, 0.0), Vector2(0.6, -0.5), Vector2(-0.7, -0.5), Vector2(-0.9, 0.0)], [Vector2(-0.3, 0.0), Vector2(-0.3, 0.55)], [Vector2(0.2, 0.0), Vector2(0.2, 0.55)]], "colour": Color(1.0, 0.6, 0.7)},
	# (an anchor)
	"docks": {"strokes": [[Vector2(0.0, 0.9), Vector2(0.0, -0.8)], [Vector2(-0.4, 0.55), Vector2(0.4, 0.55)], [Vector2(-0.7, -0.25), Vector2(-0.45, -0.7), Vector2(0.0, -0.85), Vector2(0.45, -0.7), Vector2(0.7, -0.25)]], "colour": Color(0.7, 0.92, 0.95)},
	# (a temple front: Atlantis)
	"ruins": {"strokes": [[Vector2(-0.8, -0.8), Vector2(0.8, -0.8)], [Vector2(-0.55, -0.8), Vector2(-0.55, 0.35)], [Vector2(0.0, -0.8), Vector2(0.0, 0.35)], [Vector2(0.55, -0.8), Vector2(0.55, 0.35)], [Vector2(-0.8, 0.35), Vector2(0.0, 0.9), Vector2(0.8, 0.35), Vector2(-0.8, 0.35)]], "colour": Color(1.0, 0.85, 0.45)},
	# (crossed cutlasses: the pirate ship)
	"pirate": {"strokes": [[Vector2(-0.75, -0.8), Vector2(0.7, 0.85)], [Vector2(0.75, -0.8), Vector2(-0.7, 0.85)], [Vector2(-0.95, -0.45), Vector2(-0.45, -0.95)], [Vector2(0.95, -0.45), Vector2(0.45, -0.95)]], "colour": Color(0.95, 0.75, 0.6)},
	# (the shrimp boat, where its net is: a hull, a mast and a net hanging off it; DESIGN.md's loop)
	"boat": {"strokes": [[Vector2(-0.9, 0.1), Vector2(0.9, 0.1), Vector2(0.55, -0.35), Vector2(-0.6, -0.35), Vector2(-0.9, 0.1)], [Vector2(-0.1, 0.1), Vector2(-0.1, 0.9)], [Vector2(-0.1, 0.9), Vector2(0.7, 0.45)], [Vector2(0.7, 0.45), Vector2(0.7, -0.75)], [Vector2(0.5, -0.6), Vector2(0.9, -0.6)]], "colour": Color(1.0, 0.95, 0.75)},
	"open": {"strokes": [[Vector2(-0.9, 0.0), Vector2(-0.45, 0.45), Vector2(0.0, 0.0), Vector2(0.45, 0.45), Vector2(0.9, 0.0)]], "colour": Color(0.6, 0.8, 1.0)},
	"trench": {"strokes": [[Vector2(-0.9, 0.7), Vector2(-0.3, 0.7), Vector2(0.0, -0.9), Vector2(0.3, 0.7), Vector2(0.9, 0.7)]], "colour": Color(0.8, 0.65, 1.0)},
}

## What it shows: where each thing is from the fish (x to its right, y ahead, metres) and what it
## is (z: 0 food, 1 a hunter, with how far above or below the fish it is added by `high`: the user,
## 2026-11-18, "the sonar map needs to show objects relation to you in 3d"); the landmarks, the same way, with their names; and the way the fish
## is heading (radians round from north, the sea's -Z, turning towards east).
var blips: Array[Vector3] = []
var landmarks: Array = []
var heading := 0.0


# The flat picture is drawn in five layers, bottom to top, each redrawn only when what it shows
# has changed (tools/PERF.md: drawn whole every frame it cost about 0.7 ms of a frame): the rings
# (never), the sweep and the fish's arrow (every frame), the landmarks (when new ones come, a few
# times a second), the blips (every other frame: they brighten as the sweep passes), the compass (when
# the heading turns).
var _rings: Layer
var _sweep: Layer
var _marks: Layer
var _blips: Layer
var _compass: Layer
var _marks_of: Array = []
var _compass_at := INF
var _blips_of: Array[Vector3] = []
var _frame := 0
var _tube: SubViewport


## How far above (or below) the fish a thing is, folded into a blip's z: a quarter at TALL metres
## up, minus a quarter that far down.
const TALL := 8.0
static func high(up: float) -> float:
	return clampf(up / TALL, -1.0, 1.0) * 0.25


func _init() -> void:
	var tube := SubViewport.new()
	tube.size = Vector2i(SIZE, SIZE)
	tube.transparent_bg = true
	tube.disable_3d = true
	tube.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(tube)
	_tube = tube
	_rings = _layer(tube, _draw_rings)
	_sweep = _layer(tube, _draw_sweep)
	_marks = _layer(tube, _draw_marks)
	_blips = _layer(tube, _draw_blips)
	_compass = _layer(tube, _draw_compass)
	texture = tube.get_texture()
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_SCALE
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var glass := ShaderMaterial.new()
	glass.shader = load("res://shaders/sonar_crt.gdshader")
	material = glass


func _layer(tube: SubViewport, painter: Callable) -> Layer:
	var made := Layer.new()
	made.painter = painter
	made.size = Vector2(SIZE, SIZE)
	made.mouse_filter = Control.MOUSE_FILTER_IGNORE
	tube.add_child(made)
	return made


func _process(_delta: float) -> void:
	_frame += 1
	# (a phone draws the scope every other frame: it is about 120 draws of lines and dots, each dear
	# in a phone's browser; CLAUDE.md, "Decision: a phone tier")
	if Tier.phone():
		if _frame % 2 == 1:
			return
		_tube.render_target_update_mode = SubViewport.UPDATE_ONCE
	_sweep.queue_redraw()
	# (the blips every other frame: they move only when Main sounds out again, a few times a
	# second, and their brightening as the sweep passes moves on by under 1% a frame)
	if _frame % 2 == 0 or not is_same(blips, _blips_of):
		_blips_of = blips
		_blips.queue_redraw()
	if not is_same(landmarks, _marks_of):
		_marks_of = landmarks
		_marks.queue_redraw()
	if absf(angle_difference(heading, _compass_at)) > 0.003 or is_inf(_compass_at):
		_compass_at = heading
		_compass.queue_redraw()


## Puts it over a scope whose middle and radius are given on the screen.
func fit(middle: Vector2, radius: float) -> void:
	position = middle - Vector2(radius, radius)
	size = Vector2(radius, radius) * 2.0


## One layer of the flat picture the tube shows.
class Layer:
	extends Control
	var painter: Callable

	func _draw() -> void:
		painter.call(self)


func _sweep_angle() -> float:
	return Time.get_ticks_msec() * 0.0022


const GREEN := Color(0.4, 1.0, 0.45)


# The rings and the cross.
func _draw_rings(on: Control) -> void:
	var middle := on.size * 0.5
	var r := on.size.x * 0.5
	on.draw_arc(middle, r * 0.4, 0.0, TAU, 40, Color(GREEN, 0.28), 2.0, true)
	on.draw_arc(middle, r * 0.8, 0.0, TAU, 56, Color(GREEN, 0.4), 2.0, true)
	on.draw_line(middle - Vector2(r * 0.8, 0.0), middle + Vector2(r * 0.8, 0.0), Color(GREEN, 0.12), 1.5)
	on.draw_line(middle - Vector2(0.0, r * 0.8), middle + Vector2(0.0, r * 0.8), Color(GREEN, 0.12), 1.5)


# The sweep, and the fish itself: a little arrow, ahead up.
func _draw_sweep(on: Control) -> void:
	var middle := on.size * 0.5
	var r := on.size.x * 0.5
	var sweep := _sweep_angle()
	for k in 18:
		var way := Vector2.from_angle(sweep - k * 0.05)
		on.draw_line(middle, middle + way * r * 0.8, Color(GREEN, 0.55 * (1.0 - k / 18.0)), 4.0, true)
	on.draw_colored_polygon(PackedVector2Array([middle + Vector2(0.0, -9.0), middle + Vector2(6.0, 7.0), middle + Vector2(-6.0, 7.0)]), Color(0.7, 1.0, 0.7, 0.95))


# The landmarks: a sign each, held at the rim when it is further off than the scope sees.
func _draw_marks(on: Control) -> void:
	var middle := on.size * 0.5
	var r := on.size.x * 0.5
	for mark: Array in landmarks:
		var sign: Dictionary = LANDMARKS.get(mark[0], {})
		if sign.is_empty():
			continue
		var off := Vector2(mark[1].x, -mark[1].y) / RANGE
		var far := off.length() > 0.62
		if far:
			off = off.normalized() * 0.62
		var at := middle + off * r
		var big := r * (0.085 if far else 0.11)
		var colour := Color(sign.colour, 0.75 if far else 1.0)
		for stroke: Array in sign.strokes:
			var line := PackedVector2Array()
			for point: Vector2 in stroke:
				line.append(at + Vector2(point.x, -point.y) * big)
			on.draw_polyline(line, colour, 2.5, true)
		if far:
			# (a tick outside it, pointing the way)
			var way := off.normalized()
			on.draw_line(middle + way * r * 0.71, middle + way * r * 0.78, colour, 2.5, true)


# What is about (hunters red, food green), each brightest as the sweep passes it.
func _draw_blips(on: Control) -> void:
	var middle := on.size * 0.5
	var r := on.size.x * 0.5
	var sweep := _sweep_angle()
	for blip in blips:
		var off := Vector2(blip.x, -blip.y) / RANGE
		if off.length() > 0.95:
			continue
		var lag := fposmod(sweep - off.angle(), TAU) / TAU
		var bright := 0.45 + 0.55 * (1.0 - lag)
		var hunter := blip.z > 0.5
		var colour := Color(1.0, 0.25, 0.15) if hunter else Color(0.5, 1.0, 0.5)
		# (as on an old three-dimensional scope: a stalk stands from its place on the fish's own
		# level up or down to the thing itself, which is an arrowhead pointing the way it lies)
		var up := (blip.z - (1.0 if hunter else 0.0)) * 4.0
		var foot := middle + off * r * 0.8
		var at := foot + Vector2(0.0, -up * r * 0.11)
		var big := 7.0 if hunter else 5.0
		if absf(up) < 0.2:
			on.draw_circle(at, big, Color(colour, bright))
		else:
			on.draw_line(foot, at, Color(colour, bright * 0.6), 2.0, true)
			on.draw_circle(foot, 2.0, Color(colour, bright * 0.6))
			var tip := -signf(up) * big * 1.3
			on.draw_colored_polygon(PackedVector2Array([at + Vector2(0.0, tip), at + Vector2(big, -tip * 0.6), at + Vector2(-big, -tip * 0.6)]), Color(colour, bright))


# The compass: N, E, S and W round the rim, turning as the fish does; north brighter.
func _draw_compass(on: Control) -> void:
	var middle := on.size * 0.5
	var r := on.size.x * 0.5
	var font := on.get_theme_default_font()
	for k in 4:
		var bearing := k * PI * 0.5 - heading
		var at := middle + Vector2(sin(bearing), -cos(bearing)) * r * 0.9
		var said := "NESW"[k]
		var tall := 26
		var wide := font.get_string_size(said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, tall).x
		on.draw_string(font, at + Vector2(-wide * 0.5, tall * 0.36), said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, tall, Color(1.0, 0.9, 0.5) if k == 0 else Color(GREEN, 0.9))
	for k in 8:
		var bearing := (k + 0.5) * PI * 0.25 - heading
		var way := Vector2(sin(bearing), -cos(bearing))
		on.draw_line(middle + way * r * 0.84, middle + way * r * 0.95, Color(GREEN, 0.5), 2.0, true)
