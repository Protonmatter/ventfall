"""voforge test suite — runs entirely offline via FakeBackend.

    python -m unittest discover -s tests   (from tools/voforge/)
"""
import asyncio, pathlib, sys, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import voforge
from voforge.backends import FakeBackend


CAST = {
    "_default": {"voice": "en-GB-ThomasNeural", "rate": "-6%"},
    "_subs": [["⋮", ","]],
    "hero": {"voice": "en-US-AriaNeural"},
    "brute": {"voice": "en-US-GuyNeural", "rate": "-10%", "pitch": "-20Hz"},
}


def run(coro):
    return asyncio.run(coro)


class TestHash(unittest.TestCase):
    def test_known_vector(self):
        # must match the JS reference implementation exactly
        self.assertEqual(voforge.djb2("hero|CSV line one."), "ba65874b")

    def test_utf8(self):
        self.assertEqual(len(voforge.djb2("choir|⋮ pressure ⋮")), 8)


class TestTones(unittest.TestCase):
    def test_layering_sums_matching_units(self):
        out = voforge.layer({"rate": "+6%"}, {"rate": "-12%"})
        self.assertEqual(out["rate"], "-6%")

    def test_layering_new_key(self):
        out = voforge.layer({"rate": "+6%"}, {"pitch": "-8Hz"})
        self.assertEqual(out, {"rate": "+6%", "pitch": "-8Hz"})

    def test_style_falls_back_without_backend_support(self):
        line = {"who": "hero", "text": "x", "style": "angry"}
        v, p, s, d = voforge.resolve(line, CAST["hero"], CAST, backend_styles=False)
        self.assertIsNone(s)                      # style dropped...
        self.assertEqual(p["rate"], "+16%")       # ...urgent tone applied instead

    def test_style_passes_through_with_backend_support(self):
        line = {"who": "hero", "text": "x", "style": "angry", "styledegree": "1.6"}
        v, p, s, d = voforge.resolve(line, CAST["hero"], CAST, backend_styles=True)
        self.assertEqual((s, d), ("angry", "1.6"))

    def test_line_prosody_overrides_tone(self):
        line = {"who": "hero", "text": "x", "tone": "grim", "rate": "+30%"}
        _, p, _, _ = voforge.resolve(line, CAST["hero"], CAST, False)
        self.assertEqual(p["rate"], "+30%")

    def test_unknown_tone_raises(self):
        with self.assertRaises(ValueError):
            voforge.resolve({"who": "hero", "text": "x", "tone": "sassy"},
                            CAST["hero"], CAST, False)

    def test_project_tone_override(self):
        cast = dict(CAST, _tones={"grim": {"rate": "-50%"}})
        _, p, _, _ = voforge.resolve({"who": "hero", "text": "x", "tone": "grim"},
                                     cast["hero"], cast, False)
        self.assertEqual(p["rate"], "-50%")


class TestNaming(unittest.TestCase):
    def test_modes(self):
        line = {"who": "hero", "text": "hi", "id": "a1"}
        self.assertEqual(voforge.out_name(line, "id", 1), "a1")
        self.assertEqual(voforge.out_name(line, "seq", 7), "0007")
        self.assertEqual(voforge.out_name(line, "hash", 1), voforge.djb2("hero|hi"))


class TestValidate(unittest.TestCase):
    def test_clean_input(self):
        self.assertEqual(voforge.validate([{"who": "hero", "text": "hi"}], CAST), [])

    def test_reports_all_problems(self):
        bad = [{"who": "ghost", "text": "boo", "volume2": "x"}, {"text": "no who"}]
        cast = {"hero": {"rate": "+1%"}}          # speaker missing voice, no default
        probs = voforge.validate(bad, cast)
        # ghost w/o default, unknown key volume2, missing who, voiceless cast entry
        self.assertEqual(len(probs), 4)


class TestRender(unittest.TestCase):
    def test_render_dedup_keep_force(self):
        fake = FakeBackend()
        lines = [{"who": "hero", "text": "one"},
                 {"who": "hero", "text": "one"},          # duplicate → dedup
                 {"who": "brute", "text": "two", "tone": "grim"}]
        with tempfile.TemporaryDirectory() as td:
            log = lambda *a: None
            c1 = run(voforge.render(lines, CAST, td, backend=fake, log=log))
            self.assertEqual((c1["made"], c1["kept"]), (2, 0))
            # brute base -10% layered with grim -12% = -22%
            brute_call = next(c for c in fake.calls if c["voice"] == "en-US-GuyNeural")
            self.assertEqual(brute_call["prosody"]["rate"], "-22%")
            c2 = run(voforge.render(lines, CAST, td, backend=fake, log=log))
            self.assertEqual((c2["made"], c2["kept"]), (0, 2))
            c3 = run(voforge.render(lines, CAST, td, backend=fake, force=True, log=log))
            self.assertEqual(c3["made"], 2)

    def test_subs_applied(self):
        fake = FakeBackend()
        with tempfile.TemporaryDirectory() as td:
            run(voforge.render([{"who": "hero", "text": "a ⋮ b"}], CAST, td,
                               backend=fake, log=lambda *a: None))
            self.assertEqual(fake.calls[0]["text"], "a , b")

    def test_missing_speaker_fails_not_crashes(self):
        fake = FakeBackend()
        cast = {"hero": {"voice": "x"}}           # no _default
        with tempfile.TemporaryDirectory() as td:
            c = run(voforge.render([{"who": "ghost", "text": "boo"}], cast, td,
                                   backend=fake, log=lambda *a: None))
            self.assertEqual(c["failed"], 1)


class TestCloning(unittest.TestCase):
    def test_voice_of_prefers_ref_when_cloning(self):
        spk = {"voice": "en-US-AriaNeural", "ref": "mara.wav", "voice_id": "abc"}
        self.assertEqual(voforge.voice_of(spk, cloning=True), "mara.wav")
        self.assertEqual(voforge.voice_of(spk, cloning=False), "en-US-AriaNeural")

    def test_consent_gate_blocks_unconsented_clone(self):
        cast = {"mara": {"ref": "mara.wav"}}
        self.assertEqual(voforge.check_consent(cast, cloning=True), ["mara"])
        fake = FakeBackend(); fake.clones = True
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(voforge.ConsentError):
                run(voforge.render([{"who": "mara", "text": "hi"}], cast, td,
                                   backend=fake, log=lambda *a: None))

    def test_consent_true_allows_clone(self):
        cast = {"mara": {"ref": "mara.wav", "consent": True}}
        self.assertEqual(voforge.check_consent(cast, cloning=True), [])
        fake = FakeBackend(); fake.clones = True
        with tempfile.TemporaryDirectory() as td:
            c = run(voforge.render([{"who": "mara", "text": "hi"}], cast, td,
                                   backend=fake, log=lambda *a: None))
            self.assertEqual(c["made"], 1)
            self.assertEqual(fake.calls[0]["voice"], "mara.wav")

    def test_no_consent_needed_for_stock_backend(self):
        cast = {"mara": {"ref": "mara.wav"}}
        self.assertEqual(voforge.check_consent(cast, cloning=False), [])

    def test_backend_ext_drives_filename(self):
        fake = FakeBackend(); fake.ext = "wav"; fake.clones = True
        cast = {"mara": {"ref": "mara.wav", "consent": True}}
        with tempfile.TemporaryDirectory() as td:
            run(voforge.render([{"who": "mara", "text": "hi"}], cast, td,
                               backend=fake, log=lambda *a: None))
            files = [p.name for p in pathlib.Path(td).iterdir()]
            self.assertTrue(files[0].endswith(".wav"))


class TestPlan(unittest.TestCase):
    def test_plan_reports_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            rows = voforge.plan([{"who": "hero", "text": "one", "style": "sad"}],
                                CAST, td)
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]["exists"])
            self.assertIsNone(rows[0]["style"])           # edge: degraded to tone
            self.assertEqual(rows[0]["prosody"]["rate"], "-12%")  # grim
            self.assertEqual(list(pathlib.Path(td).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
