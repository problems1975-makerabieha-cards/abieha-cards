from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, join_room, emit
import random
import os
import threading

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "abieha-final-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}

COLORS = ["red", "bluec", "greenc", "yellow"]
TEAM_ORDER = ["A", "B", "C"]
TEAM_NAMES = {"A": "الفريق الأزرق", "B": "الفريق البرتقالي", "C": "الفريق البنفسجي"}


@app.route("/")
def index():
    return send_file("templates/index.html")


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

    for _ in range(2):
        deck.append({"c": "black", "n": "تبديل"})

    random.shuffle(deck)
    return deck


def find_player(room, player_id):
    if room not in rooms:
        return -1

    for i, p in enumerate(rooms[room].get("players", [])):
        if (p.get("id") or p.get("sid")) == player_id:
            return i

    return -1


def find_spectator(room, spectator_id):
    if room not in rooms:
        return -1

    for i, s in enumerate(rooms[room].get("spectators", [])):
        if (s.get("id") or s.get("sid")) == spectator_id:
            return i

    return -1


def next_index(r):
    if not r.get("players"):
        return 0
    return (r["turn"] + r["direction"] + len(r["players"])) % len(r["players"])


def draw_to(r, idx, count):
    for _ in range(count):
        if not r["deck"] and len(r["discard"]) > 1:
            keep = r["discard"].pop()
            r["deck"] = r["discard"]
            random.shuffle(r["deck"])
            r["discard"] = [keep]

        if r["deck"] and 0 <= idx < len(r["players"]):
            r["players"][idx]["hand"].append(r["deck"].pop())


def card_points(card):
    n = card.get("n")
    if n in ["عكس", "تخطي", "+2"]:
        return 20
    if n == "لون":
        return 40
    if n == "+4":
        return 50
    if n == "تبديل":
        return 50
    try:
        return int(n)
    except Exception:
        return 0


def team_scores(r):
    scores = {"A": 0, "B": 0, "C": 0}
    for p in r.get("players", []):
        t = p.get("team")
        if t in scores:
            scores[t] += p.get("wins", 0)
    return scores


def public_state(room):
    r = rooms[room]
    return {
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
        "teamScores": team_scores(r),
        "hostId": r.get("host"),
        "host": r.get("host"),
        "players": [
            {
                "id": p.get("id") or p.get("sid"),
                "name": p.get("name", "لاعب"),
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
                "id": s.get("id") or s.get("sid"),
                "name": s.get("name", "مشاهد"),
                "avatar": s.get("avatar", "auto"),
            }
            for s in r.get("spectators", [])
        ],
        "log": r.get("log", [])[-80:],
    }


def send_state(room):
    if room not in rooms:
        return

    r = rooms[room]
    base = public_state(room)

    for p in r.get("players", []):
        sid = p.get("sid")
        if not sid:
            continue

        payload = dict(base)
        payload["myId"] = p.get("id") or sid
        payload["myHand"] = p.get("hand", [])
        payload["role"] = "player"
        socketio.emit("state", payload, room=sid)

    for s in r.get("spectators", []):
        sid = s.get("sid")
        if not sid:
            continue

        payload = dict(base)
        payload["myId"] = s.get("id") or sid
        payload["myHand"] = []
        payload["role"] = "spectator"
        socketio.emit("state", payload, room=sid)


def is_allowed(r, card):
    top = r["discard"][-1]

    if r.get("pendingDraw4", 0) > 0:
        return (
            card["n"] == "+4"
            or card["n"] == top["n"]
            or (card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"])
        )

    if r.get("pendingDraw2", 0) > 0:
        return (
            card["n"] == "+4"
            or card["n"] == top["n"]
            or (card["n"] in ["+2", "عكس", "تخطي"] and card["c"] == r["color"])
        )

    return (
        card["c"] == "black"
        or card["c"] == r["color"]
        or card["n"] == top["n"]
        or card["n"] == "تبديل"
    )


def swap_random_two_hands(r):
    if len(r["players"]) < 2:
        return
    p1, p2 = random.sample(r["players"], 2)
    p1["hand"], p2["hand"] = p2["hand"], p1["hand"]
    r["log"].insert(0, f"🔀 تبديل: {p1['name']} ↔ {p2['name']}")


def apply_effect(r, card):

    # كرت التبديل
    if card["n"] == "تبديل":
        if int(r.get("pendingDraw2", 0)) == 0 and int(r.get("pendingDraw4", 0)) == 0:
            swap_random_two_hands(r)

        r["pendingDraw2"] = 0
        r["pendingDraw4"] = 0
        r["turn"] = next_index(r)
        return

    # +2 يتراكم
    if card["n"] == "+2":
        r["pendingDraw2"] = int(r.get("pendingDraw2", 0)) + 2
        r["pendingDraw4"] = 0
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw2']}")
        r["turn"] = next_index(r)
        return

    # +4 يتراكم
    if card["n"] == "+4":
        r["pendingDraw4"] = int(r.get("pendingDraw4", 0)) + 4
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw4']}")
        r["turn"] = next_index(r)
        return

    # عكس / تخطي أثناء العقوبة: يمرر العقوبة ولا يصفرها
    if card["n"] in ["عكس", "تخطي"]:

        if r.get("pendingDraw2", 0) > 0 or r.get("pendingDraw4", 0) > 0:

            if card["n"] == "عكس":
                r["direction"] *= -1
                r["log"].insert(0, "↺ عكس أثناء العقوبة — العقوبة مستمرة")

            if card["n"] == "تخطي":
                r["log"].insert(0, "⊘ تخطي أثناء العقوبة — العقوبة مستمرة")

            # إذا لاعبين فقط: ترجع العقوبة على اللاعب الثاني
            if len(r["players"]) == 2:
                return

            # أكثر من لاعبين: تنتقل حسب الاتجاه
            r["turn"] = next_index(r)

            # التخطي يتجاوز لاعب إضافي
            if card["n"] == "تخطي":
                r["turn"] = next_index(r)

            return

        # عكس / تخطي بدون عقوبة
        r["pendingDraw2"] = 0
        r["pendingDraw4"] = 0

        if card["n"] == "عكس":
            r["direction"] *= -1
            r["log"].insert(0, "عكس اتجاه اللعب")

            if len(r["players"]) == 2:
                return

            r["turn"] = next_index(r)
            return

        if card["n"] == "تخطي":
            r["log"].insert(0, "تم تخطي اللاعب التالي")

            if len(r["players"]) == 2:
                return

            r["turn"] = next_index(r)
            r["turn"] = next_index(r)
            return

    # الكروت العادية تصفر العقوبة فقط إذا ماكو عقوبة
    r["pendingDraw2"] = 0
    r["pendingDraw4"] = 0
    r["turn"] = next_index(r)

def cancel_timer(r):
    t = r.get("timer")
    if t:
        try:
            t.cancel()
        except Exception:
            pass
    r["timer"] = None


def handle_timeout(room):
    r = rooms.get(room)
    if not r or not r.get("started") or not r.get("players"):
        return

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
        draw_to(r, idx, 1)
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته ⏱️ وسحب كرت عقوبة")

    r["turn"] = next_index(r)
    start_timer(room)
    send_state(room)


def start_timer(room):
    r = rooms.get(room)
    if not r:
        return

    cancel_timer(r)
    r["timeLeft"] = r.get("timeLimit", 30)
    send_state(room)

    def tick():
        rr = rooms.get(room)
        if not rr or not rr.get("started"):
            return

        rr["timeLeft"] = max(0, rr.get("timeLeft", 0) - 1)
        send_state(room)

        if rr["timeLeft"] <= 0:
            handle_timeout(room)
            return

        rr["timer"] = threading.Timer(1, tick)
        rr["timer"].daemon = True
        rr["timer"].start()

    r["timer"] = threading.Timer(1, tick)
    r["timer"].daemon = True
    r["timer"].start()


def reset_scores_and_game(r):
    cancel_timer(r)
    r["deck"] = []
    r["discard"] = []
    r["turn"] = 0
    r["direction"] = 1
    r["color"] = None
    r["started"] = False
    r["pendingDraw4"] = 0
    r["pendingDraw2"] = 0
    r["timeLeft"] = 0
    r["gameOver"] = False
    r["finalResults"] = None
    for p in r.get("players", []):
        p["hand"] = []
        p["last"] = False
        p["wins"] = 0
        p["score"] = 0


def set_final_results(r, winner):
    limit = r.get("scoreLimit", 500)
    losers = [pp for pp in r["players"] if pp.get("score", 0) >= limit]
    if not losers:
        return False

    loser_ids = {pp["id"] for pp in losers}
    candidates = [pp for pp in r["players"] if pp["id"] not in loser_ids]
    winner_player = min(candidates, key=lambda x: x.get("score", 0), default=winner)

    r["finalResults"] = {
        "winner": winner_player["name"],
        "losers": [pp["name"] for pp in losers],
        "players": [
            {"name": pp["name"], "score": pp.get("score", 0), "wins": pp.get("wins", 0)}
            for pp in sorted(r["players"], key=lambda x: x.get("score", 0))
        ],
    }

    r["gameOver"] = True
    r["started"] = False
    cancel_timer(r)
    r["log"].insert(0, f"🏆 الفائز النهائي: {winner_player['name']}")
    for loser in losers:
        r["log"].insert(0, f"💀 {loser['name']} وصل {limit} وخسر اللعبة")
    return True


@socketio.on("join")
def on_join(data):
    try:
        data = data or {}
        room = (data.get("room") or "ROOM1").strip().upper()
        name = (data.get("name") or "لاعب").strip()[:18]
        mode = data.get("mode", "solo")
        team_mode = data.get("teamMode", "auto")

        try:
            team_count = int(data.get("teamCount", 2) or 2)
        except Exception:
            team_count = 2

        team_count = max(2, min(3, team_count))
        selected_team = data.get("team", "A")
        avatar = data.get("avatar", "auto")
        role = data.get("role", "spectator")

        if not name:
            name = "لاعب"

        if room not in rooms:
            rooms[room] = {
                "players": [],
                "spectators": [],
                "deck": [],
                "discard": [],
                "turn": 0,
                "direction": 1,
                "color": None,
                "started": False,
                "log": [],
                "mode": mode,
                "teamMode": team_mode,
                "teamCount": team_count,
                "pendingDraw4": 0,
                "pendingDraw2": 0,
                "timeLimit": 30,
                "timeLeft": 0,
                "scoreLimit": 500,
                "gameOver": False,
                "finalResults": None,
                "timer": None,
                "host": None,
            }

        r = rooms[room]
        join_room(room)

        if role == "player":
            try:
                seat = int(data.get("seat", 0) or 0)
            except Exception:
                seat = 0

            if any(p.get("seat") == seat for p in r.get("players", [])):
                emit("error_msg", "هذا المقعد محجوز")
                return

            player_id = request.sid
            r["players"].append({
                "id": player_id,
                "sid": request.sid,
                "name": name,
                "hand": [],
                "score": 0,
                "wins": 0,
                "last": False,
                "team": selected_team,
                "avatar": avatar,
                "seat": seat,
                "connected": True,
            })

            if r.get("host") is None:
                r["host"] = player_id

            r["log"].insert(0, f"{name} جلس على المقعد {seat + 1}")

        else:
            spectator_id = request.sid
            r["spectators"].append({
                "id": spectator_id,
                "sid": request.sid,
                "name": name,
                "avatar": avatar,
                "connected": True,
            })
            r["log"].insert(0, f"{name} دخل كمشاهد 👀")

        emit("joined", {"playerId": request.sid, "room": room})
        send_state(room)

    except Exception as e:
        print("JOIN ERROR:", repr(e))
        emit("error_msg", str(e))


@socketio.on("sit_seat")
def on_sit_seat(data):
    room = data.get("room")
    player_id = data.get("playerId")

    try:
        seat = int(data.get("seat", 0))
    except Exception:
        seat = 0

    if room not in rooms:
        return

    r = rooms[room]

    if r.get("started"):
        emit("error_msg", "لا يمكن الجلوس بعد بداية اللعبة")
        return

    if any(p.get("seat") == seat for p in r.get("players", [])):
        emit("error_msg", "هذا المقعد محجوز")
        return

    sidx = find_spectator(room, player_id)
    if sidx < 0:
        emit("error_msg", "أنت جالس بالفعل أو غير موجود")
        return

    spectator = r["spectators"].pop(sidx)

    r["players"].append({
        "id": spectator["id"],
        "sid": spectator["sid"],
        "name": spectator["name"],
        "avatar": spectator.get("avatar", "auto"),
        "seat": seat,
        "hand": [],
        "score": 0,
        "wins": 0,
        "last": False,
        "team": "A",
        "connected": True,
    })

    if r.get("host") is None:
        r["host"] = spectator["id"]

    r["log"].insert(0, f"{spectator['name']} جلس على المقعد {seat + 1}")
    send_state(room)


@socketio.on("start")
def on_start(data):
    room = data.get("room")
    player_id = data.get("playerId")

    if room not in rooms:
        return

    r = rooms[room]

    if r.get("host") != player_id:
        emit("error_msg", "فقط صاحب الغرفة يقدر يبدأ اللعبة")
        return

    if len(r.get("players", [])) < 2:
        emit("error_msg", "لازم لاعبين على الأقل يجلسون على الطاولة")
        return

    if r.get("gameOver"):
        reset_scores_and_game(r)

    try:
        limit = int(data.get("timeLimit", r.get("timeLimit", 30)) or 30)
    except Exception:
        limit = 30
    r["timeLimit"] = max(5, min(180, limit))

    try:
        score_limit = int(data.get("scoreLimit", r.get("scoreLimit", 500)) or 500)
    except Exception:
        score_limit = 500
    r["scoreLimit"] = score_limit if score_limit in [200, 300, 400, 500] else 500

    r["deck"] = build_deck()
    r["discard"] = []
    r["direction"] = 1
    r["started"] = True
    r["color"] = None
    r["pendingDraw4"] = 0
    r["pendingDraw2"] = 0
    r["gameOver"] = False
    r["finalResults"] = None
    r["log"].insert(0, "بدأت اللعبة")

    for p in r["players"]:
        p["hand"] = [r["deck"].pop() for _ in range(7)]
        p["last"] = False

    first = r["deck"].pop()
    while first["c"] == "black" and first["n"] == "لون":
        r["deck"].insert(0, first)
        random.shuffle(r["deck"])
        first = r["deck"].pop()

    r["discard"].append(first)
    r["color"] = random.choice(COLORS) if first["c"] == "black" else first["c"]

    if first["n"] == "+2":
        r["pendingDraw2"] = 2
        r["log"].insert(0, "🔥 بداية: +2 — اللاعب الأول يرد أو يسحب")
    elif first["n"] == "+4":
        r["pendingDraw4"] = 4
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"🔥 بداية: +4 — اللون {r['color']}")

    host_idx = next((i for i, p in enumerate(r["players"]) if p["id"] == r["host"]), 0)
    r["turn"] = host_idx

    start_timer(room)
    send_state(room)


@socketio.on("play")
def on_play(data):
    room = data.get("room")
    player_id = data.get("playerId")

    try:
        index = int(data.get("index", -1))
    except Exception:
        index = -1

    chosen_color = data.get("color")

    if room not in rooms:
        return

    r = rooms[room]
    idx = find_player(room, player_id)

    if idx < 0:
        emit("error_msg", "أنت مشاهد فقط")
        return

    if not r.get("started"):
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
        emit("error_msg", "هذا الكرت ما ينفع")
        return

    p["hand"].pop(index)
    r["discard"].append(card)

    if card["c"] == "black":
        if not chosen_color or chosen_color not in COLORS:
            emit("error_msg", "اختر لون")
            p["hand"].insert(index, card)
            r["discard"].pop()
            return
        r["color"] = chosen_color
    else:
        r["color"] = card["c"]

    r["log"].insert(0, f"{p['name']} رمى {card['n']}")

    if len(p["hand"]) == 0:
        winner = p
        winner["wins"] = winner.get("wins", 0) + 1
        winner["score"] = max(0, winner.get("score", 0) - 10)

        for i, pp in enumerate(r["players"]):
            if i == idx:
                continue
            add_score = sum(card_points(c) for c in pp["hand"])
            pp["score"] = pp.get("score", 0) + add_score
            r["log"].insert(0, f"📊 {pp['name']} انضاف عليه {add_score} نقطة — المجموع {pp['score']}")

        r["started"] = False
        cancel_timer(r)
        r["log"].insert(0, f"🏆 فاز {winner['name']} وخصم 10 نقاط")
        set_final_results(r, winner)
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
        emit("error_msg", "أنت مشاهد فقط")
        return

    if not r.get("started"):
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
        r["pendingDraw2"] = 0
    elif amount2 > 0:
        draw_to(r, idx, amount2)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب عقوبة {amount2}")
        r["pendingDraw2"] = 0
        r["pendingDraw4"] = 0
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

    if idx < 0:
        emit("error_msg", "أنت مشاهد فقط")
        return

    if len(r["players"][idx]["hand"]) == 1:
        r["players"][idx]["last"] = True
        r["log"].insert(0, f"{r['players'][idx]['name']} قال: كرت أخير")
    else:
        emit("error_msg", "تقدر تضغط كرت أخير لما يبقى عندك كرت واحد")

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

    if idx >= 0:
        p = r["players"][idx]
    else:
        sidx = find_spectator(room, player_id)
        if sidx < 0:
            return
        p = r["spectators"][sidx]

    r["log"].append({
        "type": "chat",
        "id": player_id,
        "name": p.get("name", "لاعب"),
        "avatar": p.get("avatar", "💬"),
        "text": text
    })

    send_state(room)


@socketio.on("kick_player")
def on_kick_player(data):
    room = data.get("room")
    host_id = data.get("hostId")
    target_id = data.get("targetId")

    if room not in rooms:
        return

    r = rooms[room]

    if r.get("host") != host_id:
        emit("error_msg", "فقط قائد الغرفة يقدر يطرد")
        return

    idx = find_player(room, target_id)
    if idx >= 0:
        name = r["players"][idx]["name"]
        sid = r["players"][idx].get("sid")
        r["players"].pop(idx)

        if r["turn"] >= len(r["players"]):
            r["turn"] = 0

        r["log"].insert(0, f"🚫 تم طرد {name} من الغرفة")
        emit("kicked", {"room": room}, room=sid)
        send_state(room)
        return

    sidx = find_spectator(room, target_id)
    if sidx >= 0:
        name = r["spectators"][sidx]["name"]
        sid = r["spectators"][sidx].get("sid")
        r["spectators"].pop(sidx)

        r["log"].insert(0, f"🚫 تم طرد المشاهد {name}")
        emit("kicked", {"room": room}, room=sid)
        send_state(room)


@socketio.on("leave_room")
def on_leave_room(data):
    room = data.get("room")
    player_id = data.get("playerId")

    if room not in rooms:
        emit("left_room", {"ok": True})
        return

    r = rooms[room]
    idx = find_player(room, player_id)

    if idx >= 0:
        name = r["players"][idx]["name"]
        r["players"].pop(idx)
        r["log"].insert(0, f"{name} خرج من الغرفة")

        if r.get("host") == player_id:
            if r["players"]:
                r["host"] = r["players"][0]["id"]
                r["log"].insert(0, f"{r['players'][0]['name']} أصبح قائد الغرفة 👑")
            else:
                r["host"] = None

        if r["turn"] >= len(r["players"]):
            r["turn"] = 0
    else:
        sidx = find_spectator(room, player_id)
        if sidx >= 0:
            name = r["spectators"][sidx]["name"]
            r["spectators"].pop(sidx)
            r["log"].insert(0, f"{name} خرج من الغرفة")

    emit("left_room", {"ok": True})

    if not r.get("players") and not r.get("spectators"):
        cancel_timer(r)
        del rooms[room]
        return

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
        player = next((p for p in r.get("players", []) if p.get("sid") == request.sid), None)
        if player:
            player["connected"] = False
            player["sid"] = None
            r["log"].insert(0, f"{player['name']} انقطع اتصاله")
            send_state(room)
            break

        spectator = next((s for s in r.get("spectators", []) if s.get("sid") == request.sid), None)
        if spectator:
            spectator["connected"] = False
            spectator["sid"] = None
            r["log"].insert(0, f"{spectator['name']} انقطع اتصاله")
            send_state(room)
            break


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
