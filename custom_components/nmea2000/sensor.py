# Standard Library Imports
import asyncio
import logging
from nmea2000 import NMEA2000Message, TcpNmea2000Gateway, UsbNmea2000Gateway

# Third-Party Library Imports

# Home Assistant Imports
from .NMEA2000Sensor import NMEA2000Sensor
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP

# Setting up logging and configuring constants and default values

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
    created_sensors_key = f"{name}_created_sensors"

    # Initialize a dictionary to store references to the created sensors
    hass.data[created_sensors_key] = {}

    if mode == "USB":
        serial_port = entry.data[CONF_SERIAL_PORT]
        baudrate = entry.data[CONF_BAUDRATE]
        _LOGGER.info(
            f"USB sensor with name: {name}, serial_port: {serial_port}, baudrate: {baudrate}"
        )
        gateway = UsbNmea2000Gateway(serial_port)
    elif mode == "TCP":
        ip = entry.data[CONF_IP]
        port = entry.data[CONF_PORT]
        _LOGGER.info(f"TCP sensor with name: {name}, IP: {ip}, port: {port}")
        gateway = TcpNmea2000Gateway(ip, port)
    else:
        _LOGGER.error(f"mode {mode} not supported")
        return
    sensor = Sensor(name, hass, async_add_entities, gateway)
    await sensor.connect()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, sensor.stop)
    async_add_entities([sensor], True)

    # Start the task that updates the sensor availability every 5 minutes
    hass.loop.create_task(update_sensor_availability(hass, name))

    _LOGGER.debug(f"nmea2000 {name} setup completed.")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Retrieve configuration from entry
    name = entry.data["name"]
    _LOGGER.debug(f"Unload integration with name: {name}")

    # Clean up hass.data entries
    for key_suffix in [
        "created_sensors",
    ]:
        key = f"{name}_{key_suffix}"
        if key in hass.data:
            _LOGGER.debug(f"Removing {key} from hass.data.")
            del hass.data[key]

    _LOGGER.debug(f"Unload and cleanup for {name} completed successfully.")

    return True
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


class Sensor(SensorEntity):
    def __init__(
        self,
        name: str,
        hass: HomeAssistant,
        async_add_entities: AddEntitiesCallback,
        gateway,
    ) -> None:
        """Initialize the SensorBase."""
        self._name = name
        self.hass = hass
        self.async_add_entities = async_add_entities
        self.gateway = gateway
        self.sensors = {}
        self.gateway.set_receive_callback(self.process_message)

    async def connect(self) -> None:
        await self.gateway.connect()

    async def process_message(self, message: NMEA2000Message) -> None:
        """Process a received NMEA 2000 message."""
        _LOGGER.debug(f"Processing message: {message}")
        for field in message.fields:
            # Construct unique sensor name
            sensor_name = f"{self.name}_{message.id}_{field.id}"
            # Check for sensor existence and create/update accordingly
            sensor = self.sensors.get(field.id)
            if sensor is None:
                _LOGGER.debug(f"Creating new sensor for {sensor_name}")
                # If sensor does not exist, create and add it
                sensor = NMEA2000Sensor(
                    sensor_name,
                    field.description,
                    field.value,
                    "NMEA 2000",
                    field.unit_of_measurement,
                    message.description,
                    message.id,
                    self.name,
                )

                self.async_add_entities([sensor])
                self.sensors[field.id] = sensor
            else:
                # If sensor exists, update its state
                _LOGGER.debug(
                    f"Updating existing sensor {sensor_name} with new value: {field.value}"
                )
                sensor.set_state(field.value)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return the attributes of the entity (if any JSON present)."""
        return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return "Running"  # todo: check if gateway is running

    @callback
    def stop(self, event):
        """Close resources for the TCP connection."""
        self.gateway.close()
