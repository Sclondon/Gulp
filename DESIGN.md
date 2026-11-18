# Gulp: the treasure game (design)

Written 2026-11-18 by Claude at the user's word. Everything not quoted is Claude's pick and can change.

## The user's words

- "Thinking about adding a mode where you return tomo, the boatm as the most valuable fish you can become- you sell
  fish for money to unlock better / deeper diving equipment so that you can open chests / look for your lost treasure
  plot"
- "and there could also be a regular fishing mode rather than only the odell down under"
- "yes make the design and implement it"
- Earlier the same day, which this ties together: "the boy should also have a diving suit that you can play as to
  walk along the sea floor"; "Pause menu and other Uis need the same treat ment as the the controls, and we need a way
  to view the evolution tree, and to add some roguelike elements"; "come up with some special abilities like inking as
  a squid"; the title ("a old timey franketstein computer hooked up to a helmet on the boys head- the controls for the
  pc are the controls for the game"); "Nick of Time ... is part of the inspiration".

## The idea in one paragraph

A boy, a sea captain and an old diver work a shrimp boat over Monterey Bay, looking for the boy's lost treasure.
The boat's machine puts the boy's mind into a fish. As a fish he eats and grows (the game as it is), and when he
swims back to the boat's net the fish he has become is hauled aboard and sold: the bigger and rarer, the more money.
Money buys gear. Better gear lets the machine reach deeper, lets the boat anchor further out, and gives the boy a
diving suit with a longer air hose, in which he walks the sea floor himself, opens chests in the wrecks and the
ruins, and finds the pieces of the treasure. Between times there is a rod over the side.

## The loop

1. **On deck** (the title scene, now also the hub). Three things to do, each a thing on the boat, not a menu list:
   the helmet (swim as a fish), the diving suit on its rack (dive), the rod (fish). The captain's chart table is the
   shop and the chart; the machine's screen shows the evolution tree.
2. **A fish run.** As now, with two changes: there is a way to end it well (swim into the net hung beside the boat:
   it shows on the sonar as its own sign), and the machine's signal only reaches so deep (below that the picture
   fills with static and the fish is turned back; gear raises it). Dying still ends the run, with nothing to sell.
3. **The sale.** The catch is weighed on the deck: kind, length, price. Price = the kind's worth per metre x length,
   doubled for the last kind of a growth line at full size. The first time a kind is sold pays a bonus and fills its
   place in the evolution tree.
4. **The shop** (the chart table). A few things, each with a few steps, bought in any order:
   - *Amplifier*: how deep the fish can go: 15 m, 30 m, 50 m, 100 m.
   - *Air hose and suit*: how deep the boy can walk: canvas suit 10 m, hard-hat 25 m, armoured 50 m, the deep suit 100 m.
   - *Engine and anchor chain*: where the boat can anchor: the bay's north (start), the docks, the kelp and the pirate
     ship, the liner off Point Lobos, the canyon over Atlantis.
   - *Tools*: a lamp (dark places and night), a crowbar (plain chests), a brass key ring (locked chests), a winch
     (heavy things).
   - *Tackle*: a better rod and line, for the fishing.
5. **A dive.** The boat anchors; the boy goes down the shot line in the suit and walks the floor (slow, heavy,
   bubbles, a hose trailing up to the boat that sets how far he can go; air is not a timer, the hose is the limit).
   He can open chests, pick up what is on the floor, and is in danger from what hunts there (he can hide, and tug the
   line to be hauled up). What he brings up is sold or kept.
6. **Fishing.** Played as the older brother (the user: "the older brother is the one who does the regular fishing").
   GameCommon's `fishing` (cast, nibble, hook, reel) from the boat's rail, with the sea's real kinds by
   where the boat is anchored. What is landed is sold the same way. A calm way to earn; less than a good run.

## The treasure

Five pieces, each in a chest that needs more gear than the last, so the plot is the gear ladder:
the docks (under the wharf, a plain chest); the pirate ship's hold (crowbar); the liner's saloon (key ring, hard-hat
suit); the temple at Atlantis (lamp, armoured suit); the last under the sleeping old one in the canyon's floor (the
deep suit, the winch). Each piece shows on the chart once found. Whose treasure it is ties to the photographs
below; beyond the user's words nothing is written. Ask before writing lore.

## The photographs (the plot)

The user: "when you are diving as the boy, there should be old photographs to find on the sea floor of the captain
young man with his love"; "you need to collect all the pics to ge t the plot"; "he should be a gay captain".

The story is not told in words. Scattered on the sea floor, found only as the diver, are old photographs of the
captain as a young man with the man he loved. Each is a sepia picture, in a cracked frame or loose and curling, half
under the sand, with a faint glint; picked up, it is shown large for a moment and goes into an album at the chart
table, in its place in the order the pictures were taken. All of them together give the plot, and the last chest
cannot be found without the full album. Claude's picks: twelve pictures, two or three at each place a suit can
reach, the deepest last. What each shows, who he was, and what became of him are NOT written: ask the user before
writing any of it. The pictures are concept-art work (generated, then quality passes), the two men drawn as the
captain is (a smooth mask of a face, no eyes; the captain's big nose, young and beardless or nearly).

## Roguelike elements

Within a fish run, at each growth choice, one of the cards is sometimes a *gift of the machine* instead of a kind
(the concept's upgrade cards): a faster burst, a harder hide (one bite forgiven), a magnet for small food, a longer
safe time, a special ability early. They last the run. The sea restocks differently each run (which swarms are
where, what hunts). Gear and the tree are what stays.

## Special abilities

The two switches on the panel. A kind may have one; a gift may lend one. First set: ink (squids, octopus, cuttlefish:
a cloud that blinds hunters), puff (pufferfish), shock (a ray), sprint (tuna, sailfish), sonar ping (dolphin, orca:
shows all food), gulp (whales: swallow a swarm). The player's growth tree has no squid line yet: add one.

## Screens

All of them in the brass and iron of the control panel (`tools/art_src/concept_menus.jpg`): the pause plate, the
evolution tree on a green tube screen, the sale scale, the shop at the chart table, the gift cards.

## What is saved

`user://gulp.cfg`: money, each gear step, kinds sold (for the tree), treasure pieces found, the longest fish.

## Order of building

1. Money, worth of kinds, the net and the sale, the signal's depth limit, the shop with the amplifier, saving. A plain
   but working screen for each.
2. The brass screens (pause, tree, sale, shop, cards) and the hub on deck.
3. The diving suit: concept, model on the boy, walking, the hose, chests, the first two treasure pieces.
4. Gifts and abilities.
5. Fishing from the boat.
6. The remaining treasure pieces, anchorages and tools.

## Open questions for the user

- (Answered, the user: "yes the arena should still be part of the fish control aspect": fish runs can be the online
  arena; how a sale works from an arena run is not designed yet.)
- Phones: walking as the diver needs the same stick and buttons; is the panel kept in the suit, or a simpler one?
- Does dying as a fish lose anything but the run?
