using Toybox.WatchUi as Ui;

// Button handling on the live workout screen.
//   START / SELECT  -> log the current set (and start the rest timer)
//   UP   (prev page) -> +2.5 kg
//   DOWN (next page) -> -2.5 kg
//   MENU / BACK      -> options (reps, exercise, rest, finish, discard)
class WorkoutDelegate extends Ui.BehaviorDelegate {
    var workout;

    function initialize(w) {
        BehaviorDelegate.initialize();
        workout = w;
    }

    function onSelect() {
        workout.logSet();
        Ui.requestUpdate();
        return true;
    }

    function onPreviousPage() {     // UP
        workout.adjustWeight(2.5);
        Ui.requestUpdate();
        return true;
    }

    function onNextPage() {         // DOWN
        workout.adjustWeight(-2.5);
        Ui.requestUpdate();
        return true;
    }

    function onMenu() {
        pushOptions();
        return true;
    }

    function onBack() {
        pushOptions();
        return true;
    }

    function pushOptions() {
        var menu = new Ui.Menu2({ :title => "Workout" });
        menu.addItem(new Ui.MenuItem("Reps", workout.reps.toString(), :reps, {}));
        menu.addItem(new Ui.MenuItem("Exercise", workout.currentExercise(), :exercise, {}));
        menu.addItem(new Ui.MenuItem("Rest", (workout.restMs / 1000).toString() + "s", :rest, {}));
        menu.addItem(new Ui.MenuItem("Finish & Save", null, :finish, {}));
        menu.addItem(new Ui.MenuItem("Discard", null, :discard, {}));
        Ui.pushView(menu, new OptionsDelegate(workout), Ui.SLIDE_UP);
    }
}
