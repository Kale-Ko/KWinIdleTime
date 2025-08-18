#!/usr/bin/env python3

import sys
import argparse

arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(prog=sys.argv[0], usage="%(prog)s [options]", description="KWin Idle Time Listener", epilog="For more information, visit https://github.com/Kale-Ko/KWinIdleTime")

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

running: bool = False


async def run(stop_event: asyncio.Event = asyncio.Event()):
    global running

    running = True

    bus: dbus_next.aio.message_bus.MessageBus = dbus_next.aio.message_bus.MessageBus(bus_type=dbus_next.constants.BusType.SESSION)

    await bus.connect()

    kwin_idle_time_introspection_data: str = open(os.path.join(os.path.dirname(__file__), "io.github.kale_ko.KWinIdleTime.xml"), mode="r").read()
    kwin_idle_time_introspection: dbus_next.introspection.Node = dbus_next.introspection.Node.parse(kwin_idle_time_introspection_data)
    kwin_idle_time_proxy_object: dbus_next.aio.proxy_object.ProxyObject = bus.get_proxy_object("io.github.kale_ko.KWinIdleTime", "/io/github/kale_ko/KWinIdleTime", introspection=kwin_idle_time_introspection)
    kwin_idle_time: dbus_next.aio.proxy_object.ProxyInterface = kwin_idle_time_proxy_object.get_interface("io.github.kale_ko.KWinIdleTime")

    kwin_idle_time.on_user_idle(on_user_idle)
    kwin_idle_time.on_user_active(on_user_active)

    while running and not stop_event.is_set():
        try:
            await asyncio.sleep(0.1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            running = False

    bus.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        running = False
