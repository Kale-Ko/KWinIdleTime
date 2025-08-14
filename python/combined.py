#!/usr/bin/env python3
import sys
import threading
import asyncio
import argparse
import os

from daemon import run as run_daemon
from listener import run as run_listener

p = argparse.ArgumentParser(prog=sys.argv[0], usage="%(prog)s [options]")
p.add_argument("--threshold", "-t", type=float, default=120.0)
p.add_argument("--listeners-path", "-l", type=str, default=None)
args = p.parse_args(sys.argv[1:])

os.environ["KWINIDLETIME_THRESHOLD_SECONDS"] = str(args.threshold)
if args.listeners_path:
    os.environ["KWINIDLETIME_LISTENERS_DIR"] = args.listeners_path

daemon_stop = asyncio.Event()
listener_stop = asyncio.Event()

daemon_thread = threading.Thread(target=asyncio.run, args=(run_daemon(daemon_stop),), daemon=False)
listener_thread = threading.Thread(target=asyncio.run, args=(run_listener(listener_stop),), daemon=False)

daemon_thread.start()
listener_thread.start()

try:
    listener_thread.join()
    daemon_thread.join()
except KeyboardInterrupt:
    listener_stop.set()
    daemon_stop.set()
    try:
        listener_thread.join()
        daemon_thread.join()
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
