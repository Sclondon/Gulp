@tool
extends Node3D
## A round area in the bay editor: a spawn zone (with the kinds of animal that live in it), a
## harbour, a level shelf under a set piece, Atlantis's clear basin, the river's mouth. Drawn as a
## ring (and a dashed outer ring where it has one) with its name. Move it with the gizmo; drag the
## round handles (or type in the Inspector) to change its size. Saved into data/layout.json by `role`
## (BayEditor._save_circles).

const BayLabel := preload("res://addons/bay_layout/bay_label.gd")

## What it is: "zone:<name>", "zone_also:<name>", "harbour", "shelf:<name>", "ruins_clear", "estuary",
## "reef_back".
@export var role := ""
## Its radius (m); and an outer radius it blends out to (0: none).
@export var radius := 10.0:
	set(v):
		radius = maxf(v, 0.0)
		refresh()
@export var outer := 0.0:
	set(v):
		outer = maxf(v, 0.0)
		refresh()
## How deep (m below the surface): a harbour's or a shelf's.
@export var depth := 0.0
## A spawn zone's animals: the kinds that live in it (Species names), and the schools that keep to it.
@export var kinds: PackedStringArray = []
@export var schools: PackedStringArray = []
## Anything else saved with it (a zone's "region" or "deeper"; a shelf's slope and long shape).
@export var extra := {}
@export var colour := Color(0.3, 0.9, 1.0):
	set(v):
		colour = v
		refresh()

var _ring: MeshInstance3D
var _label: Label3D


func _ready() -> void:
	refresh()


func refresh() -> void:
	if not is_inside_tree():
		return
	if _ring == null:
		_ring = MeshInstance3D.new()
		_ring.name = "Ring"
		_ring.mesh = ImmediateMesh.new()
		add_child(_ring)
		_label = BayLabel.make(self, 20)
	_ring.material_override = BayLabel.line_material(colour)
	var im := _ring.mesh as ImmediateMesh
	im.clear_surfaces()
	for ring: float in [radius, outer]:
		if ring <= 0.0:
			continue
		var dashed := ring == outer
		var n := clampi(int(ring * 1.5), 24, 160)
		im.surface_begin(Mesh.PRIMITIVE_LINES)
		for k in n:
			if dashed and k % 2 == 1:
				continue
			var a := TAU * k / n
			var b := TAU * (k + 1) / n
			im.surface_add_vertex(Vector3(cos(a) * ring, 0.0, sin(a) * ring))
			im.surface_add_vertex(Vector3(cos(b) * ring, 0.0, sin(b) * ring))
		im.surface_end()
	_label.text = name
	_label.modulate = colour
	_label.position = Vector3(0.0, 0.5, -radius)
