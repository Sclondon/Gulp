class_name Shop
extends Control
## The shop (DESIGN.md, the loop, 4), after a sale: what is in the purse, and the amplifier's
## steps, each how deep the machine's signal reaches with it and what it costs; the next step is
## bought by pressing it (or B) when there is money enough. The round button with the arrow down
## (or Enter, Space, a gamepad's A) sends the fish back down from the boat.
##
## Only the amplifier is here so far: the suit, the anchorages, the tools and the tackle come with
## the stages that use them (Claude's call: nothing that cannot be used yet).
##
## A plain screen for now (a later stage rebuilds it at the captain's chart table): its whole
## interface is `open(purse)`, `bought` and `dive`.

## A step of the amplifier was bought.
signal bought
## Back into the sea.
signal dive

var purse: Purse
var _steps: Array[Sale.Knob] = []
var _go: Sale.Knob
var _for := 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = false
	for k in Purse.AMP_DEPTH.size():
		var step := Sale.Knob.new()
		step.focus_mode = Control.FOCUS_NONE
		step.paint = _paint_step.bind(k)
		step.pressed.connect(_press_step.bind(k))
		add_child(step)
		_steps.append(step)
	_go = Sale.Knob.new()
	_go.focus_mode = Control.FOCUS_NONE
	_go.paint = func(knob: Sale.Knob) -> void: Sale.Knob.arrow(knob, PI * 0.5)
	_go.pressed.connect(_finish)
	add_child(_go)


func open(with: Purse) -> void:
	purse = with
	_for = 0.0
	visible = true


## Buys the next step of the amplifier, if it can be paid for.
func buy_next() -> bool:
	if purse and purse.buy_amp():
		bought.emit()
		return true
	return false


func _press_step(k: int) -> void:
	if purse and k == purse.amp + 1:
		buy_next()


func _finish() -> void:
	if not visible or _for < 0.4:
		return
	visible = false
	dive.emit()


func _input(event: InputEvent) -> void:
	if not visible:
		return
	if event.is_action_pressed(&"ui_accept") or (event is InputEventJoypadButton and event.pressed and event.button_index == JOY_BUTTON_A):
		_finish()
	elif event is InputEventKey and event.pressed and not event.echo and (event as InputEventKey).physical_keycode == KEY_B:
		buy_next()


func _process(delta: float) -> void:
	if not visible:
		return
	_for += delta
	var u := minf(size.x, size.y) / 720.0
	var many := _steps.size()
	var each := minf(170.0 * u, (size.x - 32.0 * u) / many - 12.0 * u)
	var row_y := _row_y()
	for k in many:
		_steps[k].size = Vector2(each, each * 1.25)
		_steps[k].position = Vector2(size.x * 0.5 + (k - (many - 1) * 0.5) * (each + 12.0 * u) - each * 0.5, row_y)
		_steps[k].disabled = not (k == purse.amp + 1 and purse.money >= Purse.AMP_PRICE[k])
	_go.size = Vector2(150.0, 150.0) * u
	_go.position = Vector2(size.x * 0.5, size.y - 110.0 * u) - _go.size * 0.5
	queue_redraw()


func _draw() -> void:
	if purse == null:
		return
	var u := minf(size.x, size.y) / 720.0
	var font := get_theme_default_font()
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.03, 0.03, 0.05, 0.85))
	# the purse
	var high := int(56.0 * u)
	var said := "%d" % purse.money
	var wide := font.get_string_size(said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high).x
	var y := size.y * (0.16 if size.y > size.x else 0.12)
	Sale.Knob.symbol(self, "purse", Vector2(size.x * 0.5 - wide * 0.5 - high * 0.5, y - high * 0.33), high * 0.45)
	draw_string(font, Vector2(size.x * 0.5 - wide * 0.5 + high * 0.2, y), said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, Color(1.0, 0.85, 0.45))
	# the amplifier's sign over its row of steps
	Sale.Knob.symbol(self, "antenna", Vector2(size.x * 0.5, _row_y() - 70.0 * u), 42.0 * u)


# One step of the amplifier: its depth, and its price (a coin), or a tick once had.
func _paint_step(knob: Sale.Knob, k: int) -> void:
	var had := k <= purse.amp
	var next := k == purse.amp + 1
	var can: bool = next and purse.money >= int(Purse.AMP_PRICE[k])
	var box := Rect2(Vector2.ZERO, knob.size)
	var fill := Color(0.16, 0.3, 0.18, 0.9) if had else (Color(0.45, 0.32, 0.12, 0.95 if knob.button_pressed else 0.85) if can else Color(0.12, 0.11, 0.1, 0.85))
	knob.draw_rect(box, fill)
	knob.draw_rect(box.grow(-2.0), Color(1.0, 0.85, 0.45) if can else Color(0.6, 0.55, 0.45, 0.6), false, 3.0 if can else 1.5)
	var font := knob.get_theme_default_font()
	var ink := Color(0.95, 0.92, 0.82, 1.0 if had or next else 0.5)
	var high := int(knob.size.x * 0.27)
	var said := "%d m" % int(Purse.AMP_DEPTH[k])
	var wide := font.get_string_size(said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high).x
	knob.draw_string(font, Vector2(knob.size.x * 0.5 - wide * 0.5, knob.size.y * 0.38), said, HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, ink)
	var low := Vector2(knob.size.x * 0.5, knob.size.y * 0.74)
	if had:
		# (a tick)
		var r := knob.size.x * 0.16
		knob.draw_polyline(PackedVector2Array([low + Vector2(-r, 0.0), low + Vector2(-r * 0.25, r * 0.7), low + Vector2(r, -r * 0.7)]), Color(0.55, 1.0, 0.6), r * 0.3, true)
	else:
		var price := "%d" % Purse.AMP_PRICE[k]
		var small := int(knob.size.x * 0.22)
		var price_wide := font.get_string_size(price, HORIZONTAL_ALIGNMENT_LEFT, -1.0, small).x
		var left := low.x - (price_wide + small * 1.0) * 0.5
		Sale.Knob.symbol(knob, "coin", Vector2(left + small * 0.35, low.y - small * 0.05), small * 0.35, not can)
		knob.draw_string(font, Vector2(left + small * 0.85, low.y + small * 0.33), price, HORIZONTAL_ALIGNMENT_LEFT, -1.0, small, Color(1.0, 0.85, 0.45, 1.0 if can else 0.5))


# How far down the row of steps is (higher on a wide screen, clear of the round button).
func _row_y() -> float:
	return size.y * (0.42 if size.y > size.x else 0.34)
