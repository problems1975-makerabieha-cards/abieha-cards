def apply_effect(r, card):
    # ===== +2 =====
    if card["n"] == "+2":
        r["pendingDraw2"] = int(r.get("pendingDraw2", 0)) + 2
        r["pendingDraw4"] = 0
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw2']} أو رد +2 / عكس / تخطي بنفس اللون")
        r["turn"] = next_index(r)
        return

    # ===== +4 =====
    if card["n"] == "+4":
        r["pendingDraw4"] = int(r.get("pendingDraw4", 0)) + 4
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw4']} أو رد +4 / عكس / تخطي بنفس اللون")
        r["turn"] = next_index(r)
        return

    # ===== عكس / تخطي =====
    if card["n"] in ["عكس", "تخطي"]:

        # 🟡 إذا فيه عقوبة +2 → تمرير العقوبة
        if r.get("pendingDraw2", 0) > 0:
            if card["n"] == "عكس":
                r["direction"] *= -1
                r["log"].insert(0, f"تم عكس عقوبة +2 — التالي يرد أو يسحب {r['pendingDraw2']}")
            else:
                r["log"].insert(0, f"تم تخطي عقوبة +2 — التالي يرد أو يسحب {r['pendingDraw2']}")

            r["turn"] = next_index(r)
            return

        # 🟡 إذا فيه عقوبة +4 → تمريرها
        if r.get("pendingDraw4", 0) > 0:
            if card["n"] == "عكس":
                r["direction"] *= -1
                r["log"].insert(0, f"تم عكس عقوبة +4 — التالي يرد أو يسحب {r['pendingDraw4']}")
            else:
                r["log"].insert(0, f"تم تخطي عقوبة +4 — التالي يرد أو يسحب {r['pendingDraw4']}")

            r["turn"] = next_index(r)
            return

        # 🟢 اللعب العادي
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

    # ===== باقي الكروت =====
    r["pendingDraw2"] = 0
    r["pendingDraw4"] = 0
    r["turn"] = next_index(r)
