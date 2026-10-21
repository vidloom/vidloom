# Verification record — 2026-10-21

- 26 regression tests passed with `python3 -m unittest discover -s premium_pipeline/v3/tests -v`.
- Empty project template failed validation as intended; it is not a fake approved example.
- Python modules compiled successfully.
- Existing-media FFmpeg filter smoke test passed for silent footage plus continuous
  narration, explicit frame cuts, captions, ducking and normalization.
- A second existing-media smoke test passed for production audio, 1.5x `atempo`,
  an explicitly timed music event, captions, ducking and normalization.
- Both smoke tests used FFmpeg's null sink. No video file was rendered or saved.
- The current host has libopenh264 and h264_nvenc encoders, but not libx264.
  The CLI defaults to libopenh264; GPU encoding remains an explicit selection.

Not validated in this task: a newly generated voice performance, end-to-end
encoded v3 MP4/AAC quality, real project semantic accuracy, provider API
integration, WhisperX installation on this host, actual mobile UI clearance,
or audience performance. Those require future production and actual inspection.
Technical checks are not an editorial approval or a ranking prediction.

Original projects and rendered videos were preserved. The parent README and
historical contract now direct new production to v3.
