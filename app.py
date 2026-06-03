from flask import Flask, request, send_file
from flask_socketio import SocketIO, join_room, emit
import random, os, threading

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "abieha-final-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}
puzzle_rooms = {}

COLORS = ["red", "bluec", "greenc", "yellow"]
TEAM_ORDER = ["A", "B", "C"]

def get_random_puzzle_image(category="general"):
    allowed = {"animals", "football", "actors", "artists", "cartoon", "products", "flags", "plants", "general"}
    category = category if category in allowed else "general"

    folder = os.path.join("static", "puzzle-images", category)

    if not os.path.exists(folder):
        return "https://picsum.photos/seed/default/900"

    files = [
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    if not files:
        return "https://picsum.photos/seed/empty/900"

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


@socketio.on("puzzle_join")
def puzzle_join(data):
    room = str(data.get("room", "ROOM1")).strip().upper()
    name = str(data.get("name", "لاعب")).strip()
    avatar = str(data.get("avatar", "🎮"))

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

    category = data.get("category", "general")
    r["imageUrl"] = get_random_puzzle_image(category)

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
    r["players"] = [p for p in r.get("players", []) if p.get("pid") != pid]

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


@socketio.on("leave_room")
def on_leave_room(data):
    room = data.get("room")
    player_id = data.get("playerId")

    if room not in rooms:
        emit("left_room", {"ok": True})
        return

    r = rooms[room]
    was_host = r.get("host") == player_id

    idx = find_player(room, player_id)
    if idx >= 0:
        name = r["players"][idx]["name"]
        r["players"].pop(idx)
        r["trustedHosts"] = [x for x in r.get("trustedHosts", []) if x != player_id]
        r["log"].insert(0, f"🚪 {name} خرج من الغرفة")

        if r.get("turn", 0) >= len(r.get("players", [])):
            r["turn"] = 0
    else:
        sidx = find_spectator(room, player_id)
        if sidx >= 0:
            name = r["spectators"][sidx]["name"]
            r["spectators"].pop(sidx)
            r["trustedHosts"] = [x for x in r.get("trustedHosts", []) if x != player_id]
            r["log"].insert(0, f"🚪 {name} خرج من الغرفة")

    if was_host:
        transfer_host(room, r)

    emit("left_room", {"ok": True})

    if reset_room_if_empty(room, r):
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
        emit("error_msg", f"فقط قائد الغرفة يقدر ينهي اللعبة — القائد: {host_name(r) or '-'}")
        return

    r["started"] = False
    r["pendingDraw4"] = 0
    r["pendingDraw2"] = 0
    cancel_timer(r)
    r["log"].insert(0, "تم إنهاء اللعبة بواسطة قائد الغرفة")
    send_state(room)


@socketio.on("disconnect")
def on_disconnect():
    for proom, pr in list(puzzle_rooms.items()):
        changed = False
        for p in pr.get("players", []):
            if p.get("sid") == request.sid:
                p["online"] = False
                changed = True
                if pr.get("hostSid") == request.sid:
                    pr["hostSid"] = None
        if changed:
            emit("puzzle_state", pr, room="puzzle_" + proom)

    for room, r in list(rooms.items()):

        for i, player in enumerate(list(r.get("players", []))):
            if player.get("sid") == request.sid:
                was_host = r.get("host") == player.get("id")
                name = player.get("name", "لاعب")
                pid = player.get("id")

                r["players"].pop(i)
                r["trustedHosts"] = [x for x in r.get("trustedHosts", []) if x != pid]

                if r.get("turn", 0) >= len(r.get("players", [])):
                    r["turn"] = 0

                r["log"].insert(0, f"🚪 {name} خرج من الغرفة")

                if was_host:
                    transfer_host(room, r)

                if reset_room_if_empty(room, r):
                    return

                send_state(room)
                return

        for i, spectator in enumerate(list(r.get("spectators", []))):
            if spectator.get("sid") == request.sid:
                was_host = r.get("host") == spectator.get("id")
                name = spectator.get("name", "مشاهد")
                sid = spectator.get("id")

                r["spectators"].pop(i)
                r["trustedHosts"] = [x for x in r.get("trustedHosts", []) if x != sid]

                r["log"].insert(0, f"🚪 {name} خرج من الغرفة")

                if was_host:
                    transfer_host(room, r)

                if reset_room_if_empty(room, r):
                    return

                send_state(room)
                return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
