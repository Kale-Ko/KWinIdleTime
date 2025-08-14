#!/usr/bin/env python3

import sys
import argparse

arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(prog=sys.argv[0], usage="%(prog)s [options]", description="KWin Idle Time Listener", epilog="For more information, visit https://github.com/Kale-Ko/KWinIdleTime")

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
    print(f"User has become idle.")

    for listener in listeners:
        try:
            subprocess.run(args=[listener, "idle"], cwd=listeners_path, start_new_session=True, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15.0)
        except subprocess.SubprocessError as e:
            print(f"Error executing listener '{listener}': {e}", file=sys.stderr)
            continue

        print(f"Executed idle listener '{listener}'.")


def on_user_active(delta_time: float):
    print(f"User has become active after {delta_time:0.1f} seconds")

    for listener in listeners:
        try:
            subprocess.run(args=[listener, "active", f"{delta_time:.2f}"], cwd=listeners_path, start_new_session=True, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15.0)
        except subprocess.SubprocessError as e:
            print(f"Error executing listener '{listener}': {e}", file=sys.stderr)
            continue

        print(f"Executed active listener '{listener}'.")


load_listeners()


import asyncio
import dbus_next
import dbus_next.aio

running: bool = False


async def run(stop_event: asyncio.Event = asyncio.Event()):
    global running

    running = True

    bus: dbus_next.aio.message_bus.MessageBus = dbus_next.aio.message_bus.MessageBus(bus_type=dbus_next.constants.BusType.SESSION)

    await bus.connect()

    kwin_idle_time_introspection_data: str = open(os.path.join(os.path.dirname(__file__), "io.github.kale_ko.KWinIdleTime.xml")).read()
    kwin_idle_time_introspection: dbus_next.introspection.Node = dbus_next.introspection.Node.parse(kwin_idle_time_introspection_data)
    kwin_idle_time_proxy_object: dbus_next.aio.proxy_object.ProxyObject = bus.get_proxy_object("io.github.kale_ko.KWinIdleTime", "/io/github/kale_ko/KWinIdleTime", introspection=kwin_idle_time_introspection)
    kwin_idle_time: dbus_next.aio.proxy_object.ProxyInterface = kwin_idle_time_proxy_object.get_interface("io.github.kale_ko.KWinIdleTime")

    kwin_idle_time.on_user_idle(on_user_idle)
    kwin_idle_time.on_user_active(on_user_active)

    while running and not stop_event.is_set():
        try:
            await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            running = False

    bus.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        running = False
