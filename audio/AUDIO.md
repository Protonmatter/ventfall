# VENTFALL — Sound Pack

32 original sound effects for real-time strategy games, in WAV (44.1 kHz /
16-bit mono) and MP3 (192 kbps). Every file is synthesized from oscillators and
filtered noise by `synth.py`, which is included. No sampled, recorded, or
third-party audio was used at any stage.

## Licence

Public domain (CC0 1.0). Commercial use, no attribution, no permission needed.

## Contents

| File | Length | Use |
|---|---|---|
| `ui_select` | 0.09 s | Unit selection blip |
| `ui_click` | 0.03 s | Generic button click |
| `ui_denied` | 0.14 s | Invalid / unaffordable action |
| `order_move` | 0.08 s | Move order acknowledged |
| `order_attack` | 0.16 s | Attack order acknowledged |
| `build_place` | 0.22 s | Structure footprint placed |
| `build_complete` | 0.62 s | Construction finished |
| `weapon_light` | 0.09 s | Light rapid weapon |
| `weapon_heavy` | 0.20 s | Heavy turret weapon |
| `impact` | 0.07 s | Projectile impact |
| `explosion_small` | 0.53 s | Unit destroyed |
| `explosion_large` | 1.06 s | Structure destroyed |
| `ore_deposit` | 0.07 s | Resource delivered |
| `sonar_ping` | 1.06 s | Minimap sonar sweep |
| `alarm_underattack` | 0.44 s | Base under attack |
| `sting_victory` | 2.01 s | Victory sting |
| `sting_defeat` | 2.51 s | Defeat sting |
| `ambient_loop` | 7.50 s | Seamless 7.5 s underwater bed |
| `alert_resources` | 0.26 s | Insufficient resources |
| `alert_capacity` | 0.42 s | Crew capacity reached |
| `alert_construction` | 0.46 s | Construction complete |
| `alert_unit_ready` | 0.25 s | Unit ready |
| `alert_research` | 0.30 s | Upgrade complete |
| `alert_lost` | 0.34 s | Structure lost |
| `ack_yes` | 0.09 s | Generic affirmative |
| `ack_move` | 0.14 s | Move order acknowledged |
| `ack_attack` | 0.21 s | Attack order acknowledged |
| `ack_build` | 0.11 s | Build order acknowledged |
| `weapon_missile` | 0.34 s | Missile / launcher |
| `weapon_energy` | 0.22 s | Energy weapon |
| `shield_hit` | 0.20 s | Shield / armour deflect |
| `repair_loop` | 1.20 s | Loopable repair / weld bed |

`ambient_loop` and `repair_loop` are crossfaded end-to-head and repeat with no
audible seam.

## Advisor cues

The `alert_*` and `ack_*` families are run through a narrowband filter
(roughly 500–2800 Hz) with light bit-crushing — that squeezed-comms character is
what reads as "late-90s RTS advisor" far more than the pitches do. `comms()` in
`synth.py` exposes both parameters if you want it drier or dirtier.

## Using them

Short cues fire many times per second, so pool them and throttle repeats:

```js
const pool = (src, n = 6) => {
  const v = Array.from({length: n}, () => new Audio(src));
  let i = 0, last = 0;
  return (gain = 1) => {
    if (performance.now() - last < 50) return;
    last = performance.now();
    const a = v[i = (i + 1) % n];
    a.currentTime = 0; a.volume = gain; a.play().catch(() => {});
  };
};

const sfx = {
  select: pool('mp3/ui_select.mp3'),
  shoot:  pool('mp3/weapon_light.mp3', 8),
  alert:  pool('mp3/alert_resources.mp3', 2)
};
```

Advisor alerts should be throttled far harder than combat sounds — one every
~4 s per category, or they stack into noise.

Browsers block audio until user interaction, so start from a click or key press.

## Regenerating

```bash
pip install numpy scipy      # ffmpeg only needed for MP3s
python3 synth.py             # PACK_OUT=/some/dir to change output
```

Pitches, envelopes and filter bands are plain parameters in the `s_*` functions.
The seed is fixed, so output is reproducible.
