#!/usr/bin/env python3
"""voforge — batch neural voice-over generator.

Turns a list of dialog lines plus a cast sheet into one audio file per line,
using Microsoft's neural voices via edge-tts. Project-agnostic: nothing here
knows about any particular game or app. Network is needed at build time only —
the rendered files ship with your project and play offline.

Inputs
------
lines file (JSON):   [ {"who": "voss", "text": "Hello."},
                       {"id": "intro_01", "who": "narr", "text": "..."} , ...]
         or (CSV):    who,text[,id] header row + rows

cast file (JSON):    { "_default": {"voice": "en-GB-ThomasNeural"},
                       "_subs":    [["⋮", ","], ["[▸·—…]", ", "]],
                       "voss":     {"voice": "en-US-AriaNeural"},
                       "krane":    {"voice": "en-GB-RyanNeural", "rate": "+6%"},
                       "choir":    {"voice": "en-US-GuyNeural",
                                    "rate": "-30%", "pitch": "-35Hz"} }
    Per-speaker keys: voice (required), rate, pitch, volume — any prosody
    option edge_tts.Communicate accepts. "_subs" is a list of [regex, repl]
    applied to text before synthesis (typography → phonetics). "_default"
    covers speakers missing from the sheet.

Output naming (--name)
----------------------
hash  (default)  <djb2(who|text)>.mp3 — content-addressed, no manifest needed.
                 Look lines up at runtime with the same hash; a missing file
                 is your signal to fall back (e.g. to live speechSynthesis).
id               <line id>.mp3 — requires an id on every line.
seq              0001.mp3, 0002.mp3, ...

The hash is djb2 (h = (h*33 XOR byte) mod 2^32, seed 5381) over the UTF-8
bytes of "who|text". Reference JavaScript implementation:

    function voHash(s){
      const b=new TextEncoder().encode(s);
      let h=5381;
      for(let i=0;i<b.length;i++) h=(Math.imul(h,33)^b[i])>>>0;
      return h.toString(16).padStart(8,"0");
    }

Usage
-----
    pip install edge-tts
    python voforge.py --lines lines.json --cast cast.json --out vo/
    python voforge.py --list-voices en-GB
    python voforge.py --audition en-NG-AbeoNeural "Pressure's green." --out .
"""
import argparse, asyncio, csv, json, pathlib, re, sys

try:
    import edge_tts
except ImportError:
    edge_tts = None


def djb2(s: str) -> str:
    h = 5381
    for b in s.encode("utf-8"):
        h = ((h * 33) ^ b) & 0xFFFFFFFF
    return format(h, "08x")


def clean(text: str, subs) -> str:
    for pat, repl in subs or []:
        text = re.sub(pat, repl, text)
    return re.sub(r"\s+", " ", text).strip()


def load_lines(path: pathlib.Path):
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        return [{"who": r["who"], "text": r["text"], "id": r.get("id")} for r in rows]
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("lines file must be a JSON array")
    return data


def out_name(line, mode, seq):
    if mode == "id":
        if not line.get("id"):
            raise SystemExit(f"--name id requires an id on every line: {line}")
        return line["id"]
    if mode == "seq":
        return f"{seq:04d}"
    return djb2(line["who"] + "|" + line["text"])


async def _render_one(line, name, cast, out_dir, force, fmt, sem, log):
    path = out_dir / f"{name}.{fmt}"
    if path.exists() and not force:
        return "kept"
    speaker = cast.get(line["who"]) or cast.get("_default")
    if not speaker or "voice" not in speaker:
        log(f"  no voice for speaker '{line['who']}' and no _default — skipped")
        return "failed"
    kwargs = {k: v for k, v in speaker.items() if k in ("rate", "pitch", "volume")}
    text = clean(line["text"], cast.get("_subs"))
    if not text:
        return "kept"
    async with sem:
        for attempt in range(3):
            try:
                await edge_tts.Communicate(text, speaker["voice"], **kwargs).save(str(path))
                return "made"
            except Exception as e:
                if attempt == 2:
                    log(f"  FAILED {line['who']} {name}: {e}")
                    return "failed"
                await asyncio.sleep(2 * (attempt + 1))


async def render(lines, cast, out_dir, name_mode="hash", jobs=4, force=False,
                 fmt="mp3", log=print):
    """Render every unique line. Returns dict of result counts."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    unique, seen = [], set()
    for i, line in enumerate(lines):
        name = out_name(line, name_mode, i + 1)
        if name in seen:
            continue
        seen.add(name)
        unique.append((line, name))
    sem = asyncio.Semaphore(jobs)
    results = await asyncio.gather(
        *(_render_one(l, n, cast, out_dir, force, fmt, sem, log) for l, n in unique))
    counts = {r: results.count(r) for r in ("made", "kept", "failed")}
    size = sum(f.stat().st_size for f in out_dir.glob(f"*.{fmt}"))
    log(f"{len(unique)} unique lines — made {counts['made']}, kept {counts['kept']}, "
        f"failed {counts['failed']}; pack {size/1e6:.1f} MB")
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description="Batch neural voice-over generator (edge-tts).")
    ap.add_argument("--lines", type=pathlib.Path, help="JSON array or CSV of {who,text[,id]}")
    ap.add_argument("--cast", type=pathlib.Path, help="cast sheet JSON (see module docstring)")
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("vo"))
    ap.add_argument("--name", choices=("hash", "id", "seq"), default="hash")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--force", action="store_true", help="re-render existing files")
    ap.add_argument("--list-voices", nargs="?", const="", metavar="FILTER",
                    help="list available neural voices (optionally filtered)")
    ap.add_argument("--audition", nargs=2, metavar=("VOICE", "TEXT"),
                    help="render one sample line to <out>/audition.mp3")
    a = ap.parse_args(argv)

    if edge_tts is None:
        raise SystemExit("pip install edge-tts")

    if a.list_voices is not None:
        voices = asyncio.run(edge_tts.list_voices())
        for v in voices:
            if a.list_voices.lower() in v["ShortName"].lower():
                print(f'{v["ShortName"]:34} {v["Gender"]:7} {", ".join(v.get("VoiceTag",{}).get("VoicePersonalities",[]))}')
        return

    if a.audition:
        voice, text = a.audition
        a.out.mkdir(parents=True, exist_ok=True)
        path = a.out / "audition.mp3"
        asyncio.run(edge_tts.Communicate(text, voice).save(str(path)))
        print(f"wrote {path}")
        return

    if not a.lines or not a.cast:
        ap.error("--lines and --cast are required (or use --list-voices / --audition)")
    lines = load_lines(a.lines)
    cast = json.loads(a.cast.read_text(encoding="utf-8"))
    asyncio.run(render(lines, cast, a.out, a.name, a.jobs, a.force))


if __name__ == "__main__":
    main()
