# ByteLearn Backend

This is the **backend** of ByteLearn.  
It powers the app using **Python (FastAPI)**.

## Current Status
- Basic setup with `main.py` is ready.
- Provides a simple health check API at `/`.

## How to Run
1. Clone this repo  
git clone <backend-repo-link>
2. Install dependencies  
pip install fastapi uvicorn
3. Start the server  
uvicorn main:app --reload
4. Open http://127.0.0.1:8000 in your browser.
