extends RefCounted
## How the figed figures' hair pieces are drawn: which shader settings each piece made by tools/figed/hair.py wears
## (shaders/hair_stylised.gdshader). One table, so every viewer (tests/figed_hair_view.gd, a pose test, the game
## later) shows the same hair: `preload("res://tests/figed_hair_looks.gd").wear(model)` puts the materials on every
## piece under a node.
## The older brother's looks (Claude's picks, matched by eye to tools/art_src/concept_brother_bible_head.jpg).
## tools/figed/README.md, "Hair as locks", says what each setting does.

const SHADER := preload("res://shaders/hair_stylised.gdshader")

## piece (the start of a mesh's name; the longest that fits wins) -> settings
const LOOKS := {
	"hair_locks": {"base": Color(0.31, 0.18, 0.14), "deep": Color(0.14, 0.07, 0.07),
			"light": Color(0.56, 0.36, 0.27), "lock_shape": 1.0, "taper": 0.22, "taper_round": 2.6, "hook": 0.6,
			"fork": 0.0, "ribbons": 2.0, "ribbon_wave": 0.3, "ribbon_waves": 1.0, "ribbon_tips": 0.3,
			"ribbon_taper": 0.2, "ribbon_vary": 0.12, "strand_depth": 0.1, "strand_run": 0.6, "shine": 0.6,
			"shine_length": 0.3, "shine_every": 0.07, "edge_width": 0.22, "edge_dark": 0.85, "under_edge": 0.55, "ridge": 0.55},
	"hair_cap": {"base": Color(0.25, 0.145, 0.11), "deep": Color(0.14, 0.07, 0.065),
			"light": Color(0.42, 0.26, 0.19), "lock_shape": 0.0, "edge_points": 0.2, "edge_point_count": 64.0, "shine": 0.0, "ridge": 0.5, "edge_dark": 0.7,
			"edge_width": 0.3, "under_edge": 0.4, "ribbons": 30.0, "ribbon_wave": 0.04, "ribbon_waves": 2.5,
			"ribbon_vary": 0.15, "strands": 2.0, "strand_depth": 0.08,
			"root_dark": 0.0, "depth_shade": 0.0, "vary": 0.0, "under_shade": 0.3},
	"moustache_locks": {"base": Color(0.60, 0.29, 0.15), "deep": Color(0.40, 0.16, 0.08),
			"light": Color(0.74, 0.42, 0.24), "lock_shape": 1.0, "taper": 0.3, "taper_round": 1.5, "hook": 0.5,
			"hook_way": 1.0, "fork": 0.0, "waver": 0.0, "root_narrow": 0.0, "ribbons": 4.0, "ribbon_wave": 0.12,
			"ribbon_waves": 0.8, "ribbon_tips": 0.12, "ribbon_taper": 0.2, "ribbon_vary": 0.1,
			"edge_dark": 0.45, "edge_width": 0.3, "under_edge": 0.3, "strands": 2.0, "strand_depth": 0.1,
			"ridge": 0.4, "shine": 0.3, "shine_at": 0.4, "shine_length": 0.35, "root_dark": 0.0,
			"under_shade": 0.45, "depth_shade": 0.3, "vary": 0.06},
	"stubble": {"base": Color(0.60, 0.36, 0.25), "deep": Color(0.5, 0.26, 0.16), "light": Color(0.66, 0.4, 0.27),
			"lock_shape": 0.0, "stubble": 1.2, "stubble_size": 0.0019, "stubble_width": 0.16, "ridge": 0.0, "edge_dark": 0.0, "under_edge": 0.0, "shine": 0.0,
			"strand_depth": 0.0, "root_dark": 0.0, "depth_shade": 0.0, "vary": 0.0, "under_shade": 0.0},
	"moustache": {"base": Color(0.48, 0.2, 0.1), "deep": Color(0.4, 0.15, 0.08), "ridge": 0.0, "edge_dark": 0.0,
			"under_edge": 0.0,
			"light": Color(0.78, 0.45, 0.22), "lock_shape": 0.0, "strands": 14.0, "strand_depth": 0.22,
			"strand_run": 3.0, "shine": 0.35, "shine_at": 0.45, "shine_length": 0.4, "root_dark": 0.0,
			"depth_shade": 0.0, "vary": 0.0, "under_shade": 0.45},
}


## The piece of LOOKS a mesh of this name wears ("" none).
static func piece_of(mesh_name: String) -> String:
	var key := mesh_name.to_lower()
	var best := ""
	for piece in LOOKS:
		if key.begins_with(piece) and piece.length() > best.length():
			best = piece
	return best


## A material for a piece; `sets` are number settings laid over the table ("<piece>.<setting>" -> number).
static func material(piece: String, sets: Dictionary = {}) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	for k in LOOKS[piece]:
		mat.set_shader_parameter(k, LOOKS[piece][k])
	for k in sets:
		if k.begins_with(piece + "."):
			mat.set_shader_parameter(k.substr(piece.length() + 1), sets[k])
	return mat


## Every hair piece under `node` given its material. Returns the meshes dressed.
static func wear(node: Node, sets: Dictionary = {}) -> Array:
	var done: Array = []
	if node is MeshInstance3D:
		var piece := piece_of(String(node.name))
		if piece != "":
			node.material_override = material(piece, sets)
			done.append(node)
	for c in node.get_children():
		done.append_array(wear(c, sets))
	return done
