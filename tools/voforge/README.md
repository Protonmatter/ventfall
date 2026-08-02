# voforge

Batch neural voice-over generator with **tones, emotional styles, and voice
cloning**. Feed it a list of dialog lines and a cast sheet; it renders one
audio file per unique line. Project-agnostic, pip-installable, CI-friendly,
with drop-in runtime players for web, Unity, and Godot.

Network is needed at **build time only** — the rendered pack ships with your
project and plays offline. This is the generator behind VENTFALL's
fully-voiced campaign (139 lines, seven actors).

> **Canonical repo:** [github.com/Protonmatter/voforge](https://github.com/Protonmatter/voforge).
> This directory is a vendored copy kept in the VENTFALL repo so the voice
> pack can be regenerated in place; upstream fixes land in the standalone repo
> first.

```bash
pip install ./tools/voforge          # or: pip install git+https://github.com/Protonmatter/ventfall#subdirectory=tools/voforge
voforge --lines lines.json --cast cast.json --out vo/
```

## Choosing a backend for naturalness

Naturalness, intonation, and accuracy are properties of the **model**, not a
knob — so pick the backend that matches how natural you need it:

| Backend | Naturalness | Emotion path | Cost / setup |
|---|---|---|---|
| `edge` (default) | good neutral neural voices | **tones** (prosody deltas — an *approximation* of emotion, not acted) | free, no key |
| `azure` | good, with acted emotion | **styles** — true `express-as` (angry/sad/whispering...) with natural intonation | Azure Speech key |
| `xtts` | **very natural, clones a real performance** | inherits the reference recording's own prosody & intonation | free, local, one-time model download |
| `elevenlabs` | **most natural** | contextual, per-line | paid API key |

Honest guidance: prosody **tones never produce natural acted emotion** — they
pitch/speed-shift a neutral read. For genuinely natural emotional delivery use
`azure` (acted styles) or, best of all, **clone a reference performance with
`xtts`/`elevenlabs`** — the model reproduces the intonation of the sample you
give it.

## Expression: tones vs styles

Two tiers, one schema — write your dialogue once, render on any backend:

**Tones** are prosody presets (rate/pitch/volume deltas layered on the
speaker's base voice). They work everywhere, including the free edge backend.
Built-ins: `grim, urgent, soft, whisper, bright, cold, awe, fear, weary,
neutral` (`voforge --list-tones`), and projects can add their own via
`_tones` in the cast sheet.

**Styles** are true acted emotions (`angry`, `sad`, `whispering`,
`terrified`, ...) rendered by Microsoft's express-as engine — these need the
`azure` backend (a real Azure Speech key). On backends without style support
each style **degrades automatically to the nearest tone**, so the same lines
file renders anywhere, just less theatrically.

```json
[
  {"who": "mentor",  "text": "Careful, kid.", "tone": "grim"},
  {"who": "villain", "text": "That was your first mistake.",
   "style": "angry", "styledegree": "1.4"},
  {"who": "mentor",  "text": "Run. RUN!", "tone": "urgent", "rate": "+25%"}
]
```

Resolution order: speaker base → tone preset → per-line `rate`/`pitch`/
`volume` overrides. `voforge --dry-run` shows exactly how every line resolves
before you spend a single network call.

## Voice cloning from a microphone, audio, or video

Clone any voice you have the right to use — feed the model a short reference
recording and it reproduces that person's timbre **and their natural
prosody/intonation**.

**1. Make a reference clip** (6–30 s of one clear speaker, no music):

```bash
voforge --record-ref mara.wav --duration 20            # from the microphone
voforge --extract-ref interview.mp4 mara.wav --start 12 --duration 20   # from video
voforge --extract-ref memo.m4a mara.wav                # from an audio file
```

(`--extract-ref`/`--record-ref` use ffmpeg — found on PATH or via
`pip install imageio-ffmpeg`.)

**2. Point a cast entry at it** and declare consent:

```json
{ "mara": { "ref": "mara.wav", "consent": true } }
```

**3. Render with a cloning backend:**

```bash
voforge --lines lines.json --cast cast.json --backend xtts --out vo/
```

Cloned lines are written as `.wav`; the runtime players take an `ext: "wav"`
option to match. **Consent gate:** voforge refuses to synthesize from a `ref`
or `voice_id` unless that cast entry has `"consent": true`. Only clone voices
you own or have explicit permission to use.

### Setting up the local cloning engine (xtts)

XTTS needs PyTorch, which currently ships wheels only for **Python 3.12**
(not 3.13/3.14). Provision a dedicated env — verified working, including on
Windows on Arm / Snapdragon:

```bash
# 1. a Python 3.12 environment (uv is the easy way on any OS/arch):
uv venv voforge-clone --python 3.12
# 2. native torch from the PyTorch CPU index (win-arm64 or win-amd64 wheels;
#    on Snapdragon the amd64 wheels also run fine under emulation):
uv pip install torch==2.7.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cpu
# 3. voforge + the cloning stack (pins in requirements-clone.txt):
uv pip install ./tools/voforge -r ./tools/voforge/requirements-clone.txt
```

First render downloads ~1.8 GB of XTTS weights, then runs fully offline.

## Backends

| Backend | Cost | Expression | Setup |
|---|---|---|---|
| `edge` (default) | free, no key | tones (prosody) | `pip install edge-tts` |
| `azure` | Azure Speech pricing | tones + true styles + beat breaks (`…`/`—` → 350ms pauses) | `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` |
| `xtts` | free, local | clones a reference recording (natural prosody) | Python 3.12 + `requirements-clone.txt` |
| `elevenlabs` | paid API | hosted synthesis / cloning by `voice_id` | `ELEVENLABS_API_KEY` |

The azure and elevenlabs backends are implemented to their documented REST
contracts but haven't been exercised against live subscriptions from this
repo; treat the first run as a shakedown. The `edge` and `xtts` backends are
verified end-to-end (xtts on Windows-on-Arm, x86-64-emulated).

## Inputs

**lines** — JSON array (or CSV with a header) of:

| key | | |
|---|---|---|
| `who` | required | speaker, must match the cast sheet (or `_default` exists) |
| `text` | required | the line |
| `id` | optional | stable name for `--name id` |
| `tone` | optional | tone preset name |
| `style`, `styledegree` | optional | acted emotion (azure; degrades to tone elsewhere) |
| `rate`, `pitch`, `volume` | optional | explicit prosody overrides (`"+6%"`, `"-35Hz"`) |

**cast** — voice per speaker plus specials:

```json
{
  "_default": {"voice": "en-GB-ThomasNeural"},
  "_subs":    [["⋮", ","], ["[▸·—…]", ", "]],
  "_tones":   {"spooked": {"rate": "+10%", "pitch": "+9Hz", "volume": "-15%"}},
  "hero":     {"voice": "en-US-AriaNeural"},
  "villain":  {"voice": "en-GB-RyanNeural", "rate": "+6%", "style": "unfriendly"}
}
```

`_subs` is regex `[pattern, replacement]` text cleanup (typography →
phonetics). Speakers can carry a default `style`/`tone` of their own.

## Output naming and runtime lookup

Default is **content-addressed**: `<djb2(who|text)>.mp3`. Your app computes
the same hash at runtime and requests the file — no manifest, and a 404 is
the fallback signal (e.g. to live `speechSynthesis`). `--name id` and
`--name seq` exist for stable/manual naming.

Hash: djb2, `h = (h*33 XOR byte) mod 2^32`, seed 5381, over UTF-8 of
`"who|text"`, hex-encoded to 8 chars.

## Runtime players (`runtime/`)

Matching consumers so projects don't reimplement the hash:

- **`voforge.js`** — browser ES module: `VoPlayer` with WebAudio, caching,
  `preload`, cancel-on-advance, and a fallback hook. Tested.
- **`VoForge.cs`** — Unity reference implementation (hash + streaming play).
- **`voforge.gd`** — Godot 4 reference implementation.

## CLI

```
voforge --lines FILE --cast FILE [--out DIR] [--name hash|id|seq]
        [--backend edge|azure|xtts|elevenlabs] [--jobs N] [--force] [--dry-run]
voforge --list-voices [FILTER]
voforge --list-tones
voforge --audition VOICE "TEXT" [--tone TONE] [--out DIR]
voforge --record-ref OUT.wav [--duration S] [--device NAME]
voforge --extract-ref MEDIA OUT.wav [--start S] [--duration S]
```

Build-ready behavior: inputs are validated up front with every problem
listed; exit code `0` on success, `1` if any line failed to render, `2` on
bad input — safe to gate CI on. Rendering is incremental (existing files are
kept; `--force` re-renders).

## Library

```python
import asyncio, voforge
asyncio.run(voforge.render(lines, cast, "vo/"))          # edge backend
voforge.plan(lines, cast, "vo/")                          # dry-run rows
voforge.render(..., backend=voforge.make_backend("azure"))
```

## Tests

```bash
python -m unittest discover -s tests    # fully offline (FakeBackend)
```

## License

MIT, same as the repository. Voice audio is generated through Microsoft
text-to-speech services — review the service terms for your use case.
