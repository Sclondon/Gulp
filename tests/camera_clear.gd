extends SceneTree
## Does the camera keep out of the rocks and the floor? (tools/QUALITY.md, "The camera".) The sea's
## rocks are built (Scenery: the liner, the pirate ship, Atlantis, the kelp's rocks, the cliffs,
## the docks' piles); then at each place a fish is put at many points round the rocks, heading
## every way, at three sizes (a sardine, a tuna, an orca), and Main's `_camera_place` is asked where
## the eye goes. Counted: the eye inside a rock or under the floor, and the sight line from the fish
## to the eye crossing either. "old" is the place without `_camera_clear`.
##   godot --headless --path . --audio-driver Dummy -s res://tests/camera_clear.gd

const PLACES := {
	"liner": Vector3(-40.0, 0.0, 129.6), "pirate": Vector3(-80.0, 0.0, -12.8), "ruins": Vector3(-75.2, 0.0, 73.6),
	"kelp": Vector3(53.0, 0.0, 42.0), "docks": Vector3(35.2, 0.0, 78.4),
}
const SIZES := [0.25, 1.7, 7.5]
const TRIES := 300

var _scenery: Node


func _initialize() -> void:
	_scenery = Scenery.new()
	root.add_child(_scenery)
	_run.call_deferred()


func _blocked(p: Vector3) -> bool:
	return p.y < Sea.ground(p.x, p.z) + 0.05 or Sea.clear_of_rocks(p, 0.05).distance_squared_to(p) > 0.0001


func _line_blocked(a: Vector3, b: Vector3) -> bool:
	for k in range(1, 20):
		if _blocked(a.lerp(b, k / 20.0)):
			return true
	return false


func _run() -> void:
	await process_frame
	var main: Node = load("res://scripts/main.gd").new()
	var player: Player = Player.new()
	root.add_child(player)
	player.begin(Vector3(0.0, 30.0, 0.0), "sardine")
	main.player = player
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	print("CAM place | size | eye in rock or floor: old, new | sight line blocked: old, new | eye nearer than its body")
	for place: String in PLACES:
		var at: Vector3 = PLACES[place]
		# (the rocks near the place)
		var near: Array[Vector4] = []
		for rock: Vector4 in Sea.rocks:
			if Vector2(rock.x - at.x, rock.z - at.z).length() < 30.0:
				near.append(rock)
		if near.is_empty():
			print("CAM %s | no rocks" % place)
			continue
		for size: float in SIZES:
			var counts := [0, 0, 0, 0, 0]
			var n := 0
			for i in TRIES:
				var rock: Vector4 = near[rng.randi() % near.size()]
				var dir := Vector3(rng.randf_range(-1, 1), rng.randf_range(-0.6, 1), rng.randf_range(-1, 1)).normalized()
				var p := Vector3(rock.x, rock.y, rock.z) + dir * (rock.w + maxf(size * 0.3, 0.12) + rng.randf_range(0.0, 1.0))
				p = Sea.clear_of_rocks(Sea.keep_in(p, maxf(size * 0.3, 0.12)), maxf(size * 0.3, 0.12))
				if _blocked(p):
					continue
				n += 1
				player.length = size
				player.global_position = p
				player.heading = Vector3(rng.randf_range(-1, 1), rng.randf_range(-0.5, 0.5), rng.randf_range(-1, 1)).normalized()
				var long := size
				var old := p - player.heading * (0.25 + long * 1.9) + Vector3.UP * (0.2 + long * 1.1)
				old = Sea.keep_in(old, 0.3)
				old.y = minf(old.y, Sea.SURFACE - 0.5)
				var new: Vector3 = main._camera_place()
				counts[0] += int(_blocked(old))
				counts[1] += int(_blocked(new))
				counts[2] += int(_line_blocked(p, old))
				counts[3] += int(_line_blocked(p, new))
				counts[4] += int(new.distance_to(p) < size * 0.55)
			print("CAM %s | %.2f m | %d%%, %d%% | %d%%, %d%% | %d%%  (%d points)" % [place, size, 100 * counts[0] / maxi(n, 1),
				100 * counts[1] / maxi(n, 1), 100 * counts[2] / maxi(n, 1), 100 * counts[3] / maxi(n, 1), 100 * counts[4] / maxi(n, 1), n])
	main.free()
	quit(0)
