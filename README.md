# Be My Eye

An AI-powered voice assistant that helps blind and low-vision users understand and interact with their surroundings. Point a phone camera at a scene, ask a question out loud, and get a concise, natural spoken answer — powered by a Vision-Language Model, speech recognition, and text-to-speech, all orchestrated by a backend that keeps AI providers swappable behind stable interfaces.

> **Design philosophy:** conversation over image captioning. The assistant answers the user's *intent* ("Can I drink this?"), not just describes pixels ("a bottle is present").

## Table of Contents

- [Key Features](#key-features)
- [Project Status](#project-status)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started — Backend](#getting-started--backend)
- [Getting Started — Mobile](#getting-started--mobile)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Available Scripts](#available-scripts)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Documentation Map](#documentation-map)

## Key Features

- **Scene understanding** — "What's in front of me?" answered from the latest camera frame.
- **Object questions** — "Can I drink this?" answered with intent, not a generic description.
- **Currency reader** — "How much is this?" identifies banknote denominations.
- **Color detector** — "What color is this?" describes the color of an object.
- **Product identifier** — "What am I holding?" reads brand/label context from packaging.
- **Object finder (grounding)** — "Where are my keys?" locates an object within the frame.
- **Text reading (OCR)** — "Read this page" extracts and reads visible text aloud.
- **Multi-turn conversation memory** — short-term history so follow-ups ("Is it open?") resolve naturally.
- **Fully voice-driven, bilingual** — spoken input in (English or Arabic), spoken response out, no typing required.
- **Provider-based architecture** — every AI capability (ASR, Vision, OCR, LLM, TTS, Grounding) sits behind a stable interface, so any model or vendor can be swapped without touching application logic.

## Project Status

This is an active proof-of-concept. Be honest with yourself about what's real before you rely on it:

| Component | Status |
| --- | --- |
| Backend (FastAPI) | **Working, tested, deployed** — live on Vercel with real Groq providers |
| Backend test suite | **Green** — 54 passed, 1 skipped (real-mode smoke test is env-gated) |
| Mobile app (Flutter) | **Working** — full app implemented (capture, playback, conversation state, Stitch-designed hold-to-ask screen), 20/20 tests passing, verified running live on an iOS Simulator |
| Vision-task routing + grounding | **Working** — currency/color/product/scene routing and object-finder grounding, with Arabic keyword support (this app's ASR defaults to Arabic), verified live end-to-end |
| `/conversation` end-to-end | **Fully verified live** — ASR → routing → Vision/OCR/Grounding → LLM → TTS all confirmed working against real Groq APIs |
| CI/CD | **Set up** — GitHub Actions run backend `pytest` and mobile `flutter analyze && flutter test` on every PR; deploys remain manual via the Vercel CLI |

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full phased plan and [`docs/superpowers/plans/`](docs/superpowers/plans/) for the detailed, task-by-task implementation plans driving this work.

## Tech Stack

**Backend**
- **Language:** Python 3.11+ (deployed with 3.13)
- **Framework:** FastAPI
- **AI Provider:** [Groq](https://console.groq.com) — Vision-Language Model, Whisper (ASR), and TTS, all behind provider interfaces
- **Validation:** Pydantic v2
- **Image handling:** Pillow
- **Server:** Uvicorn (local dev)
- **Deployment:** Vercel (Python / Fluid Compute runtime)

**Mobile**
- **Framework:** Flutter (Dart SDK ≥3.8.0)
- **State management:** `provider` (`ChangeNotifier`-based `ConversationState`)
- **Camera:** `camera`
- **Audio:** `record` (capture), `just_audio` (playback)
- **Networking:** `http`
- **Permissions:** `permission_handler`
- **Image compression:** `image`
- **Fonts:** `google_fonts`

## Prerequisites

- **Python 3.11 or higher** (backend)
- **A [Groq API key](https://console.groq.com/keys)** (for real AI responses; a fake-provider mode exists for development without one)
- **[Vercel CLI](https://vercel.com/docs/cli)** — `npm i -g vercel` (only needed if you're deploying)
- **Flutter SDK ≥3.8.0** — for the mobile app; not required to run the backend
- **Xcode or Android Studio** — for iOS Simulator / Android Emulator or physical-device testing (camera and microphone require real hardware; simulators/emulators have neither)

## Getting Started — Backend

### 1. Clone the Repository

```bash
git clone https://github.com/Ahmed-Aboalasaad/be-my-eye.git
cd be-my-eye
```

### 2. Install Python Dependencies

From the `backend/` directory:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

This installs FastAPI, Groq's SDK, Pydantic, Pillow, Uvicorn, and pytest (via the `dev` extra defined in `pyproject.toml`).

### 3. Environment Setup (Optional — for Real AI Responses)

By default, the backend runs in **fake-provider mode**: every AI capability (ASR, Vision, OCR, LLM, TTS) returns deterministic, canned responses. This is enough to explore the API and run the full test suite without any credentials.

To use real Groq models, create a `.env` file at the **repository root** (checked by `backend/app/core/config.py`, which also checks `backend/.env` if run from that directory):

```bash
USE_REAL_PROVIDERS=true
GROQ_API_KEY=your_groq_api_key_here
GROQ_MULTIMODAL_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

See [Environment Variables](#environment-variables) below for the full list and defaults.

### 4. Run the Development Server

```bash
cd backend
uvicorn app.main:app --reload
```

The API is now available at [http://localhost:8000](http://localhost:8000). Check it's alive:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 5. Try the Conversation Endpoint

The backend exposes a single endpoint, `POST /conversation`, which accepts a base64-encoded image, base64-encoded audio, and a session ID, and returns a spoken response (also base64-encoded). See [`docs/API_SPEC.md`](docs/API_SPEC.md) for the full contract.

```bash
python3 -c "
import base64, io, json
from PIL import Image
buf = io.BytesIO()
Image.new('RGB', (32, 32), color='white').save(buf, format='PNG')
print(json.dumps({'image_base64': base64.b64encode(buf.getvalue()).decode()}))
" > /tmp/image_payload.json

curl -s -X POST http://localhost:8000/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "local-test",
    "image_base64": "'"$(python3 -c "
import base64, io
from PIL import Image
buf = io.BytesIO()
Image.new('RGB', (32, 32), color='white').save(buf, format='PNG')
print(base64.b64encode(buf.getvalue()).decode())
")"'",
    "audio_base64": "'"$(python3 -c "
import base64, io, wave
buf = io.BytesIO()
with wave.open(buf, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
    w.writeframes(b'\x00\x00' * 1600)
print(base64.b64encode(buf.getvalue()).decode())
")"'",
    "debug": true
  }'
```

With `USE_REAL_PROVIDERS` unset (the default), this returns deterministic fake-provider output instantly. With real providers configured, it calls Groq for ASR, Vision, LLM reasoning, and TTS.

## Getting Started — Mobile

```bash
cd mobile
flutter pub get
flutter run --dart-define=BACKEND_URL=https://backend-mu-azure-ghm6imsjg1.vercel.app
```

This runs the app against the deployed backend. To point at a local backend instead, run `uvicorn app.main:app --reload` in `backend/` and pass `--dart-define=BACKEND_URL=http://localhost:8000` (use your machine's LAN IP, not `localhost`, when running on a physical device).

**Camera and microphone require real hardware.** The iOS Simulator and Android Emulator have neither — holding the "Hold to ask" button there shows "Could not access the camera" / "Could not start recording" errors, which is expected, not a bug. For a full test of the capture pipeline, run on a physical device:

```bash
flutter devices              # confirm your device is listed
flutter run -d <device-id> --dart-define=BACKEND_URL=https://backend-mu-azure-ghm6imsjg1.vercel.app
```

On iOS, a physical device needs a signing team configured in Xcode (`open ios/Runner.xcworkspace`, then Signing & Capabilities) the first time you deploy to it.

## Architecture

Be My Eye is a **modular monolith**: one backend application with clearly separated internal components, one mobile client, and every AI capability accessed through a provider interface so implementations can be swapped without touching application logic. The backend — not the LLM — owns orchestration: it decides which providers to call; the LLM only reasons over the assembled context. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md) for the full rationale.

### Directory Structure

```
be-my-eye/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory, provider wiring, CORS
│   │   ├── api/
│   │   │   └── conversation.py        # POST /conversation route
│   │   ├── core/
│   │   │   ├── config.py              # Settings from environment variables
│   │   │   └── prompts.py             # Prompt templates for each provider
│   │   ├── schemas/
│   │   │   ├── common.py              # ConversationTurn, ConversationResponse, ErrorResponse
│   │   │   └── conversation.py        # ConversationRequest
│   │   ├── services/
│   │   │   ├── conversation_service.py  # Orchestration: ASR -> route -> Vision/OCR -> LLM -> TTS
│   │   │   ├── intent_router.py         # Decides which providers a request needs
│   │   │   └── session_store.py         # In-memory conversation history
│   │   └── providers/
│   │       ├── base.py                # Abstract provider interfaces (ASR/Vision/OCR/LLM/TTS/Grounding)
│   │       ├── fakes.py                # Deterministic fake providers (no API calls)
│   │       └── groq.py                 # Real Groq-backed provider implementations
│   ├── tests/
│   │   ├── unit/                      # One test file per production module
│   │   └── integration/               # Full-endpoint tests, real-mode smoke test (env-gated)
│   ├── scripts/
│   │   └── live_image_smoke.py        # Manual smoke-test script against real Groq
│   ├── vercel.json                    # Vercel deployment config
│   ├── requirements.txt               # Mirrors pyproject.toml, required by Vercel's Python builder
│   └── pyproject.toml                 # Dependencies, [tool.vercel] entrypoint
├── mobile/                            # Flutter client
│   ├── lib/
│   │   ├── main.dart                          # Entry point, wires real services into ConversationState
│   │   └── features/conversation/
│   │       ├── conversation_screen.dart       # Accessible hold-to-ask screen (Stitch-designed UI)
│   │       ├── conversation_state.dart        # ChangeNotifier orchestrating capture -> submit -> playback
│   │       ├── backend_client.dart            # POST /conversation HTTP client
│   │       ├── media_services.dart            # Camera/mic capture + image compression
│   │       ├── audio_playback.dart            # Speech playback
│   │       ├── models.dart                    # Request/response models
│   │       └── demo_capture.dart              # Hardcoded demo image/audio for quick manual testing
│   ├── test/                          # 20 tests covering state, models, capture, and the screen's semantics
│   └── pubspec.yaml                   # camera, record, just_audio, http, provider, permission_handler, image, google_fonts
├── docs/                              # Vision, requirements, architecture, decisions, roadmap
│   └── superpowers/                   # Design specs and implementation plans for this effort
└── playground/                        # Prototype scripts (VLM, depth) — reference only, not production code
```

### Request Lifecycle

1. Mobile app captures the current camera frame and records the user's spoken question.
2. A single `POST /conversation` request carries the session ID, image, and audio to the backend.
3. **ASR** (`GroqASRProvider` / `FakeASRProvider`) transcribes the audio to text.
4. **`IntentRouter`** inspects the transcript and decides which providers this request actually needs — e.g., a "read this" request routes to OCR in addition to Vision; a plain question routes to Vision alone.
5. Selected providers run: **Vision** analyzes the frame for the user's question; **OCR** extracts visible text if requested.
6. **LLM** (`GroqLLMProvider` / `FakeLLMProvider`) reasons over the transcript, provider outputs, and recent conversation history to produce one concise, natural response. The LLM never decides which providers to call — that's the backend's job, not an agentic loop.
7. **TTS** synthesizes the response text into speech.
8. The backend returns text, base64-encoded audio, and (in debug mode) which providers were selected and their raw outputs.
9. `ConversationService` records the turn in the session store so follow-up questions have context.

### Provider Interfaces

Every AI capability is an abstract base class in `backend/app/providers/base.py`:

| Provider | Responsibility | Fake Implementation | Real Implementation |
| --- | --- | --- | --- |
| `ASRProvider` | Speech → text | Deterministic fixed text | Groq Whisper |
| `VisionProvider` | Scene/question understanding | Deterministic summary | Groq Vision-Language Model |
| `OCRProvider` | Text extraction from images | Deterministic text | Delegates to the same Groq VLM |
| `LLMProvider` | Final response reasoning | Deterministic response | Groq LLM |
| `TTSProvider` | Text → speech | Deterministic UTF-8 bytes | Groq TTS |
| `GroundingProvider` | Object location ("where are my keys?") | Deterministic location string | Groq VLM |

Swapping any provider's implementation — a different vendor, a local model, a specialized OCR engine — never requires changing `ConversationService`, the API contract, or the mobile client. See [`docs/PROVIDERS.md`](docs/PROVIDERS.md).

## Environment Variables

All settings are read by `backend/app/core/config.py`. A `.env` file at the repository root (or inside `backend/`) is loaded automatically if present; environment variables always take precedence.

| Variable | Description | Default |
| --- | --- | --- |
| `USE_REAL_PROVIDERS` | `true` to call real Groq APIs; `false`/unset uses deterministic fakes | `false` |
| `GROQ_API_KEY` | Your Groq API key — **required** when `USE_REAL_PROVIDERS=true` | *(none)* |
| `GROQ_MULTIMODAL_MODEL` | Groq vision-capable model ID — **required** when `USE_REAL_PROVIDERS=true`; the app refuses to start without it | *(none)* |
| `GROQ_LLM_MODEL` | Groq model for final response reasoning | `llama-3.3-70b-versatile` |
| `GROQ_ASR_MODEL` | Groq model for speech-to-text | `whisper-large-v3` |
| `GROQ_ASR_LANGUAGE` | ASR language hint | `ar` (Arabic) |
| `GROQ_TTS_MODEL` | Groq model for text-to-speech | `canopylabs/orpheus-arabic-saudi` |
| `GROQ_TTS_VOICE` | TTS voice name | `abdullah` |
| `BE_MY_EYE_APP_NAME` | FastAPI app title | `Be My Eye Backend` |
| `BE_MY_EYE_ENV` | Environment label | `development` |
| `BE_MY_EYE_DEBUG` | FastAPI debug mode | `true` |

> **Note on defaults:** the ASR language and TTS voice default to Arabic — this reflects the project's current target users. Override `GROQ_ASR_LANGUAGE`/`GROQ_TTS_MODEL`/`GROQ_TTS_VOICE` for other languages.

Never commit a `.env` file — it's already covered by `.gitignore`. On Vercel, set these as [project environment variables](https://vercel.com/docs/projects/environment-variables) (see [Deployment](#deployment)), not in `vercel.json`.

## Available Scripts

| Command | Description |
| --- | --- |
| `uvicorn app.main:app --reload` | Start the backend dev server (run from `backend/`) |
| `python3 -m pytest -v` | Run the full backend test suite (run from `backend/`) |
| `python3 -m pytest tests/unit/ -v` | Run only unit tests |
| `python3 -m pytest tests/integration/ -v` | Run only integration tests |
| `RUN_REAL_GROQ_SMOKE_TESTS=true python3 -m pytest -v` | Include the real-mode Groq smoke test (needs `GROQ_API_KEY` + `GROQ_MULTIMODAL_MODEL`) |
| `python3 scripts/live_image_smoke.py` | Manual smoke-test script that hits real Groq with a sample image/question |
| `vercel dev` | Run the backend locally through Vercel's emulator (run from `backend/`, after `vercel link`) |
| `vercel deploy --prod` | Deploy the backend to Vercel production (run from `backend/`) |
| `vercel env ls production` | List configured production environment variables |

## Testing

### Running Tests

```bash
cd backend
python3 -m pytest -v
```

Expected output: **54 passed, 1 skipped**. The one skip is `tests/integration/test_real_mode_smoke.py`, which only runs when `RUN_REAL_GROQ_SMOKE_TESTS=true` and a real `GROQ_MULTIMODAL_MODEL` are set — it makes real Groq API calls and isn't part of the default fast, deterministic suite.

### Test Structure

```
backend/tests/
├── unit/
│   ├── test_common_schemas.py       # ConversationTurn, ConversationDebug, ConversationResponse
│   ├── test_config.py               # Settings loading, .env parsing
│   ├── test_conversation_request.py # Request schema validation
│   ├── test_conversation_service.py # Orchestration logic
│   ├── test_fake_providers.py       # Deterministic fake provider behavior
│   ├── test_groq_providers.py       # Real provider request-building (mocked client)
│   ├── test_intent_router.py        # Provider-selection routing rules
│   ├── test_main.py                 # App factory, CORS middleware registration
│   ├── test_prompts.py              # Prompt template loading/overrides
│   ├── test_provider_base.py        # Abstract interfaces are truly abstract
│   └── test_session_store.py        # Conversation history isolation per session
└── integration/
    ├── test_conversation_api.py     # Full endpoint tests with fake providers
    └── test_real_mode_smoke.py      # Real Groq smoke test (env-gated, skipped by default)
```

### Writing Tests

Every production module has a corresponding unit test file — when you add a module, add its test file alongside it. Example pattern used throughout this codebase:

```python
from app.services.intent_router import IntentRouter

def test_intent_router_adds_ocr_for_text_requests():
    router = IntentRouter()
    result = router.select_providers("Can you read this receipt for me?")
    assert "ocr" in result
```

Mobile tests run via `flutter test` from `mobile/` (20 tests, all passing) and cover `ConversationState`, `BackendClient`, `MediaCaptureService`, `AudioPlaybackService`, and the conversation screen's semantics, using fake implementations of each service. `flutter analyze` is clean with no issues.

## Deployment

The backend deploys to **Vercel** using its Python runtime (Fluid Compute). The `[tool.vercel]` entry in `backend/pyproject.toml` points Vercel directly at the existing `app.main:app` FastAPI instance — no wrapper file or directory restructuring needed.

### One-Time Setup

```bash
npm i -g vercel
cd backend
vercel login
vercel link --yes
```

### Configure Production Environment Variables

Secrets are set via the Vercel CLI (interactively, so they never appear in shell history or command-line arguments) or the [Vercel dashboard](https://vercel.com/dashboard):

```bash
vercel env add USE_REAL_PROVIDERS production
# enter: true

vercel env add GROQ_API_KEY production
# paste your key when prompted

vercel env add GROQ_MULTIMODAL_MODEL production
# enter your chosen Groq vision model ID
```

Verify:

```bash
vercel env ls production
```

### Deploy

```bash
vercel deploy --prod
```

Vercel builds using `backend/requirements.txt` (its Python builder needs this file explicitly — it does not read `pyproject.toml` dependencies) and `backend/.python-version` (pinned to `3.13`). On success, it prints a production URL and a stable alias URL; use the **alias URL** (not the unique per-deployment URL, which sits behind Vercel's SSO wall by default) as your `BACKEND_URL` for the mobile app.

### Verify the Deployment

```bash
curl https://your-alias-url.vercel.app/health
# {"status":"ok"}
```

### Local Verification Before Deploying

Always verify with Vercel's local emulator before pushing to production — it catches configuration errors (like an invalid `vercel.json` `functions` path) that only surface under Vercel's actual routing, not under plain `uvicorn`:

```bash
vercel dev
curl http://localhost:3000/health
```

### CI/CD

GitHub Actions run tests on every push/PR, path-filtered so each workflow only runs when its area changes:

- [`.github/workflows/backend-ci.yml`](.github/workflows/backend-ci.yml) — `pytest` with fake providers (no secrets required), triggered on `backend/**` changes
- [`.github/workflows/mobile-ci.yml`](.github/workflows/mobile-ci.yml) — `flutter analyze && flutter test`, triggered on `mobile/**` changes

These workflows run tests only — they do not deploy anything. Deploys remain manual via the Vercel CLI (see [Deploy](#deploy) above). **Recommended next step (manual, one-time):** connect this GitHub repository to the Vercel project via the [Vercel dashboard](https://vercel.com/dashboard) → Project Settings → Git, so pushes to `main` auto-deploy to production and PRs get preview URLs automatically.

## Troubleshooting

### `vercel.json` error: "doesn't match any Serverless Functions inside the api directory"

Vercel's `functions` key in `vercel.json` only accepts paths rooted at `api/` (or framework-specific directories) — it cannot reference a custom `[tool.vercel] entrypoint` path like `app/main.py` directly, even though entrypoint detection itself works fine. If you need to configure `maxDuration` or similar per-function settings, either omit the `functions` key (Vercel's platform default is currently 300s, generous for this app's ASR → Vision → LLM → TTS chain) or restructure under `api/`.

### `groq.BadRequestError: ... requires terms acceptance`

Some Groq models (notably the default TTS model, `canopylabs/orpheus-arabic-saudi`) require a one-time terms acceptance by the account/org admin. Visit the URL in the error message (or `https://console.groq.com/playground?model=<model-id>`) and accept the terms, then retry.

### `RuntimeError: GROQ_MULTIMODAL_MODEL is required when real providers are enabled`

Set `GROQ_MULTIMODAL_MODEL` to a vision-capable model ID from your Groq account. The app deliberately refuses to start in real mode without it rather than failing confusingly later.

### Backend works locally but fails after deploying to Vercel

Check `vercel env ls production` — environment variables set locally in a `.env` file are **not** automatically available in production; they must be added via `vercel env add` (see [Deployment](#deployment)).

### `mobile/lib/main.dart` is gitignored / mobile changes aren't being tracked

The root `.gitignore` used to be a Python project template whose `lib/` pattern (intended for Python build output) also matched Flutter's `mobile/lib/` source directory, silently excluding Dart source from every commit. This was fixed by scoping `.gitignore` per language root (see decision [D-014](docs/DECISIONS.md)). If you still see this, check `git check-ignore -v mobile/lib/main.dart` — it should report no match. If it does match something, your local `.gitignore` may predate the fix; pull the latest `main`.

### "Hold to ask" shows "Could not access the camera" / "Could not start recording"

Expected on the iOS Simulator and Android Emulator — neither has a camera or microphone. Test on a physical device (see [Getting Started — Mobile](#getting-started--mobile)).

## Documentation Map

This README covers setup, architecture, and deployment. For deeper context:

| Document | Covers |
| --- | --- |
| [`docs/VISION.md`](docs/VISION.md) | Product mission and design principles |
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | Functional and non-functional requirements, explicit out-of-scope items |
| [`docs/USER_STORIES.md`](docs/USER_STORIES.md) | Concrete user stories with acceptance criteria |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System-level architecture and request lifecycle |
| [`docs/API_SPEC.md`](docs/API_SPEC.md) | The `/conversation` endpoint contract in detail |
| [`docs/PROVIDERS.md`](docs/PROVIDERS.md) | Every provider's responsibility and future extensions |
| [`docs/AI_BEHAVIOR.md`](docs/AI_BEHAVIOR.md) | How the assistant should sound and behave |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Numbered architectural decision records (D-001 onward) |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phased MVP roadmap and live progress tracker |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | Full design specs for in-progress work |
| [`docs/superpowers/plans/`](docs/superpowers/plans/) | Detailed, task-by-task implementation plans |
