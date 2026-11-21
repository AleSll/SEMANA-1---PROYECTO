# Cómo publicar SIMTELE-RISK y obtener el enlace

La aplicación es Flask + SQLite. Necesita un hosting que ejecute Python (no sirve GitHub Pages).

## Opción recomendada: PythonAnywhere (gratis, el historial SÍ se conserva)
1. Cree una cuenta en https://www.pythonanywhere.com (plan *Beginner*, gratis).
2. Consola **Bash**: `git clone https://github.com/<usuario>/<repositorio>.git simtele-risk`
3. `cd simtele-risk && python3 -m venv ~/venv && source ~/venv/bin/activate && pip install -r requirements.txt`
4. Pestaña **Web** → *Add a new web app* → *Manual configuration* → misma versión de Python.
5. En **Virtualenv** ponga `/home/<usuario>/venv`. En **WSGI configuration file** reemplace el contenido por:
   ```python
   import sys
   sys.path.insert(0, "/home/<usuario>/simtele-risk")
   from wsgi import app as application
   ```
6. *Reload*. El enlace será `https://<usuario>.pythonanywhere.com`. La base queda en `simtele-risk/data/simtele.db` y persiste.

## Alternativa: Render
Con `render.yaml`/`Procfile` incluidos: *New → Web Service* → conectar el repositorio. En el plan gratuito el disco es efímero
(el historial se borra al reiniciar el servicio); para persistencia agregue un *Disk* y apunte `SIMTELE_DB` a él.

## Verificación
Abra `<enlace>/api/salud` (debe responder `{"ok": true}`), luego ejecute un módulo y revise el **Historial**.
