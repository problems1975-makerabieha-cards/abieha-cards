from flask import Flask, request, send_file
from flask_socketio import SocketIO, join_room, emit
import random, os, threading

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "abieha-final-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}

@app.route("/")
def index():
    return send_file("templates/index.html")

# ==============================
# 👑 نقل القيادة
# ==============================
def transfer_host(room, r):
    trusted = r.get("trustedHosts", [])

    # نائب أول
    for tid in trusted:
        for p in r["players"]:
            if p["id"] == tid:
                r["host"] = p["id"]
                r["log"].insert(0, f"👑 القائد الجديد (نائب): {p['name']}")
                return

    # fallback
    if r["players"]:
        r["host"] = r["players"][0]["id"]
        r["log"].insert(0, f"👑 القائد الجديد: {r['players'][0]['name']}")
    else:
        r["host"] = None

# ==============================
# 🧠 STATE
# ==============================
def public_state(room):
    r = rooms[room]
    return {
        "room": room,
        "hostId": r.get("host"),
        "trustedHosts": r.get("trustedHosts", []),
        "players": r.get("players", []),
        "spectators": r.get("spectators", []),
        "log": r.get("log", [])
    }

def send_state(room):
    r = rooms[room]
    for p in r["players"] + r["spectators"]:
        if p.get("sid"):
            socketio.emit("state", public_state(room), room=p["sid"])

# ==============================
# 🔥 JOIN
# ==============================
@socketio.on("join")
def on_join(data):
    room = (data.get("room") or "ROOM1").upper()
    name = data.get("name") or "لاعب"

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

    # 👑 أول شخص = القائد
    if r["host"] is None:
        r["host"] = player_id

    r["log"].insert(0, f"{name} دخل 👀")

    emit("joined", {"playerId": player_id, "room": room})
    send_state(room)

# ==============================
# 🪑 الجلوس
# ==============================
@socketio.on("sit_seat")
def sit(data):
    room = data.get("room")
    pid = data.get("playerId")
    seat = int(data.get("seat", 0))

    if room not in rooms:
        return

    r = rooms[room]

    # تحقق من المقعد
    if any(p.get("seat") == seat for p in r["players"]):
        emit("error_msg", "المقعد محجوز")
        return

    # تحويل من مشاهد إلى لاعب
    for i, s in enumerate(r["spectators"]):
        if s["id"] == pid:
            spectator = r["spectators"].pop(i)

            r["players"].append({
                "id": spectator["id"],
                "sid": spectator["sid"],
                "name": spectator["name"],
                "seat": seat
            })

            r["log"].insert(0, f"{spectator['name']} جلس على المقعد {seat+1}")

            send_state(room)
            return

# ==============================
# 🚫 طرد
# ==============================
@socketio.on("kick_player")
def kick(data):
    room = data.get("room")
    host_id = data.get("hostId")
    target = data.get("targetId")

    if room not in rooms:
        return

    r = rooms[room]

    if r["host"] != host_id:
        emit("error_msg", "فقط القائد")
        return

    if target == host_id:
        emit("error_msg", "ما تقدر تطرد نفسك")
        return

    # لاعب
    for i,p in enumerate(r["players"]):
        if p["id"] == target:
            sid = p["sid"]
            name = p["name"]
            r["players"].pop(i)
            r["log"].insert(0, f"🚫 تم طرد {name}")
            if sid:
                emit("kicked", room=sid)
            send_state(room)
            return

    # مشاهد
    for i,s in enumerate(r["spectators"]):
        if s["id"] == target:
            sid = s["sid"]
            name = s["name"]
            r["spectators"].pop(i)
            r["log"].insert(0, f"🚫 تم طرد {name}")
            if sid:
                emit("kicked", room=sid)
            send_state(room)

# ==============================
# 🔄 خروج
# ==============================
@socketio.on("leave_room")
def leave(data):
    room = data.get("room")
    pid = data.get("playerId")

    if room not in rooms:
        return

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
# ❌ disconnect
# ==============================
@socketio.on("disconnect")
def disc():
    for room, r in rooms.items():
        for p in r["players"]:
            if p["sid"] == request.sid:
                if r["host"] == p["id"]:
                    transfer_host(room, r)
                return

# ==============================
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
