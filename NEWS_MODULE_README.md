# 🗞️ Módulo de Noticias Verificadas - TubeNauta V5

## 📋 Descripción
Este módulo permite crear videos de noticias/historias verificando la información en internet antes de generar el contenido. Funciona como un sistema **COMPLETAMENTE INDEPENDIENTE** del TubeNauta V5 original - no modifica ni interfiere con tu configuración actual.

## ✨ Características Principales

1. **Verificación en Internet**: Busca y verifica información usando Google Search API + Gemini
2. **Guión Estructurado**: Genera guiones optimizados para retención en Shorts/TikTok
3. **Fidelidad de Personajes**: Asegura que deportistas, cantantes y figuras históricas sean reconocibles
4. **Pasos Automatizados**: Genera audio TTS, subtítulos y prompts de imágenes automáticamente

## 🚀 Cómo Usar

### Opción 1: Ejecutar directamente (Recomendado)
```bash
python news_runner.py
```

### Opción 2: Desde cualquier ubicación
```bash
python "E:\TubeNauta V4 Pack_1\TubeNauta V5 - Masivo IMG\news_runner.py"
```

### Opción 3: Importar como módulo
```python
from news_module import NewsVideoPipeline

pipeline = NewsVideoPipeline()
result = pipeline.process_news(
    user_input="Ronaldinho, la magia del futbol",
    target_duration=60,
    estilo=ESTILO_ADDICTIVO
)
```

## ⚙️ Configuración Opcional (Para Verificación)

Si quieres que el sistema verifique noticias en internet, configura estas variables de entorno:

```bash
# Windows PowerShell
$env:GOOGLE_SEARCH_API_KEY = "tu_api_key_aqui"
$env:GOOGLE_SEARCH_ENGINE_ID = "tu_search_engine_id_aqui"

# O en archivo .env
GOOGLE_SEARCH_API_KEY=tu_api_key_aqui
GOOGLE_SEARCH_ENGINE_ID=tu_search_engine_id_aqui
```

**Obtener claves:**
1. Ve a: https://developers.google.com/custom-search/v1/overview
2. Crea un proyecto y obtén API Key
3. Configura un Custom Search Engine
4. Copia el Search Engine ID

> ⚠️ **Sin estas claves, el sistema funciona igual** - solo usa la información que proporciones sin verificación externa.

## 📝 Flujo de Trabajo

1. **Ejecutas**: `python news_runner.py`
2. **Ingresas**: La noticia o historia que quieres convertir
3. **Verificación**: El sistema busca información en internet (si tienes API configurada)
4. **Guión**: Genera un guión estructurado con enganche, desarrollo y cierre
5. **Audio**: Crea el audio TTS automáticamente
6. **Subtítulos**: Genera archivo .srt sincronizado
7. **Imágenes**: Crea prompts optimizados para cada escena (con fidelidad de personajes)
8. **Render**: Tú generas las imágenes en ComfyUI y ensamblas el video

## 🎨 Estilos Disponibles

Al ejecutar, puedes elegir entre:
1. **Addictivo** (recomendado para noticias virales)
2. **Cine Épico** (para historias impactantes)
3. **Estilo base del sistema**

### Estilos de Fidelidad para Personajes

Para asegurar que los personajes se vean como el original:

```python
from estilos_imagen import (
    ESTILO_FIDELIDAD_DEPORTISTA,    # Para atletas
    ESTILO_FIDELIDAD_CANTANTE,      # Para músicos
    ESTILO_FIDELIDAD_HISTORICA,     # Para figuras históricas
    ESTILO_FIDELIDAD_CARICATURA,    # Estilo caricatura pero reconocible
    ESTILO_FIDELIDAD_2D_ANIMADO,    # Animación 2D fiel
    ESTILO_FIDELIDAD_CINE_HISTORICO # Estilo biopic realista
)
```

## 📁 Estructura de Salida

Los videos de noticias se guardan en: `output/news_videos/`

Cada video tiene su propia carpeta con:
- `1. Guion.json` - Guión estructurado completo
- `2. Guion.txt` - Texto para narración
- `3. Audio_TTS.mp3` - Audio generado
- `4. Subtitulos.srt` - Subtítulos sincronizados
- `imagenes/` - Prompts para cada escena

## 👤 Fidelidad de Personajes

El sistema detecta automáticamente personajes conocidos y añade instrucciones específicas:

- **Ronaldinho**: Sonrisa característica, pelo rizado con banda, dientes prominentes
- **Messi**: Barba corta, pelo castaño, mirada intensa, camiseta #10
- **Willy Colón**: Bigote, pelo rizado, trombón, estilo salsa 70s
- **Simón Bolívar**: Uniforme blanco militar, pelo largo ondulado
- **Che Guevara**: Boina negra con estrella, mirada revolucionaria
- Y más...

## 🔗 Integración con TubeNauta V5 Original

Este módulo **NO modifica** ningún archivo de tu TubeNauta V5. Puedes seguir usando:
- `main.py` para videos normales
- `news_runner.py` para noticias verificadas

Ambos funcionan independientemente.

## 💡 Ejemplos de Uso

```
📝 Ingresa la noticia o historia:
> El último clásico entre Barcelona y Real Madrid donde Ronaldinho
> hizo magia en el campo

⚙️ Configuración:
Duración [60]: 90
Estilo [1]: 1 (Addictivo)

✅ Resultado: Guion verificado + Audio + Subtítulos + Prompts de imágenes
```

## 🆘 Solución de Problemas

**Error: "No module named 'news_module'"**
- Asegúrate de estar en la carpeta: `E:\TubeNauta V4 Pack_1\TubeNauta V5 - Masivo IMG`
- Ejecuta: `python news_runner.py`

**No encuentra información en internet**
- Configura GOOGLE_SEARCH_API_KEY y GOOGLE_SEARCH_ENGINE_ID
- O procede sin verificación (funciona igual con tu input)

**Las imágenes no se parecen al personaje**
- Usa los estilos `fidelidad_*` de `estilos_imagen.py`
- El módulo añade automáticamente rasgos distintivos detectados

---

**Creado como módulo independiente para TubeNauta V5**
**No afecta el sistema original**
