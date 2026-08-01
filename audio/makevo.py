#!/usr/bin/env python3
"""Generate the campaign voice-over pack.

Extracts every dialog shot from index.html, casts each character to a
Microsoft neural voice via edge-tts, and renders one mp3 per unique line into
audio/vo/<hash>.mp3. The filename hash (djb2 over UTF-8 of "who|text") matches
the lookup the game computes at runtime, so no manifest is needed: a missing
file simply falls back to live browser speech synthesis.

Usage:  python audio/makevo.py            (from the repo root)
Needs:  pip install edge-tts, network access (build-time only).
"""
import asyncio, pathlib, re, sys

import edge_tts

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "audio" / "vo"

CAST = {
    "voss":   {"voice": "en-US-AriaNeural"},
    "okafor": {"voice": "en-NG-AbeoNeural"},
    "krane":  {"voice": "en-GB-RyanNeural",  "rate": "+6%"},
    "sable":  {"voice": "en-SG-LunaNeural",  "rate": "+4%"},
    "reyne":  {"voice": "en-AU-NatashaNeural"},
    "choir":  {"voice": "en-US-GuyNeural",   "rate": "-30%", "pitch": "-35Hz"},
    "narr":   {"voice": "en-GB-ThomasNeural", "rate": "-6%"},
}

def djb2(s: str) -> str:
    h = 5381
    for b in s.encode("utf-8"):
        h = ((h * 33) ^ b) & 0xFFFFFFFF
    return format(h, "08x")

def spoken(text: str) -> str:
    # the Choir's glyphs are typography, not phonetics; same cleanup as the game
    t = text.replace("⋮", ",")
    t = re.sub(r"[▸·—…]", ", ", t)
    return re.sub(r"\s+", " ", t).strip()

def extract(src: str):
    # every shot is a literal {who:"x"[, title:"…"], text:"…"}
    pat = re.compile(r'\{who:"(\w+)",\s*(?:title:"(?:[^"\\]|\\.)*",\s*)?text:"((?:[^"\\]|\\.)*)"')
    seen = {}
    for who, raw in pat.findall(src):
        text = raw.replace('\\"', '"').replace("\\n", " ")
        key = djb2(who + "|" + text)
        seen.setdefault(key, (who, text))
    return seen

async def render(key, who, text, sem):
    path = OUT / f"{key}.mp3"
    if path.exists():
        return "kept"
    cast = CAST.get(who, CAST["narr"])
    kwargs = {k: v for k, v in cast.items() if k != "voice"}
    async with sem:
        for attempt in range(3):
            try:
                tts = edge_tts.Communicate(spoken(text), cast["voice"], **kwargs)
                await tts.save(str(path))
                return "made"
            except Exception as e:
                if attempt == 2:
                    print(f"  FAILED {who} {key}: {e}", file=sys.stderr)
                    return "failed"
                await asyncio.sleep(2 * (attempt + 1))

async def main():
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    lines = extract(src)
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{len(lines)} unique lines")
    sem = asyncio.Semaphore(4)
    results = await asyncio.gather(*(render(k, w, t, sem) for k, (w, t) in lines.items()))
    made = results.count("made"); kept = results.count("kept"); failed = results.count("failed")
    total = sum(f.stat().st_size for f in OUT.glob("*.mp3"))
    print(f"made {made}, kept {kept}, failed {failed}; pack {total/1e6:.1f} MB")

if __name__ == "__main__":
    asyncio.run(main())
