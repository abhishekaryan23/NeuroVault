import os
import time
import base64
import torch
import sdnq # Critical for patching loading of Z-Image-Turbo-SDNQ
from io import BytesIO
from diffusers import AutoPipelineForText2Image, FlowMatchEulerDiscreteScheduler

# Critical for MPS performance with Z-Image
os.environ["PYTORCH_MPS_FAST_MATH"] = "1"

class ImageGenerationService:
    _pipeline = None

    @classmethod
    def get_pipeline(cls):
        """
        Lazy load the Z-Image Turbo pipeline with Mac Silicon optimizations.
        """
        if cls._pipeline is None:
            print("Loading Z-Image-Turbo Pipeline...")
            
            # Use bfloat16 for MPS (cleaner images than float16, faster than float32)
            dtype = torch.bfloat16 if torch.backends.mps.is_available() else torch.float32
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            
            try:
                pipe = AutoPipelineForText2Image.from_pretrained(
                    "Disty0/Z-Image-Turbo-SDNQ-uint4-svd-r32",
                    trust_remote_code=True,
                    torch_dtype=dtype,
                    low_cpu_mem_usage=True
                )
                
                # Configure Scheduler specifically for Z-Image
                # Reference: use_beta_sigmas=True is critical
                pipe.scheduler = FlowMatchEulerDiscreteScheduler.from_config(
                    pipe.scheduler.config,
                    use_beta_sigmas=True
                )
                
                pipe.to(device)
                
                # Memory Optimizations for 8GB/16GB Macs
                pipe.enable_attention_slicing()
                
                if hasattr(pipe, "enable_vae_slicing"):
                    pipe.enable_vae_slicing()
                    
                if hasattr(getattr(pipe, "vae", None), "enable_tiling"):
                    pipe.vae.enable_tiling()

                print(f"Z-Image Pipeline Loaded on {device}")
                cls._pipeline = pipe
                
            except Exception as e:
                print(f"Failed to load Image Pipeline: {e}")
                raise e
            
        return cls._pipeline

    @classmethod
    async def generate_image(cls, prompt: str, steps: int = 9, width: int = 1024, height: int = 1024, seed: int = None, guidance_scale: float = 0.0):
        """
        Generate an image from prompt.
        """
        start_time = time.time()
        
        try:
            pipe = cls.get_pipeline()
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            
            # Seed handling
            if seed is None:
                seed = int(time.time())
            
            # Generator must match device
            generator = torch.Generator(device).manual_seed(seed)
            
            # Inference
            # guidance_scale=0.0 is typical for Turbo/Lightning models, 
            # though some use 1.0. Reference repo uses 0.0.
            result = pipe(
                prompt=prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale, 
                width=width,
                height=height,
                generator=generator
            )
            
            image = result.images[0]
            
            # Convert to Base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            duration = time.time() - start_time
            
            return {
                "image": img_str,
                "generation_time": round(duration, 2),
                "seed": seed,
                "device": device
            }
            
        except Exception as e:
            print(f"Image Generation Error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
