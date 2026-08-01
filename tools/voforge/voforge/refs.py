"""Reference-voice utilities: turn any media into a clean cloning reference.

A cloning reference is a short mono WAV (6-30s of one person speaking,
no music, no crosstalk). Sources:

  extract_ref("interview.mp4", "mara.wav", start=12, duration=20)   # video
  extract_ref("memo.m4a",      "mara.wav")                          # audio file
  record_ref("mara.wav", seconds=20)                                # microphone

ffmpeg is found on PATH or via the imageio-ffmpeg pip package (which ships a
static binary), so no system install is required.

CONSENT: only clone voices you own or have explicit permission to use. The
render pipeline refuses cloned speakers whose cast entry lacks
"consent": true — see README.
"""
import pathlib, shutil, subprocess, sys


def ffmpeg_path():
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit(
            "ffmpeg not found — install it, or: pip install imageio-ffmpeg")


def _run(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{proc.stderr[-800:]}")


def extract_ref(src, out_wav, start=None, duration=None, sample_rate=24000):
    """Extract a mono cloning reference from any audio or video file."""
    src, out_wav = pathlib.Path(src), pathlib.Path(out_wav)
    if not src.exists():
        raise SystemExit(f"no such file: {src}")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    args = [ffmpeg_path(), "-y"]
    if start is not None:
        args += ["-ss", str(start)]
    args += ["-i", str(src)]
    if duration is not None:
        args += ["-t", str(duration)]
    args += ["-vn", "-ac", "1", "-ar", str(sample_rate),
             "-af", "loudnorm=I=-20:TP=-3",       # even out levels for cloning
             str(out_wav)]
    _run(args)
    return out_wav


def record_ref(out_wav, seconds=20, device=None, sample_rate=24000):
    """Record a cloning reference straight from the default microphone."""
    out_wav = pathlib.Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_path()
    if sys.platform == "win32":
        dev = device or "audio=default"
        if device and not device.startswith("audio="):
            dev = f"audio={device}"
        grab = ["-f", "dshow", "-i", dev]
    elif sys.platform == "darwin":
        grab = ["-f", "avfoundation", "-i", f":{device or '0'}"]
    else:
        grab = ["-f", "pulse", "-i", device or "default"]
    print(f"recording {seconds}s from microphone — speak naturally, then wait...")
    _run([ff, "-y", *grab, "-t", str(seconds),
          "-ac", "1", "-ar", str(sample_rate),
          "-af", "loudnorm=I=-20:TP=-3", str(out_wav)])
    return out_wav
