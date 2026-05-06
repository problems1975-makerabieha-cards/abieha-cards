from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, join_room, emit
import random, uuid, os, threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

COLORS = ["red", "bluec", "greenc", "yellow"]
rooms = {}

# =========================
# أدوات
# =========================

def next_index(r):
    return (r["turn"] + r["direction"]) % len(r["players"])

def draw_to(r, idx, count):
    for _ in range(count):
        if not r["deck"] and len(r["discard"]) > 1:
            keep = r["discard"].pop()
            r["deck"] = r["discard"]
            random.shuffle(r["deck"])
            r["discard"] = [keep]
        if r["deck"]:
            r["players"][idx]["hand"].append(r["deck"].pop())

def card_points(card):
    n = card.get("n")
    if n in ["عكس", "تخطي", "+2"]:
        return 20
    if n == "لون":
        return 40
    if n == "+4":
        return 50
    try:
        return int(n)
    except:
        return 0

# =========================
# الدك
# =========================

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

# =========================
# السماح باللعب
# =========================

def is_allowed(r, card):
    top = r["discard"][-1]

    # +4
    if r.get("pendingDraw4", 0) > 0:
        return (
            card["n"] == "+4" or
            (card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"])
        )

    # +2
    if r.get("pendingDraw2", 0) > 0:
        return (
            card["n"] == "+2" or
            (card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"])
        )

    # اللعب العادي
    return (
        card["c"] == "black" or
        card["c"] == r["color"] or
        card["n"] == top["n"]
    )

# =========================
# التأثيرات
# =========================

def apply_effect(r, card):

    # +2
    if card["n"] == "+2":
        r["pendingDraw2"] = int(r.get("pendingDraw2", 0)) + 2
        r["pendingDraw4"] = 0
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw2']}")
        r["turn"] = next_index(r)
        return

    # +4
    if card["n"] == "+4":
        r["pendingDraw4"] = int(r.get("pendingDraw4", 0)) + 4
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw4']}")
        r["turn"] = next_index(r)
        return

    # عكس / تخطي
    if card["n"] in ["عكس", "تخطي"]:

        # تمرير عقوبة +2
        if r.get("pendingDraw2", 0) > 0:
            r["log"].insert(0, f"تم تمرير العقوبة {r['pendingDraw2']}")
            r["turn"] = next_index(r)
            return

        # تمرير عقوبة +4
        if r.get("pendingDraw4", 0) > 0:
            r["log"].insert(0, f"تم تمرير العقوبة {r['pendingDraw4']}")
            r["turn"] = next_index(r)
            return

        if card["n"] == "عكس":
            r["direction"] *= -1
            r["log"].insert(0, "عكس اتجاه اللعب")
        else:
            r["log"].insert(0, "تم تخطي اللاعب التالي")
            r["turn"] = next_index(r)

        r["pendingDraw2"] = 0
        r["pendingDraw4"] = 0
        r["turn"] = next_index(r)
        return

    # باقي الكروت
    r["pendingDraw2"] = 0
    r["pendingDraw4"] = 0
    r["turn"] = next_index(r)

# =========================
# التايمر
# =========================

def cancel_timer(r):
    t = r.get("timer")
    if t:
        try:
            t.cancel()
        except:
            pass

def start_timer(room):
    r = rooms.get(room)
    if not r:
        return

    cancel_timer(r)
    r["timeLeft"] = r.get("timeLimit", 30)

    def tick():
        rr = rooms.get(room)
        if not rr or not rr.get("started"):
            return

        rr["timeLeft"] -= 1
        send_state(room)

        if rr["timeLeft"] <= 0:
            handle_timeout(room)
            return

        rr["timer"] = threading.Timer(1, tick)
        rr["timer"].start()

    r["timer"] = threading.Timer(1, tick)
    r["timer"].start()

def handle_timeout(room):
    r = rooms.get(room)
    if not r:
        return

    idx = r["turn"]

    if r.get("pendingDraw4", 0) > 0:
        draw_to(r, idx, r["pendingDraw4"])
        r["pendingDraw4"] = 0
    elif r.get("pendingDraw2", 0) > 0:
        draw_to(r, idx, r["pendingDraw2"])
        r["pendingDraw2"] = 0
    else:
        draw_to(r, idx, 1)

    r["turn"] = next_index(r)
    start_timer(room)
    send_state(room)

# =========================
# الحالة
# =========================

def send_state(room):
    r = rooms.get(room)
    if not r:
        return

    for p in r["players"]:
        socketio.emit("state", {
            "players": [
                {
                    "id": pp["id"],
                    "name": pp["name"],
                    "count": len(pp["hand"]),
                    "score": pp.get("score", 0)
                } for pp in r["players"]
            ],
            "myHand": p["hand"],
            "top": r["discard"][-1],
            "turn": r["turn"],
            "color": r["color"],
            "log": r["log"],
            "timeLeft": r["timeLeft"],
            "started": r["started"]
        }, room=p["sid"])

# =========================
# Flask
# =========================

@app.route("/")
def index():
    return render_template("index.html")

# =========================
# Socket
# =========================

@socketio.on("join")
def join(data):
    room = data["room"]
    name = data["name"]

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
            "timeLimit": 30
        }

    r = rooms[room]

    pid = str(uuid.uuid4())
    join_room(room)

    r["players"].append({
        "id": pid,
        "sid": request.sid,
        "name": name,
        "hand": [],
        "score": 0
    })

    emit("joined", {"playerId": pid})
    send_state(room)

@socketio.on("start")
def start(data):
    room = data["room"]
    r = rooms[room]

    r["deck"] = build_deck()
    r["discard"] = []
    r["started"] = True
    r["log"] = ["بدأت اللعبة"]

    for p in r["players"]:
        p["hand"] = [r["deck"].pop() for _ in range(7)]

    first = r["deck"].pop()
    r["discard"].append(first)
    r["color"] = first["c"]

    start_timer(room)
    send_state(room)

@socketio.on("play")
def play(data):
    room = data["room"]
    player_id = data["playerId"]
    index = data["index"]

    r = rooms[room]
    idx = next(i for i,p in enumerate(r["players"]) if p["id"]==player_id)

    p = r["players"][idx]
    card = p["hand"][index]

    if not is_allowed(r, card):
        emit("error_msg", "هذا الكرت ما ينفع")
        return

    p["hand"].pop(index)
    r["discard"].append(card)
    r["color"] = card["c"]

    apply_effect(r, card)

    start_timer(room)
    send_state(room)

@socketio.on("draw")
def draw(data):
    room = data["room"]
    player_id = data["playerId"]

    r = rooms[room]
    idx = next(i for i,p in enumerate(r["players"]) if p["id"]==player_id)

    if r.get("pendingDraw4", 0):
        draw_to(r, idx, r["pendingDraw4"])
        r["pendingDraw4"] = 0
    elif r.get("pendingDraw2", 0):
        draw_to(r, idx, r["pendingDraw2"])
        r["pendingDraw2"] = 0
    else:
        draw_to(r, idx, 1)

    r["turn"] = next_index(r)
    start_timer(room)
    send_state(room)

# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
