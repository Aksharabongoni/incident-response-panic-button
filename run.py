"""
Incident Response Panic Button - Local Server Runner
"""
import sys
import os

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("=" * 65)
    print(" [*] INCIDENT RESPONSE PANIC BUTTON SYSTEM STARTED")
    print(f" [*] Web Dashboard: http://{host}:{port}/")
    print(f" [*] Analytics:     http://{host}:{port}/analytics")
    print(f" [*] Audit Trail:   http://{host}:{port}/audit")
    print(f" [*] API Panic:     POST http://{host}:{port}/api/panic")
    print("=" * 65)
    app.run(host=host, port=port, debug=False)

