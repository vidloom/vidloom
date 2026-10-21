# Vidloom control plane

Cloudflare Worker backend and static asset host for the private Vidloom owner dashboard.

It keeps the GitHub credential server-side, signs an HttpOnly owner session, proxies live state and workflow runs, dispatches safe production actions, and commits validated queue items. No browser token is used.

Required Worker secrets:

- `GITHUB_TOKEN`: fine-grained token for only `vidloom/vidloom`; Actions read/write and Contents read/write.
- `CONTROL_PASSWORD`: the dashboard password.
- `SESSION_SECRET`: random 32+ byte value used only to sign sessions.

Local checks:

```bash
cd cloudflare-control
npm install
npm run check
```

Deployment uses browser login, then hidden secret prompts:

```bash
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put CONTROL_PASSWORD
npx wrangler secret put SESSION_SECRET
npm run deploy
```
