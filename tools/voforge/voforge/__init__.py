"""voforge — batch neural voice-over generator with tones, emotional styles,
and voice cloning from microphone/media references.

Public API:
    render(lines, cast, out_dir, ...)   async render pipeline
    plan(lines, cast, out_dir, ...)     dry-run resolution
    djb2(s), clean(text, subs)          hashing / text cleanup
    TONES, STYLE_FALLBACK, layer        tone system
    extract_ref(...), record_ref(...)   build cloning references
    make_backend(name)                  edge | azure | xtts | elevenlabs | fake

See README.md for the cast-sheet and lines-file formats, and runtime/ for
drop-in pack consumers (JS, Unity, Godot).
"""
from .core import (ConsentError, check_consent, clean, djb2, load_lines,
                   out_name, plan, render, validate)
from .backends import BACKENDS, make_backend
from .refs import extract_ref, record_ref
from .tones import STYLE_FALLBACK, TONES, layer, resolve, voice_of

__version__ = "0.3.0"
__all__ = ["render", "plan", "validate", "load_lines", "out_name", "djb2", "clean",
           "TONES", "STYLE_FALLBACK", "layer", "resolve", "voice_of",
           "make_backend", "BACKENDS", "extract_ref", "record_ref",
           "check_consent", "ConsentError", "__version__"]
