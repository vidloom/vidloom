# Vidloom automation

This directory is the control plane between a completed v3 Short and YouTube.
It never weakens the editorial pipeline to fill a release slot.

Flow:

```text
Gemini/coding agent builds one reviewed v3 project
  → automation.enqueue adds it to the locked-genre queue
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

`--force` exists for an explicit local/manual dry run while the global switch is
paused. Scheduled GitHub runs never use it.
