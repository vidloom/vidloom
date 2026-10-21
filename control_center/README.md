# Vidloom Control Center

Responsive owner console for the private Vidloom production system. Cloudflare
Workers serves the interface and a protected API; GitHub Actions and the Fedora
self-hosted runner perform production work.

The browser never receives a GitHub credential. After password sign-in it gets
an HttpOnly, SameSite session cookie. The Worker reads studio state, dispatches
workflows, and writes validated queue changes with an encrypted server-side
secret. Upload remains separately gated by evidence validation, AI editorial
pass, technical QC, and the reviewed render hash.

Static layout preview:

```bash
python3 -m automation.dashboard_state --output control_center/data/dashboard.json
python3 -m http.server 4173 --directory control_center
```

Worker source and deployment instructions are in `cloudflare-control/`.
Production setup is documented in `automation/SETUP.md`.
