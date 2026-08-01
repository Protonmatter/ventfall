# Implementation notes

## Structure

`index.html` is self-contained: styles, markup and the full game in one file.
The game is an IIFE with no globals leaked.

Main systems, in source order:

- `DEFS` / `UPGRADES` — all unit, structure and upgrade data. Balance lives here.
- `Audio_` — Web Audio synthesis. Every cue is oscillators plus filtered noise.
  `gate(tag, ms)` throttles repeats so 30 units firing doesn't blow out the mix.
- terrain generation — seeded, with a protected corridor between the two bases
- spatial hash (`rehash` / `near`) — 64px buckets, rebuilt each frame
- `tickUnit` / `tickBld` — per-entity simulation
- `steer` / `separate` — obstacle avoidance and crowd separation
- fog of war — three states (unseen / explored / visible) on a tile grid
- `tickAI` — opponent economy, tech and wave logic
- render — canvas draw, then the sonar scope

## Things worth knowing before editing

**Upgrades never mutate `DEFS`.** They are read through `uHp()`, `uRng()` and
`uSpd()`, which take a team. This keeps the two teams independent — the AI can
have Servo Drives while you don't. If you add a stat that upgrades touch, add a
helper rather than writing into `DEFS`.

**Ablative Plating rescales existing units** in `tickBld`, preserving each unit's
damage percentage so researching mid-fight doesn't act as a heal.

**Mortar shells target a ground point, not an entity.** `shoot()` drops the
target reference when `splash` is set, so the shell lands where the target *was*
and can be dodged. Splash falls off linearly to 45% at the edge.

**`attackTick` holds a local reference to the target.** Killing an entity nulls
`u.tgt` mid-call, so reading `u.tgt` after `damage()` throws. Keep the local.

**The canvas must be sized with explicit `width`/`height` in CSS**, not `inset`.
Canvas is a replaced element; with `width:auto` it keeps its intrinsic 300×150
regardless of positioning, and every pointer event lands on the parent instead.

**Edge-scroll is gated on `mouse.inside`.** Without it, the default pointer
position sits in the scroll zone and the camera runs to the map corner on load.

**The base-to-base corridor is on `tx + ty`**, not `tx - ty`. The bases sit at
roughly (11, 60) and (60, 11). Protecting the wrong diagonal walls off the map
and attack waves pile against terrain halfway across.

**The HUD rebuilds only on change.** `lastSig` holds signatures for the command
grid, roster and queue. Rebuilding every frame destroys buttons mid-click and
breaks keyboard focus.

## Balance dials

- `waveSize` (start 6), `+3` per wave, cap 20 — enemy push size
- `firstPush` (95s) — grace period before the first attack, also reused as the
  inter-wave cooldown (26s)
- `DEFS[x].cost` / `.train` — economy pacing
- crew cap is `gives: 8` per Habitat, hard cap 120

## Known rough edges

- Crew capacity is tight early; a second Habitat is close to mandatory.
- Pathing is local steering with a stuck-detector, not a planner. Units handle
  concave terrain but can take scenic routes on long diagonals.
- Tier II sprites have not been eyeballed at scale in a large mixed squad.
