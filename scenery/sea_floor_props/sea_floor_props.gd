class_name SeaFloorProps
extends RefCounted
## A kit of sea floor scenery, every piece a still model built in Blender: fractured rocks for a
## rocky reef or a kelp forest's floor, tall cliff pieces for the edge of a shelf, coral bommies,
## cold-water reef life (sea fans, hydrocoral, sponges, anemones, urchins, sea stars, a scallop,
## mussels, feather-duster worms) and tropical corals (brain, table, staghorn and pillar corals, a
## barrel sponge, a purple sea fan, a soft coral, sea rods, a giant clam).
##
## Nothing here is a node: ask for a piece's mesh and material by name and draw it however the
## game draws scenery (a MeshInstance3D, or a MultiMesh for many).
##
##     for piece in SeaFloorProps.names("rock"):
##         var many := MultiMesh.new()
##         many.transform_format = MultiMesh.TRANSFORM_3D
##         many.use_colors = true            # see below: needed, even when every colour is white
##         many.mesh = SeaFloorProps.mesh_of(piece)
##         ...
##         instance.material_override = SeaFloorProps.material_of(piece)
##
## Every piece stands with its base at y = 0 (reaching a little below, to bed into uneven sand)
## and +Y up. Rocks and bommies stand over their own middle. A cliff piece's back is the plane
## z = 0 and its face looks to +Z: see the README for how they go side by side.
##
## Colours are painted on the points of each mesh; the two shaders multiply them by the
## instance's colour, so a MultiMesh's instance colour tints a piece (`tints_of` gives colours
## that suit it: a sea star in purple, orange or brown). In GL Compatibility a MultiMesh must
## have `use_colors` on and every instance's colour set, or everything is drawn black.
##
## The soft things sway by the global shader uniform `water_clock` (a float the game keeps moving:
## Project Settings, Shader Globals).

const DIR := "res://scenery/sea_floor_props/"
const ROCK_SHADER := preload("res://scenery/sea_floor_props/sea_floor_rock.gdshader")
const SOFT_SHADER := preload("res://scenery/sea_floor_props/sea_floor_soft.gdshader")
## The groups a piece can be in (`names(group)`).
const GROUPS: PackedStringArray = ["rock", "cliff", "bommie", "cold", "tropical"]
## A cliff piece is made to be put every CLIFF_WIDE metres along the shelf's edge (it is a metre
## wider than that at each end, so that neighbours run into each other) and is CLIFF_TALL high.
const CLIFF_WIDE := 12.0
const CLIFF_TALL := 16.0

static var _info := {}
static var _meshes := {}
static var _materials := {}


## The pieces' names; with a group ("rock", "cliff", "bommie", "cold", "tropical"), only its own.
static func names(group := "") -> PackedStringArray:
	var out := PackedStringArray()
	for piece: String in _all():
		if group == "" or _info[piece]["group"] == group:
			out.append(piece)
	return out


## Which group a piece is in.
static func group_of(piece: String) -> String:
	return _all()[piece]["group"]


## A piece's mesh: the full one, or the low one (a fifth of the triangles or fewer) for far off.
static func mesh_of(piece: String, low := false) -> Mesh:
	if _meshes.is_empty():
		for file: String in ["sea_floor_props.glb", "sea_floor_props_lo.glb"]:
			var made: Node = (load(DIR + "models/" + file) as PackedScene).instantiate()
			for child in made.find_children("*", "MeshInstance3D", true, false):
				_meshes[String(child.name)] = (child as MeshInstance3D).mesh
			made.free()
	return _meshes.get(piece + ("_lo" if low else ""))


## The material a piece takes. There are three, shared by every piece that takes them, so
## changing one changes them all: "rock" (rocks, cliffs, bommies), "firm" (shells, hard corals,
## sea stars, urchins: the rock shader with a fine grain) and "soft" (what sways).
static func material_of(piece: String) -> ShaderMaterial:
	return material(_all()[piece]["material"])


## One of the three shared materials by its own name: "rock", "firm" or "soft".
static func material(kind: String) -> ShaderMaterial:
	if not _materials.has(kind):
		var made := ShaderMaterial.new()
		made.shader = SOFT_SHADER if kind == "soft" else ROCK_SHADER
		if kind == "firm":
			made.set_shader_parameter(&"grain", 0.16)
			made.set_shader_parameter(&"grain_size", 0.05)
			made.set_shader_parameter(&"gloss", 0.25)
		_materials[kind] = made
	return _materials[kind]


## Spheres (x, y, z, radius, in the piece's own space) that roughly fill a rock, a cliff piece or
## a bommie, for keeping swimmers out of it without physics. Each is inside the piece's skin but
## for a little, so a hole through a piece (the arch's) stays open. Nothing for living things.
static func spheres_of(piece: String) -> Array[Vector4]:
	var out: Array[Vector4] = []
	for s: Array in _all()[piece]["spheres"]:
		out.append(Vector4(s[0], s[1], s[2], s[3]))
	return out


## How wide (x), tall (y) and deep (z) a piece is, in metres at scale 1.
static func size_of(piece: String) -> Vector3:
	var s: Array = _all()[piece]["size"]
	return Vector3(s[0], s[1], s[2])


## Colours that suit a piece as an instance's colour: white alone for most; for the sea stars
## and the hard corals, which are painted pale to be tinted, several.
static func tints_of(piece: String) -> PackedColorArray:
	var out := PackedColorArray()
	for t: Array in _all()[piece]["tints"]:
		out.append(Color(t[0], t[1], t[2]))
	return out


## How many triangles a piece has.
static func triangles_of(piece: String, low := false) -> int:
	return int(_all()[piece]["tris_lo" if low else "tris"])


static func _all() -> Dictionary:
	if _info.is_empty():
		_info = (load(DIR + "models/sea_floor_props.json") as JSON).data
	return _info
