"""NMEA 2000 Integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from .const import DOMAIN
import logging

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    _LOGGER.debug("Options for NMEA2000 have been updated - applying changes")
    # Reload the integration to apply changes
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: dict):
    version = getattr(hass.data["integrations"][DOMAIN], "version", 0)
    _LOGGER.debug("Setting up NMEA2000 integration. Version: %s", version)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up NMEA2000 integration entry: %s", entry.as_dict())
    # Register the update listener
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Unloading NMEA2000 integration entry: %s", entry.as_dict())
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    sensor = entry.runtime_data
    if sensor is not None:
        sensor.stop(None)
    return True
