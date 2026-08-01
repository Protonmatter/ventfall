# voforge

Batch neural voice-over generator. Feed it a list of dialog lines and a cast
sheet; it renders one mp3 per unique line using Microsoft's neural voices
(via [edge-tts](https://pypi.org/project/edge-tts/)). Project-agnostic —
drop this folder into any game or app. Network is needed at **build time
only**; the rendered files ship with your project and play offline.

This is the generator behind VENTFALL's fully-voiced campaign (139 lines,
seven actors); `audio/makevo.py` in the repo root is a working example of a
project extractor driving it.

## Quick start

```bash
pip install edge-tts

# what voices exist?
python voforge.py --list-voices en-GB

# hear one before casting it
python voforge.py --audition en-NG-AbeoNeural "Pressure's green, Commander." --out .

# render a project
python voforge.py --lines lines.json --cast cast.json --out vo/
```

## Inputs

**lines.json** — an array of `{who, text}` (optional `id`), or a CSV with a
`who,text[,id]` header:

```json
[
  {"who": "voss",  "text": "Four drones and a rig older than I am."},
  {"who": "krane", "text": "The quota stands."}
]
```

**cast.json** — voice per speaker, plus optional prosody and text substitutions:

```json
{
  "_default": {"voice": "en-GB-ThomasNeural"},
  "_subs":    [["⋮", ","], ["[▸·—…]", ", "]],
  "voss":     {"voice": "en-US-AriaNeural"},
  "krane":    {"voice": "en-GB-RyanNeural", "rate": "+6%"},
  "choir":    {"voice": "en-US-GuyNeural", "rate": "-30%", "pitch": "-35Hz"}
}
```

`rate`, `pitch`, `volume` take edge-tts prosody strings (`"+6%"`, `"-35Hz"`).
`_subs` is a list of `[regex, replacement]` applied before synthesis — use it
to turn typography (glyphs, em dashes) into phonetics. `_default` covers any
speaker missing from the sheet.

## Output naming and runtime lookup

By default files are **content-addressed**: `<djb2(who|text)>.mp3`. Your app
computes the same hash at runtime and just requests the file — no manifest,
and a 404 is your fallback signal (e.g. to live `speechSynthesis`).

The hash is djb2 (`h = (h*33 XOR byte) mod 2^32`, seed 5381) over the UTF-8
bytes of `"who|text"`. Reference JavaScript:

```js
function voHash(s){
  const b=new TextEncoder().encode(s);
  let h=5381;
  for(let i=0;i<b.length;i++) h=(Math.imul(h,33)^b[i])>>>0;
  return h.toString(16).padStart(8,"0");
}
// ...
new Audio("vo/"+voHash(who+"|"+text)+".mp3").play();
```

Prefer stable names? `--name id` uses each line's `id` field; `--name seq`
numbers them.

## Flags

| Flag | Meaning |
|---|---|
| `--lines FILE` | JSON array or CSV of lines |
| `--cast FILE` | cast sheet JSON |
| `--out DIR` | output directory (default `vo/`) |
| `--name hash\|id\|seq` | file naming scheme (default `hash`) |
| `--jobs N` | parallel renders (default 4) |
| `--force` | re-render lines whose files already exist |
| `--list-voices [FILTER]` | print available voices |
| `--audition VOICE "TEXT"` | render one sample to `<out>/audition.mp3` |

Incremental by design: existing files are kept, so re-running after adding
dialog only renders the new lines.

## Using it as a library

```python
import voforge, asyncio
asyncio.run(voforge.render(lines, cast, "vo/", name_mode="hash"))
```

## License

MIT, same as the repository. Voice audio is generated through Microsoft's
Edge text-to-speech service — review the service's terms for your use case.
