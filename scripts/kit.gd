class_name Kit
extends RefCounted
## The sea floor kit as the game uses it: GameCommon's SeaFloorProps (rocks, cliffs, bommies, reef
## life) and the sea's own pieces built for the places (tools/BIOMES.md section 8: reef slabs,
## understory kelp, the kelp canopy, bull kelp, surfgrass, sea pens, sand dollars, the whale fall...,
## each by its own tools/build_<piece>.py, into models/kit/). The same calls as SeaFloorProps
## (`mesh_of`, `material_of`, `spheres_of`, `size_of`, `tints_of`, `names`), so Scenery and Biomes
## take either. The sea's own pieces wear the kit's own two shaders (rock and soft), so they add
## no shader program; the tall swaying ones (kelp) a "kelp" material of the soft shader that sways
## further.

const DIR := "res://models/kit/"
## (as SeaFloorProps has them: Scenery asks the kit)
const CLIFF_WIDE := SeaFloorProps.CLIFF_WIDE
const CLIFF_TALL := SeaFloorProps.CLIFF_TALL
## The sea's own pieces (each models/kit/<name>.glb with <name> and <name>_lo, and <name>.json).
const OWN: PackedStringArray = ["reef_slab_a", "reef_slab_b", "reef_slab_c", "understory_kelp", "understory_kelp_b", "kelp_canopy",
		"bull_kelp", "surfgrass", "pile_mussels", "pile_strawberry", "pile_plumose", "sea_pen", "sea_pen_deep", "sea_whip",
		"sand_dollars", "whale_fall", "kelp_raft", "fish_shed"]
## Which of them sway as kelp does (metres a free tip moves each way).
const KELP_SWAY := {"bull_kelp": 0.35, "kelp_canopy": 0.25, "understory_kelp": 0.12, "understory_kelp_b": 0.12, "surfgrass": 0.14, "kelp_raft": 0.2}

static var _info := {}
static var _meshes := {}
static var _materials := {}
static var _loaded := false


## Whether the sea's own piece is built (its files are there).
static func has(piece: String) -> bool:
	return _own().has(piece)


static func names(group := "") -> PackedStringArray:
	if group == "kit":
		return PackedStringArray(_own().keys())
	return SeaFloorProps.names(group)


static func mesh_of(piece: String, low := false) -> Mesh:
	if not _own().has(piece):
		return SeaFloorProps.mesh_of(piece, low)
	var key := piece + ("_lo" if low else "")
	if not _meshes.has(key):
		var made: Node = (load(DIR + piece + ".glb") as PackedScene).instantiate()
		for child in made.find_children("*", "MeshInstance3D", true, false):
			_meshes[String(child.name)] = (child as MeshInstance3D).mesh
		made.free()
	return _meshes.get(key)


static func material_of(piece: String) -> ShaderMaterial:
	if not _own().has(piece):
		return SeaFloorProps.material_of(piece)
	if KELP_SWAY.has(piece):
		var key := "sway_%s" % str(KELP_SWAY[piece])
		if not _materials.has(key):
			# (the soft shader, swaying further: the same program as every soft piece)
			var made := SeaFloorProps.material("soft").duplicate() as ShaderMaterial
			made.set_shader_parameter(&"sway", float(KELP_SWAY[piece]))
			made.set_shader_parameter(&"sway_speed", 0.8)
			_materials[key] = made
		return _materials[key]
	return SeaFloorProps.material(String(_own()[piece]["material"]))


static func spheres_of(piece: String) -> Array[Vector4]:
	if not _own().has(piece):
		return SeaFloorProps.spheres_of(piece)
	var out: Array[Vector4] = []
	for s: Array in _own()[piece]["spheres"]:
		out.append(Vector4(s[0], s[1], s[2], s[3]))
	return out


static func size_of(piece: String) -> Vector3:
	if not _own().has(piece):
		return SeaFloorProps.size_of(piece)
	var s: Array = _own()[piece]["size"]
	return Vector3(s[0], s[1], s[2])


static func tints_of(piece: String) -> PackedColorArray:
	if not _own().has(piece):
		return SeaFloorProps.tints_of(piece)
	var out := PackedColorArray()
	for t: Array in _own()[piece]["tints"]:
		out.append(Color(t[0], t[1], t[2]))
	return out


static func triangles_of(piece: String, low := false) -> int:
	if not _own().has(piece):
		return SeaFloorProps.triangles_of(piece, low)
	return int(_own()[piece]["tris_lo" if low else "tris"])


static func _own() -> Dictionary:
	if not _loaded:
		for piece in OWN:
			var path := DIR + piece + ".json"
			# (loaded as a resource, as SeaFloorProps does: a web build packs the imported JSON)
			if ResourceLoader.exists(path) and ResourceLoader.exists(DIR + piece + ".glb"):
				var data: Variant = (load(path) as JSON).data
				if data is Dictionary:
					_info[piece] = data
		_loaded = true
	return _info


## Whether a piece can be drawn: one of the sea's own that is built, or one of GameCommon's.
static func exists(piece: String) -> bool:
	return _own().has(piece) or (not OWN.has(piece) and SeaFloorProps.names().has(piece))
