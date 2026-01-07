import edge_tts
import tempfile
import os

async def text_to_speech(text: str, voice: str = "ru-RU-DmitryNeural", rate: str = "+0%") -> str:
    """Convert text to speech and return path to audio file"""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate
    )
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        await communicate.save(temp_path)
        return temp_path
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise RuntimeError(f"TTS generation failed: {str(e)}")

async def file_to_speech(file_path: str, voice: str = "ru-RU-DmitryNeural", rate: str = "+0%") -> str:
    """Read text file and convert to speech"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return await text_to_speech(text, voice, rate)
    except Exception as e:
        raise RuntimeError(f"File processing failed: {str(e)}")