@tool
extends Node3D
## A place in the bay editor: a set piece or a spot (the start, the liner, the pirate ship, Atlantis,
## the outcrops, the docks...), drawn as a light stand-in of about its size with its name over it.
## Move it with the editor's gizmo; turning it (rotation.y) turns those that have a heading. It is
## saved into data/layout.json by `key` (BayEditor._save_places).

const BayLabel := preload("res://addons/bay_layout/bay_label.gd")

## Where it is saved: "start", "liner", "pirate", "atlantis", "outcrop", "market:monterey",
## "dune_anchor" (one of the list, in order)...
@export var key := ""
## The stand-in: "box", "cylinder" or "sphere", its size (m; a box's x across, z along its heading),
## and colour.
@export var shape := "box"
@export var size := Vector3(4.0, 4.0, 4.0)
@export var colour := Color(0.9, 0.7, 0.3)
## Its height is its own (the liner's keel, the pirate ship, Atlantis); otherwise it sits on the floor
## and only x and z are saved.
@export var keeps_height := false
## Its turn is saved (rotation.y).
@export var turns := false
## Anything else saved with it (a dune anchor's "size").
@export var extra := {}

var _look: MeshInstance3D
var _label: Label3D


func _ready() -> void:
	refresh()


## Draws its stand-in and its name.
func refresh() -> void:
	if _look == null:
		# (a copy made with ctrl+D brings its drawing along: dropped, drawn afresh)
		for child in get_children():
			if child.owner == null and (child is MeshInstance3D or child is Label3D):
				child.free()
		_look = MeshInstance3D.new()
		_look.name = "StandIn"
		add_child(_look)
		_label = BayLabel.make(self)
	var m: PrimitiveMesh
	match shape:
		"cylinder":
			var c := CylinderMesh.new()
			c.top_radius = size.x * 0.35
			c.bottom_radius = size.x * 0.5
			c.height = size.y
			m = c
		"sphere":
			var s := SphereMesh.new()
			s.radius = size.x * 0.5
			s.height = size.y
			m = s
		_:
			var b := BoxMesh.new()
			b.size = size
			m = b
	var mat := StandardMaterial3D.new()
	mat.albedo_color = colour
	mat.roughness = 0.9
	m.material = mat
	_look.mesh = m
	_look.position = Vector3(0.0, size.y * 0.5, 0.0)
	_label.text = name
	_label.position = Vector3(0.0, size.y + 2.0, 0.0)

