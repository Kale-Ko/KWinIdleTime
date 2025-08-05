var i = 0;
workspace.cursorPosChanged.connect(function () {
    if (i % 25 === 0) {
        callDBus("io.github.kale_ko.KWinIdleTime", "/io/github/kale_ko/KWinIdleTime", "io.github.kale_ko.KWinIdleTime", "MarkInteraction", function (response) { });
    }
    i++;
});