"""Synthesis backends.

edge   — free, no key, Microsoft neural voices via edge-tts. Prosody only:
         tones work, acted styles degrade to tones.
azure  — Azure Speech (needs AZURE_SPEECH_KEY + AZURE_SPEECH_REGION env vars).
         Full SSML: true express-as emotional styles with styledegree, plus
         prosody and break tags for beats.
xtts   — LOCAL voice cloning (Coqui XTTS-v2). Speakers carry a "ref" wav —
         a mic recording or a clip extracted from any audio/video — instead
         of a stock voice name. Free, offline after the first model download,
         needs `pip install coqui-tts` (torch). Cloned speakers must declare
         "consent": true in the cast sheet.
elevenlabs — API voice cloning/synthesis (ELEVENLABS_API_KEY env var). The
         most natural output; speakers use a "voice_id" from your ElevenLabs
         account (including instant-cloned voices). Same consent rule for
         cloned voices.
fake   — writes tiny placeholder files; used by the test suite and --dry-run
         style verification without touching the network.
"""
import asyncio, json, os, urllib.request
from xml.sax.saxutils import escape


class EdgeBackend:
    name = "edge"
    ext = "mp3"
    styles = False
    clones = False

    def __init__(self):
        try:
            import edge_tts
        except ImportError:
            raise SystemExit("the edge backend needs: pip install edge-tts")
        self._et = edge_tts

    async def synth(self, text, voice, prosody, style, degree, out_path):
        kwargs = {k: v for k, v in prosody.items() if k in ("rate", "pitch", "volume")}
        await self._et.Communicate(text, voice, **kwargs).save(str(out_path))


class AzureBackend:
    """Azure Cognitive Services TTS. Untested without a subscription key —
    implemented to the documented REST contract; report issues if the service
    shifts. Beats: '…' and '—' in text become 350ms breaks."""
    name = "azure"
    ext = "mp3"
    styles = True
    clones = False
    FORMAT = "audio-24khz-96kbitrate-mono-mp3"

    def __init__(self):
        self.key = os.environ.get("AZURE_SPEECH_KEY")
        self.region = os.environ.get("AZURE_SPEECH_REGION")
        if not self.key or not self.region:
            raise SystemExit("the azure backend needs AZURE_SPEECH_KEY and "
                             "AZURE_SPEECH_REGION environment variables")
        self.url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"

    def _ssml(self, text, voice, prosody, style, degree):
        body = escape(text)
        body = body.replace("…", '<break time="350ms"/>').replace("—", '<break time="350ms"/>')
        if prosody:
            attrs = " ".join(f'{k}="{v}"' for k, v in prosody.items())
            body = f"<prosody {attrs}>{body}</prosody>"
        if style:
            deg = f' styledegree="{degree}"' if degree else ""
            body = f'<mstts:express-as style="{escape(str(style))}"{deg}>{body}</mstts:express-as>'
        lang = "-".join(voice.split("-")[:2])
        return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{lang}">'
                f'<voice name="{voice}">{body}</voice></speak>')

    def _post(self, ssml):
        req = urllib.request.Request(self.url, data=ssml.encode("utf-8"), headers={
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": self.FORMAT,
            "User-Agent": "voforge",
        })
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    async def synth(self, text, voice, prosody, style, degree, out_path):
        data = await asyncio.to_thread(self._post, self._ssml(text, voice, prosody, style, degree))
        out_path.write_bytes(data)


class XttsBackend:
    """Local voice cloning with Coqui XTTS-v2. The 'voice' a speaker carries is
    the path to a reference WAV (see voforge.refs / `voforge --extract-ref`);
    prosody deltas and styles do not apply — the reference performance drives
    the delivery. First run downloads ~1.8GB of model weights."""
    name = "xtts"
    ext = "wav"   # XTTS emits WAV; keep it honest
    styles = False
    clones = True

    def __init__(self):
        try:
            from TTS.api import TTS
        except ImportError:
            raise SystemExit("the xtts backend needs: pip install coqui-tts "
                             "(a torch-compatible Python is required)")
        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

    async def synth(self, text, voice, prosody, style, degree, out_path):
        # `voice` is the reference wav path; language from prosody slot "lang"
        lang = prosody.get("lang", "en") if isinstance(prosody, dict) else "en"
        await asyncio.to_thread(
            self._tts.tts_to_file, text=text, speaker_wav=str(voice),
            language=lang, file_path=str(out_path))


class ElevenLabsBackend:
    """ElevenLabs TTS/cloning REST API (ELEVENLABS_API_KEY env var). The
    'voice' a speaker carries is an ElevenLabs voice_id — stock or a voice
    you cloned in your account. Untested without a subscription; implemented
    to the documented v1 contract."""
    name = "elevenlabs"
    ext = "mp3"
    styles = False
    clones = True
    MODEL = "eleven_multilingual_v2"

    def __init__(self):
        self.key = os.environ.get("ELEVENLABS_API_KEY")
        if not self.key:
            raise SystemExit("the elevenlabs backend needs the "
                             "ELEVENLABS_API_KEY environment variable")

    def _post(self, voice_id, payload):
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"xi-api-key": self.key, "Content-Type": "application/json",
                     "Accept": "audio/mpeg"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()

    async def synth(self, text, voice, prosody, style, degree, out_path):
        payload = {"text": text, "model_id": self.MODEL}
        data = await asyncio.to_thread(self._post, voice, payload)
        out_path.write_bytes(data)


class FakeBackend:
    name = "fake"
    ext = "mp3"
    styles = True
    clones = False   # tests that exercise the cloning path set this True

    def __init__(self):
        self.calls = []

    async def synth(self, text, voice, prosody, style, degree, out_path):
        self.calls.append({"text": text, "voice": voice, "prosody": dict(prosody),
                           "style": style, "degree": degree, "path": str(out_path)})
        out_path.write_bytes(b"FAKE")


BACKENDS = {"edge": EdgeBackend, "azure": AzureBackend, "xtts": XttsBackend,
            "elevenlabs": ElevenLabsBackend, "fake": FakeBackend}


def make_backend(name):
    if name not in BACKENDS:
        raise SystemExit(f"unknown backend {name!r} (have: {', '.join(BACKENDS)})")
    return BACKENDS[name]()
