# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TubeNauta V5 - Masivo IMG is an automated video generation system for YouTube Shorts (1080x1920, 40-70s). It batch-processes topics or news stories through a 7-step pipeline to produce videos with AI-generated scripts, TTS narration, Whisper subtitles, Flux-generated images, and FFmpeg assembly.

## Running the System

```bash
# Batch video generation from temas.txt
python main.py

# Single topic via CLI
python main.py "Topic 1" "Topic 2"

# News-based videos from noticias.txt (stories separated by "---")
python news_runner.py

# Web interface at http://localhost:5000
python app.py
```

**Prerequisites before running**: ComfyUI must be running at `http://127.0.0.1:8188`, Ollama with `gemma3:4b` loaded, `GEMINI_API_KEY` environment variable set, and FFmpeg installed.

## Architecture & Data Flow

### 7-Step Pipeline (pipeline.py)
Each topic/news story runs through these sequential steps; the pipeline auto-skips completed steps (checks output file existence):

1. **Guion** → AI generates 61-70s script (Gemini primary, Ollama fallback)
2. **Metadatos** → Title/description/tags via separate AI calls
3. **Voz** → Gemini TTS (Algieba voice) → `4. Crudo.wav` + compressed `5. Voz.mp3`
4. **Subtítulos** → Whisper large-v3 → `6. Subtitulos.srt`
5. **Escenas** → Segments subtitles (min 2.5s), generates English visual prompts → `7. Escenas.csv`
6. **Imágenes** → Flux via ComfyUI API (1024×1536) → `imagenes/{start}_{end}_1.png`
7. **Video** → FFmpeg with h264_nvenc, zoom-pan effects, ASS subtitles, subscribe banner → `8. Video.mp4`

### Output Directory Structure
Each video is stored in `output/video{N}/` (or `output/news{N}/`):
```
1. Tema.txt       # Topic
2. Guion.txt      # Script
3. Metadatos.txt  # Title/description/tags (separated by "---")
4. Crudo.wav/.mp3 # Raw TTS audio
5. Voz.mp3        # Compressed/normalized audio
6. Subtitulos.srt # Word-level subtitles
7. Escenas.csv    # Scene timing + prompts (cols: Inicio, Final, Subtitulos, Escena)
8. Video.mp4      # Final output
imagenes/         # Scene images named {start}_{end}_1.png
```

### Key Modules
- **[config.py](config.py)** — Single source of truth for all settings: API keys, model names, paths, image dimensions, ComfyUI node IDs, video dimensions, TTS voice, Whisper settings
- **[ai_utils.py](ai_utils.py)** — `chat()` (smart Gemini/Ollama routing), `generar_audio_tts()` (with retry/backoff), `extraer_palabras()` (Whisper with CUDA)
- **[imagen_flux.py](imagen_flux.py)** — Sends prompts to ComfyUI REST API, polls for completion, downloads images
- **[estilos_imagen.py](estilos_imagen.py)** — 25+ image style presets; select via `TUBENAUTA_ESTILO` env var or `ESTILO_BASE` in config
- **[video_assembler.py](video_assembler.py)** — FFmpeg orchestration: zoom-pan per clip, ASS subtitle generation, banner overlay, NVENC encoding

## Configuration

All tuneable parameters live in **[config.py](config.py)**:

| Setting | Default | Notes |
|---|---|---|
| `GEMINI_MODEL` | `gemini-2.5-flash` | Text generation |
| `GEMINI_TTS_MODEL` | `gemini-2.5-flash-preview-tts` | Audio |
| `OLLAMA_MODEL` | `gemma3:4b` | Local fallback |
| `COMFYUI_URL` | `http://127.0.0.1:8188` | Local ComfyUI |
| `IMAGE_WIDTH/HEIGHT` | `1024×1536` | Flux output (portrait) |
| `VIDEO_WIDTH/HEIGHT` | `1080×1920` | Final video (Shorts) |
| `TTS_VOICE` | `Algieba` | Spanish neutral |
| `SEGMENT_MIN_DURATION` | `2.5s` | Min scene duration |

Image style is selected by writing a style name to `.estilo_temp.txt` or setting `TUBENAUTA_ESTILO` env var.

## Important Implementation Details

**AI Fallback Chain**: `chat()` in ai_utils.py tries Gemini first, falls back to Ollama on failure. Prompts are loaded from `prompts/` directory as templates with `{placeholder}` substitution.

**Windows/CUDA workaround**: `ai_utils.py` monkey-patches `sys.modules['torchcodec'] = None` before importing Whisper to avoid a Windows-incompatible dependency. Audio is pre-converted to 16kHz mono via pydub before Whisper inference.

**ComfyUI node IDs**: Injected prompt goes into node `"6"` (CLIP Text Encode). Node IDs are defined in `config.py → FLUX_NODOS` and must match the loaded workflow.

**Anatomy fix**: `ANATOMY_FIX` string from config.py is appended to every Flux prompt to prevent anatomical defects.

**BIOGRAPHY vs ORIGINAL mode**: The scene prompt generator (`prompts/4. Escena.txt`) detects historical/celebrity topics and switches to character-consistency mode. `estilos_imagen.py` contains a hardcoded database of known character visual traits (footballers, singers, historical figures).

**Video extension**: If TTS audio is longer than the assembled video, `video_assembler.py` uses FFmpeg `tpad` filter to extend the last frame rather than truncating audio.

**FFmpeg paths**: `escapar_ruta_windows()` in video_assembler.py handles Windows path escaping for FFmpeg filter arguments.

## Web Interface (app.py)

Flask server with SSE (Server-Sent Events) for real-time log streaming. Pipelines run as subprocesses for isolation. Thread-safe log queue with `threading.Lock`. Routes: `/` dashboard, `/temas`, `/noticias`, `/progreso` (SSE logs), `/galeria`, `/config`.

API endpoints: `POST /api/start` (start processing), `GET /api/status` (SSE stream), `GET /api/download/<path>`.

## News Module

`news_runner.py` + `news_pipeline.py` operate identically to the main pipeline but use `prompts/5. Noticias.txt` and output to `output/news{N}/`. News stories in `noticias.txt` are separated by `---`. Supports optional internet verification and character fidelity styles from `estilos_imagen.py`.

## Code Conventions

- Variable/function names and comments are in **Spanish**
- Pipeline progress is logged with Unicode indicators: `✔` success, `✗` error, `↻` resuming, `[N/7]` step progress
- Output files use numbered prefixes (`1. Tema.txt`, `2. Guion.txt`, etc.) for visual ordering
- Constants use `UPPER_SNAKE_CASE`; module-level functions use `snake_case` in Spanish
