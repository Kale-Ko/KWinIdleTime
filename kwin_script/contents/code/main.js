const CURSOR_INTERVAL = 25; // How many cursor events before we fire a MarkInteraction

function markInteraction() {
    callDBus("io.github.kale_ko.KWinIdleTime", "/io/github/kale_ko/KWinIdleTime", "io.github.kale_ko.KWinIdleTime", "MarkInteraction", function (response) { });
}

var c = 0;
workspace.cursorPosChanged.connect(function () {
    if (c % CURSOR_INTERVAL === 0) {
        markInteraction();
    }
    c++;
});

workspace.windowActivated.connect(function (window) {
    markInteraction();
});

workspace.currentDesktopChanged.connect(function (desktop) {
    markInteraction();
});

workspace.currentActivityChanged.connect(function (activity) {
    markInteraction();
});