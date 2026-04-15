"""
Generador de imágenes usando Flux vía ComfyUI API.
Usa el workflow fluxAxl.json como template.
"""
import json
import random
import uuid
import time
import os
import requests
from pathlib import Path

from config import COMFYUI_URL, FLUX_WORKFLOW, FLUX_NODOS, ESTILO_BASE, ANATOMY_FIX
from estilos_imagen import ESTILOS


def _cargar_workflow() -> dict:
    return json.loads(FLUX_WORKFLOW.read_text(encoding="utf-8"))


def _obtener_estilo_actual() -> str:
    """Obtiene el estilo seleccionado actualmente.
    Primero intenta leer desde variable de entorno TUBENAUTA_ESTILO,
    luego desde archivo .estilo_temp.txt,
    finalmente usa ESTILO_BASE como fallback.
    """
    # 1. Intentar variable de entorno
    estilo_env = os.environ.get('TUBENAUTA_ESTILO')
    if estilo_env and estilo_env in ESTILOS:
        return ESTILOS[estilo_env]

    # 2. Intentar archivo temporal
    estilo_temp_file = Path.cwd() / '.estilo_temp.txt'
    if estilo_temp_file.exists():
        estilo_id = estilo_temp_file.read_text(encoding='utf-8').strip()
        if estilo_id in ESTILOS:
            return ESTILOS[estilo_id]

    # 3. Usar estilo base por defecto
    return ESTILO_BASE


def generar_imagen(prompt: str, ruta_salida: Path) -> None:
    workflow = _cargar_workflow()

    # Inyectar prompt positivo con estilo (obtener estilo actual)
    estilo_actual = _obtener_estilo_actual()
    prompt_final = estilo_actual + prompt + " " + ANATOMY_FIX
    workflow[FLUX_NODOS["prompt_positivo"]]["inputs"]["text"] = prompt_final

    # Seed aleatorio
    workflow[FLUX_NODOS["seed"]]["inputs"]["noise_seed"] = random.randint(0, 2**64 - 1)

    # Prefix de archivo
    filename_prefix = ruta_salida.stem
    workflow[FLUX_NODOS["save_image"]]["inputs"]["filename_prefix"] = filename_prefix

    # Enviar a ComfyUI
    payload = {"prompt": workflow, "client_id": str(uuid.uuid4())}
    print(f"    → Enviando prompt Flux a {COMFYUI_URL} para {ruta_salida.name}...")

    r = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=120)
    if not r.ok:
        print(f"\n    Error {r.status_code}: {r.text}\n")
        r.raise_for_status()

    prompt_id = r.json().get("prompt_id")

    # Esperar resultado
    print("      Esperando resultado de ComfyUI...")
    img_info = None
    while True:
        try:
            h = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=60)
            if h.status_code == 200:
                hist = h.json()
                out = hist.get(prompt_id, {}).get("outputs", {}).get(FLUX_NODOS["save_image"])
                if out and out.get("images"):
                    img_info = out["images"][0]
                    if "filename" in img_info:
                        print("      ✔ Imagen Flux lista.")
                        break
        except requests.RequestException:
            pass
        time.sleep(2)

    # Descargar imagen
    ruta_salida.write_bytes(
        requests.get(
            f"{COMFYUI_URL}/view",
            params={
                "filename": img_info["filename"],
                "subfolder": img_info.get("subfolder", ""),
                "type": "output",
            },
            timeout=300,
        ).content
    )
    print(f"      ✔ Imagen guardada: {ruta_salida}")
