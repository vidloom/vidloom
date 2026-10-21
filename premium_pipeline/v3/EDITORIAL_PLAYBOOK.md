# Vidloom v3 editorial production protocol

Read RESEARCH.md for evidence and limits. This document describes our production
choices. It supersedes the earlier movie-specific editor contract for v3 work.

## 1. The reason to exist

Write: "For [specific viewer] who [problem/desire], this episode delivers
[observable benefit] by showing [unique evidence or experience]."
Then answer: what can they understand, do, feel or decide afterward that they
could not before? What would disappear if this video disappeared? If the answer
is merely attractive shots and captions, reject the idea.

Develop three ideas against footage you can actually obtain. Rate viewer need,
distinctiveness, proof availability and payoff clarity 0–3 each; use the numbers
to explain selection, not as a predicted viral score. A zero in proof disqualifies
an instructional idea. Choose a narrow promise and one intended viewer action.
Entertainment can be the benefit, but still needs a specific setup and resolution.

Default food-series concept: "One cooking failure, one visible fix." Example
questions: why does this sauce split; what happens when the pan is crowded;
what does properly reduced sauce look like? These are concepts, not permission
to assert untested results. A complete recipe needs complete process coverage.

## 2. Inspect first, write second

Build an asset ledger containing path, source URL/owner, measured duration,
dimensions and audio streams. Watch exact usable ranges. At a minimum inspect
their beginning, midpoint and end; fast action needs denser sampling or playback.
Record literal subject, action, material state, tool and continuity session.
Separate observation (oil visibly bubbles) from inference (oil is 180 C).
Do not infer temperature, quantity, elapsed cooking time or taste from an image.

Classify footage as primary proof, context, comparison, or explicitly labeled
illustration. A generic shot of a different batch cannot prove this recipe's
transformation. A generated food image cannot prove a real cooking result.
Stock footage can illustrate an explanation if identified honestly; it is not
automatically a coherent demonstration.

Maintain a coverage table: claim / required evidence / asset / source interval /
what is visible / uncertainty / missing recording. If missing: acquire the
specific shot, simplify to a narrower supported idea, or return a precise missing
asset list. Never change an observation's subject to make a validator pass.
Scallops do not become potatoes because they are round and browned.

For recipes, use a verified recipe reference or a documented cooking test.
Maintain an ingredient/quantity ledger and operation order. Essential doneness,
heat, cooling, draining and other necessary steps must survive compression.
When showing a transformation, preserve ingredient identity, cutting shape,
utensils and batch continuity. A time jump must be clear. "15 minutes" needs
measured or referenced timing, not a convenient heading.

## 3. Write a spoken story

Structure depends on the benefit:

| Format | Opening | Development | Payoff |
| --- | --- | --- | --- |
| Demonstration | Finished result plus the practical obstacle | Necessary actions, with the critical detail visible | Same batch/result, observable doneness or texture |
| Comparison | Two genuinely different outcomes | Hold conditions equal, change one variable | Explain the observed difference and limitation |
| Explanation | A familiar confusion made visible | Cause, mechanism, consequence with labeled evidence | A concrete rule the viewer can use |
| Story | A specific desire or problem | Attempt, complication, meaningful choice | The promised resolution or honest result |

Write natural connected clauses: "Let the surface dry before it hits the pan,
so it can brown instead of steaming." Avoid machine-gun fragments such as
"Dry. Hot pan. Golden. Insane crunch." Let emphasis vary inside sentences.
Rewrite jargon, empty superlatives and information viewers already see unless
the narration explains why it matters. Keep useful breaths and short anticipation.

Choose three truthful hook candidates: visual contradiction, relatable failure,
or useful result. Pick the one requiring the least explanation and supported by
the first frame. Do not create fake suspense by hiding necessary context. The
payoff must answer that exact opening. A save prompt is optional and must follow
a useful takeaway; "save this" cannot be the takeaway.

Read the whole script aloud before synthesis. Duration follows the information
and performance. Remove a weak sentence before speeding up the speaker. Never
force a recipe into 25 seconds if it loses essential steps.

## 4. Direct a performance, then lock it

Keep the acceptable voice unless the subject requires another. Generate a whole
connected take, not one request per caption or sentence. Audition 2–3 takes if
available; compare flow, word stress, credibility and the final cadence. A bright
voice cannot repair stiff prose. Rewrite difficult passages and regenerate the
whole paragraph, preserving enough surrounding context.

Suggested direction: "Explain this to a friend beside you in the kitchen.
Connected phrases, relaxed confidence, a little curiosity before the reveal.
Stress the one useful contrast. Let the thought finish naturally."

Provider notes: the local `take` command uses one Kokoro call at speed 1.0 and
does not trim internal silence. It cannot guarantee the model won't internally
chunk. For Gemini TTS, check the current installed SDK/model documentation and
capabilities; keep voice persona and delivery directions in supported metadata.
No credentials or permission to use a provider means use available local audio
or report the limitation. Never silently replace the chosen voice/provider.

Listen to voice alone from start to finish. If there is a pitch reset every
sentence, chopped consonant, unnecessary pause, flat list cadence or breathless
run-on, reject the take. Preserve natural phrase boundaries. Do not normalize
every sentence separately. Record take identity and exact script.

Align the accepted waveform using forced alignment, or manually by listening.
Alignment is the timing authority. Verify first/last words, numbers, names and
each instruction at its actual sound. Missing timestamps are blockers.
Caption word-count weights and estimated speech duration are prohibited.

## 5. Edit around meaning

Use integer output frames and measured word times. Each beat refers to an
inclusive range of spoken words. Every shot has explicit output in/out, source
in, speed and observed interval; its source out is computed. No proportional
redistribution of a shot list after narration changes.

Cover the entire claim with evidence compatible with its subject and action.
If you need a setup cut or context picture, place it in its own spoken beat,
or leave the audio silent during it. A spoon swirling while narration describes
knife tenderness fails. The manifest's labels must come from inspection.

Cut when the viewer receives new information, changes attention, or needs to
see the next operation. Hold long enough to understand the critical action.
No minimum number of cuts. Keep important contact moments, before/after states,
and reveals legible. Use an unbroken sound bridge to connect related shots.
Speed increases belong in repetitive process, never in a demonstration of
real-time reaction, sound, or timing. Record any time compression in the edit notes.

## 6. Frame the evidence

Crop coordinates are source pixels `[x, y, width, height]`, after rotation and
pixel-aspect normalization. Use even values and a 9:16 rectangle. Inspect the
subject/action box at the start, middle and end. Include the knife tip, stream,
contact point, steam or comparison region needed to understand the action.
Do not zoom simply because the source resolution permits it.

The baseline renderer deliberately uses stable crops and neutral color. If a
subject leaves the crop, choose a wider usable source or a motivated shot split
and inspect again. True smooth tracking and arbitrary motion graphics are not
implemented in this baseline; don't call a fixed crop subject tracking. If a
wide comparison can't fit vertically, make a designed, clearly labeled layout
as an explicit source asset rather than cropping away the evidence.

Judge color and exposure across adjacent shots; food should remain believable.
No default aggressive contrast, vignette, over-sharpening, white flash, HUD,
top banner, or cinematic grade. Those are decisions needing a purpose.

## 7. Caption hierarchy and sound

Captions help a muted viewer understand the useful thought. Use short natural
phrases, accurate words and one stable family. The baseline derives text from
aligned words and uses DejaVu Sans, white with restrained dark outline. No bounce
on every word. Place them away from the action and UI; keep a consistent anchor
unless the shot demands a move. Numerical recipe cards belong in a deliberately
composed source graphic, never a giant paragraph over the pan.

The validator estimates text width conservatively. It does not measure actual
glyph bounds, detect faces, or know changing platform UI. Inspect rendered
captions at phone size with actual UI overlays before final acceptance. Check
first, midpoint and last frame of every caption for collisions and clipping.

Hierarchy: voice intelligibility, relevant source sound, motivated foley, music.
For sensory moments, briefly let the actual sound lead. Use source audio where
available. Foley may reinforce contact; synthesized noise may not be presented
as proof that food actually crunches. Give every effect a named visible event.
Skip whooshes on ordinary hard cuts and impacts without impacts.

Choose music for scene energy and rhythm; a single coherent bed often suffices.
Place changes at story turns. Set gains by listening; automatic ducking is a
starting point. Listen for pumping, masking and fatigue on headphones and a
small mono speaker. Baseline mastering is single-pass -16 LUFS with -1.5 dBTP
target and post-encode measurement. It is a delivery default, not an algorithm
hack or proof of subjective audio quality.

## 8. Six separate reviews

The editor or a capable multimodal reviewer performs these reviews; they are
not requests for user permission. Record reviewer identity, concrete timestamps
and current project fingerprint. A changed script, edit, asset or recording
invalidates reviews. Never mark an inaccessible sensory check as passed.

1. Purpose: state the viewer benefit and the distinctive evidence without
   repeating the video's promotional adjectives.
2. Proof: challenge every claim against the source clip. Search for the strongest
   counterexample: wrong ingredient, operation, batch, result or unsupported fact.
3. Voice: listen to the full take without pictures; check continuity and emphasis.
4. Framing: inspect source start/mid/end and crop rectangles; action must survive.
5. Readability: inspect planned text and crops; later inspect actual rendered text.
6. Payoff: describe exactly how the ending resolves the opening; no empty CTA.

Automated checks validate metadata and declarations; a model can still lie or
misidentify footage. Strict JSON and an audit trail constrain errors, not truth.
When sensory review is unavailable, stop with the relevant review pending.

After a future render, repeat a complete normal-speed watch, muted watch, voice
and mixed-audio listen, and phone-size UI check. Technical QC alone never releases
a draft. Write `FINAL_REVIEW.md` with video SHA256, specific observations and any
remaining limitations. Handoff begins with the exact absolute file path.

## 9. Iterate with observed audience outcomes

Use the experiment protocol and metric definitions in RESEARCH.md. Maintain a
format identity and test one change at a time. Budget effort first to idea,
evidence and performance, then editing and packaging. Fail early if the key
footage is unavailable. More transitions cannot compensate for absent evidence.
