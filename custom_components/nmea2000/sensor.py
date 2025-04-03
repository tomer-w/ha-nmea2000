# Standard Library Imports
import logging

# Third-Party Library Imports

# Home Assistant Imports
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import CONF_NAME

# Setting up logging and configuring constants and default values

_LOGGER = logging.getLogger(__name__)


# Seems like an ugly hack to get the async_add_entities callback. I dont have access to it from the hub itself
async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    _LOGGER.debug("NMEA2000 %s async_setup_entry", entry.data[CONF_NAME])

    hub = entry.runtime_data
    hub.register_async_add_entities(async_add_entities)

    return True
