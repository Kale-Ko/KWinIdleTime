#!/usr/bin/env python3

import threading
import asyncio
import time

from daemon import run as run_daemon
from listener import run as run_listener

daemon: threading.Thread = threading.Thread(target=asyncio.run, args=(run_daemon(),), daemon=True)
listener: threading.Thread = threading.Thread(target=asyncio.run, args=(run_listener(),), daemon=False)

daemon.start()
time.sleep(5.0)
listener.start()

listener.join()
daemon.join()
