@tool
extends RefCounted
## The bay editor's labels and lines (kept out of the saved scene: no owner).

const HIGH := 44.5


## A name over a node, readable from far off.
static func make(parent: Node3D, size := 28) -> Label3D:
	var label := Label3D.new()
	label.name = "Label"
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.fixed_size = true
	label.pixel_size = 0.0012
	label.font_size = size
	label.outline_size = 8
	label.no_depth_test = true
	label.render_priority = 4
	label.outline_render_priority = 3
	parent.add_child(label)
	return label


## An unshaded line material drawn over everything.
static func line_material(colour: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = colour
	mat.no_depth_test = true
	mat.render_priority = 2
	return mat


## A see-through fill material.
static func fill_material(colour: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(colour, 0.16)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.no_depth_test = true
	mat.render_priority = 1
	return mat
