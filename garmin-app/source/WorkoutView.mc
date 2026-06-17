using Toybox.WatchUi as Ui;
using Toybox.Graphics as Gfx;
using Toybox.Activity;
using Toybox.Timer;

// The live workout screen: exercise, weight × reps, set count, and a
// rest-timer / heart-rate footer. Refreshes once a second.
class WorkoutView extends Ui.View {
    var workout;
    var uiTimer;

    function initialize(w) {
        View.initialize();
        workout = w;
    }

    function onShow() {
        uiTimer = new Timer.Timer();
        uiTimer.start(method(:tick), 1000, true);
    }

    function onHide() {
        if (uiTimer != null) { uiTimer.stop(); uiTimer = null; }
    }

    function tick() as Void { Ui.requestUpdate(); }

    function onUpdate(dc) {
        dc.setColor(Gfx.COLOR_WHITE, Gfx.COLOR_BLACK);
        dc.clear();
        var w = dc.getWidth();
        var h = dc.getHeight();
        var cx = w / 2;

        // exercise name (teal)
        dc.setColor(0x33D6FF, Gfx.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.10, Gfx.FONT_SMALL, workout.currentExercise(), Gfx.TEXT_JUSTIFY_CENTER);

        // weight (big number) + reps
        dc.setColor(Gfx.COLOR_WHITE, Gfx.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.28, Gfx.FONT_NUMBER_MEDIUM, workout.weight.format("%.1f") + " kg", Gfx.TEXT_JUSTIFY_CENTER);
        dc.drawText(cx, h * 0.52, Gfx.FONT_MEDIUM, workout.reps.toString() + " reps", Gfx.TEXT_JUSTIFY_CENTER);

        // set count for this exercise
        dc.setColor(Gfx.COLOR_LT_GRAY, Gfx.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.66, Gfx.FONT_TINY, "Set " + (workout.setsForCurrent() + 1), Gfx.TEXT_JUSTIFY_CENTER);

        // footer: rest countdown (amber) or live HR (red)
        var rem = workout.restRemaining();
        if (rem > 0) {
            dc.setColor(0xFFC451, Gfx.COLOR_TRANSPARENT);
            dc.drawText(cx, h * 0.80, Gfx.FONT_TINY, "Rest " + (rem / 1000) + "s", Gfx.TEXT_JUSTIFY_CENTER);
        } else {
            var info = Activity.getActivityInfo();
            var hr = (info != null && info.currentHeartRate != null)
                ? info.currentHeartRate.toString() + " bpm" : "-- bpm";
            dc.setColor(0xFF5A6E, Gfx.COLOR_TRANSPARENT);
            dc.drawText(cx, h * 0.80, Gfx.FONT_TINY, hr, Gfx.TEXT_JUSTIFY_CENTER);
        }
    }
}
