UNO أبيها - النسخة النهائية

Build:
pip install -r requirements.txt

Start:
gunicorn --worker-class eventlet -w 1 app:app
