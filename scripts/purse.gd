class_name Purse
extends RefCounted
## What is kept between runs (DESIGN.md, "What is saved"): the money, the gear bought, the kinds
## sold (for the evolution tree, later), the treasure pieces found (none can be yet), and the
## longest fish. In `user://gulp.cfg`, which also held only the longest length before (its
## [best] length is read and written as it was).
##
## `path` empty keeps it in memory only: Main does that whenever a test, the bot or a picture is
## driving, so that they never touch the player's own save.
##
## Selling: a kind's `WORTH` a metre times its length, doubled for the last of a growth line at
## its full length; the first sale of a kind also pays `WORTH` x `FIRST_METRES` once.

## Money a metre for each kind the player can become (Player.GROWTH), more for the rarer and the
## later ones (Claude's numbers, 2026-11-18).
const WORTH := {
	"sardine": 8,
	"flying": 18, "mackerel": 16, "smolt": 18, "surfperch": 16,
	"bonito": 24, "barracuda": 24, "salmon": 28, "kelp_bass": 26, "rockfish": 26,
	"snapper": 36, "tuna": 40, "mahi": 40, "wahoo": 40, "leopard_shark": 36, "grouper": 36,
	"sea_bass": 50, "bluefin": 60, "sailfish": 60, "blue_shark": 55,
	"swordfish": 80, "marlin": 85, "white_shark": 90,
	"orca": 120,
	"shark": 50,
}
## The first sale of a kind pays this many metres' worth over the price, once.
const FIRST_METRES := 1.0
## The amplifier: how deep the machine's signal reaches at each step (m), and what each step costs
## (the first is had from the start).
const AMP_DEPTH := [15.0, 30.0, 50.0, 100.0]
const AMP_PRICE := [0, 30, 150, 600]

var path := ""
var money := 0
## The amplifier's step (an index into AMP_DEPTH).
var amp := 0
## Every kind sold at least once.
var sold: Array = []
## Treasure pieces found (names; none yet).
var treasure: Array = []
## The longest the player has ever been (m).
var best := 0.0


func _init(at := "") -> void:
	path = at
	if path != "":
		var kept := ConfigFile.new()
		if kept.load(path) == OK:
			best = float(kept.get_value("best", "length", 0.0))
			money = int(kept.get_value("purse", "money", 0))
			amp = clampi(int(kept.get_value("gear", "amplifier", 0)), 0, AMP_DEPTH.size() - 1)
			sold = kept.get_value("purse", "sold", [])
			treasure = kept.get_value("purse", "treasure", [])


func save() -> void:
	if path == "":
		return
	var kept := ConfigFile.new()
	kept.set_value("best", "length", best)
	kept.set_value("purse", "money", money)
	kept.set_value("purse", "sold", sold)
	kept.set_value("purse", "treasure", treasure)
	kept.set_value("gear", "amplifier", amp)
	kept.save(path)


## Back to nothing (and saved so).
func reset() -> void:
	money = 0
	amp = 0
	sold = []
	treasure = []
	best = 0.0
	save()


## How deep the fish may go (m below the surface).
func depth() -> float:
	return AMP_DEPTH[amp]


## What the next amplifier step costs (-1: there is none).
func next_amp_price() -> int:
	return AMP_PRICE[amp + 1] if amp + 1 < AMP_PRICE.size() else -1


## Buys the next amplifier step, if there is one and it can be paid for.
func buy_amp() -> bool:
	var price := next_amp_price()
	if price < 0 or money < price:
		return false
	money -= price
	amp += 1
	save()
	return true


## What a fish would fetch: {kind, length, worth (a metre), base, doubled, bonus, total}.
func price_of(kind: String, length: float, biggest: bool) -> Dictionary:
	var worth: int = WORTH.get(kind, 8)
	var base := roundi(worth * length)
	var bonus := 0 if kind in sold else roundi(worth * FIRST_METRES)
	var total := base * (2 if biggest else 1) + bonus
	return {"kind": kind, "length": length, "worth": worth, "base": base, "doubled": biggest, "bonus": bonus, "total": total}


## Sells a fish: pays, notes the kind, saves. Gives back what price_of gives, with the purse's new
## `money`.
func sell(kind: String, length: float, biggest: bool) -> Dictionary:
	var receipt := price_of(kind, length, biggest)
	money += int(receipt.total)
	if not kind in sold:
		sold.append(kind)
	best = maxf(best, length)
	save()
	receipt["money"] = money
	return receipt
