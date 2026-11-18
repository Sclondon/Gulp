extends SceneTree
## Counts the kelp forest the placer makes (tools/BIOMES.md, the kelp biome): plants, their lengths,
## the frond pieces, the kelp region's area and its rock, and the understory, without drawing.
##   godot --headless --path . --audio-driver Dummy -s tools/kelp_count.gd


func _initialize() -> void:
	var sea := Sea.new()
	get_root().add_child(sea)
	var scenery := Scenery.new()
	get_root().add_child(scenery)
	await process_frame
	var biomes: Biomes = scenery._biomes
	var places := biomes.kelp_places
	var lengths := biomes.kelp_lengths
	var metres := 0.0
	var in_kelp := 0
	for i in places.size():
		metres += lengths[i]
		if BiomeRegions.at(places[i].x, places[i].z) == BiomeRegions.KELP:
			in_kelp += 1
	var box := BiomeRegions.bounds(BiomeRegions.KELP)
	var area := 0
	var rock := 0
	var x := box.position.x
	while x < box.end.x:
		var z := box.position.y
		while z < box.end.y:
			if BiomeRegions.at(x, z) == BiomeRegions.KELP:
				area += 4
				if FloorTypes.of(x, z) == 1:
					rock += 4
			z += 2.0
		x += 2.0
	print("KELP COUNT plants %d (in the kelp biome %d), frond metres %d, mean length %.1f m" % [places.size(), in_kelp, int(metres), metres / maxf(places.size(), 1)])
	print("KELP COUNT region %d m2, rock %d m2, plants per 100 m2 of rock %.2f" % [area, rock, in_kelp * 100.0 / maxf(rock, 1.0)])
	var middle: Vector2 = Sea.ZONES.kelp.at
	print("KELP COUNT weight at the kelp zone's middle %.2f (%s)" % [BiomeRegions.weight(BiomeRegions.KELP, middle.x, middle.y), BiomeRegions.at(middle.x, middle.y)])
	for key: String in biomes.made:
		if key.begins_with("kelp ") or key.begins_with("carmel "):
			print("KELP COUNT layer ", key, " = ", biomes.made[key])
	var forest: Node = null
	for child in scenery.get_children():
		if child.get_script() and (child.get_script() as Script).resource_path == Scenery.KELP:
			forest = child
	if forest:
		print("KELP COUNT forest ", forest.call(&"counts"))
	quit()
