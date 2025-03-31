import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
# from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)


USB_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("serial_port", default="/dev/ttyUSB0"): str,
        vol.Required("baudrate", default=2000000): int,
        vol.Optional("pgn_include"): str,
        vol.Optional("pgn_exclude"): str,
    }
)
TCP_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("ip", default="192.168.0.46"): str,
        vol.Optional("port", default=8881): int,
        vol.Optional("pgn_include"): str,
        vol.Optional("pgn_exclude"): str,
    }
)


class NMEA2000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("async_step_user called with user_input: %s", user_input)
        errors = {}

        if user_input is not None:
            existing_names = {
                entry.data.get("name") for entry in self._async_current_entries()
            }
            _LOGGER.debug("Existing names in the integration: %s", existing_names)

            if user_input["name"] in existing_names:
                _LOGGER.debug("Name exists error")
                errors["name"] = "name_exists"
            else:
                _LOGGER.debug(
                    "User input is valid, creating entry with name: %s",
                    user_input.get("name"),
                )
                self.data = user_input
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required("mode", default="USB"): SelectSelector(
                        SelectSelectorConfig(options=["USB", "TCP"])
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
            new_data = self.data | user_input
            _LOGGER.debug("final data for create: %s", new_data)
            return self.async_create_entry(title=new_data.get("name"), data=new_data)

        return self.async_show_form(
            step_id="options",
            data_schema=USB_DATA_SCHEMA
            if self.data["mode"] == "USB"
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

        if user_input is not None:
            _LOGGER.debug("Processing user input")

            _LOGGER.debug("Received user_input: %s", user_input)

            new_data = current_data | user_input
            _LOGGER.debug("New data after processing user_input: %s", new_data)

            # Update the config entry with new data.
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )

            _LOGGER.debug("data updated with user input. New data: %s", new_data)

            return self.async_create_entry(title="", data=None)

        else:
            _LOGGER.debug("user_input is None")
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    USB_DATA_SCHEMA
                    if current_data["mode"] == "USB"
                    else TCP_DATA_SCHEMA,
                    current_data,
                ),
            )
