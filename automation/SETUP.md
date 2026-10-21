# Vidloom control center deployment

The application is complete locally, but it intentionally starts paused. Do not
paste keys into source files or chat. Put them in GitHub Actions encrypted
secrets.

## 1. Create the GitHub repository

Create a **private** repository. A self-hosted runner must not execute pull
request code from a public repository. If your GitHub plan cannot publish Pages
from a private repository, use GitHub Pro or split the public static dashboard
from the private production repository; do not make the production runner public.

From the repository root:

```bash
git init
git branch -M main
git remote add origin git@github.com:OWNER/REPO.git
git add .
git commit -m "build: add Vidloom control center"
git push -u origin main
```

In GitHub, open **Settings → Pages → Build and deployment** and select **GitHub
Actions**. The `Deploy control center` workflow publishes `control_center/`.

## 2. Register the production machine

Open **Settings → Actions → Runners → New self-hosted runner**. Follow GitHub's
Linux commands on this machine, then add the custom runner label `vidloom`.
Install the runner as a service so scheduled work survives logout.

Create this repository variable under **Settings → Secrets and variables →
Actions → Variables**:

```text
VIDLOOM_MEDIA_ROOT=/home/omie/MyShits/Youtube Automation - Vidloom
```

The workflow copies missing project media from that persistent directory into
its isolated checkout. Models and large output files remain on the machine and
are not committed to GitHub.

## 3. Connect YouTube

In Google Cloud Console:

1. Create/select a project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen for your Google account.
3. Create an OAuth 2.0 **Desktop app** client and download its JSON file.
4. Install the GitHub CLI, authenticate it with `gh auth login`, then run. On
   Fedora the packaged installation command is `sudo dnf install gh`; a local
   install at `~/.local/bin/gh` also works.

```bash
python3 -m venv .venv-automation
.venv-automation/bin/pip install -r automation/requirements.txt
.venv-automation/bin/python -m automation.oauth_setup
```

To authorize in a different browser or browser profile, pass
`--no-open-browser`; the helper prints a URL that can be copied anywhere on the
same machine:

```bash
.venv-automation/bin/python -m automation.oauth_setup \
  --repo OWNER/REPO \
  --client-json /absolute/path/to/client_secret.json \
  --no-open-browser
```

The helper opens Google's consent page and sends the client ID, client secret
and refresh token directly to these repository secrets without storing them:

```text
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN
```

## 4. Deploy the private website controls

The production console is a Cloudflare Worker. GitHub Pages remains only a
static fallback. From the project root, use Cloudflare's browser login and set
three hidden Worker secrets:

```bash
cd cloudflare-control
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put CONTROL_PASSWORD
npx wrangler secret put SESSION_SECRET
npm run deploy
```

Use a fine-grained GitHub token limited to only `vidloom/vidloom` with:

```text
Actions: write
Contents: write
Metadata: read
```

The token is encrypted by Cloudflare and never reaches browser JavaScript.
`CONTROL_PASSWORD` is the password used to unlock the owner console.
`SESSION_SECRET` must be a random 32+ byte value.

For automatic website deployment on future pushes, create a Cloudflare API
token from the **Edit Cloudflare Workers** template and save it as the GitHub
Actions secret `CLOUDFLARE_API_TOKEN`. The non-secret account ID belongs in the
repository variable `CLOUDFLARE_ACCOUNT_ID`. The workflow is:

```text
.github/workflows/deploy-cloudflare.yml
```

## 5. Test, then go live

Run `Production cycle` manually with `dry_run=true`. It must validate the v3
project, re-run QC and verify that `FINAL_REVIEW.md` contains the exact MP4 hash.
No upload occurs during a dry run.

When the dry run passes, use the dashboard's **Resume automation** control. The
schedule then runs Tuesday, Thursday and Saturday at 17:47 IST and asks YouTube
to publish the private upload at 19:30 IST.

Never enable the schedule with fewer than three reviewed projects in the queue.
The dashboard marks low coverage, but it does not manufacture filler content.

If an upload fails after data transfer begins, check YouTube Studio before
retrying that item. Automatic selection skips failed items so a lost API response
cannot silently create a duplicate upload.
