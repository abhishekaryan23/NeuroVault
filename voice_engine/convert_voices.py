import json
import numpy as np
import os

print("Loading voices.json...")
with open("voices.json", "r") as f:
    data = json.load(f)

print("Converting to numpy...")
# It seems data is a dict or list?
# voices.json from release is normally a JSON object mapping name -> embedding
# BUT headers showed [[...]]?
# Let's check type.

if isinstance(data, dict):
    print("Detected Dictionary format.")
    # If library expects np.load() to return a dictionary-like object (allow_pickle=True needed usually) or struct array?
    # Wait, np.load on a file usually returns an array or NpzFile.
    # If the library expects `self.voices` to be an array, this is confusing.
    pass
elif isinstance(data, list):
    print("Detected List format.")
    arr = np.array(data, dtype=np.float32)
    np.save("voices.npy", arr)
    print("Saved voices.npy")
else:
    print(f"Unknown type: {type(data)}")

# However, if kokoro-onnx source code does `np.load(path)`, it expects a .npy file.
# If I provide a .npy file, `np.load` works.
# But what DOES it expect inside?
# If it expects a dictionary of voices?
# Newer kokoro-onnx might use a simplified voices.bin or .npy which is just a big array?
# Let's try to save what we have as .npy and see if passing "voices.npy" works.
