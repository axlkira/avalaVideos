# TubeNauta V5 - Frontend Web

Interfaz web profesional para gestionar la creación masiva de videos.

## 🚀 Inicio Rápido

### Requisitos Previos
1. **ComfyUI debe estar corriendo** en `http://127.0.0.1:8188`
2. **Gemini API Key** configurada en variable de entorno `GEMINI_API_KEY`

### Pasos para Iniciar

1. **Instalar dependencias web:**
```bash
pip install -r requirements-web.txt
```

2. **Iniciar el servidor Flask (DEBE PERMANECER CORRIENDO):**

**Opción A - Usando el script:**
```bash
start_frontend.bat
```

**Opción B - Manualmente:**
```bash
python app.py
```

3. **Abrir en navegador:**
```
http://localhost:5000
```

## ⚠️ IMPORTANTE

- **Flask (`app.py`)** debe estar **SIEMPRE corriendo** - Es el servidor web del frontend
- **NO cierres** la ventana de Flask mientras uses la aplicación
- **ComfyUI** permanece abierto después de generar videos (no se cierra)
- Cada vez que clickeas "Procesar Temas", Flask ejecuta `main.py` internamente
- Los logs aparecen en tiempo real en la página `/progreso`

## Características

- 🎨 **Interfaz Moderna**: Diseño responsive con Tailwind CSS
- 📊 **Dashboard Intuitivo**: Resumen de estadísticas y estado del sistema
- 🔄 **Progreso en Tiempo Real**: Server-Sent Events (SSE) para logs en vivo
- 📝 **Dos Modos de Creación**:
  - **Temas Cortos**: Videos virales de 40-50s
  - **Noticias Completas**: Videos narrativos desde noticias
- 🖼️ **Galería de Videos**: Visualización y descarga de videos generados
- ⚙️ **Configuración Visual**: Vista de parámetros del sistema

## Instalación

1. **Instalar dependencias web** (además de las existentes):
```bash
pip install -r requirements-web.txt
```

2. **Verificar que ComfyUI esté corriendo**:
```bash
# ComfyUI debe estar en http://127.0.0.1:8188
```

3. **Configurar Gemini API Key** (si no está configurada):
```bash
# Windows
set GEMINI_API_KEY=tu_api_key_aqui

# Linux/Mac
export GEMINI_API_KEY=tu_api_key_aqui
```

## Uso

### Iniciar el servidor web:

```bash
python app.py
```

La aplicación estará disponible en: **http://localhost:5000**

### Flujo de trabajo:

1. **Dashboard** (`/`) - Ver resumen y estado del sistema
2. **Crear Videos**:
   - **Temas** (`/temas`) - Escribe temas cortos, uno por línea
   - **Noticias** (`/noticias`) - Escribe noticias completas separadas por `---`
3. **Procesar** - Click en "Procesar" para iniciar
4. **Progreso** (`/progreso`) - Observa logs en tiempo real
5. **Galería** (`/galeria`) - Descarga videos generados

## Estructura de Archivos

```
avalaVideos/
├── app.py                    # Servidor Flask principal
├── web/
│   ├── templates/            # Templates HTML
│   │   ├── base.html         # Layout base
│   │   ├── dashboard.html    # Página principal
│   │   ├── temas.html        # Editor de temas
│   │   ├── noticias.html     # Editor de noticias
│   │   ├── progreso.html     # Logs en tiempo real
│   │   ├── galeria.html      # Videos generados
│   │   └── config.html       # Configuración
│   └── static/               # Archivos estáticos (vacío, usa Tailwind CDN)
├── requirements-web.txt      # Dependencias web
└── ... (archivos existentes)
```

## API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Dashboard principal |
| `/temas` | GET | Editor de temas cortos |
| `/noticias` | GET | Editor de noticias |
| `/progreso` | GET | Página de progreso |
| `/galeria` | GET | Galería de videos |
| `/config` | GET | Configuración |
| `/api/start` | POST | Iniciar procesamiento |
| `/api/status` | GET | SSE para progreso en tiempo real |
| `/api/download/<path>` | GET | Descargar video |

## Tecnologías

- **Backend**: Flask (Python)
- **Frontend**: Tailwind CSS (vía CDN)
- **Real-time**: Server-Sent Events (SSE)
- **Procesamiento**: Subprocess para ejecutar pipelines

## Notas

- El frontend NO modifica el código original de los pipelines
- Los pipelines se ejecutan como subprocesos independientes
- Los logs se capturan en tiempo real vía stdout
- La configuración se visualiza pero debe editarse manualmente en `config.py`

## Troubleshooting

**ComfyUI offline:**
- Verifica que ComfyUI esté corriendo en http://127.0.0.1:8188
- Revisa el puerto en `config.py` si usas otro

**Gemini API no configurada:**
- Configura la variable de entorno `GEMINI_API_KEY`
- Reinicia el servidor Flask

**Videos no se generan:**
- Revisa los logs en `/progreso`
- Verifica que todos los requisitos estén instalados
- Asegúrate de que Flux esté cargado en ComfyUI

## Soporte

Para más información sobre los pipelines originales, consulta `README.md` en la raíz del proyecto.
