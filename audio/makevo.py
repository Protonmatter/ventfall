#!/usr/bin/env python3
"""Generate VENTFALL's campaign voice-over pack.

This is a thin project-specific EXTRACTOR: it pulls every dialog line out of
index.html and hands it to the reusable generator in tools/voforge/ along with
VENTFALL's cast sheet. All the TTS machinery lives in voforge, so it is shared
with any other project; this file only knows how VENTFALL stores its dialogue.

Usage:  python audio/makevo.py            (from the repo root)
Needs:  pip install edge-tts, network access (build-time only).

If you edit or add any `text:` in index.html, rerun this. Output naming (djb2
of "who|text") matches voHash() in the game, so unchanged lines are kept and
only new/edited lines render.
"""
import asyncio, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "voforge"))
import voforge  # noqa: E402

CAST = {
    "_default": {"voice": "en-GB-ThomasNeural", "rate": "-6%"},
    # the Choir's glyphs are typography, not phonetics
    "_subs":  [["⋮", ","], ["[▸·—…]", ", "]],
    "voss":   {"voice": "en-US-AriaNeural"},
    "okafor": {"voice": "en-NG-AbeoNeural"},
    "krane":  {"voice": "en-GB-RyanNeural",  "rate": "+6%"},
    "sable":  {"voice": "en-SG-LunaNeural",  "rate": "+4%"},
    "reyne":  {"voice": "en-AU-NatashaNeural"},
    "choir":  {"voice": "en-US-GuyNeural",   "rate": "-30%", "pitch": "-35Hz"},
    "narr":   {"voice": "en-GB-ThomasNeural", "rate": "-6%"},
}

def extract(src: str):
    # every shot is a literal {who:"x"[, title:"…"], text:"…"}
    pat = re.compile(r'\{who:"(\w+)",\s*(?:title:"(?:[^"\\]|\\.)*",\s*)?text:"((?:[^"\\]|\\.)*)"')
    out = []
    for who, raw in pat.findall(src):
        text = raw.replace('\\"', '"').replace("\\n", " ")
        out.append({"who": who, "text": text})
    return out

def main():
    lines = extract((ROOT / "index.html").read_text(encoding="utf-8"))
    asyncio.run(voforge.render(lines, CAST, ROOT / "audio" / "vo", name_mode="hash"))

if __name__ == "__main__":
    main()
