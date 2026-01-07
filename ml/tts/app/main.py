from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import tempfile
from pathlib import Path
from . import tts
import re

app = FastAPI(title="TTS Service", version="1.0.0")
templates = Jinja2Templates(directory="app/templates")

def validate_rate(rate: str) -> str:
    """
    Validate and format rate parameter for edge-tts
    Valid formats: +0%, -0%, +10%, -10%, etc.
    """
    rate = rate.strip()
    
    if re.match(r'^[+-]\d+%$', rate):
        return rate
    
    try:
        rate_value = int(rate.replace('%', ''))
        return f"+{rate_value}%" if rate_value >= 0 else f"{rate_value}%"
    except (ValueError, TypeError):
        return "+0%"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main web page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/tts/text")
async def tts_from_text(
    request: Request
):
    """Convert text to speech"""
    data = await request.json()
    text = data.get("text", "").strip()
    voice = data.get("voice", "ru-RU-SvetlanaNeural")
    rate = data.get("rate", "+0%")  
    
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    rate = validate_rate(rate)
    
    try:
        audio_path = await tts.text_to_speech(text, voice, rate)
        
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            filename="speech.mp3",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
        
    except Exception as e:
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.unlink(audio_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts/file")
async def tts_from_file(
    file: UploadFile = File(...),
    voice: str = Query("ru-RU-SvetlanaNeural"),
    rate: str = Query("+0%")  
):
    """Convert uploaded text file to speech"""
    if not file.filename.endswith(('.txt', '.md', '.text')):
        raise HTTPException(status_code=400, detail="Only text files are supported")
    
    rate = validate_rate(rate)
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        audio_path = await tts.file_to_speech(temp_file_path, voice, rate)
        
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            filename=f"{Path(file.filename).stem}_speech.mp3",
            headers={"Content-Disposition": f"attachment; filename={Path(file.filename).stem}_speech.mp3"}
        )
        
    except Exception as e:
        # Cleanup temp files
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.unlink(audio_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voices")
async def list_voices():
    """List available voices"""
    voices = [
        "ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural",
        "en-US-JennyNeural", "en-US-GuyNeural",
        "de-DE-KatjaNeural", "de-DE-ConradNeural",
        "fr-FR-DeniseNeural", "fr-FR-HenriNeural"
    ]
    return {"voices": voices}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "tts-api"}