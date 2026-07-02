# CI/CD & Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automated test workflows for both backend and mobile on every PR, document the deployment process, and bring `docs/ROADMAP.md` up to date with everything Plans 1-3 actually delivered.

**Architecture:** Two independent GitHub Actions workflows, each path-filtered so backend changes don't trigger mobile CI and vice versa. No deploy automation in Actions — Vercel's Git integration (a one-time dashboard connection, not a file in this repo) handles preview/production deploys; Actions is test-only.

**Tech Stack:** GitHub Actions, existing `pytest` (backend) and `flutter test`/`flutter analyze` (mobile) — no new testing frameworks.

## Global Constraints

- Backend CI must run with fake providers only (`USE_REAL_PROVIDERS` unset) — no `GROQ_API_KEY` secret required in CI, matching the existing test suite's design (32+ tests pass with zero external calls).
- Mobile CI must not require code-signing, simulators, or a physical device — `flutter test`/`flutter analyze` run headless.
- One commit per logical file change.

---

## Task 1: Backend CI workflow

**Files:**
- Create: `.github/workflows/backend-ci.yml`

**Interfaces:**
- Consumes: `backend/pyproject.toml` (installs via `pip install -e ".[dev]"`).
- Produces: a GitHub Actions check that runs on every push/PR touching `backend/**`.

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/backend-ci.yml`:

```yaml
name: Backend CI

on:
  push:
    branches: [main]
    paths:
      - "backend/**"
      - ".github/workflows/backend-ci.yml"
  pull_request:
    paths:
      - "backend/**"
      - ".github/workflows/backend-ci.yml"

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: python3 -m pytest -v
```

- [ ] **Step 2: Verify the YAML is well-formed**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/backend-ci.yml'))"`
Expected: no output (no exception raised means valid YAML). If `pyyaml` isn't installed, run `pip install pyyaml` first (dev-machine only, not a project dependency).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/backend-ci.yml
git commit -m "$(cat <<'EOF'
ci: add backend GitHub Actions workflow

Runs pytest against fake providers only (no GROQ_API_KEY secret
needed) on every push/PR touching backend/. Path-filtered so mobile
changes don't trigger this workflow.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Mobile CI workflow

**Files:**
- Create: `.github/workflows/mobile-ci.yml`

**Interfaces:**
- Consumes: `mobile/pubspec.yaml` (resolves via `flutter pub get`).
- Produces: a GitHub Actions check that runs on every push/PR touching `mobile/**`.

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/mobile-ci.yml`:

```yaml
name: Mobile CI

on:
  push:
    branches: [main]
    paths:
      - "mobile/**"
      - ".github/workflows/mobile-ci.yml"
  pull_request:
    paths:
      - "mobile/**"
      - ".github/workflows/mobile-ci.yml"

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: mobile
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: "3.44.4"
          channel: "stable"
      - name: Install dependencies
        run: flutter pub get
      - name: Analyze
        run: flutter analyze
      - name: Run tests
        run: flutter test
```

- [ ] **Step 2: Verify the YAML is well-formed**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/mobile-ci.yml'))"`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/mobile-ci.yml
git commit -m "$(cat <<'EOF'
ci: add mobile GitHub Actions workflow

Runs flutter analyze + flutter test headlessly (no simulator, no
code-signing needed) on every push/PR touching mobile/. Path-filtered
so backend changes don't trigger this workflow.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Deployment documentation

**Files:**
- Create: `docs/DEPLOYMENT.md`

**Interfaces:**
- Consumes: nothing (documentation only).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write `docs/DEPLOYMENT.md`**

Create `docs/DEPLOYMENT.md`:

```markdown
# DEPLOYMENT

## Backend (Vercel)

The backend deploys to Vercel's Python runtime. See the root [README.md](../README.md#deployment) for the full step-by-step (one-time setup, environment variables, deploy, verification, local pre-deploy checks with `vercel dev`).

**Current production URL:** `https://backend-mu-azure-ghm6imsjg1.vercel.app`

### Redeploying after a change

```bash
cd backend
vercel deploy --prod
```

Always verify afterward:

```bash
curl https://backend-mu-azure-ghm6imsjg1.vercel.app/health
```

### CI vs. Deploy

GitHub Actions (`.github/workflows/backend-ci.yml`, `.github/workflows/mobile-ci.yml`) run tests only — they do not deploy anything. Deploys are manual via the Vercel CLI today.

**Recommended next step (manual, one-time, not automated by this repo):** connect this GitHub repository to the Vercel project via the [Vercel dashboard](https://vercel.com/dashboard) → Project Settings → Git, so pushes to `main` auto-deploy to production and PRs get preview URLs automatically. This requires a human with dashboard access; it is not a file-based change these workflows can make.

## Mobile

Not yet deployed to any app store (this is an active POC). Local development:

```bash
cd mobile
flutter pub get
flutter run --dart-define=BACKEND_URL=https://backend-mu-azure-ghm6imsjg1.vercel.app
```

See the root [README.md](../README.md#getting-started--mobile) for full setup, including physical-device testing steps (camera/microphone require real hardware; the iOS Simulator and Android Emulator have no camera/mic and will show "Could not access the camera" / "Could not start recording" errors on the hold-to-ask gesture — this is expected, not a bug).
```

- [ ] **Step 2: Verify the file references real, existing anchors**

Run: `grep -n "## Deployment\|## Getting Started — Mobile" README.md`
Expected: both headings exist in the root README (confirms the cross-links in DEPLOYMENT.md resolve to real sections).

- [ ] **Step 3: Commit**

```bash
git add docs/DEPLOYMENT.md
git commit -m "$(cat <<'EOF'
docs: add DEPLOYMENT.md

Backend redeploy steps, CI-vs-deploy distinction, and a pointer to
connecting Vercel's Git integration (a one-time manual dashboard
step, not something these GitHub Actions workflows do). Mobile
section notes that Simulator/Emulator have no camera/mic hardware --
the "Could not access the camera" error there is expected, not a bug.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Update ROADMAP.md for Plan 3 completion

**Files:**
- Modify: `docs/ROADMAP.md`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing consumed by later tasks.

**Context:** `docs/ROADMAP.md`'s `### Done` list (under `## Current Status`) and Progress Tracker table currently reflect the state after Plan 1 (backend deployed, TTS verified). This task adds the Plan 3 outcomes: vision-task routing (currency/color/product/scene), grounding wired in, client-carried history, and the Arabic-keyword fix.

- [ ] **Step 1: Read the current file to get exact line numbers**

Run: `grep -n "^### Done\|^## Progress Tracker\|Provider adapters" docs/ROADMAP.md`

Use the output to locate the end of the `### Done` numbered list and the `Provider adapters` row of the Progress Tracker table before editing — do not guess line numbers, they may have shifted since this plan was written.

- [ ] **Step 2: Append a new item to the `### Done` list**

Add a new numbered item at the end of the list (after the Vercel deployment item), continuing the existing numbering:

```markdown
12. Vision-task routing (currency, color, product, scene) and object-finder grounding are wired into ConversationService, with Arabic keyword support (this app's ASR defaults to Arabic) verified live end-to-end via real Groq TTS/ASR round-trips.
```

- [ ] **Step 3: Update the Progress Tracker table's "Provider adapters" row**

Change the Notes cell from `Groq-backed Vision, OCR, Grounding, LLM, ASR, and TTS adapters are in code; real mode is config-driven.` to:

```markdown
Groq-backed Vision, OCR, Grounding, LLM, ASR, and TTS adapters are in code and wired into ConversationService; real mode is config-driven. Vision-task routing (currency/color/product/scene) and grounding support both English and Arabic keywords, verified live.
```

- [ ] **Step 4: Verify**

Run: `grep -n "Arabic" docs/ROADMAP.md`
Expected: at least two matches (the new Done item and the updated table row).

- [ ] **Step 5: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "$(cat <<'EOF'
docs: reflect Plan 3 completion in roadmap

Vision-task routing, grounding wiring, client history, and the
Arabic-keyword routing fix are now documented as done.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Definition of Done

- [ ] `.github/workflows/backend-ci.yml` and `.github/workflows/mobile-ci.yml` exist and are valid YAML.
- [ ] `docs/DEPLOYMENT.md` exists and cross-references resolve to real README sections.
- [ ] `docs/ROADMAP.md` reflects Plan 3's actual outcomes, including the Arabic-keyword fix.
- [ ] Every task is committed as its own commit.
