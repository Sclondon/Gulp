class_name Species
## Every kind of animal in the sea, in one table: what draws it, how it is fitted to a length,
## where it lives, how many there are, and how it behaves. Fish reads it to dress a swimmer;
## Life reads it to stock the sea.
##
## A kind whose creature component is not installed (its script is not there) is simply left
## out of the sea: `has(kind)` says whether it can be made.
##
## Each entry:
## - script: its GameCommon creature (creatures/<name>/<name>.gd).
## - long, front: its length as built (0: the script's LENGTH) and how far its nose is ahead of
##   its own origin (left out: half its length, an origin at its middle).
## - set: properties to set on the creature when it is made.
## - turn: turned this far round (radians) in its holder (a crab walks sideways).
## - curls: its shader has `curl` (left out: it has).
## - how: "swim" (the default), "floor" (it keeps to the bottom, on it or just over it), or
##   "giant" (it cruises, takes no notice of anything, and nothing eats it).
## - hunts: it goes for the player when it is big enough to eat it (left out: it does).
## - breathes: it comes down from the surface and goes back up to it (seals, whales).
## - zones: where it lives (Sea.Zone names); band: the depth it keeps to there (0 the floor,
##   1 the surface); count; size: how long (from, to), metres.

const ALL := {
	# The player's own fish (also stocked in the sea).
	"sardine": {"script": "sardine/sardine", "zones": [], "count": 0, "size": [0.18, 0.24]},
	"smolt": {"script": "sockeye_salmon/sockeye_salmon", "set": {"stage": 2}, "zones": ["grass", "sand"], "band": [0.3, 0.9], "count": 5, "size": [0.5, 0.62]},
	"salmon": {"script": "sockeye_salmon/sockeye_salmon", "set": {"stage": 3}, "zones": ["kelp", "open"], "band": [0.3, 0.9], "count": 5, "size": [0.9, 1.2]},
	"tuna": {"script": "yellowfin_tuna/yellowfin_tuna", "set": {"first_dorsal": 0.25}, "zones": ["open"], "band": [0.5, 0.95], "count": 3, "size": [1.4, 1.9]},
	"shark": {"script": "", "zones": [], "count": 0, "size": [3.0, 5.0]},
	# The estuary's fish, in the sea grass.
	"loach": {"script": "clown_loach/clown_loach", "zones": ["grass"], "band": [0.0, 0.25], "count": 3, "size": [0.16, 0.24]},
	"trout": {"script": "cutthroat_trout/cutthroat_trout", "zones": ["grass"], "band": [0.2, 0.8], "count": 3, "size": [0.3, 0.45]},
	"golden": {"script": "cutthroat_trout/cutthroat_trout", "set": {"look": 1}, "zones": ["grass"], "band": [0.2, 0.8], "count": 2, "size": [0.32, 0.45]},
	"catfish": {"script": "channel_catfish/channel_catfish", "zones": ["grass"], "band": [0.0, 0.1], "count": 2, "size": [0.55, 0.8]},
	# The kelp forest and the reef.
	"garibaldi": {"script": "garibaldi/garibaldi", "zones": ["kelp", "reef"], "band": [0.05, 0.5], "count": 6, "size": [0.24, 0.34]},
	"surfperch": {"script": "surfperch/surfperch", "zones": ["kelp", "grass"], "band": [0.1, 0.7], "count": 7, "size": [0.2, 0.34]},
	"kelp_bass": {"script": "kelp_bass/kelp_bass", "zones": ["kelp"], "band": [0.1, 0.8], "count": 5, "size": [0.4, 0.6]},
	"rockfish": {"script": "rockfish/rockfish", "zones": ["reef", "kelp"], "band": [0.02, 0.25], "count": 5, "size": [0.38, 0.55]},
	"snapper": {"script": "snapper/snapper", "zones": ["reef"], "band": [0.1, 0.6], "count": 4, "size": [0.5, 0.8]},
	"grouper": {"script": "grouper/grouper", "zones": ["reef"], "band": [0.02, 0.3], "count": 2, "size": [1.0, 1.3]},
	"sea_bass": {"script": "giant_sea_bass/giant_sea_bass", "zones": ["kelp"], "band": [0.05, 0.4], "count": 2, "size": [1.8, 2.2]},
	"barracuda": {"script": "barracuda/barracuda", "zones": ["kelp", "reef"], "band": [0.6, 0.95], "count": 4, "size": [0.9, 1.2]},
	"eel": {"script": "moray_eel/moray_eel", "front": 0.0, "curls": false, "how": "floor", "zones": ["reef", "kelp"], "band": [0.02, 0.1], "count": 3, "size": [1.4, 1.9]},
	"octopus": {"script": "giant_pacific_octopus/giant_pacific_octopus", "long": 2.33, "front": 0.58, "curls": false, "how": "floor", "zones": ["reef"], "band": [0.03, 0.15], "count": 2, "size": [1.6, 2.2]},
	"cuttlefish": {"script": "cuttlefish/cuttlefish", "zones": ["reef", "grass"], "band": [0.05, 0.4], "count": 3, "size": [0.35, 0.45]},
	# The coral reef's small fish (several kinds of butterflyfish and angelfish).
	"threadfin": {"script": "butterflyfish/butterflyfish", "set": {"type": 0}, "zones": ["reef"], "band": [0.05, 0.5], "count": 3, "size": [0.15, 0.2]},
	"raccoon": {"script": "butterflyfish/butterflyfish", "set": {"type": 1}, "zones": ["reef"], "band": [0.05, 0.5], "count": 3, "size": [0.15, 0.2]},
	"copperband": {"script": "butterflyfish/butterflyfish", "set": {"type": 2}, "zones": ["reef"], "band": [0.05, 0.4], "count": 2, "size": [0.15, 0.2]},
	"longnose": {"script": "butterflyfish/butterflyfish", "set": {"type": 3}, "zones": ["reef"], "band": [0.05, 0.4], "count": 2, "size": [0.15, 0.2]},
	"bannerfish": {"script": "butterflyfish/butterflyfish", "set": {"type": 4}, "zones": ["reef"], "band": [0.2, 0.7], "count": 3, "size": [0.16, 0.22]},
	"emperor": {"script": "angelfish/angelfish", "set": {"type": 0}, "zones": ["reef"], "band": [0.05, 0.5], "count": 2, "size": [0.3, 0.4]},
	"queen": {"script": "angelfish/angelfish", "set": {"type": 1}, "zones": ["reef"], "band": [0.05, 0.5], "count": 2, "size": [0.3, 0.4]},
	"french": {"script": "angelfish/angelfish", "set": {"type": 2}, "zones": ["reef"], "band": [0.05, 0.5], "count": 2, "size": [0.3, 0.42]},
	"lionfish": {"script": "lionfish/lionfish", "zones": ["reef"], "band": [0.03, 0.3], "count": 3, "size": [0.3, 0.4]},
	"parrotfish": {"script": "parrotfish/parrotfish", "zones": ["reef"], "band": [0.05, 0.5], "count": 4, "size": [0.4, 0.55]},
	"cleaner": {"script": "wrasse/wrasse", "set": {"kind": 0}, "zones": ["reef"], "band": [0.05, 0.5], "count": 3, "size": [0.12, 0.16]},
	"wrasse": {"script": "wrasse/wrasse", "set": {"kind": 1}, "zones": ["reef"], "band": [0.05, 0.6], "count": 3, "size": [0.2, 0.28]},
	"yellow_tang": {"script": "surgeonfish/surgeonfish", "set": {"kind": 0}, "zones": ["reef"], "band": [0.05, 0.6], "count": 4, "size": [0.18, 0.24]},
	"surgeonfish": {"script": "surgeonfish/surgeonfish", "set": {"kind": 1}, "zones": ["reef"], "band": [0.05, 0.6], "count": 3, "size": [0.2, 0.28]},
	"convict": {"script": "surgeonfish/surgeonfish", "set": {"kind": 2}, "zones": ["reef"], "band": [0.05, 0.6], "count": 3, "size": [0.18, 0.24]},
	"blue_tang": {"script": "blue_tang/blue_tang", "zones": ["reef"], "band": [0.1, 0.7], "count": 4, "size": [0.2, 0.27]},
	"clownfish": {"script": "clownfish/clownfish", "zones": ["reef"], "band": [0.02, 0.15], "count": 5, "size": [0.09, 0.12]},
	# The sand flats.
	"halibut": {"script": "california_halibut/california_halibut", "how": "floor", "zones": ["sand"], "band": [0.01, 0.05], "count": 3, "size": [0.8, 1.1]},
	"stingray": {"script": "round_stingray/round_stingray", "how": "floor", "zones": ["sand", "grass"], "band": [0.01, 0.04], "count": 4, "size": [0.4, 0.5]},
	"bat_ray": {"script": "bat_ray/bat_ray", "zones": ["sand", "grass"], "band": [0.05, 0.35], "count": 3, "size": [1.0, 1.4]},
	"leopard_shark": {"script": "leopard_shark/leopard_shark", "zones": ["sand", "grass"], "band": [0.03, 0.3], "count": 3, "size": [1.3, 1.6]},
	# What walks on the bottom.
	"crab": {"script": "rock_crab/rock_crab", "long": 0.16, "turn": 1.5708, "curls": false, "how": "floor", "zones": ["reef", "kelp", "sand"], "band": [0.0, 0.0], "count": 8, "size": [0.12, 0.2]},
	"prawn": {"script": "spot_prawn/spot_prawn", "curls": false, "how": "floor", "zones": ["reef", "grass"], "band": [0.0, 0.0], "count": 8, "size": [0.15, 0.22]},
	"lobster": {"script": "spiny_lobster/spiny_lobster", "curls": false, "how": "floor", "zones": ["reef", "kelp"], "band": [0.0, 0.0], "count": 4, "size": [0.4, 0.6]},
	"nudibranch": {"script": "nudibranch/nudibranch", "curls": false, "how": "floor", "zones": ["reef", "kelp"], "band": [0.0, 0.0], "count": 6, "size": [0.1, 0.16]},
	# The open ocean, beyond the shelf's edge.
	"mackerel": {"script": "pacific_mackerel/pacific_mackerel", "zones": ["open", "kelp"], "band": [0.5, 0.95], "count": 4, "size": [0.36, 0.44]},
	"flying": {"script": "flying_fish/flying_fish", "zones": ["open"], "band": [0.85, 1.0], "count": 6, "size": [0.24, 0.32]},
	"bonito": {"script": "pacific_bonito/pacific_bonito", "zones": ["open", "kelp"], "band": [0.5, 0.95], "count": 4, "size": [0.6, 0.85]},
	"mahi": {"script": "mahi_mahi/mahi_mahi", "zones": ["open"], "band": [0.8, 0.98], "count": 3, "size": [1.0, 1.4]},
	"wahoo": {"script": "wahoo/wahoo", "zones": ["open"], "band": [0.6, 0.95], "count": 2, "size": [1.6, 2.0]},
	"bigeye": {"script": "bigeye_tuna/bigeye_tuna", "zones": ["open"], "band": [0.3, 0.7], "count": 2, "size": [1.6, 2.0]},
	"bluefin": {"script": "bluefin_tuna/bluefin_tuna", "zones": ["open"], "band": [0.4, 0.9], "count": 2, "size": [2.2, 2.8]},
	"humboldt": {"script": "humboldt_squid/humboldt_squid", "long": 2.2, "front": 1.3, "curls": false, "set": {"colour_beat": 7.0}, "zones": ["open"], "band": [0.1, 0.45], "count": 3, "size": [1.9, 2.4]},
	"sailfish": {"script": "sailfish/sailfish", "zones": ["open"], "band": [0.7, 0.97], "count": 2, "size": [2.5, 3.0]},
	"swordfish": {"script": "swordfish/swordfish", "zones": ["open"], "band": [0.3, 0.8], "count": 2, "size": [3.1, 3.8]},
	"marlin": {"script": "blue_marlin/blue_marlin", "zones": ["open"], "band": [0.6, 0.95], "count": 2, "size": [3.2, 3.8]},
	"blue_shark": {"script": "blue_shark/blue_shark", "zones": ["open"], "band": [0.4, 0.95], "count": 2, "size": [2.6, 3.2]},
	"white_shark": {"script": "white_shark/white_shark", "zones": ["open", "kelp"], "band": [0.3, 0.9], "count": 1, "size": [4.6, 5.0]},
	"giant": {"script": "giant_squid/giant_squid", "long": 5.1, "front": 2.2, "curls": false, "zones": ["trench"], "band": [ 0.05, 0.5], "count": 1, "size": [7.0, 7.0]},
	# The river mouth, among the mangroves: fresh-water fish.
	"arowana": {"script": "arowana/arowana", "zones": ["river"], "band": [0.8, 1.0], "count": 2, "size": [0.8, 1.0]},
	"piranha": {"script": "piranha/piranha", "zones": ["river"], "band": [0.2, 0.8], "count": 5, "size": [0.25, 0.32]},
	"pike": {"script": "northern_pike/northern_pike", "zones": ["river"], "band": [0.2, 0.7], "count": 2, "size": [0.9, 1.1]},
	"perch": {"script": "yellow_perch/yellow_perch", "zones": ["river", "grass"], "band": [0.2, 0.7], "count": 4, "size": [0.25, 0.32]},
	"walleye": {"script": "walleye/walleye", "zones": ["river"], "band": [0.05, 0.5], "count": 2, "size": [0.6, 0.75]},
	"gar": {"script": "gar/gar", "zones": ["river"], "band": [0.6, 0.95], "count": 2, "size": [1.1, 1.4]},
	"carp": {"script": "carp/carp", "set": {"type": 0}, "zones": ["river"], "band": [0.05, 0.4], "count": 2, "size": [0.6, 0.75]},
	"koi": {"script": "carp/carp", "set": {"type": 1}, "zones": ["river"], "band": [0.3, 0.9], "count": 2, "size": [0.55, 0.7]},
	"koi_sanke": {"script": "carp/carp", "set": {"type": 2}, "zones": ["river"], "band": [0.3, 0.9], "count": 1, "size": [0.55, 0.7]},
	"koi_showa": {"script": "carp/carp", "set": {"type": 3}, "zones": ["river"], "band": [0.3, 0.9], "count": 1, "size": [0.55, 0.7]},
	"koi_ogon": {"script": "carp/carp", "set": {"type": 4}, "zones": ["river"], "band": [0.3, 0.9], "count": 1, "size": [0.55, 0.7]},
	"lamprey": {"script": "lamprey/lamprey", "zones": ["river"], "band": [0.02, 0.3], "count": 2, "size": [0.6, 0.75]},
	"goldfish": {"script": "goldfish/goldfish", "zones": ["river"], "band": [0.2, 0.8], "count": 3, "size": [0.13, 0.18]},
	"betta": {"script": "betta/betta", "zones": ["river"], "band": [0.5, 0.95], "count": 3, "size": [0.07, 0.1]},
	"guppy": {"script": "guppy/guppy", "zones": ["river"], "band": [0.5, 0.95], "count": 6, "size": [0.05, 0.07]},
	"corydoras": {"script": "corydoras/corydoras", "how": "floor", "zones": ["river"], "band": [0.01, 0.05], "count": 4, "size": [0.07, 0.1]},
	"platy": {"script": "platy/platy", "zones": ["river"], "band": [0.3, 0.9], "count": 5, "size": [0.06, 0.08]},
	# The trench: what lives in the dark, with lights of its own.
	"anglerfish": {"script": "deep_anglerfish/deep_anglerfish", "zones": ["trench"], "band": [0.02, 0.3], "count": 3, "size": [0.5, 0.9]},
	"viperfish": {"script": "viperfish/viperfish", "zones": ["trench"], "band": [0.05, 0.4], "count": 3, "size": [0.35, 0.5]},
	"gulper": {"script": "gulper_eel/gulper_eel", "zones": ["trench"], "band": [0.05, 0.4], "count": 2, "size": [0.9, 1.3]},
	"ammonite": {"script": "ammonite/ammonite", "curls": false, "hunts": false, "zones": ["trench", "open"], "band": [0.1, 0.5], "count": 3, "size": [0.35, 0.5]},
	"horseshoe_crab": {"script": "horseshoe_crab/horseshoe_crab", "curls": false, "how": "floor", "hunts": false, "zones": ["sand", "grass"], "band": [0.0, 0.0], "count": 4, "size": [0.4, 0.55]},
	# What breathes air, and comes down from the surface to hunt.
	"otter": {"script": "sea_otter/sea_otter", "breathes": true, "zones": ["kelp"], "band": [0.7, 1.0], "count": 2, "size": [1.2, 1.3]},
	"seal": {"script": "harbor_seal/harbor_seal", "breathes": true, "zones": ["kelp", "grass"], "band": [0.5, 1.0], "count": 2, "size": [1.5, 1.7]},
	"sea_lion": {"script": "sea_lion/sea_lion", "breathes": true, "zones": ["kelp", "reef"], "band": [0.5, 1.0], "count": 2, "size": [2.0, 2.3]},
	"dolphin": {"script": "dolphin/dolphin", "breathes": true, "zones": ["open"], "band": [0.7, 1.0], "count": 3, "size": [2.5, 2.8]},
	"orca": {"script": "orca/orca", "breathes": true, "zones": ["open"], "band": [0.6, 1.0], "count": 1, "size": [6.5, 7.0]},
	"devil_ray": {"script": "devil_ray/devil_ray", "long": 0.64, "front": 0.32, "hunts": false, "zones": ["open", "sand"], "band": [0.5, 0.95], "count": 5, "size": [0.6, 0.7]},
	"eagle_ray": {"script": "spotted_eagle_ray/spotted_eagle_ray", "long": 1.15, "front": 0.575, "hunts": false, "zones": ["reef", "sand"], "band": [0.05, 0.4], "count": 2, "size": [1.1, 1.3]},
	"manta": {"script": "manta_ray/manta_ray", "long": 3.06, "front": 1.53, "how": "giant", "zones": ["open", "reef"], "band": [0.5, 0.9], "count": 2, "size": [3.0, 3.4]},
	# The giants: they cruise the open ocean and take no notice of a fish.
	"whale_shark": {"script": "whale_shark/whale_shark", "how": "giant", "zones": ["open"], "band": [0.6, 0.95], "count": 1, "size": [9.0, 10.0]},
	"humpback": {"script": "humpback_whale/humpback_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.5, 0.95], "count": 1, "size": [13.0, 14.0]},
	"gray_whale": {"script": "gray_whale/gray_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.4, 0.9], "count": 1, "size": [12.0, 13.0]},
	"fin_whale": {"script": "fin_whale/fin_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.5, 0.95], "count": 1, "size": [19.0, 20.0]},
	"blue_whale": {"script": "blue_whale/blue_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.5, 0.95], "count": 1, "size": [24.0, 25.0]},
	"sperm_whale": {"script": "sperm_whale/sperm_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.05, 0.9], "count": 1, "size": [14.0, 15.0]},
}

static var _scripts := {}


## Whether a kind can be made (its creature is installed; the old shark always can).
static func has(kind: String) -> bool:
	if not ALL.has(kind):
		return false
	var named: String = ALL[kind].script
	return named == "" or ResourceLoader.exists(_path(named))


## A kind's entry.
static func of(kind: String) -> Dictionary:
	return ALL.get(kind, {})


## A new creature of a kind, dressed (not yet in the tree), or null for the old shark.
static func make(kind: String) -> Node3D:
	var entry: Dictionary = ALL[kind]
	if entry.script == "":
		return null
	if not _scripts.has(kind):
		_scripts[kind] = load(_path(entry.script))
	var made: Node3D = (_scripts[kind] as GDScript).new()
	var sets: Dictionary = entry.get("set", {})
	for setting: String in sets:
		made.set(setting, sets[setting])
	return made


## How long a kind is as built (metres).
static func long_of(kind: String, made: Node3D) -> float:
	var long: float = ALL[kind].get("long", 0.0)
	if long <= 0.0:
		long = float((made.get_script() as GDScript).get_script_constant_map().get("LENGTH", 1.0))
	return long


static func _path(named: String) -> String:
	return "res://creatures/%s.gd" % named
