"""
Ensamblador de video: combina imágenes + audio + subtítulos en un video final.
Replica la lógica de _7. Armar.py pero parametrizado.
"""
import os
import re
import subprocess
import random
import tempfile
from pathlib import Path

from config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS


# ═══════════════════════════════════════════════════════════════════════════════
#  UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════════

def srt_a_segundos(t: str) -> float:
    t = t.replace(',', '.')
    h, m, s_ms = t.split(':')
    s, ms = s_ms.split('.')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def leer_srt(ruta_srt: Path) -> list[tuple]:
    subtitulos = []
    if not ruta_srt.exists():
        return subtitulos
    bloques = ruta_srt.read_text(encoding='utf-8').strip().split('\n\n')
    for bloque in bloques:
        lineas = bloque.splitlines()
        if len(lineas) >= 3:
            try:
                tiempos = lineas[1].split(' --> ')
                ini = srt_a_segundos(tiempos[0])
                fin = srt_a_segundos(tiempos[1])
                txt = lineas[2]
                subtitulos.append((ini, fin, txt))
            except Exception:
                continue
    return subtitulos


def ajustar_subtitulos_continuos(subs, duracion_video):
    if not subs:
        return subs
    subs_sorted = sorted(subs, key=lambda x: x[0])
    subs_sorted[0] = (0.0, subs_sorted[0][1], subs_sorted[0][2])
    for i in range(len(subs_sorted) - 1):
        inicio = subs_sorted[i][0]
        fin = subs_sorted[i + 1][0]
        txt = subs_sorted[i][2]
        subs_sorted[i] = (inicio, fin, txt)
    ultimo = subs_sorted[-1]
    subs_sorted[-1] = (ultimo[0], duracion_video, ultimo[2])
    return subs_sorted


def segundos_a_ass(t: float) -> str:
    horas = int(t // 3600)
    minutos = int((t % 3600) // 60)
    segundos = int(t % 60)
    centesimas = int((t - int(t)) * 100)
    return f"{horas:d}:{minutos:02d}:{segundos:02d}.{centesimas:02d}"


def limpiar_texto(texto: str) -> str:
    limpio = re.sub(r'[^\w\s]', '', texto)
    return limpio.upper()


def escapar_ruta_windows(ruta: Path) -> str:
    ruta_str = ruta.resolve().as_posix()
    if os.name == 'nt':
        ruta_str = str(ruta.resolve()).replace('\\', '\\\\').replace(':', '\\:')
    return ruta_str


def obtener_duracion(path: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True, capture_output=True, text=True
        )
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def archivo_valido(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


# ═══════════════════════════════════════════════════════════════════════════════
#  ASS (subtítulos avanzados)
# ═══════════════════════════════════════════════════════════════════════════════

def generar_ass(srt_path: Path, ass_path: Path, duracion_video: float):
    width, height = VIDEO_WIDTH, VIDEO_HEIGHT
    pos_x = width // 2
    pos_y = int(height * 0.75)
    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,110,&H0000FFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,125,100,0,0,1,8,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    subs = leer_srt(srt_path)
    subs_ajustados = ajustar_subtitulos_continuos(subs, duracion_video)
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_header)
        for ini, fin, txt in subs_ajustados:
            txt_lim = limpiar_texto(txt)
            ini_ass = segundos_a_ass(ini)
            fin_ass = segundos_a_ass(fin)
            linea = f"Dialogue: 0,{ini_ass},{fin_ass},Default,,0,0,0,,{{\\pos({pos_x},{pos_y})}}{txt_lim}\n"
            f.write(linea)


# ═══════════════════════════════════════════════════════════════════════════════
#  REESCALAR IMAGEN → CLIP DE VIDEO
# ═══════════════════════════════════════════════════════════════════════════════

def reescalar_imagen(imagen_path: Path, output_path: Path,
                     width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT,
                     duracion_objetivo: float = None):
    if imagen_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
        comando = ["ffmpeg", "-y", "-loop", "1", "-i", str(imagen_path)]
    else:
        comando = ["ffmpeg", "-y", "-i", str(imagen_path)]

    if duracion_objetivo and duracion_objetivo > 0:
        comando += ["-t", f"{duracion_objetivo:.6f}"]

    vf_filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "format=yuv420p"
    ]

    if imagen_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.bmp'] and duracion_objetivo:
        frames = max(1, int(duracion_objetivo * FPS))
        esquina = random.choice(["tl", "tr", "bl", "br"])
        if esquina == "tl":
            x_expr, y_expr = "0", "0"
        elif esquina == "tr":
            x_expr, y_expr = "iw-(iw/zoom)", "0"
        elif esquina == "bl":
            x_expr, y_expr = "0", "ih-(ih/zoom)"
        else:
            x_expr, y_expr = "iw-(iw/zoom)", "ih-(ih/zoom)"
        vf_filters.append(
            f"zoompan=z='1.2-0.2*on/{frames}':"
            f"x='{x_expr}':"
            f"y='{y_expr}':"
            f"d=1*{FPS}:s={width}x{height}:fps={FPS}"
        )

    comando += [
        "-vf", ",".join(vf_filters),
        "-c:v", "h264_nvenc",
        "-preset", "p6",
        "-tune", "ll",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-vsync", "cfr",
        "-g", "60",
        "-profile:v", "high",
        "-level:v", "4.2",
        "-an",
        str(output_path)
    ]
    result = subprocess.run(comando, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ERROR ffmpeg para {imagen_path.name}: {result.stderr[:500]}")
        raise Exception(f"FFmpeg error: {result.stderr}")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENSAMBLAJE FINAL
# ═══════════════════════════════════════════════════════════════════════════════

def ensamblar_video(escenas: list[dict], imagenes_dir: Path, voz_mp3: Path,
                    srt_file: Path, output_video: Path):
    """
    escenas: lista de dicts con claves 'Inicio', 'Final'
    """
    print(f"  [Video] Buscando imágenes para {len(escenas)} escenas...")
    imagenes_esperados = []

    for idx, esc in enumerate(escenas, 1):
        ini = float(esc['Inicio'])
        fin = float(esc['Final'])
        nombre_png = f"{ini:.2f}_{fin:.2f}_1.png"
        ruta_png = imagenes_dir / nombre_png
        if not archivo_valido(ruta_png):
            print(f"    ERROR: No se encontró imagen para escena {idx}: {ini:.2f}-{fin:.2f}")
            return False
        imagenes_esperados.append((ini, fin, ruta_png))

    print(f"  [Video] {len(imagenes_esperados)} imágenes encontradas. Procesando...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        rescaled_dir = temp_path / "rescaled"
        rescaled_dir.mkdir()
        lista_txt = temp_path / "list.txt"

        with open(lista_txt, 'w', encoding='utf-8') as f:
            for idx, (ini, fin, imagen) in enumerate(sorted(imagenes_esperados, key=lambda x: x[0]), 1):
                dur = max(0.5, fin - ini)
                output_clip = rescaled_dir / (imagen.stem + ".mp4")
                print(f"    Clip {idx}/{len(imagenes_esperados)}: {imagen.name} ({dur:.2f}s)")
                reescalar_imagen(imagen, output_clip, duracion_objetivo=dur)
                f.write(f"file '{output_clip.resolve().as_posix()}'\n")

        # Concatenar clips
        print("  [Video] Concatenando clips...")
        tmp_concat = temp_path / "concat.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(lista_txt), "-c", "copy", str(tmp_concat)
        ], check=True, capture_output=True)

        # Generar subtítulos ASS
        print("  [Video] Generando subtítulos ASS...")
        ass_path = temp_path / "subs.ass"
        video_dur = obtener_duracion(tmp_concat)
        generar_ass(srt_file, ass_path, video_dur)
        ass_esc = escapar_ruta_windows(ass_path)

        # Banner
        texto_banner = "Suscríbete"
        font_path = Path("C:/Windows/Fonts/Impact.ttf")
        if not font_path.exists():
            font_path = Path("C:/Windows/Fonts/Arial.ttf")
        font_esc = escapar_ruta_windows(font_path)

        # Extensión si audio > video
        voz_dur = obtener_duracion(voz_mp3) if voz_mp3.exists() else 0.0
        ext = 0.0
        if voz_dur > 0 and video_dur > 0 and voz_dur > video_dur:
            ext = max(0.0, voz_dur - video_dur + 0.05)

        drawtext_filter = (
            f"drawtext=fontfile='{font_esc}':"
            f"text='{texto_banner}':fontcolor=white:fontsize=64:"
            f"box=1:boxcolor=red@0.9:boxborderw=25:x=25:y=25"
        )
        vf_parts = ["format=yuv420p", drawtext_filter]
        if ext > 0:
            vf_parts.append(f"tpad=stop_mode=clone:stop_duration={ext:.6f}")
        vf_parts.append(f"subtitles='{ass_esc}'")
        vf_filter = ",".join(vf_parts)

        # Render final
        print("  [Video] Renderizando video final...")
        if output_video.exists():
            try:
                output_video.unlink()
            except OSError:
                output_video = output_video.with_name(output_video.stem + "_new.mp4")

        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(tmp_concat),
            "-i", str(voz_mp3) if voz_mp3.exists() else str(tmp_concat),
            "-filter_complex",
            f"[1:a]volume=1.0[a1];[a1]anullsink;[0:v] {vf_filter} [vout]",
            "-map", "[vout]", "-map", "1:a",
            "-c:v", "h264_nvenc",
            "-preset", "p6",
            "-tune", "ll",
            "-crf", "18",
            "-profile:v", "high", "-level:v", "4.2",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", str(output_video)
        ]
        try:
            subprocess.run(cmd_final, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"    ERROR generando video final: {e.stderr[:500] if e.stderr else 'Sin detalle'}")
            raise

    print(f"  [Video] ✔ Video generado: {output_video}")
    return True
