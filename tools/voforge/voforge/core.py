"""voforge core: line loading, validation, naming, and the render pipeline."""
import asyncio, csv, json, pathlib, re

from .tones import resolve, voice_of

LINE_KEYS = {"who", "text", "id", "tone", "style", "styledegree",
             "rate", "pitch", "volume"}
CAST_KEYS = {"voice", "ref", "voice_id", "consent", "lang", "tone", "style",
             "styledegree", "rate", "pitch", "volume"}


class ConsentError(Exception):
    """A cloned speaker was used without an explicit consent declaration."""


def check_consent(cast, cloning):
    """Cloning a real person's voice requires "consent": true on the speaker.

    voforge will not synthesize from a reference recording otherwise. This is
    a deliberate speed bump, not a security control — but it keeps accidental
    or careless cloning out of a build pipeline.
    """
    if not cloning:
        return []
    bad = []
    for who, spec in cast.items():
        if who.startswith("_") or not isinstance(spec, dict):
            continue
        if (spec.get("ref") or spec.get("voice_id")) and spec.get("consent") is not True:
            bad.append(who)
    return bad


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
        return [{k: v for k, v in r.items() if k in LINE_KEYS and v} for r in rows]
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("lines file must be a JSON array")
    return data


def validate(lines, cast):
    """Fail fast with every problem listed, not just the first."""
    problems = []
    speakers = {k for k in cast if not k.startswith("_")}
    has_default = isinstance(cast.get("_default"), dict) and "voice" in cast["_default"]
    for i, line in enumerate(lines):
        where = f"line {i+1}"
        if not isinstance(line, dict) or "who" not in line or "text" not in line:
            problems.append(f"{where}: needs at least {{who, text}}")
            continue
        if line["who"] not in speakers and not has_default:
            problems.append(f"{where}: speaker {line['who']!r} not in cast and no _default")
        unknown = set(line) - LINE_KEYS
        if unknown:
            problems.append(f"{where}: unknown keys {sorted(unknown)}")
    for who, spec in cast.items():
        if who.startswith("_") and who not in ("_default", "_subs", "_tones"):
            problems.append(f"cast: unknown special key {who!r}")
        if who in ("_subs", "_tones"):
            continue
        if isinstance(spec, dict):
            if not (spec.get("voice") or spec.get("ref") or spec.get("voice_id")):
                problems.append(f"cast: speaker {who!r} has no voice/ref/voice_id")
            unknown = set(spec) - CAST_KEYS
            if unknown:
                problems.append(f"cast: speaker {who!r} unknown keys {sorted(unknown)}")
            ref = spec.get("ref")
            if ref and not pathlib.Path(ref).exists():
                problems.append(f"cast: speaker {who!r} reference not found: {ref}")
    return problems


def out_name(line, mode, seq):
    if mode == "id":
        if not line.get("id"):
            raise SystemExit(f"--name id requires an id on every line: {line}")
        return line["id"]
    if mode == "seq":
        return f"{seq:04d}"
    return djb2(line["who"] + "|" + line["text"])


async def _render_one(backend, line, name, cast, out_dir, force, fmt, sem, log):
    path = out_dir / f"{name}.{fmt}"
    if path.exists() and not force:
        return "kept"
    cloning = getattr(backend, "clones", False)
    speaker = cast.get(line["who"]) or cast.get("_default")
    if not speaker or not voice_of(speaker, cloning):
        log(f"  no voice for speaker '{line['who']}' and no _default — skipped")
        return "failed"
    text = clean(line["text"], cast.get("_subs"))
    if not text:
        return "kept"
    try:
        voice, prosody, style, degree = resolve(line, speaker, cast, backend.styles, cloning)
    except ValueError as e:
        log(f"  {name}: {e}")
        return "failed"
    async with sem:
        for attempt in range(3):
            try:
                await backend.synth(text, voice, prosody, style, degree, path)
                return "made"
            except Exception as e:
                if attempt == 2:
                    log(f"  FAILED {line['who']} {name}: {e}")
                    return "failed"
                await asyncio.sleep(2 * (attempt + 1))


def plan(lines, cast, out_dir, name_mode="hash", fmt="mp3", backend_styles=False,
         cloning=False, ext=None):
    fmt = ext or fmt
    """Dry-run: what would render, what exists, how each line resolves."""
    out_dir = pathlib.Path(out_dir)
    rows, seen = [], set()
    for i, line in enumerate(lines):
        name = out_name(line, name_mode, i + 1)
        if name in seen:
            continue
        seen.add(name)
        speaker = cast.get(line["who"]) or cast.get("_default") or {}
        entry = {"name": name, "who": line["who"],
                 "exists": (out_dir / f"{name}.{fmt}").exists()}
        if voice_of(speaker, cloning):
            try:
                v, p, s, d = resolve(line, speaker, cast, backend_styles, cloning)
                entry.update(voice=v, prosody=p, style=s)
            except ValueError as e:
                entry["error"] = str(e)
        else:
            entry["error"] = "no voice"
        rows.append(entry)
    return rows


async def render(lines, cast, out_dir, name_mode="hash", jobs=4, force=False,
                 fmt=None, log=print, backend=None):
    """Render every unique line. Returns dict of result counts."""
    if backend is None:
        from .backends import EdgeBackend
        backend = EdgeBackend()
    fmt = fmt or getattr(backend, "ext", "mp3")   # honest container per backend
    missing = check_consent(cast, getattr(backend, "clones", False))
    if missing:
        raise ConsentError(
            "cloned voices require explicit permission — add \"consent\": true to "
            f"these cast entries once you have the right to use them: {', '.join(missing)}")
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
        *(_render_one(backend, l, n, cast, out_dir, force, fmt, sem, log)
          for l, n in unique))
    counts = {r: results.count(r) for r in ("made", "kept", "failed")}
    size = sum(f.stat().st_size for f in out_dir.glob(f"*.{fmt}"))
    log(f"{len(unique)} unique lines — made {counts['made']}, kept {counts['kept']}, "
        f"failed {counts['failed']}; pack {size/1e6:.1f} MB")
    return counts
