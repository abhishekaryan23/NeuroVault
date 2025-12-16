import os
from typing import Optional
# from transformers import pipeline # Commented out to avoid immediate heavy load
from app.config import settings
from app.core.prompts import Prompts
from app.core.llm import NeuroVaultLLM

class MultimodalService:
    _captioner = None
    _transcriber = None

    @classmethod
    def get_captioner(cls):
        if cls._captioner is None:
            print("Loading image captioning model (BLIP)...")
            from transformers import pipeline
            cls._captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
        return cls._captioner

    @classmethod
    def get_transcriber(cls):
        if cls._transcriber is None:
            print("Loading audio transcription model (Whisper)...")
            from transformers import pipeline
            cls._transcriber = pipeline("automatic-speech-recognition", model="openai/whisper-tiny.en")
        return cls._transcriber

    @classmethod
    async def process_image(cls, file_path: str) -> str:
        try:
            import ollama
            print(f"Processing image with {settings.IMAGE_MODEL}...")
            
            # Define Schema
            from pydantic import BaseModel
            class ImageAnalysis(BaseModel):
                description: str
                tags: list[str]

            response = await NeuroVaultLLM.chat(
                model=settings.IMAGE_MODEL,
                messages=[{
                    'role': 'user',
                    'content': Prompts.IMAGE_DESCRIPTION_USER,
                    'images': [file_path]
                }],
                format=ImageAnalysis.model_json_schema() # Pass schema for structured output
            )
            
            # Response is now strictly valid JSON matching schema
            import json
            content = response['message']['content']
            data = json.loads(content)
            
            return {
                "description": data.get("description", "No description"),
                "tags": data.get("tags", [])
            }
            
        except Exception as e:
            print(f"Captioning failed: {e}")
            return {
                "description": "Could not generate caption.",
                "tags": []
            }

    @classmethod
    async def process_audio(cls, file_path: str) -> str:
        try:
            transcriber = cls.get_transcriber()
            result = transcriber(file_path)
            # Result is usually {'text': '...'}
            text = result['text']
            return f"[Voice Note]: {text}"
        except Exception as e:
            print(f"Transcription failed: {e}")
            return "[Voice Note]: Could not transcribe audio."
