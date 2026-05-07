from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, join_room, emit
import random, os, threading

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}

@app.route("/")
def index():
    return send_file("templates/index.html")

# ==============================
# 🔥 نقل القيادة الذكي
# ==============================
def transfer_host(room, r):
    trusted = r.get("trustedHosts", [])

    for tid in trusted:
        for p in r["players"]:
            if p["id"] == tid:
                r["host"] = p["id"]
                r["log"].insert(0, f"👑 القائد الجديد (نائب): {p['name']}")
                return

    if r["players"]:
        r["host"] = r["players"][0]["id"]
        r["log"].insert(0, f"👑 القائد الجديد: {r['players'][0]['name']}")
    else:
        r["host"] = None

# ==============================
# 🔥 JOIN
# ==============================
@socketio.on("join")
def on_join(data):
    room = data.get("room", "ROOM1")
    name = data.get("name", "لاعب")

    if room not in rooms:
        rooms[room] = {
            "players": [],
            "spectators": [],
            "host": None,
            "trustedHosts": [],
            "log": []
        }

    r = rooms[room]
    join_room(room)

    player_id = request.sid

    r["spectators"].append({
        "id": player_id,
        "sid": request.sid,
        "name": name
    })

    if r["host"] is None:
        r["host"] = player_id

    emit("joined", {"playerId": player_id, "room": room})
    send_state(room)

# ==============================
# 🔥 STATE
# ==============================
def public_state(room):
    r = rooms[room]
    return {
        "room": room,
        "hostId": r.get("host"),
        "trustedHosts": r.get("trustedHosts", []),
        "players": r["players"],
        "spectators": r["spectators"],
        "log": r["log"]
    }

def send_state(room):
    for p in rooms[room]["players"] + rooms[room]["spectators"]:
        socketio.emit("state", public_state(room), room=p["sid"])

# ==============================
# 🔥 طرد لاعب / مشاهد
# ==============================
@socketio.on("kick_player")
def kick(data):
    room = data.get("room")
    host = data.get("hostId")
    target = data.get("targetId")

    if room not in rooms: return
    r = rooms[room]

    if r["host"] != host:
        emit("error_msg", "فقط القائد")
        return

    if target == host:
        emit("error_msg", "ما تقدر تطرد نفسك")
        return

    # لاعب
    for i,p in enumerate(r["players"]):
        if p["id"] == target:
            sid = p["sid"]
            name = p["name"]
            r["players"].pop(i)
            r["log"].insert(0, f"🚫 تم طرد {name}")
            socketio.emit("kicked", room=sid)
            send_state(room)
            return

    # مشاهد
    for i,s in enumerate(r["spectators"]):
        if s["id"] == target:
            sid = s["sid"]
            name = s["name"]
            r["spectators"].pop(i)
            r["log"].insert(0, f"🚫 تم طرد {name}")
            socketio.emit("kicked", room=sid)
            send_state(room)

# ==============================
# 🔥 نائب قائد
# ==============================
@socketio.on("toggle_trusted_host")
def toggle_trusted(data):
    room = data.get("room")
    host = data.get("hostId")
    target = data.get("targetId")

    if room not in rooms: return
    r = rooms[room]

    if r["host"] != host: return

    if target in r["trustedHosts"]:
        r["trustedHosts"].remove(target)
    else:
        r["trustedHosts"].append(target)

    send_state(room)

# ==============================
# 🔥 نقل القيادة يدوي
# ==============================
@socketio.on("make_host")
def make_host(data):
    room = data.get("room")
    host = data.get("hostId")
    target = data.get("targetId")

    if room not in rooms: return
    r = rooms[room]

    if r["host"] != host: return

    r["host"] = target
    r["log"].insert(0, "👑 تم تغيير القائد")
    send_state(room)

# ==============================
# 🔥 خروج
# ==============================
@socketio.on("leave_room")
def leave(data):
    room = data.get("room")
    pid = data.get("playerId")

    if room not in rooms: return
    r = rooms[room]

    for arr in ["players","spectators"]:
        for i,x in enumerate(r[arr]):
            if x["id"] == pid:
                r[arr].pop(i)
                break

    if r["host"] == pid:
        transfer_host(room, r)

    send_state(room)

# ==============================
# 🔥 disconnect
# ==============================
@socketio.on("disconnect")
def disc():
    for room,r in rooms.items():
        for p in r["players"]:
            if p["sid"] == request.sid:
                if r["host"] == p["id"]:
                    transfer_host(room,r)
                return

# ==============================
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
