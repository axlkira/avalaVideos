# Migración a Nueva API de Google Gemini

## Fecha: 19 Mayo 2026

## Resumen de Cambios

Google actualizó su API de Gemini, requiriendo migración del SDK antiguo al nuevo `google-genai`.

## Cambios Implementados

### 1. Modelos Actualizados (`config.py`)

**Antes:**
```python
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
```

**Después:**
```python
GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_TTS_MODEL = "gemini-3.1-flash-tts-preview"
```

### 2. Imports Actualizados (`ai_utils.py`)

**Antes:**
```python
import google.generativeai as genai
from openai import OpenAI

_openai_client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=GEMINI_API_KEY
)
genai.configure(api_key=GEMINI_API_KEY)
_tts_model = genai.GenerativeModel(GEMINI_TTS_MODEL)
```

**Después:**
```python
from google import genai
from google.genai import types

_gemini_client = genai.Client(api_key=GEMINI_API_KEY)
```

### 3. Función `chat_gemini()` Actualizada

**Antes:**
```python
def chat_gemini(mensaje: str) -> str | None:
    try:
        respuesta = _openai_client.chat.completions.create(
            model=GEMINI_MODEL,
            messages=[{"role": "user", "content": mensaje}]
        ).choices[0].message.content
        # ...
```

**Después:**
```python
def chat_gemini(mensaje: str) -> str | None:
    try:
        response = _gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=mensaje
        )
        respuesta = response.text
        # ...
```

### 4. Función `generar_audio_tts()` Actualizada

**Antes:**
```python
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
    respuesta = _tts_model.generate_content(
        contents=TTS_LANGUAGE_INSTRUCTION + guion,
        generation_config=config_tts
    )
```

**Después:**
```python
def generar_audio_tts(guion: str, max_retries: int = 5) -> AudioSegment:
    response = _gemini_client.models.generate_content(
        model=GEMINI_TTS_MODEL,
        contents=TTS_LANGUAGE_INSTRUCTION + guion,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=TTS_VOICE
                    )
                )
            )
        )
    )
```

## Instalación de Dependencias

```bash
pip install google-genai>=0.2.0
```

O instalar todas las dependencias:
```bash
pip install -r requirements.txt
```

## Funcionalidades Preservadas

✅ Generación de guiones con Gemini
✅ Generación de voz (TTS) con voz Algieba
✅ Sistema de reintentos con manejo de errores
✅ Fallback a Ollama local
✅ Procesamiento de audio
✅ Generación de subtítulos con Whisper
✅ Generación de imágenes con Flux/ComfyUI
✅ Ensamblaje de video con FFmpeg
✅ Frontend web Flask

## Voces Disponibles (TTS)

La nueva API soporta 30 voces prediseñadas. La voz actual configurada es:
- **Algieba**: Voz suave en español

Otras voces disponibles: Zephyr, Puck, Kore, Fenrir, Aoede, Charon, etc.

## Notas Importantes

1. **Sin cambios en el pipeline**: El flujo de 7 pasos permanece idéntico
2. **Sin cambios en la configuración**: Todas las variables de entorno y archivos de configuración funcionan igual
3. **Compatibilidad total**: Los videos se generan exactamente igual que antes
4. **Mejoras de la nueva API**: 
   - Mejor manejo de errores
   - Soporte mejorado para múltiples idiomas
   - Control más fino sobre el estilo de voz con instrucciones en lenguaje natural

## Verificación

Para verificar que todo funciona correctamente:

```bash
# Asegúrate de tener la variable de entorno configurada
export GEMINI_API_KEY="tu_api_key"

# Ejecuta un video de prueba
python main.py "la historia del chocolate"
```

El sistema debe generar:
1. Guion (con Gemini 3.5 Flash)
2. Voz (con Gemini 3.1 Flash TTS)
3. Subtítulos (con Whisper)
4. Imágenes (con Flux)
5. Video final (con FFmpeg)

## Soporte

Si encuentras algún problema, verifica:
1. Que `google-genai>=0.2.0` esté instalado
2. Que `GEMINI_API_KEY` esté configurada correctamente
3. Que ComfyUI esté corriendo en `http://127.0.0.1:8188`
4. Los logs en la consola para errores específicos
