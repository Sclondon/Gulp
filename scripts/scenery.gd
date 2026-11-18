class_name Scenery
extends Node3D
## What grows in each part of the sea (Sea.ZONES): the kelp forest and the sea grass bed, planted
## from GameCommon's plant components where they are installed (plants/kelp, plants/sea_grass).
## The same places every time (a seed of its own).
##
## Nothing here stops a swimmer: fish pass through kelp and grass.

const KELP := "res://plants/kelp/kelp_forest.gd"
const GRASS := "res://plants/sea_grass/sea_grass_bed.gd"
## How many kelp plants and tufts of grass.
const KELPS := 150
const TUFTS := 2600
## Beyond this the water hides them (m).
const SEEN := 60.0

## Who lays the grass aside (the player).
var player: Node3D

var _grass: Node3D
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.seed = 11
	if ResourceLoader.exists(KELP):
		_plant_kelp()
	if ResourceLoader.exists(GRASS):
		_plant_grass()


func _process(_delta: float) -> void:
	if _grass and player:
		_grass.set(&"pushers", PackedVector3Array([player.global_position]))


# The kelp forest: plants standing in clumps with clear lanes between, each reaching for the
# surface (the tallest lie along it).
func _plant_kelp() -> void:
	var zone: Dictionary = Sea.ZONES.kelp
	var places := PackedVector3Array()
	var heights := PackedFloat32Array()
	var clumps: Array[Vector2] = []
	for i in 22:
		var turn := _rng.randf() * TAU
		clumps.append(zone.at + Vector2(cos(turn), sin(turn)) * float(zone.radius) * sqrt(_rng.randf()) * 0.95)
	for i in KELPS:
		var clump := clumps[i % clumps.size()]
		var turn := _rng.randf() * TAU
		var at := clump + Vector2(cos(turn), sin(turn)) * _rng.randf_range(0.3, 4.5)
		var low := Sea.ground(at.x, at.y)
		var deep := Sea.SURFACE - low
		if deep < 5.0:
			continue
		places.append(Vector3(at.x, low - 0.1, at.y))
		heights.append(minf(deep * _rng.randf_range(0.7, 1.25), 25.0))
	var forest: Node3D = (load(KELP) as GDScript).new()
	forest.set(&"far", SEEN)
	forest.set(&"current", Vector2(0.3, 0.1))
	add_child(forest)
	forest.call(&"plant", places, heights, Sea.SURFACE)


# The sea grass bed: thick in the middle, thinning to its edge, and up the river's mouth.
func _plant_grass() -> void:
	var zone: Dictionary = Sea.ZONES.grass
	var places := PackedVector3Array()
	var heights := PackedFloat32Array()
	for i in TUFTS:
		var turn := _rng.randf() * TAU
		# (more of them towards the middle)
		var at: Vector2 = zone.at + Vector2(cos(turn), sin(turn)) * float(zone.radius) * pow(_rng.randf(), 0.7)
		var low := Sea.ground(at.x, at.y)
		if Sea.SURFACE - low < 1.5:
			continue
		places.append(Vector3(at.x, low - 0.03, at.y))
		heights.append(_rng.randf_range(0.45, 1.2))
	_grass = (load(GRASS) as GDScript).new()
	_grass.set(&"far", SEEN)
	_grass.set(&"current", Vector2(0.3, 0.1))
	_grass.set(&"push_radius", 0.7)
	add_child(_grass)
	_grass.call(&"plant", places, heights)
