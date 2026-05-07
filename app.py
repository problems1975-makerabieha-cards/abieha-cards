from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, join_room, emit
import random
import uuid
import os
import threading

app = Flask(__name__)
app.config["SECRET_KEY"] = "abieha-final-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}

COLORS = ["red","bluec","greenc","yellow"]

@app.route("/")
def index():
    return send_file("templates/index.html")

# ===============================
# أدوات أساسية
# ===============================

def find_player(room, player_id):
    if room not in rooms:
        return -1
    for i,p in enumerate(rooms[room]["players"]):
        if p["id"] == player_id:
            return i
    return -1

def send_state(room):
    if room not in rooms:
        return

    r = rooms[room]

    base_payload = {
        "room": room,
        "started": r.get("started", False),
        "turn": r.get("turn", 0),
        "direction": r.get("direction", 1),
        "color": r.get("color"),
        "mode": r.get("mode", "solo"),
        "teamMode": r.get("teamMode", "auto"),
        "teamCount": r.get("teamCount", 2),
        "pendingDraw4": r.get("pendingDraw4", 0),
        "pendingDraw2": r.get("pendingDraw2", 0),
        "top": r["discard"][-1] if r.get("discard") else None,
        "deckCount": len(r.get("deck", [])),
        "timeLeft": r.get("timeLeft", 0),
        "timeLimit": r.get("timeLimit", 30),
        "scoreLimit": r.get("scoreLimit", 500),
        "gameOver": r.get("gameOver", False),
        "finalResults": r.get("finalResults"),
        "host": r.get("host"),
        "hostId": r.get("host"),
        "players": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "team": p.get("team"),
                "avatar": p.get("avatar", "auto"),
                "count": len(p.get("hand", [])),
                "last": p.get("last", False),
                "wins": p.get("wins", 0),
                "score": p.get("score", 0),
                "seat": p.get("seat", 0),
            }
            for p in r.get("players", [])
        ],
        "spectators": [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "avatar": s.get("avatar", "🎭"),
            }
            for s in r.get("spectators", [])
        ],
        "log": r.get("log", [])[-80:],
    }

    # إرسال للاعبين
    for p in r.get("players", []):
        payload = dict(base_payload)
        payload["myId"] = p.get("id")
        payload["myHand"] = p.get("hand", [])
        payload["role"] = "player"
        socketio.emit("state", payload, room=p.get("sid"))

    # إرسال للمشاهدين
    for s in r.get("spectators", []):
        payload = dict(base_payload)
        payload["myId"] = s.get("id")
        payload["myHand"] = []
        payload["role"] = "spectator"
        socketio.emit("state", payload, room=s.get("sid"))
# ===============================
# دخول
# ===============================

@socketio.on("join")
def on_join(data):

    room = data.get("room","ROOM1").upper()
    name = data.get("name","لاعب")
    avatar = data.get("avatar","auto")

    role = data.get("role","player")
    seat = int(data.get("seat",0))

    if room not in rooms:
        rooms[room] = {
            "players": [],
            "spectators": [],
            "log": [],
            "host": None
        }

    r = rooms[room]

    join_room(room)

    if role == "spectator":
        r["spectators"].append({
            "id": request.sid,
            "sid": request.sid,
            "name": name,
            "avatar": avatar
        })

        r["log"].insert(0, f"{name} دخل كمشاهد 👀")

    else:
        if any(p.get("seat") == seat for p in r["players"]):
            emit("error_msg", "المقعد محجوز")
            return

        r["players"].append({
            "id": request.sid,
            "sid": request.sid,
            "name": name,
            "avatar": avatar,
            "seat": seat,
            "hand": []
        })

        if r["host"] is None:
            r["host"] = request.sid

        r["log"].insert(0, f"{name} جلس على المقعد {seat+1}")

    emit("joined", {"playerId": request.sid, "room": room})
    send_state(room)

# ===============================
# الشات
# ===============================

@socketio.on("chat")
def on_chat(data):
    room = data.get("room")
    player_id = data.get("playerId")
    text = data.get("text","")

    if room not in rooms or not text:
        return

    r = rooms[room]

    # لاعب
    idx = find_player(room, player_id)
    if idx >= 0:
        p = r["players"][idx]
    else:
        # مشاهد
        p = next((s for s in r["spectators"] if s["id"] == player_id), None)
        if not p:
            return

    r["log"].append({
        "type":"chat",
        "id":player_id,
        "name":p["name"],
        "avatar":p.get("avatar","💬"),
        "text":text
    })

    send_state(room)

# ===============================
# الطرد (يشمل الجميع)
# ===============================

@socketio.on("kick_player")
def on_kick_player(data):

    room = data.get("room")
    host_id = data.get("hostId")
    target_id = data.get("targetId")

    if room not in rooms:
        return

    r = rooms[room]

    if r.get("host") != host_id:
        emit("error_msg","فقط صاحب الغرفة")
        return

    # لاعب
    idx = find_player(room, target_id)
    if idx >= 0:
        name = r["players"][idx]["name"]
        sid = r["players"][idx]["sid"]
        r["players"].pop(idx)

        r["log"].insert(0, f"🚫 تم طرد {name}")
        emit("kicked",{}, room=sid)
        send_state(room)
        return

    # مشاهد
    spectators = r.get("spectators",[])
    sidx = next((i for i,s in enumerate(spectators) if s["id"]==target_id), -1)

    if sidx >= 0:
        name = spectators[sidx]["name"]
        sid = spectators[sidx]["sid"]
        spectators.pop(sidx)

        r["log"].insert(0, f"🚫 تم طرد المشاهد {name}")
        emit("kicked",{}, room=sid)
        send_state(room)
        return

# ===============================
# خروج
# ===============================

@socketio.on("leave_room")
def on_leave(data):

    room = data.get("room")
    pid = data.get("playerId")

    if room not in rooms:
        return

    r = rooms[room]

    idx = find_player(room, pid)
    if idx >= 0:
        name = r["players"][idx]["name"]
        r["players"].pop(idx)
        r["log"].insert(0, f"{name} خرج")

    else:
        spectators = r.get("spectators",[])
        s = next((x for x in spectators if x["id"]==pid), None)
        if s:
            spectators.remove(s)
            r["log"].insert(0, f"{s['name']} خرج (مشاهد)")

    send_state(room)

# ===============================
# تشغيل السيرفر
# ===============================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
