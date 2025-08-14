#!/usr/bin/env python3

import sys
import argparse

arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(prog=sys.argv[0], usage="%(prog)s [options]", description="KWin Idle Time Daemon", epilog="For more information, visit https://github.com/Kale-Ko/KWinIdleTime")

arg_parser.add_argument("-t", "--threshold", type=float, default=120.0, help="Set how long it will for the daemon to mark the user as idle (default: 2 minutes)")
arg_parser.add_argument("-l", "--listeners-path", type=str, required=True, help="Set the path that listeners are automatically loaded from. Files must be executable to be loaded.")

args: argparse.Namespace = arg_parser.parse_args(sys.argv[1::])


import sys
import os
import os.path
import subprocess

listeners_path: str = os.path.abspath(args.listeners_path)

listeners: list[str] = []


def load_listeners():
    print(f"Looking for listeners in '{listeners_path}'...")

    os.makedirs(os.path.dirname(listeners_path), exist_ok=True)

    os.umask(0o0277)
    if not os.path.exists(listeners_path):
        os.mkdir(listeners_path, mode=0o0500)

    stat: os.stat_result = os.stat(listeners_path, follow_symlinks=False)
    if stat.st_uid != os.getuid() or stat.st_gid != os.getgid():
        raise Exception(f"The owner {stat.st_uid}:{stat.st_gid} of directory '{listeners_path}' is not the current user {os.getuid()}:{os.getgid()}.")
    elif stat.st_mode & 0o7277 > 0:
        raise Exception(f"The permissions {oct(stat.st_mode & 0o7777).zfill(3)} of directory '{listeners_path}' are too permissive, set them to 500.")

    files: list[str] = os.listdir(listeners_path)

    for file in files:
        file: str = os.path.join(listeners_path, file)
        if not os.path.isfile(file) or not os.access(file, os.R_OK | os.X_OK, follow_symlinks=False):
            continue

        perms: int = os.stat(file, follow_symlinks=False).st_mode
        if stat.st_uid != os.getuid() or stat.st_gid != os.getgid():
            print(f"WARNING: The owner {stat.st_uid}:{stat.st_gid} of file '{file}' is not the current user {os.getuid()}:{os.getgid()}. This listener will not be loaded.", file=sys.stderr)
            continue
        elif perms & 0o7277 > 0:
            print(f"WARNING: The permissions {oct(perms & 0o7777).zfill(3)} of file '{file}' are too permissive, set them to 500. This listener will not be loaded.", file=sys.stderr)
            continue

        listeners.append(file)

    if len(listeners) > 0:
        print(f"Loaded {len(listeners)} listeners successfully.")
    else:
        print(f"No listeners found!", file=sys.stderr)


def on_user_idle():
    for listener in listeners:
        try:
            subprocess.run(args=[listener, "idle"], cwd=listeners_path, start_new_session=True, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15.0)
        except subprocess.SubprocessError as e:
            print(f"Error executing listener '{listener}': {e}", file=sys.stderr)
            continue

        print(f"Executed idle listener '{listener}'.")


def on_user_active(delta: float):
    for listener in listeners:
        try:
            subprocess.run(args=[listener, "active", f"{delta:.2f}"], cwd=listeners_path, start_new_session=True, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15.0)
        except subprocess.SubprocessError as e:
            print(f"Error executing listener '{listener}': {e}", file=sys.stderr)
            continue

        print(f"Executed active listener '{listener}'.")


load_listeners()


import asyncio
import dbus_next
import dbus_next.aio
import time

threshold_time: float = args.threshold

running: bool = False
last_interaction: float = time.monotonic()
is_idle: bool = False


class KWinIdleTime(dbus_next.service.ServiceInterface):
    def __init__(self, name: str):
        super().__init__(name)

    @dbus_next.service.method(name="MarkInteraction")
    def MarkInteraction(self):
        global last_interaction
        global is_idle

        delta_time: float = time.monotonic() - last_interaction
        last_interaction = time.monotonic()

        if is_idle:
            print(f"User has become active @ {last_interaction * 1000:.0f}ms after {delta_time:0.1f} seconds")

            is_idle = False

            on_user_active(delta_time)
            self.UserActive(delta_time)

    @dbus_next.service.signal(name="UserIdle")
    def UserIdle(self) -> "":
        return

    @dbus_next.service.signal(name="UserActive")
    def UserActive(self, idle_time: float) -> "d":
        return idle_time


async def run(stop_event: asyncio.Event = asyncio.Event()):
    global threshold_time
    global running
    global last_interaction
    global is_idle

    running = True

    bus: dbus_next.aio.message_bus.MessageBus = dbus_next.aio.message_bus.MessageBus(bus_type=dbus_next.constants.BusType.SESSION)

    await bus.connect()

    await bus.request_name(name="io.github.kale_ko.KWinIdleTime", flags=dbus_next.constants.NameFlag.NONE)

    interface: KWinIdleTime = KWinIdleTime(name="io.github.kale_ko.KWinIdleTime")

    bus.export(path="/io/github/kale_ko/KWinIdleTime", interface=interface)

    while running and not stop_event.is_set():
        try:
            await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            running = False

        if not is_idle:
            current_time: float = time.monotonic()
            if current_time - last_interaction > threshold_time:
                print(f"User has become idle @ {last_interaction * 1000:.0f}ms")

                is_idle = True

                on_user_idle()
                interface.UserIdle()

    bus.unexport(path="/io/github/kale_ko/KWinIdleTime", interface=interface)

    await bus.release_name(name="io.github.kale_ko.KWinIdleTime")

    bus.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        running = False
