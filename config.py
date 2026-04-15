"""
Configuración centralizada para TubeNauta V5 - Masivo IMG
"""
import os
from pathlib import Path
from estilos_imagen import ESTILOS

# ─── Rutas base ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output"
FLUX_WORKFLOW = BASE_DIR / "flux_workflow.json"

# ─── API Keys ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ─── Modelos de IA ────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
OLLAMA_MODEL = "gemma3:4b"

# ─── ComfyUI / Flux ──────────────────────────────────────────────────────────
COMFYUI_URL = "http://127.0.0.1:8188"

# Nodos del workflow Flux que se modifican dinámicamente
FLUX_NODOS = {
    "prompt_positivo": "6",      # CLIPTextEncode (Positive Prompt)
    "seed": "100",               # RandomNoise
    "save_image": "114",         # SaveImage
    "width_latent": "99",        # EmptyFlux2LatentImage
    "height_latent": "99",       # EmptyFlux2LatentImage
    "width_scheduler": "102",    # Flux2Scheduler
    "height_scheduler": "102",   # Flux2Scheduler
}

# ─── Imagen ───────────────────────────────────────────────────────────────────
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1536

# ─── Estilo base para imágenes ────────────────────────────────────────────────
# Leer estilo desde variable de entorno (usado por el frontend web)
_estilo_seleccionado = os.environ.get("TUBENAUTA_ESTILO", "narrativo")
ESTILO_BASE = ESTILOS.get(_estilo_seleccionado, ESTILOS["narrativo"])

# Instrucciones anti-defectos anatómicos (se añade al final de cada prompt)
ANATOMY_FIX = (
    "anatomically correct, perfect human anatomy, exactly five fingers on each hand, "
    "correct number of limbs, no extra fingers, no missing fingers, no extra hands, "
    "no deformed hands, no extra heads, no duplicate body parts,no deformed musician instruments, "
    "perfect animal anatomy, correct number of legs and eyes for each species, "
    "no mutated features, no body horror, no anatomical defects, "
    "physically accurate proportions, natural realistic body structure, "
)

# ─── Video ────────────────────────────────────────────────────────────────────
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# ─── TTS ──────────────────────────────────────────────────────────────────────
TTS_VOICE = "Algieba"
TTS_LANGUAGE_INSTRUCTION = "Lee en voz alta en español neutro con un tono cálido y amigable: "

# ─── Whisper ──────────────────────────────────────────────────────────────────
WHISPER_MODEL = "openai/whisper-large-v3"
WHISPER_LANGUAGE = "es"

# ─── Automatización módulo de noticias ─────────────────────────────────────────
AUTO_NEWS_GENERATE_IMAGES = True
AUTO_NEWS_ASSEMBLE_VIDEO = True

# ─── Segmentación de subtítulos ──────────────────────────────────────────────
SEGMENT_MIN_DURATION = 2.5  # segundos mínimos por segmento de escena
