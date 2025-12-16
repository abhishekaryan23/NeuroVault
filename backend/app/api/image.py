from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.image_generation_service import ImageGenerationService

router = APIRouter()

class ImageGenerationRequest(BaseModel):
    prompt: str
    steps: int = 9
    width: int = 1024
    height: int = 1024
    guidance_scale: float = 0.0
    seed: int | None = None

@router.post("/generate")
async def generate_image(request: ImageGenerationRequest):
    try:
        if not request.prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
            
        result = await ImageGenerationService.generate_image(
            prompt=request.prompt,
            steps=request.steps,
            width=request.width,
            height=request.height,
            guidance_scale=request.guidance_scale,
            seed=request.seed
        )
        
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
             
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
