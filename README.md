# TubeNauta V5 - Masivo IMG

Creación **masiva** de videos con imágenes generadas por **Flux** vía ComfyUI.

## Flujo automático por cada tema

1. **Guion** → Gemini genera un guion viral de 40-50s
2. **Metadatos** → Título SEO, descripción y etiquetas
3. **Voz** → TTS con Gemini (voz Algieba, español neutro)
4. **Subtítulos** → Whisper transcribe palabra por palabra
5. **Escenas** → IA genera prompts visuales para cada segmento
6. **Imágenes** → Flux genera imágenes vía ComfyUI API
7. **Video** → FFmpeg ensambla imágenes + audio + subtítulos

## Requisitos

- **Python 3.10+**
- **ComfyUI** corriendo en `http://127.0.0.1:8188` con Flux configurado
- **FFmpeg** y **FFprobe** en el PATH
- **Variable de entorno**: `GEMINI_API_KEY`
- **Ollama** con modelo `gemma3:4b` (respaldo local)

### Dependencias Python

```
pip install openai ollama google-generativeai pydub torch transformers pandas flask requests
```

## Uso

### Opción 1: Archivo de temas (recomendado para masivo)

Edita `temas.txt` (un tema por línea):

```
la ansiedad y ejercicios para combatirla
5 datos curiosos sobre el cerebro humano
la historia del chocolate
```

Ejecuta:

```
python main.py
```

### Opción 2: Argumentos por CLI

```
python main.py "la ansiedad" "el cerebro humano" "la historia del chocolate"
```

## Estructura de salida

```
output/
├── video1/
│   ├── 1. Tema.txt
│   ├── 2. Guion.txt
│   ├── 3. Metadatos.txt
│   ├── 4. Crudo.wav
│   ├── 4. Crudo.mp3
│   ├── 5. Voz.mp3
│   ├── 6. Subtitulos.srt
│   ├── 7. Escenas.csv
│   ├── 8. Video.mp4
│   └── imagenes/
│       ├── 0.00_2.50_1.png
│       ├── 2.50_5.00_1.png
│       └── ...
├── video2/
│   └── ...
└── video3/
    └── ...
```

## Cambiar estilo de imagen

Edita `ESTILO_BASE` en `config.py`. Los estilos disponibles están en `estilos_imagen.py`.

Ejemplo:

```python
# En config.py, cambia ESTILO_BASE por el que prefieras:
from estilos_imagen import ESTILO_ANIME_MODERNO
ESTILO_BASE = ESTILO_ANIME_MODERNO
```

## Reanudación

Si un video falla a mitad de proceso, vuelve a ejecutar. El pipeline **omite pasos ya completados** (si el archivo ya existe y no está vacío).

## Archivos

| Archivo | Función |
|---|---|
| `main.py` | Punto de entrada masivo |
| `pipeline.py` | Orquestador de los 7 pasos por video |
| `config.py` | Configuración centralizada |
| `ai_utils.py` | Funciones de IA (Gemini, Ollama, TTS, Whisper) |
| `imagen_flux.py` | Generador de imágenes con Flux/ComfyUI |
| `video_assembler.py` | Ensamblaje FFmpeg del video final |
| `estilos_imagen.py` | Catálogo de estilos visuales |
| `flux_workflow.json` | Workflow de ComfyUI para Flux |
| `temas.txt` | Lista de temas a procesar |
| `prompts/` | Prompts de IA para cada paso |
