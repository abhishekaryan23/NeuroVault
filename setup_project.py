import os
import sys
import subprocess
import platform
import time
import shutil
import urllib.request
from pathlib import Path

# --- Configuration ---
PROJECT_NAME = "NeuroVault"
BACKEND_DIR = Path("backend").resolve()
VOICE_DIR = Path("voice_engine").resolve()
FRONTEND_DIR = Path("frontend").resolve()
MODELS = {
    "ollama": ["gemma3:4b", "embeddinggemma"],
    "voice": {
        "kokoro-v0_19.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx",
        "voices.json": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.json"
    },
    "huggingface": [
        "Disty0/Z-Image-Turbo-SDNQ-uint4-svd-r32"
    ]
}

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(msg):
    print(f"\n{Colors.HEADER}>>> {msg}{Colors.ENDC}")

def print_ok(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_err(msg):
    print(f"{Colors.FAIL}✖ {msg}{Colors.ENDC}")

def run_command(cmd, cwd=None, check=True, shell=True, env=None, capture=True):
    try:
        if env:
            # Merge with current env
            current_env = os.environ.copy()
            current_env.update(env)
        else:
            current_env = None
        
        if capture:
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                check=check, 
                shell=shell, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                env=current_env
            )
            return result.stdout.strip()
        else:
            # Stream output to console
            subprocess.run(
                cmd, 
                cwd=cwd, 
                check=check, 
                shell=shell, 
                env=current_env
            )
            return None

    except subprocess.CalledProcessError as e:
        if capture:
            print_err(f"Command failed: {cmd}")
            print(f"Error output: {e.stderr}")
        else:
            print_err(f"Command failed: {cmd}")
            # Output already printed to console
        if check:
            sys.exit(1)
        return None

def check_prerequisites():
    print_step("Checking Prerequisites")
    
    # 1. OS Check
    if platform.system() != "Darwin":
        print_err("This script is designed for macOS.")
        # Continue anyway? No, strictly requested for Mac.
        sys.exit(1)
    print_ok("macOS detected")

    # 2. Brew Check
    if not shutil.which("brew"):
        print_err("Homebrew not found.")
        print("Please install Homebrew first: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        sys.exit(1)
    print_ok("Homebrew installed")

    # 3. Node.js Check
    if not shutil.which("node"):
        print(f"{Colors.WARNING}Node.js not found. Installing via brew...{Colors.ENDC}")
        run_command("brew install node")
    else:
        print_ok(f"Node.js installed ({run_command('node -v', check=False)})")


    # 4. Python Check (Target 3.12 for sqlite-vec support)
    python_cmd = "python3"
    # Try to find python3.12 explicitly
    if shutil.which("python3.12"):
        python_cmd = "python3.12"
        print_ok(f"Found Python 3.12 ({python_cmd})")
    else:
        print(f"{Colors.WARNING}Python 3.12 not found (recommended for sqlite-vec). Checking 'python3'...{Colors.ENDC}")
        # Check version of python3
        try:
            ver = run_command("python3 --version", check=False) # Python 3.x.x
            # Very rough check
            if "3.12" not in ver:
                 print(f"{Colors.WARNING}Current python3 is {ver}. Installing python@3.12 via brew for best compatibility...{Colors.ENDC}")
                 run_command("brew install python@3.12", check=False)
                 if shutil.which("python3.12"):
                     python_cmd = "python3.12"
                     print_ok("Installed and using Python 3.12")
                 else:
                     print(f"{Colors.FAIL}Failed to install Python 3.12. Proceeding with system python (might fail on sqlite extensions).{Colors.ENDC}")
            else:
                print_ok(f"System python is 3.12")
        except:
            pass
    
    # Store the python command for venv creation
    os.environ["TARGET_PYTHON"] = python_cmd

    # 5. Ollama Check
    if not shutil.which("ollama"):
        print(f"{Colors.WARNING}Ollama not found. Installing via brew...{Colors.ENDC}")
        run_command("brew install ollama")
    else:
        print_ok("Ollama installed")

def setup_ollama():
    print_step("Setting up AI Models (Ollama)")
    
    # Check if service is running
    try:
        run_command("curl http://localhost:11434/api/tags", check=True)
        print_ok("Ollama service is running")
    except:
        print(f"{Colors.WARNING}Ollama service not responding. Starting service...{Colors.ENDC}")
        # Try brew services first
        run_command("brew services start ollama", check=False)
        # Wait a bit
        print("Waiting for Ollama to start (10s)...")
        time.sleep(10)
    
    # Check Models
    installed_models = run_command("ollama list", check=False) or ""
    
    for model in MODELS["ollama"]:
        if model not in installed_models:
            print(f"Pulling model: {model}...")
            # Let it print to stdout
            subprocess.run(f"ollama pull {model}", shell=True, check=True)
            print_ok(f"Pulled {model}")
        else:
            print_ok(f"Model {model} already exists")

def fix_permissions():
    print_step("Fixing Permissions")
    # Ensure dumps dir exists with write access
    dumps_path = BACKEND_DIR / "dumps"
    if not dumps_path.exists():
        os.makedirs(dumps_path)
    
    print("Applying chmod 755 to backend/dumps...")
    run_command(f"chmod -R 755 {dumps_path}")
    print_ok("Permissions applied")

def preload_huggingface_models():
    print_step("Preloading Hugging Face Models")
    
    venv_path = BACKEND_DIR / ".venv"
    python_cmd = venv_path / "bin" / "python"
    
    if not python_cmd.exists():
        print_err("Backend venv not found. Cannot download models.")
        return

    hf_models = MODELS.get("huggingface", [])
    if not hf_models:
        return

    script_content = """
import sys
from huggingface_hub import snapshot_download

models = {models_list}

for model in models:
    print(f"Downloading snapshot for: {{model}}")
    try:
        snapshot_download(repo_id=model)
        print(f"Successfully downloaded {{model}}")
    except Exception as e:
        print(f"Failed to download {{model}}: {{e}}")
        sys.exit(1)
""".format(models_list=hf_models)

    temp_script = BACKEND_DIR / "download_models_temp.py"
    with open(temp_script, "w") as f:
        f.write(script_content)
        
    try:
        print(f"Downloading {len(hf_models)} models (this may take a while)...")
        # Run in backend dir so it uses the venv environment variables if any (though we invoke venv python directly)
        run_command(f'"{python_cmd}" download_models_temp.py', cwd=BACKEND_DIR, capture=False)
        print_ok("All Hugging Face models preloaded")
    except Exception as e:
        print_err(f"Model download failed: {e}")
    finally:
        if temp_script.exists():
            os.remove(temp_script)


def setup_backend():
    print_step("Setting up Backend")
    
    if not BACKEND_DIR.exists():
        print_err("backend directory not found!")
        sys.exit(1)

    # 1. Create .env
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        print("Creating backend/.env...")
        with open(env_path, "w") as f:
            f.write(f'PROJECT_NAME="{PROJECT_NAME}"\n')
            f.write('DATABASE_URL="sqlite+aiosqlite:///./neurovault.db"\n')
            f.write('UPLOAD_DIR="dumps"\n')
            f.write('EMBEDDING_MODEL="embeddinggemma"\n')
            f.write('SUMMARY_MODEL="gemma3:4b"\n')
            f.write('IMAGE_MODEL="gemma3:4b"\n')
            f.write('AUDITOR_MODEL="gemma3:4b"\n')
            f.write('MESSENGER_MODEL="gemma3:4b"\n')
            f.write('LLM_PROVIDER="ollama"\n')
            f.write('LLM_API_BASE="http://localhost:11434"\n')
        print_ok("Created .env")
    
    # 2. Create Venv
    venv_path = BACKEND_DIR / ".venv"
    target_python = os.environ.get("TARGET_PYTHON", "python3")
    
    if not venv_path.exists():
        print(f"Creating venv using {target_python}...")
        run_command(f'"{target_python}" -m venv "{venv_path}"')
    
    # 3. Install Requirements
    pip_cmd = venv_path / "bin" / "pip"
    if not pip_cmd.exists():
        print_err(f"pip not found at {pip_cmd}")
        sys.exit(1)

    print("Installing requirements...")
    run_command(f'"{pip_cmd}" install -r requirements.txt', cwd=BACKEND_DIR, capture=False)
    
    # 4. Initialize DB
    print("Initializing Database...")
    init_script = """
import asyncio
import sys
import os
sys.path.append(os.getcwd())
try:
    from db.database import init_db, engine
    asyncio.run(init_db())
    asyncio.run(engine.dispose())
    print("DB Init Success")
    sys.exit(0)
except Exception as e:
    print(f"DB Init Failed: {e}")
    sys.exit(1)
"""
    python_cmd = venv_path / "bin" / "python"
    # Write temp script
    with open(BACKEND_DIR / "init_db_temp.py", "w") as f:
        f.write(init_script)
    
    try:
        run_command(f'"{python_cmd}" init_db_temp.py', cwd=BACKEND_DIR, capture=False)
        print_ok("Database Initialized")
    finally:
        if (BACKEND_DIR / "init_db_temp.py").exists():
            os.remove(BACKEND_DIR / "init_db_temp.py")
            
    # 5. Fix Permissions immediately after creating potential folders
    fix_permissions()

    # 6. Preload Hugging Face Models (after requirements installed)
    preload_huggingface_models()

def verify_installation():
    print_step("Verifying Core Dependencies")
    venv_path = BACKEND_DIR / ".venv"
    python_cmd = venv_path / "bin" / "python"
    
    if not python_cmd.exists():
        print_err("Backend venv not found! Setup failed.")
        sys.exit(1)

    verification_script = """
import sys
try:
    print("Checking pypdf...", end="")
    import pypdf
    print(" OK")
    
    print("Checking sqlite_vec...", end="")
    import sqlite_vec
    print(" OK")
    
    print("Checking ollama...", end="")
    import ollama
    print(" OK")
    
except ImportError as e:
    print(f" FAIL: {e}")
    sys.exit(1)
except Exception as e:
    print(f" ERROR: {e}")
    sys.exit(1)
"""
    temp_script = BACKEND_DIR / "verify_deps.py"
    with open(temp_script, "w") as f:
        f.write(verification_script)
        
    try:
        run_command(f'"{python_cmd}" verify_deps.py', cwd=BACKEND_DIR, capture=False)
        print_ok("All core dependencies verified successfully.")
    except:
        print_err("Dependency verification failed. Please check the error output above.")
        print_err("Try running 'pip install -r requirements.txt' manually in backend/.venv")
        sys.exit(1)
    finally:
        if temp_script.exists():
            os.remove(temp_script)

def setup_voice_engine():
    print_step("Setting up Voice Engine")
    
    if not VOICE_DIR.exists():
        print_err("voice_engine directory not found!")
        sys.exit(1)

    # 1. Create Venv
    venv_path = VOICE_DIR / ".venv"
    target_python = os.environ.get("TARGET_PYTHON", "python3")
    
    if not venv_path.exists():
        print(f"Creating venv using {target_python}...")
        run_command(f'"{target_python}" -m venv "{venv_path}"')
    
    # 2. Install Requirements
    pip_cmd = venv_path / "bin" / "pip"
    if not pip_cmd.exists():
        print_err(f"pip not found at {pip_cmd}")
        sys.exit(1)

    print("Installing requirements...")
    run_command(f'"{pip_cmd}" install -r requirements.txt', cwd=VOICE_DIR, capture=False)
    
    # 3. Download Models
    for filename, url in MODELS["voice"].items():
        file_path = VOICE_DIR / filename
        if not file_path.exists():
            print(f"Downloading {filename}...")
            try:
                # Use urllib for zero-dep download
                urllib.request.urlretrieve(url, file_path)
                print_ok(f"Downloaded {filename}")
            except Exception as e:
                print_err(f"Failed to download {filename}: {e}")
                # Try curl fallback
                run_command(f"curl -L -o {filename} {url}", cwd=VOICE_DIR)
        else:
            print_ok(f"Found {filename}")

def setup_frontend():
    print_step("Setting up Frontend")
    
    if not FRONTEND_DIR.exists():
        print_err("frontend directory not found!")
        sys.exit(1)
        
    # 1. Install Dependencies
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Running npm install...")
        run_command("npm install", cwd=FRONTEND_DIR, capture=False)
    
    # 2. Build
    print("Running npm run build...")
    run_command("npm run build", cwd=FRONTEND_DIR, capture=False)
    print_ok("Frontend built")

def create_launcher():
    print_step("Creating Launcher Script")
    
    launcher_content = """#!/bin/bash

# Cleanup function
cleanup() {
    echo "Stopping services..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting NeuroVault..."

# Start Voice Engine
echo "Starting Voice Engine on port 8001..."
cd voice_engine
source .venv/bin/activate
python server.py &
VOICE_PID=$!
cd ..

# Wait a bit
sleep 2

# Start Backend
echo "Starting Backend on port 8000..."
cd backend
source .venv/bin/activate
# Run with reload for dev, or without for prod? Let's use reload for now as per user habits
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Start Frontend (Dev Mode for now, or serve build?)
# User usually runs 'npm run dev'. Let's stick to that for 'start_app.sh'
# If we wanted to serve built files, we'd need a static file server or have FastAPI serve them.
# Given 'setup_project.py' builds it, maybe we assume user might want to serve it? 
# But 'npm run dev' is safer for local interaction usually.
# Let's use npm run dev.
echo "Starting Frontend..."
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

wait
"""
    with open("start_app.sh", "w") as f:
        f.write(launcher_content)
    
    run_command("chmod +x start_app.sh")
    print_ok("Created start_app.sh")

def run_tests():
    print_step("Running Tests")
    try:
        venv_path = BACKEND_DIR / ".venv"
        python_cmd = venv_path / "bin" / "python"
        
        if not python_cmd.exists():
            print_err("Backend venv not found. Cannot run tests.")
            return

        print("Running backend tests with pytest...")
        # Use PYTHONPATH=. to ensure imports work from backend root
        cmd = f'PYTHONPATH=. "{python_cmd}" -m pytest tests'
        run_command(cmd, cwd=BACKEND_DIR, capture=False)
        print_ok("Tests Completed")
    except Exception as e:
        print_err(f"Test run failed: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="NeuroVault Setup & Management")
    parser.add_argument("--reset", action="store_true", help="Wipe database and dumps for a fresh start")
    parser.add_argument("--test", action="store_true", help="Run backend tests")
    args = parser.parse_args()

    print(f"{Colors.BOLD}NeuroVault Automated Manager{Colors.ENDC}")
    print("=" * 30)
    
    if args.reset:
        print(f"{Colors.WARNING}!!! WARNING: RESET MODE !!!{Colors.ENDC}")
        print("This will DELETE 'neurovault.db' and all 'dumps/audio'.")
        print("Press Ctrl+C within 5 seconds to cancel...")
        time.sleep(5)
        
        # Delete DB
        db_path = BACKEND_DIR / "neurovault.db"
        if db_path.exists():
            os.remove(db_path)
            print_ok("Deleted neurovault.db")
        
        # Clean Audio Dumps
        audio_dump = BACKEND_DIR / "dumps" / "audio"
        if audio_dump.exists():
            shutil.rmtree(audio_dump)
            print_ok("Cleaned dumps/audio")
            
        print_step("Reset Complete. Re-initializing...")

    if args.test:
        run_tests()
        sys.exit(0)

    check_prerequisites()
    setup_ollama()
    setup_backend()
    verify_installation()
    setup_voice_engine()
    setup_frontend()
    create_launcher()
    
    print("\n" + "=" * 30)
    print(f"{Colors.OKGREEN}Setup Complete!{Colors.ENDC}")
    print(f"Run {Colors.BOLD}./start_app.sh{Colors.ENDC} to start the application.")
    print(f"Run {Colors.BOLD}python3 setup_project.py --reset{Colors.ENDC} to reset DB.")

if __name__ == "__main__":
    main()
