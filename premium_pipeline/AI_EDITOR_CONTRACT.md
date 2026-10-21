# Vidloom premium editor contract

Historical v1/v2 contract. New work follows
[the v3 playbook](v3/EDITORIAL_PLAYBOOK.md). In particular, fixed shot-count,
fixed duration, mandatory micro-pauses and sentence-by-sentence synthesis are
not v3 quality requirements.

An AI editor must create or modify only `project.json`. It should never invent
render commands or bypass the quality-controlled renderer.

## Story gate

Before editing, the AI must be able to state the video's value in one sentence.
The script must teach, reveal, reframe, or emotionally resolve something. A list
of escalating adjectives is not a story.

- Hook: subject plus contradiction in 6–12 spoken words.
- Context: only facts required to understand the danger.
- Mechanism: explain what the character actually does.
- Escalation: introduce the cost of failure after the mechanism is clear.
- Payoff: resolve the exact question opened by the hook.
- Ban: “you won't believe,” “humanity's last hope,” “greatest ever,” “insane,”
  and unsupported superlatives.
- Target: 55–75 words and 20–32 seconds. Never stretch a weak idea to fit.

Read the script aloud. If it sounds like a trailer announcer, rewrite it as one
smart person urgently explaining something to another.

## Visual gate

- The opening frame must show consequence, motion, or an unanswered visual.
- Every shot must add information, scale, emotion, mechanism, or payoff.
- Use 16–28 shots per 25 seconds, but hold longer when comprehension needs it.
- `crop_start` and `crop_end` must follow the subject; they are not decoration.
- Detect and remove baked-in letterboxing with `edit.active_crop` before any
  vertical scale or reframe.
- Captions contain 1–5 words per phrase, one highlighted idea, and no transcript
  paragraphs.
- Keep text away from the right-side buttons and bottom description overlay.
- Effects must clarify a beat. No random glitch packs or transition spam.

## Sound gate

- Narration is intimate and conversational, never an announcer impression.
- Preserve scene audio at low level so images retain physical reality.
- One tension bed and one score arc maximum; transition between them intentionally.
- Add impacts only to genuine impacts. Add whooshes only to motivated movement.
- Side-chain all beds under narration.
- Master delivery to approximately -14 LUFS and no higher than -1 dBTP.

## Manifest gate

- Every asset path must exist before rendering.
- Shot weights must be positive and crop values must remain between 0 and 1.
- The final narration must end 0.25–0.65 seconds before the video.
- Run the generated contact sheet, loudness report, and full decode check.
- Reject the result if captions collide with faces or UI, if a crop loses the
  subject, or if any shot is present only because it “looks cinematic.”
