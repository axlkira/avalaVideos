"""
Utilidades de IA centralizadas: Gemini, Ollama, TTS, Whisper
"""
import sys
# Bloquear torchcodec roto ANTES de importar transformers.
# torchcodec está instalado pero sus DLLs no cargan en Windows,
# causando RuntimeError. Al marcarlo como None, Python lanza ImportError
# y transformers usa el fallback normal (soundfile/numpy).
sys.modules['torchcodec'] = None

import os
import re
import wave
import gc
from io import BytesIO

import numpy as np
import torch
import ollama
from openai import OpenAI
from pydub import AudioSegment, effects
from pydub.effects import compress_dynamic_range
import google.generativeai as genai
from transformers import pipeline as hf_pipeline

import time
import re

import google.api_core.exceptions

from config import (
    GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TTS_MODEL, OLLAMA_MODEL,
    TTS_VOICE, TTS_LANGUAGE_INSTRUCTION, WHISPER_MODEL, WHISPER_LANGUAGE
)

# ─── Clientes ─────────────────────────────────────────────────────────────────
_openai_client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=GEMINI_API_KEY
)

genai.configure(api_key=GEMINI_API_KEY)
_tts_model = genai.GenerativeModel(GEMINI_TTS_MODEL)


# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT (texto)
# ═══════════════════════════════════════════════════════════════════════════════

def chat_gemini(mensaje: str) -> str | None:
    try:
        respuesta = _openai_client.chat.completions.create(
            model=GEMINI_MODEL,
            messages=[{"role": "user", "content": mensaje}]
        ).choices[0].message.content
        if respuesta and "</think>" in respuesta:
            respuesta = respuesta.split("</think>", 1)[1]
        return respuesta.strip()
    except Exception as e:
        print(f"  [Gemini] Error: {e}")
        return None


def chat_ollama(mensaje: str, modelo: str = OLLAMA_MODEL) -> str | None:
    try:
        respuesta = ollama.chat(
            model=modelo,
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta["message"]["content"]
    except Exception as e:
        print(f"  [Ollama] Error: {e}")
        return None


def chat(prompt_template: str, reemplazos: dict, preferir_gemini: bool = True) -> str:
    mensaje = prompt_template
    for k, v in reemplazos.items():
        mensaje = mensaje.replace(k, v)

    if preferir_gemini:
        respuesta = chat_gemini(mensaje)
        if respuesta is None:
            print("  Gemini no respondió, usando modelo local...")
            respuesta = chat_ollama(mensaje)
    else:
        respuesta = chat_ollama(mensaje)
        if respuesta is None:
            print("  Ollama no respondió, usando Gemini como respaldo...")
            respuesta = chat_gemini(mensaje)

    return respuesta.strip() if respuesta else ""


def limpiar_linea(texto: str) -> str:
    return re.sub(r'["\'`´¨\n\*]', '', " ".join(texto.split())).rstrip('.').strip()


# ═══════════════════════════════════════════════════════════════════════════════
#  TTS (voz)
# ═══════════════════════════════════════════════════════════════════════════════

def generar_audio_tts(guion: str, max_retries: int = 5) -> AudioSegment:
    config_tts = {
        "response_modalities": ["AUDIO"],
        "speech_config": {
            "voice_config": {
                "prebuilt_voice_config": {
                    "voice_name": TTS_VOICE
                }
            }
        }
    }
    
    for attempt in range(max_retries):
        try:
            respuesta = _tts_model.generate_content(
                contents=TTS_LANGUAGE_INSTRUCTION + guion,
                generation_config=config_tts
            )
            datos = respuesta.candidates[0].content.parts[0].inline_data.data
            buffer = BytesIO()
            with wave.open(buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(datos)
            buffer.seek(0)
            return AudioSegment.from_wav(buffer)
        except google.api_core.exceptions.ResourceExhausted as e:
            match = re.search(r'Please retry in ([\d.]+)s', str(e))
            if match:
                wait_time = float(match.group(1))
            else:
                wait_time = (attempt + 1) * 30  # Fallback: 30s, 60s, 90s...
            
            if attempt < max_retries - 1:
                print(f"  ⚠ Cuota excedida (429). Esperando {wait_time:.1f}s antes de reintentar... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time + 2)  # +2s de margen
            else:
                raise  # Último intento fallido, propagar error
        except (
            google.api_core.exceptions.InternalServerError,
            google.api_core.exceptions.ServiceUnavailable,
            google.api_core.exceptions.DeadlineExceeded,
        ) as e:
            if attempt < max_retries - 1:
                wait_time = min((attempt + 1) * 10, 60)
                print(
                    f"  ⚠ Gemini TTS fallo {e.__class__.__name__}: reintentando en {wait_time:.1f}s... "
                    f"({attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = min((attempt + 1) * 5, 30)
                print(
                    f"  ⚠ Error inesperado en TTS ({e.__class__.__name__}): "
                    f"reintentando en {wait_time:.1f}s... ({attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                raise

    raise RuntimeError("No se pudo generar audio TTS tras múltiples intentos")


def procesar_audio(audio: AudioSegment) -> AudioSegment:
    audio = compress_dynamic_range(audio, threshold=-30.0, ratio=1.0, attack=5.0, release=100.0)
    return effects.normalize(audio, headroom=0.01).apply_gain(3)


# ═══════════════════════════════════════════════════════════════════════════════
#  WHISPER (subtítulos)
# ═══════════════════════════════════════════════════════════════════════════════

def _cargar_audio_como_array(audio_path: str) -> dict:
    """Carga audio con pydub y lo convierte a numpy array 16kHz mono.
    Esto evita que transformers use torchcodec (que falla en Windows)."""
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0
    return {"array": samples, "sampling_rate": 16000}


def extraer_palabras(audio_path: str) -> list[dict]:
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    asr = hf_pipeline(
        "automatic-speech-recognition",
        model=WHISPER_MODEL,
        torch_dtype=dtype,
        device=device
    )
    audio_input = _cargar_audio_como_array(audio_path)
    resp = asr(audio_input, return_timestamps="word", generate_kwargs={"language": WHISPER_LANGUAGE})
    palabras = []
    for chunk in resp.get("chunks", []):
        word_text = chunk.get("text", "").strip()
        timestamp = chunk.get("timestamp")
        if not (word_text and timestamp):
            continue
        start, end = timestamp
        palabras.append({"word": word_text, "start": float(start), "end": float(end)})
    del asr
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    return palabras
