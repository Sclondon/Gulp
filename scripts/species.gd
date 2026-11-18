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
## - slow: how fast it goes beside a fish of its length (left out: 1; a starfish creeps, 0 stays put).
## - hunts: it goes for the player when it is big enough to eat it (left out: it does).
## - breathes: it comes down from the surface and goes back up to it (seals, whales).
## - zones: where it lives (Sea.Zone names); band: the depth it keeps to there (0 the floor,
##   1 the surface); count; size: how long (from, to), metres.

const ALL := {
	# The player's own fish (also stocked in the sea).
	"sardine": {"script": "sardine/sardine", "zones": [], "count": 0, "size": [0.18, 0.24]},
	"smolt": {"script": "sockeye_salmon/sockeye_salmon", "set": {"stage": 2}, "zones": ["grass", "sand", "beach"], "band": [0.3, 0.9], "count": 5, "size": [0.5, 0.62], "social": "school", "group": [3, 5]},
	"salmon": {"script": "sockeye_salmon/sockeye_salmon", "set": {"stage": 3}, "zones": ["kelp", "open", "sand"], "band": [0.3, 0.9], "count": 5, "size": [0.9, 1.2], "social": "school", "group": [3, 5]},
	"tuna": {"script": "yellowfin_tuna/yellowfin_tuna", "set": {"first_dorsal": 0.25}, "zones": ["open"], "band": [0.5, 0.95], "count": 3, "size": [1.4, 1.9], "social": "school", "group": [3, 5], "mix": "tunas", "habit": "pack"},
	"shark": {"script": "", "zones": [], "count": 0, "size": [3.0, 5.0]},
	# The estuary's fish, in the sea grass.
	"loach": {"script": "clown_loach/clown_loach", "zones": ["river", "grass"], "band": [0.0, 0.25], "count": 3, "size": [0.16, 0.24], "social": "shoal", "group": [3, 3], "habit": "graze"},
	"trout": {"script": "cutthroat_trout/cutthroat_trout", "zones": ["river", "grass"], "band": [0.2, 0.8], "count": 3, "size": [0.3, 0.45], "social": "shoal", "group": [2, 5], "mix": "trout"},
	"golden": {"script": "cutthroat_trout/cutthroat_trout", "set": {"look": 1}, "zones": ["river"], "band": [0.2, 0.8], "count": 2, "size": [0.32, 0.45], "social": "shoal", "group": [2, 5], "mix": "trout"},
	"catfish": {"script": "channel_catfish/channel_catfish", "zones": ["river"], "band": [0.0, 0.1], "count": 2, "size": [0.55, 0.8], "habit": "graze"},
	# The kelp forest and the reef.
	"garibaldi": {"script": "garibaldi/garibaldi", "zones": ["kelp", "reef", "pirate"], "band": [0.05, 0.5], "count": 6, "size": [0.24, 0.34], "habit": "home"},
	"surfperch": {"script": "surfperch/surfperch", "zones": ["kelp", "docks", "beach", "grass"], "band": [0.1, 0.7], "count": 7, "size": [0.2, 0.34], "social": "shoal", "group": [3, 7]},
	"kelp_bass": {"script": "kelp_bass/kelp_bass", "zones": ["kelp", "docks", "pirate"], "band": [0.1, 0.8], "count": 5, "size": [0.4, 0.6], "social": "shoal", "group": [2, 3]},
	"rockfish": {"script": "rockfish/rockfish", "zones": ["reef", "kelp", "docks", "pirate"], "band": [0.02, 0.25], "count": 5, "size": [0.38, 0.55], "habit": "ambush"},
	"snapper": {"script": "snapper/snapper", "zones": ["reef", "pirate"], "band": [0.1, 0.6], "count": 4, "size": [0.5, 0.8], "social": "shoal", "group": [4, 4], "visits": true},
	"grouper": {"script": "grouper/grouper", "zones": ["reef", "ruins"], "band": [0.02, 0.3], "count": 2, "size": [1.0, 1.3], "habit": "ambush", "visits": true},
	"sea_bass": {"script": "giant_sea_bass/giant_sea_bass", "zones": ["kelp", "reef"], "band": [0.05, 0.4], "count": 2, "size": [1.8, 2.2], "visits": true},
	"barracuda": {"script": "barracuda/barracuda", "zones": ["kelp", "reef", "pirate"], "band": [0.6, 0.95], "count": 4, "size": [0.9, 1.2], "social": "school", "group": [4, 4], "habit": "pack"},
	"eel": {"script": "moray_eel/moray_eel", "front": 0.0, "curls": false, "how": "floor", "zones": ["reef", "kelp", "ruins", "pirate"], "band": [0.02, 0.1], "count": 3, "size": [1.4, 1.9], "habit": "ambush"},
	"octopus": {"script": "giant_pacific_octopus/giant_pacific_octopus", "long": 2.33, "front": 0.58, "curls": false, "how": "floor", "zones": ["reef", "ruins", "pirate", "docks"], "band": [0.03, 0.15], "count": 2, "size": [1.6, 2.2], "habit": "ambush"},
	"cuttlefish": {"script": "cuttlefish/cuttlefish", "zones": ["reef", "grass"], "band": [0.05, 0.4], "count": 3, "size": [0.35, 0.45], "habit": "strike"},
	# The coral reef's small fish (several kinds of butterflyfish and angelfish).
	"threadfin": {"script": "butterflyfish/butterflyfish", "set": {"type": 0}, "zones": ["reef"], "band": [0.05, 0.5], "count": 3, "size": [0.15, 0.2], "social": "shoal", "group": [6, 9], "mix": "reef_roam", "habit": "graze"},
	"raccoon": {"script": "butterflyfish/butterflyfish", "set": {"type": 1}, "zones": ["reef"], "band": [0.05, 0.5], "count": 3, "size": [0.15, 0.2], "social": "shoal", "group": [6, 9], "mix": "reef_roam", "habit": "graze"},
	"copperband": {"script": "butterflyfish/butterflyfish", "set": {"type": 2}, "zones": ["reef"], "band": [0.05, 0.4], "count": 2, "size": [0.15, 0.2], "social": "pair", "group": [2, 2]},
	"longnose": {"script": "butterflyfish/butterflyfish", "set": {"type": 3}, "zones": ["reef"], "band": [0.05, 0.4], "count": 2, "size": [0.15, 0.2], "social": "pair", "group": [2, 2]},
	"bannerfish": {"script": "butterflyfish/butterflyfish", "set": {"type": 4}, "zones": ["reef"], "band": [0.2, 0.7], "count": 3, "size": [0.16, 0.22], "social": "shoal", "group": [6, 9], "mix": "reef_roam", "habit": "graze"},
	"emperor": {"script": "angelfish/angelfish", "set": {"type": 0}, "zones": ["reef"], "band": [0.05, 0.5], "count": 2, "size": [0.3, 0.4], "social": "pair", "group": [2, 2], "visits": true},
	"queen": {"script": "angelfish/angelfish", "set": {"type": 1}, "zones": ["reef"], "band": [0.05, 0.5], "count": 2, "size": [0.3, 0.4], "social": "pair", "group": [2, 2], "visits": true},
	"french": {"script": "angelfish/angelfish", "set": {"type": 2}, "zones": ["reef"], "band": [0.05, 0.5], "count": 2, "size": [0.3, 0.42], "social": "pair", "group": [2, 2], "visits": true},
	"lionfish": {"script": "lionfish/lionfish", "zones": ["reef", "ruins"], "band": [0.03, 0.3], "count": 3, "size": [0.3, 0.4], "habit": "sting"},
	"parrotfish": {"script": "parrotfish/parrotfish", "zones": ["reef"], "band": [0.05, 0.5], "count": 4, "size": [0.4, 0.55], "social": "harem", "group": [4, 4], "habit": "graze", "visits": true},
	"cleaner": {"script": "wrasse/wrasse", "set": {"kind": 0}, "zones": ["reef"], "band": [0.05, 0.5], "count": 3, "size": [0.12, 0.16], "habit": "cleaner"},
	"wrasse": {"script": "wrasse/wrasse", "set": {"kind": 1}, "zones": ["reef"], "band": [0.05, 0.6], "count": 3, "size": [0.2, 0.28], "social": "harem", "group": [3, 3]},
	"yellow_tang": {"script": "surgeonfish/surgeonfish", "set": {"kind": 0}, "zones": ["reef"], "band": [0.05, 0.6], "count": 6, "size": [0.18, 0.24], "social": "shoal", "group": [6, 9], "mix": "reef_roam", "habit": "graze"},
	"surgeonfish": {"script": "surgeonfish/surgeonfish", "set": {"kind": 1}, "zones": ["reef"], "band": [0.05, 0.6], "count": 3, "size": [0.2, 0.28], "social": "shoal", "group": [6, 9], "mix": "reef_roam", "habit": "graze"},
	"convict": {"script": "surgeonfish/surgeonfish", "set": {"kind": 2}, "zones": ["reef"], "band": [0.05, 0.6], "count": 5, "size": [0.18, 0.24], "social": "shoal", "group": [6, 9], "mix": "reef_roam", "habit": "graze"},
	"blue_tang": {"script": "blue_tang/blue_tang", "zones": ["reef"], "band": [0.1, 0.7], "count": 4, "size": [0.2, 0.27], "social": "shoal", "group": [6, 9], "mix": "reef_roam", "habit": "graze"},
	"clownfish": {"script": "clownfish/clownfish", "zones": ["reef"], "band": [0.02, 0.15], "count": 5, "size": [0.09, 0.12], "habit": "home"},
	# The sand flats.
	"halibut": {"script": "california_halibut/california_halibut", "how": "floor", "zones": ["sand", "beach"], "band": [0.01, 0.05], "count": 3, "size": [0.8, 1.1], "habit": "ambush"},
	"stingray": {"script": "round_stingray/round_stingray", "how": "floor", "zones": ["sand", "beach"], "band": [0.01, 0.04], "count": 4, "size": [0.4, 0.5]},
	"bat_ray": {"script": "bat_ray/bat_ray", "zones": ["sand", "beach", "river", "docks"], "band": [0.05, 0.35], "count": 3, "size": [1.0, 1.4], "social": "school", "group": [3, 3]},
	"leopard_shark": {"script": "leopard_shark/leopard_shark", "zones": ["beach", "river", "sand"], "band": [0.03, 0.3], "count": 3, "size": [1.3, 1.6], "social": "shoal", "group": [3, 3]},
	# What walks on the bottom.
	"crab": {"script": "rock_crab/rock_crab", "hunts": false, "long": 0.16, "turn": 1.5708, "curls": false, "how": "floor", "zones": ["reef", "kelp", "sand", "docks", "pirate", "beach"], "band": [0.0, 0.0], "count": 8, "size": [0.12, 0.2]},
	"prawn": {"script": "spot_prawn/spot_prawn", "hunts": false, "curls": false, "how": "floor", "zones": ["reef", "grass", "docks"], "band": [0.0, 0.0], "count": 8, "size": [0.15, 0.22]},
	"lobster": {"script": "spiny_lobster/spiny_lobster", "hunts": false, "curls": false, "how": "floor", "zones": ["reef", "kelp", "pirate"], "band": [0.0, 0.0], "count": 4, "size": [0.4, 0.6]},
	"nudibranch": {"script": "nudibranch/nudibranch", "hunts": false, "curls": false, "how": "floor", "zones": ["reef", "kelp", "docks"], "band": [0.0, 0.0], "count": 6, "size": [0.1, 0.16]},
	# The open ocean, beyond the shelf's edge.
	"mackerel": {"script": "pacific_mackerel/pacific_mackerel", "zones": ["open", "kelp"], "band": [0.5, 0.95], "count": 4, "size": [0.36, 0.44], "social": "school", "group": [4, 4], "habit": "pack"},
	"flying": {"script": "flying_fish/flying_fish", "zones": ["open"], "band": [0.85, 1.0], "count": 6, "size": [0.24, 0.32], "social": "school", "group": [3, 3], "leaps": true},
	"bonito": {"script": "pacific_bonito/pacific_bonito", "zones": ["open", "kelp"], "band": [0.5, 0.95], "count": 4, "size": [0.6, 0.85], "social": "school", "group": [4, 4], "habit": "pack"},
	"mahi": {"script": "mahi_mahi/mahi_mahi", "zones": ["open"], "band": [0.8, 0.98], "count": 3, "size": [1.0, 1.4], "social": "school", "group": [3, 3], "habit": "pack", "leaps": true},
	"wahoo": {"script": "wahoo/wahoo", "zones": ["open"], "band": [0.6, 0.95], "count": 2, "size": [1.6, 2.0]},
	"bigeye": {"script": "bigeye_tuna/bigeye_tuna", "zones": ["open"], "band": [0.3, 0.7], "count": 2, "size": [1.6, 2.0], "social": "school", "group": [3, 5], "mix": "tunas", "habit": "pack"},
	"bluefin": {"script": "bluefin_tuna/bluefin_tuna", "zones": ["open"], "band": [0.4, 0.9], "count": 2, "size": [2.2, 2.8], "social": "school", "group": [2, 2], "habit": "pack"},
	"humboldt": {"script": "humboldt_squid/humboldt_squid", "long": 2.2, "front": 1.3, "curls": false, "set": {"colour_beat": 7.0}, "zones": ["open"], "band": [0.1, 0.45], "count": 3, "size": [1.9, 2.4], "social": "school", "group": [3, 3], "habit": "pack"},
	"sailfish": {"script": "sailfish/sailfish", "zones": ["open"], "band": [0.7, 0.97], "count": 2, "size": [2.5, 3.0], "social": "school", "group": [2, 2], "habit": "pack"},
	"swordfish": {"script": "swordfish/swordfish", "zones": ["open"], "band": [0.3, 0.8], "count": 2, "size": [3.1, 3.8]},
	"marlin": {"script": "blue_marlin/blue_marlin", "zones": ["open"], "band": [0.6, 0.95], "count": 2, "size": [3.2, 3.8], "habit": "pack"},
	"blue_shark": {"script": "blue_shark/blue_shark", "zones": ["open", "ruins"], "band": [0.4, 0.95], "count": 2, "size": [2.6, 3.2], "habit": "stalk"},
	"white_shark": {"script": "white_shark/white_shark", "zones": ["open", "kelp", "ruins"], "band": [0.3, 0.9], "count": 1, "size": [4.6, 5.0], "habit": "stalk"},
	"giant": {"script": "giant_squid/giant_squid", "long": 5.1, "front": 2.2, "curls": false, "zones": ["trench"], "band": [ 0.05, 0.5], "count": 1, "size": [7.0, 7.0]},
	# The river mouth, among the mangroves: fresh-water fish.
	"arowana": {"script": "arowana/arowana", "zones": ["river"], "band": [0.8, 1.0], "count": 2, "size": [0.8, 1.0], "leaps": true},
	"piranha": {"script": "piranha/piranha", "zones": ["river"], "band": [0.2, 0.8], "count": 5, "size": [0.25, 0.32], "social": "school", "group": [5, 5]},
	"pike": {"script": "northern_pike/northern_pike", "zones": ["river"], "band": [0.2, 0.7], "count": 2, "size": [0.9, 1.1], "habit": "ambush"},
	"perch": {"script": "yellow_perch/yellow_perch", "zones": ["river", "grass"], "band": [0.2, 0.7], "count": 4, "size": [0.25, 0.32], "social": "shoal", "group": [4, 4]},
	"walleye": {"script": "walleye/walleye", "zones": ["river"], "band": [0.05, 0.5], "count": 2, "size": [0.6, 0.75], "social": "shoal", "group": [2, 2], "nocturnal": true},
	"gar": {"script": "gar/gar", "zones": ["river"], "band": [0.6, 0.95], "count": 2, "size": [1.1, 1.4], "habit": "ambush"},
	"carp": {"script": "carp/carp", "set": {"type": 0}, "zones": ["river"], "band": [0.05, 0.4], "count": 2, "size": [0.6, 0.75], "social": "shoal", "group": [3, 4], "mix": "carp", "habit": "graze"},
	"koi": {"script": "carp/carp", "set": {"type": 1}, "zones": ["river"], "band": [0.3, 0.9], "count": 2, "size": [0.55, 0.7], "social": "shoal", "group": [3, 4], "mix": "carp", "habit": "graze"},
	"koi_sanke": {"script": "carp/carp", "set": {"type": 2}, "zones": ["river"], "band": [0.3, 0.9], "count": 1, "size": [0.55, 0.7], "social": "shoal", "group": [3, 4], "mix": "carp", "habit": "graze"},
	"koi_showa": {"script": "carp/carp", "set": {"type": 3}, "zones": ["river"], "band": [0.3, 0.9], "count": 1, "size": [0.55, 0.7], "social": "shoal", "group": [3, 4], "mix": "carp", "habit": "graze"},
	"koi_ogon": {"script": "carp/carp", "set": {"type": 4}, "zones": ["river"], "band": [0.3, 0.9], "count": 1, "size": [0.55, 0.7], "social": "shoal", "group": [3, 4], "mix": "carp", "habit": "graze"},
	"lamprey": {"script": "lamprey/lamprey", "zones": ["river"], "band": [0.02, 0.3], "count": 2, "size": [0.6, 0.75]},
	"goldfish": {"script": "goldfish/goldfish", "zones": ["river"], "band": [0.2, 0.8], "count": 3, "size": [0.13, 0.18], "social": "shoal", "group": [3, 5], "mix": "goldfish", "habit": "graze"},
	"betta_red": {"script": "betta/betta", "set": {"type": 1}, "zones": ["river"], "band": [0.5, 0.95], "count": 1, "size": [0.07, 0.1], "habit": "display"},
	"betta_marble": {"script": "betta/betta", "set": {"type": 2}, "zones": ["river"], "band": [0.5, 0.95], "count": 1, "size": [0.07, 0.1], "habit": "display"},
	"betta": {"script": "betta/betta", "zones": ["river"], "band": [0.5, 0.95], "count": 1, "size": [0.07, 0.1], "habit": "display"},
	"guppy_female": {"script": "guppy/guppy", "set": {"type": 0}, "zones": ["river"], "band": [0.5, 0.95], "count": 3, "size": [0.06, 0.08], "social": "shoal", "group": [4, 7], "mix": "livebearers"},
	"guppy_red": {"script": "guppy/guppy", "set": {"type": 2}, "zones": ["river"], "band": [0.5, 0.95], "count": 2, "size": [0.05, 0.07], "social": "shoal", "group": [4, 7], "mix": "livebearers"},
	"guppy_blue": {"script": "guppy/guppy", "set": {"type": 3}, "zones": ["river"], "band": [0.5, 0.95], "count": 2, "size": [0.05, 0.07], "social": "shoal", "group": [4, 7], "mix": "livebearers"},
	"guppy_cobra": {"script": "guppy/guppy", "set": {"type": 4}, "zones": ["river"], "band": [0.5, 0.95], "count": 2, "size": [0.05, 0.07], "social": "shoal", "group": [4, 7], "mix": "livebearers"},
	"guppy": {"script": "guppy/guppy", "set": {"type": 1}, "zones": ["river"], "band": [0.5, 0.95], "count": 2, "size": [0.05, 0.07], "social": "shoal", "group": [4, 7], "mix": "livebearers"},
	"corydoras": {"script": "corydoras/corydoras", "hunts": false, "how": "floor", "zones": ["river"], "band": [0.01, 0.05], "count": 2, "size": [0.07, 0.1], "social": "school", "group": [4, 4], "mix": "cory"},
	"goldfish_fantail": {"script": "goldfish/goldfish", "set": {"kind": 1, "colouring": 2}, "zones": ["river"], "band": [0.2, 0.8], "count": 2, "size": [0.13, 0.18], "social": "shoal", "group": [3, 5], "mix": "goldfish", "habit": "graze"},
	"corydoras_panda": {"script": "corydoras/corydoras", "hunts": false, "set": {"kind": 1}, "how": "floor", "zones": ["river"], "band": [0.01, 0.05], "count": 2, "size": [0.07, 0.1], "social": "school", "group": [4, 4], "mix": "cory"},
	"platy_wagtail": {"script": "platy/platy", "set": {"colouring": 1}, "zones": ["river"], "band": [0.3, 0.9], "count": 2, "size": [0.06, 0.08], "social": "shoal", "group": [4, 7], "mix": "livebearers"},
	"platy_blue": {"script": "platy/platy", "set": {"colouring": 2}, "zones": ["river"], "band": [0.3, 0.9], "count": 2, "size": [0.06, 0.08], "social": "shoal", "group": [4, 7], "mix": "livebearers"},
	"platy": {"script": "platy/platy", "zones": ["river"], "band": [0.3, 0.9], "count": 2, "size": [0.06, 0.08], "social": "shoal", "group": [4, 7], "mix": "livebearers"},
	# The trench: what lives in the dark, with lights of its own.
	"anglerfish": {"script": "deep_anglerfish/deep_anglerfish", "zones": ["trench", "ruins"], "band": [0.02, 0.3], "count": 3, "size": [0.5, 0.9], "habit": "ambush"},
	"viperfish": {"script": "viperfish/viperfish", "zones": ["trench", "ruins"], "band": [0.05, 0.4], "count": 3, "size": [0.35, 0.5], "habit": "ambush", "nocturnal": true},
	"gulper": {"script": "gulper_eel/gulper_eel", "zones": ["trench"], "band": [0.05, 0.4], "count": 2, "size": [0.9, 1.3], "habit": "ambush"},
	"ammonite": {"script": "ammonite/ammonite", "curls": false, "hunts": false, "zones": ["trench", "open", "ruins"], "band": [0.1, 0.5], "count": 3, "size": [0.35, 0.5], "social": "shoal", "group": [3, 3], "habit": "drift"},
	"horseshoe_crab": {"script": "horseshoe_crab/horseshoe_crab", "curls": false, "how": "floor", "hunts": false, "zones": ["sand", "grass", "beach"], "band": [0.0, 0.0], "count": 4, "size": [0.4, 0.55]},
	# What breathes air, and comes down from the surface to hunt.
	"otter": {"script": "sea_otter/sea_otter", "breathes": true, "zones": ["kelp", "docks", "river"], "band": [0.7, 1.0], "count": 2, "size": [1.2, 1.3], "social": "shoal", "group": [2, 2], "habit": "float"},
	"seal": {"script": "harbor_seal/harbor_seal", "breathes": true, "zones": ["kelp", "docks", "river"], "band": [0.5, 1.0], "count": 2, "size": [1.5, 1.7]},
	"sea_lion": {"script": "sea_lion/sea_lion", "breathes": true, "zones": ["kelp", "docks", "reef"], "band": [0.5, 1.0], "count": 2, "size": [2.0, 2.3], "social": "shoal", "group": [2, 2], "habit": "pack"},
	"dolphin": {"script": "dolphin/dolphin", "breathes": true, "zones": ["open"], "band": [0.7, 1.0], "count": 3, "size": [2.5, 2.8], "social": "pod", "group": [3, 3], "habit": "pack", "leaps": true},
	"orca": {"script": "orca/orca", "breathes": true, "zones": ["open"], "band": [0.6, 1.0], "count": 3, "size": [6.5, 7.0], "social": "pod", "group": [3, 3], "habit": "pack"},
	# Marine reptiles (the user, 2026-11-18): in the open ocean (Claude's pick of place, numbers and sizes).
	"ichthyosaur": {"script": "ichthyosaur/ichthyosaur", "breathes": true, "zones": ["open"], "band": [0.5, 1.0], "count": 2, "size": [3.6, 4.2], "social": "pod", "group": [2, 2], "habit": "pack"},
	"mosasaur": {"script": "mosasaur/mosasaur", "breathes": true, "zones": ["open"], "band": [0.3, 0.9], "count": 1, "size": [10.0, 12.0], "habit": "stalk"},
	"plesiosaur": {"script": "plesiosaur/plesiosaur", "long": 9.0, "front": 4.3, "curls": false, "breathes": true, "zones": ["open"], "band": [0.4, 0.95], "count": 1, "size": [8.0, 9.0]},
	# Arctic animals (the user, 2026-11-18); there is no cold sea here yet, so they are in the open ocean (Claude's pick).
	"walrus": {"script": "walrus/walrus", "breathes": true, "hunts": false, "zones": ["open"], "band": [0.2, 0.9], "count": 1, "size": [2.8, 3.2], "habit": "graze"},
	"narwhal": {"script": "narwhal/narwhal", "breathes": true, "hunts": false, "zones": ["open"], "band": [0.5, 1.0], "count": 2, "size": [4.2, 4.6], "social": "pod", "group": [2, 2]},
	"devil_ray": {"script": "devil_ray/devil_ray", "long": 0.64, "front": 0.32, "hunts": false, "zones": ["open", "sand"], "band": [0.5, 0.95], "count": 5, "size": [0.6, 0.7], "social": "school", "group": [5, 5], "habit": "filter"},
	"eagle_ray": {"script": "spotted_eagle_ray/spotted_eagle_ray", "long": 1.15, "front": 0.575, "hunts": false, "zones": ["reef", "sand", "beach"], "band": [0.05, 0.4], "count": 2, "size": [1.1, 1.3], "social": "school", "group": [2, 2]},
	"manta": {"script": "manta_ray/manta_ray", "long": 3.06, "front": 1.53, "how": "giant", "zones": ["open", "reef"], "band": [0.5, 0.9], "count": 2, "size": [3.0, 3.4], "habit": "filter", "visits": true},
	# More of the user's second list (2026-11-18); places, numbers and sizes are Claude's picks.
	"green_turtle": {"script": "sea_turtle/sea_turtle", "set": {"type": 0}, "long": 1.1, "front": 0.712, "curls": false, "hunts": false, "breathes": true, "zones": ["grass", "reef", "ruins"], "band": [0.2, 0.9], "count": 2, "size": [0.9, 1.2], "habit": "graze"},
	"hawksbill": {"script": "sea_turtle/sea_turtle", "set": {"type": 1}, "long": 0.9, "front": 0.611, "curls": false, "hunts": false, "breathes": true, "zones": ["reef", "ruins"], "band": [0.1, 0.8], "count": 2, "size": [0.7, 0.9], "habit": "graze", "visits": true},
	"loggerhead": {"script": "sea_turtle/sea_turtle", "set": {"type": 2}, "long": 1.0, "front": 0.738, "curls": false, "hunts": false, "breathes": true, "zones": ["kelp", "open", "ruins"], "band": [0.3, 0.9], "count": 1, "size": [0.9, 1.1]},
	"leatherback": {"script": "sea_turtle/sea_turtle", "set": {"type": 3}, "long": 1.8, "front": 1.161, "curls": false, "hunts": false, "breathes": true, "zones": ["open"], "band": [0.4, 0.95], "count": 1, "size": [1.7, 2.0]},
	"pufferfish": {"script": "pufferfish/pufferfish", "hunts": false, "zones": ["reef", "sand", "pirate"], "band": [0.05, 0.5], "count": 4, "size": [0.22, 0.32], "habit": "shy"},
	"seahorse": {"script": "seahorse/seahorse", "set": {"type": 0}, "long": 0.15, "curls": false, "hunts": false, "slow": 0.25, "zones": ["grass"], "band": [0.02, 0.2], "count": 5, "size": [0.16, 0.22], "social": "pair", "group": [2, 2], "habit": "cling"},
	"thorny_seahorse": {"script": "seahorse/seahorse", "set": {"type": 1}, "long": 0.15, "curls": false, "hunts": false, "slow": 0.25, "zones": ["reef", "kelp"], "band": [0.02, 0.2], "count": 4, "size": [0.13, 0.17], "social": "pair", "group": [2, 2], "habit": "cling"},
	"pygmy_seahorse": {"script": "seahorse/seahorse", "set": {"type": 2}, "long": 0.15, "curls": false, "hunts": false, "slow": 0.25, "zones": ["reef"], "band": [0.02, 0.15], "count": 5, "size": [0.02, 0.03], "habit": "cling"},
	"cleaner_shrimp": {"script": "shrimps/shrimp", "set": {"kind": 0}, "long": 0.058, "curls": false, "hunts": false, "how": "floor", "zones": ["reef"], "band": [0.0, 0.0], "count": 6, "size": [0.05, 0.07], "habit": "cleaner"},
	"mantis_shrimp": {"script": "shrimps/shrimp", "set": {"kind": 1}, "long": 0.1485, "curls": false, "hunts": false, "how": "floor", "zones": ["reef", "sand"], "band": [0.0, 0.0], "count": 4, "size": [0.13, 0.18], "habit": "strike"},
	"pistol_shrimp": {"script": "shrimps/shrimp", "set": {"kind": 2}, "long": 0.045, "curls": false, "hunts": false, "how": "floor", "zones": ["sand"], "band": [0.0, 0.0], "count": 5, "size": [0.04, 0.05], "habit": "strike"},
	"starfish": {"script": "starfish/starfish", "set": {"kind": 0}, "long": 0.26, "curls": false, "hunts": false, "how": "floor", "slow": 0.03, "zones": ["kelp", "reef", "docks", "pirate"], "band": [0.0, 0.0], "count": 8, "size": [0.2, 0.3]},
	"sunflower_star": {"script": "starfish/starfish", "set": {"kind": 1}, "long": 0.58, "curls": false, "hunts": false, "how": "floor", "slow": 0.05, "zones": ["kelp", "docks"], "band": [0.0, 0.0], "count": 3, "size": [0.5, 0.7]},
	"brittle_star": {"script": "starfish/starfish", "set": {"kind": 2}, "long": 0.19, "curls": false, "hunts": false, "how": "floor", "slow": 0.08, "zones": ["reef", "trench", "ruins"], "band": [0.0, 0.0], "count": 6, "size": [0.15, 0.22]},
	"long_spined_urchin": {"script": "sea_urchin/sea_urchin", "set": {"kind": 0}, "long": 0.29, "curls": false, "hunts": false, "how": "floor", "slow": 0.02, "zones": ["reef"], "band": [0.0, 0.0], "count": 6, "size": [0.24, 0.32], "habit": "shy"},
	"purple_urchin": {"script": "sea_urchin/sea_urchin", "set": {"kind": 1}, "long": 0.13, "curls": false, "hunts": false, "how": "floor", "slow": 0.02, "zones": ["kelp", "docks"], "band": [0.0, 0.0], "count": 10, "size": [0.1, 0.15], "habit": "shy"},
	"pencil_urchin": {"script": "sea_urchin/sea_urchin", "set": {"kind": 2}, "long": 0.17, "curls": false, "hunts": false, "how": "floor", "slow": 0.02, "zones": ["reef"], "band": [0.0, 0.0], "count": 5, "size": [0.14, 0.2], "habit": "shy"},
	"feather_star": {"script": "crinoid/crinoid", "set": {"kind": 0}, "long": 0.3, "curls": false, "hunts": false, "how": "floor", "slow": 0.0, "zones": ["reef"], "band": [0.0, 0.0], "count": 5, "size": [0.25, 0.35], "habit": "shy"},
	"sea_lily": {"script": "crinoid/crinoid", "set": {"kind": 2}, "long": 0.5, "curls": false, "hunts": false, "how": "floor", "slow": 0.0, "zones": ["trench", "ruins"], "band": [0.0, 0.0], "count": 6, "size": [0.45, 0.6], "habit": "shy"},
	"sea_hare": {"script": "sea_slug/sea_slug", "set": {"kind": 0}, "long": 0.3, "curls": false, "hunts": false, "how": "floor", "slow": 0.12, "zones": ["grass", "kelp", "docks"], "band": [0.0, 0.0], "count": 5, "size": [0.2, 0.35]},
	"spanish_dancer": {"script": "sea_slug/sea_slug", "set": {"kind": 2, "swim": 1.0}, "long": 0.3, "curls": false, "hunts": false, "slow": 0.25, "zones": ["reef"], "band": [0.05, 0.4], "count": 3, "size": [0.25, 0.4], "habit": "drift"},
	"giant_clam": {"script": "clam/clam", "set": {"kind": 0, "open": 0.7}, "long": 1.0, "curls": false, "how": "giant", "slow": 0.0, "zones": ["reef"], "band": [0.0, 0.0], "count": 4, "size": [0.7, 1.1], "habit": "shy"},
	"scallop": {"script": "clam/clam", "set": {"kind": 1, "open": 0.5}, "long": 0.078, "curls": false, "hunts": false, "how": "floor", "slow": 0.0, "zones": ["sand", "beach"], "band": [0.0, 0.0], "count": 10, "size": [0.07, 0.11], "habit": "hop"},
	"razor_clam": {"script": "clam/clam", "set": {"kind": 2}, "long": 0.15, "curls": false, "hunts": false, "how": "floor", "slow": 0.0, "zones": ["sand", "grass", "beach"], "band": [0.0, 0.0], "count": 8, "size": [0.12, 0.18], "habit": "shy"},
	"oyster": {"script": "oyster/oyster", "set": {"kind": 1, "open": 0.6, "pearl": true}, "long": 0.184, "curls": false, "hunts": false, "how": "floor", "slow": 0.0, "zones": ["river", "grass", "docks"], "band": [0.0, 0.0], "count": 8, "size": [0.2, 0.3], "habit": "shy"},
	"cameroceras": {"script": "cameroceras/cameroceras", "curls": false, "zones": ["open", "trench", "ruins"], "band": [0.1, 0.6], "count": 1, "size": [5.0, 6.0]},
	"anomalocaris": {"script": "anomalocaris/anomalocaris", "curls": false, "zones": ["reef", "sand", "ruins"], "band": [0.1, 0.5], "count": 2, "size": [0.7, 0.9]},
	"trilobite": {"script": "trilobite/trilobite", "set": {"kind": 0}, "long": 0.15, "curls": false, "hunts": false, "how": "floor", "slow": 0.5, "zones": ["sand", "grass", "ruins"], "band": [0.0, 0.0], "count": 8, "size": [0.12, 0.18]},
	"spiny_trilobite": {"script": "trilobite/trilobite", "set": {"kind": 1}, "long": 0.2, "curls": false, "hunts": false, "how": "floor", "slow": 0.5, "zones": ["reef", "ruins"], "band": [0.0, 0.0], "count": 5, "size": [0.16, 0.24]},
	"cheeked_trilobite": {"script": "trilobite/trilobite", "set": {"kind": 2}, "long": 0.3, "curls": false, "hunts": false, "how": "floor", "slow": 0.5, "zones": ["sand", "trench", "ruins"], "band": [0.0, 0.0], "count": 5, "size": [0.25, 0.35]},
	# The trench's glowing animals.
	"dumbo_octopus": {"script": "dumbo_octopus/dumbo_octopus", "set": {"glow": 1.0}, "curls": false, "hunts": false, "slow": 0.4, "zones": ["trench", "ruins"], "band": [0.05, 0.5], "count": 3, "size": [0.25, 0.4], "habit": "drift"},
	"firefly_squid": {"script": "firefly_squid/firefly_squid", "set": {"glow": 1.2}, "curls": false, "hunts": false, "zones": ["trench", "ruins"], "band": [0.1, 0.8], "count": 10, "size": [0.06, 0.08], "social": "school", "group": [5, 5], "habit": "drift", "nocturnal": true},
	"comb_jelly": {"script": "comb_jelly/comb_jelly", "set": {"glow": 1.0}, "curls": false, "hunts": false, "slow": 0.3, "zones": ["trench", "open", "ruins"], "band": [0.2, 0.9], "count": 8, "size": [0.08, 0.14], "habit": "drift"},
	"pyrosome": {"script": "pyrosome/pyrosome", "set": {"glow": 1.0}, "curls": false, "how": "giant", "zones": ["trench", "open", "ruins"], "band": [0.2, 0.7], "count": 2, "size": [1.6, 2.4], "habit": "drift"},
	# The giants: they cruise the open ocean and take no notice of a fish.
	"whale_shark": {"script": "whale_shark/whale_shark", "how": "giant", "zones": ["open"], "band": [0.6, 0.95], "count": 1, "size": [9.0, 10.0], "habit": "filter"},
	"humpback": {"script": "humpback_whale/humpback_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.5, 0.95], "count": 1, "size": [13.0, 14.0], "habit": "filter"},
	"gray_whale": {"script": "gray_whale/gray_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.4, 0.9], "count": 1, "size": [12.0, 13.0], "habit": "graze"},
	"fin_whale": {"script": "fin_whale/fin_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.5, 0.95], "count": 1, "size": [19.0, 20.0], "habit": "filter"},
	# Sea monsters (the user, 2026-11-18: "leviathan, sea monster, cthulu old one, and godzilla like designs"):
	# the leviathan a harmless giant of the deep, the sea serpent a stalker along the shelf's edge (Claude's
	# places, numbers and sizes).
	"leviathan": {"script": "leviathan/leviathan", "how": "giant", "zones": ["open", "trench"], "band": [0.2, 0.7], "count": 1, "size": [36.0, 40.0], "habit": "filter"},
	"sea_serpent": {"script": "sea_serpent/sea_serpent", "zones": ["open"], "band": [0.3, 0.9], "count": 1, "size": [22.0, 25.0], "habit": "stalk"},
	"blue_whale": {"script": "blue_whale/blue_whale", "how": "giant", "breathes": true, "zones": ["open"], "band": [0.5, 0.95], "count": 1, "size": [24.0, 25.0], "habit": "filter"},
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
