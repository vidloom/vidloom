# Vidloom premium pipeline

**New projects: use [v3](v3/README.md) and its [Gemini prompt](v3/GEMINI_PROMPT.md).**
The older renderer below is retained for historical projects. Its weighted shot
timing and per-line TTS do not enforce semantic synchronization or natural
continuous narration. Do not use the old recipe example as a quality reference.

The pipeline separates editorial judgment from rendering. An AI fills a strict
`project.json`; the renderer turns that manifest into a mastered 9:16 video.

## Render the included Interstellar example

```bash
python3 premium_pipeline/render_project.py \
  premium_pipeline/projects/interstellar_docking
```

Reuse an existing narration while changing visuals or sound:

```bash
python3 premium_pipeline/render_project.py \
  premium_pipeline/projects/interstellar_docking --reuse-voice
```

The engine provides:

- Kokoro offline narration with an Edge fallback
- line-specific pacing and exact beat timing
- semantic phrase captions with controlled emphasis
- per-shot moving vertical reframes
- retained production audio
- multiple intentional music layers
- timed impacts, whooshes, and lock effects
- narration-driven side-chain ducking
- -14 LUFS / -1.2 dBTP mastering
- H.264 delivery, contact-sheet inspection, ffprobe and loudness reports

For a new film, copy the example project, replace the licensed inputs, and edit
the manifest. Follow `AI_EDITOR_CONTRACT.md`; it is the quality gate that stops
generic scripts and arbitrary effect spam from reaching the renderer.

Movie footage and commercial scores in the example are private prototype inputs,
not publication rights.
