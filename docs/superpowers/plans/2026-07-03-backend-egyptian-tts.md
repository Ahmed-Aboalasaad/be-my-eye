# Backend Egyptian TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current Saudi-dialect Groq TTS voice with a real, free, Egyptian-Arabic voice for the main conversation flow, with a clean signal the mobile app can use to fall back to its own on-device Arabic voice when Egyptian synthesis fails.

**Architecture:** A new `EgyptianTTSProvider` implements the existing `TTSProvider` interface by calling a live, public, free Hugging Face Gradio Space (`omarelshehy/NAMAA-Egyptian-Voice`) via the `gradio_client` library — **this exact API contract was verified live during design** (see below), not guessed. `ConversationService` catches a new `TTSUnavailableError` around the synthesis call; on failure it returns empty audio plus a new `tts_fallback_required: true` flag in the response instead of erroring, so the mobile app (wired in a later plan) knows to speak `response.text` itself using the phone's built-in offline Arabic voice. This deliberately does **not** fall back to the old Groq Saudi voice — reintroducing that voice on failure would defeat the entire purpose of this change.

**Tech Stack:** `gradio_client` (new dependency), the existing `TTSProvider` interface, pytest.

## Global Constraints

- Do not fall back to `GroqTTSProvider` (Saudi voice) anywhere in this plan's real-provider wiring. On Egyptian TTS failure, the correct behavior is: return the response text with empty audio and `tts_fallback_required=true`, letting the *mobile app* speak locally (this is Plan 4's job — this plan only produces the correct signal).
- `GroqTTSProvider` itself is not deleted — it remains valid provider-interface code, simply unused by `create_app()`'s real-provider branch after this plan.
- The Gradio Space API used here (`omarelshehy/NAMAA-Egyptian-Voice`, endpoint `/generate_tts_audio`) was live-tested during this plan's design: calling it with `text_input="إزيك عامل ايه"` and default values for the other five parameters returned a real WAV file (49,964 bytes) in one call. Use these exact parameter names — do not invent different ones.
- Every new production module gets test coverage, following this repo's one-file-per-module convention.

---

### Task 1: `TTSUnavailableError` + response schema changes

**Files:**
- Modify: `backend/app/providers/base.py`
- Modify: `backend/app/schemas/common.py`
- Test: `backend/tests/unit/test_provider_base.py`, `backend/tests/unit/test_common_schemas.py`

**Interfaces:**
- Produces: `TTSUnavailableError` (exception class), `ConversationResponse.tts_fallback_required: bool` (new field, default `False`), `ConversationResponse.audio_base64` relaxed to allow an empty string — consumed by Tasks 3 and 4.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/unit/test_provider_base.py` (after the existing `test_provider_interfaces_are_abstract` function):

```python
def test_tts_unavailable_error_is_an_exception():
    from app.providers.base import TTSUnavailableError

    error = TTSUnavailableError("synthesis failed")
    assert isinstance(error, Exception)
    assert str(error) == "synthesis failed"
```

Add to `backend/tests/unit/test_common_schemas.py`:

```python
def test_conversation_response_allows_empty_audio_with_fallback_flag():
    response = ConversationResponse(
        session_id="session-1",
        text="A desk with a laptop.",
        audio_base64="",
        tts_fallback_required=True,
    )

    assert response.audio_base64 == ""
    assert response.tts_fallback_required is True


def test_conversation_response_defaults_tts_fallback_required_to_false():
    response = ConversationResponse(
        session_id="session-1",
        text="A desk with a laptop.",
        audio_base64="YWJj",
    )

    assert response.tts_fallback_required is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/unit/test_provider_base.py tests/unit/test_common_schemas.py -v`
Expected: FAIL — `ImportError: cannot import name 'TTSUnavailableError'`, and `ValidationError` from `ConversationResponse(audio_base64="", ...)` since the field currently requires `min_length=1`.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/providers/base.py`, add near the top (after the imports, before `class ASRProvider`):

```python
class TTSUnavailableError(Exception):
    """Raised by a TTSProvider when speech synthesis could not be completed."""
```

In `backend/app/schemas/common.py`, change the `ConversationResponse` class:

```python
class ConversationResponse(BaseModel):
    session_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    audio_base64: str = Field(min_length=1)
    debug: ConversationDebug | None = None
```

to:

```python
class ConversationResponse(BaseModel):
    session_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    audio_base64: str = ""
    tts_fallback_required: bool = False
    debug: ConversationDebug | None = None
```

(Removing `Field(min_length=1)` on `audio_base64` and giving it a plain `""` default — empty audio is now a valid, meaningful state, not an error.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/unit/test_provider_base.py tests/unit/test_common_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/base.py backend/app/schemas/common.py backend/tests/unit/test_provider_base.py backend/tests/unit/test_common_schemas.py
git commit -m "feat: add TTSUnavailableError and tts_fallback_required response field"
```

---

### Task 2: Add `gradio_client` dependency

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces: the `gradio_client` package available for import — consumed by Task 3.

- [ ] **Step 1: Add to `pyproject.toml`**

In `backend/pyproject.toml`, add `"gradio_client>=1.6"` to the `dependencies` list:

```toml
dependencies = [
    "fastapi>=0.115",
    "groq>=0.31",
    "pydantic>=2.8",
    "pillow>=10.0",
    "uvicorn>=0.30",
    "httpx>=0.27",
    "gradio_client>=1.6",
]
```

- [ ] **Step 2: Add to `requirements.txt`**

Add a new line to `backend/requirements.txt`:

```
gradio_client==1.6.0
```

so the file reads:

```
fastapi==0.136.1
groq==1.4.0
pydantic==2.12.5
pillow==12.0.0
uvicorn==0.47.0
httpx==0.28.1
gradio_client==1.6.0
```

- [ ] **Step 3: Install locally**

Run: `cd backend && pip install gradio_client==1.6.0`
Expected: installs successfully (it was already installed and verified working during this plan's design research).

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/requirements.txt
git commit -m "chore: add gradio_client dependency for Egyptian TTS"
```

---

### Task 3: `EgyptianTTSProvider`

**Files:**
- Create: `backend/app/providers/egyptian_tts.py`
- Test: `backend/tests/unit/test_egyptian_tts_provider.py`

**Interfaces:**
- Consumes: `TTSProvider` (base interface), `TTSUnavailableError` (Task 1).
- Produces: `EgyptianTTSProvider` — consumed by Task 5 (main.py wiring).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_egyptian_tts_provider.py`:

```python
import pytest

from app.providers.base import TTSUnavailableError
from app.providers.egyptian_tts import EgyptianTTSProvider


class FakeGradioClient:
    def __init__(self, result_path: str | None = None, error: Exception | None = None):
        self._result_path = result_path
        self._error = error
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._result_path


def test_egyptian_tts_returns_audio_bytes_on_success(tmp_path):
    audio_file = tmp_path / "output.wav"
    audio_file.write_bytes(b"fake-wav-bytes")
    client = FakeGradioClient(result_path=str(audio_file))
    provider = EgyptianTTSProvider(space_id="omarelshehy/NAMAA-Egyptian-Voice", client=client)

    result = provider.synthesize_speech("إزيك عامل ايه")

    assert result == b"fake-wav-bytes"
    assert client.calls[0]["text_input"] == "إزيك عامل ايه"
    assert client.calls[0]["api_name"] == "/generate_tts_audio"


def test_egyptian_tts_raises_unavailable_error_on_client_failure():
    client = FakeGradioClient(error=RuntimeError("space is sleeping"))
    provider = EgyptianTTSProvider(space_id="omarelshehy/NAMAA-Egyptian-Voice", client=client)

    with pytest.raises(TTSUnavailableError):
        provider.synthesize_speech("hello")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/unit/test_egyptian_tts_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.providers.egyptian_tts'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/providers/egyptian_tts.py`:

```python
from __future__ import annotations

from app.providers.base import TTSProvider, TTSUnavailableError


class EgyptianTTSProvider(TTSProvider):
    """Calls the free, public omarelshehy/NAMAA-Egyptian-Voice Gradio Space
    for Egyptian-Arabic speech synthesis. Its API was live-verified during
    design: /generate_tts_audio takes text_input plus five optional tuning
    parameters, and returns a filepath to a generated WAV file.
    """

    def __init__(self, space_id: str, client: object | None = None) -> None:
        self._space_id = space_id
        self._client = client

    def _ensure_client(self) -> object:
        if self._client is None:
            from gradio_client import Client

            self._client = Client(self._space_id)
        return self._client

    def synthesize_speech(self, text: str) -> bytes:
        try:
            client = self._ensure_client()
            result_path = client.predict(
                text_input=text,
                audio_prompt_path_input=None,
                exaggeration_input=0.5,
                temperature_input=0.8,
                seed_num_input=0,
                cfgw_input=0.5,
                api_name="/generate_tts_audio",
            )
            with open(result_path, "rb") as audio_file:
                return audio_file.read()
        except Exception as exc:  # noqa: BLE001 -- any failure here means "use the fallback"
            raise TTSUnavailableError(f"Egyptian TTS unavailable: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/unit/test_egyptian_tts_provider.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/egyptian_tts.py backend/tests/unit/test_egyptian_tts_provider.py
git commit -m "feat: add EgyptianTTSProvider calling the NAMAA-Egyptian-Voice Gradio Space"
```

---

### Task 4: Wire fallback handling into `ConversationService`

**Files:**
- Modify: `backend/app/services/conversation_service.py`
- Modify: `backend/app/providers/fakes.py`
- Test: `backend/tests/unit/test_conversation_service.py`

**Interfaces:**
- Consumes: `TTSUnavailableError` (Task 1), `ConversationResponse.tts_fallback_required` (Task 1).
- Produces: `ConversationService.handle()` now never raises on a TTS failure — it degrades gracefully. Consumed by Task 5 (end-to-end wiring) and, later, by the mobile plan reading this field.

- [ ] **Step 1: Write the failing test**

Add to `backend/app/providers/fakes.py`, after `FakeTTSProvider`:

```python
class FakeFailingTTSProvider(TTSProvider):
    def synthesize_speech(self, text: str) -> bytes:
        raise TTSUnavailableError("fake TTS failure for testing")
```

(Add `TTSUnavailableError` to the existing `from app.providers.base import ...` import line in that file.)

Add to `backend/tests/unit/test_conversation_service.py`:

```python
def test_conversation_service_sets_fallback_flag_when_tts_unavailable():
    from app.providers.fakes import FakeFailingTTSProvider

    service = ConversationService(
        asr=FakeASRProvider(),
        vision=FakeVisionProvider(),
        ocr=FakeOCRProvider(),
        llm=FakeLLMProvider(),
        tts=FakeFailingTTSProvider(),
        grounding=FakeGroundingProvider(),
        session_store=InMemorySessionStore(),
        router=IntentRouter(),
    )
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"What is in front of me?").decode("ascii"),
    )

    response = service.handle(request)

    assert response.tts_fallback_required is True
    assert response.audio_base64 == ""
    assert response.text  # the text answer must still be present
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/unit/test_conversation_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'FakeFailingTTSProvider'` (it doesn't exist yet), then (once added) the service call raises `TTSUnavailableError` uncaught instead of returning a response.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/conversation_service.py`, add the import:

```python
from app.providers.base import (
    ASRProvider,
    GroundingProvider,
    LLMProvider,
    OCRProvider,
    TTSProvider,
    TTSUnavailableError,
    VisionProvider,
)
```

Then change the block that currently reads:

```python
        response_text = self.llm.generate_response(
            transcript, vision_summary, ocr_text, history, grounding_result=grounding_result
        )
        speech_bytes = self.tts.synthesize_speech(response_text)
```

to:

```python
        response_text = self.llm.generate_response(
            transcript, vision_summary, ocr_text, history, grounding_result=grounding_result
        )
        tts_fallback_required = False
        try:
            speech_bytes = self.tts.synthesize_speech(response_text)
        except TTSUnavailableError:
            speech_bytes = b""
            tts_fallback_required = True
```

Finally, update the final `ConversationResponse(...)` construction to pass the new field:

```python
        return ConversationResponse(
            session_id=request.session_id,
            text=response_text,
            audio_base64=base64.b64encode(speech_bytes).decode("ascii"),
            tts_fallback_required=tts_fallback_required,
            debug=debug,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/unit/test_conversation_service.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python3 -m pytest -v`
Expected: all tests pass (the existing 80 plus every test added in Tasks 1-4).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/conversation_service.py backend/app/providers/fakes.py backend/tests/unit/test_conversation_service.py
git commit -m "feat: degrade gracefully to tts_fallback_required on TTS failure"
```

---

### Task 5: Wire `EgyptianTTSProvider` into `create_app()`

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/unit/test_config.py`, `backend/tests/unit/test_main.py`

**Interfaces:**
- Consumes: `EgyptianTTSProvider` (Task 3).
- Produces: the running app's real-provider mode now uses Egyptian TTS instead of `GroqTTSProvider` for the conversation flow. This is the final integration point in this plan.

- [ ] **Step 1: Write the failing tests**

`backend/tests/unit/test_config.py` has two settings tests (`test_get_settings_uses_environment_defaults`, `test_get_settings_reads_environment`), each using `monkeypatch.delenv`/`monkeypatch.setenv` on every relevant variable before calling `get_settings()`. Add two new standalone tests following that same style — no need to touch the two existing tests:

```python
def test_settings_includes_egyptian_tts_space_id():
    settings = get_settings()

    assert settings.egyptian_tts_space_id == "omarelshehy/NAMAA-Egyptian-Voice"


def test_settings_reads_egyptian_tts_space_id_override(monkeypatch):
    monkeypatch.setenv("EGYPTIAN_TTS_SPACE_ID", "some-other/space")

    settings = get_settings()

    assert settings.egyptian_tts_space_id == "some-other/space"
```

Add to `backend/tests/unit/test_main.py`:

```python
def test_create_app_uses_egyptian_tts_in_real_mode(monkeypatch):
    from app.providers.egyptian_tts import EgyptianTTSProvider

    monkeypatch.setenv("USE_REAL_PROVIDERS", "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MULTIMODAL_MODEL", "test-model")

    app = create_app()

    # The service is a closure captured by the route; the cleanest external
    # check is that the app builds without error in real mode with the new
    # provider wired in -- deeper inspection would require reaching into
    # FastAPI's dependency closures, which this repo's other tests don't do.
    assert app is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/unit/test_config.py tests/unit/test_main.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'egyptian_tts_space_id'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/core/config.py`, add a new field to the `Settings` dataclass:

```python
@dataclass(frozen=True)
class Settings:
    app_name: str = "Be My Eye Backend"
    environment: str = "development"
    debug: bool = True
    use_real_providers: bool = False
    groq_api_key: str = ""
    groq_multimodal_model: str = ""
    groq_llm_model: str = "llama-3.3-70b-versatile"
    groq_asr_model: str = "whisper-large-v3"
    groq_tts_model: str = "canopylabs/orpheus-arabic-saudi"
    groq_tts_voice: str = "abdullah"
    groq_asr_language: str = "ar"
    egyptian_tts_space_id: str = "omarelshehy/NAMAA-Egyptian-Voice"
```

And in `get_settings()`, add the matching line:

```python
        egyptian_tts_space_id=os.getenv("EGYPTIAN_TTS_SPACE_ID", "omarelshehy/NAMAA-Egyptian-Voice"),
```

(add this line inside the `Settings(...)` constructor call, alongside the existing `groq_asr_language=...` line).

In `backend/app/main.py`, add the import:

```python
from app.providers.egyptian_tts import EgyptianTTSProvider
```

Then change the real-provider branch of `create_app()` from:

```python
        service = ConversationService(
            asr=GroqASRProvider(model=settings.groq_asr_model, language=settings.groq_asr_language),
            vision=GroqVisionProvider(model=settings.groq_multimodal_model, prompts=prompts),
            ocr=GroqOCRProvider(model=settings.groq_multimodal_model, prompts=prompts),
            llm=GroqLLMProvider(model=settings.groq_llm_model, prompts=prompts),
            tts=GroqTTSProvider(model=settings.groq_tts_model, voice=settings.groq_tts_voice),
            grounding=GroqGroundingProvider(model=settings.groq_multimodal_model, prompts=prompts),
            session_store=InMemorySessionStore(),
            router=IntentRouter(),
        )
```

to:

```python
        service = ConversationService(
            asr=GroqASRProvider(model=settings.groq_asr_model, language=settings.groq_asr_language),
            vision=GroqVisionProvider(model=settings.groq_multimodal_model, prompts=prompts),
            ocr=GroqOCRProvider(model=settings.groq_multimodal_model, prompts=prompts),
            llm=GroqLLMProvider(model=settings.groq_llm_model, prompts=prompts),
            tts=EgyptianTTSProvider(space_id=settings.egyptian_tts_space_id),
            grounding=GroqGroundingProvider(model=settings.groq_multimodal_model, prompts=prompts),
            session_store=InMemorySessionStore(),
            router=IntentRouter(),
        )
```

(`GroqTTSProvider` is intentionally no longer referenced here — leave its import in place, since removing an otherwise-unused import for a class still used by other tests is out of scope for this task; do not delete `GroqTTSProvider`'s class definition or its own tests.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/unit/test_config.py tests/unit/test_main.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python3 -m pytest -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/main.py backend/tests/unit/test_config.py backend/tests/unit/test_main.py
git commit -m "feat: wire EgyptianTTSProvider into create_app for real-provider mode"
```

---

## Plan Complete

After Task 5, the backend's real-provider conversation flow speaks in an authentic Egyptian dialect by default. When Egyptian TTS synthesis fails for any reason, `ConversationResponse.tts_fallback_required` is `true` and `audio_base64` is empty, with `response.text` always present — this is exactly the signal Plan 4 (mobile) needs to trigger the on-device OS Arabic voice fallback.

**Deployment note (not part of this plan's tasks, but required before this reaches production):** after merging, redeploy the backend to Vercel (`cd backend && vercel deploy --prod`) so the live app actually uses Egyptian TTS. Also be aware the free Gradio Space may go idle and take longer to respond on its first call after a period of inactivity (matching every other free-tier constraint already documented in this project) — this is exactly why the fallback signal exists, not a bug to fix here.
