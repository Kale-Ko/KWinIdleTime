#!/usr/bin/env python3

import sys
import argparse

arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(prog=sys.argv[0], usage="%(prog)s [options]", description="KWin Idle Time Daemon", epilog="For more information, visit https://github.com/Kale-Ko/KWinIdleTime")

arg_parser.add_argument("-t", "--threshold", type=float, default=120.0, help="Set how long it will for the daemon to mark the user as idle (default: 2 minutes)")

if __name__ != "__main__":
    arg_parser.add_argument("-l", "--listener-path", type=str, required=True, help="Set the path that listeners are automatically loaded from. Files must be executable to be loaded.")

args: argparse.Namespace = arg_parser.parse_args(sys.argv[1::])

import asyncio
import dbus_next
import dbus_next.aio
import time

threshold_time: float = args.threshold

running: bool = False
last_interaction: float = time.time()
is_idle: bool = False


class KWinIdleTime(dbus_next.service.ServiceInterface):
    def __init__(self, name: str):
        super().__init__(name)

    @dbus_next.service.method(name="MarkInteraction")
    def MarkInteraction(self):
        global last_interaction
        global is_idle

        delta_time: float = time.time() - last_interaction
        last_interaction = time.time()

        if is_idle:
            print(f"User has become active @ {last_interaction * 1000:.0f}ms after {delta_time:0.1f} seconds")

            is_idle = False
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
            current_time: float = time.time()
            if current_time - last_interaction > threshold_time:
                print(f"User has become idle @ {last_interaction * 1000:.0f}ms")

                is_idle = True
                interface.UserIdle()

    bus.unexport(path="/io/github/kale_ko/KWinIdleTime", interface=interface)

    await bus.release_name(name="io.github.kale_ko.KWinIdleTime")

    bus.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        running = False
