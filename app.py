"""
TubeNauta V5 - Web Frontend
===========================
Interfaz web Flask para gestionar la creación masiva de videos.
"""
import os
import json
import subprocess
import threading
import queue
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_file, redirect, url_for

from config import OUTPUT_DIR, BASE_DIR, GEMINI_API_KEY, COMFYUI_URL
from estilos_imagen import ESTILOS

app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')

# Sistema de logs global (lista thread-safe)
logs_list = []
logs_lock = threading.Lock()
processing_status = {
    'running': False,
    'current_video': None,
    'total_videos': 0,
    'completed': 0,
    'mode': None,  # 'temas' o 'noticias'
    'last_log_index': 0
}

def add_log(message, log_type='info'):
    """Agrega un log a la lista global de forma thread-safe."""
    with logs_lock:
        logs_list.append({
            'type': log_type,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })


# ═══════════════════════════════════════════════════════════════════════════════
#  RUTAS PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def dashboard():
    """Dashboard principal con resumen."""
    # Contar videos generados
    videos_temas = list((OUTPUT_DIR).glob('video*/8. Video.mp4')) if OUTPUT_DIR.exists() else []
    news_dir = OUTPUT_DIR / 'news_videos'
    videos_noticias = list(news_dir.glob('news*/8. Video.mp4')) if news_dir.exists() else []
    
    # Estado de servicios
    comfyui_status = check_comfyui_status()
    gemini_configured = bool(GEMINI_API_KEY)
    
    stats = {
        'total_videos': len(videos_temas) + len(videos_noticias),
        'videos_temas': len(videos_temas),
        'videos_noticias': len(videos_noticias),
        'comfyui_online': comfyui_status,
        'gemini_configured': gemini_configured,
        'processing': processing_status['running']
    }
    
    return render_template('dashboard.html', stats=stats)


@app.route('/temas')
def temas():
    """Editor de temas cortos."""
    # Cargar temas existentes
    temas_file = BASE_DIR / 'temas.txt'
    temas_content = ""
    if temas_file.exists():
        temas_content = temas_file.read_text(encoding='utf-8')
    
    return render_template('temas.html', temas_content=temas_content)


@app.route('/noticias')
def noticias():
    """Editor de noticias completas."""
    # Cargar noticias existentes
    noticias_file = BASE_DIR / 'noticias.txt'
    noticias_content = ""
    if noticias_file.exists():
        noticias_content = noticias_file.read_text(encoding='utf-8')
    
    return render_template('noticias.html', noticias_content=noticias_content)


@app.route('/progreso')
def progreso():
    """Página de progreso en tiempo real."""
    return render_template('progreso.html', status=processing_status)


@app.route('/galeria')
def galeria():
    """Galería de videos generados."""
    videos = []
    
    # Videos de temas
    if OUTPUT_DIR.exists():
        for carpeta in sorted(OUTPUT_DIR.glob('video*')):
            if carpeta.is_dir():
                video_path = carpeta / '8. Video.mp4'
                if video_path.exists():
                    videos.append(get_video_info(carpeta, 'tema'))
    
    # Videos de noticias
    news_dir = OUTPUT_DIR / 'news_videos'
    if news_dir.exists():
        for carpeta in sorted(news_dir.glob('news*')):
            if carpeta.is_dir():
                video_path = carpeta / '8. Video.mp4'
                if video_path.exists():
                    videos.append(get_video_info(carpeta, 'noticia'))
    
    return render_template('galeria.html', videos=videos)


@app.route('/config')
def config_page():
    """Página de configuración."""
    from config import (
        GEMINI_API_KEY, COMFYUI_URL, IMAGE_WIDTH, IMAGE_HEIGHT,
        TTS_VOICE, WHISPER_MODEL, ESTILO_BASE
    )
    
    config_data = {
        'gemini_api_key': GEMINI_API_KEY[:10] + '...' if GEMINI_API_KEY else '',
        'comfyui_url': COMFYUI_URL,
        'image_width': IMAGE_WIDTH,
        'image_height': IMAGE_HEIGHT,
        'tts_voice': TTS_VOICE,
        'whisper_model': WHISPER_MODEL,
        'estilo_base': ESTILO_BASE
    }
    
    return render_template('config.html', config=config_data)


# ═══════════════════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/estilos', methods=['GET'])
def api_estilos():
    """Devuelve la lista de estilos disponibles."""
    estilos_list = []
    for key, value in ESTILOS.items():
        # Crear nombre legible
        nombre = key.replace('_', ' ').title()
        preview = value[:80] + '...' if len(value) > 80 else value
        estilos_list.append({
            'id': key,
            'nombre': nombre,
            'preview': preview
        })
    return jsonify(estilos_list)


@app.route('/api/start', methods=['POST'])
def api_start():
    """Inicia el procesamiento de videos."""
    if processing_status['running']:
        return jsonify({'error': 'Ya hay un procesamiento en curso'}), 400
    
    data = request.json
    mode = data.get('mode')  # 'temas' o 'noticias'
    content = data.get('content', '')
    estilo = data.get('estilo', 'narrativo')  # Estilo seleccionado
    
    if not mode or not content:
        return jsonify({'error': 'Faltan parámetros'}), 400
    
    # Validar que el estilo existe
    if estilo not in ESTILOS:
        return jsonify({'error': f'Estilo "{estilo}" no existe'}), 400
    
    # Guardar contenido en archivo correspondiente
    if mode == 'temas':
        file_path = BASE_DIR / 'temas.txt'
    else:
        file_path = BASE_DIR / 'noticias.txt'
    
    file_path.write_text(content, encoding='utf-8')
    
    # Guardar estilo seleccionado temporalmente
    estilo_file = BASE_DIR / '.estilo_temp.txt'
    estilo_file.write_text(estilo, encoding='utf-8')
    
    # Iniciar procesamiento en thread separado
    processing_status['running'] = True
    processing_status['mode'] = mode
    processing_status['completed'] = 0
    processing_status['estilo'] = estilo
    
    thread = threading.Thread(target=run_pipeline, args=(mode, estilo))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'mode': mode, 'estilo': estilo})


@app.route('/api/logs')
def api_logs():
    """Devuelve logs nuevos desde el último índice solicitado."""
    last_index = request.args.get('last_index', 0, type=int)
    
    with logs_lock:
        new_logs = logs_list[last_index:]
        return jsonify({
            'logs': new_logs,
            'last_index': len(logs_list),
            'status': processing_status.copy()
        })


@app.route('/api/download/<path:video_path>')
def api_download(video_path):
    """Descarga un video."""
    full_path = OUTPUT_DIR / video_path
    if full_path.exists():
        return send_file(full_path, as_attachment=True)
    return jsonify({'error': 'Video no encontrado'}), 404


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def check_comfyui_status():
    """Verifica si ComfyUI está online."""
    try:
        import requests
        response = requests.get(COMFYUI_URL, timeout=2)
        return response.status_code == 200
    except:
        return False


def get_video_info(carpeta: Path, tipo: str):
    """Extrae información de un video generado."""
    video_path = carpeta / '8. Video.mp4'
    tema_path = carpeta / '1. Tema.txt' if tipo == 'tema' else carpeta / '1. Noticia.txt'
    meta_path = carpeta / '3. Metadatos.txt'
    
    info = {
        'folder': carpeta.name,
        'tipo': tipo,
        'video_path': str(video_path.relative_to(OUTPUT_DIR)),
        'size_mb': round(video_path.stat().st_size / (1024 * 1024), 2),
        'created': datetime.fromtimestamp(video_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
        'tema': '',
        'titulo': '',
        'descripcion': '',
        'etiquetas': '',
    }

    if tema_path.exists():
        info['tema'] = tema_path.read_text(encoding='utf-8').strip()[:100]

    if meta_path.exists():
        meta_content = meta_path.read_text(encoding='utf-8')
        partes = meta_content.split('\n---\n')
        info['titulo']     = partes[0].strip() if len(partes) > 0 else ''
        info['descripcion'] = partes[1].strip() if len(partes) > 1 else ''
        info['etiquetas']  = partes[2].strip() if len(partes) > 2 else ''

    return info


class LogRedirector:
    """Redirige stdout/stderr al sistema de logging."""
    def __init__(self):
        self.buffer = ""
        
    def write(self, text):
        if text and text.strip():
            # Agregar cada línea al log
            for line in text.strip().split('\n'):
                if line.strip():
                    add_log(line.strip(), 'info')
        return len(text)
    
    def flush(self):
        pass

def run_pipeline(mode: str, estilo: str):
    """Ejecuta main.py o news_runner.py con captura de logs."""
    import sys
    import io
    
    try:
        # Log inicial
        add_log(f'🚀 Iniciando pipeline en modo: {mode} con estilo: {estilo}', 'info')
        
        # Configurar estilo via variable de entorno
        os.environ['TUBENAUTA_ESTILO'] = estilo
        add_log(f'🎨 Estilo configurado: {estilo}', 'info')
        
        # Guardar stdout/stderr originales
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        # Crear redirector de logs
        log_redirector = LogRedirector()
        
        try:
            # Redirigir stdout/stderr
            sys.stdout = log_redirector
            sys.stderr = log_redirector
            
            if mode == 'temas':
                add_log('📝 Ejecutando main.py...', 'info')
                # Ejecutar main.py directamente
                import main
                import importlib
                importlib.reload(main)  # Recargar para obtener nuevos temas
                main.main()
            else:
                add_log('📰 Ejecutando news_runner.py...', 'info')
                # Ejecutar news_runner.py directamente
                import news_runner
                import importlib
                importlib.reload(news_runner)  # Recargar para obtener nuevas noticias
                news_runner.main()
            
            add_log('✅ Pipeline completado exitosamente', 'success')
            
        finally:
            # SIEMPRE restaurar stdout/stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
    except Exception as e:
        import traceback
        # Restaurar stdout/stderr antes de imprimir error
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        error_msg = f'❌ ERROR: {str(e)}\n{traceback.format_exc()}'
        add_log(error_msg, 'error')
        print(f"ERROR en run_pipeline: {error_msg}", file=sys.stderr)
    
    finally:
        processing_status['running'] = False
        add_log('🔚 Pipeline finalizado', 'info')




if __name__ == '__main__':
    # Crear directorios necesarios
    (BASE_DIR / 'web' / 'templates').mkdir(parents=True, exist_ok=True)
    (BASE_DIR / 'web' / 'static' / 'css').mkdir(parents=True, exist_ok=True)
    (BASE_DIR / 'web' / 'static' / 'js').mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("  TubeNauta V5 - Web Frontend")
    print("=" * 60)
    print(f"  Abriendo en: http://localhost:5000")
    print(f"  ComfyUI: {COMFYUI_URL}")
    print(f"  Gemini API: {'✔ Configurada' if GEMINI_API_KEY else '✗ No configurada'}")
    print("=" * 60)
    
    # Desactivar auto-reload para que no se reinicie durante el procesamiento
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
