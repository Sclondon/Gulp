class_name Title
extends Node3D
## The start of the game: a shrimp boat on the sea over the place the fish starts. The user
## (2026-11-18): "the main menu / start of the game should be the boy from warren, a sea captain,
## and and oldtimy diver on a shrimping boat (look up reference pics). In the open back cabin of
## the shrimping boat should be a old timey franketstein computer hooked up to a helmet on the
## boys head- the controls for the pc are the controls for the game".
##
## So: the boat (models/shrimp_boat.glb) rocks on the swell; in its open cabin stands the
## computer, which is the game's own control panel (models/control_panel.glb, the same model the
## TouchPad shows, on a bench); the boy stands at it in a helmet (models/brain_helmet.glb) cabled
## to it; the captain and the diver stand on the deck behind. The eye stands astern looking into
## the cabin. When the game is started, Main sends the eye down through the surface to the fish:
## what the boy steers.
##
## It stands at the sea's surface (its origin is on the waterline). The boat's markers say where
## things go (tools/SHRIMP_BOAT.md); the figures are TitleFigures (tools/TITLE_FIGURES.md). Any
## part that is not there yet (a model not built) is left out.

const BOAT := "res://models/shrimp_boat.glb"
const PANEL := "res://models/control_panel.glb"
const HELMET := "res://models/brain_helmet.glb"
const FIGURES := "res://scripts/title_figures.gd"
## How big the computer is beside the model it shares with the TouchPad, and how high its bench is (m).
const COMPUTER := 0.3
const BENCH := 0.5
## The boy's head, as a radius over his hair (m): what the helmet is sized to.
const HEAD := 0.128
## Where things go on the boat if its model does not say (metres from its middle at the waterline;
## the bow is towards -Z).
const SPOTS := {
	"ConsoleSpot": Vector3(0.0, 0.9, 0.4),
	"BoySpot": Vector3(0.0, 0.9, 1.3),
	"CaptainSpot": Vector3(-1.3, 0.9, 3.4),
	"DiverSpot": Vector3(1.3, 0.9, 3.4),
	"HelmetCable": Vector3(0.0, 2.4, 0.4),
}

var boat: Node3D
var boy: Node3D
var _spots := {}
var _helmet: Node3D
var _cables: Array[Node3D] = []
var _sockets: Array[Node3D] = []
var _clock := 0.0


func _ready() -> void:
	boat = Node3D.new()
	add_child(boat)
	_spots = SPOTS.duplicate()
	if ResourceLoader.exists(BOAT):
		var hull: Node3D = (load(BOAT) as PackedScene).instantiate()
		boat.add_child(hull)
		# (its plank lines and grime are vertex colours)
		for mesh: MeshInstance3D in hull.find_children("*", "MeshInstance3D", true, false):
			for surface in mesh.mesh.get_surface_count():
				var paint := mesh.mesh.surface_get_material(surface) as StandardMaterial3D
				if paint:
					paint.vertex_color_use_as_albedo = true
		for named: String in SPOTS:
			var marker := hull.find_child(named) as Node3D
			if marker:
				_spots[named] = _place_in(marker, boat)
	# The computer: the control panel's three housings side by side on a bench, leaning back.
	var parts: Node3D = (load(HELMET) as PackedScene).instantiate()
	PanelModel.paint(parts, true, "res://textures/panel/helmet_atlas.png")
	var bench := parts.find_child("Bench") as Node3D
	bench.get_parent().remove_child(bench)
	bench.position = _spots["ConsoleSpot"] + Vector3(0.0, 0.0, 0.34)
	boat.add_child(bench)
	var computer: Node3D = (load(PANEL) as PackedScene).instantiate()
	PanelModel.paint(computer, true)
	computer.scale = Vector3.ONE * COMPUTER
	computer.position = _spots["ConsoleSpot"] + Vector3(0.0, BENCH, 0.2)
	computer.rotation.x = -0.14
	(computer.find_child("Helm") as Node3D).position.x = -(PanelModel.GAUGE_WIDE + PanelModel.SIDE_WIDE) * 0.5 - 0.15
	(computer.find_child("Engine") as Node3D).position.x = (PanelModel.GAUGE_WIDE + PanelModel.SIDE_WIDE) * 0.5 + 0.15
	boat.add_child(computer)
	# The three of them.
	if ResourceLoader.exists(FIGURES):
		var figures: GDScript = load(FIGURES)
		boy = figures.call(&"boy")
		boy.position = _spots["BoySpot"]
		boat.add_child(boy)
		var captain: Node3D = figures.call(&"captain")
		captain.position = _spots["CaptainSpot"]
		captain.rotation.y = PI * 0.8
		boat.add_child(captain)
		var diver: Node3D = figures.call(&"diver")
		diver.position = _spots["DiverSpot"]
		diver.rotation.y = -PI * 0.8
		boat.add_child(diver)
		# The helmet on the boy's head, and its two cables to the computer.
		var head: Node3D = figures.call(&"head_node", boy)
		if head:
			_helmet = parts.find_child("Helmet") as Node3D
			_helmet.get_parent().remove_child(_helmet)
			head.add_child(_helmet)
			# (built round a head of radius 1 with its face to +Z, as the mount is: sized to his, and sat
			# on the middle of his skull)
			_helmet.transform = Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * HEAD), Vector3(0.0, 0.1, 0.005))
			var cable := parts.find_child("Cable") as Node3D
			cable.get_parent().remove_child(cable)
			for named: String in ["CableA", "CableB"]:
				_sockets.append(_helmet.find_child(named))
				var one: Node3D = cable.duplicate()
				boat.add_child(one)
				_cables.append(one)
			cable.free()
	parts.free()


# Where a node of a model is, in the space of something it is under.
func _place_in(node: Node3D, under: Node3D) -> Vector3:
	var at := Transform3D.IDENTITY
	var each: Node = node
	while each != under and each is Node3D:
		at = (each as Node3D).transform * at
		each = each.get_parent()
	return at.origin


func _process(delta: float) -> void:
	_clock += delta
	# The boat on the swell.
	boat.rotation.z = sin(_clock * 0.8) * 0.03
	boat.rotation.x = sin(_clock * 0.6 + 1.0) * 0.018
	boat.position.y = sin(_clock * 0.7) * 0.06
	# The cables, from the helmet's sockets to the top of the computer, hanging slack.
	for k in _cables.size():
		var from := boat.to_local(_sockets[k].global_position)
		var to: Vector3 = _spots["HelmetCable"] + Vector3((k - 0.5) * 0.5, -0.35, 0.2)
		var along := to - from
		var long := along.length()
		var side := along.cross(Vector3.UP).normalized() * long
		_cables[k].transform = Transform3D(Basis(along, Vector3.UP * long * 0.8, side * 0.7), from)


## Where the eye stands (in the world): astern and above, looking into the open cabin; further
## back in an upright window, where the picture is narrow.
func eye(upright: bool) -> Transform3D:
	var back := 9.5 if upright else 7.9
	var from := global_position + Vector3(0.0, 2.7 if not upright else 3.2, _spots["ConsoleSpot"].z + back)
	var at: Vector3 = global_position + _spots["ConsoleSpot"] + Vector3(0.0, 0.9, 0.6)
	return Transform3D(Basis.IDENTITY, from).looking_at(at, Vector3.UP)


## The card over the title: the game's name, and the button that starts it (or Enter, Space, a
## gamepad's A).
class Card:
	extends Control
	signal go

	func _ready() -> void:
		set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _process(_delta: float) -> void:
		queue_redraw()

	func _unit() -> float:
		return minf(size.x, size.y) / 720.0

	func _button() -> Vector2:
		return Vector2(size.x * 0.5, size.y - 120.0 * _unit())

	func _input(event: InputEvent) -> void:
		if not visible:
			return
		var touch := event as InputEventScreenTouch
		if touch and touch.pressed and touch.position.distance_to(_button()) < 95.0 * _unit():
			go.emit()
		elif event.is_action_pressed(&"ui_accept"):
			go.emit()

	func _draw() -> void:
		var u := _unit()
		var font := get_theme_default_font()
		var high := int(130.0 * u)
		var wide := font.get_string_size("GULP", HORIZONTAL_ALIGNMENT_LEFT, -1.0, high).x
		var at := Vector2((size.x - wide) * 0.5, 60.0 * u + high)
		draw_string_outline(font, at, "GULP", HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, int(14.0 * u), Color(0.05, 0.1, 0.16, 0.9))
		draw_string(font, at, "GULP", HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, Color(1.0, 0.86, 0.5))
		# the start button: a brass disc with an arrow, breathing
		var middle := _button()
		var r := (64.0 + 4.0 * sin(Time.get_ticks_msec() * 0.004)) * u
		draw_circle(middle, r + 8.0 * u, Color(0.1, 0.07, 0.03, 0.85))
		draw_circle(middle, r, Color(0.8, 0.55, 0.18))
		draw_circle(middle, r - 9.0 * u, Color(0.95, 0.5, 0.1))
		draw_colored_polygon(PackedVector2Array([middle + Vector2(-0.3, -0.42) * r, middle + Vector2(0.5, 0.0) * r, middle + Vector2(-0.3, 0.42) * r]), Color(0.2, 0.1, 0.03))
