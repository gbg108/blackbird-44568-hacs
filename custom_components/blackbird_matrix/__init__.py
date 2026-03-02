"""The Blackbird Matrix component (supports legacy, 39670, and 44568 8x8)."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Blackbird Matrix integration (required so the platform can load)."""
    return True
