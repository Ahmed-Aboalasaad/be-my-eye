import os
from pathlib import Path

from app.core.config import get_settings
from app.core.config import _load_dotenv_once


def test_get_settings_uses_environment_defaults(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_APP_NAME", raising=False)
    monkeypatch.delenv("BE_MY_EYE_ENV", raising=False)
    monkeypatch.delenv("BE_MY_EYE_DEBUG", raising=False)
    monkeypatch.delenv("USE_REAL_PROVIDERS", raising=False)
    monkeypatch.delenv("GROQ_MULTIMODAL_MODEL", raising=False)
    monkeypatch.delenv("GROQ_LLM_MODEL", raising=False)
    monkeypatch.delenv("GROQ_ASR_MODEL", raising=False)
    monkeypatch.delenv("GROQ_TTS_MODEL", raising=False)
    monkeypatch.delenv("GROQ_TTS_VOICE", raising=False)
    monkeypatch.delenv("GROQ_ASR_LANGUAGE", raising=False)

    settings = get_settings()

    assert settings.app_name == "Be My Eye Backend"
    assert settings.environment == "development"
    assert settings.debug is True


def test_get_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("BE_MY_EYE_APP_NAME", "Custom App")
    monkeypatch.setenv("BE_MY_EYE_ENV", "test")
    monkeypatch.setenv("BE_MY_EYE_DEBUG", "false")
    monkeypatch.setenv("USE_REAL_PROVIDERS", "true")
    monkeypatch.setenv("GROQ_MULTIMODAL_MODEL", "qwen-model")
    monkeypatch.setenv("GROQ_LLM_MODEL", "llama-model")
    monkeypatch.setenv("GROQ_ASR_MODEL", "asr-model")
    monkeypatch.setenv("GROQ_TTS_MODEL", "tts-model")
    monkeypatch.setenv("GROQ_TTS_VOICE", "voice")
    monkeypatch.setenv("GROQ_ASR_LANGUAGE", "ar")

    settings = get_settings()

    assert settings.app_name == "Custom App"
    assert settings.environment == "test"
    assert settings.debug is False
    assert settings.use_real_providers is True
    assert settings.groq_multimodal_model == "qwen-model"
    assert settings.groq_llm_model == "llama-model"
    assert settings.groq_asr_model == "asr-model"
    assert settings.groq_tts_model == "tts-model"
    assert settings.groq_tts_voice == "voice"
    assert settings.groq_asr_language == "ar"


def test_load_dotenv_reads_root_file(monkeypatch):
    env_dir = Path(__file__).resolve().parent / "_dotenv_fixture"
    env_dir.mkdir(exist_ok=True)
    env_file = env_dir / ".env"
    env_file.write_text("TEST_FROM_ENV=hello\n", encoding="utf-8")
    monkeypatch.chdir(env_dir)
    monkeypatch.delenv("TEST_FROM_ENV", raising=False)
    setattr(_load_dotenv_once, "_loaded", False)

    _load_dotenv_once()

    assert os.getenv("TEST_FROM_ENV") == "hello"
    env_file.unlink(missing_ok=True)


def test_settings_includes_egyptian_tts_space_id():
    settings = get_settings()

    assert settings.egyptian_tts_space_id == "omarelshehy/NAMAA-Egyptian-Voice"


def test_settings_reads_egyptian_tts_space_id_override(monkeypatch):
    monkeypatch.setenv("EGYPTIAN_TTS_SPACE_ID", "some-other/space")

    settings = get_settings()

    assert settings.egyptian_tts_space_id == "some-other/space"


def test_settings_includes_roboflow_currency_defaults():
    settings = get_settings()

    assert settings.roboflow_api_key == ""
    assert settings.roboflow_currency_project == "egyptian-currency-psnkr"
    assert settings.roboflow_currency_version == "1"


def test_settings_reads_roboflow_currency_overrides(monkeypatch):
    monkeypatch.setenv("ROBOFLOW_API_KEY", "test-roboflow-key")
    monkeypatch.setenv("ROBOFLOW_CURRENCY_PROJECT", "some-other-project")
    monkeypatch.setenv("ROBOFLOW_CURRENCY_VERSION", "3")

    settings = get_settings()

    assert settings.roboflow_api_key == "test-roboflow-key"
    assert settings.roboflow_currency_project == "some-other-project"
    assert settings.roboflow_currency_version == "3"
