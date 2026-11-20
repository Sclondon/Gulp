@tool
extends Node
## Numbers and lists of the layout edited in the Inspector, in the bay editor: how many of each kind of
## animal there are ("Animals"), which zones each school keeps to ("Schools"), the floor's bake numbers
## ("Floor numbers") and the biomes' ("Biome numbers"). Saved into data/layout.json at `key`.

## Where in the layout it is saved ("kinds_count", "schools", "bake", "biomes").
@export var key := ""
@export var values := {}
