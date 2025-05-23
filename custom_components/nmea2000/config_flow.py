from enum import Enum
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
from homeassistant.const import CONF_NAME
# from homeassistant.exceptions import HomeAssistantError

from .const import CONF_DEVICE_TYPE, DOMAIN, CONF_PGN_INCLUDE, CONF_PGN_EXCLUDE, CONF_PORT, CONF_IP, CONF_BAUDRATE, CONF_MODE, CONF_SERIAL_PORT, CONF_MODE_TCP, CONF_MODE_USB, CONF_MS_BETWEEN_UPDATES, CONF_EXCLUDE_AIS
import logging

_LOGGER = logging.getLogger(__name__)

class NetwrorkDeviceType(Enum):
    """Enum for device types."""
    EBYTE = "EBYTE"
    ACTISENSE = "Actisense"
    YACHT_DEVICES = "Yacht Devices"
    

USB_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_PORT, default="/dev/ttyUSB0"): str,
        vol.Required(CONF_BAUDRATE, default=2000000): int,
        vol.Optional(CONF_PGN_INCLUDE): str,
        vol.Optional(CONF_PGN_EXCLUDE): str,
        vol.Optional(CONF_EXCLUDE_AIS): bool,
        vol.Optional(CONF_MS_BETWEEN_UPDATES, default=5000): int,
    }
)
TCP_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_TYPE, default=NetwrorkDeviceType.EBYTE): vol.In([e.value for e in NetwrorkDeviceType]),
        vol.Required(CONF_IP, default="192.168.0.46"): str,
        vol.Required(CONF_PORT, default=8881): int,
        vol.Optional(CONF_PGN_INCLUDE): str,
        vol.Optional(CONF_PGN_EXCLUDE): str,
        vol.Optional(CONF_EXCLUDE_AIS): bool,
        vol.Optional(CONF_MS_BETWEEN_UPDATES, default=5000): int,
    }
)

def parse_and_validate_comma_separated_integers(input_str: str) -> list[int]:
    """Parse and validate a comma-separated string of integers."""
    # Check if the input string is empty or contains only whitespace
    if not input_str.strip():
        return []

    # Split the string by commas to get potential integer values
    potential_integers = input_str.split(",")

    validated_integers = []
    for value in potential_integers:
        value = value.strip()  # Remove any leading/trailing whitespace
        if value:  # Check if the string is not empty
            try:
                # Attempt to convert the string to an integer
                integer_value = int(value)
                validated_integers.append(integer_value)
            except ValueError:
                # Raise an error indicating the specific value that couldn't be converted
                raise ValueError(f"Invalid pgn value found: '{value}' in input '{input_str}'")

    return validated_integers

class NMEA2000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("async_step_user called with user_input: %s", user_input)
        errors = {}

        if user_input is not None:
            existing_names = {
                entry.data.get(CONF_NAME) for entry in self._async_current_entries()
            }
            _LOGGER.debug("Existing names in the integration: %s", existing_names)

            if user_input[CONF_NAME] in existing_names:
                _LOGGER.debug("Name exists error")
                errors[CONF_NAME] = "name_exists"
            else:
                _LOGGER.debug(
                    "User input is valid, creating entry with name: %s",
                    user_input.get(CONF_NAME),
                )
                self.data = user_input
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_MODE, default=CONF_MODE_USB): SelectSelector(
                        SelectSelectorConfig(options=[CONF_MODE_USB, CONF_MODE_TCP])
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_options(self, user_input=None):
        """Handle the options step of the config flow."""
        _LOGGER.debug(
            "async_step_options called with user_input: %s, data: %s",
            user_input,
            self.data,
        )

        errors = {}
        if user_input is not None:
            if CONF_PGN_INCLUDE in user_input:
                try:
                    parse_and_validate_comma_separated_integers(user_input[CONF_PGN_INCLUDE])
                except ValueError:
                    errors[CONF_PGN_INCLUDE] = "pgn_not_valid"
            
            if CONF_PGN_EXCLUDE in user_input:
                try:
                    parse_and_validate_comma_separated_integers(user_input[CONF_PGN_EXCLUDE])
                except ValueError:
                    errors[CONF_PGN_EXCLUDE] = "pgn_not_valid"

            if CONF_PGN_INCLUDE in user_input and CONF_PGN_EXCLUDE in user_input:
                errors[CONF_PGN_EXCLUDE] = "include_exclude_only_one"

            if len(errors) == 0:
                new_data = self.data | user_input
                _LOGGER.debug("No errors. Storing data: %s", new_data)
                return self.async_create_entry(title=new_data.get(CONF_NAME), data=new_data)

        return self.async_show_form(
            step_id="options",
            data_schema=USB_DATA_SCHEMA
            if self.data[CONF_MODE] == CONF_MODE_USB
            else TCP_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        _LOGGER.debug("Getting options flow handler")
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        _LOGGER.debug(
            "OptionsFlowHandler.async_step_init called with user_input: %s", user_input
        )

        # Log the current options before any updates
        current_data = self.config_entry.data
        _LOGGER.debug("Current options before any updates: %s", current_data)

        errors = {}
        if user_input is not None:
            _LOGGER.debug("Processing user input")

            _LOGGER.debug("Received user_input: %s", user_input)

            if CONF_PGN_INCLUDE in user_input:
                try:
                    parse_and_validate_comma_separated_integers(user_input[CONF_PGN_INCLUDE])
                except ValueError:
                    errors[CONF_PGN_INCLUDE] = "pgn_not_valid"
            
            if CONF_PGN_EXCLUDE in user_input:
                try:
                    parse_and_validate_comma_separated_integers(user_input[CONF_PGN_EXCLUDE])
                except ValueError:
                    errors[CONF_PGN_EXCLUDE] = "pgn_not_valid"

            if CONF_PGN_INCLUDE in user_input and CONF_PGN_EXCLUDE in user_input:
                errors[CONF_PGN_EXCLUDE] = "include_exclude_only_one"

            if len(errors) == 0:
                new_data = user_input
                # merge back the name and mode which are missing from this page
                new_data.update({k: current_data[k] for k in [CONF_NAME, CONF_MODE]})
                _LOGGER.debug("New data after processing user_input: %s", new_data)
                # Update the config entry with new data.
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )

                _LOGGER.debug("data updated with user input. New data: %s", user_input)
                return self.async_create_entry(title="", data=None)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                USB_DATA_SCHEMA
                if current_data[CONF_MODE] == CONF_MODE_USB
                else TCP_DATA_SCHEMA,
                current_data,
            ),
            errors=errors
        )
