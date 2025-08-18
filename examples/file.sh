#!/bin/sh

# Script that will either create a file named "active" or "idle" depending on the user's state.

case "$1" in
    "idle")
        rm -f kwin-active
        touch kwin-idle
        ;;
    "active")
        rm -f kwin-idle
        touch kwin-active
        ;;
    *)
        echo "Usage: $0 {idle|active}"
        exit 1
        ;;
esac
