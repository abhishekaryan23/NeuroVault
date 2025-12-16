import subprocess
import time
import sys
import os
import signal
import platform

# Configuration
BACKEND_DIR = os.path.join(os.getcwd(), "backend")
VOICE_DIR = os.path.join(os.getcwd(), "voice_engine")
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend")
VENV_PYTHON = os.path.join(BACKEND_DIR, ".venv", "bin", "python")

if platform.system() == "Windows":
    VENV_PYTHON = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")

processes = []

def signal_handler(sig, frame):
    print("\n[Unified Launcher] Shutting down services...")
    for p in processes:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def check_port(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def verify_environment():
    print("🔍 Running Pre-flight Checks...")
    checks_passed = True

    # 1. Check Python Venv
    if not os.path.exists(VENV_PYTHON):
        print(f"❌ Python Venv missing: {VENV_PYTHON}")
        print("   -> Run 'python setup_project.py' to fix.")
        checks_passed = False
    else:
        print(f"✅ Python Venv found.")

    # 2. Check Frontend node_modules
    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.exists(node_modules):
        print(f"❌ Frontend dependencies missing: {node_modules}")
        print("   -> Run 'cd frontend && npm install' or 'python setup_project.py'")
        checks_passed = False
    else:
        print(f"✅ Frontend dependencies found.")

    # 3. Check Ports
    for port, name in [(8000, "Backend"), (8001, "Voice Engine"), (5173, "Frontend")]:
        if check_port(port):
            print(f"❌ Port {port} ({name}) is already in use!")
            print(f"   -> Kill the process using it: lsof -t -i :{port} | xargs kill -9")
            checks_passed = False
        else:
            print(f"✅ Port {port} is free.")

    # 4. Check Voice Resources
    if not os.path.exists(os.path.join(VOICE_DIR, "kokoro-v0_19.onnx")):
        print(f"⚠️  Voice Model (ONNX) missing in {VOICE_DIR}")
        print("   -> Run 'python setup_project.py' to download.")
        # Warning only, technically could run STT without TTS
    
    if not checks_passed:
        print("\n❌ Environment checks failed. Please fix the issues above and try again.")
        sys.exit(1)
    
    print("✅ All checks passed.\n")

def main():
    verify_environment()
    print("🚀 Starting NeuroVault Alpha (Unified Mode)...")
    
    # Check Venv
    # This check is now handled by verify_environment()
    # if not os.path.exists(VENV_PYTHON):
    #     print(f"❌ Virtual Environment not found at {VENV_PYTHON}")
    #     print("   Please run 'python setup_project.py' first.")
    #     return

    # 1. Start Voice Engine
    print("🎙️  Starting Voice Engine (Port 8001)...")
    try:
        p_voice = subprocess.Popen(
            [VENV_PYTHON, "server.py"], 
            cwd=VOICE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(p_voice)
    except Exception as e:
        print(f"❌ Failed to start Voice Engine: {e}")

    # 2. Start Backend API
    print("🧠 Starting Main Backend (Port 8000)...")
    try:
        p_backend = subprocess.Popen(
            [VENV_PYTHON, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"], 
            cwd=BACKEND_DIR
        )
        processes.append(p_backend)
    except Exception as e:
        print(f"❌ Failed to start Backend: {e}")

    # 3. Start Frontend
    print("🎨 Starting Frontend (Vite)...")
    try:
        # Check if npm is installed/avail ? Assume yes.
        p_frontend = subprocess.Popen(
            ["npm", "run", "dev"], 
            cwd=FRONTEND_DIR
        )
        processes.append(p_frontend)
    except Exception as e:
        print(f"❌ Failed to start Frontend: {e}")

    print("\n✅ All services launched. Press Ctrl+C to stop.")
    
    # Monitor loop
    while True:
        time.sleep(1)
        # Check if any process died
        if p_voice.poll() is not None:
            print("⚠️  Voice Engine stopped unexpectedly!")
            print(p_voice.stderr.read().decode())
            break
        if p_backend.poll() is not None:
            print("⚠️  Backend stopped unexpectedly!")
            break

if __name__ == "__main__":
    main()
