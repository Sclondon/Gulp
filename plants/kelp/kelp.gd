class_name Kelp
extends Node3D
## One giant kelp plant, where this node is: its holdfast at the node's place, `height` metres
## of fronds, under a surface at world height `surface_y`. It is a KelpForest of one (`forest`):
## for many plants, give one KelpForest all their places instead, which draws them together.
##
##   var kelp := Kelp.new()
##   kelp.height = 14.0
##   kelp.surface_y = 0.0
##   kelp.position = Vector3(3.0, -12.0, 1.0)
##   add_child(kelp)
##
## Leave it unturned and unscaled. After moving it up or down, or changing its height or the
## surface, call `grow()`.

## How long its fronds are, metres (4 to 25 is what it is made for).
@export var height := 12.0
## The world height of the water's surface.
@export var surface_y := 0.0
## As KelpForest's.
@export_range(0.0, 3.0) var sway := 1.0:
	set(value):
		sway = value
		forest.sway = value
@export var current := Vector2.ZERO:
	set(value):
		current = value
		forest.current = value

var forest := KelpForest.new()


func _ready() -> void:
	add_child(forest)
	grow()


func grow() -> void:
	forest.plant(PackedVector3Array([Vector3.ZERO]), PackedFloat32Array([height]), surface_y)
