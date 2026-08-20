"""
Tamil & English TTS — Microsoft Edge neural voices (free, no API key).

Voices tuned for South Indian farmer advisory (warm, slower, less “news reader”):
- Tamil: Pallavi (conversational TN Tamil)
- English/Tanglish: Neerja Expressive (natural Indian English)
"""
from __future__ import annotations

import asyncio
import io

import edge_tts

# Warmer, more conversational than Valluvar/Prabhat (less robotic news tone)
TAMIL_VOICE = "ta-IN-PallaviNeural"
ENGLISH_VOICE = "en-IN-NeerjaExpressiveNeural"

# Slightly slower + soft pitch = more human, less AI
DEFAULT_RATE = "-14%"
DEFAULT_PITCH = "-1Hz"


async def _synthesize(text: str, voice: str, rate: str = DEFAULT_RATE, pitch: str = DEFAULT_PITCH) -> bytes:
    communicate = edge_tts.Communicate(text.strip(), voice, rate=rate, pitch=pitch)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


def synthesize_speech(text: str, language: str = "Tamil") -> bytes:
    from app.services.farmer_voice_script import pick_voice, prepare_for_speech

    script = prepare_for_speech(text, language)
    if not script.strip():
        script = (text or "").strip()[:380]
    voice, rate, pitch = pick_voice(language, script)
    return asyncio.run(_synthesize(script, voice, rate=rate, pitch=pitch))
