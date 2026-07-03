# Mobile Money Mode, Barcode Scanning, and TTS Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two dedicated one-tap actions to the mobile app (Money, Scan barcode) alongside the existing hold-to-ask flow, and wire in the on-device Arabic TTS fallback for whenever cloud speech synthesis is unavailable (`tts_fallback_required`, added to the backend in an earlier plan but never consumed by the mobile client).

**Architecture:** A small new backend endpoint (`POST /currency-lookup`) gives the Money button a fast, non-conversational path to the currency specialist added in the previous plan (no ASR/LLM round-trip needed for "how much is this"). Barcode scanning reuses the existing `POST /product-lookup` endpoint from an earlier plan and composes the spoken sentence entirely on-device (structured product data doesn't need a cloud voice). Both new mobile flows, plus the existing conversation flow, share one `OsTtsFallbackService` (wrapping `flutter_tts`) that `ConversationState.playLastResponse()` uses whenever a response's `ttsFallbackRequired` is `true` instead of trying to play empty/absent cloud audio.

**Tech Stack:** `flutter_tts` (new dependency, on-device Arabic TTS), `mobile_scanner` (new dependency, camera-based barcode scanning), the existing provider-interface pattern on the backend.

## Global Constraints

- `ConversationResponse.ttsFallbackRequired` must be checked by `playLastResponse()` for **every** flow that produces a response (conversation, money, barcode) — a response with empty `audioBase64` must never be silently handed to `AudioPlaybackService`, which has no meaningful empty-audio behavior defined.
- Barcode lookup results are always spoken via the on-device OS voice (`ttsFallbackRequired: true` unconditionally) — this is a deliberate simplification, not a bug: structured product/ingredient text doesn't need the cloud Egyptian voice, and this avoids adding TTS to `/product-lookup`'s contract.
- Every new production module gets test coverage. Flutter widgets that wrap real hardware (camera, barcode scanner) are verified via `flutter analyze` plus the existing testable business-logic layer (`ConversationState`), matching this app's established pattern for `CameraMediaCaptureService`.

---

### Task 1: Backend — `CurrencyLookupRequest`/`CurrencyLookupResponse` schemas

**Files:**
- Modify: `backend/app/schemas/currency.py`
- Test: `backend/tests/unit/test_common_schemas.py` (create a new `test_currency_schemas.py` instead, to keep one file per schema module, matching `test_product_schemas.py`)
- Create: `backend/tests/unit/test_currency_schemas.py`

**Interfaces:**
- Produces: `CurrencyLookupRequest` (image_base64), `CurrencyLookupResponse` (found, denomination, confidence, spoken_text, audio_base64, tts_fallback_required) — consumed by Tasks 2, 3.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_currency_schemas.py`:

```python
from app.schemas.currency import CurrencyLookupRequest, CurrencyLookupResponse


def test_currency_lookup_request_accepts_image():
    request = CurrencyLookupRequest(image_base64="aW1hZ2U=")

    assert request.image_base64 == "aW1hZ2U="


def test_currency_lookup_response_defaults():
    response = CurrencyLookupResponse(found=False, spoken_text="Not sure.")

    assert response.found is False
    assert response.denomination is None
    assert response.confidence is None
    assert response.audio_base64 == ""
    assert response.tts_fallback_required is False


def test_currency_lookup_response_with_detection():
    response = CurrencyLookupResponse(
        found=True,
        denomination="20 EGP",
        confidence=0.92,
        spoken_text="This looks like 20 EGP.",
        audio_base64="d2F2",
    )

    assert response.denomination == "20 EGP"
    assert response.confidence == 0.92
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/unit/test_currency_schemas.py -v`
Expected: FAIL with `ImportError: cannot import name 'CurrencyLookupRequest'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/schemas/currency.py`, add to the end of the existing file (which currently only has `CurrencyDetectionResult`):

```python
class CurrencyLookupRequest(BaseModel):
    image_base64: str = Field(min_length=1)


class CurrencyLookupResponse(BaseModel):
    found: bool
    denomination: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    spoken_text: str = Field(min_length=1)
    audio_base64: str = ""
    tts_fallback_required: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/unit/test_currency_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/currency.py backend/tests/unit/test_currency_schemas.py
git commit -m "feat: add CurrencyLookupRequest/Response schemas"
```

---

### Task 2: Backend — `CurrencyLookupService`

**Files:**
- Create: `backend/app/services/currency_lookup_service.py`
- Test: `backend/tests/unit/test_currency_lookup_service.py`

**Interfaces:**
- Consumes: `CurrencyDetectionProvider`, `VisionProvider`, `TTSProvider`, `TTSUnavailableError`, `CurrencyLookupResponse` (Task 1), `FakeVisionProvider`/`FakeTTSProvider`/`FakeCurrencyDetectionProvider`/`FakeFailingTTSProvider` (existing fakes).
- Produces: `CurrencyLookupService` — consumed by Task 3.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_currency_lookup_service.py`:

```python
from app.providers.fakes import (
    FakeCurrencyDetectionProvider,
    FakeFailingTTSProvider,
    FakeTTSProvider,
    FakeVisionProvider,
)
from app.services.currency_lookup_service import CurrencyLookupService


def test_currency_lookup_uses_specialist_when_confident():
    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeTTSProvider(),
        currency_detector=FakeCurrencyDetectionProvider(),
    )

    response = service.handle(b"fake-image-bytes")

    assert response.found is True
    assert response.denomination == "20 EGP"
    assert "20 EGP" in response.spoken_text
    assert response.audio_base64 != ""


def test_currency_lookup_falls_back_to_vlm_without_detector():
    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeTTSProvider(),
        currency_detector=None,
    )

    response = service.handle(b"fake-image-bytes")

    assert response.found is False
    assert response.denomination is None
    assert response.spoken_text  # VLM's fake summary still produces text


def test_currency_lookup_sets_fallback_flag_when_tts_unavailable():
    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeFailingTTSProvider(),
        currency_detector=FakeCurrencyDetectionProvider(),
    )

    response = service.handle(b"fake-image-bytes")

    assert response.tts_fallback_required is True
    assert response.audio_base64 == ""
    assert response.spoken_text  # text must still be present for the OS-voice fallback
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/unit/test_currency_lookup_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.currency_lookup_service'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/currency_lookup_service.py`:

```python
from __future__ import annotations

import base64
from dataclasses import dataclass

from app.providers.base import CurrencyDetectionProvider, TTSProvider, TTSUnavailableError, VisionProvider
from app.schemas.common import VisionTask
from app.schemas.currency import CurrencyLookupResponse


@dataclass
class CurrencyLookupService:
    vision: VisionProvider
    tts: TTSProvider
    currency_detector: CurrencyDetectionProvider | None = None

    CURRENCY_CONFIDENCE_THRESHOLD = 0.6

    def handle(self, image_bytes: bytes) -> CurrencyLookupResponse:
        currency_result = self.currency_detector.detect_currency(image_bytes) if self.currency_detector else None

        if currency_result is not None and currency_result.confidence >= self.CURRENCY_CONFIDENCE_THRESHOLD:
            found = True
            denomination = currency_result.denomination
            confidence = currency_result.confidence
            spoken_text = f"This looks like {currency_result.denomination}."
        else:
            found = False
            denomination = None
            confidence = None
            spoken_text = self.vision.analyze(
                image_bytes,
                "What Egyptian currency denomination is shown in this image?",
                [],
                task=VisionTask.currency,
            )

        tts_fallback_required = False
        try:
            speech_bytes = self.tts.synthesize_speech(spoken_text)
        except TTSUnavailableError:
            speech_bytes = b""
            tts_fallback_required = True

        return CurrencyLookupResponse(
            found=found,
            denomination=denomination,
            confidence=confidence,
            spoken_text=spoken_text,
            audio_base64=base64.b64encode(speech_bytes).decode("ascii"),
            tts_fallback_required=tts_fallback_required,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/unit/test_currency_lookup_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/currency_lookup_service.py backend/tests/unit/test_currency_lookup_service.py
git commit -m "feat: add CurrencyLookupService for the Money Mode fast path"
```

---

### Task 3: Backend — `POST /currency-lookup` endpoint + `create_app()` wiring

**Files:**
- Create: `backend/app/api/currency.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/integration/test_currency_api.py`, `backend/tests/unit/test_main.py`

**Interfaces:**
- Consumes: `CurrencyLookupService` (Task 2), `CurrencyLookupRequest`/`Response` (Task 1).
- Produces: the running app now serves `/currency-lookup` alongside `/conversation`, `/product-lookup`, and `/health`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/integration/test_currency_api.py`:

```python
import base64

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.currency import create_currency_router
from app.providers.fakes import FakeCurrencyDetectionProvider, FakeTTSProvider, FakeVisionProvider
from app.services.currency_lookup_service import CurrencyLookupService


def make_client() -> TestClient:
    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeTTSProvider(),
        currency_detector=FakeCurrencyDetectionProvider(),
    )
    app = FastAPI()
    app.include_router(create_currency_router(service))
    return TestClient(app)


def test_currency_lookup_endpoint_returns_detection():
    client = make_client()

    response = client.post(
        "/currency-lookup",
        json={"image_base64": base64.b64encode(b"fake-image-bytes").decode("ascii")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["denomination"] == "20 EGP"


def test_currency_lookup_endpoint_rejects_invalid_base64():
    client = make_client()

    response = client.post("/currency-lookup", json={"image_base64": "not-valid-base64!!!"})

    assert response.status_code == 400
```

Add to `backend/tests/unit/test_main.py`:

```python
def test_create_app_registers_currency_lookup_route():
    app = create_app()

    paths = {route.path for route in app.routes}
    assert "/currency-lookup" in paths
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/integration/test_currency_api.py tests/unit/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.api.currency'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/api/currency.py`:

```python
from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException

from app.schemas.common import ErrorResponse
from app.schemas.currency import CurrencyLookupRequest, CurrencyLookupResponse
from app.services.currency_lookup_service import CurrencyLookupService


def create_currency_router(service: CurrencyLookupService) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/currency-lookup",
        response_model=CurrencyLookupResponse,
        responses={400: {"model": ErrorResponse}},
    )
    def post_currency_lookup(payload: CurrencyLookupRequest) -> CurrencyLookupResponse:
        try:
            image_bytes = base64.b64decode(payload.image_base64, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(code="invalid_request", message="Invalid base64 payload for image_base64").model_dump(),
            ) from exc
        return service.handle(image_bytes)

    return router
```

In `backend/app/main.py`, add the imports:

```python
from app.api.currency import create_currency_router
from app.services.currency_lookup_service import CurrencyLookupService
```

Then, after the existing `product_lookup_provider = (...)` line, add a `CurrencyLookupService` construction shared by both branches (it needs `vision`, `tts`, and `currency_detector`, all of which already exist as local variables or are easy to reconstruct per branch):

```python
    if settings.use_real_providers:
        currency_lookup_service = CurrencyLookupService(
            vision=GroqVisionProvider(model=settings.groq_multimodal_model, prompts=prompts),
            tts=EgyptianTTSProvider(space_id=settings.egyptian_tts_space_id),
            currency_detector=currency_detector,
        )
    else:
        currency_lookup_service = CurrencyLookupService(
            vision=FakeVisionProvider(),
            tts=FakeTTSProvider(),
            currency_detector=None,
        )
```

(Place this new `if/else` block right after the existing `product_lookup_provider = (...)` line, before the `app = FastAPI(...)` line. Note this constructs a second `GroqVisionProvider`/`EgyptianTTSProvider` instance in real mode, separate from the ones inside `ConversationService` -- this is intentional and matches this file's existing style of constructing providers inline per use, not sharing instances across services.)

Finally, add the new router:

```python
    app.include_router(create_conversation_router(service))
    app.include_router(create_product_router(product_lookup_provider))
    app.include_router(create_currency_router(currency_lookup_service))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/integration/test_currency_api.py tests/unit/test_main.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python3 -m pytest -v`
Expected: all tests pass (the existing 101 plus every test added in Tasks 1-3).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/currency.py backend/app/main.py backend/tests/integration/test_currency_api.py backend/tests/unit/test_main.py
git commit -m "feat: add POST /currency-lookup endpoint for the mobile Money button"
```

---

### Task 4: Mobile — parse `ttsFallbackRequired`, add currency/product models

**Files:**
- Modify: `mobile/lib/features/conversation/models.dart`
- Test: `mobile/test/models_test.dart`

**Interfaces:**
- Produces: `ConversationResponse.ttsFallbackRequired`, `CurrencyLookupResponse`, `ProductInfo`, `ProductLookupResponse` — consumed by Tasks 5, 6, 7.

- [ ] **Step 1: Write the failing test**

`mobile/test/models_test.dart` currently has two tests inside one `main() { ... }` block, each a plain `test('...', () { ... })` call with `expect(...)` assertions — no setup/teardown, no groups. Add four new tests in that same style, inside the existing `main()` block:

```dart
test('ConversationResponse parses tts_fallback_required, defaulting to false', () {
  final withFlag = ConversationResponse.fromJson({
    'session_id': 's1',
    'text': 'hello',
    'audio_base64': '',
    'tts_fallback_required': true,
  });
  final withoutFlag = ConversationResponse.fromJson({
    'session_id': 's1',
    'text': 'hello',
    'audio_base64': 'd2F2',
  });

  expect(withFlag.ttsFallbackRequired, isTrue);
  expect(withoutFlag.ttsFallbackRequired, isFalse);
});

test('CurrencyLookupResponse parses a confident detection', () {
  final response = CurrencyLookupResponse.fromJson({
    'found': true,
    'denomination': '20 EGP',
    'confidence': 0.92,
    'spoken_text': 'This looks like 20 EGP.',
    'audio_base64': 'd2F2',
    'tts_fallback_required': false,
  });

  expect(response.found, isTrue);
  expect(response.denomination, '20 EGP');
  expect(response.confidence, 0.92);
});

test('ProductLookupResponse parses a found product', () {
  final response = ProductLookupResponse.fromJson({
    'found': true,
    'product': {
      'name': 'Sample Product',
      'brand': 'Sample Brand',
      'ingredients_text': 'water, sugar',
      'allergens': ['milk'],
    },
  });

  expect(response.found, isTrue);
  expect(response.product?.name, 'Sample Product');
  expect(response.product?.allergens, ['milk']);
});

test('ProductLookupResponse parses a not-found result', () {
  final response = ProductLookupResponse.fromJson({'found': false, 'product': null});

  expect(response.found, isFalse);
  expect(response.product, isNull);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && flutter test test/models_test.dart`
Expected: FAIL — `ttsFallbackRequired` doesn't exist on `ConversationResponse`, and `CurrencyLookupResponse`/`ProductLookupResponse`/`ProductInfo` don't exist yet.

- [ ] **Step 3: Write minimal implementation**

In `mobile/lib/features/conversation/models.dart`, change the `ConversationResponse` class from:

```dart
class ConversationResponse {
  ConversationResponse({
    required this.sessionId,
    required this.text,
    required this.audioBase64,
    this.debug,
  });

  final String sessionId;
  final String text;
  final String audioBase64;
  final ConversationDebug? debug;

  factory ConversationResponse.fromJson(Map<String, dynamic> json) {
    return ConversationResponse(
      sessionId: json['session_id'] as String,
      text: json['text'] as String,
      audioBase64: json['audio_base64'] as String,
      debug: json['debug'] != null
          ? ConversationDebug.fromJson(json['debug'] as Map<String, dynamic>)
          : null,
    );
  }
}
```

to:

```dart
class ConversationResponse {
  ConversationResponse({
    required this.sessionId,
    required this.text,
    required this.audioBase64,
    this.ttsFallbackRequired = false,
    this.debug,
  });

  final String sessionId;
  final String text;
  final String audioBase64;
  final bool ttsFallbackRequired;
  final ConversationDebug? debug;

  factory ConversationResponse.fromJson(Map<String, dynamic> json) {
    return ConversationResponse(
      sessionId: json['session_id'] as String,
      text: json['text'] as String,
      audioBase64: json['audio_base64'] as String,
      ttsFallbackRequired: json['tts_fallback_required'] as bool? ?? false,
      debug: json['debug'] != null
          ? ConversationDebug.fromJson(json['debug'] as Map<String, dynamic>)
          : null,
    );
  }
}
```

Then append these new classes to the end of the file:

```dart
class CurrencyLookupResponse {
  CurrencyLookupResponse({
    required this.found,
    this.denomination,
    this.confidence,
    required this.spokenText,
    this.audioBase64 = '',
    this.ttsFallbackRequired = false,
  });

  final bool found;
  final String? denomination;
  final double? confidence;
  final String spokenText;
  final String audioBase64;
  final bool ttsFallbackRequired;

  factory CurrencyLookupResponse.fromJson(Map<String, dynamic> json) {
    return CurrencyLookupResponse(
      found: json['found'] as bool,
      denomination: json['denomination'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
      spokenText: json['spoken_text'] as String,
      audioBase64: json['audio_base64'] as String? ?? '',
      ttsFallbackRequired: json['tts_fallback_required'] as bool? ?? false,
    );
  }
}

class ProductInfo {
  ProductInfo({
    required this.name,
    this.brand,
    this.ingredientsText,
    this.allergens = const [],
  });

  final String name;
  final String? brand;
  final String? ingredientsText;
  final List<String> allergens;

  factory ProductInfo.fromJson(Map<String, dynamic> json) {
    return ProductInfo(
      name: json['name'] as String,
      brand: json['brand'] as String?,
      ingredientsText: json['ingredients_text'] as String?,
      allergens: List<String>.from(json['allergens'] as List? ?? const []),
    );
  }
}

class ProductLookupResponse {
  ProductLookupResponse({required this.found, this.product});

  final bool found;
  final ProductInfo? product;

  factory ProductLookupResponse.fromJson(Map<String, dynamic> json) {
    return ProductLookupResponse(
      found: json['found'] as bool,
      product: json['product'] != null
          ? ProductInfo.fromJson(json['product'] as Map<String, dynamic>)
          : null,
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile && flutter test test/models_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/features/conversation/models.dart mobile/test/models_test.dart
git commit -m "feat: parse ttsFallbackRequired and add currency/product response models"
```

---

### Task 5: Mobile — `OsTtsFallbackService` + wire into `playLastResponse()`

**Files:**
- Modify: `mobile/pubspec.yaml`
- Create: `mobile/lib/features/conversation/os_tts_fallback.dart`
- Modify: `mobile/lib/features/conversation/conversation_state.dart`
- Modify: `mobile/lib/main.dart`
- Test: `mobile/test/conversation_state_test.dart`

**Interfaces:**
- Consumes: `ConversationResponse.ttsFallbackRequired` (Task 4).
- Produces: `OsTtsFallbackService` (abstract) + `FlutterOsTtsFallbackService` (real) — consumed by Tasks 6, 7 (Money and barcode both call `playLastResponse()`, which now checks this flag).

- [ ] **Step 1: Add the `flutter_tts` dependency**

In `mobile/pubspec.yaml`, add `flutter_tts: ^4.2.5` to `dependencies` (alongside the existing `google_fonts: ^6.2.1`):

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.2
  just_audio: ^0.10.6
  path_provider: ^2.1.6
  record: ^7.1.1
  camera: ^0.12.0+1
  permission_handler: ^12.0.3
  provider: ^6.1.2
  image: ^4.3.0
  google_fonts: ^6.2.1
  flutter_tts: ^4.2.5
```

Run: `cd mobile && flutter pub get`

- [ ] **Step 2: Write the failing test**

Add to `mobile/test/conversation_state_test.dart`, a fake implementing a new `OsTtsFallbackService` interface:

```dart
class FakeOsTtsFallbackService implements OsTtsFallbackService {
  String? spokenText;

  @override
  Future<void> speak(String text) async {
    spokenText = text;
  }
}
```

(Add `import 'package:be_my_eye/features/conversation/os_tts_fallback.dart';` to the file's imports.)

Then add a new test:

```dart
test('ConversationState speaks locally when tts_fallback_required is true', () async {
  final backendClient = FakeBackendClient();
  final audioPlaybackService = FakeAudioPlaybackService();
  final osTtsFallbackService = FakeOsTtsFallbackService();
  final state = ConversationState(
    backendClient: backendClient,
    mediaCaptureService: FakeMediaCaptureService(),
    audioPlaybackService: audioPlaybackService,
    osTtsFallbackService: osTtsFallbackService,
  );

  state.debugSetResponseForTest('the answer', ttsFallbackRequired: true);
  await state.playLastResponse();

  expect(osTtsFallbackService.spokenText, 'the answer');
  expect(audioPlaybackService.playedAudioBase64, isNull);
});
```

This requires `debugSetResponseForTest` to accept an optional `ttsFallbackRequired` parameter -- update its existing declaration (find it via `grep -n debugSetResponseForTest mobile/lib/features/conversation/conversation_state.dart`) to add `bool ttsFallbackRequired = false` as a new optional parameter, and pass it through to the `ConversationResponse` it constructs.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd mobile && flutter test test/conversation_state_test.dart`
Expected: FAIL — `OsTtsFallbackService` doesn't exist, and `ConversationState`'s constructor doesn't accept `osTtsFallbackService`.

- [ ] **Step 4: Write minimal implementation**

Create `mobile/lib/features/conversation/os_tts_fallback.dart`:

```dart
import 'package:flutter_tts/flutter_tts.dart';

/// Speaks text using the phone's built-in offline Arabic voice. Used when
/// cloud Egyptian TTS synthesis failed (ConversationResponse.ttsFallbackRequired)
/// so the user always hears an answer, even without a natural Egyptian accent.
abstract class OsTtsFallbackService {
  Future<void> speak(String text);
}

class FlutterOsTtsFallbackService implements OsTtsFallbackService {
  FlutterOsTtsFallbackService({FlutterTts? tts}) : _tts = tts ?? FlutterTts() {
    _tts.setLanguage('ar');
  }

  final FlutterTts _tts;

  @override
  Future<void> speak(String text) async {
    await _tts.speak(text);
  }
}
```

In `mobile/lib/features/conversation/conversation_state.dart`, add the import:

```dart
import 'os_tts_fallback.dart';
```

Update the constructor and fields:

```dart
class ConversationState extends ChangeNotifier {
  ConversationState({
    required BackendClient backendClient,
    required MediaCaptureService mediaCaptureService,
    required AudioPlaybackService audioPlaybackService,
    required OsTtsFallbackService osTtsFallbackService,
    this.debug = false,
  })  : _backendClient = backendClient,
        _mediaCaptureService = mediaCaptureService,
        _audioPlaybackService = audioPlaybackService,
        _osTtsFallbackService = osTtsFallbackService;

  final BackendClient _backendClient;
  final MediaCaptureService _mediaCaptureService;
  final AudioPlaybackService _audioPlaybackService;
  final OsTtsFallbackService _osTtsFallbackService;
  final bool debug;
```

Change `playLastResponse()` from:

```dart
  Future<void> playLastResponse() async {
    final response = _lastResponse;
    if (response == null) {
      return;
    }
    await _audioPlaybackService.playBase64Audio(response.audioBase64);
  }
```

to:

```dart
  Future<void> playLastResponse() async {
    final response = _lastResponse;
    if (response == null) {
      return;
    }
    if (response.ttsFallbackRequired) {
      await _osTtsFallbackService.speak(response.text);
    } else {
      await _audioPlaybackService.playBase64Audio(response.audioBase64);
    }
  }
```

Update `debugSetResponseForTest` to accept the new optional parameter:

```dart
  @visibleForTesting
  void debugSetResponseForTest(String text, {bool ttsFallbackRequired = false}) {
    _lastResponse = ConversationResponse(
      sessionId: 'test-session',
      text: text,
      audioBase64: 'test-audio',
      ttsFallbackRequired: ttsFallbackRequired,
    );
    notifyListeners();
  }
```

In `mobile/lib/main.dart`, add the import and pass the new required constructor parameter:

```dart
import 'features/conversation/os_tts_fallback.dart';
```

```dart
      create: (_) => ConversationState(
        backendClient: BackendClient(baseUrl: _backendUrl),
        mediaCaptureService: CameraMediaCaptureService(),
        audioPlaybackService: JustAudioPlaybackService(),
        osTtsFallbackService: FlutterOsTtsFallbackService(),
      ),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd mobile && flutter test`
Expected: PASS (all tests, since every existing `ConversationState(...)` construction site in the test file needs the new required `osTtsFallbackService` parameter -- add `osTtsFallbackService: FakeOsTtsFallbackService()` to each one you find via `grep -n "ConversationState(" mobile/test/conversation_state_test.dart`).

- [ ] **Step 6: Commit**

```bash
git add mobile/pubspec.yaml mobile/pubspec.lock mobile/lib/features/conversation/os_tts_fallback.dart mobile/lib/features/conversation/conversation_state.dart mobile/lib/main.dart mobile/test/conversation_state_test.dart
git commit -m "feat: add OsTtsFallbackService and wire tts_fallback_required into playLastResponse"
```

---

### Task 6: Mobile — Money Mode button

**Files:**
- Modify: `mobile/lib/features/conversation/backend_client.dart`
- Modify: `mobile/lib/features/conversation/conversation_state.dart`
- Modify: `mobile/lib/features/conversation/conversation_screen.dart`
- Test: `mobile/test/conversation_state_test.dart`

**Interfaces:**
- Consumes: `CurrencyLookupResponse` (Task 4), `OsTtsFallbackService`-aware `playLastResponse()` (Task 5).
- Produces: `ConversationState.captureAndLookupCurrency()` — a standalone action independent of the hold-to-ask flow.

- [ ] **Step 1: Write the failing test**

Add to `mobile/test/conversation_state_test.dart`. First, extend `FakeBackendClient` with the new method:

```dart
class FakeBackendClient extends BackendClient {
  FakeBackendClient() : super(baseUrl: 'http://localhost');

  ConversationRequest? lastRequest;
  String? lastCurrencyImageBase64;

  @override
  Future<ConversationResponse> sendConversation(ConversationRequest request) async {
    lastRequest = request;
    return ConversationResponse(
      sessionId: request.sessionId,
      text: 'assistant reply',
      audioBase64: 'response-audio',
    );
  }

  @override
  Future<CurrencyLookupResponse> lookupCurrency(String imageBase64) async {
    lastCurrencyImageBase64 = imageBase64;
    return CurrencyLookupResponse(
      found: true,
      denomination: '20 EGP',
      confidence: 0.92,
      spokenText: 'This looks like 20 EGP.',
      audioBase64: 'currency-audio',
    );
  }
}
```

(`FakeBackendClient` already exists in this file with the `sendConversation` override -- add `lookupCurrency` to the same class, plus the new import `import 'package:be_my_eye/features/conversation/models.dart';` if `CurrencyLookupResponse` isn't already reachable through an existing import.)

Then add:

```dart
test('ConversationState captures a photo and looks up currency', () async {
  final backendClient = FakeBackendClient();
  final mediaCaptureService = FakeMediaCaptureService();
  final audioPlaybackService = FakeAudioPlaybackService();
  final state = ConversationState(
    backendClient: backendClient,
    mediaCaptureService: mediaCaptureService,
    audioPlaybackService: audioPlaybackService,
    osTtsFallbackService: FakeOsTtsFallbackService(),
  );

  await state.captureAndLookupCurrency();

  expect(mediaCaptureService.captureImageCalled, isTrue);
  expect(backendClient.lastCurrencyImageBase64, 'captured-image');
  expect(state.lastResponse?.text, 'This looks like 20 EGP.');
  expect(audioPlaybackService.playedAudioBase64, 'currency-audio');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && flutter test test/conversation_state_test.dart`
Expected: FAIL — `BackendClient` has no `lookupCurrency` method, and `ConversationState` has no `captureAndLookupCurrency` method.

- [ ] **Step 3: Write minimal implementation**

In `mobile/lib/features/conversation/backend_client.dart`, add the new method to the `BackendClient` class:

```dart
  Future<CurrencyLookupResponse> lookupCurrency(String imageBase64) async {
    final uri = Uri.parse('$baseUrl/currency-lookup');
    final response = await _httpClient.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'image_base64': imageBase64}),
    );

    if (response.statusCode != 200) {
      throw BackendException(
        'Backend returned ${response.statusCode}: ${response.body}',
      );
    }

    return CurrencyLookupResponse.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }
```

In `mobile/lib/features/conversation/conversation_state.dart`, add a new method after `submit()`:

```dart
  Future<void> captureAndLookupCurrency() async {
    _lastError = null;
    _lastResponse = null;
    notifyListeners();

    final String imageBase64;
    try {
      imageBase64 = await _mediaCaptureService.captureImageBase64();
    } catch (error) {
      _lastError = 'Could not access the camera: $error';
      notifyListeners();
      return;
    }

    _isBusy = true;
    notifyListeners();

    try {
      final result = await _backendClient.lookupCurrency(imageBase64);
      _lastResponse = ConversationResponse(
        sessionId: 'money-mode',
        text: result.spokenText,
        audioBase64: result.audioBase64,
        ttsFallbackRequired: result.ttsFallbackRequired,
      );
      _lastError = null;
    } catch (error) {
      _lastError = error.toString();
    } finally {
      _isBusy = false;
      notifyListeners();
    }

    await playLastResponse();
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile && flutter test test/conversation_state_test.dart`
Expected: PASS.

- [ ] **Step 5: Add the Money button to the screen**

In `mobile/lib/features/conversation/conversation_screen.dart`, add a Money button positioned near the top of the screen (above the main hold-to-ask target, so it doesn't overlap the existing full-screen `GestureDetector`). Add this as a new child in the `Stack` inside `build()`, right after the existing `if (_isListening) ..._buildPulseRings(),` line:

```dart
                Positioned(
                  top: 48,
                  left: 24,
                  child: Semantics(
                    button: true,
                    label: 'Money',
                    child: IconButton(
                      icon: const Icon(Icons.attach_money, color: _kAccent, size: 32),
                      onPressed: () => context.read<ConversationState>().captureAndLookupCurrency(),
                    ),
                  ),
                ),
```

- [ ] **Step 6: Run `flutter analyze` to confirm the screen still compiles cleanly**

Run: `cd mobile && flutter analyze`
Expected: No issues found.

- [ ] **Step 7: Commit**

```bash
git add mobile/lib/features/conversation/backend_client.dart mobile/lib/features/conversation/conversation_state.dart mobile/lib/features/conversation/conversation_screen.dart mobile/test/conversation_state_test.dart
git commit -m "feat: add Money Mode button (captureAndLookupCurrency)"
```

---

### Task 7: Mobile — Barcode scanning button

**Files:**
- Modify: `mobile/pubspec.yaml`
- Modify: `mobile/lib/features/conversation/backend_client.dart`
- Modify: `mobile/lib/features/conversation/conversation_state.dart`
- Create: `mobile/lib/features/conversation/barcode_scanner_screen.dart`
- Modify: `mobile/lib/features/conversation/conversation_screen.dart`
- Test: `mobile/test/conversation_state_test.dart`

**Interfaces:**
- Consumes: `ProductLookupResponse`, `ProductInfo` (Task 4), `OsTtsFallbackService`-aware `playLastResponse()` (Task 5).
- Produces: `ConversationState.lookupProductByBarcode(String barcode)` — the business-logic half of barcode scanning (testable); `BarcodeScannerScreen` is the hardware-facing half (verified via `flutter analyze` only, matching this app's established pattern for camera/mic code).

- [ ] **Step 1: Add the `mobile_scanner` dependency**

In `mobile/pubspec.yaml`, add `mobile_scanner: ^7.2.0`:

```yaml
  flutter_tts: ^4.2.5
  mobile_scanner: ^7.2.0
```

Run: `cd mobile && flutter pub get`

- [ ] **Step 2: Write the failing test**

Add to `mobile/test/conversation_state_test.dart`. Extend `FakeBackendClient` again:

```dart
  String? lastBarcode;

  @override
  Future<ProductLookupResponse> lookupProduct(String barcode) async {
    lastBarcode = barcode;
    if (barcode == '0000000000000') {
      return ProductLookupResponse(found: false, product: null);
    }
    return ProductLookupResponse(
      found: true,
      product: ProductInfo(
        name: 'Sample Product',
        brand: 'Sample Brand',
        allergens: const ['milk'],
      ),
    );
  }
```

Then add:

```dart
test('ConversationState looks up a product by barcode and describes it', () async {
  final backendClient = FakeBackendClient();
  final state = ConversationState(
    backendClient: backendClient,
    mediaCaptureService: FakeMediaCaptureService(),
    audioPlaybackService: FakeAudioPlaybackService(),
    osTtsFallbackService: FakeOsTtsFallbackService(),
  );

  await state.lookupProductByBarcode('1234567890123');

  expect(backendClient.lastBarcode, '1234567890123');
  expect(state.lastResponse?.text, contains('Sample Product'));
  expect(state.lastResponse?.text, contains('milk'));
  expect(state.lastResponse?.ttsFallbackRequired, isTrue);
});

test('ConversationState reports when a barcode is not found', () async {
  final backendClient = FakeBackendClient();
  final state = ConversationState(
    backendClient: backendClient,
    mediaCaptureService: FakeMediaCaptureService(),
    audioPlaybackService: FakeAudioPlaybackService(),
    osTtsFallbackService: FakeOsTtsFallbackService(),
  );

  await state.lookupProductByBarcode('0000000000000');

  expect(state.lastResponse?.text, contains("couldn't find"));
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd mobile && flutter test test/conversation_state_test.dart`
Expected: FAIL — `BackendClient` has no `lookupProduct` method, `ConversationState` has no `lookupProductByBarcode` method.

- [ ] **Step 4: Write minimal implementation**

In `mobile/lib/features/conversation/backend_client.dart`, add:

```dart
  Future<ProductLookupResponse> lookupProduct(String barcode) async {
    final uri = Uri.parse('$baseUrl/product-lookup');
    final response = await _httpClient.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'barcode': barcode}),
    );

    if (response.statusCode != 200) {
      throw BackendException(
        'Backend returned ${response.statusCode}: ${response.body}',
      );
    }

    return ProductLookupResponse.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }
```

In `mobile/lib/features/conversation/conversation_state.dart`, add:

```dart
  Future<void> lookupProductByBarcode(String barcode) async {
    _lastError = null;
    _lastResponse = null;
    _isBusy = true;
    notifyListeners();

    try {
      final result = await _backendClient.lookupProduct(barcode);
      final text = result.found ? _describeProduct(result.product!) : "I couldn't find a product for this barcode.";
      _lastResponse = ConversationResponse(
        sessionId: 'barcode-mode',
        text: text,
        audioBase64: '',
        ttsFallbackRequired: true,
      );
      _lastError = null;
    } catch (error) {
      _lastError = error.toString();
    } finally {
      _isBusy = false;
      notifyListeners();
    }

    await playLastResponse();
  }

  String _describeProduct(ProductInfo product) {
    final buffer = StringBuffer('This is ${product.name}');
    if (product.brand != null) {
      buffer.write(' by ${product.brand}');
    }
    buffer.write('.');
    if (product.allergens.isNotEmpty) {
      buffer.write(' Contains: ${product.allergens.join(', ')}.');
    }
    return buffer.toString();
  }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd mobile && flutter test test/conversation_state_test.dart`
Expected: PASS.

- [ ] **Step 6: Create the barcode scanner screen**

Create `mobile/lib/features/conversation/barcode_scanner_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

/// Scans a single barcode and pops back with its raw value. All lookup and
/// speech logic lives in ConversationState.lookupProductByBarcode -- this
/// screen only wraps the camera hardware, matching this app's established
/// pattern for hardware-facing code (verified via flutter analyze, not
/// full behavioral tests, since it can't run meaningfully without a device).
class BarcodeScannerScreen extends StatefulWidget {
  const BarcodeScannerScreen({super.key});

  @override
  State<BarcodeScannerScreen> createState() => _BarcodeScannerScreenState();
}

class _BarcodeScannerScreenState extends State<BarcodeScannerScreen> {
  bool _handled = false;

  void _onDetect(BarcodeCapture capture) {
    if (_handled || capture.barcodes.isEmpty) {
      return;
    }
    final rawValue = capture.barcodes.first.rawValue;
    if (rawValue == null) {
      return;
    }
    _handled = true;
    Navigator.of(context).pop(rawValue);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan barcode')),
      body: MobileScanner(onDetect: _onDetect),
    );
  }
}
```

- [ ] **Step 7: Add the barcode button to the screen**

In `mobile/lib/features/conversation/conversation_screen.dart`, add the import:

```dart
import 'barcode_scanner_screen.dart';
```

Add a new method to `_ConversationScreenState`:

```dart
  Future<void> _handleScanBarcode(ConversationState state) async {
    final barcode = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const BarcodeScannerScreen()),
    );
    if (barcode != null) {
      await state.lookupProductByBarcode(barcode);
    }
  }
```

Add a second `Positioned` button in the `Stack`, right after the Money button added in Task 6:

```dart
                Positioned(
                  top: 48,
                  right: 24,
                  child: Semantics(
                    button: true,
                    label: 'Scan barcode',
                    child: IconButton(
                      icon: const Icon(Icons.qr_code_scanner, color: _kAccent, size: 32),
                      onPressed: () => _handleScanBarcode(state),
                    ),
                  ),
                ),
```

- [ ] **Step 8: Run `flutter analyze` and the full test suite**

Run: `cd mobile && flutter analyze && flutter test`
Expected: No issues found; all tests pass.

- [ ] **Step 9: Commit**

```bash
git add mobile/pubspec.yaml mobile/pubspec.lock mobile/lib/features/conversation/backend_client.dart mobile/lib/features/conversation/conversation_state.dart mobile/lib/features/conversation/barcode_scanner_screen.dart mobile/lib/features/conversation/conversation_screen.dart mobile/test/conversation_state_test.dart
git commit -m "feat: add barcode scanning button (lookupProductByBarcode)"
```

---

## Plan Complete

After Task 7, the mobile app has three independent capture actions on one screen: hold-to-ask (voice), Money (one tap, backend currency specialist), and Scan barcode (one tap, camera barcode scan -> product lookup). All three, plus every existing conversation response, correctly fall back to the on-device Arabic voice whenever cloud TTS synthesis fails.

**Not yet done after this plan (tracked for the docs plan and final review):** the Money button's backend accuracy depends entirely on `ROBOFLOW_API_KEY` being configured (see the previous plan's "required manual step") — without it, Money Mode still works, just via the general VLM fallback, identical to asking "how much is this" by voice today.
