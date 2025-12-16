from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
import uvicorn
import base64
import soundfile as sf
import io
import numpy as np
import os

# Import Libraries (Validation that imports work)
try:
    from kokoro_onnx import Kokoro
    from faster_whisper import WhisperModel
except ImportError as e:
    print(f"Missing dependency: {e}")
    exit(1)

app = FastAPI(title="Voice Engine (Py3.12)")

# --- Initialize Models ---
print("Loading Kokoro TTS...")
try:
    # Hack: voices.json is a dict, but kokoro-onnx expects an npy file (single voice or pickle?).
    # We will extract 'af_sarah' and save as .npy to feed it.
    import json
    if os.path.exists("voices.json"):
        with open("voices.json", "r") as f:
            voices_data = json.load(f)
        
        # Check available voices
        # print(f"Available voices: {list(voices_data.keys())}")
        
        target_voice = "af_sarah"
        if target_voice not in voices_data and "af" in voices_data:
             target_voice = "af"
        
        if target_voice in voices_data:
            print(f"Extracting voice: {target_voice}")
            voice_arr = np.array(voices_data[target_voice], dtype=np.float32)
            np.save("voice.npy", voice_arr)
            
            kokoro = Kokoro("kokoro-v0_19.onnx", "voice.npy")
            # Monkey-patch: Ensure kokoro.voices is a dict so name lookup works
            kokoro.voices = {target_voice: voice_arr}
            print(f"Kokoro Loaded with single voice: {target_voice}")
        else:
            print("Target voice not found in voices.json")
            kokoro = None
    else:
        print("voices.json not found.")
        kokoro = None

except Exception as e:
    print(f"Failed to load Kokoro: {e}")
    kokoro = None

print("Loading Faster Whisper...")
try:
    # "tiny" or "base" or "small" for speed on CPU/Mac
    # default to "base" which is good balance
    whisper = WhisperModel("base", device="cpu", compute_type="int8") 
    print("Faster Whisper Loaded.")
except Exception as e:
    print(f"Failed to load Whisper: {e}")
    whisper = None


class TTSRequest(BaseModel):
    text: str
    voice: str = "af_sarah" # Default voice

@app.post("/tts")
async def tts(request: TTSRequest):
    if not kokoro:
        raise HTTPException(status_code=500, detail="Kokoro model not loaded")
        
    try:
        # Generate Audio
        # kokoro.create returns (samples, sample_rate)
        samples, sample_rate = kokoro.create(
            request.text, 
            voice=request.voice, 
            speed=1.0, 
            lang="en-us"
        )
        
        # Convert float32 numpy array to WAV bytes
        # soundfile.write expects file path or file-like object
        buffer = io.BytesIO()
        sf.write(buffer, samples, sample_rate, format='WAV')
        buffer.seek(0)
        wav_bytes = buffer.read()
        
        # Return Base64
        b64_audio = base64.b64encode(wav_bytes).decode('utf-8')
        return {"audio": b64_audio}
        
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stt")
async def stt(file: UploadFile = File(...)):
    if not whisper:
        raise HTTPException(status_code=500, detail="Whisper model not loaded")
        
    try:
        # Save temp file because faster-whisper often prefers path or binary stream
        # It accepts binary stream too!
        audio_bytes = await file.read()
        audio_stream = io.BytesIO(audio_bytes)
        
        segments, info = whisper.transcribe(audio_stream, beam_size=5)
        
        text = " ".join([segment.text for segment in segments]).strip()
        return {"text": text}
        
    except Exception as e:
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voices")
def get_voices():
    if kokoro and hasattr(kokoro, 'voices') and isinstance(kokoro.voices, dict):
        return {"voices": list(kokoro.voices.keys())}
    return {"voices": ["default"]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
