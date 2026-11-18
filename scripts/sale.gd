class_name Sale
extends Control
## The sale (DESIGN.md, the loop, 3): the fish the run ended as, hauled up in the boat's net and
## sold. Shows the kind (the animal turning, and its name), its length, its worth a metre and the
## price, the price doubled (a crown) for the last of a growth line at its full length, the bonus
## (a star) for the first of its kind sold, the sum, and what is in the purse now. One round button
## (or Enter, Space, a gamepad's A) goes on to the shop.
##
## A plain screen for now (a later stage rebuilds it in the panel's brass): its whole interface is
## `show_receipt(receipt)` and the `done` signal.

signal done

var _receipt := {}
var _card: Hud.ChoiceCard
var _go: Knob
var _for := 0.0
# The middle of the column of numbers (x).
var _x := 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = false
	_go = Knob.new()
	_go.focus_mode = Control.FOCUS_NONE
	_go.paint = func(knob: Knob) -> void: Knob.arrow(knob, 0.0)
	_go.pressed.connect(_finish)
	add_child(_go)


## Shows a sale: what Purse.sell gave back.
func show_receipt(receipt: Dictionary) -> void:
	_receipt = receipt
	_for = 0.0
	if _card:
		_card.queue_free()
	_card = Hud.ChoiceCard.new()
	_card.kind = String(receipt.kind)
	_card.disabled = true
	_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_card)
	visible = true


func _finish() -> void:
	if not visible or _for < 0.4:
		return
	visible = false
	if _card:
		_card.queue_free()
		_card = null
	done.emit()


func _input(event: InputEvent) -> void:
	if visible and (event.is_action_pressed(&"ui_accept") or (event is InputEventJoypadButton and event.pressed and event.button_index == JOY_BUTTON_A)):
		_finish()


func _process(delta: float) -> void:
	if not visible:
		return
	_for += delta
	var u := minf(size.x, size.y) / 720.0
	var card := _card_box()
	if _card:
		_card.size = card.size
		_card.position = card.position
	_go.size = Vector2(150.0, 150.0) * u
	_go.position = Vector2(size.x * 0.5, size.y - 110.0 * u) - _go.size * 0.5
	queue_redraw()


func _draw() -> void:
	if _receipt.is_empty():
		return
	var u := _unit()
	var font := get_theme_default_font()
	var ink := Color(0.92, 0.88, 0.78)
	var gold := Color(1.0, 0.82, 0.35)
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.03, 0.03, 0.05, 0.8))
	var card := _card_box()
	# (upright: the writing under the animal; on its side, beside it)
	var upright := size.y > size.x
	_x = size.x * 0.5 if upright else card.end.x + 60.0 * u + 170.0 * u
	# the kind's name, under the animal
	var named := String(_receipt.kind).replace("_", " ")
	var high := int(34.0 * u)
	var named_wide := font.get_string_size(named, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high).x
	draw_string(font, Vector2(card.get_center().x - named_wide * 0.5, card.end.y + 40.0 * u), named, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, ink)
	var y := card.end.y + 130.0 * u if upright else card.position.y + 50.0 * u
	# length x worth a metre = the price
	_say(font, "%.2f m  ×  %d" % [float(_receipt.length), int(_receipt.worth)], y, int(40.0 * u), ink, true)
	y += 56.0 * u
	if _receipt.doubled:
		_say(font, "×2", y, int(40.0 * u), gold, false, "crown")
		y += 56.0 * u
	if int(_receipt.bonus) > 0:
		_say(font, "+%d" % int(_receipt.bonus), y, int(40.0 * u), gold, true, "star")
		y += 56.0 * u
	draw_line(Vector2(_x - 150.0 * u, y - 34.0 * u), Vector2(_x + 150.0 * u, y - 34.0 * u), Color(ink, 0.6), 3.0 * u)
	y += 24.0 * u
	_say(font, "%d" % int(_receipt.total), y, int(64.0 * u), gold, true)
	y += 90.0 * u
	# the purse now: a purse of coins and the sum
	_say(font, "%d" % int(_receipt.money), y, int(44.0 * u), ink, false, "purse")


# One unit of the layout: by the shorter side, or on an upright screen by its width (a narrow
# phone has room down it for bigger writing).
func _unit() -> float:
	if size.y > size.x:
		return minf(size.x / 480.0, size.y / 900.0)
	return minf(size.x, size.y) / 720.0


# Where the animal's card goes: upright, high in the middle; on its side, to the left.
func _card_box() -> Rect2:
	var u := _unit()
	if size.y > size.x:
		var card := 280.0 * u
		return Rect2(Vector2(size.x * 0.5 - card * 0.5, size.y * 0.1), Vector2(card, card))
	var card := 260.0 * u
	return Rect2(Vector2(size.x * 0.5 - 60.0 * u - card - 60.0 * u, size.y * 0.42 - card * 0.5), Vector2(card, card))


# A line of writing across the column at a height, with a coin after it, or a sign before it.
func _say(font: Font, said: String, y: float, high: int, colour: Color, coin := false, sign := "") -> void:
	var wide := font.get_string_size(said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high).x
	var extra := high * 1.1 if coin or sign != "" else 0.0
	var left := _x - (wide + extra) * 0.5
	if sign != "":
		Knob.symbol(self, sign, Vector2(left + high * 0.45, y - high * 0.33), high * 0.45)
		left += extra
	draw_string(font, Vector2(left, y), said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, colour)
	if coin:
		Knob.symbol(self, "coin", Vector2(left + wide + high * 0.65, y - high * 0.33), high * 0.4)


## A round button drawn by a function given to it (the sale's and the shop's), and the signs the
## screens share.
class Knob:
	extends Button
	var paint: Callable
	## Lit, ready to press (else dim).
	var lit := true

	func _ready() -> void:
		flat = true
		for state: StringName in [&"normal", &"hover", &"pressed", &"focus", &"disabled"]:
			add_theme_stylebox_override(state, StyleBoxEmpty.new())

	func _process(_delta: float) -> void:
		queue_redraw()

	func _draw() -> void:
		if paint.is_valid() and size.x > 4.0:
			paint.call(self)

	## A round button with an arrow in it, pointing `angle` radians round from the right.
	static func arrow(knob: Knob, angle: float) -> void:
		var middle := knob.size * 0.5
		var r := knob.size.x * 0.5
		var lit := knob.lit and not knob.disabled
		var ink := Color(1.0, 0.92, 0.7, 1.0 if lit else 0.35)
		knob.draw_circle(middle, r, Color(0.45, 0.32, 0.12, (0.95 if knob.button_pressed else 0.8) if lit else 0.35))
		knob.draw_arc(middle, r - 3.0, 0.0, TAU, 64, ink, r * 0.06, true)
		var way := Vector2.from_angle(angle)
		var side := way.orthogonal()
		knob.draw_line(middle - way * r * 0.42, middle + way * r * 0.1, ink, r * 0.16, true)
		knob.draw_colored_polygon(PackedVector2Array([middle + way * r * 0.5, middle + way * r * 0.02 + side * r * 0.32, middle + way * r * 0.02 - side * r * 0.32]), ink)

	## Signs drawn on any CanvasItem: "coin", "star", "crown", "purse", "lock", "antenna".
	static func symbol(on: CanvasItem, named: String, at: Vector2, r: float, dim := false) -> void:
		var a := 0.4 if dim else 1.0
		var gold := Color(1.0, 0.8, 0.3, a)
		var dark := Color(0.45, 0.3, 0.08, a)
		match named:
			"coin":
				on.draw_circle(at, r, gold)
				on.draw_arc(at, r * 0.72, 0.0, TAU, 24, dark, r * 0.14, true)
			"star":
				var points := PackedVector2Array()
				for k in 10:
					var reach := r if k % 2 == 0 else r * 0.45
					points.append(at + Vector2.from_angle(-PI * 0.5 + k * PI / 5.0) * reach)
				on.draw_colored_polygon(points, gold)
			"crown":
				var w := r * 2.0
				var h := r * 1.4
				var o := at - Vector2(r, 0.0)
				on.draw_colored_polygon(PackedVector2Array([o + Vector2(0.0, h * 0.5), o + Vector2(0.0, -h * 0.5), o + Vector2(w * 0.25, 0.0), o + Vector2(w * 0.5, -h * 0.5),
						o + Vector2(w * 0.75, 0.0), o + Vector2(w, -h * 0.5), o + Vector2(w, h * 0.5)]), gold)
			"purse":
				on.draw_circle(at + Vector2(0.0, r * 0.2), r * 0.85, Color(0.55, 0.36, 0.16, a))
				on.draw_colored_polygon(PackedVector2Array([at + Vector2(-r * 0.45, -r * 0.55), at + Vector2(r * 0.45, -r * 0.55), at + Vector2(r * 0.2, -r * 0.3), at + Vector2(-r * 0.2, -r * 0.3)]), Color(0.55, 0.36, 0.16, a))
				on.draw_circle(at + Vector2(0.0, r * 0.25), r * 0.32, gold)
			"lock":
				on.draw_arc(at + Vector2(0.0, -r * 0.2), r * 0.45, PI, TAU, 16, Color(0.7, 0.7, 0.72, a), r * 0.18, true)
				on.draw_rect(Rect2(at + Vector2(-r * 0.7, -r * 0.2), Vector2(r * 1.4, r * 1.1)), Color(0.7, 0.7, 0.72, a))
			"antenna":
				# (the machine's signal: a mast with waves going out from its top)
				var top := at + Vector2(0.0, -r * 0.5)
				on.draw_line(at + Vector2(-r * 0.5, r), top, gold, r * 0.14, true)
				on.draw_line(at + Vector2(r * 0.5, r), top, gold, r * 0.14, true)
				on.draw_line(at + Vector2(-r * 0.3, r * 0.4), at + Vector2(r * 0.3, r * 0.4), gold, r * 0.1, true)
				for k in 2:
					on.draw_arc(top, r * (0.4 + k * 0.35), -PI * 0.8, -PI * 0.2, 12, gold, r * 0.1, true)
