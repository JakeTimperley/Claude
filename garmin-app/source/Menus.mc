using Toybox.WatchUi as Ui;
using Toybox.System;

// Build a numeric pick list (used for reps and rest seconds).
function buildNumberMenu(title, lo, hi, step) {
    var menu = new Ui.Menu2({ :title => title });
    for (var v = lo; v <= hi; v += step) {
        menu.addItem(new Ui.MenuItem(v.toString(), null, v, {}));
    }
    return menu;
}

function buildExerciseMenu(workout) {
    var menu = new Ui.Menu2({ :title => "Exercise" });
    for (var i = 0; i < workout.exercises.size(); i++) {
        menu.addItem(new Ui.MenuItem(workout.exercises[i], null, i, {}));
    }
    return menu;
}

// The options menu off the live screen.
class OptionsDelegate extends Ui.Menu2InputDelegate {
    var workout;
    function initialize(w) {
        Menu2InputDelegate.initialize();
        workout = w;
    }
    function onSelect(item) {
        var id = item.getId();
        if (id == :reps) {
            Ui.pushView(buildNumberMenu("Reps", 1, 20, 1), new RepsDelegate(workout), Ui.SLIDE_LEFT);
        } else if (id == :exercise) {
            Ui.pushView(buildExerciseMenu(workout), new ExerciseDelegate(workout), Ui.SLIDE_LEFT);
        } else if (id == :rest) {
            Ui.pushView(buildNumberMenu("Rest (s)", 30, 240, 15), new RestDelegate(workout), Ui.SLIDE_LEFT);
        } else if (id == :finish) {
            workout.finish(true);
            Ui.switchToView(new SummaryView(workout), new SummaryDelegate(), Ui.SLIDE_UP);
        } else if (id == :discard) {
            workout.finish(false);
            System.exit();
        }
    }
}

class RepsDelegate extends Ui.Menu2InputDelegate {
    var workout;
    function initialize(w) { Menu2InputDelegate.initialize(); workout = w; }
    function onSelect(item) {
        workout.reps = item.getId();
        Ui.popView(Ui.SLIDE_RIGHT);   // close number menu
        Ui.popView(Ui.SLIDE_RIGHT);   // close options menu -> back to live view
    }
}

class RestDelegate extends Ui.Menu2InputDelegate {
    var workout;
    function initialize(w) { Menu2InputDelegate.initialize(); workout = w; }
    function onSelect(item) {
        workout.restMs = item.getId() * 1000;
        Ui.popView(Ui.SLIDE_RIGHT);
        Ui.popView(Ui.SLIDE_RIGHT);
    }
}

class ExerciseDelegate extends Ui.Menu2InputDelegate {
    var workout;
    function initialize(w) { Menu2InputDelegate.initialize(); workout = w; }
    function onSelect(item) {
        workout.setExercise(item.getId());
        Ui.popView(Ui.SLIDE_RIGHT);
        Ui.popView(Ui.SLIDE_RIGHT);
    }
}
