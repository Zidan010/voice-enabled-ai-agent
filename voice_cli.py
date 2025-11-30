#!/usr/bin/env python3
"""
VOICE + CLI Interface for UnifiedAgentSystem
--------------------------------------------

Flow:
1. Accept voice input (file or microphone)
2. Deepgram STT → text
3. Text → UnifiedAgentSystem (your RAG pipeline)
4. Text response → Deepgram TTS → audio output file
5. Optionally play audio
"""

import os
import sys
import json
import time
import tempfile
from datetime import datetime
from pathlib import Path
import subprocess

from deepgram import DeepgramClient  # Removed SpeakOptions; use dict for options
import sounddevice as sd
import soundfile as sf

from langchain_groq_rag import UnifiedAgentSystem


# ============================
#  CONFIG
# ============================

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    print("ERROR: Missing DEEPGRAM_API_KEY.")
    sys.exit(1)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("ERROR: Missing GROQ_API_KEY.")
    sys.exit(1)


# ============================
#  AUDIO UTILS
# ============================

def record_microphone(duration=5, samplerate=16000, channels=1):
    """Record live microphone audio for a set duration."""
    print(f"\n🎙 Recording {duration} seconds ...")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels)
    sd.wait()

    temp_path = tempfile.mktemp(suffix=".wav")
    sf.write(temp_path, audio, samplerate)

    print(f"Saved recording to: {temp_path}")
    return temp_path


def play_audio(path):
    """Play an audio file (cross-platform)."""
    print(f"\n🔊 Playing: {path}")

    try:
        if sys.platform.startswith("win"):
            # Windows
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
        elif sys.platform == "darwin":
            subprocess.call(["afplay", path])
        else:
            subprocess.call(["aplay", path])
    except Exception as e:
        print("Unable to play audio:", e)


# ============================
#  DEEPGRAM STT
# ============================

def speech_to_text(path):
    """Convert audio file → text using Deepgram STT."""
    print("\n🧠 Transcribing audio using Deepgram...")

    dg = DeepgramClient(api_key=DEEPGRAM_API_KEY)  # Fixed: Use keyword arg

    with open(path, "rb") as f:
        # Fixed: Use v1.media.transcribe_file (current SDK path); pass buffer as 'request' bytes
        stt = dg.listen.v1.media.transcribe_file(
            request=f.read(),
            model="nova-2-general"
        )

    text = stt.results.channels[0].alternatives[0].transcript.strip()
    print("📝 Transcription:", text)
    return text


# ============================
#  DEEPGRAM TTS
# ============================
def text_to_speech(text, voice="aura-asteria-en"):
    """Convert text → speech with Deepgram. Saves to temp + permanent history."""
    print("\nConverting response to audio using Deepgram...")

    if not text.strip():
        print("Empty text → skipping TTS")
        return None  # No audio to play

    dg = DeepgramClient(api_key=DEEPGRAM_API_KEY)

    # Temp + permanent paths
    temp_path = tempfile.mktemp(suffix=".wav")
    os.makedirs("voice_history", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_text = "".join(c if c.isalnum() else "_" for c in text.strip().lower())[:50]
    permanent_path = f"voice_history/{timestamp}__{safe_text}__response.wav"

    # Generate TTS
    result = dg.speak.v1.audio.generate(
        text=text,
        model=voice,
        encoding="linear16",
        container="wav"
    )

    # ────── CRITICAL: Proper error handling ──────
    if isinstance(result, tuple):
        generator, error = result
        if error is not None:
            print(f"TTS failed → {error}")
            return None  # Skip playback gracefully
    else:
        generator = result

    # Write to both files
    try:
        with open(temp_path, "wb") as temp_file, open(permanent_path, "wb") as perm_file:
            for chunk in generator:
                temp_file.write(chunk)
                perm_file.write(chunk)
        print(f"Saved TTS → {temp_path}")
        print(f"Permanently saved → {permanent_path}")
        return temp_path
    except Exception as e:
        print(f"Failed to write audio files: {e}")
        return None
# ============================
#  MAIN VOICE CLI
# ============================

class VoiceCLI:
    def __init__(self):
        print("Initializing UnifiedAgentSystem...")
        self.system = UnifiedAgentSystem()
        print("System Ready.\n")

    def process_text_query(self, text):
        print("\nProcessing query...")
        result = self.system.query(text, verbose=False)

        print("\n=== TEXT RESPONSE ===")
        print(result["response"])

        audio_path = text_to_speech(result["response"])
        if audio_path and os.path.exists(audio_path):
            play_audio(audio_path)
        else:
            print("(No audio generated for this response)")

    def voice_from_file(self, path):
        text = speech_to_text(path)
        self.process_text_query(text)

    def voice_from_mic(self, seconds=5):
        path = record_microphone(seconds)
        self.voice_from_file(path)

    def run(self):
        print("VOICE + CLI MODE")
        print("----------------------")
        print("Commands:")
        print("  /mic 5       → record 5 sec and process")
        print("  /file path   → use audio file")
        print("  /text query  → text mode")
        print("  /exit        → quit")
        print("----------------------\n")

        while True:
            try:
                user = input("You: ").strip()

                if user == "/exit":
                    print("Goodbye!")
                    break

                # Microphone input
                if user.startswith("/mic"):
                    parts = user.split()
                    seconds = int(parts[1]) if len(parts) > 1 else 5
                    self.voice_from_mic(seconds)
                    continue

                # File input
                if user.startswith("/file"):
                    parts = user.split(maxsplit=1)
                    if len(parts) < 2:
                        print("Usage: /file path/to/audio.wav")
                        continue
                    self.voice_from_file(parts[1])
                    continue

                # Normal text mode
                if user.startswith("/text"):
                    text = user.replace("/text", "").strip()
                    self.process_text_query(text)
                    continue

                # Fallback: treat as text
                self.process_text_query(user)

            except Exception as e:
                print("ERROR:", e)


# ============================
#  ENTRY POINT
# ============================

if __name__ == "__main__":
    VoiceCLI().run()