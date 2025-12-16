from kokoro_onnx import Kokoro
import traceback
import os

print(f"Size of onnx: {os.path.getsize('kokoro-v0_19.onnx')}")
print(f"Size of voices: {os.path.getsize('voices.json')}")

try:
    k = Kokoro("kokoro-v0_19.onnx", "voices.json")
    print("Success!")
except Exception:
    traceback.print_exc()
