from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, join_room, emit
import random, uuid, os, threading

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "abieha-final-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

COLORS = ["red", "bluec", "greenc", "yellow"]
TEAM_ORDER = ["A", "B", "C"]
TEAM_NAMES = {"A": "الفريق الأزرق", "B": "الفريق البرتقالي", "C": "الفريق البنفسجي"}

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
        t = p.get("team")
        if t in scores:
            scores[t] += p.get("wins", 0)
    return scores

def public_state(room):
    r = rooms[room]
    return {
        "room": room,
        "started": r["started"],
        "turn": r["turn"],
        "direction": r["direction"],
        "color": r["color"],
        "mode": r.get("mode", "solo"),
        "teamMode": r.get("teamMode", "auto"),
        "teamCount": r.get("teamCount", 2),
        "pendingDraw4": r.get("pendingDraw4", 0),
        "pendingDraw2": r.get("pendingDraw2", 0),
        "top": r["discard"][-1] if r["discard"] else None,
        "deckCount": len(r["deck"]),
        "timeLeft": r.get("timeLeft", 0),
        "timeLimit": r.get("timeLimit", 10),
        "teamScores": team_scores(r),
        "hostId": r.get("host"),
        "players": [
            {
                "id": p["id"],
                "name": p["name"],
                "team": p.get("team"),
                "count": len(p["hand"]),
                "last": p.get("last", False),
                "wins": p.get("wins", 0),
            }
            for p in r["players"]
        ],
   "log": [
    x for x in r.get("log", [])[:60]
    if (
        "دخل الغرفة" in x or
        "خرج من الغرفة" in x or
        x.startswith("💬")
    )
],
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
    valid = TEAM_ORDER[:count]
    return valid[len(r["players"]) % len(valid)]

def is_allowed(r, card):
    top = r["discard"][-1]

    # إذا فيه عقوبة +4: لا أرقام، فقط +4 أو عكس/تخطي بنفس اللون
    if r.get("pendingDraw4", 0) > 0:
        return card["n"] == "+4" or (
            card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"]
        )

    # إذا فيه عقوبة +2: لا أرقام، فقط +2/+4 أو عكس/تخطي حسب الكرت أو اللون
    if r.get("pendingDraw2", 0) > 0:
        return (
            card["n"] in ["+2", "+4"] or
            (
                card["n"] in ["عكس", "تخطي"] and
                (card["n"] == top["n"] or card["c"] == r["color"])
            )
        )

    # الوضع العادي: بعد تخطي/عكس تقدر تلعب رقم إذا نفس اللون
    return card["c"] == "black" or card["c"] == r["color"] or card["n"] == top["n"]
    # During Skip/Reverse challenge: player may answer with Skip/Reverse in the requested color,
    # otherwise the Draw button makes them draw two cards.
def is_allowed(r, card):
    top = r["discard"][-1]

    # إذا فيه عقوبة +4: لا أرقام
    if r.get("pendingDraw4", 0) > 0:
        return card["n"] == "+4" or (
            card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"]
        )

    # إذا فيه عقوبة +2: لا أرقام
    if r.get("pendingDraw2", 0) > 0:
        return (
            card["n"] in ["+2", "+4"] or
            (
                card["n"] in ["عكس", "تخطي"] and
                (
                    card["n"] == top["n"] or
                    card["c"] == r["color"]
                )
            )
        )

    # اللعب العادي:
    # إذا الموجود عكس/تخطي، يسمح برقم نفس اللون
    return card["c"] == "black" or card["c"] == r["color"] or card["n"] == top["n"]

def apply_effect(r, card):
    # +2 (stack)
    if card["n"] == "+2":
        r["pendingDraw2"] = int(r.get("pendingDraw2", 0)) + 2
        r["log"].insert(0, f"العقوبة الآن: {r['pendingDraw2']}")
        r["turn"] = next_index(r)
        return

    # +4 (stack)
    if card["n"] == "+4":
        r["pendingDraw4"] = int(r.get("pendingDraw4", 0)) + 4
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw4']} أو رد +4 / تخطي / عكس بنفس اللون")
        r["turn"] = next_index(r)
        return

    # دفاع ضد +4
    if r.get("pendingDraw4", 0) > 0 and card["n"] == "عكس":
        r["direction"] *= -1
        r["log"].insert(0, "تم عكس عقوبة +4")
        r["turn"] = next_index(r)
        return

    if r.get("pendingDraw4", 0) > 0 and card["n"] == "تخطي":
        r["log"].insert(0, "تم تمرير عقوبة +4")
        r["turn"] = next_index(r)
        return

    # عكس / تخطي
    if card["n"] in ["عكس", "تخطي"]:

        # لاعبين فقط
        if len(r["players"]) == 2:
            current = r["turn"]

            if card["n"] == "عكس":
                r["direction"] *= -1
                r["log"].insert(0, "عكس: نفس اللاعب يلعب")
            else:
                r["log"].insert(0, "تخطي: نفس اللاعب يلعب")

            r["turn"] = current
            return

        # أكثر من لاعبين
        if card["n"] == "عكس":
            r["direction"] *= -1
            r["log"].insert(0, "عكس: اللاعب التالي يرد أو يسحب")
        else:
            r["log"].insert(0, "تخطي: اللاعب التالي يرد أو يسحب")

        r["pendingDraw2"] = 2
        r["turn"] = next_index(r)
        return

    # كرت عادي
    r["pendingDraw2"] = 0
    r["turn"] = next_index(r)
def cancel_timer(r):
    t = r.get("timer")
    if t:
        try:
            t.cancel()
        except Exception:
            pass
        r["timer"] = None

def start_timer(room):
    r = rooms[room]
    cancel_timer(r)
    r["timeLeft"] = r.get("timeLimit", 10)

    def tick():
        if not r["started"]:
            return

        r["timeLeft"] -= 1

if r["timeLeft"] <= 0:
    idx = r["turn"]

    amount4 = int(r.get("pendingDraw4", 0) or 0)
    amount2 = int(r.get("pendingDraw2", 0) or 0)

    if amount4 > 0:
        total = amount4 + 1
        draw_to(r, idx, total)
        r["pendingDraw4"] = 0
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته ⏱️ وسحب {total}")

    elif amount2 > 0:
        total = amount2 + 1
        draw_to(r, idx, total)
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته ⏱️ وسحب {total}")

    else:
def tick():
    r = rooms.get(room)
    if not r:
        return

    r["timeLeft"] = max(0, r.get("timeLeft", 0) - 1)

    if r["timeLeft"] <= 0:
        handle_timeout(room)
        return

    r["timer"] = threading.Timer(1, tick)
    r["timer"].daemon = True
    r["timer"].start()
@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception:
        # Fallback for Render deploys where templates/ was accidentally removed
        return send_file("index.html")

@socketio.on("kick_player")
def on_kick_player(data):
    room = data.get("room")
    host_id = data.get("hostId")
    target_id = data.get("targetId")

    if room not in rooms:
        return

    r = rooms[room]

    # فقط صاحب الغرفة يطرد
    if r.get("host") != host_id:
        emit("error_msg", "فقط قائد الغرفة يقدر يطرد")
        return

    idx = find_player(room, target_id)
    if idx < 0:
        return

    name = r["players"][idx]["name"]
    r["players"].pop(idx)

    if r["turn"] >= len(r["players"]):
        r["turn"] = 0

    r["log"].insert(0, f"🚫 تم طرد {name} من الغرفة")

    emit("kicked", {"room": room}, room=target_id)
    send_state(room)
@socketio.on("join")
def on_join(data):
    room = (data.get("room") or "ROOM1").strip().upper()
    name = (data.get("name") or "لاعب").strip()[:18]
    mode = data.get("mode", "solo")
    team_mode = data.get("teamMode", "auto")
    team_count = max(2, min(3, int(data.get("teamCount", 2) or 2)))
    selected_team = data.get("team", "A")

    if room not in rooms:
        rooms[room] = {
            "players": [], "deck": [], "discard": [],
            "turn": 0, "direction": 1, "color": None,
            "started": False, "log": [],
            "mode": mode, "teamMode": team_mode, "teamCount": team_count,
            "pendingDraw4": 0, "pendingDraw2": 0, "timeLimit": 30, "timeLeft": 0, "timer": None,
            "host": None
        }

    r = rooms[room]

    if r["started"]:
        emit("error_msg", "اللعبة بدأت، انتظر الجولة القادمة")
        return

    if len(r["players"]) >= 6:
        emit("error_msg", "الغرفة ممتلئة، الحد 6 لاعبين")
        return

    # first player locks options and becomes host
    pid = str(uuid.uuid4())
    if len(r["players"]) == 0:
        r["mode"] = mode
        r["teamMode"] = team_mode
        r["teamCount"] = team_count
        r["host"] = pid

    team = None
    if r.get("mode") == "teams":
        if r.get("teamMode") == "manual":
            allowed = TEAM_ORDER[:r.get("teamCount", 2)]
            team = selected_team if selected_team in allowed else allowed[0]
        else:
            team = assign_auto_team(r)

    join_room(room)
    r["players"].append({
        "id": pid, "sid": request.sid, "name": name,
        "team": team, "hand": [], "last": False, "wins": 0
    })

    r["log"].insert(0, f"{name} دخل الغرفة" + (f" - {TEAM_NAMES.get(team, team)}" if team else ""))

    emit("joined", {"room": room, "playerId": pid})
    send_state(room)

@socketio.on("chat")
def on_chat(data):
    room = data.get("room")
    player_id = data.get("playerId")
    text = (data.get("text") or "").strip()

    if room not in rooms or not text:
        return

    r = rooms[room]
    idx = find_player(room, player_id)
    if idx < 0:
        return

    name = r["players"][idx]["name"]
    r["log"].insert(0, f"💬 {name}: {text[:120]}")

    send_state(room)

@socketio.on("change_team")
def on_change_team(data):
    room = data.get("room")
    player_id = data.get("playerId")
    team = data.get("team")
    if room not in rooms:
        return
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
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    if r.get("host") != player_id:
        emit("error_msg", "فقط صاحب الغرفة يقدر يبدأ اللعبة ويحدد الوقت")
        return
    if len(r["players"]) < 2:
        emit("error_msg", "لازم لاعبين على الأقل")
        return
    try:
        limit = int(data.get("timeLimit", r.get("timeLimit", 30)) or 30)
    except Exception:
        limit = 30
    r["timeLimit"] = max(5, min(180, limit))

    r["deck"] = build_deck()
    r["discard"] = []
    r["direction"] = 1
    r["started"] = True
    r["color"] = None
    r["pendingDraw4"] = 0
    r["pendingDraw2"] = 0
    r["log"] = ["بدأت اللعبة"]

    # deal
    for p in r["players"]:
        p["hand"] = [r["deck"].pop() for _ in range(7)]
        p["last"] = False

    # first non-black
    first = r["deck"].pop()
    while first["c"] == "black":
        r["deck"].insert(0, first)
        random.shuffle(r["deck"])
        first = r["deck"].pop()

    r["discard"].append(first)
    r["color"] = first["c"]

    # host starts
    host_idx = next((i for i,p in enumerate(r["players"]) if p["id"] == r["host"]), 0)
    r["turn"] = host_idx

    start_timer(room)
    send_state(room)

@socketio.on("play")
def on_play(data):
    room = data.get("room")
    player_id = data.get("playerId")
    index = int(data.get("index", -1))
    chosen_color = data.get("color")

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

    if not is_allowed(r, card):
        if r.get("pendingDraw4", 0) > 0:
            emit("error_msg", "عليك +4: مسموح +4 أو عكس/تخطي بنفس اللون المطلوب، أو اسحب العقوبة")
        elif r.get("pendingDraw2", 0) > 0:
            emit("error_msg", "عليك رد عكس/تخطي بنفس اللون أو اضغط اسحب لتسحب كرتين")
        else:
            emit("error_msg", "هذا الكرت ما ينفع")
        return

    # play
    p["hand"].pop(index)
    r["discard"].append(card)

    if card["c"] == "black":
        if not chosen_color or chosen_color not in COLORS:
            emit("error_msg", "اختر لون")
            # put card back
            p["hand"].insert(index, card)
            r["discard"].pop()
            return
        r["color"] = chosen_color
    else:
        r["color"] = card["c"]

    r["log"].insert(0, f"{p['name']} رمى {card['n']}")

    # win
    if len(p["hand"]) == 0:
        p["wins"] = p.get("wins", 0) + 1
        r["started"] = False
        cancel_timer(r)
        if r.get("mode") == "teams" and p.get("team"):
            r["log"].insert(0, f"🏆 فاز {TEAM_NAMES.get(p['team'], p['team'])} بسبب {p['name']}")
        else:
            r["log"].insert(0, f"🏆 فاز {p['name']}")
        send_state(room)
        return

    apply_effect(r, card)

    for pp in r["players"]:
        if len(pp["hand"]) != 1:
            pp["last"] = False

    start_timer(room)
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

    amount4 = int(r.get("pendingDraw4", 0) or 0)
    amount2 = int(r.get("pendingDraw2", 0) or 0)
    if amount4 > 0:
        draw_to(r, idx, amount4)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب عقوبة {amount4}")
        r["pendingDraw4"] = 0

    elif amount2 > 0:
        draw_to(r, idx, amount2)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب عقوبة +2 عدد {amount2}")
        r["pendingDraw2"] = 0

    else:
        draw_to(r, idx, 1)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب كرت")
    r["turn"] = next_index(r)
    start_timer(room)
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


@socketio.on("leave_room")
def on_leave_room(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    idx = find_player(room, player_id)
    if idx < 0:
        return
    name = r["players"][idx]["name"]
    r["players"].pop(idx)
    if not r["players"]:
        cancel_timer(r)
        del rooms[room]
        emit("left_room", {"ok": True})
        return
    # إذا اللي خرج هو صاحب الغرفة
    if r.get("host") == player_id:
        new_host = r["players"][0]
        r["host"] = new_host["id"]
        r["log"].insert(0, f"{new_host['name']} أصبح قائد الغرفة 👑")
    if r["turn"] >= len(r["players"]):
        r["turn"] = 0
    r["log"].insert(0, f"{name} خرج من الغرفة")
    emit("left_room", {"ok": True})
    send_state(room)

@socketio.on("end_game")
def on_end_game(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    if r.get("host") != player_id:
        emit("error_msg", "فقط صاحب الغرفة يقدر ينهي اللعبة")
        return
    r["started"] = False
    r["pendingDraw4"] = 0
    r["pendingDraw2"] = 0
    cancel_timer(r)
    r["log"].insert(0, "تم إنهاء اللعبة بواسطة صاحب الغرفة")
    send_state(room)

@socketio.on("disconnect")
def on_disconnect():
    for room, r in list(rooms.items()):
        before = len(r["players"])
        r["players"] = [p for p in r["players"] if p["sid"] != request.sid]
        if len(r["players"]) != before:
            if not r["players"]:
                cancel_timer(r)
                del rooms[room]
            else:
                if r["turn"] >= len(r["players"]):
                    r["turn"] = 0
                r["log"].insert(0, "لاعب خرج من الغرفة")
                send_state(room)
            break

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
