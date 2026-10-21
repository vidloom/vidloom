# Vidloom Premium V2 — Top Gun reference edit

This folder is a hand-authored quality target for the automation system. It is
not meant to be a one-off replacement for the generic pipeline; it demonstrates
the editorial decisions that the future pipeline must represent as structured
data.

## Build

```bash
python3 movie_shorts/premium_v2/build_premium_topgun.py
```

After the first build, reuse the generated narration to iterate faster:

```bash
python3 movie_shorts/premium_v2/build_premium_topgun.py --reuse-voice
```

Output: `output/vidloom_topgun_premium_v2.mp4`

## What changed from V1

- An 11-word premise hook and a cold-open impact frame replace the slow setup.
- Twenty short, contrasting shots replace ten long literal scene chunks.
- Every crop can move during the shot; this is a real reframe track, not a fixed
  per-shot crop pretending to be subject tracking.
- Captions arrive as short semantic phrases, pop on entry, use a single accent
  colour, and stay inside mobile UI-safe margins.
- Production audio from every selected shot is retained under the narration.
- The score and production bed are side-chain ducked by the voice.
- The final mix is mastered to -14 LUFS / -1.2 dBTP instead of peak-normalized.
- The build emits probe, loudness, and contact-sheet QC artifacts.

## Rights note

The movie footage and studio score in `assets/` are retained only for the
owner's private prototype/comparison. Do not publish or commercialize this
sample without the necessary rights. The production system should use licensed,
commissioned, public-domain, or creator-owned visual and music inputs.
