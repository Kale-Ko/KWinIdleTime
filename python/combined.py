#!/usr/bin/env python3

import sys
import threading
import asyncio

from daemon import run as run_daemon
from listener import run as run_listener

daemon_stop_event: asyncio.Event = asyncio.Event()
listener_stop_event: asyncio.Event = asyncio.Event()

daemon: threading.Thread = threading.Thread(target=asyncio.run, args=(run_daemon(daemon_stop_event),), daemon=False)
listener: threading.Thread = threading.Thread(target=asyncio.run, args=(run_listener(listener_stop_event),), daemon=False)

daemon.start()
listener.start()

try:
    listener.join()
    daemon.join()
except KeyboardInterrupt:
    listener_stop_event.set()
    daemon_stop_event.set()

    try:
        listener.join()
        daemon.join()

        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
