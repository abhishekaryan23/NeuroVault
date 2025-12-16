# Backend Directory

This directory contains the Python FastAPI application source code and utility scripts.

For a comprehensive guide, see [BACKEND_GUIDE.md](../BACKEND_GUIDE.md).

## Directory Structure
- **`app/`**: Core application logic (API, Services, Models).
- **`db/`**: Database connection and migration logic.
- **`dumps/`**: Storage for uploaded files (PDFs, Images, Audio).

## Scripts
- **`reindex_vectors.py`**: Maintenance script to regenerate all vector embeddings.
- **`debug_search.py`**: Diagnostic script to verify search and vector tables.

## Quick Start
```bash
# Activate virtualenv
source .venv/bin/activate

# Run Server
python -m uvicorn app.main:app --reload

# Run Scripts
python reindex_vectors.py
```
