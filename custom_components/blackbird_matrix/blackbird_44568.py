"""
Monoprice Blackbird 8x8 (PN 44568) RS-232 protocol client.

18G 8x8 HDMI 2.0 Matrix HDBaseT 150M with 8 Receivers.
Protocol: ASCII commands ending with !, default 115200 8N1.
"""

from __future__ import annotations

import re
import logging
import time
import serial
from threading import RLock
from collections import namedtuple

_LOGGER = logging.getLogger(__name__)

EOL = b"\r"
TIMEOUT = 2
DEFAULT_BAUD = 115200

# input 1 -> output 1
AV_PATTERN = re.compile(r"input\s+(\d+)\s+->\s+output\s+(\d+)", re.IGNORECASE)
# enable hdmi output 1 stream / disable hdmi output 1 stream
STREAM_PATTERN = re.compile(
    r"(enable|disable)\s+hdmi\s+output\s+(\d+)\s+stream", re.IGNORECASE
)

ZoneStatus = namedtuple("ZoneStatus", ["zone", "power", "av", "ir"])


class Blackbird44568:
    """Client for Monoprice Blackbird 8x8 PN 44568 over RS-232."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD) -> None:
        self._port = serial.serial_for_url(port, do_not_open=True)
        self._port.baudrate = baud
        self._port.stopbits = serial.STOPBITS_ONE
        self._port.bytesize = serial.EIGHTBITS
        self._port.parity = serial.PARITY_NONE
        self._port.timeout = TIMEOUT
        self._port.write_timeout = TIMEOUT
        self._port.open()
        self._lock = RLock()
        self._video_cache: dict[int, int] = {}
        self._power_cache: dict[int, bool] = {}
        self._cache_time: float = 0
        self._cache_ttl = 2.0

    def _send(self, cmd: str) -> str:
        """Send command (must end with !) and return full response.

        Mirrors the bash script approach: write the command, wait 350 ms for
        the device to process it, then drain whatever arrived in the buffer.
        The 50 ms inter-chunk loop handles multi-line responses (e.g. r av out 0!)
        that arrive in several bursts.
        """
        cmd = cmd.strip()
        if not cmd.endswith("!"):
            cmd += "!"
        request = (cmd + "\r").encode("ascii")
        with self._lock:
            self._port.reset_output_buffer()
            self._port.reset_input_buffer()
            self._port.write(request)
            self._port.flush()
            time.sleep(0.35)          # give device time to process & respond
            result = bytearray()
            while self._port.in_waiting:
                result += self._port.read(self._port.in_waiting)
                time.sleep(0.05)      # wait briefly in case more bytes follow
            ret = bytes(result).decode("ascii", errors="replace")
        _LOGGER.debug("44568 sent %r received %r", request, ret)
        return ret

    def _refresh_cache(self) -> None:
        """Fetch r av out 0! and r hdmi 0 stream! and update caches.

        The lock is held for the full refresh so that when 8 zones all call
        zone_status() simultaneously, only the first thread does the two serial
        queries; the rest wait, then find the cache warm and return immediately.
        Without this, every zone sends its own query (thundering herd).
        _send() re-acquires the RLock safely because RLock is reentrant.
        """
        now = time.monotonic()
        if now - self._cache_time < self._cache_ttl:
            return
        with self._lock:
            now = time.monotonic()          # re-check after acquiring lock
            if now - self._cache_time < self._cache_ttl:
                return                      # another thread already refreshed
            try:
                av_resp = self._send("r av out 0")
                stream_resp = self._send("r hdmi 0 stream")
            except serial.SerialTimeoutException:
                _LOGGER.warning("44568 cache refresh timed out")
                return
            self._video_cache = {}
            for m in AV_PATTERN.finditer(av_resp):
                in_id = int(m.group(1))
                out_id = int(m.group(2))
                self._video_cache[out_id] = in_id
            self._power_cache = {}
            for m in STREAM_PATTERN.finditer(stream_resp):
                power = m.group(1).lower() == "enable"
                out_id = int(m.group(2))
                self._power_cache[out_id] = power
            self._cache_time = now

    def zone_status(self, zone: int) -> ZoneStatus | None:
        """Return status for the given zone (output) 1–8."""
        self._refresh_cache()
        power = self._power_cache.get(zone, True)
        av = self._video_cache.get(zone)
        return ZoneStatus(zone=zone, power=power, av=av, ir=None)

    def set_zone_power(self, zone: int, power: bool) -> None:
        """Turn output zone on or off (HDMI stream enable/disable). Zone 1–8."""
        z = 1 if power else 0
        self._send(f"s hdmi {zone} stream {z}")
        self._cache_time = 0

    def set_zone_source(self, zone: int, source: int) -> None:
        """Route source (input) 1–8 to zone (output) 1–8."""
        source = max(1, min(8, source))
        self._send(f"s in {source} av out {zone}")
        self._cache_time = 0

    def set_all_zone_source(self, source: int) -> None:
        """Route source to all outputs. y=0 means all."""
        source = max(1, min(8, source))
        self._send(f"s in {source} av out 0")
        self._cache_time = 0
