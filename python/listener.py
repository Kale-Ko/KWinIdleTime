#!/usr/bin/env python3

import sys
import argparse

arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="kwinidletime-listener", usage="%(prog)s [options]", description="KWin Idle Time Listener", epilog="For more information, visit https://github.com/Kale-Ko/KWinIdleTime")

arg_parser.add_argument("-l", "--listener-path", type=str, required=True, help="Set the path that listeners are automatically loaded from. Files must be executable to be loaded.")

args: argparse.Namespace = arg_parser.parse_args(sys.argv[1::])


import sys
import os
import os.path
import subprocess

listener_path: str = os.path.abspath(args.listener_path)

listeners: list[str] = []


def load_listeners():
    if not os.path.exists(listener_path):
        os.mkdir(listener_path)

    files: list[str] = os.listdir(listener_path)

    for file in files:
        file: str = os.path.join(listener_path, file)
        if not os.path.isfile(file):
            continue

        if not os.access(file, os.R_OK | os.X_OK):
            continue

        listeners.append(file)

    if len(listeners) > 0:
        print(f"Loaded {len(listeners)} listeners successfully.")
    else:
        print(f"No listeners found.")
        sys.exit(1)


def on_user_idle():
    if __name__ == "__main__":
        print(f"User has become idle.")

    for listener in listeners:
        try:
            subprocess.run(args=[listener, "idle"], cwd=listener_path, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15.0)
        except subprocess.CalledProcessError as e:
            print(f"Error executing listener '{listener}': {e}")
            continue

        print(f"Executed idle listener '{listener}'.")


def on_user_active(delta: float):
    if __name__ == "__main__":
        print(f"User has become active after {delta:0.1f} seconds")

    for listener in listeners:
        try:
            subprocess.run(args=[listener, "active", f"{delta:.2f}"], cwd=listener_path, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15.0)
        except subprocess.CalledProcessError as e:
            print(f"Error executing listener '{listener}': {e}")
            continue

        print(f"Executed active listener '{listener}'.")


load_listeners()

import asyncio
import dbus_next
import dbus_next.aio

running: bool = False


async def run():
    global running

    running = True

    bus: dbus_next.aio.message_bus.MessageBus = dbus_next.aio.message_bus.MessageBus(bus_type=dbus_next.constants.BusType.SESSION)

    await bus.connect()

    kwin_idle_time_introspection = await bus.introspect("io.github.kale_ko.KWinIdleTime", "/io/github/kale_ko/KWinIdleTime")
    kwin_idle_time_proxy_object = bus.get_proxy_object("io.github.kale_ko.KWinIdleTime", "/io/github/kale_ko/KWinIdleTime", introspection=kwin_idle_time_introspection)
    kwin_idle_time = kwin_idle_time_proxy_object.get_interface("io.github.kale_ko.KWinIdleTime")

    kwin_idle_time.on_user_idle(on_user_idle)
    kwin_idle_time.on_user_active(on_user_active)

    while running:
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
