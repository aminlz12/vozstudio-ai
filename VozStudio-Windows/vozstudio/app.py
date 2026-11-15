from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import subprocess, tempfile, os, sys, uuid

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / 'models'
OUTPUT = ROOT / 'generated'
OUTPUT.mkdir(exist_ok=True)
app = FastAPI(title='VozStudio Local')
app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')

class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=6000)
    voice: str
    speed: float = Field(default=1, ge=0.7, le=1.35)

@app.get('/')
def home():
    return FileResponse(ROOT/'static'/'index.html')

@app.get('/api/voices')
def voices():
    return [{'id':p.stem,'label':p.stem.replace('es_ES-','').replace('-medium',' · ES').replace('-high',' · ES').replace('-low',' · ES')} for p in sorted(MODEL_DIR.glob('*.onnx'))] if MODEL_DIR.exists() else []

@app.post('/api/generate')
def generate(data:Speech):
    allowed = {p.stem:p for p in MODEL_DIR.glob('*.onnx')} if MODEL_DIR.exists() else {}
    if data.voice not in allowed:
        raise HTTPException(400,'No hay un modelo válido. Descarga una voz en la carpeta models.')
    name = uuid.uuid4().hex + '.wav'
    output = OUTPUT/name
    # Piper length_scale > 1 = slower
    cmd = [sys.executable,'-m','piper','--model',str(allowed[data.voice]),'--output_file',str(output),'--length_scale',str(1/data.speed)]
    try:
        proc = subprocess.run(cmd,input=data.text,encoding='utf-8',capture_output=True,timeout=180,cwd=ROOT)
    except subprocess.TimeoutExpired:
        raise HTTPException(504,'La generación tardó demasiado.')
    if proc.returncode or not output.exists():
        raise HTTPException(500,'Error del motor Piper: '+proc.stderr[-700:])
    return {'url':'/api/audio/'+name,'filename':'vozstudio-'+name}

@app.get('/api/audio/{name}')
def audio(name:str):
    if not name.endswith('.wav') or len(name)!=36 or not all(c in '0123456789abcdef' for c in name[:-4]):
        raise HTTPException(404,'Archivo no encontrado')
    path=OUTPUT/name
    if not path.exists():raise HTTPException(404,'Archivo no encontrado')
    return FileResponse(path,media_type='audio/wav',filename='vozstudio-'+name)
