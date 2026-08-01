# VENTFALL

A real-time strategy game that runs in a browser. One HTML file, no build step, no
dependencies, no network calls. All graphics are drawn procedurally to canvas and
all in-game audio is synthesized at runtime with the Web Audio API.

Two mining rigs sit on a hydrothermal field two miles down. Only one is there at
shift end.

## Play

Open `index.html` in any modern browser. That's the whole install.

Or serve it:

```bash
python3 -m http.server 8000
# http://localhost:8000
```

## Controls

| Input | Action |
|---|---|
| Drag | Box-select units |
| Click | Select one unit or structure |
| Double-click | Select all of that type on screen |
| Right click | Move · attack · mine · build (context-sensitive) |
| `W` `A` `S` `D` | Pan the field (screen edges also pan) |
| `Q` | Attack-move |
| `E` | Stop |
| `Ctrl`+`1`–`9` | Assign control group |
| `1`–`9` | Recall control group |
| `Space` | Snap camera to your Rig Core |
| `Esc` | Cancel pending order |
| `V` `B` `N` `K` | Build Habitat · Foundry · Turret · Deepworks |
| `P` `O` `U` | Research Plating · Optics · Servos |

## Tech tree

```
Rig Core ──> Foundry ──> Deepworks
   │            │             │
 Drone      Lancer        Ripper
            Gunner        Mortar
                          Tender
                          + upgrades
```

### Units

| Unit | Cost | Crew | Role |
|---|---|---|---|
| Drone | 50 | 1 | Harvests ore, constructs buildings |
| Lancer | 75 | 2 | Cheap melee line |
| Gunner | 110 | 2 | Ranged support, 135 range |
| **Ripper** | 150 | 3 | Shock brawler. **Armor 3** subtracts from every hit, so it beats rapid small-arms fire and loses to splash |
| **Mortar** | 185 | 3 | Siege. 230 range, 46px splash, but a **70px minimum range** — it cannot defend itself and needs a screen |
| **Tender** | 120 | 2 | Repairs the most-wounded friendly in range; follows the army when idle |

### Structures

| Structure | Cost | Notes |
|---|---|---|
| Rig Core | — | Ore dropoff, trains Drones, +8 crew |
| Habitat | 100 | +8 crew |
| Foundry | 150 | Trains Lancer, Gunner |
| Turret | 125 | Automated defense, 170 range |
| Deepworks | 275 | Requires Foundry. Tier II units + upgrades |

### Upgrades

Team-wide, researched at the Deepworks, one at a time.

| Upgrade | Cost | Effect |
|---|---|---|
| Ablative Plating | 150 | +25% integrity (rescales existing units, preserving damage %) |
| Pressure Optics | 175 | +18% weapon range |
| Servo Drives | 140 | +20% movement speed |

## Opponent

The AI runs a full economy: it expands drone count, builds Habitats against its own
supply cap, adds Foundries, techs to a Deepworks, fields a mixed composition
(Tender first, then Mortars, then Rippers), researches upgrades, and escalates
attack waves on a timer with a cooldown between pushes. It is not scripted —
it plays the same rules you do.

A passive player loses around 2:40. An engaged opening survives well past that.

## Audio

`audio/` holds 32 original sound effects in WAV (44.1 kHz / 16-bit mono) and MP3
(192 kbps), plus `synth.py` that generates them. Every sample is synthesized from
oscillators and filtered noise — no sampled, recorded, or third-party audio at any
stage. See `audio/AUDIO.md`.

The game itself synthesizes its audio live and does not load these files; they are
here for reuse.

## Project layout

```
index.html        the entire game
audio/wav/        32 effects, WAV
audio/mp3/        32 effects, MP3
audio/synth.py    regenerates the pack
audio/AUDIO.md    per-file reference and integration notes
docs/             notes
```

## Licence

MIT for the code, CC0 for the audio. See `LICENSE`.

All content is original. Nothing here is derived from any existing game's assets.
