class_name FoodMarks
extends Node3D
## What the player can eat, and what can eat it, marked in the sea (the user, 2026-11-20, picking
## concept A, tools/art_src/concept_food_a_gold2.jpg; before that, "maybe they need to have a subtle
## outline and sparkle", and "its extremely unclear what you can eat and how to find it"):
##
## - an animal the player can eat now, near it and no deeper than it can go, wears a thin gold rim of
##   light and has a few small gold sparkles round it; a school or cloud of food (krill, anchovies,
##   tetras) and a jelly small enough to eat have the sparkles (they are not drawn by the motion
##   family shaders, so they have no rim);
## - an animal that can eat the player wears a faint red rim.
##
## Both follow the player's size: what was food turns plain and then red as it is outgrown the other
## way round, and the marks are worked out again every frame. The rim is a setting of the motion family
## shaders (`mark_rim`, shaders/motion/motion_paint.gdshaderinc), set on each animal's own material
## (Creature.mark): no program of its own. The sparkles are one MultiMesh of cards (shaders/sparkle.gdshader),
## one draw for all of them. CLAUDE.md, "Decision: food marks and the sonar ping".

const GOLD := Color(1.0, 0.76, 0.28)
const RED := Color(1.0, 0.16, 0.08)
## How far off food is marked (m; it fades out over the last FADE) and how strong its rim is.
const FOOD_NEAR := 14.0
const FOOD_RIM := 2.2
## How far off a hunter is marked, and how strong its rim (fainter than food's, as in the concept).
const HUNTER_NEAR := 24.0
const HUNTER_RIM := 1.4
const FADE := 4.0
## Sparkles: how many in all, how many round each thing, and how far off food has them (m).
const SPARKLES := 48
const PER_FOOD := 3
const SPARKLE_NEAR := 11.0
## How big a sparkle is drawn, as a share of its distance from the eye (so each is the same few pixels
## of the half-size picture, near or far).
const SPARKLE_SEEN := 0.05

var life: Life
var player: Player
var eye: Node3D
## How deep the player can go just now (m under the surface: where the signal's static begins). Food
## deeper than that is not marked (it would only lead the player into the static).
var deepest := INF
## Off: nothing is marked (the run is over, the sea stands still).
var on := true

var _marked: Array[Creature] = []
var _many: MultiMesh
var _cards: MultiMeshInstance3D
var _clock := 0.0


func _ready() -> void:
	_many = MultiMesh.new()
	_many.transform_format = MultiMesh.TRANSFORM_3D
	_many.use_colors = true
	_many.use_custom_data = true
	var card := QuadMesh.new()
	card.size = Vector2.ONE
	_many.mesh = card
	_many.instance_count = SPARKLES
	for i in SPARKLES:
		_many.set_instance_transform(i, Transform3D.IDENTITY)
	_many.visible_instance_count = 0
	_cards = MultiMeshInstance3D.new()
	_cards.name = "Sparkles"
	_cards.multimesh = _many
	_cards.top_level = true
	_cards.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var paint := ShaderMaterial.new()
	paint.shader = load("res://shaders/sparkle.gdshader")
	_cards.material_override = paint
	# (it moves about with the player: never culled by a box left where it was made)
	_cards.custom_aabb = AABB(Vector3(-1000.0, -1000.0, -1000.0), Vector3(2000.0, 2000.0, 2000.0))
	add_child(_cards)


## Whether something `prey` metres long, at a height `y`, is food the player can eat and reach now.
static func is_food_now(player_length: float, prey: float, y: float, deepest_now: float) -> bool:
	return Life.is_food(player_length, prey) and Sea.SURFACE - y < deepest_now


## Whether an animal hunts the player as it is now (big enough to eat it, and not so big that it
## takes no notice of it).
static func hunts_player(each: Creature, player_length: float) -> bool:
	return each.hunts and not each.giant and Life.can_eat(each.length, player_length) and player_length >= each.length * Life.TOO_SMALL


func _process(delta: float) -> void:
	_clock += delta
	if life == null or player == null:
		return
	var live := on and player.alive and visible
	var at := player.global_position
	# The rims: every awake animal near enough is looked at each frame (a few dozen comparisons);
	# a material is only told when its mark changes.
	var still: Array[Creature] = []
	if live:
		for each in life.awake:
			if not each.dressed or not each.visible or each.away > 0.0:
				continue
			var far := each.global_position.distance_to(at)
			if far > HUNTER_NEAR:
				continue
			var rim := Color(0.0, 0.0, 0.0, 0.0)
			if hunts_player(each, player.length):
				rim = Color(RED, HUNTER_RIM * _fade(far, HUNTER_NEAR))
			elif far < FOOD_NEAR and not each.giant and not each.guarded() and is_food_now(player.length, each.length, each.global_position.y, deepest):
				rim = Color(GOLD, FOOD_RIM * _fade(far, FOOD_NEAR))
			if rim.a > 0.0:
				each.mark(rim)
				still.append(each)
	for each in _marked:
		if is_instance_valid(each) and not still.has(each):
			each.mark(Color(0.0, 0.0, 0.0, 0.0))
	_marked = still
	_sparkle(live)


# How strong a mark is at a distance: whole, then fading out over the last FADE metres; in steps of a
# tenth, so a material is told only now and then as a thing swims nearer.
func _fade(far: float, near: float) -> float:
	return snappedf(clampf((near - far) / FADE, 0.0, 1.0), 0.1)


# The sparkles: round the nearest food (single animals, the nearest of a school or a cloud, a small
# jelly), PER_FOOD each.
func _sparkle(live: bool) -> void:
	if not live:
		_many.visible_instance_count = 0
		return
	var at := player.global_position
	var near: Array = []
	for each in _marked:
		if each.marked().r > 0.9 and each.marked().g > 0.5:
			var far := each.global_position.distance_to(at)
			if far < SPARKLE_NEAR:
				near.append([far, each.global_position, maxf(each.length, 0.05), each.get_instance_id()])
	for school: Dictionary in life.schools:
		var flock: Flock = school.flock
		if not flock.visible or not Life.is_food(player.length, float(school.length)):
			continue
		var i := flock.nearest(at)
		if i < 0:
			continue
		var spot := flock.boid_position(i)
		var far := spot.distance_to(at)
		if far < SPARKLE_NEAR and Sea.SURFACE - spot.y < deepest:
			# (round the nearest of them, spread over a little of the school)
			near.append([far, spot, maxf(float(school.radius) * 0.25, 0.3), flock.get_instance_id()])
	for jelly: MoonJelly in life.jellies:
		if jelly.visible and is_food_now(player.length, jelly.size * 2.0, jelly.global_position.y, deepest):
			var far := jelly.global_position.distance_to(at)
			if far < SPARKLE_NEAR:
				near.append([far, jelly.global_position, jelly.size * 2.0, jelly.get_instance_id()])
	near.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
	var eye_at := eye.global_position if eye else at
	_cards.global_position = at
	# (how many are drawn: each thing near has PER_FOOD)
	_many.visible_instance_count = mini(near.size(), SPARKLES / PER_FOOD) * PER_FOOD
	var n := 0
	for thing: Array in near:
		if n + PER_FOOD > SPARKLES:
			break
		var middle: Vector3 = thing[1]
		var wide: float = thing[2]
		var seed_of: int = thing[3]
		var strength := clampf((SPARKLE_NEAR - float(thing[0])) / 3.0, 0.0, 1.0)
		for k in PER_FOOD:
			# (each drifts slowly round the thing, over and beside it, on its own path)
			var a := float((seed_of * 7 + k * 131) % 1000) / 1000.0 * TAU + _clock * (0.5 + 0.17 * k)
			var lift := 0.35 + 0.3 * sin(_clock * 0.8 + k * 2.1 + seed_of % 17)
			var off := Vector3(cos(a), lift, sin(a)) * wide * 0.7
			var spot := middle + off
			# (about the same few pixels wherever it is: small, crisp stars, as in the concept)
			var big := spot.distance_to(eye_at) * SPARKLE_SEEN
			# (its place and size go in the custom data: shaders/sparkle.gdshader turns the card to the eye)
			var from := spot - _cards.global_position
			_many.set_instance_custom_data(n, Color(from.x, from.y, from.z, big))
			_many.set_instance_color(n, Color(GOLD, strength))
			n += 1
