# Be My Eye — MVP Completion & Feature Expansion Design

**Date:** 2026-07-02
**Status:** Approved (pending written-spec review)
**Scope:** Rebuild the mobile app, add 4 accessibility features, deploy the backend to Vercel, wire CI/CD.

---

## 1. Context & Problem Statement

Be My Eye is an AI voice assistant for blind and low-vision users: point the camera, ask a
question by voice, get a spoken answer. The design philosophy is **conversation over captioning** —
answer the user's *intent*, not just describe the scene.

### Current state (verified)

| Layer | Status | Notes |
|---|---|---|
| Docs/architecture | Complete | 12 docs: vision, requirements, decisions, roadmap, AI behavior |
| Backend | Complete & tested | FastAPI, provider pattern (ASR/Vision/OCR/LLM/TTS), Groq adapters, fakes, IntentRouter, in-memory sessions, pytest coverage |
| Mobile source | **Missing from repo** | Only `mobile/test/` was committed; `mobile/lib/` was never tracked |

### Root cause of the missing mobile app

The **root `.gitignore` is a Python template**. Line 17, `lib/` (intended for Python build
directories), silently matched the Flutter **`mobile/lib/`** source root. Every commit
(`"application finished"`, `"Mobile App Draft"`) committed everything *except* the app source.
Only the test files survived (they live in `test/`, not `lib/`).

**Silver lining:** the committed tests fully encode the intended app contract
(`BackendClient`, `ConversationState`, `MediaCaptureService`, `AudioPlaybackService`,
`DemoCapture`, `ConversationRequest/Response`). Rebuilding is spec-driven, not from zero.

### Decisions locked with the user

1. **Goal:** Polished MVP + 4 new accessibility features.
2. **Mobile:** Fix `.gitignore`, rebuild the Flutter app fresh (guided by the tests + a new Stitch design).
3. **Deploy target:** Vercel (FastAPI on Python / Fluid Compute).
4. **New features:** Currency reader, Color detector, Object finder (grounding), Product identifier.
5. **Delivery approach:** Fix-first vertical slice — get something live on a phone early, then expand.

---

## 2. Goals & Non-Goals

### Goals
- Fix repository hygiene so `mobile/lib/` is tracked.
- Deploy the existing backend to Vercel and prove it live (`/health`, `/conversation`).
- Rebuild the Flutter app against the live backend; all committed tests pass.
- Add 4 features via one extensible mechanism (3 vision tasks + 1 grounding route).
- Ship an accessible, voice-first UI designed in Stitch.
- Reliable multi-turn conversation on serverless (client-carried history).
- CI/CD: automated tests + Vercel Git-integration deploys.

### Non-Goals (out of scope for this effort)
- Navigation / obstacle avoidance / depth estimation.
- Continuous scene monitoring or unsolicited notifications.
- User accounts / authentication / persistent long-term memory.
- Offline / on-device inference.
- Server-side session store (KV/Redis) — noted as a future upgrade.

---

## 3. Architecture Overview

Unchanged core: **modular monolith**, **backend orchestrates**, **provider interfaces** for all AI,
**single `POST /conversation` endpoint**. This design extends — it does not rearchitect.

```
Mobile (Flutter)                 Backend (FastAPI on Vercel)
──────────────                   ────────────────────────────
ConversationScreen               POST /conversation
   │ hold-to-ask                    │
ConversationState  ── HTTP ──▶   ConversationService.handle()
   ├ MediaCaptureService             ├ ASR.transcribe
   ├ AudioPlaybackService            ├ IntentRouter.route() → vision task + ocr + grounding query
   └ BackendClient                   ├ Vision.analyze(task=...)     [scene|currency|color|product]
                                     ├ OCR.extract_text (if flagged)
                                     ├ Grounding.locate_object (if query)
                                     ├ LLM.generate_response (aggregates all + history)
                                     └ TTS.synthesize_speech
```

---

## 4. Design Sections

### 4.1 Repository hygiene (blocker — do first)

- Remove `lib/` (and other Flutter-hostile Python patterns) from the **root** `.gitignore`.
- Replace with **scoped ignores**: a Python `.gitignore` in `backend/`, keep the correct Flutter
  `.gitignore` in `mobile/`, and a minimal root `.gitignore` (`.DS_Store`, `.env`, editor files).
- Record the fix as **D-014** in `docs/DECISIONS.md`.
- **Outcome:** `mobile/lib/` becomes trackable; the rebuilt app will actually be committed.

### 4.2 Backend feature mechanism (vision tasks + grounding)

**One abstraction covers 3 of 4 features.** A `VisionTask` selects a specialized prompt.

- **`VisionTask` values:** `scene` (default), `currency`, `color`, `product`.
- **Prompt templates** added to `app/core/prompts.py`, each following `AI_BEHAVIOR.md`
  (concise, express uncertainty, natural spatial language, never invent).
- **`IntentRouter`** returns a structured routing decision instead of a flat list:
  - `vision_task: VisionTask`
  - `use_ocr: bool`
  - `grounding_query: str | None`
  - Keyword maps:
    - currency ← money, cash, bill, banknote, dollar, "how much", denomination, currency, note
    - color ← color, colour, shade
    - product ← "what am I holding", brand, package, label, product
    - grounding ← where, "where is", "where are", find, locate, "which direction"
- **`VisionProvider.analyze(image, question, history, task=VisionTask.scene)`** — optional `task`
  param keeps the interface backward compatible.
- **Grounding wiring:** `ConversationService.handle` calls `grounding.locate_object(image, query, history)`
  when `grounding_query` is set, and feeds the result into the LLM context.
- **Schemas:** extend `ConversationDebug` with `vision_task` and `grounding_result`.
- **Tests:** unit tests for each new route and prompt; contract tests keep the API stable.

**Routing conflict rule:** `vision_task` is single-select by priority
(currency > color > product > scene); `use_ocr` and `grounding_query` are additive.

### 4.3 Backend on Vercel (stateless)

- **Serverless entry:** `backend/api/index.py` exposes the FastAPI `app` as an ASGI handler;
  `vercel.json` sets the Vercel project root to `backend/` and routes all paths to the app.
- **Runtime:** Python on Fluid Compute; 300s timeout is ample for ASR→VLM→LLM→TTS.
- **Secrets/env (Vercel project settings):** `GROQ_API_KEY`, `GROQ_MULTIMODAL_MODEL`,
  `GROQ_LLM_MODEL`, `GROQ_ASR_MODEL`, `GROQ_TTS_MODEL`, `GROQ_TTS_VOICE`, `USE_REAL_PROVIDERS=true`.
  Confirm `app/core/config.py` reads all from `os.environ`.
- **Sessions → client-carried history:** add optional `history: list[ConversationTurn]` to
  `ConversationRequest`. If provided, the service uses it; otherwise it falls back to the in-memory
  store. Stateless-friendly, zero infra, backward compatible. Mobile keeps the last **5 turns**
  (bounded to protect payload size) and sends them with each request.
- **Payload size:** serverless body limit ≈ 4.5 MB; base64 inflates ~33%. Mobile **compresses
  images** (max ~1024px, JPEG ~70%) and keeps audio short. Documented as a hard client requirement.
- **CORS:** add CORS middleware (needed for web/dev testing; harmless for native).
- Record as **D-016** (Vercel deploy) and **D-015** (client-carried history).

### 4.4 Mobile architecture (rebuild from the tests)

Target structure (dictated by committed tests):

```
mobile/lib/
  main.dart                                  # MyApp entry
  features/conversation/
    models.dart          # ConversationRequest/Response; snake_case toJson (test-locked)
    backend_client.dart  # BackendClient(baseUrl).sendConversation() via `http`
    media_services.dart  # MediaCaptureService: captureImageBase64 / start+stopAudioRecording (+compression)
    audio_playback.dart  # AudioPlaybackService: playBase64Audio() via `just_audio`
    demo_capture.dart    # embedded PNG + WAV for hardware-free testing (magic-byte test-locked)
    conversation_state.dart   # orchestrator: capture→submit→play; lastResponse / lastError / isBusy
    conversation_screen.dart  # accessible UI (4.5)
```

- **State:** lightweight `ChangeNotifier` + `provider`. `ConversationState` stays a plain injectable
  class (tests construct it with fakes).
- **Config:** backend base URL injected via `--dart-define=BACKEND_URL=...` → the Vercel URL.
- **Validation:** reject send without both captures (test: "Capture an image and audio before sending.").
- **Correctness gate:** all committed tests in `mobile/test/` pass; replace the stale default
  `widget_test.dart` (counter) with a real screen test.

### 4.5 Stitch accessible UI

Voice-first, one-gesture — usable **without sight**.

- **Whole screen = one giant "Hold to ask" button.** Hold records audio; release captures the frame
  and sends. No small targets to aim at.
- **No per-feature buttons.** Users ask naturally; the backend router selects the feature. Simple UI,
  voice-discoverable features.
- **Multi-sensory feedback:** haptics + earcons for Listening / Thinking / Answer-ready; the answer
  auto-plays via TTS.
- **Screen-reader first:** semantic labels, live-region announcements, WCAG AA contrast, large
  dynamic type, reduced-motion.
- **Camera preview** shown for low-vision/sighted helpers but never required to operate.
- **Process:** Stitch generates screen states + a small design system (color/type/spacing); translate
  to Flutter widgets.
- Record the vision-task mechanism as **D-017**.

### 4.6 CI/CD & docs

- **GitHub Actions:**
  - `backend-ci.yml` — Python setup, install, `pytest` (fake providers, no API key), path-filtered to `backend/`.
  - `mobile-ci.yml` — Flutter setup, `flutter analyze` + `flutter test`, path-filtered to `mobile/`.
- **Deploy:** Vercel **native Git integration** — preview URLs on PRs, production on merge to `main`.
  No deploy secrets in Actions.
- **Docs:** add `docs/DEPLOYMENT.md`; update `docs/ROADMAP.md` status; add a root `README.md`;
  add decision records D-014…D-017.

---

## 5. Build Sequence

1. **Repo hygiene** — scoped `.gitignore`s; commit. (Unblocks tracking `mobile/lib/`.)
2. **Deploy current backend to Vercel** — serverless entry, env, prove `/health` + `/conversation` live with real Groq.
3. **Rebuild Flutter app** — `lib/` from tests, wired to the live URL; existing tests green; run on device with demo capture then real capture.
4. **Vision-task features** — currency / color / product prompts + router + tests.
5. **Grounding route** — object finder wired into the service + tests.
6. **Stitch accessible UI** — implement designed screens + haptics/screen-reader.
7. **Client-carried history** — optional `history` field end-to-end for multi-turn.
8. **CI/CD + docs** — Actions test workflows, Vercel Git integration, DEPLOYMENT.md, decision records.
9. **Comprehensive review** — full-review pass; fix issues before calling it done.

---

## 6. Testing Strategy

- **Backend unit:** one pytest file per module; new tests for vision-task routing, prompts,
  grounding route, client-carried history. External model calls use fakes.
- **Backend integration:** `/conversation` end-to-end with fakes; request validation, session
  handling, error responses; optional real-adapter smoke behind a marker.
- **Contract:** lock the request/response schema and provider interfaces so the mobile/backend
  contract can't drift silently.
- **Mobile:** all committed tests pass; add a `conversation_screen` widget/interaction test and a
  compression test for the capture service.
- **Manual smoke (demo scenarios):** scene understanding, currency, color, product, OCR read,
  object finder, multi-turn follow-up, voice-only, provider-failure fallback.

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Serverless payload limit (~4.5 MB) | Client-side image compression; short audio; documented as hard requirement |
| In-memory sessions don't persist on serverless | Client-carried history (primary); in-memory as fallback only |
| Grounding prompt quality (hardest feature) | Sequenced last; MVP demos without it if needed |
| Model latency feels slow | Keep orchestration lean; single VLM call per task; concise prompts |
| OCR/currency accuracy from VLM alone | Express uncertainty per AI_BEHAVIOR; note specialized models as future work |
| Re-introducing the gitignore bug | Scoped `.gitignore`s + D-014 record |

---

## 8. Success Criteria

1. Backend is live on Vercel; `/conversation` answers with real Groq providers.
2. A user can hold-to-ask on a real phone and hear an answer end-to-end.
3. All 4 features work: currency, color, product, object finder.
4. Multi-turn follow-ups work via client-carried history.
5. `mobile/lib/` is tracked in git; all tests (backend + mobile) pass in CI.
6. UI meets WCAG AA and is operable with a screen reader / without sight.
7. Docs updated; decision records D-014…D-017 added.
