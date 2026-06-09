from flask import Flask, request, send_file
from flask_socketio import SocketIO, join_room, emit
import random, os, threading
import json, urllib.request

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "abieha-final-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}
puzzle_rooms = {}
letters_rooms = {}

COLORS = ["red", "bluec", "greenc", "yellow"]
TEAM_ORDER = ["A", "B", "C"]


def get_random_puzzle_image(category="general"):

    if category == "random":
        return f"https://picsum.photos/seed/{random.randint(1000,999999)}/900"

    allowed = {
        "animals",
        "football",
        "actors",
        "artists",
        "cartoon",
        "products",
        "flags",
        "plants",
        "general"
    }

    category = category if category in allowed else "general"

    folder = os.path.join("static", "puzzle-images", category)

    if not os.path.exists(folder):
        return f"https://picsum.photos/seed/{random.randint(1000,999999)}/900"

    files = [
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    if not files:
        return f"https://picsum.photos/seed/{random.randint(1000,999999)}/900"

    filename = random.choice(files)
    return f"/static/puzzle-images/{category}/{filename}"


@app.route("/")
def home():
    return send_file("templates/home.html")


@app.route("/uno")
def uno():
    return send_file("templates/index.html")


@app.route("/puzzle")
def puzzle():
    return send_file("templates/puzzle.html")


@app.route("/letters")
def letters():
    return send_file("templates/letters.html")


@app.route("/categories")
def categories_game():
    return send_file("templates/categories.html")


@socketio.on("puzzle_join")
def puzzle_join(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    name = str(data.get("name", "لاعب")).strip()
    avatar = str(data.get("avatar", "🎮"))
    pid = str(data.get("pid") or request.sid).strip()

    join_room("puzzle_" + room)

    if room not in puzzle_rooms:
        puzzle_rooms[room] = {
            "players": [],
            "winner": None,
            "winnerTime": 0,
            "size": 4,
            "imageUrl": "https://picsum.photos/900?random=77",
            "order": [],
            "status": "waiting",
            "host": pid,
            "hostSid": request.sid,
            "round": 0,
            "roundLimit": 3,
            "finalWinner": None
        }

    r = puzzle_rooms[room]
    players = r["players"]
    display_name = f"{avatar} {name}"

    old = next((p for p in players if p.get("pid") == pid), None)

    if old:
        old["sid"] = request.sid
        old["name"] = display_name
        old["online"] = True
    else:
        players.append({
            "pid": pid,
            "sid": request.sid,
            "name": display_name,
            "progress": 0,
            "time": 0,
            "finished": False,
            "wins": 0,
            "score": 0,
            "roundScore": 0,
            "online": True
        })

    if not r.get("host"):
        r["host"] = pid
        r["hostSid"] = request.sid

    if r.get("host") == pid:
        r["hostSid"] = request.sid

    emit("puzzle_joined", {"pid": pid, "room": room})
    emit("puzzle_state", r, room="puzzle_" + room)


@socketio.on("puzzle_progress")
def puzzle_progress(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    pid = str(data.get("pid", "")).strip()

    if room not in puzzle_rooms:
        return

    r = puzzle_rooms[room]

    for p in r["players"]:
        if p.get("pid") == pid or p.get("sid") == request.sid:
            p["sid"] = request.sid
            p["online"] = True
            p["progress"] = int(data.get("progress", 0))
            p["time"] = int(data.get("time", 0))
            break

    emit("puzzle_state", r, room="puzzle_" + room)


@socketio.on("puzzle_finish")
def puzzle_finish(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    pid = str(data.get("pid", "")).strip()

    if room not in puzzle_rooms:
        return

    r = puzzle_rooms[room]
    time = int(data.get("time", 0))

    if r.get("winner") is None:
        round_winner = None

        for p in r["players"]:
            if p.get("pid") == pid or p.get("sid") == request.sid:
                p["sid"] = request.sid
                p["online"] = True
                p["progress"] = 100
                p["time"] = time
                p["finished"] = True
                p["wins"] = int(p.get("wins", 0)) + 1
                round_winner = p
                break

        if round_winner:
            for pp in r["players"]:
                pct = int(pp.get("progress", 0) or 0)
                pct = max(0, min(100, pct))
                pp["roundScore"] = pct
                pp["score"] = int(pp.get("score", 0) or 0) + pct

            r["winner"] = round_winner["name"]
            r["winnerTime"] = time
            r["status"] = "round_finished"

            if int(r.get("round", 0)) >= int(r.get("roundLimit", 3)):
                r["status"] = "game_finished"
                best = sorted(
                    r["players"],
                    key=lambda x: (
                        int(x.get("wins", 0) or 0),
                        int(x.get("score", 0) or 0),
                        int(x.get("roundScore", 0) or 0),
                        -int(x.get("time", 999999) or 999999)
                    ),
                    reverse=True
                )
                r["finalWinner"] = best[0]["name"] if best else round_winner["name"]

    emit("puzzle_state", r, room="puzzle_" + room)


@socketio.on("puzzle_reset")
def puzzle_reset(data):
    room = str(data.get("room", "ROOM1")).strip().upper()

    if room not in puzzle_rooms:
        return

    if puzzle_rooms[room].get("hostSid") != request.sid:
        return

    r = puzzle_rooms[room]
    r["winner"] = None
    r["winnerTime"] = 0
    r["status"] = "waiting"
    r["order"] = []
    r["round"] = 0
    r["finalWinner"] = None

    for p in r["players"]:
        p["progress"] = 0
        p["time"] = 0
        p["finished"] = False
        p["wins"] = 0
        p["score"] = 0
        p["roundScore"] = 0

    emit("puzzle_reset_done", {}, room="puzzle_" + room)
    emit("puzzle_state", r, room="puzzle_" + room)


@socketio.on("puzzle_start")
def puzzle_start(data):
    room = str(data.get("room", "ROOM1")).strip().upper()

    if room not in puzzle_rooms:
        return

    if puzzle_rooms[room].get("hostSid") != request.sid:
        return

    r = puzzle_rooms[room]

    if r.get("status") == "game_finished":
        r["round"] = 0
        r["finalWinner"] = None
        for p in r["players"]:
            p["wins"] = 0
            p["score"] = 0
            p["roundScore"] = 0

    next_round = int(r.get("round", 0)) + 1

    r["winner"] = None
    r["winnerTime"] = 0
    r["size"] = int(data.get("size", 4))

    categories = data.get("categories", ["general"])

    if not isinstance(categories, list) or not categories:
        categories = ["general"]

    category = random.choice(categories)
    r["imageUrl"] = get_random_puzzle_image(category)
    r["category"] = category

    r["order"] = data.get("order", [])
    r["status"] = "started"
    r["roundLimit"] = int(data.get("roundLimit", r.get("roundLimit", 3)))
    r["round"] = next_round
    r["category"] = category

    for p in r["players"]:
        p["progress"] = 0
        p["time"] = 0
        p["finished"] = False
        p["roundScore"] = 0

    emit("puzzle_started", r, room="puzzle_" + room)
    emit("puzzle_state", r, room="puzzle_" + room)

@socketio.on("puzzle_image")
def puzzle_image(data):
    room = str(data.get("room", "ROOM1")).strip().upper()

    if room not in puzzle_rooms:
        return

    if puzzle_rooms[room].get("hostSid") != request.sid:
        return

    image_url = data.get("imageUrl")

    if not image_url:
        return

    puzzle_rooms[room]["imageUrl"] = image_url

    emit(
        "puzzle_image_changed",
        {"imageUrl": image_url},
        room="puzzle_" + room
    )

    emit(
        "puzzle_state",
        puzzle_rooms[room],
        room="puzzle_" + room
    )


@socketio.on("puzzle_leave")
def puzzle_leave(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    pid = str(data.get("pid", "")).strip()

    if room not in puzzle_rooms:
        emit("puzzle_left", {"ok": True}, room=request.sid)
        return

    r = puzzle_rooms[room]

    # خروج عادي: فقط اللاعب نفسه ينحذف
    r["players"] = [
        p for p in r.get("players", [])
        if p.get("pid") != pid
    ]

    # إذا صاحب الروم خرج، ننقل القيادة لأول لاعب موجود
    if r.get("host") == pid:
        if r.get("players"):
            r["host"] = r["players"][0].get("pid")
            r["hostSid"] = r["players"][0].get("sid")
        else:
            del puzzle_rooms[room]
            emit("puzzle_left", {"ok": True}, room=request.sid)
            return

    emit("puzzle_left", {"ok": True}, room=request.sid)
    emit("puzzle_state", r, room="puzzle_" + room)


@socketio.on("puzzle_kick")
def puzzle_kick(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    target_pid = str(data.get("targetPid", "")).strip()

    if room not in puzzle_rooms:
        return

    r = puzzle_rooms[room]

    if r.get("hostSid") != request.sid:
        return

    if not target_pid or target_pid == r.get("host"):
        return

    target = next((p for p in r.get("players", []) if p.get("pid") == target_pid), None)
    if not target:
        return

    target_sid = target.get("sid")
    r["players"] = [p for p in r.get("players", []) if p.get("pid") != target_pid]

    if target_sid:
        emit("puzzle_kicked", {"room": room}, room=target_sid)

    emit("puzzle_state", r, room="puzzle_" + room)


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
        if p.get("id") == player_id:
            return i
    return -1


def find_spectator(room, spectator_id):
    if room not in rooms:
        return -1
    for i, s in enumerate(rooms[room].get("spectators", [])):
        if s.get("id") == spectator_id:
            return i
    return -1


def cancel_timer(r):
    t = r.get("timer")
    if t:
        try:
            t.cancel()
        except Exception:
            pass
    r["timer"] = None


def host_name(r):
    hid = r.get("host")
    for p in r.get("players", []):
        if p.get("id") == hid:
            return p.get("name", "القائد")
    for s in r.get("spectators", []):
        if s.get("id") == hid:
            return s.get("name", "القائد")
    return None


def transfer_host(room, r):
    alive_ids = {p.get("id") for p in r.get("players", [])} | {s.get("id") for s in r.get("spectators", [])}
    r["trustedHosts"] = [x for x in r.get("trustedHosts", []) if x in alive_ids]

    for tid in r.get("trustedHosts", []):
        for p in r.get("players", []):
            if p.get("id") == tid:
                r["host"] = p["id"]
                r["log"].insert(0, f"👑 القائد الجديد: {p['name']}")
                return

    if r.get("players"):
        r["host"] = r["players"][0]["id"]
        r["log"].insert(0, f"👑 القائد الجديد: {r['players'][0]['name']}")
        return

    if r.get("spectators"):
        r["host"] = r["spectators"][0]["id"]
        r["log"].insert(0, f"👑 القائد المؤقت: {r['spectators'][0]['name']}")
        return

    r["host"] = None


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
    if n in ["لون", "+4", "تبديل"]:
        return 50
    try:
        return int(n)
    except Exception:
        return 0


def team_scores(r):
    return {"A": 0, "B": 0, "C": 0}


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
        "hostName": host_name(r),
        "trustedHosts": r.get("trustedHosts", []),

        "players": [
            {
                "id": p.get("id"),
                "name": p.get("name", "لاعب"),
                "team": p.get("team", "A"),
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
        if sid:
            payload = dict(base)
            payload["myId"] = p.get("id")
            payload["myHand"] = p.get("hand", [])
            payload["role"] = "player"
            socketio.emit("state", payload, room=sid)

    for s in r.get("spectators", []):
        sid = s.get("sid")
        if sid:
            payload = dict(base)
            payload["myId"] = s.get("id")
            payload["myHand"] = []
            payload["role"] = "spectator"
            socketio.emit("state", payload, room=sid)


def is_allowed(r, card):
    top = r["discard"][-1]

    # أثناء عقوبة +4
    if r.get("pendingDraw4", 0) > 0:
        return (
            card["n"] == "+4"
            or card["n"] == top["n"]
            or (card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"])
        )

    # أثناء عقوبة +2
    if r.get("pendingDraw2", 0) > 0:
        return (
            card["n"] == "+2"
            or card["n"] == "+4"
            or card["n"] == top["n"]
            or (card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"])
        )

    # اللعب الطبيعي
    return (
        card["c"] == "black"
        or card["c"] == r["color"]
        or card["n"] == top["n"]
        or card["n"] == "تبديل"
    )

def swap_random_two_hands(r):
    if len(r.get("players", [])) < 2:
        return

    p1, p2 = random.sample(r["players"], 2)

    p1["hand"], p2["hand"] = p2["hand"], p1["hand"]

    r["log"].insert(0, f"🔀 تم تبديل أوراق {p1['name']} مع {p2['name']}")

def apply_effect(r, card):

    # كرت التبديل: يبدل أوراق أي لاعبين عشوائي فقط
    # لا يغير اللون ولا يتحول إلى +4 ولا يسحب أوراق
    if card["n"] == "تبديل":
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

    # +4 يتراكم ويغير اللون من on_play حسب اختيار اللاعب
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

            # إذا لاعبين فقط: نفس اللاعب يلعب مرة ثانية
            if len(r["players"]) == 2:
                return

            r["turn"] = next_index(r)

            if card["n"] == "تخطي":
                r["turn"] = next_index(r)

            return

        # عكس / تخطي بدون عقوبة
        r["pendingDraw2"] = 0
        r["pendingDraw4"] = 0

        if card["n"] == "عكس":
            r["direction"] *= -1
            r["log"].insert(0, "عكس اتجاه اللعب")

            # إذا لاعبين فقط: نفس اللاعب يلعب مرة ثانية
            if len(r["players"]) == 2:
                return

            r["turn"] = next_index(r)
            return

        if card["n"] == "تخطي":
            r["log"].insert(0, "تم تخطي اللاعب التالي")

            # إذا لاعبين فقط: نفس اللاعب يلعب مرة ثانية
            if len(r["players"]) == 2:
                return

            r["turn"] = next_index(r)
            r["turn"] = next_index(r)
            return

    # كرت تغيير اللون فقط: اللون يتغير في on_play ثم ينتقل الدور
    # الكروت العادية
    r["pendingDraw2"] = 0
    r["pendingDraw4"] = 0
    r["turn"] = next_index(r)


def handle_timeout(room):
    r = rooms.get(room)
    if not r or not r.get("started") or not r.get("players"):
        return

    idx = r.get("turn", 0)
    if idx >= len(r["players"]):
        r["turn"] = 0
        idx = 0

    amount4 = int(r.get("pendingDraw4", 0) or 0)
    amount2 = int(r.get("pendingDraw2", 0) or 0)

    if amount4 > 0:
        total = amount4 + 1
        draw_to(r, idx, total)
        r["pendingDraw4"] = 0
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته وسحب {total}")
    elif amount2 > 0:
        total = amount2 + 1
        draw_to(r, idx, total)
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته وسحب {total}")
    else:
        draw_to(r, idx, 1)
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته وسحب كرت")

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


def reset_room_if_empty(room, r):
    if not r.get("players") and not r.get("spectators"):
        cancel_timer(r)
        del rooms[room]
        return True
    return False


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
                "trustedHosts": [],
            }

        r = rooms[room]
        join_room(room)

        old_player = next((p for p in r["players"] if p.get("id") == request.sid), None)
        old_spectator = next((s for s in r["spectators"] if s.get("id") == request.sid), None)

        if not old_player and not old_spectator:
            spectator_id = request.sid
            r["spectators"].append({
                "id": spectator_id,
                "sid": request.sid,
                "name": name,
                "avatar": avatar,
                "team": selected_team,
            })

            if r.get("host") is None:
                r["host"] = spectator_id
                r["log"].insert(0, f"👑 {name} أصبح قائد الغرفة")

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

    if seat < 0 or seat > 5:
        emit("error_msg", "المقعد غير صحيح")
        return

    if any(p.get("seat") == seat for p in r.get("players", [])):
        emit("error_msg", "هذا المقعد محجوز")
        return

    if find_player(room, player_id) >= 0:
        emit("error_msg", "أنت جالس بالفعل")
        return

    sidx = find_spectator(room, player_id)
    if sidx < 0:
        emit("error_msg", "لم يتم العثور عليك كمشاهد")
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
        "team": spectator.get("team", "A"),
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
        emit("error_msg", f"فقط قائد الغرفة يقدر يبدأ اللعبة — القائد: {host_name(r) or '-'}")
        return

    if len(r.get("players", [])) < 2:
        emit("error_msg", "لازم لاعبين على الأقل يجلسون على الطاولة")
        return

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

    # +4 وكرت اللون فقط يحتاجون اختيار لون.
    # كرت تبديل لا يحتاج لون ولا يغير اللون الحالي.
    if card["n"] in ["+4", "لون"]:
        if not chosen_color or chosen_color not in COLORS:
            emit("error_msg", "اختر لون")
            p["hand"].insert(index, card)
            r["discard"].pop()
            return
        r["color"] = chosen_color
    elif card["c"] != "black":
        r["color"] = card["c"]

    r["log"].insert(0, f"{p['name']} رمى {card['n']}")

    if len(p["hand"]) == 0:
        winner = p
        winner["wins"] = winner.get("wins", 0) + 1

        for i, pp in enumerate(r["players"]):
            if i == idx:
                continue

            add_score = sum(card_points(c) for c in pp["hand"])
            pp["score"] = pp.get("score", 0) + add_score
            r["log"].insert(0, f"📊 {pp['name']} انضاف عليه {add_score} نقطة — المجموع {pp['score']}")

        r["log"].insert(0, f"🏆 فاز {winner['name']}")

        score_limit = int(r.get("scoreLimit", 500) or 500)
        losers = [pp for pp in r["players"] if pp.get("score", 0) >= score_limit]

        if losers:
            loser_ids = {pp["id"] for pp in losers}
            candidates = [pp for pp in r["players"] if pp["id"] not in loser_ids]
            final_winner = min(candidates, key=lambda x: x.get("score", 0), default=winner)

            r["started"] = False
            r["gameOver"] = True
            r["finalResults"] = {
                "winner": final_winner["name"],
                "losers": [pp["name"] for pp in losers],
                "players": [
                    {"name": pp["name"], "score": pp.get("score", 0), "wins": pp.get("wins", 0)}
                    for pp in sorted(r["players"], key=lambda x: x.get("score", 0))
                ],
            }

            cancel_timer(r)
            r["log"].insert(0, f"🏆 الفائز النهائي: {final_winner['name']}")
            send_state(room)
            return

        # انتهت الجولة فقط، ولا نوزع جولة جديدة إلا عند ضغط ابدأ مرة ثانية
        r["started"] = False
        cancel_timer(r)
        send_state(room)
        return

    apply_effect(r, card)

    for pp in r["players"]:
        if len(pp.get("hand", [])) != 1:
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
        r["pendingDraw4"] = 0
        r["pendingDraw2"] = 0
    elif amount2 > 0:
        draw_to(r, idx, amount2)
        r["pendingDraw2"] = 0
        r["pendingDraw4"] = 0
    else:
        draw_to(r, idx, 1)

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
        "text": text[:200]
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
        emit("error_msg", f"فقط القائد يقدر يطرد — القائد: {host_name(r) or '-'}")
        return

    if target_id == host_id:
        emit("error_msg", "ما تقدر تطرد نفسك")
        return

    idx = find_player(room, target_id)
    if idx >= 0:
        name = r["players"][idx]["name"]
        sid = r["players"][idx].get("sid")
        r["players"].pop(idx)
        r["trustedHosts"] = [x for x in r.get("trustedHosts", []) if x != target_id]

        if r.get("turn", 0) >= len(r.get("players", [])):
            r["turn"] = 0

        r["log"].insert(0, f"🚫 تم طرد {name}")
        if sid:
            emit("kicked", {"room": room}, room=sid)

        send_state(room)
        return

    sidx = find_spectator(room, target_id)
    if sidx >= 0:
        name = r["spectators"][sidx]["name"]
        sid = r["spectators"][sidx].get("sid")
        r["spectators"].pop(sidx)
        r["trustedHosts"] = [x for x in r.get("trustedHosts", []) if x != target_id]

        r["log"].insert(0, f"🚫 تم طرد المشاهد {name}")
        if sid:
            emit("kicked", {"room": room}, room=sid)

        send_state(room)


@socketio.on("toggle_trusted_host")
def toggle_trusted_host(data):
    room = data.get("room")
    host_id = data.get("hostId")
    target_id = data.get("targetId")

    if room not in rooms:
        return

    r = rooms[room]

    if r.get("host") != host_id:
        emit("error_msg", "فقط القائد يقدر يعيّن نائب")
        return

    if find_player(room, target_id) < 0:
        emit("error_msg", "النائب لازم يكون لاعب جالس")
        return

    trusted = r.setdefault("trustedHosts", [])

    if target_id in trusted:
        trusted.remove(target_id)
        r["log"].insert(0, "❌ تم إزالة نائب قائد")
    else:
        trusted.append(target_id)
        r["log"].insert(0, "⭐ تم تعيين نائب قائد")

    send_state(room)


@socketio.on("make_host")
def make_host(data):
    room = data.get("room")
    host_id = data.get("hostId")
    target_id = data.get("targetId")

    if room not in rooms:
        return

    r = rooms[room]

    if r.get("host") != host_id:
        emit("error_msg", "فقط القائد يقدر ينقل القيادة")
        return

    idx = find_player(room, target_id)
    if idx < 0:
        emit("error_msg", "لا يمكن نقل القيادة إلا للاعب جالس")
        return

    r["host"] = target_id
    r["log"].insert(0, f"👑 تم نقل القيادة إلى {r['players'][idx]['name']}")
    send_state(room)



# ===== لعبة آخر حرف =====


# ===== قاموس لعبة آخر حرف + فحص AI للكلمات الجديدة =====
DICTIONARY_PATH = "static/dictionaries/arabic_words.txt"
CUSTOM_WORDS_PATH = "static/dictionaries/custom_words.txt"

ARABIC_WORDS = set()


def normalize_arabic_word(word):
    word = (word or "").strip()
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي"
    }
    for old, new in replacements.items():
        word = word.replace(old, new)
    return word


def load_arabic_dictionaries():
    global ARABIC_WORDS
    ARABIC_WORDS = set()

    for path in [DICTIONARY_PATH, CUSTOM_WORDS_PATH]:
        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        w = line.strip()
                        if w:
                            ARABIC_WORDS.add(w)
                            ARABIC_WORDS.add(normalize_arabic_word(w))
        except Exception as e:
            print("Dictionary load error:", path, e)

    print("Loaded Arabic words:", len(ARABIC_WORDS))


def save_custom_arabic_word(word):
    word = (word or "").strip()
    if not word:
        return

    os.makedirs(os.path.dirname(CUSTOM_WORDS_PATH), exist_ok=True)

    if word not in ARABIC_WORDS:
        ARABIC_WORDS.add(word)
        ARABIC_WORDS.add(normalize_arabic_word(word))

        try:
            with open(CUSTOM_WORDS_PATH, "a", encoding="utf-8") as f:
                f.write(word + "\n")
        except Exception as e:
            print("Custom word save error:", e)


def ai_check_arabic_word(word):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if not api_key:
        return False

    word = (word or "").strip()

    if len(word) < 2 or len(word) > 25:
        return False

    if not all(("\u0600" <= c <= "\u06FF") or c.isspace() for c in word):
        return False

    prompt = (
        "هل الكلمة التالية كلمة عربية حقيقية ومفهومة ومستخدمة ككلمة مستقلة؟ "
        "ارفض الحروف العشوائية أو الكلمات المخترعة أو التكرار غير المفهوم. "
        "أجب فقط بكلمة واحدة: نعم أو لا.\n\n"
        f"الكلمة: {word}"
    )

    payload = {
        "model": os.environ.get("OPENAI_WORD_MODEL", "gpt-4.1-mini"),
        "messages": [
            {
                "role": "system",
                "content": "أنت مدقق كلمات للعبة عربية. أجب فقط: نعم أو لا."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0,
        "max_tokens": 2
    }

    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        answer = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
            .lower()
        )

        return answer.startswith("نعم") or answer.startswith("yes")

    except Exception as e:
        print("AI word check error:", e)
        return False


load_arabic_dictionaries()


def last_arabic_letter(word):
    word = (word or "").strip()
    chars = [c for c in word if c.isalpha()]
    if not chars:
        return ""

    mapping = {
        "ة": "ه",
        "ى": "ي",
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ء": "ا",
        "ؤ": "و"
    }

    return mapping.get(chars[-1], chars[-1])

def first_arabic_letter(word):
    word = (word or "").strip()
    chars = [c for c in word if c.isalpha()]
    if not chars:
        return ""

    mapping = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ء": "ا",
        "ؤ": "و"
    }
    return mapping.get(chars[0], chars[0])


def letters_public_state(room):
    r = letters_rooms[room]

    host_name = "---"
    for p in r.get("players", []):
        if p.get("pid") == r.get("host"):
            host_name = p.get("name", "القائد")
            break

    return {
        "room": room,
        "players": r.get("players", []),
        "host": r.get("host"),
        "hostName": host_name,
        "started": r.get("started", False),
        "currentWord": r.get("currentWord", ""),
        "neededLetter": r.get("neededLetter", ""),
        "turn": r.get("turn", 0),
        "timeLeft": r.get("timeLeft", 0),
        "timeLimit": r.get("timeLimit", 30),
        "words": r.get("words", []),
        "roundWinner": r.get("roundWinner"),
        "roundMessage": r.get("roundMessage", ""),
    }


def send_letters_state(room):
    if room not in letters_rooms:
        return

    # مهم: نستخدم socketio.emit بدل emit لأن التايمر يشتغل خارج request context
    socketio.emit("letters_state", letters_public_state(room), room="letters_" + room)


@socketio.on("letters_join")
def letters_join(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    name = str(data.get("name", "لاعب")).strip()
    avatar = str(data.get("avatar", "🎮")).strip()
    pid = str(data.get("pid") or request.sid).strip()

    join_room("letters_" + room)

    if room not in letters_rooms:
        letters_rooms[room] = {
            "players": [],
            "host": pid,
            "hostSid": request.sid,
            "started": False,
            "currentWord": "",
            "neededLetter": "",
            "turn": 0,
            "words": [],
            "timeLimit": 30,
            "timeLeft": 30,
            "timer": None,
            "timerToken": 0,
            "used": set(),
            "roundWinner": None,
            "roundMessage": "",
        }
    r = letters_rooms[room]
    display_name = f"{avatar} {name}"

    old = next((p for p in r["players"] if p.get("pid") == pid), None)

    if old:
        old["sid"] = request.sid
        old["name"] = display_name
        old["online"] = True
    else:
        if r.get("started"):
            emit("letters_error", {
                 "message": "اللعبة بدأت، تقدر تدخل وتشارك من بداية الجولة القادمة"
             }, room=request.sid)
            return

        r["players"].append({
            "pid": pid,
            "sid": request.sid,
            "name": display_name,
            "score": 0,
            "fails": 0,
            "active": True,
            "online": True
        })

    if r.get("host") == pid:
        r["hostSid"] = request.sid

    send_letters_state(room)


def cancel_letters_timer(r):
    r["timerToken"] = int(r.get("timerToken", 0) or 0) + 1
    t = r.get("timer")
    if t:
        try:
            t.cancel()
        except Exception:
            pass
    r["timer"] = None


def letters_active_players(r):
    return [p for p in r.get("players", []) if not p.get("eliminated")]


def finish_letters_round_if_needed(room):
    if room not in letters_rooms:
        return True

    r = letters_rooms[room]
    active = letters_active_players(r)

    if len(active) <= 1 and r.get("started"):
        cancel_letters_timer(r)
        r["started"] = False
        r["timeLeft"] = 0

        if active:
            winner = active[0]
            r["roundWinner"] = winner.get("name", "لاعب")
            r["roundMessage"] = f"🏆 الفائز بالجولة: {r['roundWinner']}"
            r["words"].append({"word": "🏆 فاز بالجولة", "player": r["roundWinner"]})
            socketio.emit("letters_round_winner", {"winner": r["roundWinner"]}, room="letters_" + room)
        else:
            r["roundWinner"] = None
            r["roundMessage"] = "انتهت الجولة بدون فائز"

        send_letters_state(room)
        return True

    return False


def next_letters_turn(room):
    if room not in letters_rooms:
        return

    r = letters_rooms[room]
    players = r.get("players", [])

    if not players:
        cancel_letters_timer(r)
        return

    if finish_letters_round_if_needed(room):
        return

    start = int(r.get("turn", 0) or 0)
    for step in range(1, len(players) + 1):
        ni = (start + step) % len(players)
        if not players[ni].get("eliminated"):
            r["turn"] = ni
            break

    start_letters_timer(room)
    send_letters_state(room)


def letters_fail_current_player(room, reason="محاولة فاشلة"):
    if room not in letters_rooms:
        return

    r = letters_rooms[room]
    players = r.get("players", [])
    if not players or not r.get("started"):
        return

    turn = int(r.get("turn", 0) or 0) % len(players)
    player = players[turn]

    player["fails"] = int(player.get("fails", 0) or 0) + 1
    fails = player["fails"]

    if reason == "انتهى الوقت":
        player["timeouts"] = int(player.get("timeouts", 0) or 0) + 1

    if fails >= 2:
        player["eliminated"] = True
        r["words"].append({"word": "❌ طرد من الجولة", "player": player.get("name", "لاعب")})
        socketio.emit("letters_player_eliminated", {"name": player.get("name", "لاعب")}, room="letters_" + room)
    else:
        r["words"].append({"word": f"⚠️ {reason} ({fails}/2)", "player": player.get("name", "لاعب")})

    if finish_letters_round_if_needed(room):
        return

    next_letters_turn(room)


def start_letters_timer(room):
    if room not in letters_rooms:
        return

    r = letters_rooms[room]
    cancel_letters_timer(r)

    if not r.get("started"):
        send_letters_state(room)
        return

    r["timerToken"] = int(r.get("timerToken", 0) or 0) + 1
    token = r["timerToken"]
    r["timeLeft"] = int(r.get("timeLimit", 30) or 30)

    socketio.emit("letters_timer", {"timeLeft": r["timeLeft"]}, room="letters_" + room)
    send_letters_state(room)

    def tick():
        if room not in letters_rooms:
            return

        rr = letters_rooms[room]

        if rr.get("timerToken") != token or not rr.get("started"):
            return

        rr["timeLeft"] = max(0, int(rr.get("timeLeft", 0) or 0) - 1)

        socketio.emit("letters_timer", {"timeLeft": rr["timeLeft"]}, room="letters_" + room)
        send_letters_state(room)

        if rr["timeLeft"] <= 0:
            socketio.emit("letters_time_up", {}, room="letters_" + room)
            letters_fail_current_player(room, "انتهى الوقت")
            return

        rr["timer"] = threading.Timer(1, tick)
        rr["timer"].daemon = True
        rr["timer"].start()

    r["timer"] = threading.Timer(1, tick)
    r["timer"].daemon = True
    r["timer"].start()
    
@socketio.on("letters_start")
def letters_start(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    word = str(data.get("word", "")).strip()

    if room not in letters_rooms:
        return

    r = letters_rooms[room]

    if r.get("hostSid") != request.sid:
        return

    if len(r.get("players", [])) < 2:
        emit("letters_error", {"message": "لازم لاعبين على الأقل"}, room=request.sid)
        return

    if not word:
        emit("letters_error", {"message": "اكتب كلمة البداية"}, room=request.sid)
        return

    try:
        time_limit = int(data.get("timeLimit", 30))
    except Exception:
        time_limit = 30

    r["timeLimit"] = max(5, min(120, time_limit))
    r["timeLeft"] = r["timeLimit"]

    r["started"] = True
    r["roundWinner"] = None
    r["roundMessage"] = ""
    r["currentWord"] = word
    r["neededLetter"] = last_arabic_letter(word)
    r["turn"] = 1 if len(r["players"]) > 1 else 0
    r["words"] = [{"word": word, "player": "القائد"}]
    r["used"] = {word.strip().lower(), normalize_arabic_word(word.strip().lower())}

    for p in r.get("players", []):
        p["fails"] = 0
        p["timeouts"] = 0
        p["eliminated"] = False

    start_letters_timer(room)
    send_letters_state(room)

@socketio.on("letters_word")
def letters_word(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    pid = str(data.get("pid", "")).strip()
    word = str(data.get("word", "")).strip()

    if room not in letters_rooms:
        return

    r = letters_rooms[room]

    if not r.get("started"):
        emit("letters_error", {"message": "اللعبة لم تبدأ"}, room=request.sid)
        return

    players = r.get("players", [])
    if not players:
        return

    turn = int(r.get("turn", 0)) % len(players)
    current_player = players[turn]

    if current_player.get("pid") != pid:
        emit("letters_error", {"message": "مو دورك"}, room=request.sid)
        return

    if current_player.get("eliminated"):
        emit("letters_error", {"message": "أنت مطرود من الجولة"}, room=request.sid)
        return

    if not word:
        emit("letters_error", {"message": "اكتب كلمة"}, room=request.sid)
        return

    def fail_and_reply(message):
        emit("letters_error", {"message": message}, room=request.sid)
        letters_fail_current_player(room, message)

    if len(word) < 2:
        fail_and_reply("الكلمة قصيرة جداً")
        return

    if not all(("\u0600" <= c <= "\u06FF") or c.isspace() for c in word):
        fail_and_reply("اكتب كلمة عربية فقط")
        return

    word_key = word.strip().lower()
    normalized_key = normalize_arabic_word(word_key)

    if word_key not in ARABIC_WORDS and normalized_key not in ARABIC_WORDS:
        if ai_check_arabic_word(word):
            save_custom_arabic_word(word)
        else:
            fail_and_reply("❌ الكلمة غير موجودة أو غير مفهومة")
            return

    if word_key in r.get("used", set()) or normalized_key in r.get("used", set()):
        fail_and_reply("الكلمة مكررة")
        return

    needed = r.get("neededLetter", "")
    first = first_arabic_letter(word)

    if needed and first != needed:
        fail_and_reply(f"الكلمة لازم تبدأ بحرف: {needed}")
        return

    current_player["score"] = int(current_player.get("score", 0)) + 1
    r["currentWord"] = word
    r["neededLetter"] = last_arabic_letter(word)
    r["words"].append({"word": word, "player": current_player.get("name", "لاعب")})
    r["used"].add(word_key)
    r["used"].add(normalized_key)

    next_letters_turn(room)


@socketio.on("letters_reset")
def letters_reset(data):
    room = str(data.get("room", "ROOM1")).strip().upper()

    if room not in letters_rooms:
        return

    r = letters_rooms[room]

    if r.get("hostSid") != request.sid:
        return

    cancel_letters_timer(r)

    r["started"] = False
    r["currentWord"] = ""
    r["neededLetter"] = ""
    r["turn"] = 0
    r["words"] = []
    r["used"] = set()
    r["timeLeft"] = int(r.get("timeLimit", 30))
    r["roundWinner"] = None
    r["roundMessage"] = ""

    for p in r["players"]:
        p["score"] = 0
        p["fails"] = 0
        p["timeouts"] = 0
        p["eliminated"] = False

    send_letters_state(room)


@socketio.on("letters_leave")
def letters_leave(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    pid = str(data.get("pid", "")).strip()

    if room not in letters_rooms:
        emit("letters_left", {"ok": True}, room=request.sid)
        return

    r = letters_rooms[room]
    r["players"] = [p for p in r.get("players", []) if p.get("pid") != pid]

    if r.get("host") == pid:
        if r.get("players"):
            r["host"] = r["players"][0]["pid"]
            r["hostSid"] = r["players"][0]["sid"]
        else:
            cancel_letters_timer(r)
            del letters_rooms[room]
            emit("letters_left", {"ok": True}, room=request.sid)
            return

    if r.get("turn", 0) >= len(r.get("players", [])):
        r["turn"] = 0

    emit("letters_left", {"ok": True}, room=request.sid)
    send_letters_state(room)


@socketio.on("letters_kick")
def letters_kick(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    target_pid = str(data.get("targetPid", "")).strip()

    if room not in letters_rooms:
        return

    r = letters_rooms[room]

    if r.get("hostSid") != request.sid:
        return

    if target_pid == r.get("host"):
        return

    target = next((p for p in r.get("players", []) if p.get("pid") == target_pid), None)

    if not target:
        return

    target_sid = target.get("sid")
    r["players"] = [p for p in r.get("players", []) if p.get("pid") != target_pid]

    if target_sid:
        emit("letters_kicked", {"room": room}, room=target_sid)

    if r.get("turn", 0) >= len(r.get("players", [])):
        r["turn"] = 0

    send_letters_state(room)



# ===== لعبة اسم بنت ولد حيوان جماد بلاد نبات =====
categories_rooms = {}

CATEGORY_DEFS = [
    {"key": "girls", "label": "اسم بنت"},
    {"key": "boys", "label": "اسم ولد"},
    {"key": "animals", "label": "حيوان"},
    {"key": "objects", "label": "جماد"},
    {"key": "countries", "label": "بلاد"},
    {"key": "plants", "label": "نبات"},
]

CATEGORY_LABELS = {c["key"]: c["label"] for c in CATEGORY_DEFS}
CATEGORY_KEYS = [c["key"] for c in CATEGORY_DEFS]
CATEGORY_BASE_PATHS = {
    "girls": "static/dictionaries/girls.txt",
    "boys": "static/dictionaries/boys.txt",
    "animals": "static/dictionaries/animals.txt",
    "objects": "static/dictionaries/objects.txt",
    "countries": "static/dictionaries/countries.txt",
    "plants": "static/dictionaries/plants.txt",
}
CATEGORY_CUSTOM_PATHS = {
    "girls": "static/dictionaries/custom_girls.txt",
    "boys": "static/dictionaries/custom_boys.txt",
    "animals": "static/dictionaries/custom_animals.txt",
    "objects": "static/dictionaries/custom_objects.txt",
    "countries": "static/dictionaries/custom_countries.txt",
    "plants": "static/dictionaries/custom_plants.txt",
}
import sqlite3
CATEGORY_WORDS = {k: set() for k in CATEGORY_KEYS}
ARABIC_LETTERS = list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")


def load_category_dictionaries():
    global CATEGORY_WORDS
    CATEGORY_WORDS = {k: set() for k in CATEGORY_KEYS}
    os.makedirs("static/dictionaries", exist_ok=True)

    for key in CATEGORY_KEYS:
        for path in [CATEGORY_BASE_PATHS[key], CATEGORY_CUSTOM_PATHS[key]]:
            try:
                if not os.path.exists(path):
                    open(path, "a", encoding="utf-8").close()
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        w = line.strip()
                        if w:
                            CATEGORY_WORDS[key].add(w.strip().lower())
                            CATEGORY_WORDS[key].add(normalize_arabic_word(w.strip().lower()))
            except Exception as e:
                print("Category dictionary load error:", key, path, e)

    print("Loaded category words:", {k: len(v) for k, v in CATEGORY_WORDS.items()})


def save_custom_category_word(category, word):
    category = category if category in CATEGORY_KEYS else "objects"
    word = (word or "").strip()
    if not word:
        return

    word_key = word.strip().lower()
    normalized_key = normalize_arabic_word(word_key)

    if word_key not in CATEGORY_WORDS[category] and normalized_key not in CATEGORY_WORDS[category]:
        CATEGORY_WORDS[category].add(word_key)
        CATEGORY_WORDS[category].add(normalized_key)

        try:
            conn = sqlite3.connect("quiz.db")
            c = conn.cursor()

            c.execute("""
                INSERT OR IGNORE INTO category_words(category, word)
                VALUES (?, ?)
            """, (category, word))

            conn.commit()
            conn.close()

            print("✅ SAVED TO SQLITE:", category, word)

        except Exception as e:
            print("Custom category word save error:", category, e)


def category_first_letter(word):
    word = normalize_arabic_word((word or "").strip())
    if word.startswith("ال") and len(word) > 2:
        word = word[2:]
    return first_arabic_letter(word)


def ai_check_category_word(category, word):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return False

    category = category if category in CATEGORY_KEYS else "objects"
    label = CATEGORY_LABELS.get(category, category)
    word = (word or "").strip()

    if len(word) < 2 or len(word) > 30:
        return False

    if not all(("\u0600" <= c <= "\u06FF") or c.isspace() for c in word):
        return False

    prompt = (
        f"هل الكلمة التالية تصلح لفئة ({label}) في لعبة اسم بنت اسم ولد حيوان جماد بلاد نبات؟ "
        "اقبل فقط الكلمات العربية الحقيقية أو الأسماء المعروفة أو البلاد المعروفة. "
        "ارفض الكلمات العشوائية أو غير المناسبة للفئة. "
        "أجب فقط بكلمة واحدة: نعم أو لا.\n\n"
        f"الفئة: {label}\nالكلمة: {word}"
    )

    payload = {
        "model": os.environ.get("OPENAI_WORD_MODEL", "gpt-4.1-mini"),
        "messages": [
            {"role": "system", "content": "أنت مدقق إجابات لعبة عربية. أجب فقط: نعم أو لا."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 2
    }

    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
        return answer.startswith("نعم") or answer.startswith("yes")
    except Exception as e:
        print("AI category check error:", category, word, e)
        return False


load_category_dictionaries()

def init_category_db():
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS category_words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        word TEXT NOT NULL,
        UNIQUE(category, word)
    )
    """)

    conn.commit()
    conn.close()

init_category_db()

def cancel_categories_timer(r):
    r["timerToken"] = int(r.get("timerToken", 0) or 0) + 1
    t = r.get("timer")
    if t:
        try:
            t.cancel()
        except Exception:
            pass
    r["timer"] = None


def categories_public_state(room, reveal=False):
    r = categories_rooms[room]
    host_name = "---"
    for p in r.get("players", []):
        if p.get("pid") == r.get("host"):
            host_name = p.get("name", "القائد")
            break

    payload = {
        "room": room,
        "players": r.get("players", []),
        "host": r.get("host"),
        "hostName": host_name,
        "started": r.get("started", False),
        "status": r.get("status", "waiting"),
        "letter": r.get("letter", ""),
        "round": r.get("round", 0),
        "roundLimit": r.get("roundLimit", 5),
        "timeLeft": r.get("timeLeft", 0),
        "timeLimit": r.get("timeLimit", 45),
        "categories": CATEGORY_DEFS,
        "roundResults": r.get("roundResults", []),
        "finalResults": r.get("finalResults"),
        "message": r.get("message", ""),
        "submitted": list(r.get("submitted", {}).keys()),
    }

    if reveal or r.get("status") in ["round_finished", "game_finished"]:
        payload["answers"] = r.get("answers", {})
    else:
        payload["answers"] = {}

    return payload


def send_categories_state(room):
    if room not in categories_rooms:
        return
    socketio.emit("categories_state", categories_public_state(room), room="categories_" + room)


def finish_categories_round(room, reason="انتهى الوقت"):
    if room not in categories_rooms:
        return

    r = categories_rooms[room]
    if not r.get("started") or r.get("status") != "started":
        return

    cancel_categories_timer(r)
    players = [p for p in r.get("players", []) if not p.get("eliminated")]
    answers = r.get("answers", {})
    letter = r.get("letter", "")
    results = []
    total_added = {p.get("pid"): 0 for p in players}

    # نحسب الكلمات المتكررة داخل نفس الفئة بين اللاعبين
    repeated = {key: {} for key in CATEGORY_KEYS}
    for pid, ans in answers.items():
        for key in CATEGORY_KEYS:
            w = str(ans.get(key, "")).strip().lower()
            nw = normalize_arabic_word(w)
            if nw:
                repeated[key].setdefault(nw, 0)
                repeated[key][nw] += 1

    submit_order = r.get("submitOrder", [])
    for p in players:
        pid = p.get("pid")
        ans = answers.get(pid, {})
        row = {"pid": pid, "name": p.get("name", "لاعب"), "items": {}, "bonus": 0, "roundScore": 0}
        round_score = 0

        for key in CATEGORY_KEYS:
            word = str(ans.get(key, "")).strip()
            item = {"word": word, "ok": False, "points": 0, "reason": ""}

            if not word:
                item["reason"] = "فارغ"
            elif not all(("\u0600" <= c <= "\u06FF") or c.isspace() for c in word):
                item["reason"] = "غير عربي"
            elif category_first_letter(word) != letter:
                item["reason"] = f"لا يبدأ بحرف {letter}"
            else:
                word_key = word.strip().lower()
                normalized_key = normalize_arabic_word(word_key)
                known = word_key in CATEGORY_WORDS[key] or normalized_key in CATEGORY_WORDS[key]
                if not known:
                    known = ai_check_category_word(key, word)
                    if known:
                        save_custom_category_word(key, word)

                if known:
                    item["ok"] = True
                    item["points"] = 10
                    if repeated[key].get(normalized_key, 0) == 1:
                        item["points"] += 10
                        item["reason"] = "صحيح وفريد"
                    else:
                        item["reason"] = "صحيح"
                else:
                    item["reason"] = "غير موجود أو غير مناسب"

            round_score += int(item["points"])
            row["items"][key] = item

        if pid in submit_order:
            pos = submit_order.index(pid)
            if pos == 0:
                row["bonus"] = 5
            elif pos == 1:
                row["bonus"] = 3
            elif pos == 2:
                row["bonus"] = 1
            round_score += row["bonus"]

        row["roundScore"] = round_score
        total_added[pid] = round_score
        results.append(row)

    for p in r.get("players", []):
        pid = p.get("pid")
        p["score"] = int(p.get("score", 0) or 0) + int(total_added.get(pid, 0) or 0)
        p["lastRoundScore"] = int(total_added.get(pid, 0) or 0)

    r["roundResults"] = sorted(results, key=lambda x: x.get("roundScore", 0), reverse=True)
    r["status"] = "round_finished"
    r["started"] = False
    r["timeLeft"] = 0
    r["message"] = reason

    if int(r.get("round", 0)) >= int(r.get("roundLimit", 5)):
        r["status"] = "game_finished"
        final = sorted(r.get("players", []), key=lambda x: int(x.get("score", 0) or 0), reverse=True)
        r["finalResults"] = [{"name": p.get("name"), "score": p.get("score", 0)} for p in final]
        r["message"] = "انتهت اللعبة"

    send_categories_state(room)


def start_categories_timer(room):
    if room not in categories_rooms:
        return

    r = categories_rooms[room]
    cancel_categories_timer(r)
    r["timerToken"] = int(r.get("timerToken", 0) or 0) + 1
    token = r["timerToken"]
    r["timeLeft"] = int(r.get("timeLimit", 45) or 45)
    send_categories_state(room)

    def tick():
        if room not in categories_rooms:
            return
        rr = categories_rooms[room]
        if rr.get("timerToken") != token or rr.get("status") != "started":
            return

        rr["timeLeft"] = max(0, int(rr.get("timeLeft", 0) or 0) - 1)
        send_categories_state(room)

        if rr["timeLeft"] <= 0:
            finish_categories_round(room, "انتهى الوقت")
            return

        rr["timer"] = threading.Timer(1, tick)
        rr["timer"].daemon = True
        rr["timer"].start()

    r["timer"] = threading.Timer(1, tick)
    r["timer"].daemon = True
    r["timer"].start()


@socketio.on("categories_join")
def categories_join(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    name = str(data.get("name", "لاعب")).strip()[:18]
    avatar = str(data.get("avatar", "🎮")).strip()
    pid = str(data.get("pid") or request.sid).strip()

    join_room("categories_" + room)

    if room not in categories_rooms:
        categories_rooms[room] = {
            "players": [],
            "host": pid,
            "hostSid": request.sid,
            "started": False,
            "status": "waiting",
            "letter": "",
            "round": 0,
            "roundLimit": 5,
            "timeLimit": 45,
            "timeLeft": 45,
            "timer": None,
            "timerToken": 0,
            "answers": {},
            "submitted": {},
            "submitOrder": [],
            "roundResults": [],
            "finalResults": None,
            "message": "",
        }

    r = categories_rooms[room]
    display_name = f"{avatar} {name}"
    old = next((p for p in r["players"] if p.get("pid") == pid), None)

    if old:
        old["sid"] = request.sid
        old["name"] = display_name
        old["online"] = True
    else:
        if r.get("status") == "started":
            emit("categories_error", {"message": "الجولة بدأت، تقدر تدخل من الجولة القادمة"}, room=request.sid)
            return
        r["players"].append({
            "pid": pid,
            "sid": request.sid,
            "name": display_name,
            "score": 0,
            "lastRoundScore": 0,
            "online": True,
        })

    if r.get("host") == pid:
        r["hostSid"] = request.sid

    emit("categories_joined", {"pid": pid, "room": room}, room=request.sid)
    send_categories_state(room)


@socketio.on("categories_start")
def categories_start(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    if room not in categories_rooms:
        return
    r = categories_rooms[room]
    if r.get("hostSid") != request.sid:
        return
    if len(r.get("players", [])) < 2:
        emit("categories_error", {"message": "لازم لاعبين على الأقل"}, room=request.sid)
        return

    try:
        r["timeLimit"] = max(10, min(120, int(data.get("timeLimit", r.get("timeLimit", 45)) or 45)))
    except Exception:
        r["timeLimit"] = 45

    try:
        r["roundLimit"] = max(1, min(20, int(data.get("roundLimit", r.get("roundLimit", 5)) or 5)))
    except Exception:
        r["roundLimit"] = 5

    if r.get("status") == "game_finished" or int(r.get("round", 0)) >= int(r.get("roundLimit", 5)):
        r["round"] = 0
        r["finalResults"] = None
        for p in r.get("players", []):
            p["score"] = 0
            p["lastRoundScore"] = 0

    r["round"] = int(r.get("round", 0) or 0) + 1
    r["letter"] = random.choice(ARABIC_LETTERS)
    r["started"] = True
    r["status"] = "started"
    r["answers"] = {}
    r["submitted"] = {}
    r["submitOrder"] = []
    r["roundResults"] = []
    r["message"] = ""

    for p in r.get("players", []):
        p["lastRoundScore"] = 0

    start_categories_timer(room)


@socketio.on("categories_submit")
def categories_submit(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    pid = str(data.get("pid", "")).strip()
    answers = data.get("answers", {}) or {}

    if room not in categories_rooms:
        return
    r = categories_rooms[room]
    if r.get("status") != "started":
        emit("categories_error", {"message": "الجولة غير شغالة"}, room=request.sid)
        return
    if pid not in [p.get("pid") for p in r.get("players", [])]:
        emit("categories_error", {"message": "أنت مو داخل الروم"}, room=request.sid)
        return
    if pid in r.get("submitted", {}):
        emit("categories_error", {"message": "أنت سلمت إجاباتك"}, room=request.sid)
        return

    clean = {}
    for key in CATEGORY_KEYS:
        clean[key] = str(answers.get(key, "")).strip()[:30]

    r["answers"][pid] = clean
    r["submitted"][pid] = True
    r["submitOrder"].append(pid)

    emit("categories_submitted", {"ok": True}, room=request.sid)

    active_count = len(r.get("players", []))
    if len(r.get("submitted", {})) >= active_count:
        finish_categories_round(room, "كل اللاعبين سلموا")
    else:
        send_categories_state(room)


@socketio.on("categories_reset")
def categories_reset(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    if room not in categories_rooms:
        return
    r = categories_rooms[room]
    if r.get("hostSid") != request.sid:
        return
    cancel_categories_timer(r)
    r["started"] = False
    r["status"] = "waiting"
    r["letter"] = ""
    r["round"] = 0
    r["timeLeft"] = int(r.get("timeLimit", 45) or 45)
    r["answers"] = {}
    r["submitted"] = {}
    r["submitOrder"] = []
    r["roundResults"] = []
    r["finalResults"] = None
    r["message"] = ""
    for p in r.get("players", []):
        p["score"] = 0
        p["lastRoundScore"] = 0
    send_categories_state(room)


@socketio.on("categories_leave")
def categories_leave(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    pid = str(data.get("pid", "")).strip()
    if room not in categories_rooms:
        emit("categories_left", {"ok": True}, room=request.sid)
        return
    r = categories_rooms[room]
    r["players"] = [p for p in r.get("players", []) if p.get("pid") != pid]
    r.get("answers", {}).pop(pid, None)
    r.get("submitted", {}).pop(pid, None)

    if r.get("host") == pid:
        if r.get("players"):
            r["host"] = r["players"][0].get("pid")
            r["hostSid"] = r["players"][0].get("sid")
        else:
            cancel_categories_timer(r)
            del categories_rooms[room]
            emit("categories_left", {"ok": True}, room=request.sid)
            return

    emit("categories_left", {"ok": True}, room=request.sid)
    send_categories_state(room)


@socketio.on("categories_kick")
def categories_kick(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    target_pid = str(data.get("targetPid", "")).strip()
    if room not in categories_rooms:
        return
    r = categories_rooms[room]
    if r.get("hostSid") != request.sid:
        return
    if not target_pid or target_pid == r.get("host"):
        return

    target = next((p for p in r.get("players", []) if p.get("pid") == target_pid), None)
    if not target:
        return
    target_sid = target.get("sid")
    r["players"] = [p for p in r.get("players", []) if p.get("pid") != target_pid]
    r.get("answers", {}).pop(target_pid, None)
    r.get("submitted", {}).pop(target_pid, None)

    if target_sid:
        emit("categories_kicked", {"room": room}, room=target_sid)
    send_categories_state(room)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
