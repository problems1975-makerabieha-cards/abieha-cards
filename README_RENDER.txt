Render settings:
Build Command: pip install -r requirements.txt
Start Command: gunicorn -w 1 --threads 100 app:app
Make sure Root Directory is empty, not templates or static.
