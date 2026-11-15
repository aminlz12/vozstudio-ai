from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import subprocess, sys, uuid, shutil, wave, threading

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

CLONE_LOCK = threading.Lock()
@app.post('/api/clone')
def clone(text: str = Form(..., min_length=1, max_length=6000), reference: UploadFile = File(...)):
    if not reference.filename or not reference.filename.lower().endswith('.wav'):
        raise HTTPException(400, 'Necesitas una referencia WAV.')
    key = uuid.uuid4().hex
    sample = OUTPUT / (key + '-reference.wav')
    target = OUTPUT / (key + '.wav')
    try:
        with sample.open('wb') as f:
            shutil.copyfileobj(reference.file, f)
        if sample.stat().st_size > 12_000_000:
            raise HTTPException(413, 'Máximo 12 MB.')
        try:
            with wave.open(str(sample)) as wav:
                if wav.getframerate() < 16000 or wav.getnframes() == 0:
                    raise ValueError('WAV vacío o frecuencia baja')
        except (wave.Error, ValueError):
            raise HTTPException(400, 'Se necesita WAV PCM de al menos 16 kHz.')
        try:
            from TTS.api import TTS
            import torch
        except ImportError:
            raise HTTPException(503, 'Instala requirements-clone.txt primero.')
        with CLONE_LOCK:
            try:
                engine = getattr(app.state, 'xtts_engine', None)
                if engine is None:
                    engine = TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=torch.cuda.is_available())
                    app.state.xtts_engine = engine
                engine.tts_to_file(text=text, speaker_wav=str(sample), language='es', file_path=str(target))
            except Exception as exc:
                raise HTTPException(500, 'Error XTTS: ' + str(exc)[:300])
        return {'url':'/api/audio/'+target.name, 'filename':'vozstudio-clon-'+target.name}
    finally:
        sample.unlink(missing_ok=True)
