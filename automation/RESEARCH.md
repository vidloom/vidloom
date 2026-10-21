# Automation decisions and evidence

Research date: 2026-10-21. Only primary platform documentation is used here.
This document records platform constraints; it does not claim that a posting
time or automation system can guarantee distribution.

## Channel format

The system is locked to **cinema scene breakdowns**: one scene, one original
observation about craft, visible evidence, and a complete payoff. Plot recaps,
clip dumps and generic movie facts are rejected. This preserves a coherent
viewer promise while requiring meaningful variation in the substance of every
episode.

YouTube says monetized content should be original and authentic rather than
mass-produced or repetitive. It lists critical reviews and transformed scenes
with substantive commentary as examples that may be allowed under its reused
content policy, while warning that copyright rules still apply separately:
https://support.google.com/youtube/answer/1311392

That is why a technical render pass is insufficient. Every queued project must
also contain evidence reviews and a `FINAL_REVIEW.md` matching the exact rendered
file hash. This is a quality gate, not a legal determination. The rights holder
can still claim or block film footage.

## Schedule

Initial release slots are Tuesday, Thursday and Saturday at 19:30 Asia/Kolkata.
The corresponding workflow starts at 12:17 UTC (17:47 IST), giving the runner
103 minutes to validate, render if necessary, QC and upload the video privately.
YouTube then publishes at the exact scheduled timestamp.

Three weekly releases are a sustainable starting hypothesis, not a universal
best time. YouTube's own guidance emphasizes a consistent, sustainable schedule:
https://support.google.com/youtube/answer/13616979

After at least 28 days, use the channel's Audience report—specifically “When
your viewers are on YouTube”—to reconsider the time:
https://support.google.com/youtube/answer/9314416

The GitHub cron runs at minute 17 because GitHub documents that scheduled jobs
may be delayed during high load, especially at the start of an hour. Scheduled
workflows also need to exist on the default branch:
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

## Upload behavior

Uploads use OAuth 2.0 with `youtube.upload` plus the read-only scope needed to
verify processing/publication state, and an offline refresh token. YouTube does
not support service accounts for user channel data:
https://developers.google.com/youtube/v3/guides/authentication

Videos are uploaded as private with `status.publishAt`. The API documents that
scheduled publication requires private status and a video that has never been
published:
https://developers.google.com/youtube/data/reference/rest/v3/videos

The uploader uses resumable 8 MiB chunks and bounded retry for transient server
or network failures. A six-hour status job checks the real privacy and processing
state instead of assuming that a scheduled video published successfully. It
stores only the resulting video ID and public URL.

## GitHub hosting and security

The dashboard is a static GitHub Pages artifact. GitHub documents custom Pages
deployment through `configure-pages`, `upload-pages-artifact` and `deploy-pages`:
https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

The media pipeline runs on a self-hosted Linux runner because it needs the
local models, FFmpeg/NVENC and the persistent media library. Keep the production
repository private. GitHub warns that public-repository pull requests can
compromise a self-hosted runner and its secrets:
https://docs.github.com/en/actions/reference/security/secure-use#hardening-for-self-hosted-runners

The Pages dashboard contains no secrets. Optional direct controls require a
short-lived, repository-scoped fine-grained token. It is kept in browser
`sessionStorage`, disappears when the tab session ends and is never written to
the repository. The safer fallback is to use the linked GitHub Actions page.
