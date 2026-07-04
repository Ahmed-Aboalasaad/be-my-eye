# DECISIONS

## D-001: Use a Modular Monolith Architecture

**Decision**

Build the system as a single backend application with clearly separated internal components.

**Reason**

The POC does not need microservices. A modular monolith keeps development fast while preserving clean boundaries.

---

## D-002: Backend as the Orchestrator

**Decision**

The backend controls the workflow and decides which capabilities are required.

The LLM is responsible for reasoning and generating responses, not for controlling application flow.

**Reason**

Deterministic orchestration is easier to debug, test, and optimize during the POC.

---

## D-003: Provider-Based AI Architecture

**Decision**

All AI capabilities must be accessed through provider interfaces.

Examples:

* Vision Provider
* OCR Provider
* LLM Provider
* ASR Provider
* TTS Provider

**Reason**

Models and external APIs should be replaceable without affecting application logic.

---

## D-004: Single Mobile-to-Backend Endpoint

**Decision**

The mobile application communicates through one main endpoint:

`POST /conversation`

**Reason**

The user interacts with an assistant, not individual AI services. Provider selection should remain hidden from the client.

---

## D-005: Backend Handles All AI Processing

**Decision**

The mobile application only handles:

* Camera capture
* Audio recording
* Audio playback
* User interaction

AI inference happens on the backend.

**Reason**

Keeps the mobile app lightweight and allows faster iteration on AI components.

---

## D-006: On-Demand Vision Processing

**Decision**

The system analyzes the latest camera frame only when the user asks a question.

**Reason**

Continuous perception adds complexity and unnecessary cost for the POC.

---

## D-007: Conversation Memory Is Required

**Decision**

The assistant maintains short-term conversation history.

**Reason**

Natural interactions require multi-turn understanding.

Example:

User:
"What is this?"

User:
"What color is it?"

The second question depends on previous context.

---

## D-008: VLM-First Visual Understanding for POC

**Decision**

The initial implementation relies heavily on the Vision-Language Model.

Dedicated perception modules are postponed.

**Future Extensions**

* Grounding Provider
* Depth Provider

**Reason**

A VLM provides enough capability for the initial demo while keeping implementation simple.

---

## D-009: OCR as a Separate Capability

**Decision**

OCR is represented as its own provider even if initially implemented through the VLM.

**Reason**

Reading text is a distinct accessibility capability and may later use specialized models.

---

## D-010: Avoid Early Agentic Tool Calling

**Decision**

Do not let the LLM dynamically decide which tools/providers to call in the POC.

**Reason**

Agentic orchestration introduces complexity before the core experience is validated.

The architecture should support it later.

---

## D-011: Flutter for Mobile Application

**Decision**

Use Flutter for the mobile client.

**Reason**

Provides a fast cross-platform development path with good camera and audio support.

---

## D-012: Cloud-Based Inference

**Decision**

Use external AI providers/backend inference instead of running models locally.

**Reason**

The available hardware and timeline favor rapid development over local optimization.

---

## D-013: Design for Future Spatial Understanding

**Decision**

Keep placeholders for:

* Grounding
* Depth estimation
* Navigation

**Reason**

Spatial understanding is important for the long-term vision but outside the POC scope.

---

## D-014: Scoped `.gitignore` Files Per Language Root

**Decision**

Use a minimal root `.gitignore` for cross-cutting, OS/editor/secret patterns only. Each
language root (`backend/`, `mobile/`) owns a `.gitignore` scoped to its own toolchain.

**Reason**

The original root `.gitignore` was a Python template. Its `lib/` pattern silently matched
Flutter's `mobile/lib/` source root, causing every historical mobile commit to exclude the
actual app code. A single shared ignore file across a polyglot monorepo is a recurring
footgun; scoping ignore files to their language root prevents one toolchain's conventions
from silently deleting another's source tree.

---

## D-016: Deploy the Backend on Vercel via `[tool.vercel]` Entrypoint

**Decision**

Deploy the FastAPI backend on Vercel's Python runtime (Fluid Compute). Point Vercel at the
existing `app.main:app` instance through `[tool.vercel] entrypoint` in `pyproject.toml`
rather than creating a wrapper file or moving the app under an `api/` directory.

**Reason**

Vercel's FastAPI framework detection supports a configurable entrypoint, so the existing
package layout (`app/main.py`, `app/api/`, `app/services/`, `app/providers/`) stays
untouched. Fluid Compute's 300s ceiling comfortably covers the ASR → Vision → OCR → LLM →
TTS chain, and Vercel's Git-integration deploys give preview URLs on every PR for free.

---

## D-017: Hybrid Architecture — Specialist Models Behind Provider Interfaces, With VLM Fallback

**Decision**

For tasks where general VLM accuracy is insufficient (Egyptian currency, authentic
dialect speech), add a dedicated specialist provider implementing the existing
provider-interface pattern, tried first when configured, falling back to the general
VLM/Groq path otherwise. Never require the specialist to be present for the app to work.

**Reason**

D-008 chose VLM-first for the POC because a single general model minimizes integration
surface. That tradeoff broke down for two accuracy-critical, culturally-specific tasks:
Egyptian banknotes (several denominations look similar; a general VLM performs poorly)
and Egyptian-dialect speech (the original TTS voice was Saudi-accented). Rather than
replacing the VLM-first architecture, this extends it: the provider-interface boundary
already established in D-003 makes "try a specialist, fall back to the general model"
a natural addition, not a redesign.

---

## D-018: Money Mode Is a Dedicated Button, Not Routed Through Voice

**Decision**

Currency detection via the specialist provider is reachable two ways: a dedicated
"Money" button (captures a photo, skips ASR/LLM entirely, calls `POST
/currency-lookup` directly) and the existing voice flow (transcript keyword routes to
the `currency` VisionTask through `POST /conversation`, same as any other intent).

**Reason**

An accurate, fast money check depends on knowing the user's intent before transcription
finishes — but ASR happens server-side, so a purely voice-driven flow cannot skip that
round-trip. A dedicated button removes the dependency on ASR/LLM for the single most
time-critical, common use case (reading cash at a counter) without removing the voice
path, which stays useful for follow-up or combined questions ("how much is this and is
it real").

**Retraction (added after implementation review):** the original design spec's D-1/D-2
promised Money Mode would be fully offline and instant, on the assumption of an
on-device TFLite/CoreML model. D-017 documents why that was abandoned (no free
pretrained weights exist) in favor of a hosted Roboflow API call. That pivot means
Money Mode now requires network connectivity like every other feature in this app —
the offline/instant guarantee from D-1/D-2 no longer holds and should not be treated as
current. What Money Mode still delivers, and the actual reason for this decision: a
faster, more accurate path than the general voice flow, not an offline one.

---

## D-019: TTS Failure Falls Back to the Device's Voice, Not to the Old Cloud Voice

**Decision**

When the Egyptian-dialect TTS provider (`EgyptianTTSProvider`) fails, the backend
returns `tts_fallback_required: true` with empty audio rather than silently retrying
with `GroqTTSProvider`'s Saudi voice. The mobile client is responsible for speaking the
response text locally, using the phone's built-in offline Arabic voice.

**Reason**

The entire point of adding Egyptian TTS was that the Saudi voice sounds foreign to the
target users. Falling back to it on failure would silently reintroduce the exact
problem this work set out to fix, and the failure would be invisible (a user might
never know the app briefly reverted to a different accent). Falling back to the
device's own voice is honest about the tradeoff (authentic accent unavailable right
now) rather than silently substituting a different wrong answer.

---

## D-020: Barcode Lookup Excludes Price

**Decision**

`ProductLookupProvider`/Open Food Facts integration returns product identity,
ingredients, and allergens. It does not return price, and no price field exists in the
schema.

**Reason**

No free, reliable, real-time retail-price data source exists. Promising price lookup
without one would ship a feature that either silently returns nothing or requires a
paid API this project doesn't have budget for. Better to scope the feature to what a
free data source genuinely supports than to build a half-working promise.

---

## D-021: Multi-Turn Memory Uses Client-Supplied History, Not Server-Side Persistence

**Decision**

`ConversationResponse.transcript` is now always returned (not just under `debug: true`),
and the mobile app accumulates `ConversationTurn`s locally and sends them as
`request.history` with each `/conversation` call. No new backend storage (Redis,
Postgres, etc.) was added; `InMemorySessionStore` remains, unused as a fallback for
history when the client omits it.

**Reason**

`ConversationService.handle()` already preferred `request.history` over the server-side
session store, but the mobile client never populated it, and the backend runs on
Vercel's serverless functions where an in-process dict does not reliably survive across
invocations/cold starts anyway. Threading history through the client closes the actual
gap with zero new infrastructure, cost, or secrets — the alternative (an external
session store) would have been a real infra decision needing the user's sign-off, which
wasn't necessary once the simpler fix was visible.

---

## D-022: Roboflow Currency Model Confirmed Not to Detect Real Banknotes (This Version)

**Finding**

Tested `RoboflowCurrencyProvider` against 7 real images total, across two rounds:
- Round 1 (5 images): official Wikimedia Commons reference photos — the 10 EGP and
  20 EGP polymer notes, the 100 EGP note, an older 1-pound bill, and one non-currency
  control image.
- Round 2 (2 images, after digging into *why*): a clean single-note press photo, and a
  genuinely natural/candid real-world photo (a Wiki Loves Africa contest submission
  showing cash and tickets, 6000×4000, Nikon D5300) — tested at both full resolution
  and resized to 640px, and against both of the model's known hostnames
  (`detect.roboflow.com` and its registered `serverless.roboflow.com` endpoint).

Every request across both rounds returned an empty `predictions` list, at confidence
thresholds down to 1%.

**This is not a low-quality or undeployed model.** Queried Roboflow's own project API
directly (`api.roboflow.com/banha-university-dxs4z/egyptian-currency-psnkr/1`): the
project has 4,787 annotated images across 12 classes, built by Banha University, and
version 1 (the only version with an actual deployed model — versions 2 and 3 are
dataset-only, `"models": {}`) reports **99.50% mAP, 96.29% recall, 96.56% precision**
on its own held-out test set. The API integration is unambiguously correct: 200 OK,
correct response shape, correct project/version, both possible hostnames tried.

**Most likely explanation**: a train/deploy distribution gap. The model's excellent
metrics are measured against a held-out split of its *own* training images, which were
very likely collected under fairly homogeneous conditions (e.g. a specific team's
capture setup). None of our 7 test images — spanning official press photos, a
historical bill, and a genuinely natural phone-camera-style photo from an unrelated
source — matched whatever that training distribution actually looks like closely
enough to fire, despite the model excelling on its own test set. This is a well-known
generalization problem with small/narrow academic datasets, not a bug in
`RoboflowCurrencyProvider` or the request format.

**Consequence**

`RoboflowCurrencyProvider` currently defers to the VLM fallback for every real currency
query in production. The D-017 hybrid architecture handles this gracefully (no user
ever sees a broken response), and D-023's prompt sharpening improves the fallback
path's own accuracy. But the "specialist tried first" path is not adding value with
this specific model right now. Next step, if this still matters: test with an actual
phone-camera photo of a real banknote from this project's own target hardware (closer
to the model's real-world use case than any of the 7 test images tried so far), or
evaluate an alternative Roboflow Universe project (e.g. "New Egyptian Currency Object
Detection Dataset" by Belal Safy, or "EgyCurrency-Detectron") — unverified candidates,
not yet tested.

---

## D-023: Responses Must Spell Out Numbers as Arabic Words, Never Digits

**Decision**

`vision_system` and `llm_system` now explicitly require every number in a response to
be spelled out as an Arabic word (e.g. عشرين، خمسين، مية) rather than written as a
digit (20, ٢٠, 50). `currency_instruction` was also sharpened to prioritize reading the
denomination actually printed on a note over a general color/size impression, and to
state uncertainty honestly rather than guess.

**Reason**

Reported bug: spoken amounts were inaccurate and the Egyptian voice mispronounced
numbers. Both TTS paths (the cloud Egyptian voice and the on-device Arabic fallback)
read numeral digits inconsistently/incorrectly regardless of engine — spelling numbers
out as words in the source text sidesteps the whole class of problem rather than
depending on either TTS engine's numeral-reading behavior. `CurrencyLookupService`'s
specialist-path phrases (`DENOMINATION_PHRASES_AR`) already used words, not digits; this
closed the same gap for the LLM/VLM-generated paths, which is where it actually
mattered given D-022 means most real Money Mode use goes through the VLM fallback right
now, not the specialist path.
