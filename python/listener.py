#!/usr/bin/env python3
import asyncio
import os
import stat
import sys
from typing import Optional
from dbus_next.aio import MessageBus
from dbus_next.constants import MessageType
from dbus_next import Message

IFACE = "io.github.kale_ko.KWinIdleTime"
OBJ_PATH = "/io/github/kale_ko/KWinIdleTime"
DEFAULT_TIMEOUT = 15.0


def xdg_config_home() -> str:
    return os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))


def listeners_dir() -> str:
    return os.environ.get("KWINIDLETIME_LISTENERS_DIR", os.path.join(xdg_config_home(), "kwinidletime", "listeners"))


def ensure_secure_dir(path: str) -> None:
    try:
        st = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        os.makedirs(path, mode=0o700, exist_ok=True)
        st = os.stat(path, follow_symlinks=False)
    if not stat.S_ISDIR(st.st_mode):
        sys.exit(f"{path} is not a directory")
    if st.st_uid != os.getuid():
        sys.exit(f"{path} must be owned by the current user")
    if (st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        sys.exit(f"{path} must not be group/other-writable (chmod 700)")


def safe_iter_listeners(root: str):
    root_real = os.path.realpath(root)
    try:
        names = os.listdir(root)
    except FileNotFoundError:
        return
    for name in sorted(names):
        p = os.path.join(root, name)
        if os.path.islink(p):
            continue
        real = os.path.realpath(p)
        if not real.startswith(root_real + os.sep):
            continue
        try:
            st = os.stat(real, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(st.st_mode):
            continue
        if st.st_uid != os.getuid():
            continue
        if (st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
            continue
        if not os.access(real, os.X_OK):
            continue
        yield real


def _timeout() -> float:
    try:
        return float(os.getenv("KWINIDLETIME_LISTENER_TIMEOUT", str(DEFAULT_TIMEOUT)))
    except Exception:
        return DEFAULT_TIMEOUT


async def run_exec(exe: str, args, cwd: Optional[str]) -> bool:
    import subprocess, signal
    timeout = _timeout()
    with open(os.devnull, "rb") as devnull_in, open(os.devnull, "wb") as devnull_out:
        proc = subprocess.Popen(
            [exe, *args],
            cwd=cwd,
            stdin=devnull_in,
            stdout=devnull_out,
            stderr=devnull_out,
            start_new_session=True,
            close_fds=True,
        )
        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(loop.run_in_executor(None, proc.wait), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(loop.run_in_executor(None, proc.wait), timeout=2.0)
            except asyncio.TimeoutError:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await loop.run_in_executor(None, proc.wait)
            return False
        return proc.returncode == 0


async def dispatch_all(kind: str, extra: Optional[str] = None) -> None:
    root = listeners_dir()
    ensure_secure_dir(root)
    tasks = []
    for exe in safe_iter_listeners(root):
        args = [kind] + ([extra] if extra is not None else [])
        tasks.append(asyncio.create_task(run_exec(exe, args, cwd=root)))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def get_name_owner(bus: MessageBus, name: str) -> Optional[str]:
    try:
        reply = await bus.call(
            Message(
                destination="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                interface="org.freedesktop.DBus",
                member="GetNameOwner",
                signature="s",
                body=[name],
            )
        )
        return reply.body[0]
    except Exception:
        return None


async def run(stop_event: asyncio.Event = asyncio.Event()) -> int:
    bus = await MessageBus().connect()
    owner: Optional[str] = await get_name_owner(bus, IFACE)

    async def on_owner_changed(msg):
        nonlocal owner
        if msg.message_type != MessageType.SIGNAL:
            return
        if msg.interface != "org.freedesktop.DBus" or msg.member != "NameOwnerChanged":
            return
        try:
            name, old, new = msg.body
        except Exception:
            return
        if name == IFACE:
            owner = new or None

    bus.add_message_handler(on_owner_changed)

    async def on_signal(msg):
        if msg.message_type != MessageType.SIGNAL:
            return
        if msg.interface != IFACE or msg.path != OBJ_PATH:
            return
        if owner is not None and msg.sender != owner:
            return
        if msg.member == "UserIdle":
            await dispatch_all("idle")
        elif msg.member == "UserActive":
            try:
                idle_secs = int(msg.body[0])
            except Exception:
                idle_secs = 0
            await dispatch_all("active", str(idle_secs))

    bus.add_message_handler(lambda m: asyncio.create_task(on_signal(m)))

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run()))
    except KeyboardInterrupt:
        raise SystemExit(130)
