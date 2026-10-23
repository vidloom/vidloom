"""Regression tests for the actual prior failure modes. No video generation."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline as m
from import_alignment import convert


class Gates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.words = [{"word":"Watch", "start":0.1,"end":0.5},
                      {"word":"this.", "start":0.55,"end":0.9},
                      {"word":"It", "start":1.1,"end":1.4},
                      {"word":"browns.", "start":1.5,"end":1.9}]
        m.write(self.root/"words.json",self.words)
        self.p = {
            "version":3,"title":"Metadata fixture only","fps":30,"total_frames":66,
            "brief":{"audience":"Home cooks","viewer_problem":"Recognize browning","promise":"Show actual color change",
                     "original_contribution":"Measured same-batch comparison","payoff":"Visible browned surface","format":"demonstration"},
            "assets":[{"id":"A","path":"source.mp4","kind":"video","source_url":"original recording","rights":"owned",
                       "observations":[{"id":"O","start":0,"end":5,"subject":"potato","action":"browning","continuity":"session1",
                                        "detail":"Fixture only; not real observation","inspected":True}]}],
            "narration":{"path":"voice.wav","script":"Watch this. It browns.","delivery":"Connected explanation",
                         "generation":"continuous_take","alignment_path":"words.json","alignment_method":"manual_listened"},
            "beats":[{"id":"B1","word_first":0,"word_last":1,"role":"hook","claim":"Look at browning","subject":"potato","action":"browning","source":"recording"},
                     {"id":"B2","word_first":2,"word_last":3,"role":"payoff","claim":"It browns","subject":"potato","action":"browning","source":"recording"}],
            "shots":[{"id":"S1","asset":"A","observation":"O","start_frame":0,"end_frame":30,"source_in":0,"speed":1,
                      "crop":[0,0,1080,1920],"subject_boxes":[[100,100,500,500]]*3,"beat_ids":["B1"],"purpose":"Evidence","production_gain_db":-96},
                     {"id":"S2","asset":"A","observation":"O","start_frame":30,"end_frame":66,"source_in":1,"speed":1,
                      "crop":[0,0,1080,1920],"subject_boxes":[[100,100,500,500]]*3,"beat_ids":["B2"],"purpose":"Payoff","production_gain_db":-96}],
            "captions":[{"word_first":0,"word_last":1,"x":480,"y":1300,"font_size":56},
                        {"word_first":2,"word_last":3,"x":480,"y":1300,"font_size":56}],
            "audio":[],"reviews":[]}

    def errors(self, **kw):
        return m.validate(self.p,self.root,media=False,reviews=False,**kw)[0]

    def assert_error(self, code):
        self.assertTrue(any(code in e for e in self.errors()),self.errors())

    def test_valid_fixture(self):
        self.assertEqual([],self.errors())

    def test_wrong_food_rejected(self):
        self.p["assets"][0]["observations"][0]["subject"]="scallop"
        self.assert_error("SEMANTIC_MISMATCH")

    def test_wrong_action_rejected(self):
        self.p["assets"][0]["observations"][0]["action"]="washing"
        self.assert_error("SEMANTIC_MISMATCH")

    def test_matching_footage_at_wrong_time_rejected(self):
        self.p["shots"][0]["beat_ids"]=["B2"]
        self.p["shots"][1]["beat_ids"]=["B1"]
        self.assert_error("UNCOVERED_CLAIM")

    def test_source_outside_observation_rejected(self):
        self.p["shots"][1]["source_in"]=4.9
        self.assert_error("PROOF_RANGE")

    def test_gap_rejected(self):
        self.p["shots"][1]["start_frame"]=31
        self.assert_error("TIMELINE")

    def test_overlap_rejected(self):
        self.p["shots"][1]["start_frame"]=29
        self.assert_error("TIMELINE")

    def test_lost_subject_rejected(self):
        self.p["shots"][0]["subject_boxes"][0]=[1000,100,500,500]
        self.assert_error("SUBJECT_LOST")

    def test_landscape_crop_rejected(self):
        self.p["shots"][0]["crop"]=[0,0,1920,1080]
        self.assert_error("CROP")

    def test_caption_outside_safe_area(self):
        self.p["captions"][0]["x"]=1000
        self.assert_error("CAPTION_SAFE_AREA")

    def test_fake_transcript_rejected(self):
        self.p["narration"]["script"]="These are scallops."
        self.assert_error("TRANSCRIPT_MISMATCH")

    def test_word_overlap_rejected(self):
        self.words[1]["start"]=0.2
        m.write(self.root/"words.json",self.words)
        self.assert_error("ALIGNMENT")

    def test_unknown_fields_rejected(self):
        self.p["shots"][0]["weight"]=0.8
        self.assert_error("SCHEMA")

    def test_nonfinite_rejected(self):
        self.p["shots"][0]["speed"]=float("nan")
        self.assert_error("NONFINITE")

    def test_uninspected_asset_rejected(self):
        self.p["assets"][0]["observations"][0]["inspected"]=False
        self.assert_error("OBSERVATION")

    def test_multiple_batches_rejected(self):
        o=copy.deepcopy(self.p["assets"][0]["observations"][0])
        o.update(id="O2",continuity="different_batch")
        self.p["assets"][0]["observations"].append(o)
        self.p["shots"][1]["observation"]="O2"
        self.assert_error("CONTINUITY")

    def test_no_review_no_release(self):
        errors,_=m.validate(self.p,self.root,media=False,reviews=True)
        self.assertEqual(6,sum("REVIEW_REQUIRED" in e for e in errors))

    def test_review_invalidated_by_edit(self):
        fp=m.fingerprint(self.p,self.root)
        self.p["reviews"]=[{"criterion":c,"passed":True,"reviewer":"test fixture",
                           "evidence":"Synthetic test note only, not a real editorial review.","fingerprint":fp} for c in m.CRITERIA]
        self.assertEqual([],m.validate(self.p,self.root,media=False,reviews=True)[0])
        self.p["shots"][0]["purpose"]="Changed edit"
        self.assertTrue(any("REVIEW_REQUIRED" in e for e in m.validate(self.p,self.root,media=False,reviews=True)[0]))

    def test_media_hash_invalidates_review(self):
        before=m.fingerprint(self.p,self.root)
        m.write(self.root/"words.json", self.words+[{'word':'extra','start':2,'end':2.1}])
        self.assertNotEqual(before,m.fingerprint(self.p,self.root))

    def test_alignment_import_refuses_guesses(self):
        with self.assertRaises(ValueError):
            convert({"word_segments":[{"word":"unmeasured"}]})

    def test_alignment_import(self):
        self.assertEqual(self.words,convert({"segments":[{"words":self.words}]}))

    def test_continuous_voice_and_exact_frames_compiled(self):
        graph,command=m.compile_graph(self.p,self.root)
        self.assertIn("trim=end_frame=30",graph)
        self.assertIn("trim=end_frame=36",graph)
        self.assertNotIn("silenceremove",graph)
        self.assertEqual(1,sum(x.endswith("voice.wav") for x in command))
        self.assertNotIn("vignette",graph)
        self.assertNotIn("drawbox",graph)

    def test_source_audio_retimed_with_atempo(self):
        self.p["shots"][0]["speed"]=1.5
        self.p["shots"][0]["production_gain_db"]=-12
        graph,_=m.compile_graph(self.p,self.root)
        self.assertIn("atempo=1.5",graph)
        self.assertIn("duration=1.5",graph)

    def test_caption_uses_recorded_timestamps(self):
        text=m.captions(self.p,self.words)
        self.assertIn("0:00:00.10",text)
        self.assertIn("0:00:00.90",text)
        self.assertIn("&H0000FFFF&",text)
        self.assertIn("Watch",text)
        self.assertIn("this.",text)
        self.assertNotIn("\\t(",text)

    def test_actual_media_bounds_probed(self):
        fake={"streams":[{"codec_type":"video","width":1080,"height":1920,"sample_aspect_ratio":"1:1"}],"format":{"duration":"0.5"}}
        with patch.object(Path,"is_file",return_value=True),patch.object(m,"probe",return_value=fake):
            errors,_=m.validate(self.p,self.root,media=True,reviews=False)
        self.assertTrue(any("SOURCE_OVERRUN" in e for e in errors))

    def test_silent_source_audio_rejected(self):
        self.p["shots"][0]["production_gain_db"]=-12
        fake={"streams":[{"codec_type":"video","width":1080,"height":1920,"sample_aspect_ratio":"1:1"}],"format":{"duration":"10"}}
        with patch.object(Path,"is_file",return_value=True),patch.object(m,"probe",return_value=fake):
            errors,_=m.validate(self.p,self.root,media=True,reviews=False)
        self.assertTrue(any("SOURCE_AUDIO" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
