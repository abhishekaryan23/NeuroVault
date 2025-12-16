# Voice Engine Documentation

The **Voice Engine** is a specialized microservice dedicated to heavy audio processing tasks (Text-to-Speech and Speech-to-Text). It runs independently from the main backend to isolate large model dependencies (Kokoro, Whisper) and optimize performance.

## Overview
- **Path**: `voice_engine/`
- **Port**: `8001`
- **Framework**: FastAPI

## Components

### `server.py`
The main entry point.
- Loads **Kokoro** (via `kokoro-onnx`) for TTS.
- Loads **Faster-Whisper** for STT.
- Exposes REST endpoints for the main backend.

### `convert_voices.py` & `voices.json`
Utilities to manage voice profiles for Kokoro. We primarily use the `af_sarah` voice pack, extracted to `voice.npy`.

## Endpoints

### 1. Text-to-Speech (TTS)
- **POST** `/tts`
- **Body**: `{"text": "Hello world", "voice": "af_sarah"}`
- **Returns**: `{"audio": "<base64_encoded_wav_string>"}`

### 2. Speech-to-Text (STT)
- **POST** `/stt`
- **Form Data**: `file` (UploadFile, typically .wav or .webm)
- **Returns**: `{"text": "Transcribed text string..."}`

### 3. Get Voices
- **GET** `/voices`
- **Returns**: List of available loaded voice names.

## Setup & Run

The project includes a helper script `start_voice_engine.sh` in the root.

Manual startup:
```bash
cd voice_engine
# Ensure virtualenv is active and has dependencies (kokoro-onnx, faster-whisper, numpy, soundfile)
python server.py
```
