import io
import os
import tempfile
import base64
from typing import Optional


def text_to_speech_gtts(text: str, lang: str = "en", slow: bool = False) -> dict:
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, slow=slow)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_bytes = buf.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return {
            "success": True,
            "audio_b64": audio_b64,
            "format": "mp3",
            "error": None,
        }
    except ImportError:
        return {
            "success": False,
            "audio_b64": None,
            "format": None,
            "error": "gTTS not installed. Run: pip install gTTS",
        }
    except Exception as e:
        return {
            "success": False,
            "audio_b64": None,
            "format": None,
            "error": str(e),
        }


async def text_to_speech_edge(text: str, voice: str = "en-US-GuyNeural") -> dict:
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        audio_bytes = buf.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return {
            "success": True,
            "audio_b64": audio_b64,
            "format": "mp3",
            "error": None,
        }
    except ImportError:
        return {
            "success": False,
            "audio_b64": None,
            "format": None,
            "error": "edge-tts not installed. Run: pip install edge-tts",
        }
    except Exception as e:
        return {
            "success": False,
            "audio_b64": None,
            "format": None,
            "error": str(e),
        }


def get_tts_url(text: str, lang: str = "en") -> str:
    from urllib.parse import quote
    encoded = quote(text[:200])
    return f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={encoded}"


WAKE_WORDS: dict[str, str] = {}

def register_wake_word(agent_name: str) -> str:
    wake_word = f"hey {agent_name.lower()}"
    WAKE_WORDS[agent_name.lower()] = wake_word
    return wake_word


def detect_wake_word(transcript: str, agent_name: str) -> bool:
    wake_word = f"hey {agent_name.lower()}"
    return wake_word in transcript.lower()


if __name__ == "__main__":
    url = get_tts_url("Hello, I am your AI assistant!", "en")
    print(f"TTS URL: {url}")

    result = text_to_speech_gtts("Hello from SeVIn!", lang="en")
    if result["success"]:
        print("gTTS: Success, got audio data")
    else:
        print(f"gTTS error: {result['error']}")
