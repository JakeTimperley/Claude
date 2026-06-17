using Toybox.WatchUi as Ui;
using Toybox.Graphics as Gfx;
using Toybox.System;

// Shown after Finish & Save.
class SummaryView extends Ui.View {
    var workout;
    function initialize(w) {
        View.initialize();
        workout = w;
    }
    function onUpdate(dc) {
        dc.setColor(Gfx.COLOR_WHITE, Gfx.COLOR_BLACK);
        dc.clear();
        var w = dc.getWidth();
        var h = dc.getHeight();
        var cx = w / 2;
        dc.setColor(0x34D8A6, Gfx.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.16, Gfx.FONT_MEDIUM, "Saved", Gfx.TEXT_JUSTIFY_CENTER);
        dc.setColor(Gfx.COLOR_WHITE, Gfx.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.40, Gfx.FONT_SMALL, workout.sets.size() + " sets", Gfx.TEXT_JUSTIFY_CENTER);
        dc.drawText(cx, h * 0.55, Gfx.FONT_SMALL, "Vol " + workout.totalVolume().format("%.0f") + " kg", Gfx.TEXT_JUSTIFY_CENTER);
        dc.setColor(Gfx.COLOR_LT_GRAY, Gfx.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.74, Gfx.FONT_TINY, "Synced to Garmin Connect", Gfx.TEXT_JUSTIFY_CENTER);
    }
}

class SummaryDelegate extends Ui.BehaviorDelegate {
    function initialize() { BehaviorDelegate.initialize(); }
    function onBack() { System.exit(); }
    function onSelect() { System.exit(); }
}
