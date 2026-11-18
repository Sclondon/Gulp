class_name LodField
extends Node3D
## Many still pieces of scenery (GameCommon's sea floor kit: rocks, corals, fans, sponges...),
## drawn two MultiMeshes a piece: its full model near the eye, its light model (a fifth of the
## triangles or fewer) further off, and none beyond `far`. Which instance goes in which is
## settled by cubes of CELL metres, again only when the eye has moved, and then only for the
## pieces that have something in a cube that changed (tools/PERF.md, "Decision: scenery near and
## far"). Up close nothing changes: within `near` of the eye every piece is its full model.
##
##     var field := LodField.new()
##     field.add("brain_coral", full_mesh, light_mesh, material, transforms, colours, 1.2)
##     add_child(field)           (after every add; the transforms are in the field's space)

## The size of the cubes the field is sorted into (m).
const CELL := 4.0
## How far the eye must move before the cubes are looked at again (m).
const MOVE := 0.5

## Full models within this of the eye (m, to the nearest edge of a cube); light ones beyond.
var near := 10.0
## Nothing beyond this (m, to the nearest edge of a cube; INF: never).
var far := INF
## What the distances are measured from (the viewport's camera if null).
var eye: Node3D

# Each piece: {full: MultiMeshInstance3D, light: ..., cells: PackedInt32Array (the cubes it has
# instances in), rows: Array[PackedFloat32Array] (its instances in each, 16 floats each: the
# transform by rows and the colour), reach: PackedFloat32Array (how far its instances in each reach
# out of it), tiers: PackedByteArray (each cube's, as last drawn: 2 full, 1 light, 0 none)}.
var _pieces: Array[Dictionary] = []
var _cell_of := {}
var _mids := PackedVector3Array()
var _seen_from := Vector3.INF


## Adds a piece: where each instance stands (in the field's own space), its colour, and how far
## its farthest point reaches from its origin at scale 1 (m).
func add(label: String, full: Mesh, light: Mesh, material: Material, wheres: Array, colours: Array, reach := 1.0) -> void:
	var by_cell := {}
	var reach_of := {}
	for i in wheres.size():
		var t: Transform3D = wheres[i]
		var b := t.basis
		var c: Color = colours[i] if i < colours.size() else Color.WHITE
		var key := Vector3i((t.origin / CELL).floor())
		if not _cell_of.has(key):
			_cell_of[key] = _mids.size()
			_mids.append((Vector3(key) + Vector3.ONE * 0.5) * CELL)
		var at: int = _cell_of[key]
		var rows: PackedFloat32Array = by_cell.get(at, PackedFloat32Array())
		rows.append_array(PackedFloat32Array([b.x.x, b.y.x, b.z.x, t.origin.x, b.x.y, b.y.y, b.z.y, t.origin.y, b.x.z, b.y.z, b.z.z, t.origin.z, c.r, c.g, c.b, c.a]))
		by_cell[at] = rows
		reach_of[at] = maxf(float(reach_of.get(at, 0.0)), reach * b.get_scale().abs().x)
	var cells := PackedInt32Array()
	var reaches := PackedFloat32Array()
	var tiers := PackedByteArray()
	var all_rows: Array[PackedFloat32Array] = []
	for at: int in by_cell:
		cells.append(at)
		reaches.append(reach_of[at])
		tiers.append(255)
		all_rows.append(by_cell[at])
	_pieces.append({"full": _drawer(label, full, material), "light": _drawer(label + "_far", light if light else full, material),
			"cells": cells, "rows": all_rows, "reach": reaches, "tiers": tiers})


## How many pieces it has, and how many instances of them in all.
func placed() -> Vector2i:
	var n := 0
	for piece in _pieces:
		for rows: PackedFloat32Array in piece.rows:
			@warning_ignore("integer_division")
			n += rows.size() / 16
	return Vector2i(_pieces.size(), n)


func _drawer(label: String, mesh: Mesh, material: Material) -> MultiMeshInstance3D:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	many.use_colors = true
	many.mesh = mesh
	var drawn := MultiMeshInstance3D.new()
	drawn.name = label
	drawn.multimesh = many
	drawn.material_override = material
	drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(drawn)
	return drawn


func _process(_delta: float) -> void:
	var from := eye if eye else get_viewport().get_camera_3d()
	if from == null:
		return
	var at := global_transform.affine_inverse() * from.global_position
	if at.distance_squared_to(_seen_from) < MOVE * MOVE:
		return
	_seen_from = at
	# (each cube's distance to its nearest edge: its middle less half its diagonal; a piece's
	# instances in it are near when that, less how far they reach, is within `near`, and none are
	# drawn when it is beyond `far`)
	var half := CELL * 0.8660254
	var dists := PackedFloat32Array()
	dists.resize(_mids.size())
	for i in _mids.size():
		dists[i] = _mids[i].distance_to(at) - half
	for piece in _pieces:
		var cells: PackedInt32Array = piece.cells
		var reach: PackedFloat32Array = piece.reach
		var tiers: PackedByteArray = piece.tiers
		var hit := false
		for k in cells.size():
			var d := dists[cells[k]] - reach[k]
			var tier := 2 if d < near else (1 if d < far else 0)
			if tier != tiers[k]:
				tiers[k] = tier
				hit = true
		if hit:
			piece.tiers = tiers
			_fill(piece)


# Writes a piece's two MultiMeshes from its cubes' tiers.
func _fill(piece: Dictionary) -> void:
	var cells: PackedInt32Array = piece.cells
	var rows: Array[PackedFloat32Array] = piece.rows
	var tiers: PackedByteArray = piece.tiers
	var near_rows := PackedFloat32Array()
	var far_rows := PackedFloat32Array()
	for k in cells.size():
		var tier := tiers[k]
		if tier == 2:
			near_rows.append_array(rows[k])
		elif tier == 1:
			far_rows.append_array(rows[k])
	_put(piece.full, near_rows)
	_put(piece.light, far_rows)


static func _put(drawn: MultiMeshInstance3D, rows: PackedFloat32Array) -> void:
	var many := drawn.multimesh
	@warning_ignore("integer_division")
	var n := rows.size() / 16
	if many.instance_count != n:
		many.instance_count = n
	if n > 0:
		many.buffer = rows
	drawn.visible = n > 0
