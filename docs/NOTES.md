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

**Construction HP is additive.** `tickBld` adds `maxHp*.88*(dProg/work)` per
tick instead of assigning HP from total progress — assigning would silently heal
any damage the site took, making unfinished buildings unkillable while a worker
stands next to them.

**Research survives its building.** `G.research[team].bld` is reassigned to
another built Deepworks in `killEnt`, or refunded and cleared if none exists.
Without this the slot stays occupied forever and the team can never research
again.

**Physics is dt-scaled.** Damping uses `Math.pow(base, dt*60)` and impulses
multiply by `dt*60` (clamped), so 144Hz displays play like 60Hz ones. Don't add
a bare `u.vx*=k` — it re-introduces refresh-rate-dependent movement.

**All world/screen conversion goes through `s2w()` and `vw()`/`vh()`.** The
renderer applies `scale(zoom)` before the camera translate; camera clamps,
culling rects, the fog/terrain blit windows and the sonar viewport all divide by
`zoom`. A new screen-space feature must use these helpers or it breaks the
moment someone zooms.

**Audio prefers the shipped pack.** `Audio_.loadPack()` fetches `audio/mp3/*`
and each cue tries `playBuf(name)` before its synth body. Never call `playBuf`
without a synth fallback: `file://` and offline pages have no buffers and the
cue would silently vanish. `?nopause` in the URL disables auto-pause-on-hide
(for capture tools and automated tests whose embedded pages always report
`visibilityState === "hidden"`).

**`localStorage` keys** are `ventfall.settings` (volume/mute),
`ventfall.difficulty`, and `ventfall.stats` (career record). All reads go
through `store.read` with fallbacks — private-mode browsers throw on access.

## Balance dials

- `DIFFS` — per-difficulty `wave0` / `waveInc` / `waveCap` / `first` (grace
  period before the first push) / `aiOre` (flat AI trickle per 0.6s tick,
  Black Smoker only)
- inter-wave cooldown: `G.firstPush = G.t + 26` after each push
- `DEFS[x].cost` / `.train` — economy pacing
- crew cap is `gives: 8` per Habitat, hard cap 120

## Campaign invariants

- **Mission scripting lives in `CHAPTERS`** — objectives, timed/conditional
  events, scripted spawns, zone definitions, and function-valued briefs. Saves
  never serialise closures: they persist objective progress and per-event
  `fired` flags by index and rehydrate from `CHAPTERS` by chapter id.
- **`protect` objectives are satisfied by not failing.** They never set
  `done`; the all-done check skips them. Treating them as blocking makes any
  chapter with one unwinnable.
- **Objectives don't evaluate while a Scene is open.** A conditional event can
  open a decision scene the same tick the objectives would complete; deferring
  the check keeps a debrief from stomping an open choice.
- **`ownFlags` per chapter** list the decision flags that chapter can set;
  starting (or replaying) the chapter deletes them so choices can be remade.
  Unity/dominion points intentionally accumulate across replays.
- **Three teams.** `friendly(a,b)` treats PLAYER+ALLY as one side; any new
  targeting, splash, healing, or vision code must use it rather than `!==`.
- **URL flags**: `?nopause` disables auto-pause-on-hide (capture tools);
  `?debug` exposes `window.__V` (win/lose/start/spawn/save/load/ending) for
  automated testing.

## Known rough edges

- Crew capacity is tight early; a second Habitat is close to mandatory.
- Pathing is local steering with a stuck-detector, not a planner. Units handle
  concave terrain but can take scenic routes on long diagonals.
- Tier II sprites have not been eyeballed at scale in a large mixed squad.
- The AI ignores fog (full-map vision) and does not use waypoints, rally
  points, or attack-move — it issues plain attack orders at the nearest
  player structure.
