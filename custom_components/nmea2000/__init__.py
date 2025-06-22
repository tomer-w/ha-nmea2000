"""NMEA 2000 Integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from .const import DOMAIN
from .hub import Hub
import logging
import importlib.metadata
import asyncio
PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)
_NMEA2000_LOGGER = logging.getLogger("nmea2000")

async def _update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    _LOGGER.debug("Options for NMEA2000 have been updated - applying changes")
    # Reload the integration to apply changes
    await hass.config_entries.async_reload(entry.entry_id)


async def _get_package_version(package_name):
    loop = asyncio.get_event_loop()
    version = await loop.run_in_executor(None, importlib.metadata.version, package_name)
    return version

def _sync_library_logging():
    """Sync the log level of the library to match integration logging."""
    lib_level = _LOGGER.getEffectiveLevel()
    _NMEA2000_LOGGER.setLevel(lib_level)
    _NMEA2000_LOGGER.propagate = True  # Let it go through HA logging

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the NMEA2000 integration."""
    version = getattr(hass.data["integrations"][DOMAIN], "version", 0)
    nmea2000_version = await _get_package_version("nmea2000")
    _LOGGER.debug("Setting up NMEA2000 integration. Version: %s. NMEA 2000 package version: %s", version, nmea2000_version)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up NMEA2000 integration entry: %s", entry.as_dict())
    _sync_library_logging()

    hub = Hub(hass, entry)
    entry.runtime_data = hub

    # Register the update listener
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Unloading NMEA2000 integration entry: %s", entry.as_dict())
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    hub = entry.runtime_data
    if hub is not None:
        await hub.stop(None)

    return True
