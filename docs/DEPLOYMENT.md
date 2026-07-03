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
