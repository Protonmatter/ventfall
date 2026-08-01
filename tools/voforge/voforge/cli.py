"""voforge command-line interface."""
import argparse, asyncio, json, pathlib, sys

from .backends import make_backend
from .core import ConsentError, check_consent, load_lines, plan, render, validate
from .tones import TONES


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="voforge",
        description="Batch neural voice-over generator with tones and emotional styles.")
    ap.add_argument("--lines", type=pathlib.Path, help="JSON array or CSV of {who,text,...}")
    ap.add_argument("--cast", type=pathlib.Path, help="cast sheet JSON")
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("vo"))
    ap.add_argument("--name", choices=("hash", "id", "seq"), default="hash")
    ap.add_argument("--backend", choices=("edge", "azure", "xtts", "elevenlabs"),
                    default="edge",
                    help="edge: free stock voices, tones · azure: true emotional "
                         "styles · xtts: local voice cloning from a reference "
                         "recording · elevenlabs: hosted cloning/synthesis")
    ap.add_argument("--extract-ref", nargs=2, metavar=("MEDIA", "OUT_WAV"),
                    help="pull a cloning reference out of any audio/video file")
    ap.add_argument("--record-ref", metavar="OUT_WAV",
                    help="record a cloning reference from the microphone")
    ap.add_argument("--start", type=float, help="--extract-ref start seconds")
    ap.add_argument("--duration", type=float, default=20,
                    help="--extract-ref / --record-ref length in seconds (default 20)")
    ap.add_argument("--device", help="--record-ref input device name")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--force", action="store_true", help="re-render existing files")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would render (voice/tone/style per line), touch nothing")
    ap.add_argument("--list-voices", nargs="?", const="", metavar="FILTER",
                    help="list available voices (optionally filtered)")
    ap.add_argument("--list-tones", action="store_true", help="list built-in tone presets")
    ap.add_argument("--audition", nargs=2, metavar=("VOICE", "TEXT"),
                    help="render one sample to <out>/audition.mp3 (honors --tone)")
    ap.add_argument("--tone", help="tone preset for --audition")
    a = ap.parse_args(argv)

    if a.extract_ref:
        from .refs import extract_ref
        src, out = a.extract_ref
        p = extract_ref(src, out, start=a.start, duration=a.duration)
        print(f"wrote {p} — use it as a speaker's \"ref\" with --backend xtts")
        return 0

    if a.record_ref:
        from .refs import record_ref
        p = record_ref(a.record_ref, seconds=int(a.duration), device=a.device)
        print(f"wrote {p} — use it as a speaker's \"ref\" with --backend xtts")
        return 0

    if a.list_tones:
        for name, delta in TONES.items():
            print(f"{name:9} {delta or '(base voice)'}")
        return 0

    if a.list_voices is not None:
        import edge_tts
        voices = asyncio.run(edge_tts.list_voices())
        for v in voices:
            if a.list_voices.lower() in v["ShortName"].lower():
                tags = ", ".join(v.get("VoiceTag", {}).get("VoicePersonalities", []))
                print(f'{v["ShortName"]:34} {v["Gender"]:7} {tags}')
        return 0

    if a.audition:
        voice, text = a.audition
        backend = make_backend(a.backend)
        line = {"who": "_audition", "text": text}
        if a.tone:
            line["tone"] = a.tone
        cast = {"_audition": {"voice": voice}}
        a.out.mkdir(parents=True, exist_ok=True)
        from .tones import resolve
        v, p, s, d = resolve(line, cast["_audition"], cast, backend.styles)
        asyncio.run(backend.synth(text, v, p, s, d, a.out / "audition.mp3"))
        print(f"wrote {a.out/'audition.mp3'}  prosody={p}")
        return 0

    if not a.lines or not a.cast:
        ap.error("--lines and --cast are required (or use --list-voices / "
                 "--list-tones / --audition / --extract-ref / --record-ref)")

    try:
        lines = load_lines(a.lines)
        cast = json.loads(a.cast.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"voforge: {e}", file=sys.stderr)
        return 2

    problems = validate(lines, cast)
    if problems:
        print("voforge: input problems:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 2

    cloning = a.backend in ("xtts", "elevenlabs")
    ext = {"xtts": "wav"}.get(a.backend, "mp3")
    # refuse unconsented clones before loading an expensive model / touching an API
    unconsented = check_consent(cast, cloning)
    if unconsented:
        print("voforge: cloned voices require explicit permission — add "
              '"consent": true to these cast entries once you have the right '
              f"to use them: {', '.join(unconsented)}", file=sys.stderr)
        return 2
    if a.dry_run:
        rows = plan(lines, cast, a.out, a.name,
                    backend_styles=(a.backend == "azure"), cloning=cloning, ext=ext)
        todo = 0
        for r in rows:
            state = "error " if r.get("error") else ("exists" if r["exists"] else "RENDER")
            if state == "RENDER":
                todo += 1
            extra = r.get("error") or f'{r.get("voice","")}' \
                + (f' style={r["style"]}' if r.get("style") else "") \
                + (f' {r["prosody"]}' if r.get("prosody") else "")
            print(f"{state}  {r['name']}  {r['who']:10} {extra}")
        print(f"-- {todo} to render, {sum(1 for r in rows if r['exists'])} existing, "
              f"{sum(1 for r in rows if r.get('error'))} errors")
        return 0

    backend = make_backend(a.backend)
    try:
        counts = asyncio.run(render(lines, cast, a.out, a.name, a.jobs, a.force,
                                    backend=backend))
    except ConsentError as e:
        print(f"voforge: {e}", file=sys.stderr)
        return 2
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
