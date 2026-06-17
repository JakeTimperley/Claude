using Toybox.ActivityRecording as Rec;
using Toybox.FitContributor as Fit;
using Toybox.Activity;
using Toybox.System;
using Toybox.Lang;

// One logged set.
class SetEntry {
    var exercise;
    var weight;   // Float, kg
    var reps;     // Number
    function initialize(ex, w, r) {
        exercise = ex;
        weight = w;
        reps = r;
    }
}

// The workout model + the underlying FIT recording session.
//
// Each logged set closes a FIT "lap" carrying two developer fields (reps and
// weight). The activity records as STRENGTH_TRAINING, so it syncs to Garmin
// Connect and shows up in the Trailhead dashboard's activity feed/heatmap.
class Workout {
    var session = null;

    var exercises = [
        "Back Squat", "Front Squat", "Bench Press", "Incline Bench",
        "Deadlift", "Romanian Deadlift", "Overhead Press", "Barbell Row",
        "Pull-up", "Lat Pulldown", "Leg Press", "Bulgarian Split Squat",
        "Biceps Curl", "Triceps Pushdown", "Lateral Raise", "Other"
    ];
    var exIndex = 0;

    var weight = 60.0;        // kg
    var reps = 8;
    var sets = [];            // Array<SetEntry>

    var restMs = 90 * 1000;   // configurable rest length
    var restStartMs = 0;
    var resting = false;

    var repsField = null;
    var weightField = null;
    var setsField = null;

    function initialize() {}

    function isActive() {
        return session != null && session.isRecording();
    }

    function startSession() {
        if (session == null) {
            session = Rec.createSession({
                :name => "Strength",
                :sport => Activity.SPORT_TRAINING,
                :subSport => Activity.SUB_SPORT_STRENGTH_TRAINING
            });
            // Developer fields. Per-lap reps + weight, plus a session set total.
            repsField = session.createField(
                "reps", 0, Fit.DATA_TYPE_UINT16,
                { :mesgType => Fit.MESG_TYPE_LAP, :units => "reps" });
            weightField = session.createField(
                "weight", 1, Fit.DATA_TYPE_FLOAT,
                { :mesgType => Fit.MESG_TYPE_LAP, :units => "kg" });
            setsField = session.createField(
                "total_sets", 2, Fit.DATA_TYPE_UINT16,
                { :mesgType => Fit.MESG_TYPE_SESSION, :units => "sets" });
        }
        session.start();
    }

    function currentExercise() {
        return exercises[exIndex];
    }

    function setsForCurrent() {
        var n = 0;
        for (var i = 0; i < sets.size(); i++) {
            if (sets[i].exercise.equals(currentExercise())) { n++; }
        }
        return n;
    }

    // Record the current weight/reps as a completed set.
    function logSet() {
        if (!isActive()) { startSession(); }
        if (repsField != null)   { repsField.setData(reps); }
        if (weightField != null) { weightField.setData(weight); }
        session.addLap();                       // closes a lap with those fields
        sets.add(new SetEntry(currentExercise(), weight, reps));
        if (setsField != null)   { setsField.setData(sets.size()); }
        restStartMs = System.getTimer();
        resting = true;
    }

    function restRemaining() {
        if (!resting) { return 0; }
        var rem = restMs - (System.getTimer() - restStartMs);
        if (rem <= 0) { resting = false; return 0; }
        return rem;
    }

    function adjustWeight(delta) {
        weight += delta;
        if (weight < 0) { weight = 0.0; }
    }

    function adjustReps(delta) {
        reps += delta;
        if (reps < 1) { reps = 1; }
    }

    function setExercise(i) { exIndex = i; }

    function totalVolume() {
        var v = 0.0;
        for (var i = 0; i < sets.size(); i++) {
            v += sets[i].weight * sets[i].reps;
        }
        return v;
    }

    function finish(save) {
        if (session != null) {
            if (session.isRecording()) { session.stop(); }
            if (save) { session.save(); } else { session.discard(); }
            session = null;
        }
    }
}
