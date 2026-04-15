@echo off
echo ============================================================
echo   TubeNauta V5 - Iniciando Frontend Web
echo ============================================================
echo.
echo IMPORTANTE:
echo - Este servidor debe permanecer SIEMPRE corriendo
echo - NO cierres esta ventana
echo - Abre tu navegador en: http://localhost:5000
echo - ComfyUI debe estar corriendo en: http://127.0.0.1:8188
echo.
echo ============================================================
echo.

cd /d "%~dp0"
python app.py

pause
