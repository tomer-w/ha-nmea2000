# Standard Library Imports
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from nmea2000parser import get_parser

# Third-Party Library Imports

# Home Assistant Imports
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP

# Setting up logging and configuring constants and default values
from . import SerialSensor, TCPSensor
from . import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)


CONF_MODE = "mode"
CONF_BAUDRATE = "baudrate"
CONF_SERIAL_PORT = "serial_port"
CONF_IP = "ip"
CONF_PORT = "port"


# The main setup function to initialize the sensor platform


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    # Retrieve configuration from entry
    name = entry.data[CONF_NAME]
    mode = entry.data[CONF_MODE]

    pgn_include = parse_and_validate_comma_separated_integers(
        entry.data.get("pgn_include", "")
    )
    pgn_exclude = parse_and_validate_comma_separated_integers(
        entry.data.get("pgn_exclude", "")
    )

    _LOGGER.info(
        f"Configuring sensor with name: {name}, mode: {mode}, PGN Include: {pgn_include}, PGN Exclude: {pgn_exclude}"
    )

    # Initialize unique dictionary keys based on the integration name
    add_entities_key = f"{name}_add_entities"
    created_sensors_key = f"{name}_created_sensors"
    smart2000usb_data_key = f"{name}_smart2000usb_data"
    fast_packet_key = f"{name}_fast_packet_key"
    whitelist_key = f"{name}_whitelist_key"
    blacklist_key = f"{name}_blacklist_key"

    hass.data[whitelist_key] = pgn_include
    hass.data[blacklist_key] = pgn_exclude

    smart2000timestamp_key = f"{name}_smart2000timestamp_key"
    hass.data[smart2000timestamp_key] = {
        "last_processed": {},
        "min_interval": timedelta(seconds=5),
    }

    # Initialize dictionary to hold fast packet frames
    hass.data[fast_packet_key] = {}

    # Save a reference to the add_entities callback
    hass.data[add_entities_key] = async_add_entities

    # Initialize a dictionary to store references to the created sensors
    hass.data[created_sensors_key] = {}

    if mode == "USB":
        serial_port = entry.data[CONF_SERIAL_PORT]
        baudrate = entry.data[CONF_BAUDRATE]
        _LOGGER.info(
            f"USB sensor with name: {name}, serial_port: {serial_port}, baudrate: {baudrate}"
        )
        sensor = SerialSensor(
            name,
            serial_port,
            baudrate,
        )
    elif mode == "TCP":
        ip = entry.data[CONF_IP]
        port = entry.data[CONF_PORT]
        _LOGGER.info(f"TCP sensor with name: {name}, IP: {ip}, port: {port}")
        sensor = TCPSensor(
            name,
            ip,
            port,
        )
    else:
        _LOGGER.error(f"mode {mode} not supported")
        return

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, sensor.stop)
    async_add_entities([sensor], True)

    # Start the task that updates the sensor availability every 5 minutes
    hass.loop.create_task(update_sensor_availability(hass, name))

    _LOGGER.debug(f"Smart2000usb {name} setup completed.")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Retrieve configuration from entry
    name = entry.data["name"]

    _LOGGER.debug(f"Unload integration with name: {name}")

    # Clean up hass.data entries
    for key_suffix in [
        "add_entities",
        "created_sensors",
        "smart2000usb_data",
        "fast_packet",
        "whitelist",
        "blacklist",
        "smart2000timestamp",
    ]:
        key = f"{name}_{key_suffix}"
        if key in hass.data:
            _LOGGER.debug(f"Removing {key} from hass.data.")
            del hass.data[key]

    _LOGGER.debug(f"Unload and cleanup for {name} completed successfully.")

    return True


async def update_sensor_availability(hass, instance_name):
    """Update the availability of all sensors every 5 minutes."""

    created_sensors_key = f"{instance_name}_created_sensors"

    while True:
        _LOGGER.debug("Running update_sensor_availability")
        await asyncio.sleep(300)  # wait for 5 minutes

        for sensor in hass.data[created_sensors_key].values():
            sensor.update_availability()


def parse_and_validate_comma_separated_integers(input_str: str):
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
                _LOGGER.error(
                    f"Invalid pgn value found: '{value}' in input '{input_str}'."
                )

    return validated_integers
