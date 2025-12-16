# Open-GDR - End-to-End Setup Guide (macOS)

Welcome to Open-GDR! This guide will help you set up the entire project on your Mac without conflicting with your existing system installations.

## 🚀 Prerequisites

Before running the automated installer, ensure you have the following installed. We recommend using **Homebrew** and **pyenv** (or just Homebrew Python) to manage versions cleanly.

### 1. Install Homebrew (if not installed)
Open your Terminal and run:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Node.js
Required for the Frontend.
```bash
brew install node
```

### 3. Install Python 3.12 (Supported)
This project requires a Python version that supports **loadable SQLite extensions** (for `sqlite-vec`). The default Python 3.14 (experimental) often lacks this on macOS. **Python 3.12 via Homebrew is currently recommended.**

```bash
brew install python@3.12
# OR via pyenv if you configure it with --enable-loadable-sqlite-extensions
```

---

## 🛠️ Installation

We have provided an intelligent automated script `setup_project.py` that handles the complex setup for you.

1.  **Open Terminal** and navigate to the project folder:
    ```bash
    cd Open-GDR_Release_...
    ```

2.  **Run the Setup Script**:
    ```bash
    python3 setup_project.py
    ```

    *What this script does:*
    *   ✅ **Auto-detects** a compatible Python version (prioritizes 3.14 if compliant, falls back to 3.12).
    *   ✅ Checks for `sqlite3` extension support needed for Vector Search.
    *   ✅ Creates isolated Virtual Environments (`.venv`) for backend and voice engine.
    *   ✅ **Sets up directory permissions** for audio/file uploads (`dumps/`).
    *   ✅ Installs all dependencies (including `sqlite-vec`, `ollama`).
    *   ✅ Installs Frontend packages via `npm install`.

---

## ▶️ Running the Application (Alpha)

**One-Click Launch:**
Open one terminal and run:

```bash
python3 run_neurovault.py
```
This will automatically launch the Backend, Voice Engine, and Frontend in parallel.
*   **Web App**: http://localhost:5173
*   **API**: http://localhost:8000/docs
*   **Voice Engine**: http://localhost:8001/docs

(Press `Ctrl+C` to stop all services)

---

### Manual Start (Advanced)

If you prefer separate tabs:
<details>
<summary>Click to expand</summary>

**Terminal 1: Backend**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2: Voice Engine** (Required for TTS/STT)
```bash
cd voice_engine
# Uses same venv as backend if setup correctly, otherwise create one
source ../backend/.venv/bin/activate 
python server.py
```

**Terminal 3: Frontend**
```bash
cd frontend
npm run dev
```
</details>

## 📚 Documentation

- **[API Reference](API_REFERENCE.md)**: Detailed guide to all Backend endpoints.
- **[Backend Guide](BACKEND_GUIDE.md)**: Architecture deep dive.

---

## ❓ Troubleshooting

**"sqlite3.OperationalError: no such module: vec0"**
This means your Python version doesn't support loading the `sqlite-vec` extension. 
*   **Fix**: Run `setup_project.py` again. It should detect this and try to use Python 3.12. Ensure you have `brew install python@3.12`.

**"Permission denied" (Uploads/Audio)**
If you see errors when uploading files or saving voice notes:
*   **Fix**: Run `chmod -R 755 backend/dumps` or simply run `setup_project.py` again (it now fixes permissions automatically).

**"Port 8000/8001 already in use"**
Another process is using these ports. Terminate them with:
```bash
lsof -t -i :8000 -i :8001 | xargs kill -9
```
