"""Support for Monoprice Blackbird matrix (legacy, 39670, 44568)."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA as MEDIA_PLAYER_PLATFORM_SCHEMA,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    DOMAIN,
    SERVICE_SETALLZONES,
    CONF_MODEL,
    CONF_BAUD,
    MODEL_LEGACY,
    MODEL_39670,
    MODEL_44568,
)
from .blackbird_39670 import Blackbird39670
from .blackbird_44568 import Blackbird44568

_LOGGER = logging.getLogger(__name__)

MEDIA_PLAYER_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.comp_entity_ids})

ZONE_SCHEMA = vol.Schema({vol.Required(CONF_NAME): cv.string})

SOURCE_SCHEMA = vol.Schema({vol.Required(CONF_NAME): cv.string})

CONF_ZONES = "zones"
CONF_SOURCES = "sources"

DATA_BLACKBIRD = "blackbird_matrix"

ATTR_SOURCE = "source"

BLACKBIRD_SETALLZONES_SCHEMA = MEDIA_PLAYER_SCHEMA.extend(
    {vol.Required(ATTR_SOURCE): cv.string}
)

ZONE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=8))
SOURCE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=8))

PLATFORM_SCHEMA = vol.All(
    cv.has_at_least_one_key(CONF_PORT, CONF_HOST),
    MEDIA_PLAYER_PLATFORM_SCHEMA.extend(
        {
            vol.Exclusive(CONF_PORT, CONF_TYPE): cv.string,
            vol.Exclusive(CONF_HOST, CONF_TYPE): cv.string,
            vol.Required(CONF_ZONES): vol.Schema({ZONE_IDS: ZONE_SCHEMA}),
            vol.Required(CONF_SOURCES): vol.Schema({SOURCE_IDS: SOURCE_SCHEMA}),
            vol.Optional(CONF_MODEL, default=MODEL_LEGACY): vol.In(
                [MODEL_LEGACY, MODEL_39670, MODEL_44568]
            ),
            vol.Optional(CONF_BAUD): vol.All(vol.Coerce(int), vol.In([2400, 4800, 9600, 19200, 38400, 57600, 115200])),
        }
    ),
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Blackbird matrix platform (legacy, 39670, or 44568).

    async_setup_platform (not setup_platform) is required so that entity
    services like media_player.select_source are properly registered with
    the entity platform dispatcher.  Blocking serial I/O is offloaded to
    the executor.
    """
    if DATA_BLACKBIRD not in hass.data:
        hass.data[DATA_BLACKBIRD] = {}

    port = config.get(CONF_PORT)
    host = config.get(CONF_HOST)
    model = config.get(CONF_MODEL, MODEL_LEGACY)
    baud = config.get(CONF_BAUD)

    blackbird = None
    connection = None

    if port is not None:
        if model == MODEL_44568:
            try:
                from serial import SerialException
                blackbird = await hass.async_add_executor_job(
                    lambda: Blackbird44568(port, baud=baud or 115200)
                )
                connection = port
            except Exception as e:
                _LOGGER.error(
                    "Error connecting to Blackbird 44568 at %s: %s", port, e
                )
                return
        elif model == MODEL_39670:
            try:
                from serial import SerialException
                blackbird = await hass.async_add_executor_job(
                    lambda: Blackbird39670(port, baud=baud or 9600)
                )
                connection = port
            except Exception as e:
                _LOGGER.error(
                    "Error connecting to Blackbird 39670 at %s: %s", port, e
                )
                return
        else:
            try:
                from pyblackbird import get_blackbird
                blackbird = await hass.async_add_executor_job(get_blackbird, port)
                connection = port
            except Exception:
                _LOGGER.error("Error connecting to the Blackbird controller")
                return

    if host is not None:
        if model in (MODEL_39670, MODEL_44568):
            _LOGGER.error("%s model only supports serial port, not host", model)
            return
        try:
            from pyblackbird import get_blackbird
            blackbird = await hass.async_add_executor_job(get_blackbird, host, False)
            connection = host
        except Exception:
            _LOGGER.error("Error connecting to the Blackbird controller")
            return

    if blackbird is None:
        return

    sources = {
        source_id: extra[CONF_NAME]
        for source_id, extra in config[CONF_SOURCES].items()
    }

    devices = []
    for zone_id, extra in config[CONF_ZONES].items():
        _LOGGER.debug("Adding zone %d - %s", zone_id, extra[CONF_NAME])
        unique_id = f"{connection}-{zone_id}"
        device = BlackbirdZone(blackbird, sources, zone_id, extra[CONF_NAME])
        hass.data[DATA_BLACKBIRD][unique_id] = device
        devices.append(device)

    add_entities(devices, True)

    async def async_service_handle(service: ServiceCall) -> None:
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        source = service.data.get(ATTR_SOURCE)
        if entity_ids:
            devices_svc = [
                dev
                for dev in hass.data[DATA_BLACKBIRD].values()
                if dev.entity_id in entity_ids
            ]
        else:
            devices_svc = list(hass.data[DATA_BLACKBIRD].values())
        for device in devices_svc:
            if service.service == SERVICE_SETALLZONES:
                await hass.async_add_executor_job(device.set_all_zones, source)

    hass.services.async_register(
        DOMAIN, SERVICE_SETALLZONES, async_service_handle,
        schema=BLACKBIRD_SETALLZONES_SCHEMA,
    )


class BlackbirdZone(MediaPlayerEntity):
    """Representation of a Blackbird matrix zone."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, blackbird, sources, zone_id, zone_name):
        """Initialize new zone."""
        self._blackbird = blackbird
        self._source_id_name = sources
        self._source_name_id = {v: k for k, v in sources.items()}
        self._attr_source_list = sorted(
            self._source_name_id.keys(), key=lambda v: self._source_name_id[v]
        )
        self._zone_id = zone_id
        self._attr_name = zone_name

    async def async_update(self) -> None:
        """Retrieve latest state (runs in executor to avoid blocking the event loop)."""
        state = await self.hass.async_add_executor_job(
            self._blackbird.zone_status, self._zone_id
        )
        if not state:
            return
        self._attr_state = (
            MediaPlayerState.ON if state.power else MediaPlayerState.OFF
        )
        self._attr_source = self._source_id_name.get(state.av) if state.av else None

    @property
    def media_title(self):
        """Return the current source as media title."""
        return self.source

    def set_all_zones(self, source):
        """Set all zones to one source (called from the custom service handler)."""
        if source not in self._source_name_id:
            return
        idx = self._source_name_id[source]
        _LOGGER.warning("Blackbird: set_all_zones → source=%s idx=%d", source, idx)
        self._blackbird.set_all_zone_source(idx)

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        _LOGGER.warning(
            "Blackbird: async_select_source called zone=%d source=%r",
            self._zone_id, source,
        )
        if source not in self._source_name_id:
            _LOGGER.warning(
                "Blackbird: source %r not in source list %s",
                source, list(self._source_name_id),
            )
            return
        idx = self._source_name_id[source]
        _LOGGER.warning(
            "Blackbird: routing input %d → output (zone) %d", idx, self._zone_id
        )
        await self.hass.async_add_executor_job(
            self._blackbird.set_zone_source, self._zone_id, idx
        )

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        _LOGGER.warning("Blackbird: async_turn_on zone=%d", self._zone_id)
        await self.hass.async_add_executor_job(
            self._blackbird.set_zone_power, self._zone_id, True
        )

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        _LOGGER.warning("Blackbird: async_turn_off zone=%d", self._zone_id)
        await self.hass.async_add_executor_job(
            self._blackbird.set_zone_power, self._zone_id, False
        )
