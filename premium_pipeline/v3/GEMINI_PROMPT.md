# Copy this prompt into Gemini's coding-agent session

You are executing Vidloom v3 in this repository:
`/home/omie/MyShits/Youtube Automation - Vidloom`.

Read these files completely before doing production work:

1. `premium_pipeline/v3/README.md`
2. `premium_pipeline/v3/EDITORIAL_PLAYBOOK.md`
3. `premium_pipeline/v3/RESEARCH.md`
4. `premium_pipeline/v3/schema.py`
5. `premium_pipeline/v3/WORKED_EXAMPLE.md`

This is a production execution prompt: create one original cinema-scene
breakdown Short using the stages below, unless the user's latest explicit instruction limits the work to
planning or pipeline development. In that case do not generate a reel. Follow
the authorized stages to completion. Do not publish
or upload anything unless separately instructed. Do not ask permission for
ordinary local production steps that the user already authorized.

GENRE LOCK — MANDATORY
The only accepted format is `cinema_scene_breakdown`: one specific film scene,
one original observation about why its visual storytelling, performance,
blocking, sound, editing or setup/payoff works, visible evidence for every claim,
and a complete payoff. Reject plot recaps, clip compilations, celebrity news,
generic movie facts and uncommented footage. Do not change genre to fill a slot.

Your responsibility is a useful, coherent, evidence-supported Short. Do not
promise a ranking or call an edit premium because its resolution/loudness pass.
The last edit falsely used scallops as potatoes, matched cuts by proportional
weights and synthesized disconnected sentence fragments. Do not repeat these.
Keep the acceptable voice unless there is a concrete performance reason to change.

Work one stage at a time. Persist artifacts to a new project directory and keep
`STATUS.md` listing completed stages, exact next action and real blockers. Give
brief progress updates. Read the prior artifact before producing the next one.
Do not silently return to the old renderer or weaken the v3 checks.

STAGE A — PROVABLE IDEA
If no scene is supplied, inspect the authorized local scene library and propose
three ideas internally. Select the idea with the clearest original observation
and complete visible payoff, not the most famous movie. Define the exact viewer,
question and contribution. Write `brief.md`, including why someone would watch
through the payoff. Reject empty scene montages and plot summary. The Short must
teach the viewer something precise about how that scene works.

STAGE B — EVIDENCE
Probe local files, open actual source pages and inspect exact video ranges.
Write `evidence.md`: asset IDs, source times, literal observations, continuity,
what each range proves, fact sources and missing coverage. Record uncertainty.
Default one-frame-per-second video analysis is insufficient for fast actions;
inspect denser ranges and start/mid/end frames. If you cannot see/hear an input,
do not claim you reviewed it. Metadata is a clue, not a substitute for observation.
Never rename a subject, invent a recording, fabricate view counts, or use added
sound design to prove what occurred in the original scene. Missing proof requires another asset, a
narrower truthful idea, or a precise missing-footage report.

STAGE C — SCRIPT AND PERFORMANCE
Write three truthful opening alternatives and select the clearest one supported
by the first frame. Write one connected conversational script. Every sentence
must advance the promise, explain a cause, or resolve the question. No bullet-list
delivery, fake urgency, unsupported timing or "save this" as the entire payoff.
Read aloud. Generate/import a whole take; do not make a separate TTS call per
sentence/caption. Use local `take` if appropriate, or a configured TTS provider
whose current API you verified. Do not silently switch voices on API failure.
Listen without visuals. Repair prose or regenerate context when delivery resets.
Keep natural pauses. Never apply blanket 120ms silence splicing.

STAGE D — ALIGN AND CONSTRUCT
Align the final take using actual word timestamps. Use the provided importer
for WhisperX JSON, or documented manual listening. Stop on unaligned words.
Populate `project.json` using the template and strict schema. Bind every spoken
word to a beat, and every beat to matching observations and output intervals.
Use exact integer frames. Do not distribute a list of shots by relative weights.
Subject and action labels must come from truthful inspection. For abstract
explanations, use clearly labeled diagrams or relevant observed evidence and
review whether the image genuinely supports the inference.
Choose deliberate stable crops containing the critical action at start/mid/end.
Use aligned phrase captions with readable exposure, no automatic word bounce,
and no generic HUD. Compose graphics separately if the idea requires them.
Add source sound and only motivated effects; music supports the explanation.

STAGE E — REJECT ERRORS
Run:
`python3 premium_pipeline/v3/pipeline.py validate PROJECT/project.json --draft`
Fix the content causing each error. Never patch the validator, replace missing
times with guesses, or relabel an object merely to pass a consistency check.
If the schema does not support an essential truthful edit, document the specific
limitation rather than silently bypassing it.

Perform the six reviews in the playbook: purpose, proof, voice, framing,
readability and payoff. Do a separate skeptical inspection pass: identify the
strongest reason the edit might be wrong. Cite exact source/timeline moments in
each review. The reviewer may be you if you actually have sensory access.
Never manufacture a human review or rubber-stamp inaccessible audio/video.
Get the current fingerprint:
`python3 premium_pipeline/v3/pipeline.py fingerprint PROJECT/project.json`
Record truthful reviews against it. Changing project/media invalidates them.
Run full validation, then `plan`. A plan writes commands and captions, not video.

STAGE F — PRODUCE ONLY WHEN REQUESTED
Choose an installed, working H.264 encoder. Use the v3 render command. Never
overwrite a prior output; create a new version directory when iterating.
Inspect the full draft at normal speed, muted, voice-only and mixed audio; check
phone-size captions and interface clearance. Run QC. Technical pass does not
equal editorial pass. Write `FINAL_REVIEW.md` tied to the output SHA256, listing
observed defects and their repairs. Do not claim excellence or expected views.

QUEUE AND HANDOFF
After the final render, QC and hash-bound `FINAL_REVIEW.md` are complete, enqueue
the project exactly once. Write an accurate title and description that state the
actual observation; never use a misleading superlative. Example command shape:

`python3 -m automation.enqueue PROJECT/project.json --title "..." --description "..." --tag "film analysis" --tag "visual storytelling"`

Do not edit `automation/queue.json` by hand. The GitHub production workflow owns
validation, private upload and scheduled publication. Never print or request
YouTube credentials.

HANDOFF
The first line must be the exact absolute output file path in plain text, then
a clickable link. The user should never need to ask for the location. State
duration, the useful premise, completed checks and any material limitation.
If pipeline-only, instead give the actual pipeline/prompt locations and state
that no video was generated. If blocked, name the exact missing asset or review
capability; never hand off an unrelated montage as a finished reel.

After publication only when authorized, use the measurement protocol in
RESEARCH.md. Compare comparable episodes, preserve metric denominators, and
test one editorial variable. Do not invent a universal viral threshold.
