"""
TubeNauta V5 - Masivo IMG
==========================
Creación masiva de videos con imágenes generadas por Flux.

USO:
  1. Edita el archivo "temas.txt" en esta carpeta (un tema por línea).
  2. Ejecuta: python main.py
  3. Cada tema generará una carpeta video1, video2, video3... en output/
     con todo el contenido: guion, metadatos, audio, subtítulos, imágenes y video.

También puedes pasar temas por argumento:
  python main.py "tema 1" "tema 2" "tema 3"
"""
import sys
import time
from pathlib import Path

from config import OUTPUT_DIR, BASE_DIR
from pipeline import ejecutar_pipeline


def cargar_temas_desde_archivo() -> list[str]:
    archivo = BASE_DIR / "temas.txt"
    if not archivo.exists():
        return []
    temas = []
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            temas.append(linea)
    return temas


def obtener_siguiente_numero(output_dir: Path) -> int:
    """Encuentra el siguiente número disponible para video{N}."""
    existentes = []
    if output_dir.exists():
        for carpeta in output_dir.iterdir():
            if carpeta.is_dir() and carpeta.name.startswith("video"):
                try:
                    num = int(carpeta.name.replace("video", ""))
                    existentes.append(num)
                except ValueError:
                    pass
    return max(existentes, default=0) + 1


def buscar_carpeta_existente(tema: str, output_dir: Path) -> Path | None:
    """Busca si ya existe una carpeta con el mismo tema (para reanudar)."""
    if not output_dir.exists():
        return None
    for carpeta in sorted(output_dir.iterdir()):
        if carpeta.is_dir() and carpeta.name.startswith("video"):
            tema_file = carpeta / "1. Tema.txt"
            if tema_file.exists():
                tema_existente = tema_file.read_text(encoding="utf-8").strip()
                if tema_existente == tema.strip():
                    return carpeta
    return None


def esta_completo(carpeta: Path) -> bool:
    """Verifica si un video ya tiene el archivo final generado."""
    video = carpeta / "8. Video.mp4"
    return video.exists() and video.stat().st_size > 0


def main():
    # Obtener temas: primero de argumentos CLI, luego de temas.txt
    if len(sys.argv) > 1:
        temas = sys.argv[1:]
    else:
        temas = cargar_temas_desde_archivo()

    if not temas:
        print("=" * 60)
        print("  TubeNauta V5 - Masivo IMG")
        print("=" * 60)
        print()
        print("  No se encontraron temas.")
        print()
        print("  Opciones:")
        print("    1. Crea un archivo 'temas.txt' con un tema por línea")
        print("    2. Pasa temas como argumentos:")
        print('       python main.py "tema 1" "tema 2" "tema 3"')
        print()
        ejemplo = BASE_DIR / "temas.txt"
        if not ejemplo.exists():
            ejemplo.write_text(
                "# TubeNauta V5 - Masivo IMG\n"
                "# Escribe un tema por línea. Las líneas que empiezan con # se ignoran.\n"
                "# Ejemplo:\n"
                "# la ansiedad y ejercicios para combatirla\n"
                "# 5 datos curiosos sobre el cerebro humano\n"
                "# la historia del chocolate\n",
                encoding="utf-8"
            )
            print(f"  Se creó '{ejemplo}' como ejemplo. Edítalo y vuelve a ejecutar.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Resolver carpetas: reusar existentes o crear nuevas
    tareas = []  # lista de (tema, carpeta, modo)
    siguiente_numero = obtener_siguiente_numero(OUTPUT_DIR)
    for tema in temas:
        carpeta_existente = buscar_carpeta_existente(tema, OUTPUT_DIR)
        if carpeta_existente:
            if esta_completo(carpeta_existente):
                print(f"  ✔ Ya completado: {carpeta_existente.name} → {tema[:50]}")
                tareas.append((tema, carpeta_existente, "completado"))
            else:
                print(f"  ↻ Reanudando: {carpeta_existente.name} → {tema[:50]}")
                tareas.append((tema, carpeta_existente, "reanudar"))
        else:
            carpeta_nueva = OUTPUT_DIR / f"video{siguiente_numero}"
            carpeta_nueva.mkdir(parents=True, exist_ok=True)
            print(f"  + Nuevo: video{siguiente_numero} → {tema[:50]}")
            tareas.append((tema, carpeta_nueva, "nuevo"))
            siguiente_numero += 1

    pendientes = [(t, c, m) for t, c, m in tareas if m != "completado"]
    total = len(pendientes)
    ya_completos = len(tareas) - total

    print()
    print("=" * 60)
    print("  TubeNauta V5 - Masivo IMG")
    print(f"  {total} video(s) por procesar ({ya_completos} ya completados)")
    print("=" * 60)
    print()

    if total == 0:
        print("  Todos los videos ya están completos.")
        return

    resultados = []
    tiempo_total_inicio = time.time()

    for i, (tema, carpeta, modo) in enumerate(pendientes):
        etiqueta = "REANUDANDO" if modo == "reanudar" else "NUEVO"
        print(f"{'─' * 60}")
        print(f"  VIDEO {i + 1}/{total} [{etiqueta}]: {carpeta.name}")
        print(f"  Tema: {tema}")
        print(f"  Carpeta: {carpeta}")
        print(f"{'─' * 60}")

        t_inicio = time.time()
        exito = ejecutar_pipeline(tema, carpeta)
        t_fin = time.time()
        duracion = t_fin - t_inicio

        estado = "✔ ÉXITO" if exito else "✗ ERROR"
        print(f"\n  {estado} - {carpeta.name} ({duracion:.1f}s)\n")
        resultados.append((carpeta.name, tema, exito, duracion))

    # Resumen final
    tiempo_total = time.time() - tiempo_total_inicio
    exitosos = sum(1 for r in resultados if r[2])
    fallidos = total - exitosos

    print()
    print("=" * 60)
    print("  RESUMEN FINAL")
    print("=" * 60)
    print(f"  Total:    {total}")
    print(f"  Exitosos: {exitosos}")
    print(f"  Fallidos: {fallidos}")
    print(f"  Tiempo:   {tiempo_total:.1f}s ({tiempo_total/60:.1f} min)")
    print()

    for nombre, tema, exito, dur in resultados:
        icono = "✔" if exito else "✗"
        print(f"  {icono} {nombre} ({dur:.1f}s) → {tema[:50]}")

    print()
    print(f"  Archivos en: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
