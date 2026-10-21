# Research and failure analysis

Research date: 2026-10-21. Sources below were opened/read or retrieved as
primary-source search excerpts. This is a synthesis of platform documentation,
creator interviews and engineering references, not a causal study of viral videos.
No new Short was produced for this work. No claim is made to have watched a
representative sample of million-view Shorts or accessed their private retention.

## What the previous pipeline actually got wrong

1. `assets/pan_crisp.mp4` in the potato project is Pexels 10432188. The
   [source describes scallops](https://www.pexels.com/video/a-person-cooking-seafood-10432188/).
   It appeared as potato evidence in the hook and payoff. Renaming an asset did
   not verify its contents. This was our editorial mistake.
2. `build_filter()` distributed every shot as `total * weight / sum(weights)`.
   Speech beats never controlled the corresponding cut boundaries. Consequently
   narration about one operation could play over another operation.
3. `build_voice()` synthesized each beat separately, trimmed both edges, and
   inserted the same pause. Voice identity was acceptable; phrase continuity was
   lost. Fix the performance unit, not merely the voice name.
4. `build_captions()` divided each beat by caption word count. That was estimated
   timing, not alignment to the recording.
5. The recipe claimed a texture, process and finished result without recordings
   establishing the complete transformation. Synthetic crunch did not establish
   that the actual food was crunchy. The 15-minute heading was unverified.
6. `asetpts` was used for speed-adjusted source audio; proper tempo processing
   requires an audio tempo filter. Visual speed and audio speed were not reliably
   coupled.
7. Full decode, 1080p and loudness passed. Those checks established technical
   delivery only. Calling the result premium based on them was unjustified.

## Evidence register

| Source | What it supports | Consequence for this pipeline |
| --- | --- | --- |
| [YouTube: Shorts search and discovery](https://support.google.com/youtube/answer/11914225?co=YOUTUBE._YTVideoType%3Dshorts&hl=en) | Personalization; chose-to-view, average duration, percentage viewed, likes and surveys; topic demand and competition; no required posting cadence | Define a viewer and valuable promise. Do not score a project by effect count or claim a guaranteed ranking. |
| [YouTube: Todd Sherman / Jenny Hoyos interview](https://blog.youtube/creator-and-artist-stories/youtube-shorts-deep-dive/) (2025-01-28) | Hoyos emphasizes the first second and compact stories; discussion distinguishes feed discovery from channel presentation | Audit the first visible frame and the unresolved question. Treat this as creator practice, not a one-second algorithm rule. |
| [YouTube: Cracking the code, part 2](https://blog.youtube/creator-and-artist-stories/cracking-the-code-to-youtube-shorts-part-2/) (2026-01-22) | Ivy Febriany reports a 20M-view soba video and stresses clarity, delivery and sensory presentation; Sebastian Tedy stresses distinct personal interests | Build a repeatable editorial point of view and a complete payoff. This is an interview/self-report, not a frame-by-frame analysis or controlled experiment. |
| [YouTube: 2021 top creators](https://blog.youtube/culture-and-trends/2021s-top-trending-videos-and-creators/) | Food creators including Nick DiGiovanni and Lisa Nguyen appear in the US Shorts creator list | Evidence that food can support large audiences, not evidence that a particular food montage will work today. Historical chart; not a current top-100 benchmark. |
| [YouTube: content performance definitions](https://support.google.com/youtube/answer/12220281?co=GENIE.Platform%3DDesktop&hl=en) | Engaged views exclude loops; Shorts average duration and percentage viewed use engaged views and their watch time | Preserve denominators, snapshot dates and traffic source in experiment records. Do not mix raw plays with engaged views. |
| [YouTube: audience retention](https://support.google.com/youtube/answer/9314415?hl=en) | Spikes may indicate interest or confusion; dips indicate skipped/abandoned portions; some key-moment features require sufficient length and views | Watch the actual segment before interpreting a spike. Do not promise 30-second Shorts will expose all long-form analytics features. |
| [Google: Gemini video understanding](https://ai.google.dev/gemini-api/docs/video-understanding.md) | Default static sampling is 1 FPS and can miss fast action | Review short action ranges at higher sampling and inspect boundary frames. Do not certify knife contact, crunch or a latch from one thumbnail. |
| [Google: structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) | JSON schema can constrain output shape | Use a strict interchange schema plus semantic validation. Valid JSON does not establish truthful observations or good taste. |
| [Google: speech generation](https://ai.google.dev/gemini-api/docs/speech-generation) | Voice and delivery controls exist, with model/API-version-specific fields | Read current provider documentation before using a model. Keep delivery directions separate from spoken words using the supported interface. Never silently substitute voices. |
| [WhisperX repository](https://github.com/m-bain/whisperX) | Word-level alignment and known missing-alignment limitations | Align the accepted recording. Import measured timestamps; stop on missing words instead of distributing time by word count. |
| [Kokoro ONNX repository](https://github.com/thewh1teagle/kokoro-onnx) | Local text-to-waveform inference interface | Provide the complete connected script in a single create call. Internal model chunking can still occur; listen to the output. |
| [FFmpeg filters reference](https://www.ffmpeg.org/ffmpeg-filters.html) | `atempo`, `crop`, `trim`, `sidechaincompress`, `loudnorm` behavior | Frame-based explicit edits; correctly retimed source audio; measured final loudness rather than peak-only normalization. |

## What is an engineering/editorial choice, not research fact

The following defaults are house heuristics: a useful first-frame question;
three inspected subject boxes per shot; a conservative safe region; captions
of roughly 2–6 words; a 24-character/second readability ceiling; -16 LUFS mix
target; minimum 0.35-second caption exposure; 30 FPS delivery. They are editable
design decisions, not YouTube ranking requirements. Timing checks may require
language-specific tuning. Demonstration continuity is deliberately strict.

There is no documented universal minimum retention percentage, ideal cut count,
mandatory 120ms sentence pause, perfect 25-second length, guaranteed hashtag,
or LUFS setting that creates a viral video. A good replay is useful; a confusing
edit can also be replayed. A high APV on a very short clip is not directly
comparable with a longer tutorial. Public views cannot reveal causation.

## Research protocol for each future format

Before producing a series, build a small reference set: six strong examples and
six ordinary examples from the same topic/language/duration band, including small
channels. This is a practical sampling plan, not statistical proof. Record URL,
date inspected, upload age, public counts if visible, and what was actually
watched. Keep creator authority and topic demand as confounders.

Annotate the first frame, first audible line, central question, first evidence,
new information per beat, comprehension holds, payoff, and ending. Mark unseen
items UNKNOWN. Extract a transferable mechanism, not a copied script, costume,
catchphrase or edit. Example hypothesis: showing a side-by-side failure/result
may improve initial understanding. Test it against the channel's comparable work.

## Measurement loop

Create records at roughly 24h, 72h and 7d when data is available; these are
observation windows, not mandatory algorithm evaluation periods. Compare
same-language, similar-length, similar-topic Shorts at similar upload age and
traffic source. Use rolling median and spread of comparable uploads, not a
cherry-picked million-view outlier. Track raw plays separately from engaged
views, stayed-to-watch, AVD, APV, shares per engaged view, subscriptions per
engaged view, and comments indicating usefulness/confusion.

Change one editorial variable between comparable episodes. Organic posting is
not randomized A/B testing; audience and topic differences can explain outcomes.
Low stayed-to-watch suggests testing subject/promise clarity; early drop after a
strong opening suggests the promise wasn't being fulfilled; drop at instructions
suggests mismatch, overload or missing steps. Low reach with otherwise strong
signals can reflect competition or demand. Do not diagnose a hidden penalty.

Define any future top-100 goal by category, geography, time window and metric.
Until that exists, use verified craft quality and improving audience outcomes;
do not manufacture a leaderboard or a probability of virality.
