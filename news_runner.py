"""
TubeNauta News Module - Entry Point
====================================
Creación automática de videos desde noticias/historias completas.
Reproduce el pipeline original pero con entrada de noticias en lugar de temas cortos.

USO:
  1. Edita "noticias.txt" en esta carpeta (una noticia completa por entrada)
  2. Ejecuta: python news_runner.py
  3. Cada noticia generará una carpeta en output/news_videos/

Separador de múltiples noticias en el archivo: línea con "---" (tres guiones)
"""
import sys
import time
from pathlib import Path

from config import OUTPUT_DIR, BASE_DIR
from news_pipeline import ejecutar_pipeline_noticias


def cargar_noticias_desde_archivo() -> list[str]:
    """Carga noticias desde noticias.txt, separadas por ---"""
    archivo = BASE_DIR / "noticias.txt"
    if not archivo.exists():
        return []
    
    contenido = archivo.read_text(encoding="utf-8")
    # Separar por líneas que contengan solo ---
    noticias = []
    for bloque in contenido.split("\n---\n"):
        bloque = bloque.strip()
        if bloque and not bloque.startswith("#"):
            noticias.append(bloque)
    return noticias


def obtener_siguiente_numero_news(output_dir: Path) -> int:
    """Encuentra el siguiente número para news{N}."""
    existentes = []
    if output_dir.exists():
        for carpeta in output_dir.iterdir():
            if carpeta.is_dir() and carpeta.name.startswith("news"):
                try:
                    num = int(carpeta.name.replace("news", ""))
                    existentes.append(num)
                except ValueError:
                    pass
    return max(existentes, default=0) + 1


def buscar_carpeta_existente(noticia: str, output_dir: Path) -> Path | None:
    """Busca si ya existe carpeta con la misma noticia (primeros 100 chars)."""
    if not output_dir.exists():
        return None
    noticia_hash = noticia[:100].strip()
    for carpeta in sorted(output_dir.iterdir()):
        if carpeta.is_dir() and carpeta.name.startswith("news"):
            noticia_file = carpeta / "1. Noticia.txt"
            if noticia_file.exists():
                noticia_existente = noticia_file.read_text(encoding="utf-8").strip()[:100]
                if noticia_existente == noticia_hash:
                    return carpeta
    return None


def esta_completo(carpeta: Path) -> bool:
    """Verifica si el video final ya existe."""
    video = carpeta / "8. Video.mp4"
    return video.exists() and video.stat().st_size > 0


def main():
    # Obtener noticias: primero de argumentos CLI (como un solo bloque), luego de archivo
    if len(sys.argv) > 1:
        noticias = [" ".join(sys.argv[1:])]
    else:
        noticias = cargar_noticias_desde_archivo()

    if not noticias:
        print("=" * 60)
        print("  TubeNauta News Module")
        print("=" * 60)
        print()
        print("  No se encontraron noticias.")
        print()
        print("  Opciones:")
        print("    1. Crea un archivo 'noticias.txt' con noticias completas")
        print("       Separadas por líneas con '---' (tres guiones)")
        print("    2. Pasa noticia como argumentos:")
        print('       python news_runner.py "Texto completo de la noticia..."')
        print()
        ejemplo = BASE_DIR / "noticias.txt"
        if not ejemplo.exists():
            ejemplo.write_text(
                "# TubeNauta News Module\n"
                "# Escribe noticias completas aquí\n"
                "# Separa múltiples noticias con líneas que contengan solo ---\n"
                "# Ejemplo:\n\n"
                "El Abatimiento de El Mencho (Hoy)\n"
                "Fecha: 22 de febrero de 2026.\n"
                "Suceso: Nemesio Oseguera Cervantes...\n"
                "\n---\n\n"
                "La Captura del Chapo Guzmán (2014)\n"
                "Fecha: 22 de febrero de 2014.\n"
                "Suceso: Joaquín El Chapo Guzmán...\n",
                encoding="utf-8"
            )
            print(f"  Se creó '{ejemplo}' como ejemplo. Edítalo y vuelve a ejecutar.")
        return

    # Directorio de salida para noticias
    news_output_dir = OUTPUT_DIR / "news_videos"
    news_output_dir.mkdir(parents=True, exist_ok=True)

    # Resolver carpetas
    tareas = []  # (noticia, carpeta, modo)
    siguiente_numero = obtener_siguiente_numero_news(news_output_dir)
    
    for noticia in noticias:
        carpeta_existente = buscar_carpeta_existente(noticia, news_output_dir)
        if carpeta_existente:
            if esta_completo(carpeta_existente):
                print(f"  ✔ Ya completado: {carpeta_existente.name}")
                tareas.append((noticia, carpeta_existente, "completado"))
            else:
                print(f"  ↻ Reanudando: {carpeta_existente.name}")
                tareas.append((noticia, carpeta_existente, "reanudar"))
        else:
            carpeta_nueva = news_output_dir / f"news{siguiente_numero}"
            carpeta_nueva.mkdir(parents=True, exist_ok=True)
            print(f"  + Nuevo: news{siguiente_numero}")
            tareas.append((noticia, carpeta_nueva, "nuevo"))
            siguiente_numero += 1

    pendientes = [(n, c, m) for n, c, m in tareas if m != "completado"]
    total = len(pendientes)
    ya_completos = len(tareas) - total

    print()
    print("=" * 60)
    print("  TubeNauta News Module")
    print(f"  {total} video(s) por procesar ({ya_completos} ya completados)")
    print("=" * 60)
    print()

    if total == 0:
        print("  Todos los videos ya están completos.")
        return

    resultados = []
    tiempo_total_inicio = time.time()

    for i, (noticia, carpeta, modo) in enumerate(pendientes):
        etiqueta = "REANUDANDO" if modo == "reanudar" else "NUEVO"
        print(f"{'─' * 60}")
        print(f"  VIDEO {i + 1}/{total} [{etiqueta}]: {carpeta.name}")
        print(f"  Noticia (primeros 80 chars): {noticia[:80]}...")
        print(f"  Carpeta: {carpeta}")
        print(f"{'─' * 60}")

        t_inicio = time.time()
        exito = ejecutar_pipeline_noticias(noticia, carpeta)
        t_fin = time.time()
        duracion = t_fin - t_inicio

        estado = "✔ ÉXITO" if exito else "✗ ERROR"
        print(f"\n  {estado} - {carpeta.name} ({duracion:.1f}s)\n")
        resultados.append((carpeta.name, noticia[:50], exito, duracion))

    # Resumen
    tiempo_total = time.time() - tiempo_total_inicio
    exitosos = sum(1 for r in resultados if r[2])
    fallidos = total - exitosos

    print()
    print("=" * 60)
    print("  RESUMEN FINAL - News Module")
    print("=" * 60)
    print(f"  Total:    {total}")
    print(f"  Exitosos: {exitosos}")
    print(f"  Fallidos: {fallidos}")
    print(f"  Tiempo:   {tiempo_total:.1f}s ({tiempo_total/60:.1f} min)")
    print()

    for nombre, noticia_corta, exito, dur in resultados:
        icono = "✔" if exito else "✗"
        print(f"  {icono} {nombre} ({dur:.1f}s) → {noticia_corta}")

    print()
    print(f"  Archivos en: {news_output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
