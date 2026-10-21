# Vidloom automation

This directory is the control plane between a completed v3 Short and YouTube.
It never weakens the editorial pipeline to fill a release slot.

Flow:

```text
Coding agent builds one reviewed v3 project
  → automation.enqueue adds it to the locked-genre queue
  → Groq audits the script against declared observations and shots
  → GitHub Actions selects one ready item
  → v3 validation + render/QC + exact review-hash verification
  → resumable private YouTube upload
  → YouTube publishes at the selected slot
  → public, secret-free dashboard state is redeployed
```

Useful local commands:

```bash
python3 -m automation.dashboard_state --output control_center/data/dashboard.json
python3 -m automation.production --mode upload --item-id jack-sparrow-entrance-001 --dry-run --force
python3 -m unittest discover -s automation/tests -v
```

Groq is a backend editorial checker, not a source of fake timestamps. It receives
the project's brief, script, beats, inspected observations and shot bindings,
then writes a schema-constrained audit to `automation/state/ai.json`. The API
key exists only as the `GROQ_API_KEY` Actions secret. The production cycle caches
audits by project digest and requires a `pass` verdict; deterministic
validation, recorded word alignment, QC and the hash-bound final review remain
mandatory.

`--force` exists for an explicit local/manual dry run while the global switch is
paused. Scheduled GitHub runs never use it.
