# 🚀 How to Install & Run NeuroVault Alpha

Specific instructions for setting up the Alpha Release zip file.

## 1. Prerequisites (macOS)
- **Terminal**: You need to use the Terminal.
- **Python 3.12+**: We recommend installing via Homebrew (`brew install python@3.12`).
- **Node.js**: Required for the frontend (`brew install node`).

## 2. Installation
1.  **Unzip** the `NeuroVault_Alpha.zip` file to a folder of your choice (e.g., `~/Documents/NeuroVault`).
2.  Open **Terminal**.
3.  Navigate to the folder:
    ```bash
    cd ~/Documents/NeuroVault  # (Or your specific path)
    ```
4.  Run the **Auto-Installer**:
    ```bash
    python3 setup_project.py
    ```
    *This will take 2-5 minutes. It creates a virtual environment, installs Python libraries, downloads AI models (Vocie & Embeddings), and installs Frontend packages.*

## 3. Launching
Once setup is complete, run the **Unified Launcher**:

```bash
python3 run_neurovault.py
```

This will automatically start:
- 🧠 **Backend API** (Port 8000)
- 🎙️ **Voice Engine** (Port 8001)
- 🎨 **Web Interface** (Port 5173)

**Access the App:** open [http://localhost:5173](http://localhost:5173) in your browser.

## 4. Troubleshooting
- **"Port already in use"**: The launcher will tell you if ports are blocked. Run the command it suggests to kill old processes.
- **"Python not found"**: Ensure you have Python installed. Try running `brew install python@3.12`.
- **"Permission denied"**: If you can't run scripts, try `chmod +x setup_project.py run_neurovault.py`.

## 5. Stopping
Press `Ctrl+C` in the terminal to stop all services gracefully.
