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
9. Flutter mobile shell and backend client scaffolding have started.
10. Mobile conversation state now owns capture and playback hooks.
11. Backend deployed to Vercel at https://backend-mu-azure-ghm6imsjg1.vercel.app with real Groq providers. Full pipeline verified live end-to-end, including TTS synthesis.

### Not Done Yet

1. Finish Flutter camera and microphone capture wiring.
2. Verify mobile playback on-device.
3. Full multi-turn conversation memory beyond the in-memory starter.
4. Production hardening and demo polish.

### In Progress

1. Phase 3 is underway and the first capture/playback wiring is in place.

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

Status: `in progress`

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

Status: `not started`

Deliverables:

1. Add short-term session memory.
2. Improve provider selection rules.
3. Improve prompt templates.
4. Add better fallback and uncertainty handling.

Dependencies:

1. Depends on the conversation service being stable.
2. Depends on session identifiers and request history already working.

### Phase 5: Hardening and Demo Readiness

Status: `not started`

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
| Provider adapters | Done | Groq-backed Vision, OCR, Grounding, LLM, ASR, and TTS adapters are in code; real mode is config-driven. |
| Mobile app | In progress | Flutter shell, backend client, and capture/playback wiring are scaffolded. |
| Tests | Done | The Phase 1 slice has pytest coverage and passes. |

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
