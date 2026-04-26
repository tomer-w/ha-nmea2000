from enum import Enum
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from homeassistant.const import CONF_NAME
import logging

from .const import (
    CONF_CAN_BITRATE,
    CONF_CAN_CHANNEL,
    CONF_CAN_INTERFACE,
    CONF_DEVICE_TYPE,
    CONF_EXPERIMENTAL,
    CONF_MANUFACTURER_CODES_EXCLUDE,
    CONF_MANUFACTURER_CODES_INCLUDE,
    DOMAIN,
    CONF_PGN_INCLUDE,
    CONF_PGN_EXCLUDE,
    CONF_PORT,
    CONF_IP,
    CONF_BAUDRATE,
    CONF_MODE,
    CONF_SERIAL_PORT,
    CONF_MODE_CAN,
    CONF_MODE_TCP,
    CONF_MODE_USB,
    CONF_MS_BETWEEN_UPDATES,
    CONF_EXCLUDE_AIS,
)

from nmea2000 import ManufacturerCodes

_LOGGER = logging.getLogger(__name__)

MANUFACTURER_CODES = [
    {"value": name, "label": name}
    for name in ManufacturerCodes
]

class GatewayType(Enum):
    """Gateway type — determines transport, framing, and protocol."""
    WAVESHARE = "waveshare"
    EBYTE = "ebyte"
    TEXT = "text"
    ACTISENSE_BST = "actisense_bst"
    PYTHON_CAN = "python_can"

    @property
    def needs_ip_port(self) -> bool:
        return self in (GatewayType.EBYTE, GatewayType.TEXT, GatewayType.ACTISENSE_BST)

    @property
    def needs_serial_port(self) -> bool:
        return self == GatewayType.WAVESHARE

    @property
    def needs_can_config(self) -> bool:
        return self == GatewayType.PYTHON_CAN

def get_manufacturer_selector(name: str) -> SelectSelector:
    """Create a manufacturer selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=MANUFACTURER_CODES,
            mode=SelectSelectorMode.DROPDOWN,
            multiple=True,
            translation_key=name,
        )
    )

_COMMON_OPTIONS = {
    vol.Optional(CONF_PGN_INCLUDE): str,
    vol.Optional(CONF_PGN_EXCLUDE): str,
    vol.Optional(CONF_MS_BETWEEN_UPDATES, default=5000): int,
    vol.Optional(CONF_EXCLUDE_AIS, default=True): bool,
    vol.Optional(CONF_MANUFACTURER_CODES_INCLUDE): get_manufacturer_selector(CONF_MANUFACTURER_CODES_INCLUDE),
    vol.Optional(CONF_MANUFACTURER_CODES_EXCLUDE): get_manufacturer_selector(CONF_MANUFACTURER_CODES_EXCLUDE),
    vol.Optional(CONF_EXPERIMENTAL): bool,
}

_SERIAL_FIELDS = {
    vol.Required(CONF_SERIAL_PORT, default="/dev/ttyUSB0"): str,
    vol.Required(CONF_BAUDRATE, default=2000000): int,
}

_TCP_FIELDS = {
    vol.Required(CONF_IP, default="192.168.0.46"): str,
    vol.Required(CONF_PORT, default=8881): int,
}

_CAN_FIELDS = {
    vol.Required(CONF_CAN_INTERFACE, default="slcan"): str,
    vol.Required(CONF_CAN_CHANNEL, default="/dev/ttyUSB0"): str,
    vol.Required(CONF_CAN_BITRATE, default=250000): int,
}

def _build_options_schema(gateway_type: GatewayType) -> vol.Schema:
    """Build the options schema for the given gateway type."""
    if gateway_type.needs_ip_port:
        transport_fields = _TCP_FIELDS
    elif gateway_type.needs_serial_port:
        transport_fields = _SERIAL_FIELDS
    elif gateway_type.needs_can_config:
        transport_fields = _CAN_FIELDS
    else:
        transport_fields = {}
    return vol.Schema({**transport_fields, **_COMMON_OPTIONS})

def parse_and_validate_comma_separated_integers(input_str: str) -> list[int | str]:
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

CONF_GATEWAY_TYPE = "gateway_type"


def _resolve_gateway_type(data: dict) -> GatewayType:
    """Resolve gateway type from config data.

    Expects the ``gateway_type`` key to be present — legacy configs should
    have been migrated by ``async_migrate_entry`` before this is called.
    """
    return GatewayType(data[CONF_GATEWAY_TYPE])


class NMEA2000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

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
                    vol.Required(CONF_GATEWAY_TYPE, default=GatewayType.WAVESHARE.value): SelectSelector(
                        SelectSelectorConfig(
                            options=[e.value for e in GatewayType],
                            translation_key=CONF_GATEWAY_TYPE,
                        )
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

            if (CONF_MANUFACTURER_CODES_INCLUDE in user_input and len(user_input[CONF_MANUFACTURER_CODES_INCLUDE]) != 0) and (CONF_MANUFACTURER_CODES_EXCLUDE in user_input and len(user_input[CONF_MANUFACTURER_CODES_EXCLUDE]) != 0):
                errors[CONF_MANUFACTURER_CODES_EXCLUDE] = "include_exclude_only_one"

            if len(errors) == 0:
                new_data = self.data | user_input
                _LOGGER.debug("No errors. Storing data: %s", new_data)
                return self.async_create_entry(title=new_data.get(CONF_NAME), data=new_data)

        gateway_type = GatewayType(self.data[CONF_GATEWAY_TYPE])
        return self.async_show_form(
            step_id="options",
            data_schema=_build_options_schema(gateway_type),
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

            if (CONF_MANUFACTURER_CODES_INCLUDE in user_input and len(user_input[CONF_MANUFACTURER_CODES_INCLUDE]) != 0) and (CONF_MANUFACTURER_CODES_EXCLUDE in user_input and len(user_input[CONF_MANUFACTURER_CODES_EXCLUDE]) != 0):
                errors[CONF_MANUFACTURER_CODES_EXCLUDE] = "include_exclude_only_one"

            if len(errors) == 0:
                new_data = user_input
                # merge back the name and gateway_type which are missing from this page
                new_data.update({k: current_data[k] for k in [CONF_NAME, CONF_GATEWAY_TYPE]})
                _LOGGER.debug("New data after processing user_input: %s", new_data)
                # Update the config entry with new data.
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                # Reload the entry to apply the new options
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                _LOGGER.debug("data updated with user input. New data: %s", user_input)
                return self.async_create_entry(title="", data=None)

        gateway_type = _resolve_gateway_type(current_data)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _build_options_schema(gateway_type),
                current_data,
            ),
            errors=errors
        )
