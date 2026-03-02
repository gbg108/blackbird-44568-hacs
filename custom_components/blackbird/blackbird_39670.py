"""
Monoprice Blackbird 8x8 (PN 39670) RS-232 protocol client.

Implements the 39670 command set so the integration can use the same
BlackbirdZone interface. Serial: 9600 8N1 default, CR line ending.
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

# Output 01 Switch To In 03!
VIDEO_PATTERN = re.compile(r"Output\s+(\d+)\s+Switch To In\s+(\d+)!")
# Turn ON Output 01!  /  Turn OFF Output 02!
POUT_PATTERN = re.compile(r"Turn\s+(ON|OFF)\s+Output\s+(\d+)!")

ZoneStatus = namedtuple("ZoneStatus", ["zone", "power", "av", "ir"])


class Blackbird39670:
    """Client for Monoprice Blackbird 4K 8x8 HDBaseT Matrix (PN 39670) over RS-232."""

    def __init__(self, port: str, baud: int = 9600) -> None:
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
        """Send command (with trailing . and CR) and return full response."""
        request = (cmd.strip() + ".\r").encode("ascii")
        with self._lock:
            self._port.reset_output_buffer()
            self._port.reset_input_buffer()
            self._port.write(request)
            self._port.flush()
            result = bytearray()
            self._port.timeout = 0.05
            self._port.inter_byte_timeout = 0.15
            while True:
                c = self._port.read(1)
                if not c:
                    break
                result += c
            self._port.timeout = TIMEOUT
            self._port.inter_byte_timeout = None
            ret = bytes(result).decode("ascii", errors="replace")
        _LOGGER.debug("39670 sent %r received %r", request, ret)
        return ret

    def _refresh_cache(self) -> None:
        """Fetch STA_VIDEO and STA_POUT and update caches."""
        now = time.monotonic()
        if now - self._cache_time < self._cache_ttl:
            return
        try:
            video_resp = self._send("STA_VIDEO")
            pout_resp = self._send("STA_POUT")
        except serial.SerialTimeoutException:
            _LOGGER.warning("39670 cache refresh timed out")
            return
        self._video_cache = {}
        for m in VIDEO_PATTERN.finditer(video_resp):
            out_id = int(m.group(1))
            in_id = int(m.group(2))
            self._video_cache[out_id] = in_id
        self._power_cache = {}
        for m in POUT_PATTERN.finditer(pout_resp):
            power = m.group(1).upper() == "ON"
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
        """Turn output zone on or off. Zone 1–8."""
        cmd = f"@OUT{zone:02d}" if power else f"$OUT{zone:02d}"
        self._send(cmd)
        self._cache_time = 0

    def set_zone_source(self, zone: int, source: int) -> None:
        """Route source (input) 1–8 to zone (output) 1–8."""
        source = max(1, min(8, source))
        self._send(f"OUT{zone:02d}:{source:02d}")
        self._cache_time = 0

    def set_all_zone_source(self, source: int) -> None:
        """Route source to all outputs. 00 = all outputs."""
        source = max(1, min(8, source))
        self._send(f"OUT00:{source:02d}")
        self._cache_time = 0
