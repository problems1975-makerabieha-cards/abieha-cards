from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
import random, uuid, os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "abieha-cards-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

COLORS = ["red", "bluec", "greenc", "yellow"]
TEAM_ORDER = ["A", "B", "C"]
TEAM_NAMES = {"A": "الفريق الأزرق", "B": "الفريق البرتقالي", "C": "الفريق البنفسجي"}
rooms = {}

def build_deck():
    deck = []
    for c in COLORS:
        deck.append({"c": c, "n": "0"})
        for i in range(1, 10):
            deck += [{"c": c, "n": str(i)}, {"c": c, "n": str(i)}]
        for n in ["+2", "عكس", "تخطي"]:
            deck += [{"c": c, "n": n}, {"c": c, "n": n}]
    for _ in range(4):
        deck += [{"c": "black", "n": "لون"}, {"c": "black", "n": "+4"}]
    random.shuffle(deck)
    return deck

def next_index(r):
    return (r["turn"] + r["direction"] + len(r["players"])) % len(r["players"])

def draw_to(r, idx, count):
    for _ in range(count):
        if not r["deck"] and len(r["discard"]) > 1:
            keep = r["discard"].pop()
            r["deck"] = r["discard"]
            random.shuffle(r["deck"])
            r["discard"] = [keep]
        if r["deck"]:
            r["players"][idx]["hand"].append(r["deck"].pop())

def team_scores(r):
    scores = {"A": 0, "B": 0, "C": 0}
    for p in r["players"]:
        if p.get("team") in scores:
            scores[p["team"]] += p.get("wins", 0)
    return scores

def public_state(room):
    r = rooms[room]
    return {
        "room": room, "started": r["started"], "turn": r["turn"],
        "direction": r["direction"], "color": r["color"],
        "mode": r.get("mode", "solo"), "teamMode": r.get("teamMode", "auto"),
        "teamCount": r.get("teamCount", 2), "pendingDraw4": r.get("pendingDraw4", 0),
        "top": r["discard"][-1] if r["discard"] else None,
        "deckCount": len(r["deck"]), "teamScores": team_scores(r),
        "players": [{"id": p["id"], "name": p["name"], "team": p.get("team"),
                     "count": len(p["hand"]), "last": p.get("last", False),
                     "wins": p.get("wins", 0)} for p in r["players"]],
        "log": r["log"][:45],
    }

def send_state(room):
    if room not in rooms:
        return
    for p in rooms[room]["players"]:
        payload = public_state(room)
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

def assign_auto_team(r):
    count = max(2, min(3, int(r.get("teamCount", 2) or 2)))
    return TEAM_ORDER[:count][len(r["players"]) % count]

def is_allowed(r, card):
    if r.get("pendingDraw4", 0) > 0:
        return card["n"] in ["+4", "عكس", "تخطي"]
    top = r["discard"][-1]
    return card["c"] == "black" or card["c"] == r["color"] or card["n"] == top["n"]

def apply_effect(r, card):
    if card["n"] == "+4":
        r["pendingDraw4"] = int(r.get("pendingDraw4", 0)) + 4
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw4']}")
        r["turn"] = next_index(r)
        return
    if r.get("pendingDraw4", 0) > 0 and card["n"] == "عكس":
        r["direction"] *= -1
        r["log"].insert(0, "تم عكس عقوبة +4")
        r["turn"] = next_index(r)
        return
    if r.get("pendingDraw4", 0) > 0 and card["n"] == "تخطي":
        skipped = next_index(r)
        r["turn"] = skipped
        r["log"].insert(0, f"تم تخطي {r['players'][skipped]['name']} والعقوبة مستمرة")
        r["turn"] = next_index(r)
        return
    if card["n"] == "+2":
        r["turn"] = next_index(r)
        draw_to(r, r["turn"], 2)
        r["log"].insert(0, f"{r['players'][r['turn']]['name']} سحب كرتين")
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
    mode = data.get("mode", "solo")
    team_mode = data.get("teamMode", "auto")
    team_count = max(2, min(3, int(data.get("teamCount", 2) or 2)))
    selected_team = data.get("team", "A")

    if room not in rooms:
        rooms[room] = {"players": [], "deck": [], "discard": [], "turn": 0, "direction": 1,
                       "color": None, "started": False, "log": [], "mode": mode,
                       "teamMode": team_mode, "teamCount": team_count, "pendingDraw4": 0}

    r = rooms[room]
    if r["started"]:
        emit("error_msg", "اللعبة بدأت، انتظر الجولة القادمة")
        return
    if len(r["players"]) >= 6:
        emit("error_msg", "الغرفة ممتلئة، الحد 6 لاعبين")
        return

    if len(r["players"]) == 0:
        r["mode"] = mode
        r["teamMode"] = team_mode
        r["teamCount"] = team_count

    team = None
    if r.get("mode") == "teams":
        if r.get("teamMode") == "manual":
            allowed = TEAM_ORDER[:r.get("teamCount", 2)]
            team = selected_team if selected_team in allowed else allowed[0]
        else:
            team = assign_auto_team(r)

    join_room(room)
    pid = str(uuid.uuid4())
    r["players"].append({"id": pid, "sid": request.sid, "name": name, "team": team,
                         "hand": [], "last": False, "wins": 0})
    r["log"].insert(0, f"{name} دخل الغرفة" + (f" - {TEAM_NAMES.get(team, team)}" if team else ""))
    emit("joined", {"room": room, "playerId": pid})
    send_state(room)

@socketio.on("change_team")
def on_change_team(data):
    room, player_id, team = data.get("room"), data.get("playerId"), data.get("team")
    if room not in rooms: return
    r = rooms[room]
    if r["started"]:
        emit("error_msg", "لا يمكن تغيير الفريق بعد البداية")
        return
    idx = find_player(room, player_id)
    allowed = TEAM_ORDER[:r.get("teamCount", 2)]
    if idx >= 0 and team in allowed and r.get("mode") == "teams":
        r["players"][idx]["team"] = team
        r["log"].insert(0, f"{r['players'][idx]['name']} انتقل إلى {TEAM_NAMES.get(team, team)}")
    send_state(room)

@socketio.on("start")
def on_start(data):
    room = data.get("room")
    if room not in rooms: return
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
    r["pendingDraw4"] = 0
    r["log"] = ["بدأت اللعبة"]
    for p in r["players"]:
        p["hand"] = [r["deck"].pop() for _ in range(7)]
        p["last"] = False
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
    room, player_id = data.get("room"), data.get("playerId")
    index = int(data.get("index", -1))
    if room not in rooms: return
    r = rooms[room]
    idx = find_player(room, player_id)
    if idx < 0 or not r["started"] or idx != r["turn"]:
        emit("error_msg", "مو دورك")
        return
    p = r["players"][idx]
    if index < 0 or index >= len(p["hand"]):
        emit("error_msg", "الكرت غير موجود")
        return
    card = p["hand"][index]
    if not is_allowed(r, card):
        emit("error_msg", "عليك +4: مسموح فقط +4 أو عكس أو تخطي، أو اسحب العقوبة" if r.get("pendingDraw4",0)>0 else "هذا الكرت ما ينفع")
        return
    p["hand"].pop(index)
    r["discard"].append(card)
    r["color"] = random.choice(COLORS) if card["c"] == "black" else card["c"]
    r["log"].insert(0, f"{p['name']} رمى {card['n']}")
    if len(p["hand"]) == 0:
        p["wins"] += 1
        r["started"] = False
        r["log"].insert(0, f"🏆 فاز {TEAM_NAMES.get(p.get('team'), p['name']) if p.get('team') else p['name']}")
        send_state(room)
        return
    apply_effect(r, card)
    for pp in r["players"]:
        if len(pp["hand"]) != 1:
            pp["last"] = False
    send_state(room)

@socketio.on("draw")
def on_draw(data):
    room, player_id = data.get("room"), data.get("playerId")
    if room not in rooms: return
    r = rooms[room]
    idx = find_player(room, player_id)
    if idx < 0 or not r["started"] or idx != r["turn"]:
        emit("error_msg", "مو دورك")
        return
    amount = int(r.get("pendingDraw4", 0) or 0)
    if amount > 0:
        draw_to(r, idx, amount)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب عقوبة {amount}")
        r["pendingDraw4"] = 0
    else:
        draw_to(r, idx, 1)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب كرت")
    r["turn"] = next_index(r)
    send_state(room)

@socketio.on("last_card")
def on_last_card(data):
    room, player_id = data.get("room"), data.get("playerId")
    if room not in rooms: return
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
            if not r["players"]:
                del rooms[room]
            else:
                if r["turn"] >= len(r["players"]):
                    r["turn"] = 0
                r["log"].insert(0, "لاعب خرج من الغرفة")
                send_state(room)
            break

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
