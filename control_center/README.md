# Vidloom Control Center

Static, responsive operations dashboard for the private Vidloom production
system. GitHub Pages hosts these files; the page reads only the generated,
secret-free `data/dashboard.json` snapshot.

Direct controls call GitHub's workflow-dispatch API. The optional fine-grained
token is held in `sessionStorage` for the current browser tab and is never
written into the site, repository or dashboard state. Without a token, controls
open the authenticated workflow page on GitHub.

Local preview:

```bash
python3 -m automation.dashboard_state --output control_center/data/dashboard.json
python3 -m http.server 4173 --directory control_center
```

Production setup is documented in `automation/SETUP.md`.
