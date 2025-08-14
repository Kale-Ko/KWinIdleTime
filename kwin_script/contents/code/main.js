var c = 0;
var T = 25;

function ping() {
    callDBus(
        "io.github.kale_ko.KWinIdleTime",
        "/io/github/kale_ko/KWinIdleTime",
        "io.github.kale_ko.KWinIdleTime",
        "MarkInteraction",
        []
    );
}

workspace.cursorPosChanged.connect(function () {
    c++;
    if (c % T === 0) {
        ping();
    }
});

workspace.clientActivated.connect(function () {
    ping();
});
