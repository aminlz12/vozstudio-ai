# VozStudio AI

Interfaz pública de texto a voz. El modo navegador reproduce mediante las voces españolas disponibles del dispositivo, sin exportar WAV. Para descargar WAV es necesario un servidor Python con FastAPI, Piper y modelos instalados.

## Publicar interfaz
GitHub → Settings → Pages → Deploy from a branch → main → /(root) → Save.

## Windows con Piper
Instala Python 3.11, coloca los pares ONNX + JSON de voces españolas Piper en `models/`, inicia `INICIAR_WINDOWS.bat` y visita `http://127.0.0.1:8000`.
