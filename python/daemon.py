#!/usr/bin/env python3
import asyncio
import os
import sys
import time
from typing import Optional

import dbus_next
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface
from dbus_next.constants import NameFlag, RequestNameReply

IFACE = "io.github.kale_ko.KWinIdleTime"
OBJ_PATH = "/io/github/kale_ko/KWinIdleTime"
DEFAULT_THRESHOLD = 120.0
MIN_INTERVAL = 0.02


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


class KWinIdleTime(ServiceInterface):
    def __init__(self, name: str, threshold: float):
        super().__init__(name)
        self.threshold = max(1.0, float(threshold))
        now = time.monotonic()
        self._last_interaction: float = now
        self._last_mark_call: float = now
        self._idle_since: Optional[float] = None

    @dbus_next.service.method(name="MarkInteraction")
    def MarkInteraction(self):
        now = time.monotonic()
        if (now - self._last_mark_call) < MIN_INTERVAL:
            return
        self._last_mark_call = now
        was_idle = self._idle_since is not None
        self._last_interaction = now
        if was_idle:
            idle_seconds = float(now - self._idle_since) if self._idle_since else 0.0
            self._idle_since = None
            try:
                self.UserActive(idle_seconds)
            except Exception:
                pass

    @dbus_next.service.signal(name="UserIdle")
    def UserIdle(self) -> "":
        return

    @dbus_next.service.signal(name="UserActive")
    def UserActive(self, idle_time: float) -> "d":
        return idle_time


async def run(stop_event: asyncio.Event = asyncio.Event()) -> int:
    threshold_time: float = _env_float("KWINIDLETIME_THRESHOLD_SECONDS", DEFAULT_THRESHOLD)

    bus: MessageBus = MessageBus()
    await bus.connect()

    reply = await bus.request_name(IFACE, flags=NameFlag.DO_NOT_QUEUE)
    if reply != RequestNameReply.PRIMARY_OWNER:
        print(f"{IFACE} already owned; exiting.", file=sys.stderr)
        return 1

    iface = KWinIdleTime(name=IFACE, threshold=threshold_time)
    bus.export(OBJ_PATH, iface)

    try:
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
            if iface._idle_since is None:
                now = time.monotonic()
                if (now - iface._last_interaction) >= iface.threshold:
                    iface._idle_since = now
                    try:
                        iface.UserIdle()
                    except Exception:
                        pass
    finally:
        bus.unexport(OBJ_PATH, iface)
        try:
            await bus.release_name(IFACE)
        except Exception:
            pass
        bus.disconnect()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run()))
    except KeyboardInterrupt:
        raise SystemExit(130)
