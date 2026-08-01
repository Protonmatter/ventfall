"""Tone presets and prosody layering.

A *tone* is a named prosody delta (rate/pitch/volume) layered on top of a
speaker's base voice settings. Tones work on every backend, including the free
edge backend, because they are plain prosody. A *style* is a true acted
emotion (angry, sad, whispering...) and needs a backend that supports it
(Azure express-as); on backends without styles, each style degrades to the
nearest tone so the same cast sheet renders anywhere.
"""
import re

# Built-in tone table. Projects can override or extend via "_tones" in the
# cast sheet; entries here use the same {rate, pitch, volume} delta strings.
TONES = {
    "neutral": {},
    "grim":    {"rate": "-12%", "pitch": "-8Hz"},
    "urgent":  {"rate": "+16%", "pitch": "+6Hz"},
    "soft":    {"rate": "-8%",  "volume": "-25%"},
    "whisper": {"rate": "-10%", "volume": "-45%", "pitch": "-4Hz"},
    "bright":  {"rate": "+8%",  "pitch": "+8Hz"},
    "cold":    {"rate": "-5%",  "pitch": "-5Hz"},
    "awe":     {"rate": "-14%", "pitch": "+3Hz", "volume": "-12%"},
    "fear":    {"rate": "+12%", "pitch": "+10Hz", "volume": "-8%"},
    "weary":   {"rate": "-15%", "pitch": "-6Hz", "volume": "-10%"},
}

# How acted styles degrade on backends that only speak prosody.
STYLE_FALLBACK = {
    "angry": "urgent", "shouting": "urgent", "excited": "bright",
    "cheerful": "bright", "hopeful": "bright", "friendly": "bright",
    "sad": "grim", "depressed": "weary", "embarrassed": "soft",
    "whispering": "whisper", "terrified": "fear", "fearful": "fear",
    "serious": "cold", "unfriendly": "cold", "disgruntled": "cold",
    "gentle": "soft", "calm": "soft", "narration-professional": "neutral",
    "documentary-narration": "neutral", "newscast": "neutral",
}

_NUM = re.compile(r"^([+-]?\d+(?:\.\d+)?)\s*(%|Hz|st)$")


def _parse(delta):
    m = _NUM.match(str(delta).strip())
    if not m:
        raise ValueError(f"bad prosody delta {delta!r} (want e.g. '+6%', '-35Hz')")
    return float(m.group(1)), m.group(2)


def _fmt(value, unit):
    if unit == "%" or unit == "st":
        value = round(value, 1)
    else:
        value = round(value)
    s = f"{value:+g}"
    return f"{s}{unit}"


def layer(base, delta):
    """Combine two prosody dicts by summing matching-unit deltas."""
    out = dict(base or {})
    for key, d in (delta or {}).items():
        if key not in ("rate", "pitch", "volume"):
            continue
        if key not in out:
            out[key] = d
            continue
        v1, u1 = _parse(out[key])
        v2, u2 = _parse(d)
        if u1 != u2:      # mixed units: the tone wins
            out[key] = d
        else:
            out[key] = _fmt(v1 + v2, u1)
    return out


def voice_of(speaker, cloning):
    """The backend-appropriate voice handle for a speaker.

    Cloning backends want a reference recording ("ref") or an account voice
    ("voice_id"); stock backends want a catalogue voice name ("voice").
    """
    if cloning:
        v = speaker.get("ref") or speaker.get("voice_id") or speaker.get("voice")
    else:
        v = speaker.get("voice")
    return v


def resolve(line, speaker, cast, backend_styles, cloning=False):
    """Work out the final (voice, prosody, style, styledegree) for a line.

    Per-line keys override tone presets; tone presets layer on the speaker
    base; a requested style is passed through when the backend supports it,
    otherwise it degrades to a tone via STYLE_FALLBACK.
    """
    tones = dict(TONES)
    tones.update(cast.get("_tones") or {})

    prosody = {k: speaker[k] for k in ("rate", "pitch", "volume") if k in speaker}
    if cloning:
        # cloning backends take their delivery from the reference performance;
        # only the language hint is meaningful here
        prosody = {"lang": speaker.get("lang", "en")}
        return voice_of(speaker, True), prosody, None, None
    style = line.get("style") or speaker.get("style")
    degree = line.get("styledegree") or speaker.get("styledegree")
    tone = line.get("tone")

    if style and not backend_styles:
        tone = tone or STYLE_FALLBACK.get(style, None)
        style = None
    if tone:
        if tone not in tones:
            raise ValueError(f"unknown tone {tone!r} (built-ins: {', '.join(sorted(TONES))})")
        prosody = layer(prosody, tones[tone])
    # explicit per-line prosody wins over everything
    for k in ("rate", "pitch", "volume"):
        if k in line:
            prosody[k] = line[k]
    return voice_of(speaker, False), prosody, style, degree
