workspace.cursorPosChanged.connect(function () {
    callDBus("io.github.kale_ko.KWinIdleTime", "/io/github/kale_ko/KWinIdleTime", "io.github.kale_ko.KWinIdleTime", "MarkInteraction", function (response) { });
});