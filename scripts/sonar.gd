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
## reef, the open sea, the trench), where it lies from the fish; one further off than the scope
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
	"reef": {"strokes": [[Vector2(0.0, -0.9), Vector2(0.0, 0.1)], [Vector2(0.0, 0.1), Vector2(-0.6, 0.8)], [Vector2(0.0, 0.1), Vector2(0.6, 0.8)], [Vector2(0.0, -0.3), Vector2(0.7, 0.1)], [Vector2(0.0, -0.3), Vector2(-0.7, 0.1)]], "colour": Color(1.0, 0.6, 0.7)},
	"open": {"strokes": [[Vector2(-0.9, 0.0), Vector2(-0.45, 0.45), Vector2(0.0, 0.0), Vector2(0.45, 0.45), Vector2(0.9, 0.0)]], "colour": Color(0.6, 0.8, 1.0)},
	"trench": {"strokes": [[Vector2(-0.9, 0.7), Vector2(-0.3, 0.7), Vector2(0.0, -0.9), Vector2(0.3, 0.7), Vector2(0.9, 0.7)]], "colour": Color(0.8, 0.65, 1.0)},
}

## What it shows: where each thing is from the fish (x to its right, y ahead, metres) and what it
## is (z: 0 food, 1 a hunter); the landmarks, the same way, with their names; and the way the fish
## is heading (radians round from north, the sea's -Z, turning towards east).
var blips: Array[Vector3] = []
var landmarks: Array = []
var heading := 0.0

var _face: Face


func _init() -> void:
	var tube := SubViewport.new()
	tube.size = Vector2i(SIZE, SIZE)
	tube.transparent_bg = true
	tube.disable_3d = true
	tube.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(tube)
	_face = Face.new()
	_face.scope = self
	_face.size = Vector2(SIZE, SIZE)
	tube.add_child(_face)
	texture = tube.get_texture()
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_SCALE
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var glass := ShaderMaterial.new()
	glass.shader = load("res://shaders/sonar_crt.gdshader")
	material = glass


## Puts it over a scope whose middle and radius are given on the screen.
func fit(middle: Vector2, radius: float) -> void:
	position = middle - Vector2(radius, radius)
	size = Vector2(radius, radius) * 2.0


## The flat picture the tube shows.
class Face:
	extends Control
	var scope: Sonar

	func _process(_delta: float) -> void:
		queue_redraw()

	func _draw() -> void:
		var middle := size * 0.5
		var r := size.x * 0.5
		var font := get_theme_default_font()
		var green := Color(0.4, 1.0, 0.45)
		# the sweep, and the rings
		var sweep := Time.get_ticks_msec() * 0.0022
		for k in 18:
			var way := Vector2.from_angle(sweep - k * 0.05)
			draw_line(middle, middle + way * r * 0.8, Color(green, 0.55 * (1.0 - k / 18.0)), 4.0, true)
		draw_arc(middle, r * 0.4, 0.0, TAU, 40, Color(green, 0.28), 2.0, true)
		draw_arc(middle, r * 0.8, 0.0, TAU, 56, Color(green, 0.4), 2.0, true)
		draw_line(middle - Vector2(r * 0.8, 0.0), middle + Vector2(r * 0.8, 0.0), Color(green, 0.12), 1.5)
		draw_line(middle - Vector2(0.0, r * 0.8), middle + Vector2(0.0, r * 0.8), Color(green, 0.12), 1.5)
		# the fish itself: a little arrow, ahead up
		draw_colored_polygon(PackedVector2Array([middle + Vector2(0.0, -9.0), middle + Vector2(6.0, 7.0), middle + Vector2(-6.0, 7.0)]), Color(0.7, 1.0, 0.7, 0.95))
		# the landmarks: a sign each, held at the rim when it is further off than the scope sees
		for mark: Array in scope.landmarks:
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
				draw_polyline(line, colour, 2.5, true)
			if far:
				# (a tick outside it, pointing the way)
				var way := off.normalized()
				draw_line(middle + way * r * 0.71, middle + way * r * 0.78, colour, 2.5, true)
		# what is about (hunters red, food green), each brightest as the sweep passes it
		for blip in scope.blips:
			var off := Vector2(blip.x, -blip.y) / RANGE
			if off.length() > 0.95:
				continue
			var lag := fposmod(sweep - off.angle(), TAU) / TAU
			var bright := 0.45 + 0.55 * (1.0 - lag)
			var colour := Color(1.0, 0.25, 0.15) if blip.z > 0.5 else Color(0.5, 1.0, 0.5)
			draw_circle(middle + off * r * 0.8, 6.5 if blip.z > 0.5 else 4.5, Color(colour, bright))
		# the compass: N, E, S and W round the rim, turning as the fish does; north brighter
		for k in 4:
			var bearing := k * PI * 0.5 - scope.heading
			var at := middle + Vector2(sin(bearing), -cos(bearing)) * r * 0.9
			var said := "NESW"[k]
			var high := 26
			var wide := font.get_string_size(said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high).x
			draw_string(font, at + Vector2(-wide * 0.5, high * 0.36), said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, Color(1.0, 0.9, 0.5) if k == 0 else Color(green, 0.9))
		for k in 8:
			var bearing := (k + 0.5) * PI * 0.25 - scope.heading
			var way := Vector2(sin(bearing), -cos(bearing))
			draw_line(middle + way * r * 0.84, middle + way * r * 0.95, Color(green, 0.5), 2.0, true)
