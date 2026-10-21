"""Small, strict interchange contract. No model SDK dependency."""
def obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}

def arr(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}

S = {"type": "string", "minLength": 1}
N = {"type": "number", "minimum": 0}
I = {"type": "integer", "minimum": 0}
B = {"type": "boolean"}
BOX = {"type": "array", "items": I, "minItems": 4, "maxItems": 4}
SCHEMA = obj(
    version={"const": 3}, title=S, fps={"enum": [30, 60]}, total_frames={"type": "integer", "minimum": 1},
    brief=obj(audience=S, viewer_problem=S, promise=S, original_contribution=S, payoff=S,
              format={"enum": ["demonstration", "comparison", "explanation", "story"]}),
    assets=arr(obj(id=S, path=S, kind={"enum": ["video", "audio"]}, source_url=S, rights=S,
                   observations=arr(obj(id=S, start=N, end=N, subject=S, action=S,
                                        continuity=S, detail=S, inspected=B))), 1),
    narration=obj(path=S, script=S, delivery=S, generation={"enum": ["continuous_take", "human_recording"]},
                  alignment_path=S, alignment_method={"enum": ["forced_alignment", "manual_listened"]}),
    beats=arr(obj(id=S, word_first=I, word_last=I, role={"enum": ["hook", "context", "mechanism", "payoff"]},
                  claim=S, subject=S, action=S, source=S), 1),
    shots=arr(obj(id=S, asset=S, observation=S, start_frame=I, end_frame=I, source_in=N,
                  speed={"type": "number", "minimum": 0.5, "maximum": 2}, crop=BOX,
                  subject_boxes=arr(BOX, 3), beat_ids=arr(S), purpose=S, production_gain_db={"type": "number", "minimum": -96, "maximum": 6}), 1),
    captions=arr(obj(word_first=I, word_last=I, x=I, y=I, font_size={"type": "integer", "minimum": 40, "maximum": 100})),
    audio=arr(obj(asset=S, kind={"enum": ["music", "foley"]}, start_frame=I, end_frame=I, source_in=N,
                  gain_db={"type": "number", "minimum": -60, "maximum": 0}, motivation=S)),
    reviews=arr(obj(criterion={"enum": ["purpose", "proof", "voice", "framing", "readability", "payoff"]},
                    passed=B, reviewer=S, evidence=S, fingerprint=S))
)
SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
