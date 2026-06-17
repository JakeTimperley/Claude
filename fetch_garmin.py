#!/usr/bin/env python3
"""
fetch_garmin.py
===============
Pulls your Garmin Connect data and writes `garmin-data.js`, which the
dashboard (dashboard.html) loads as `window.GARMIN_DATA`. Run this on your own
machine — it logs in with YOUR Garmin credentials and never sends them anywhere
but Garmin.

Quick start
-----------
    python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\\Scripts\\activate)
    pip install -r requirements.txt
    cp .env.example .env          # then edit .env with your Garmin login
    python fetch_garmin.py
    # open dashboard.html in your browser

Credentials are read from environment variables (or a .env file):
    GARMIN_EMAIL, GARMIN_PASSWORD
A login token is cached in ~/.garminconnect so you only authenticate (and pass
MFA) once. If you have 2-factor on, you'll be prompted for the code the first time.

Notes
-----
* Uses the community `garminconnect` library (built on `garth`), which talks to
  the same private endpoints the Connect web app uses. Fine for reading your own
  data; method names can shift between library versions, so each section is
  wrapped in try/except and degrades gracefully — a section that fails just
  keeps the dashboard's sample data for that part.
* Strength 1RMs are ESTIMATED (Epley) from your logged working sets, because
  Garmin doesn't store a 1RM field. Requires that you log sets/reps/weight on
  the watch or in Connect.
"""

import os
import sys
import json
import datetime as dt
from collections import defaultdict

try:
    from garminconnect import Garmin
except ImportError:
    sys.exit("Missing dependency. Run:  pip install -r requirements.txt")

# Optional: load a .env file if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garmin-data.js")
TOKEN_STORE = os.path.expanduser("~/.garminconnect")
N_ACTIVITIES = 30          # how many recent activities to scan
N_RUNS = 12                # runs to keep in the dashboard
N_GYM = 12                 # strength sessions to keep
HIST_LEN = 12              # data points for trend sparklines


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def kg(grams):
    return round((grams or 0) / 1000.0, 1)

def sec_to_clock(s):
    s = int(round(s or 0))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def pace_min_per_km(speed_mps):
    """Decimal minutes per km (the format the dashboard's paceStr expects)."""
    if not speed_mps:
        return 0.0
    return round((1000.0 / speed_mps) / 60.0, 2)

def pace_str(speed_mps):
    if not speed_mps:
        return "--:--"
    total = 1000.0 / speed_mps           # seconds per km
    m, s = divmod(int(round(total)), 60)
    return f"{m}:{s:02d}"

def epley_1rm(weight_kg, reps):
    return round(weight_kg * (1 + reps / 30.0))

def safe(fn, default=None, label=""):
    try:
        return fn()
    except Exception as e:          # noqa: BLE001 - intentional broad catch
        if label:
            print(f"  ! {label}: {e}")
        return default

def fmt_date(iso):
    """'2026-06-17 06:42:11' -> 'Mon · 6:42 AM' style label."""
    try:
        d = dt.datetime.fromisoformat(iso.replace("Z", ""))
    except Exception:
        return iso
    today = dt.date.today()
    if d.date() == today:
        day = "Today"
    elif d.date() == today - dt.timedelta(days=1):
        day = "Yesterday"
    else:
        day = d.strftime("%a")
    return f"{day} · {d.strftime('%-I:%M %p') if os.name != 'nt' else d.strftime('%#I:%M %p')}"


# --------------------------------------------------------------------------- #
# login
# --------------------------------------------------------------------------- #
def connect():
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    # Try cached token first (no password needed after first run).
    try:
        g = Garmin()
        g.login(TOKEN_STORE)
        print("Authenticated from cached token.")
        return g
    except Exception:
        pass
    if not email or not password:
        sys.exit("Set GARMIN_EMAIL and GARMIN_PASSWORD (see .env.example).")
    print("Logging in to Garmin Connect…")
    g = Garmin(email=email, password=password, prompt_mfa=lambda: input("MFA code: ").strip())
    g.login()
    try:
        g.garth.dump(TOKEN_STORE)
        print(f"Token cached at {TOKEN_STORE}")
    except Exception:
        pass
    return g


# --------------------------------------------------------------------------- #
# section builders
# --------------------------------------------------------------------------- #
def build_profile(g, today):
    print("• profile / fitness metrics")
    out = {}
    stats = safe(lambda: g.get_stats(today), {}, "get_stats") or {}
    if stats.get("restingHeartRate"):
        out["restingHr"] = stats["restingHeartRate"]

    vo2 = safe(lambda: g.get_max_metrics(today), None, "get_max_metrics")
    if vo2:
        rec = vo2[0] if isinstance(vo2, list) else vo2
        val = ((rec.get("generic") or {}).get("vo2MaxPreciseValue")
               or (rec.get("generic") or {}).get("vo2MaxValue"))
        if val:
            out["vo2max"] = round(val)

    ts = safe(lambda: g.get_training_status(today), None, "get_training_status")
    if ts:
        load = safe(lambda: ts["mostRecentTrainingLoadBalance"]
                    ["metricsTrainingLoadBalanceDTOMap"], None)
        # training load number varies by payload; best-effort
        status = safe(lambda: list(ts["mostRecentTrainingStatus"]
                      ["latestTrainingStatusData"].values())[0]["trainingStatusFeedbackPhrase"], None)
        if status:
            out["loadStatus"] = str(status).replace("_", " ").title()

    bc = safe(lambda: g.get_body_composition(today, today), None, "get_body_composition")
    if bc and bc.get("dateWeightList"):
        w = bc["dateWeightList"][-1]
        if w.get("weight"):
            out["weight"] = kg(w["weight"])
        if w.get("bodyFat"):
            out["bodyFat"] = round(w["bodyFat"], 1)
    return out


def build_race_predictors(g):
    print("• race predictors")
    rp = safe(lambda: g.get_race_predictions(), None, "get_race_predictions")
    if not rp:
        return None
    rec = rp[0] if isinstance(rp, list) else rp
    rows = [("5K", "time5K"), ("10K", "time10K"),
            ("Half", "timeHalfMarathon"), ("Marathon", "timeMarathon")]
    dist_km = {"5K": 5, "10K": 10, "Half": 21.0975, "Marathon": 42.195}
    out = []
    for label, key in rows:
        secs = rec.get(key)
        if not secs:
            continue
        per_km = secs / dist_km[label]
        m, s = divmod(int(per_km), 60)
        out.append({"dist": label, "time": sec_to_clock(secs),
                    "pace": f"{m}:{s:02d} /km", "trend": "—"})
    return out or None


def normalize_route(coords):
    """[(lat,lon),…] -> [[x,y],…] in the 0..100 box the dashboard map uses."""
    if not coords:
        return []
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    mnla, mxla, mnlo, mxlo = min(lats), max(lats), min(lons), max(lons)
    dla = (mxla - mnla) or 1e-6
    dlo = (mxlo - mnlo) or 1e-6
    # downsample to ~60 points
    step = max(1, len(coords) // 60)
    pts = []
    for la, lo in coords[::step]:
        x = 8 + (lo - mnlo) / dlo * 84          # 8..92
        y = 10 + (mxla - la) / dla * 80         # 10..90, latitude inverted for screen
        pts.append([round(x, 1), round(y, 1)])
    return pts


def build_run(g, act):
    aid = act["activityId"]
    dist_km = round((act.get("distance") or 0) / 1000.0, 2)
    speed = act.get("averageSpeed")
    effort_te = act.get("aerobicTrainingEffect") or 0
    effort = ("VO2 Max" if effort_te >= 4.5 else "Tempo" if effort_te >= 3.5
              else "Long" if dist_km >= 20 else "Easy")

    run = {
        "id": f"r{aid}",
        "title": act.get("activityName") or "Run",
        "type": "run",
        "date": fmt_date(act.get("startTimeLocal", "")),
        "distance": dist_km,
        "duration": sec_to_clock(act.get("duration")),
        "pace": pace_str(speed),
        "avgHr": round(act.get("averageHR") or 0),
        "maxHr": round(act.get("maxHR") or 0),
        "elev": round(act.get("elevationGain") or 0),
        "cal": round(act.get("calories") or 0),
        "vo2": round(act.get("vO2MaxValue") or 0) or None,
        "effort": effort,
        "suffer": round(act.get("activityTrainingLoad") or effort_te * 20),
        "weather": "",
        # running dynamics (shown on the run-detail page)
        "cadence": round(act.get("averageRunningCadenceInStepsPerMinute") or 0) or None,
        "stride": round((act.get("avgStrideLength") or 0) / 100.0, 2) or None,  # cm -> m
        "vosc": round(act.get("avgVerticalOscillation") or 0, 1) or None,
        "grade": None,
        "power": round(act.get("avgPower") or 0) or None,
        "splits": [], "hr": [], "elevProfile": [], "route": [],
    }

    # per-km splits -> decimal minutes
    splits = safe(lambda: g.get_activity_splits(aid), None)
    if splits and splits.get("lapDTOs"):
        for lap in splits["lapDTOs"]:
            sp = lap.get("averageSpeed") or (
                (lap.get("distance") or 0) / (lap.get("duration") or 1))
            run["splits"].append(pace_min_per_km(sp))

    # route polyline + hr/elevation series from details
    details = safe(lambda: g.get_activity_details(aid, maxchart=120, maxpoly=200), None)
    if details:
        poly = ((details.get("geoPolylineDTO") or {}).get("polyline")) or []
        run["route"] = normalize_route([(p["lat"], p["lon"]) for p in poly
                                        if p.get("lat") and p.get("lon")])
        # metric descriptors -> pull HR + elevation arrays
        metrics = details.get("activityDetailMetrics") or []
        descs = {d.get("key"): d.get("metricsIndex")
                 for d in (details.get("metricDescriptors") or [])}
        hr_i, el_i = descs.get("directHeartRate"), descs.get("directElevation")
        sampled = metrics[:: max(1, len(metrics) // 60)] if metrics else []
        for m in sampled:
            vals = m.get("metrics") or []
            if hr_i is not None and hr_i < len(vals) and vals[hr_i] is not None:
                run["hr"].append(round(vals[hr_i]))
            if el_i is not None and el_i < len(vals) and vals[el_i] is not None:
                run["elevProfile"].append(round(vals[el_i]))

    # sensible fallbacks so charts always render
    if not run["splits"]:
        run["splits"] = [pace_min_per_km(speed)] * max(1, int(dist_km))
    if not run["hr"]:
        run["hr"] = [run["avgHr"]] * 8
    if not run["elevProfile"]:
        run["elevProfile"] = [0, run["elev"] // 2, run["elev"]]
    return run


def build_strength(g, act):
    aid = act["activityId"]
    session = {
        "id": f"g{aid}",
        "title": act.get("activityName") or "Strength",
        "type": "gym",
        "date": fmt_date(act.get("startTimeLocal", "")),
        "duration": sec_to_clock(act.get("duration")),
        "volume": 0, "sets": 0, "tonnageNote": "from Garmin",
        "exercises": [],
    }
    data = safe(lambda: g.get_activity_exercise_sets(aid), None)
    sets_list = (data or {}).get("exerciseSets") or []
    by_ex = defaultdict(list)
    for s in sets_list:
        if s.get("setType") != "ACTIVE":
            continue
        name = "Exercise"
        if s.get("exercises"):
            ex = s["exercises"][0]
            name = (ex.get("name") or ex.get("category") or "Exercise")
            name = name.replace("_", " ").title()
        wkg = kg(s.get("weight"))
        reps = s.get("repetitionCount") or 0
        if reps:
            by_ex[name].append([wkg, reps])
            session["volume"] += wkg * reps
            session["sets"] += 1
    for name, sets in by_ex.items():
        session["exercises"].append({"name": name, "sets": sets})
    session["volume"] = round(session["volume"])
    return session


def build_one_rep_max(gym_sessions):
    """Estimate current 1RM + history per major lift from logged sessions."""
    colors = {"squat": "--acc2", "deadlift": "--purple",
              "bench": "--blue", "overhead": "--green", "press": "--green"}
    goals_pct = 1.08          # naive goal = +8% over current
    history = defaultdict(list)        # lift -> [(date_order, est1rm)]
    # sessions arrive newest-first; reverse for chronological history
    for idx, s in enumerate(reversed(gym_sessions)):
        for ex in s.get("exercises", []):
            best = max((epley_1rm(w, r) for w, r in ex["sets"]), default=0)
            if best:
                history[ex["name"]].append(best)
    out = []
    for name, hist in history.items():
        key = name.lower()
        color = next((c for k, c in colors.items() if k in key), "--acc2")
        cur = hist[-1]
        prev = hist[-2] if len(hist) > 1 else cur
        series = (hist[-HIST_LEN:] if len(hist) >= 2 else [cur, cur])
        out.append({"lift": name, "current": cur, "prev": prev,
                    "goal": round(cur * goals_pct), "unit": "kg",
                    "color": color, "history": series})
    # keep the heaviest / most-tracked lifts
    out.sort(key=lambda x: x["current"], reverse=True)
    return out[:6] or None


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    g = connect()
    today = dt.date.today().isoformat()
    data = {}

    prof = build_profile(g, today)
    if prof:
        data["profile"] = prof

    rp = build_race_predictors(g)
    if rp:
        data["racePredictors"] = rp

    print(f"• fetching {N_ACTIVITIES} recent activities")
    activities = safe(lambda: g.get_activities(0, N_ACTIVITIES), [], "get_activities") or []

    runs, gym = [], []
    for act in activities:
        tk = ((act.get("activityType") or {}).get("typeKey") or "").lower()
        if "running" in tk and len(runs) < N_RUNS:
            print(f"   run  → {act.get('activityName')}")
            runs.append(build_run(g, act))
        elif "strength" in tk and len(gym) < N_GYM:
            print(f"   gym  → {act.get('activityName')}")
            gym.append(build_strength(g, act))

    if runs:
        data["runs"] = runs
    if gym:
        data["gymSessions"] = gym
        orm = build_one_rep_max(gym)
        if orm:
            data["oneRepMax"] = orm
        vol_week = sum(s["volume"] for s in gym[:4])
        data["gymTotals"] = {
            "sessions": len(activities),
            "sessionsThisMonth": len(gym),
            "volumeWeek": vol_week,
            "volumeWeekPrev": round(vol_week * 0.95),
            "setsWeek": sum(s["sets"] for s in gym[:4]),
            "prsThisMonth": 0,
        }

    payload = "// Auto-generated by fetch_garmin.py — do not edit by hand.\n" \
              "window.GARMIN_DATA = " + json.dumps(data, indent=2) + ";\n"
    with open(OUT_FILE, "w") as f:
        f.write(payload)
    print(f"\n✓ Wrote {OUT_FILE} "
          f"({len(data.get('runs', []))} runs, {len(data.get('gymSessions', []))} gym sessions)."
          "\n  Open dashboard.html to view your data.")


if __name__ == "__main__":
    main()
