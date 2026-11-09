# run.py — Atlas 7.0 Launcher

import subprocess
import sys
import os
import time
import webbrowser
import threading

def run_backend():
    """FastAPI backend start"""
    subprocess.run([sys.executable, "server.py"], cwd=os.path.dirname(__file__))

def run_frontend():
    """React frontend start"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, shell=True)

def open_browser():
    time.sleep(4)
    webbrowser.open("http://localhost:5173")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Atlas 7.0 — Starting...")
    print("=" * 60)
    print("   Backend:  http://localhost:8000")
    print("   Frontend: http://localhost:5173")
    print("   API Docs: http://localhost:8000/docs")
    print("=" * 60)

    # Backend thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    time.sleep(2)

    # Open browser
    threading.Thread(target=open_browser, daemon=True).start()

    # Frontend (main thread)
    run_frontend()
