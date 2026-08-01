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
import asyncio, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "voforge"))
import voforge  # noqa: E402

# The cast lives in data (audio/vo-cast.json) in voforge's own format, so the
# same sheet can drive the standalone tool directly:
#   python tools/voforge/voforge.py --lines <extracted.json> --cast audio/vo-cast.json
CAST = json.loads((ROOT / "audio" / "vo-cast.json").read_text(encoding="utf-8"))

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
