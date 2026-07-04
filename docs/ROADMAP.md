# ROADMAP

## Goal

Deliver a working MVP for Be My Eye as a modular monolith: one backend application, one mobile client, and provider-based AI integrations behind stable interfaces.

The first version should prove the end-to-end user experience before any advanced expansion.

## Current Status

### Done

1. Product vision and requirements are documented.
2. Core architecture decisions are documented.
3. Provider boundaries and the single-endpoint API shape are defined.
4. Prototype exploration exists in `playground/` for VLM and depth experiments.
5. This roadmap now tracks execution status.
6. Backend foundation has been scaffolded.
7. Phase 1 first vertical slice exists in the backend with fake providers and tests.
8. Real Groq-backed Vision, OCR, Grounding, LLM, ASR, and TTS adapters have been added.
9. Flutter mobile app is fully implemented: models, backend client, media capture/compression, audio playback, conversation state, and an accessible hold-to-ask screen (16/16 tests passing, `flutter analyze` clean).
10. Mobile UI was designed via Google Stitch (idle/listening/thinking/answer states) and applied to the app; verified running live on an iOS Simulator (iPhone 16e) and confirmed rendering correctly.
11. Backend deployed to Vercel at https://backend-mu-azure-ghm6imsjg1.vercel.app with real Groq providers. Full pipeline verified live end-to-end, including TTS synthesis.
12. Vision-task routing (currency, color, product, scene) and object-finder grounding are wired into ConversationService, with Arabic keyword support (this app's ASR defaults to Arabic) verified live end-to-end via real Groq TTS/ASR round-trips.
13. Backend accessibility expansion: five new VisionTasks (food, people, environment, clothing, label) with hedged, safety-conscious prompts; barcode-to-product lookup via Open Food Facts (`POST /product-lookup`).
14. Egyptian-dialect TTS via a free, public Gradio Space (`EgyptianTTSProvider`), live-verified end-to-end, replacing the previous Saudi-dialect Groq voice as the real-mode default. Falls back gracefully (`tts_fallback_required`) to the mobile app's on-device Arabic voice on synthesis failure.
15. Specialist Egyptian-currency detection (`CurrencyDetectionProvider` / `RoboflowCurrencyProvider`) tried first for currency questions and Money Mode, falling back to the general VLM when unconfident or unconfigured. Originally shipped without live verification (no Roboflow account available); a real `ROBOFLOW_API_KEY` was added afterward and confirmed working end-to-end against the live hosted API — see `docs/superpowers/plans/2026-07-03-backend-roboflow-currency-detection.md`.
16. Mobile: dedicated Money Mode and barcode-scanning buttons alongside the hold-to-ask flow, plus on-device Arabic TTS fallback wiring (`flutter_tts`, `mobile_scanner`).
17. Multi-turn conversation memory: `ConversationResponse.transcript` is now always returned, and the mobile app accumulates and sends `history` with each request, so the backend's existing (previously unused) client-supplied-history path is now actually exercised in production.
18. Hardened `ConversationService.handle()` against malformed client input: every provider call (ASR, Vision, OCR, grounding, LLM) is now wrapped so upstream failures (e.g. Groq rejecting invalid audio, PIL rejecting invalid images) return a clean `400 ConversationError` instead of leaking a raw 500 with a Python traceback. Found and fixed via real production smoke-testing with deliberately malformed payloads; re-verified against production with a genuinely valid image+audio payload afterward (200 OK, transcript present, audio synthesized). 119 backend / 33 mobile tests passing, `flutter analyze` clean, both CI workflows green.

### Not Done Yet

1. **The app is now installed and running live on a physical iPhone** (wireless debugging, `flutter run --release`), confirming build, code signing, and launch all work on real hardware — not just Simulator. What's still outstanding: hands-on tap-through of Money Mode, barcode scanning, and the TTS fallback, plus granting real camera/microphone permission prompts, which needs the phone physically in hand and can't be done from the terminal.
2. **The `egyptian-currency-psnkr` v1 Roboflow model does not detect real Egyptian banknotes.** Tested against 5 real reference images (official Wikimedia Commons photos of the current 10 EGP and 20 EGP polymer notes, the 100 EGP note, and an older 1-pound bill) at both default and `confidence=1` (near-zero threshold) — every request returned an empty `predictions` list. The API integration itself is confirmed working (200 OK, correct response shape); the model just doesn't fire on any tested real banknote. In production this means `RoboflowCurrencyProvider` will currently defer to the VLM fallback for every real currency query, which the D-017 hybrid architecture handles gracefully, but the "specialist tried first" path is not adding value with this specific model version. Worth swapping in a better-trained Roboflow model or dataset before relying on the specialist path.
3. Production hardening and demo polish.

### In Progress

1. None currently. Backend (119 passed, 1 skipped) and mobile (33/33) test suites and CI are green on `main`; production backend confirmed healthy at `/health` with the rotated Groq key verified end-to-end.

### Recently Closed

1. **Multi-turn conversation memory** — the backend already preferred client-supplied `request.history` over its in-memory session store (which doesn't survive Vercel's serverless cold starts); the mobile app now populates it. `ConversationState` accumulates `ConversationTurn`s from each turn's `transcript`/`text` and sends them with the next request. No new infrastructure required.

## Guiding Rules

1. Keep the backend as a single application with internal modules, not services.
2. Treat provider interfaces as the boundary for all AI capabilities.
3. Start with the smallest useful vertical slice.
4. Keep OCR, ASR, Vision, LLM, and TTS interchangeable from day one.
5. Write pytest coverage for every module.
6. After every implementation step, run a code review pass and fix issues before moving on.

## MVP Phases

### Phase 0: Repository Foundation

Status: `done`

Deliverables:

1. Create the backend project skeleton.
2. Define the package layout for API, services, providers, prompts, schemas, and tests.
3. Add application configuration and environment handling.
4. Add a small set of shared domain models for requests, responses, and session state.

Dependencies:

1. This phase comes first.
2. No provider code should depend on concrete models yet.

### Phase 1: Backend Vertical Slice With Fake Providers

Status: `done`

Deliverables:

1. Implement provider interfaces.
2. Implement the conversation service orchestration flow.
3. Add `POST /conversation`.
4. Add fake or stub provider implementations for ASR, Vision, OCR, LLM, and TTS.
5. Return a complete structured response from the backend.

Dependencies:

1. Depends on Phase 0 foundation.
2. The API depends on the conversation service.
3. The conversation service depends on provider interfaces, not model code.

Purpose:

1. Validate the request/response contract early.
2. Prove orchestration, session handling, and error handling before model integration.

### Phase 2: Real AI Provider Adapters

Status: `done`

Deliverables:

1. Replace fake ASR with a real adapter.
2. Replace fake Vision with a real VLM adapter.
3. Keep OCR as a separate provider, even if it initially delegates to the VLM.
4. Replace fake LLM with a real reasoning adapter.
5. Replace fake TTS with a real speech synthesis adapter.

Dependencies:

1. Depends on the stable provider interfaces from Phase 1.
2. Real adapters must not change the API contract.

### Phase 3: Mobile Client Integration

Status: `done`

Deliverables:

1. Create the Flutter app shell.
2. Capture camera frames on demand.
3. Record user audio.
4. Send a single request to `POST /conversation`.
5. Play the returned speech response.
6. Keep the UI thin and drive behavior through a small state layer.

Dependencies:

1. Depends on the backend API contract stabilizing.
2. Depends on Phase 1 being functional.
3. Depends on Phase 2 for real audio and speech behavior.

### Phase 4: Conversation Quality and Multi-Turn Behavior

Status: `done`

Deliverables:

1. Add short-term session memory. — Done: client-supplied `history`, see D-021.
2. Improve provider selection rules. — Done: `IntentRouter` now covers scene, currency, color, product, food, people, environment, clothing, and label, in English and Arabic.
3. Improve prompt templates. — Done: hedged, safety-conscious prompts for all VisionTasks in `app/core/prompts.py`.
4. Add better fallback and uncertainty handling. — Done: hybrid specialist/VLM fallback (D-017), TTS device-voice fallback (D-019), and guarded provider calls returning clean errors instead of unhandled 500s.

Dependencies:

1. Depends on the conversation service being stable.
2. Depends on session identifiers and request history already working.

### Phase 5: Hardening and Demo Readiness

Status: `in progress`

Deliverables:

1. Stabilize latency and error handling.
2. Add smoke tests for key user flows.
3. Improve response quality for the target demo scenarios.
4. Remove dead code, temporary scaffolding, and prototype leftovers.

Dependencies:

1. Depends on all earlier phases.
2. This is the final review-and-polish stage before broader expansion.

## Order Of Implementation

1. Establish the backend package structure and configuration.
2. Define request, response, and session schemas.
3. Define provider interfaces.
4. Implement the conversation service.
5. Add `POST /conversation`.
6. Add fake providers and validate the first vertical slice.
7. Add real ASR, Vision, OCR, LLM, and TTS adapters.
8. Build the Flutter client.
9. Add conversation memory and better routing rules.
10. Harden the system with tests, reviews, and demo fixes.

## Progress Tracker

| Area | Status | Notes |
| --- | --- | --- |
| Docs and architecture | Done | Vision, requirements, components, providers, API, and decisions are documented. |
| Playground experiments | Done | VLM and depth prototypes exist for reference only. |
| Backend foundation | Done | Scaffold, shared schemas, providers, service, API, and tests are in place. Deployed to Vercel at https://backend-mu-azure-ghm6imsjg1.vercel.app with real Groq providers; full pipeline (ASR → routing → Vision → LLM → TTS) verified live end-to-end. |
| API and orchestration | Done | `/conversation` works with deterministic fake providers. |
| Provider adapters | Done | Groq-backed Vision, OCR, Grounding, LLM, ASR adapters, Egyptian TTS (Gradio Space, live-verified), Roboflow currency detection (live-verified with a real API key), and Open Food Facts product lookup are in code and wired into ConversationService; real mode is config-driven. Vision-task routing (scene/currency/color/product/food/people/environment/clothing/label) and grounding support both English and Arabic keywords, verified live. |
| Mobile app | Done | Full Flutter app implemented (models, backend client, media capture/compression, audio playback + on-device TTS fallback, conversation state with multi-turn history, accessible hold-to-ask screen, Money Mode, barcode scanning), Stitch-designed UI applied, 33/33 tests passing, verified running live on iOS Simulator and on a real, physical iPhone (installed and launched via wireless debugging). Hands-on tap-through of individual features on-device is still pending. |
| Tests | Done | Backend: 119 passed, 1 skipped. Mobile: 33/33 passed, `flutter analyze` clean. Both suites green in CI on `main`. |

## Component Dependencies

1. API depends on the conversation service.
2. Conversation service depends on provider interfaces and session storage.
3. ASR runs before reasoning because audio must become text first.
4. Vision depends on the latest camera frame.
5. OCR is a separate capability that can be invoked when text reading is needed.
6. LLM depends on the assembled context from ASR, Vision, OCR, and conversation history.
7. TTS depends on the final response text.
8. Mobile depends only on the backend API contract, not internal providers.

## Initial Repository Structure

Recommended starting layout:

```text
be-my-eye/
  backend/
    pyproject.toml
    app/
      __init__.py
      main.py
      api/
        conversation.py
      core/
        config.py
      schemas/
        conversation.py
        common.py
      services/
        conversation_service.py
        session_store.py
        intent_router.py
      providers/
        base.py
        asr/
        vision/
        ocr/
        llm/
        tts/
      prompts/
  tests/
    unit/
      test_*.py
    integration/
      test_conversation_api.py
  mobile/
    lib/
  docs/
  playground/
```

Notes:

1. Keep prototype scripts in `playground/` only.
2. Do not let `playground/` become production architecture.
3. Mirror the backend module structure in `tests/` so every module gets its own test file.

## First Vertical Slice

The first vertical slice should be:

1. A `POST /conversation` request arrives with `session_id`, image, and audio.
2. ASR converts audio to text, even if the first version is stubbed.
3. The conversation service loads short session context.
4. The service routes to Vision and OCR only when needed.
5. The LLM produces a concise assistant response.
6. TTS returns speech for the response.
7. The API returns text, audio payload or reference, and debug metadata.

Why this slice first:

1. It proves the entire application shape without waiting for the mobile app.
2. It validates orchestration, interfaces, and response format early.
3. It gives a stable contract for the Flutter client.

## Testing Strategy

### Unit Tests

1. One pytest file per production module.
2. Test provider interfaces, service logic, schema validation, and routing rules.
3. Use fakes and mocks for all external model calls.
4. Keep unit tests deterministic and fast.

### Integration Tests

1. Test the `/conversation` endpoint end to end with fake providers.
2. Verify request validation, session handling, and error responses.
3. Add a small number of real-adapter tests behind optional markers if needed.

### Contract Tests

1. Lock the provider interface behavior with tests.
2. Lock the API request and response schema with tests.
3. Prevent accidental changes to the mobile/backend contract.

### Smoke Tests

1. Scene understanding.
2. OCR request.
3. Multi-turn follow-up.
4. Voice-only interaction.
5. Provider failure fallback.

### Review Rule

1. After each phase, run the test suite for the touched modules.
2. Perform a code review pass before moving to the next step.
3. Fix bugs immediately rather than carrying them forward.

## Technical Risks

1. Model latency may make the experience feel slow if orchestration becomes too chatty.
2. Audio, image, and session payloads can become awkward if the API contract is not kept tight.
3. Provider abstractions can become too abstract if they are designed before the MVP is real.
4. OCR quality may be weak if it relies only on the VLM, especially for dense documents.
5. Session memory can grow messy if the app stores too much history too early.
6. Mobile capture quality can dominate perceived AI quality, even when the backend is correct.
7. External AI provider behavior may vary, so fallbacks and uncertainty handling matter.
8. Prototype scripts in `playground/` may not reflect production constraints and should not be copied blindly.

## MVP Success Criteria

1. A user can ask a question through the mobile app.
2. The backend answers using the latest camera frame and current audio request.
3. The system supports short follow-up questions.
4. The architecture stays modular and provider-based.
5. Tests exist for every module.
6. Each implementation step is reviewed before the next one starts.
