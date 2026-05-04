import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
import uuid, random, threading, os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

rooms = {}
COLORS = ["red","blue","green","yellow"]

@app.route("/")
def home():
    return render_template("index.html")

@socketio.on("join")
def join(data):
    room = data["room"]
    name = data["name"]

    if room not in rooms:
        rooms[room] = {"players":[],"turn":0,"started":False,"log":[],"time":10}

    pid = str(uuid.uuid4())
    rooms[room]["players"].append({"id":pid,"name":name})

    join_room(room)
    emit("joined", {"id":pid}, room=request.sid)
    emit("state", rooms[room], room=room)

@socketio.on("start")
def start(data):
    r = rooms[data["room"]]
    r["started"] = True
    r["turn"] = 0
    emit("state", r, room=data["room"])
