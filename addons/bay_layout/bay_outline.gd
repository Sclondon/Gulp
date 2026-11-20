@tool
extends Path3D
## An outline in the bay editor: a biome's area, a piece of the trench, the river's course, a garden
## eel colony's band, a dune field's box. Its points are the Path3D's: select it and use the editor's
## path tools (add, move, delete points; undo works). Drawn as a coloured line (filled lightly where it
## is an area) with its name. Saved into data/layout.json by `role` (BayEditor._save_outlines).

const BayLabel := preload("res://addons/bay_layout/bay_label.gd")

## What it is: "biome:<name>", "trench", "river", "eels", "dune_field".
@export var role := ""
## An area (the last point joins the first) or a line.
@export var closed := true
@export var colour := Color(1.0, 1.0, 1.0):
	set(v):
		colour = v
		refresh()
## Anything else saved with it (an eel colony's "count").
@export var extra := {}

var _line: MeshInstance3D
var _fill: MeshInstance3D
var _label: Label3D


func _ready() -> void:
	if not curve_changed.is_connected(refresh):
		curve_changed.connect(refresh)
	refresh()


## The points, flat (world x, z).
func points() -> PackedVector2Array:
	var out := PackedVector2Array()
	if curve == null:
		return out
	for i in curve.point_count:
		var p := global_transform * curve.get_point_position(i)
		out.append(Vector2(p.x, p.z))
	return out


func refresh() -> void:
	if not is_inside_tree():
		return
	if _line == null:
		_line = MeshInstance3D.new()
		_line.name = "Line"
		add_child(_line)
		_fill = MeshInstance3D.new()
		_fill.name = "Fill"
		add_child(_fill)
		_label = BayLabel.make(self, 20)
	_line.material_override = BayLabel.line_material(colour)
	var flat: Array[Vector3] = []
	if curve != null:
		for i in curve.point_count:
			flat.append(curve.get_point_position(i))
	var lm := ArrayMesh.new()
	if flat.size() >= 2:
		var line := PackedVector3Array(flat)
		if closed:
			line.append(flat[0])
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = line
		lm.add_surface_from_arrays(Mesh.PRIMITIVE_LINE_STRIP, arrays)
	_line.mesh = lm
	var fm := ArrayMesh.new()
	if closed and flat.size() >= 3:
		var flat2 := PackedVector2Array()
		for p in flat:
			flat2.append(Vector2(p.x, p.z))
		var tris := Geometry2D.triangulate_polygon(flat2)
		if not tris.is_empty():
			var verts := PackedVector3Array()
			for t in tris:
				verts.append(flat[t])
			var arrays := []
			arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX] = verts
			fm.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	_fill.mesh = fm
	_fill.material_override = BayLabel.fill_material(colour)
	_label.text = name
	_label.modulate = colour
	var middle := Vector3.ZERO
	for p in flat:
		middle += p
	_label.position = middle / maxf(flat.size(), 1) + Vector3(0.0, 0.5, 0.0)
