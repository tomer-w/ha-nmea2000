"""NMEA 2000 Integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.start import async_at_start
from .const import DOMAIN, CONF_MODE, CONF_MODE_USB, CONF_MODE_TCP, CONF_MODE_CAN, CONF_DEVICE_TYPE
from .config_flow import CONF_GATEWAY_TYPE, GatewayType
from .hub import Hub
import logging
import importlib.metadata
import asyncio
PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)
_NMEA2000_LOGGER = logging.getLogger("nmea2000")

async def _update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    _LOGGER.info("Options for NMEA2000 have been updated - applying changes")
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

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries to the current version."""
    _LOGGER.info("Migrating NMEA2000 config entry from version %s", entry.version)

    if entry.version == 1:
        # V1 used mode (USB/TCP/CAN) + device_type (for TCP sub-types).
        # V2 uses a single gateway_type key.
        data = {**entry.data}
        mode = data.pop(CONF_MODE, None)
        device_type = data.pop(CONF_DEVICE_TYPE, None)

        if mode == CONF_MODE_USB:
            gateway_type = GatewayType.WAVESHARE
        elif mode == CONF_MODE_CAN:
            gateway_type = GatewayType.PYTHON_CAN
        elif mode == CONF_MODE_TCP:
            if device_type == "EBYTE":
                gateway_type = GatewayType.EBYTE
            else:
                # "Actisense", "Yacht Devices", "TCP", or missing → TEXT
                gateway_type = GatewayType.TEXT
        else:
            _LOGGER.error("Unknown mode '%s' during migration", mode)
            return False

        data[CONF_GATEWAY_TYPE] = gateway_type.value
        hass.config_entries.async_update_entry(entry, data=data, version=2)
        _LOGGER.info(
            "Migrated NMEA2000 config entry to v2: mode=%s, device_type=%s → gateway_type=%s",
            mode, device_type, gateway_type.value,
        )

    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the NMEA2000 integration."""
    version = getattr(hass.data["integrations"][DOMAIN], "version", 0)
    nmea2000_version = await _get_package_version("nmea2000")
    _LOGGER.info("Setting up NMEA2000 integration. Version: %s. NMEA 2000 package version: %s", version, nmea2000_version)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Setting up NMEA2000 integration entry: %s", entry.as_dict())
    _sync_library_logging()

    hub = Hub(hass, entry)
    entry.runtime_data = hub

    # Register the update listener
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start the hub AFTER sensor platform is fully set up so that
    # entity sensors are ready (async_added_to_hass has fired) before
    # the gateway connect callback tries to update their state.
    entry.async_on_unload(async_at_start(hass, hub.start))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Unloading NMEA2000 integration entry: %s", entry.as_dict())
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    hub = entry.runtime_data
    if hub is not None:
        await hub.stop(None)

    return True
