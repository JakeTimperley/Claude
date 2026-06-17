using Toybox.Application as App;
using Toybox.WatchUi as Ui;

// Entry point. Holds the shared Workout model and hands the live view +
// input delegate to the system.
class StrengthApp extends App.AppBase {
    var workout;

    function initialize() {
        AppBase.initialize();
        workout = new Workout();
    }

    function onStart(state) {}

    // If the app is closed mid-workout, save what we have so it still syncs.
    function onStop(state) {
        if (workout != null && workout.isActive()) {
            workout.finish(true);
        }
    }

    function getInitialView() {
        return [ new WorkoutView(workout), new WorkoutDelegate(workout) ];
    }
}
