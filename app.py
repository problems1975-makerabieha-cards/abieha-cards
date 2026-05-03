from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit, disconnect
import random
import uuid

app = Flask(__name__)
app.config["SECRET_KEY"] = "abieha-cards-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

COLORS = ["red", "bluec", "greenc", "yellow"]
rooms = {}

def build_deck():
    deck = []
    for c in COLORS:
        deck.append({"c": c, "n": "0"})
        for i in range(1, 10):
            deck.append({"c": c, "n": str(i)})
            deck.append({"c": c, "n": str(i)})
        for n in ["+2", "عكس", "تخطي"]:
            deck.append({"c": c, "n": n})
            deck.append({"c": c, "n": n})
    for _ in range(4):
        deck.append({"c": "black", "n": "لون"})
        deck.append({"c": "black", "n": "+4"})
    random.shuffle(deck)
    return deck

def next_index(r):
    n = len(r["players"])
    return (r["turn"] + r["direction"] + n) % n

def draw_to(r, idx, count):
    for _ in range(count):
        if not r["deck"]:
            if len(r["discard"]) > 1:
                keep = r["discard"].pop()
                r["deck"] = r["discard"]
                random.shuffle(r["deck"])
                r["discard"] = [keep]
        if r["deck"]:
            r["players"][idx]["hand"].append(r["deck"].pop())

def public_room(room):
    r = rooms[room]
    return {
        "room": room,
        "started": r["started"],
        "turn": r["turn"],
        "direction": r["direction"],
        "color": r["color"],
        "top": r["discard"][-1] if r["discard"] else None,
        "deckCount": len(r["deck"]),
        "players": [
            {
                "id": p["id"],
                "name": p["name"],
                "count": len(p["hand"]),
                "last": p.get("last", False),
                "wins": p.get("wins", 0),
            }
            for p in r["players"]
        ],
        "log": r["log"][-40:],
    }

def send_state(room):
    if room not in rooms:
        return
    r = rooms[room]
    for p in r["players"]:
        payload = public_room(room)
        payload["myId"] = p["id"]
        payload["myHand"] = p["hand"]
        socketio.emit("state", payload, room=p["sid"])

def find_player(room, player_id):
    if room not in rooms:
        return -1
    for i, p in enumerate(rooms[room]["players"]):
        if p["id"] == player_id:
            return i
    return -1

def apply_effect(r, card):
    if card["n"] == "+2":
        r["turn"] = next_index(r)
        draw_to(r, r["turn"], 2)
        r["log"].insert(0, f"{r['players'][r['turn']]['name']} سحب كرتين")
    elif card["n"] == "+4":
        r["turn"] = next_index(r)
        draw_to(r, r["turn"], 4)
        r["log"].insert(0, f"{r['players'][r['turn']]['name']} سحب 4")
    elif card["n"] == "تخطي":
        r["turn"] = next_index(r)
        r["log"].insert(0, f"تم تخطي {r['players'][r['turn']]['name']}")
    elif card["n"] == "عكس":
        r["direction"] *= -1
        r["log"].insert(0, "تغير اتجاه اللعب")
    r["turn"] = next_index(r)

@app.route("/")
def index():
    return render_template("online.html")

@socketio.on("join")
def on_join(data):
    room = (data.get("room") or "ROOM1").strip().upper()
    name = (data.get("name") or "لاعب").strip()[:18]

    if room not in rooms:
        rooms[room] = {
            "players": [],
            "deck": [],
            "discard": [],
            "turn": 0,
            "direction": 1,
            "color": None,
            "started": False,
            "log": [],
        }

    r = rooms[room]
    if len(r["players"]) >= 6:
        emit("error_msg", "الغرفة ممتلئة، الحد 6 لاعبين")
        return

    join_room(room)
    pid = str(uuid.uuid4())
    r["players"].append({
        "id": pid,
        "sid": request.sid,
        "name": name,
        "hand": [],
        "last": False,
        "wins": 0,
    })
    r["log"].insert(0, f"{name} دخل الغرفة")
    emit("joined", {"room": room, "playerId": pid})
    send_state(room)

@socketio.on("start")
def on_start(data):
    room = data.get("room")
    if room not in rooms:
        return
    r = rooms[room]
    if len(r["players"]) < 2:
        emit("error_msg", "لازم لاعبين على الأقل")
        return

    r["deck"] = build_deck()
    r["discard"] = []
    r["turn"] = 0
    r["direction"] = 1
    r["started"] = True
    r["color"] = None
    r["log"] = ["بدأت اللعبة"]

    for p in r["players"]:
        p["hand"] = []
        p["last"] = False
        for _ in range(7):
            p["hand"].append(r["deck"].pop())

    first = r["deck"].pop()
    while first["c"] == "black":
        r["deck"].insert(0, first)
        random.shuffle(r["deck"])
        first = r["deck"].pop()

    r["discard"].append(first)
    r["color"] = first["c"]
    send_state(room)

@socketio.on("play")
def on_play(data):
    room = data.get("room")
    player_id = data.get("playerId")
    index = int(data.get("index", -1))

    if room not in rooms:
        return
    r = rooms[room]
    idx = find_player(room, player_id)

    if idx < 0:
        emit("error_msg", "اللاعب غير موجود")
        return
    if not r["started"]:
        emit("error_msg", "اللعبة لم تبدأ")
        return
    if idx != r["turn"]:
        emit("error_msg", "مو دورك")
        return

    p = r["players"][idx]
    if index < 0 or index >= len(p["hand"]):
        emit("error_msg", "الكرت غير موجود")
        return

    card = p["hand"][index]
    top = r["discard"][-1]
    allowed = card["c"] == "black" or card["c"] == r["color"] or card["n"] == top["n"]

    if not allowed:
        emit("error_msg", "هذا الكرت ما ينفع")
        return

    p["hand"].pop(index)
    r["discard"].append(card)
    if card["c"] == "black":
        r["color"] = random.choice(COLORS)
    else:
        r["color"] = card["c"]

    r["log"].insert(0, f"{p['name']} رمى {card['n']}")

    if len(p["hand"]) == 0:
        p["wins"] = p.get("wins", 0) + 1
        r["started"] = False
        r["log"].insert(0, f"🏆 فاز {p['name']}")
        send_state(room)
        return

    apply_effect(r, card)
    for pp in r["players"]:
        if len(pp["hand"]) != 1:
            pp["last"] = False
    send_state(room)

@socketio.on("draw")
def on_draw(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    idx = find_player(room, player_id)

    if idx < 0:
        emit("error_msg", "اللاعب غير موجود")
        return
    if not r["started"]:
        emit("error_msg", "اللعبة لم تبدأ")
        return
    if idx != r["turn"]:
        emit("error_msg", "مو دورك")
        return

    draw_to(r, idx, 1)
    r["log"].insert(0, f"{r['players'][idx]['name']} سحب كرت")
    r["turn"] = next_index(r)
    send_state(room)

@socketio.on("last_card")
def on_last_card(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    idx = find_player(room, player_id)
    if idx >= 0 and len(r["players"][idx]["hand"]) == 1:
        r["players"][idx]["last"] = True
        r["log"].insert(0, f"{r['players'][idx]['name']} قال: كرت أخير")
    else:
        emit("error_msg", "تقدر تضغط كرت أخير لما يبقى عندك كرت واحد")
    send_state(room)

@socketio.on("disconnect")
def on_disconnect():
    for room, r in list(rooms.items()):
        before = len(r["players"])
        r["players"] = [p for p in r["players"] if p["sid"] != request.sid]
        if len(r["players"]) != before:
            r["log"].insert(0, "لاعب خرج من الغرفة")
            if not r["players"]:
                del rooms[room]
            else:
                if r["turn"] >= len(r["players"]):
                    r["turn"] = 0
                send_state(room)
            break

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)