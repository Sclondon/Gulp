# Heads and hands for the three figures: fit a base mesh, do not loft

Written 2026-11-18 by Claude. The user: "The heads and hands need a lot of work on all three- make sure you are matching
pose silhouettes aggressively"; "why is his jaw just straight flat across? Are you misunderstanding where there jaw is ?";
"Also find any free models online to use as reference and look up ways to best generate models"; (of downloading them)
"you can download those things".

## Decision (Claude's pick, from the research the user asked for)

**What:** heads, ears and hands are no longer lofted from cross-section rings. Each starts from Blender Studio's
**Human Base Meshes v1.4.1** (CC0, public domain; downloaded from
`https://download.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip`, 49 MB, kept
OUTSIDE the repo at `C:\Projects\reference\human-base-meshes\bundle\human-base-meshes-bundle-v1.4.1\human_base_meshes_bundle.blend`)
and is fitted to the figure's own bare-head and hands sheets. Bodies stay our own lofted meshes.

**Why:** a jaw, a mouth, an eye socket, an ear and a hand need purpose-made edge loops; rings stacked up a head
cannot make them (the captain's jaw came out as a flat shelf, his ears as plates, hands as gloves, over ten rounds).
**The practice it follows:** fitting a known good topology to references (landmarks, lattice or proportional moves,
shrinkwrap at low strength), the usual way both artists and tools (MakeHuman, MetaHuman, wrap tools) make a new head.
**Alternatives:** keep lofting (failed); image-to-3D generators (dense triangle soup, weakest exactly at faces and hands,
licence and hardware limits: usable as a rough shape to compare against only); MPFB2/MakeHuman bodies (kept in reserve).

## What is in the bundle that we use

Open it with `--factory-startup --disable-autoexec`. Object names have odd spacing: match with spaces removed.

- `Head - Generic Topology`: 316 quads (632 triangles) as a cage, no neck, ears included as low loops, one UV map,
  a Subdivision modifier (level 1 gives about 2,500 triangles), and SHAPE KEYS `Real_MALE`, `Real_FEMALE`, `Real_Kid`,
  `Toon_MALE`, `Toon_FEMALE`, `Toon_Anime_Kid`, `Toon Animal`, `Ork`: start the captain and the brother from `Real_MALE` or
  `Toon_MALE`, the boy from `Real_Kid`. Loops: round each eye, round the mouth, nose bridge and wings, nasolabial, along
  the jaw to behind the ear.
- `Hand - Stylized`: 880 quads; un-subdivided once it is about 220 quads (about 440 triangles): wrist, palm with a thumb
  base, four three-segment fingers, clean knuckle loops.
- `GEO-head_stylized`: a denser stylised head WITH a neck and shoulders ring (4,134 quads; un-subdivide twice): reference
  for how a neck leaves a jaw.
- `GEO-ear_male_primitive_stylized.L`: a 94-quad ear with helix, bowl and lobe, if the generic head's ear is too crude.
- Also realistic heads, feet, skull and jaw for reference.

Pictures of these: render them yourself with the scratchpad's `hbm\look.py`.

## Method

1. Copy the base mesh's data into the build (append from the bundle in the build script; never edit the bundle).
   Apply the chosen shape key mix, mirror-symmetrise, strip modifiers.
2. Scale and place by landmarks from the figure's sheets (crown, brow, eye line, nose tip, mouth, chin bottom, jaw
   angles, ear top and lobe, nape, throat).
3. Fit: move landmark vertex groups to their sheet positions with smooth falloff (a lattice, or radial-basis / proportional
   displacement of all vertices from landmark pairs), then pull the outline to the sheet's silhouettes view by view
   (front, side, back; then three-quarter views), keeping the loops' order (never let rings cross: check for folded
   faces after every step). Low-strength shrinkwrap onto the OLD lofted head is allowed as a first guess only.
4. Judge in plain grey beside each sheet view at the same angle and size, with silhouette-difference pictures and
   landmark distances, and with the same soft top-front light to compare the shadow shapes under brow, nose, lip, chin, jaw.
5. Join to our body: bridge the head's open neck edge to the body's neck ring, and the hand's wrist edge to the forearm's
   last ring (matching vertex counts with a transition row); weights by the existing skeleton.
6. UVs: the base meshes' own UV maps are good; pack them into the figure's layout. Paint by projecting each sheet view by
   facing, then fix seams. Bare model: no hair, no beard, no hat.

## Rules that still hold

Bare base model; hair by hair shader later; tattoos as a movable overlay; planned UVs; nothing of the Twilight Princess
reference models is copied (they are a yardstick only); the bundle is CC0, so a mesh derived from it may ship, but the
bundle file itself stays out of the repo.
