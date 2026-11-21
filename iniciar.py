"""Inicia SIMTELE-RISK en su computadora:

    python iniciar.py          (en Windows también: py iniciar.py)

Abre http://127.0.0.1:5000/ . El historial se guarda en el archivo simtele.db de esta carpeta.
"""
import os
import sys
import threading
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

faltan = []
for modulo in ("numpy", "flask"):
    try:
        __import__(modulo)
    except ImportError:
        faltan.append(modulo)
if faltan:
    print("Faltan paquetes de Python:", ", ".join(faltan))
    print(f"Instálelos con:\n    {Path(sys.executable).name} -m pip install -r requirements.txt")
    sys.exit(1)

from backend.app import crear_app  # noqa: E402

puerto = int(os.environ.get("PORT", 5000))
url = f"http://127.0.0.1:{puerto}/"
app = crear_app(str(RAIZ / "simtele.db"))
print(f"SIMTELE-RISK en {url}  (Ctrl+C para detener)")
threading.Timer(1.2, lambda: webbrowser.open(url)).start()
try:
    app.run(host="127.0.0.1", port=puerto)
except OSError:
    print(f"El puerto {puerto} está ocupado. Cierre el otro programa o use otro puerto:  set PORT=5001  (Windows)  /  PORT=5001 python iniciar.py")
    sys.exit(1)
