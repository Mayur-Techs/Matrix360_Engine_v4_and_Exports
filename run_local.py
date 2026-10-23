"""Matrix 360 & LeadScope AI Studio — Local Single-Command Runner.

Starts both the FastAPI web console and the background qualification worker
together in one process group for easy local execution on Windows, Mac, or Linux.

Usage:
    python run_local.py
    # or with your virtualenv:
    .\\.venv\\Scripts\\python.exe run_local.py
"""
import os
import signal
import subprocess
import sys
import time

def main():
    py = sys.executable
    port = os.getenv("PORT", "8000")
    host = os.getenv("HOST", "127.0.0.1")

    print("=" * 70)
    print(" MATRIX 360 CONSULTING (V5 ENGINE + AUTONOMOUS LEAD SCRAPING & CAMPAIGN STUDIO)")
    print("=" * 70)
    print(f" Starting Web Console at: http://{host}:{port}")
    print(" Default Login:")
    print("   Username: owner")
    print("   Password: change-me-before-sharing")
    print("=" * 70)
    print(" Starting Background Qualification Worker...")

    worker_proc = subprocess.Popen(
        [py, "-m", "services.worker.runner", "--interval", "1"],
        cwd=os.getcwd(),
    )

    print(" Starting FastAPI Web Server...")
    api_proc = subprocess.Popen(
        [py, "-m", "uvicorn", "services.api.app:app", "--host", host, "--port", port],
        cwd=os.getcwd(),
    )

    def shutdown(signum=None, frame=None):
        print("\nStopping Matrix 360 services...")
        for p in (worker_proc, api_proc):
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print("All processes stopped.")
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, shutdown)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, shutdown)
    except Exception:
        pass

    try:
        while True:
            if worker_proc.poll() is not None:
                print(f"[Worker exited with code {worker_proc.returncode}]")
                break
            if api_proc.poll() is not None:
                print(f"[API server exited with code {api_proc.returncode}]")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()

if __name__ == "__main__":
    main()
