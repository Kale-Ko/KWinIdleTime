#!/usr/bin/env python3

import sys
import argparse

arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(prog=sys.argv[0], usage="%(prog)s [options]", description="KWin Idle Time Daemon", epilog="For more information, visit https://github.com/Kale-Ko/KWinIdleTime")

arg_parser.add_argument("-t", "--threshold", type=float, default=120.0, help="Set how long it will take for the daemon to mark the user as idle (default: 2 minutes)")

arg_parser.add_argument("-l", "--listeners-path", type=str, required=True, help="Set the path that listeners are automatically loaded from, directory and files must be chmod 0500 to be loaded")

arg_parser.add_argument("--unsafe-allow-permissive-perms", action="store_true", default=False, help=argparse.SUPPRESS)

args: argparse.Namespace = arg_parser.parse_args(sys.argv[1::])


import sys
import os
import os.path
import subprocess

permissive_perms: bool = args.unsafe_allow_permissive_perms

listeners_path: str = os.path.abspath(args.listeners_path)


async def trigger_listeners(args: list[str]):
    os.makedirs(os.path.dirname(listeners_path), exist_ok=True)

    if not os.path.exists(listeners_path):
        os.mkdir(listeners_path, mode=0o0500)

    if not permissive_perms:
        listeners_path_stat: os.stat_result = os.stat(listeners_path, follow_symlinks=False)
        if listeners_path_stat.st_uid != os.getuid() or listeners_path_stat.st_gid != os.getgid():
            raise Exception(f"The owner {listeners_path_stat.st_uid}:{listeners_path_stat.st_gid} of directory '{listeners_path}' is not the current user {os.getuid()}:{os.getgid()}")
        elif listeners_path_stat.st_mode & 0o7277 > 0:
            raise Exception(f"The permissions {oct(listeners_path_stat.st_mode & 0o7777).zfill(3)} of directory '{listeners_path}' are too permissive, set them to 0500")

    filenos: list[int] = []
    tasks: list = []

    file_paths: list[str] = sorted(os.listdir(listeners_path))

    for file_path in file_paths:
        file_path: str = os.path.join(listeners_path, file_path)

        if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK | os.X_OK):
            continue

        fileno = os.open(file_path, os.O_RDONLY | os.O_CLOEXEC)
        filenos.append(fileno)

        if not permissive_perms:
            file_stat: os.stat_result = os.fstat(fileno)
            if file_stat.st_uid != os.getuid() or file_stat.st_gid != os.getgid():
                print(f"SKIPPED: The owner {file_stat.st_uid}:{file_stat.st_gid} of file '{file_path}' is not the current user {os.getuid()}:{os.getgid()}", file=sys.stderr)
                continue
            elif file_stat.st_mode & 0o7277 > 0:
                print(f"SKIPPED: The permissions {oct(file_stat.st_mode & 0o7777).zfill(3)} of file '{file_path}' are too permissive, set them to 0500", file=sys.stderr)
                continue

        exec_task = asyncio.create_subprocess_exec(file_path, *args, executable=f"/proc/self/fd/{fileno}", cwd=listeners_path, start_new_session=True, close_fds=True, pass_fds=[fileno], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tasks.append(exec_task)

        print(f"Executed {args[0]} listener '{file_path}'")

    try:
        async with asyncio.timeout(15):
            results = await asyncio.gather(*tasks, return_exceptions=True)

            print(results)
    except TimeoutError:
        print(f"Timeout waiting for listener processes to finish", file=sys.stderr)

        for task in tasks:
            if not task.done():
                task.cancel()
    finally:
        for fileno in filenos:
            os.close(fileno)


def on_user_idle():
    print(f"User has become idle")

    asyncio.create_task(trigger_listeners(args=["idle"]))


def on_user_active(delta_time: float):
    print(f"User has become active after {delta_time:0.1f} seconds")

    asyncio.create_task(trigger_listeners(args=["active", f"{delta_time:0.2f}"]))


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

    requested_name: dbus_next.constants.RequestNameReply = await bus.request_name(name="io.github.kale_ko.KWinIdleTime", flags=dbus_next.constants.NameFlag.DO_NOT_QUEUE)
    if requested_name != dbus_next.constants.RequestNameReply.PRIMARY_OWNER:
        print(f"Bus name is already owned, exiting", file=sys.stderr)
        sys.exit(1)

    interface: KWinIdleTime = KWinIdleTime(name="io.github.kale_ko.KWinIdleTime")

    bus.export(path="/io/github/kale_ko/KWinIdleTime", interface=interface)

    while running and not stop_event.is_set():
        try:
            await asyncio.sleep(0.1)
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

    release_name: dbus_next.constants.ReleaseNameReply = await bus.release_name(name="io.github.kale_ko.KWinIdleTime")
    if release_name != dbus_next.constants.ReleaseNameReply.RELEASED:
        print(f"Failed to release bus name", file=sys.stderr)

    bus.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        running = False
