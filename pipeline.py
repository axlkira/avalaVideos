"""
Pipeline completo para un solo video.
Recibe un tema y una carpeta de salida, ejecuta todos los pasos:
  1. Guion
  2. Metadatos (título, descripción, etiquetas)
  3. Voz (TTS)
  4. Subtítulos (Whisper)
  5. Escenas (prompts de imagen)
  6. Imágenes (Flux vía ComfyUI)
  7. Video final (FFmpeg)
"""
import pandas as pd
from pathlib import Path

from config import PROMPTS_DIR, SEGMENT_MIN_DURATION
from ai_utils import (
    chat, limpiar_linea, generar_audio_tts, procesar_audio, extraer_palabras
)
from imagen_flux import generar_imagen
from video_assembler import ensamblar_video


# ─── Cargar prompts ───────────────────────────────────────────────────────────
def _leer_prompt(nombre: str) -> str:
    return (PROMPTS_DIR / nombre).read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 1: GUION
# ═══════════════════════════════════════════════════════════════════════════════

def paso_guion(tema: str, carpeta: Path) -> str:
    print("  [1/7] Generando guion...")
    guion_path = carpeta / "2. Guion.txt"
    if guion_path.exists() and guion_path.stat().st_size > 0:
        guion = guion_path.read_text(encoding="utf-8")
        print(f"  [1/7] ✔ Guion ya existe ({len(guion)} chars), se omite.")
        return guion
    prompt = _leer_prompt("0. Guion.txt")
    guion = chat(prompt, {"{tema}": tema}, preferir_gemini=True)
    guion_path.write_text(guion, encoding="utf-8")
    print(f"  [1/7] ✔ Guion generado ({len(guion)} chars)")
    return guion


# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 2: METADATOS
# ═══════════════════════════════════════════════════════════════════════════════

def paso_metadatos(guion: str, carpeta: Path) -> tuple[str, str, str]:
    print("  [2/7] Generando metadatos...")
    meta_path = carpeta / "3. Metadatos.txt"
    if meta_path.exists() and meta_path.stat().st_size > 0:
        contenido = meta_path.read_text(encoding="utf-8")
        partes = contenido.split("---")
        titulo = partes[0].strip() if len(partes) > 0 else ""
        descripcion = partes[1].strip() if len(partes) > 1 else ""
        etiquetas = partes[2].strip() if len(partes) > 2 else ""
        print(f"  [2/7] ✔ Metadatos ya existen, se omite. Título: {titulo}")
        return titulo, descripcion, etiquetas

    prompt_titulo = _leer_prompt("1. Titulo.txt")
    prompt_desc = _leer_prompt("2. Descripcion.txt")
    prompt_etiq = _leer_prompt("3. Etiquetas.txt")

    titulo = limpiar_linea(chat(prompt_titulo, {"{guion}": guion}, preferir_gemini=False))
    descripcion = chat(prompt_desc, {"{titulo}": titulo, "{guion}": guion}, preferir_gemini=False)
    etiquetas = limpiar_linea(chat(prompt_etiq, {"{titulo}": titulo, "{guion}": guion}, preferir_gemini=False))

    metadatos = f"{titulo}\n---\n{descripcion}\n---\n{etiquetas}"
    meta_path.write_text(metadatos, encoding="utf-8")
    print(f"  [2/7] ✔ Título: {titulo}")
    return titulo, descripcion, etiquetas


# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 3: VOZ (TTS)
# ═══════════════════════════════════════════════════════════════════════════════

def paso_voz(guion: str, carpeta: Path) -> Path:
    print("  [3/7] Generando voz...")
    voz_mp3 = carpeta / "5. Voz.mp3"

    if voz_mp3.exists() and voz_mp3.stat().st_size > 0:
        print("  [3/7] ✔ Voz ya existe, se omite generación.")
        return voz_mp3

    audio = generar_audio_tts(guion)
    # Guardar crudo
    audio.export(str(carpeta / "4. Crudo.wav"), format="wav", bitrate="128k")
    audio.export(str(carpeta / "4. Crudo.mp3"), format="mp3", bitrate="128k")

    # Procesar
    audio_procesado = procesar_audio(audio)
    audio_procesado.export(str(voz_mp3), format="mp3", bitrate="128k")
    print("  [3/7] ✔ Voz generada y procesada.")
    return voz_mp3


# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 4: SUBTÍTULOS (Whisper)
# ═══════════════════════════════════════════════════════════════════════════════

def _formato_srt(t: float) -> str:
    ms = int(t * 1000)
    h = ms // 3600000; ms %= 3600000
    m = ms // 60000; ms %= 60000
    s = ms // 1000; ms %= 1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def paso_subtitulos(voz_mp3: Path, carpeta: Path) -> Path:
    print("  [4/7] Generando subtítulos con Whisper...")
    srt_path = carpeta / "6. Subtitulos.srt"

    if srt_path.exists() and srt_path.stat().st_size > 0:
        print("  [4/7] ✔ Subtítulos ya existen, se omite.")
        return srt_path

    palabras = extraer_palabras(str(voz_mp3))
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, p in enumerate(palabras, start=1):
            inicio = _formato_srt(p["start"])
            fin = _formato_srt(p["end"])
            f.write(f"{i}\n{inicio} --> {fin}\n{p['word']}\n\n")

    print(f"  [4/7] ✔ {len(palabras)} palabras transcritas.")
    return srt_path


# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 5: ESCENAS (prompts para cada segmento)
# ═══════════════════════════════════════════════════════════════════════════════

def _convertir_srt_a_segundos(tiempo_srt: str) -> float:
    tiempo_srt = tiempo_srt.replace(",", ".")
    horas, minutos, segundos_ms = tiempo_srt.split(":")
    segundos, milisegundos = segundos_ms.split(".")
    return int(horas) * 3600 + int(minutos) * 60 + int(segundos) + int(milisegundos) / 1000


def _leer_palabras_srt(ruta_srt: Path) -> list[dict]:
    palabras = []
    with open(ruta_srt, encoding="utf-8") as f:
        lineas = f.read().splitlines()
    i = 0
    while i < len(lineas):
        if (lineas[i].strip().isdigit() and (i + 2 < len(lineas)) and " --> " in lineas[i + 1]):
            tiempo_str = lineas[i + 1].strip()
            texto = lineas[i + 2].strip()
            inicio_str, fin_str = tiempo_str.split(" --> ")
            palabras.append({
                "palabra": texto,
                "inicio": _convertir_srt_a_segundos(inicio_str),
                "fin": _convertir_srt_a_segundos(fin_str),
            })
            i += 3
        else:
            i += 1
    return palabras


def _generar_segmentos(palabras: list[dict]) -> list[tuple]:
    segmentos = []
    segmento_temporal, tiempo_inicio = [], 0.0
    for palabra in palabras:
        if not segmento_temporal:
            tiempo_inicio = palabra["inicio"]
        segmento_temporal.append(palabra)
        if palabra["fin"] - tiempo_inicio >= SEGMENT_MIN_DURATION:
            texto = " ".join(p["palabra"] for p in segmento_temporal)
            segmentos.append((tiempo_inicio, palabra["fin"], texto))
            segmento_temporal = []
    if segmento_temporal:
        texto = " ".join(p["palabra"] for p in segmento_temporal)
        segmentos.append((tiempo_inicio, segmento_temporal[-1]["fin"], texto))
    return segmentos


def _detectar_modo_historia(titulo: str, guion: str) -> str:
    texto = f"{titulo} {guion}".lower()
    palabras_bio = ["biografia", "biografía", "biography", "la vida de",
                    "vida de", "historia de", "origen de", "trayectoria de"]
    return "BIOGRAPHY" if any(p in texto for p in palabras_bio) else "ORIGINAL"


def paso_escenas(srt_path: Path, titulo: str, guion: str, carpeta: Path) -> Path:
    print("  [5/7] Generando prompts de escenas...")
    csv_path = carpeta / "7. Escenas.csv"

    if csv_path.exists() and csv_path.stat().st_size > 0:
        print("  [5/7] ✔ Escenas ya existen, se omite.")
        return csv_path

    prompt_escena = _leer_prompt("4. Escena.txt")
    palabras = _leer_palabras_srt(srt_path)
    segmentos = _generar_segmentos(palabras)
    modo = _detectar_modo_historia(titulo, guion)
    total = len(segmentos)

    filas = []
    for indice, (inicio, fin, subtitulos) in enumerate(segmentos, start=1):
        duracion = max(0.0, fin - inicio)
        reemplazos = {
            "{subtitulos}": subtitulos.strip(),
            "{titulo}": titulo,
            "{guion}": guion,
            "{indice}": str(indice),
            "{total}": str(total),
            "{inicio}": f"{inicio:.2f}",
            "{final}": f"{fin:.2f}",
            "{duracion}": f"{duracion:.2f}",
            "{modo_historia}": modo,
        }
        escena = chat(prompt_escena, reemplazos, preferir_gemini=False)
        filas.append({
            "Inicio": round(max(0.0, inicio), 3),
            "Final": round(fin, 3),
            "Subtitulos": subtitulos.strip(),
            "Escena": escena,
        })
        print(f"    Escena {indice}/{total} generada")

    if filas:
        pd.DataFrame(filas).to_csv(csv_path, index=False, encoding="utf-8")
    print(f"  [5/7] ✔ {len(filas)} escenas generadas.")
    return csv_path


# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 6: IMÁGENES (Flux)
# ═══════════════════════════════════════════════════════════════════════════════

def paso_imagenes(csv_path: Path, carpeta: Path) -> Path:
    print("  [6/7] Generando imágenes con Flux...")
    imagenes_dir = carpeta / "imagenes"
    imagenes_dir.mkdir(parents=True, exist_ok=True)

    escenas_df = pd.read_csv(csv_path, encoding="utf-8")
    total = len(escenas_df)
    print(f"    Se procesarán {total} escenas.")

    for idx, (_, row) in enumerate(escenas_df.iterrows(), 1):
        ini = float(row['Inicio'])
        fin = float(row['Final'])
        archivo = f"{ini:.2f}_{fin:.2f}_1.png"
        ruta_png = imagenes_dir / archivo

        if ruta_png.is_file() and ruta_png.stat().st_size > 0:
            print(f"    Escena {idx}/{total}: ya existe {archivo}, se omite")
            continue

        print(f"    Escena {idx}/{total}: generando {archivo}")
        generar_imagen(row["Escena"], ruta_png)

    print(f"  [6/7] ✔ Imágenes generadas en {imagenes_dir}")
    return imagenes_dir


# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 7: VIDEO FINAL
# ═══════════════════════════════════════════════════════════════════════════════

def paso_video(csv_path: Path, imagenes_dir: Path, voz_mp3: Path,
               srt_path: Path, carpeta: Path) -> Path:
    print("  [7/7] Ensamblando video final...")
    output = carpeta / "8. Video.mp4"
    escenas_df = pd.read_csv(csv_path, encoding="utf-8")
    escenas = escenas_df.to_dict('records')

    exito = ensamblar_video(escenas, imagenes_dir, voz_mp3, srt_path, output)
    if exito:
        print(f"  [7/7] ✔ Video final: {output}")
    else:
        print("  [7/7] ✗ Error al ensamblar video.")
    return output


# ═══════════════════════════════════════════════════════════════════════════════
#  EJECUTAR PIPELINE COMPLETO
# ═══════════════════════════════════════════════════════════════════════════════

def ejecutar_pipeline(tema: str, carpeta: Path) -> bool:
    """
    Ejecuta el pipeline completo para un tema en la carpeta indicada.
    Retorna True si fue exitoso.
    """
    carpeta.mkdir(parents=True, exist_ok=True)

    # Guardar tema
    (carpeta / "1. Tema.txt").write_text(tema, encoding="utf-8")

    try:
        # Paso 1: Guion
        guion = paso_guion(tema, carpeta)
        if not guion:
            print("  ✗ No se pudo generar el guion.")
            return False

        # Paso 2: Metadatos
        titulo, descripcion, etiquetas = paso_metadatos(guion, carpeta)

        # Paso 3: Voz
        voz_mp3 = paso_voz(guion, carpeta)

        # Paso 4: Subtítulos
        srt_path = paso_subtitulos(voz_mp3, carpeta)

        # Paso 5: Escenas
        csv_path = paso_escenas(srt_path, titulo, guion, carpeta)

        # Paso 6: Imágenes
        imagenes_dir = paso_imagenes(csv_path, carpeta)

        # Paso 7: Video
        paso_video(csv_path, imagenes_dir, voz_mp3, srt_path, carpeta)

        return True

    except Exception as e:
        print(f"  ✗ Error en pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False
