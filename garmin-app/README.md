# Strength Log — Garmin Connect IQ watch app

A no-nonsense strength-training tracker for Garmin watches. It records a real
**STRENGTH_TRAINING** activity (so it syncs to Garmin Connect and shows up in the
Trailhead dashboard), and logs every set with **reps + weight** as FIT
developer fields.

## Why this exists
Most gym apps either don't record a proper activity or throw away your set data.
This one:
- Logs **weight × reps per set** with one button press
- Auto **rest timer** between sets (configurable)
- Tracks **set count, total volume**, live **heart rate**
- Saves a **FIT activity** that uploads to Garmin Connect like any run/ride

## On-watch controls (5-button watches)
| Button | Action |
|--------|--------|
| **START / SELECT** | Log the current set, start rest timer |
| **UP** | +2.5 kg |
| **DOWN** | −2.5 kg |
| **MENU** (or **BACK**) | Options: Reps · Exercise · Rest · Finish & Save · Discard |

(Touch watches: the same options menu works; tap UP/DOWN regions for weight.)

---

## Build it

You need the **Connect IQ SDK** (free). Easiest route is the VS Code extension.

1. Install **VS Code** + the **Monkey C** extension (publisher: Garmin).
2. Run **Connect IQ: Verify Installation** (palette: `Ctrl/Cmd+Shift+P`) and let it
   download an SDK + a developer key (it can generate the signing key for you).
3. Open this `garmin-app/` folder in VS Code.
4. Edit `manifest.xml` → `<iq:products>` so it lists **your exact watch**
   (e.g. `fr965`). Use **Connect IQ: Edit Products** to pick from a checklist.
5. Build: **Connect IQ: Build Current Project** → produces a `.prg`.
   - Or run in the simulator: **Connect IQ: Run** (great for testing the UI).

> Note: the `id` in `manifest.xml` is a placeholder. If you instead start with
> **Connect IQ: New Project** (type *watch-app*, min SDK 3.2) it mints a real id
> and a launcher icon; then just drop the files from `source/` and
> `resources/` into it. A 40×40 `launcher_icon.png` is already included here.

### CLI build (alternative)
```bash
monkeyc -d fr965 -f monkey.jungle -o StrengthLog.prg -y /path/to/developer_key.der
```

---

## Get it on your watch

**Private / personal — recommended: sideload (no store, no review).**
1. Build a `.prg` for your device (above).
2. Connect the watch by USB; it mounts as a drive.
3. Copy `StrengthLog.prg` into the **`GARMIN/APPS/`** folder on the watch.
4. Eject, and it appears in your activity/app list.

This is the genuinely private path — the app lives only on your watch.

**Connect IQ Store.** The public store requires Garmin's review and is *public*
(there is no per-user private listing). If you want it in the store:
1. Create a developer account at <https://apps.garmin.com> → *Upload an App*.
2. Build a **`.iq`** package: **Connect IQ: Export Project** in VS Code.
3. Upload the `.iq`, fill in store metadata, submit for review.
You can later *unpublish* to limit availability, but it can't be locked to a
single user. For private use, prefer sideloading.

---

## How it feeds the dashboard
The saved activity is a **strength_training** activity in Garmin Connect, so
`fetch_garmin.py` already picks it up into the **activity log** (it appears in
the Strength tab, the heatmap and Trends). The per-set reps/weight ride along as
FIT **developer fields** on each lap.

Reading those reps/weight back into the dashboard's 1RM/set-log views needs the
fetcher to parse lap developer fields (Garmin's native `exercise-sets` endpoint
won't contain them, since those come from the watch's built-in strength mode).
That parser is a planned follow-up — say the word and I'll add it.

---

## Files
```
manifest.xml          app metadata, device list, permissions
monkey.jungle         build config
resources/strings     app name
resources/drawables   launcher icon (+ drawables.xml)
source/StrengthApp.mc app entry
source/Workout.mc     model + FIT recording session (laps, dev fields)
source/WorkoutView.mc live screen (weight × reps, set count, rest/HR)
source/WorkoutDelegate.mc  button handling
source/Menus.mc       options / reps / exercise / rest pickers
source/SummaryView.mc post-save summary
```

> Heads-up: this project was written carefully but **has not been compiled**
> against the SDK in this environment (no SDK/watch available here). Expect to
> possibly nudge a constant or two (e.g. a device-specific product id) on first
> build. Use the simulator to iterate quickly.
