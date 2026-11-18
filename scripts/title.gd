class_name Title
extends Node3D
## The start of the game: a shrimp boat on the sea over the place the fish starts. The user
## (2026-11-18): "the main menu / start of the game should be the boy from warren, a sea captain,
## and and oldtimy diver on a shrimping boat (look up reference pics). In the open back cabin of
## the shrimping boat should be a old timey franketstein computer hooked up to a helmet on the
## boys head- the controls for the pc are the controls for the game"; then "The boat should be
## perpendicular in the start scene, and the pc against the portside wall", "And hooked up to a
## monitor".
##
## So: the boat (models/shrimp_boat.glb) lies broadside to the eye, rocking on the swell; against
## the port wall of its open cabin stands the computer, which is the game's own control panel
## (models/control_panel.glb, the same model the TouchPad shows, on a bench), with a monitor on
## the wall over it; the boy stands at it in a helmet (models/brain_helmet.glb) cabled to it; the
## captain and the diver stand on the deck. The eye stands off the starboard beam looking across
## the deck into the cabin. When the game is started, Main sends the eye down through the surface
## to the fish: what the boy steers.
##
## It stands at the sea's surface (its origin is on the waterline). The boat's markers say where
## things go and which way they face (tools/SHRIMP_BOAT.md: a marker's -Z is its facing); the
## figures are TitleFigures (tools/TITLE_FIGURES.md). Any part that is not there yet (a model not
## built) is left out.

const BOAT := "res://models/shrimp_boat.glb"
const PANEL := "res://models/control_panel.glb"
const HELMET := "res://models/brain_helmet.glb"
const HELMET_PAINT := "res://textures/panel/helmet_atlas.png"
const FIGURES := "res://scripts/title_figures.gd"
## How big the computer is beside the model it shares with the TouchPad, and how high its bench is (m).
const COMPUTER := 0.25
const BENCH := 0.5
## The boy's head, as a radius over his hair (m): what the helmet is sized to.
const HEAD := 0.128
## Where things go on the boat if its model does not say (metres from its middle at the waterline;
## the bow is towards -Z, starboard +X), each facing starboard but the boy, who faces port.
const SPOTS := {
	"ConsoleSpot": Vector3(-1.37, 0.92, -0.2),
	"BoySpot": Vector3(-0.52, 0.92, -0.2),
	"CaptainSpot": Vector3(1.6, 0.95, -2.2),
	"DiverSpot": Vector3(1.0, 0.88, 3.2),
	"HelmetCable": Vector3(-1.37, 2.22, -0.2),
	"MonitorSpot": Vector3(-1.37, 2.67, -0.2),
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
	for named: String in SPOTS:
		# (facing starboard: a marker's -Z is the way it faces)
		var faces := Basis(Vector3.UP, -PI * 0.5 if named != "BoySpot" else PI * 0.5)
		_spots[named] = Transform3D(faces, SPOTS[named])
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
	# The computer: the control panel's housings on a bench against the wall, leaning back a
	# little, the two small boxes on top of the instruments; and its monitor on the wall over it.
	# (The models face +Z; a marker faces its -Z: so they are turned round on the spot.)
	var about := Basis(Vector3.UP, PI)
	var console: Transform3D = _spots["ConsoleSpot"]
	var parts: Node3D = (load(HELMET) as PackedScene).instantiate()
	PanelModel.paint(parts, true, HELMET_PAINT)
	var bench := _take(parts, "Bench")
	bench.transform = console * Transform3D(about, Vector3(0.0, 0.0, -0.36))
	boat.add_child(bench)
	var computer: Node3D = (load(PANEL) as PackedScene).instantiate()
	PanelModel.paint(computer, true)
	computer.transform = console * Transform3D((about * Basis(Vector3.RIGHT, -0.12)).scaled(Vector3.ONE * COMPUTER), Vector3(0.0, BENCH, -0.22))
	var aside := (PanelModel.GAUGE_WIDE + PanelModel.SIDE_WIDE) * 0.5 + 0.12
	(computer.find_child("Helm") as Node3D).position.x = -aside
	(computer.find_child("Engine") as Node3D).position.x = aside
	(computer.find_child("Switches") as Node3D).position = Vector3(-PanelModel.SMALL_WIDE * 0.5 - 0.05, PanelModel.GAUGE_TALL + 0.05, 0.0)
	(computer.find_child("Aux") as Node3D).position = Vector3(PanelModel.SMALL_WIDE * 0.5 + 0.05, PanelModel.GAUGE_TALL + 0.05, 0.0)
	boat.add_child(computer)
	var monitor := _take(parts, "Monitor")
	if monitor:
		monitor.transform = (_spots["MonitorSpot"] as Transform3D) * Transform3D(about, Vector3.ZERO)
		boat.add_child(monitor)
		# (its screen glows green)
		var screen := monitor.find_child("MonitorScreen") as MeshInstance3D
		if screen:
			var lit: ShaderMaterial = (screen.get_surface_override_material(0) as ShaderMaterial).duplicate()
			lit.set_shader_parameter(&"tint", Color(2.5, 3.0, 2.5))
			lit.set_shader_parameter(&"glow", Color(0.03, 0.22, 0.07))
			screen.set_surface_override_material(0, lit)
	# The three of them.
	if ResourceLoader.exists(FIGURES):
		var figures: GDScript = load(FIGURES)
		boy = figures.call(&"boy")
		boy.transform = _spots["BoySpot"]
		boat.add_child(boy)
		var captain: Node3D = figures.call(&"captain")
		captain.transform = (_spots["CaptainSpot"] as Transform3D) * Transform3D(Basis(Vector3.UP, -0.35), Vector3.ZERO)
		boat.add_child(captain)
		var diver: Node3D = figures.call(&"diver")
		diver.transform = (_spots["DiverSpot"] as Transform3D) * Transform3D(Basis(Vector3.UP, 0.3), Vector3.ZERO)
		boat.add_child(diver)
		# The helmet on the boy's head, and its two cables to the computer.
		var head: Node3D = figures.call(&"head_node", boy)
		if head:
			_helmet = _take(parts, "Helmet")
			head.add_child(_helmet)
			# (built round a head of radius 1 with its face to +Z, as the mount is: sized to his, and sat
			# on the middle of his skull)
			_helmet.transform = Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * HEAD), Vector3(0.0, 0.1, 0.005))
			var cable := _take(parts, "Cable")
			for named: String in ["CableA", "CableB"]:
				_sockets.append(_helmet.find_child(named))
				var one: Node3D = cable.duplicate()
				boat.add_child(one)
				_cables.append(one)
			cable.free()
	parts.free()


# Takes a part out of a model, to put it somewhere else.
func _take(model: Node3D, named: String) -> Node3D:
	var part := model.find_child(named) as Node3D
	if part:
		part.get_parent().remove_child(part)
	return part


# Where a node of a model is, and how it is turned, in the space of something it is under.
func _place_in(node: Node3D, under: Node3D) -> Transform3D:
	var at := Transform3D.IDENTITY
	var each: Node = node
	while each != under and each is Node3D:
		at = (each as Node3D).transform * at
		each = each.get_parent()
	return at.orthonormalized()


func _process(delta: float) -> void:
	_clock += delta
	# The boat on the swell (seen broadside: it rolls towards and away, and pitches a little).
	boat.rotation.z = sin(_clock * 0.8) * 0.03
	boat.rotation.x = sin(_clock * 0.6 + 1.0) * 0.018
	boat.position.y = sin(_clock * 0.7) * 0.06
	# The cables, from the helmet's sockets to the top of the computer, hanging slack.
	var top: Transform3D = _spots["HelmetCable"]
	for k in _cables.size():
		var from := boat.to_local(_sockets[k].global_position)
		var to := top * Vector3((k - 0.5) * 0.5, -0.2, -0.25)
		var along := to - from
		var long := along.length()
		var side := along.cross(Vector3.UP).normalized() * long
		_cables[k].transform = Transform3D(Basis(along, Vector3.UP * long * 0.8, side * 0.7), from)


## Where the eye stands (in the world): off the starboard beam and a little above, looking across
## the deck into the open cabin; further off in an upright window, where the picture is narrow.
func eye(upright: bool) -> Transform3D:
	var console: Vector3 = (_spots["ConsoleSpot"] as Transform3D).origin
	var from := global_position + Vector3(19.0 if upright else 10.5, 4.6 if upright else 3.0, console.z + (0.0 if upright else 0.6))
	var at := global_position + Vector3(0.0, 2.6 if upright else 1.9, console.z + (0.0 if upright else 0.3))
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
		return Vector2(size.x * 0.5, size.y - 110.0 * _unit())

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
		var high := int(120.0 * u)
		var wide := font.get_string_size("GULP", HORIZONTAL_ALIGNMENT_LEFT, -1.0, high).x
		var at := Vector2((size.x - wide) * 0.5, 40.0 * u + high)
		draw_string_outline(font, at, "GULP", HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, int(14.0 * u), Color(0.05, 0.1, 0.16, 0.9))
		draw_string(font, at, "GULP", HORIZONTAL_ALIGNMENT_LEFT, -1.0, high, Color(0.93, 0.85, 0.62))
		# the start button: a brass disc with an arrow, breathing
		var middle := _button()
		var r := (64.0 + 4.0 * sin(Time.get_ticks_msec() * 0.004)) * u
		draw_circle(middle, r + 8.0 * u, Color(0.1, 0.07, 0.03, 0.85))
		draw_circle(middle, r, Color(0.5, 0.38, 0.18))
		draw_circle(middle, r - 9.0 * u, Color(0.8, 0.45, 0.12))
		draw_colored_polygon(PackedVector2Array([middle + Vector2(-0.3, -0.42) * r, middle + Vector2(0.5, 0.0) * r, middle + Vector2(-0.3, 0.42) * r]), Color(0.2, 0.1, 0.03))
