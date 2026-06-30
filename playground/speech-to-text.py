"""
Groq Arabic Text -> Speech -> Text round-trip demo.

Flow:
1. Take Arabic input text.
2. Generate audio from it using Groq's TTS model (PlayAI TTS, Arabic voice).
3. Feed that generated audio back into Groq's Whisper STT model to transcribe
   it back into text.
4. Print both the original and the re-transcribed text so you can compare them.

Setup:
    pip install groq
    export GROQ_API_KEY="your_api_key_here"
"""

import os
from groq import Groq
import dotenv

dotenv.load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---- Step 1: input text (Arabic) ----
original_text = "مرحبا، كيف حالك اليوم؟ أتمنى أن تقضي يوما رائعا."

# ---- Step 2: Text -> Speech ----
# playai-tts-arabic was decommissioned by Groq and replaced with the
# Orpheus Arabic (Saudi dialect) model: canopylabs/orpheus-arabic-saudi.
# Available voices: abdullah, fahad, sultan, lulwa, noura, aisha.
speech_file_path = "output_audio.wav"

tts_response = client.audio.speech.create(
    model="canopylabs/orpheus-arabic-saudi",
    voice="abdullah",
    input=original_text,
    response_format="wav",
)

# The SDK returns a streamable response; write it to disk.
tts_response.write_to_file(speech_file_path)
print(f"Audio generated and saved to: {speech_file_path}")

# ---- Step 3: Speech -> Text ----
with open(speech_file_path, "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-large-v3",  # Groq's Whisper model for transcription
        language="ar",             # force Arabic
        response_format="text",
    )

transcribed_text = transcription if isinstance(transcription, str) else transcription.text

# ---- Step 4: Compare ----
print("\nOriginal text:")
print(original_text)
print("\nTranscribed text (round-trip):")
print(transcribed_text)