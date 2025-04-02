# Standard Library Imports
import asyncio
import logging
import hashlib
import contextlib
from nmea2000 import NMEA2000Message, TcpNmea2000Gateway, UsbNmea2000Gateway, AsyncIOClient, FieldTypes, State

# Third-Party Library Imports

# Home Assistant Imports
from .const import DOMAIN
from .NMEA2000Sensor import NMEA2000Sensor
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import ConfigValidationError

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
    """Set up the NMEA2000 sensor platform from a config entry."""
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
        "Configuring sensor with name: %s, mode: %s, PGN Include: %s, PGN Exclude: %s",
        name,
        mode,
        pgn_include,
        pgn_exclude,
    )

    if mode == "USB":
        serial_port = entry.data[CONF_SERIAL_PORT]
        baudrate = entry.data[CONF_BAUDRATE]
        _LOGGER.info(
            "USB sensor with name: %s, serial_port: %s, baudrate: %s",
            name,
            serial_port,
            baudrate,
        )
        gateway = UsbNmea2000Gateway(serial_port, exclude_pgns=pgn_exclude, include_pgns=pgn_include)
        url = f"usb://{serial_port}"
    elif mode == "TCP":
        ip = entry.data[CONF_IP]
        port = entry.data[CONF_PORT]
        _LOGGER.info("TCP sensor with name: %s, IP: %s, port: %s", name, ip, port)
        gateway = TcpNmea2000Gateway(ip, port, exclude_pgns=pgn_exclude, include_pgns=pgn_include)
        url = f"tcp://{ip}:{port}"
    else:
        raise ConfigValidationError(f"mode {mode} not supported")

    sensor = Sensor(mode, url, name, async_add_entities, gateway)
    entry.runtime_data = sensor
    async_add_entities([sensor])
    await sensor.connect()

    _LOGGER.debug("NMEA2000 %s setup completed", name)
    return True


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
                _LOGGER.error(
                    "Invalid pgn value found: '%s' in input '%s'", value, input_str
                )

    return validated_integers


async def event_wait(evt, timeout):
    # suppress TimeoutError because we'll return False in case of timeout
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(evt.wait(), timeout)
    return evt.is_set()


class Sensor(SensorEntity):
    """Representation of a NMEA2000 sensor."""

    def __init__(
        self,
        mode: str,
        url: str,
        name: str,
        async_add_entities: AddEntitiesCallback,
        gateway: AsyncIOClient,
    ) -> None:
        """Initialize the SensorBase."""
        _LOGGER.info("Initializing Sensor: mode=%s, url=%s, name: %s", mode, url, name)
        self._device_name = name
        self._attr_name = "Status"
        self._attr_unique_id = name.lower().replace(" ", "_")
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "Gateway", name)},
            manufacturer="NMEA 2000",
            model=f"NMEA 2000 {mode} Gateway",
            name=name,
            via_device=(DOMAIN, url))
        self.async_add_entities = async_add_entities
        self.gateway = gateway
        self.sensors = {}
        self.gateway.set_receive_callback(self.receive_callback)
        self.gateway.set_status_callback(self.status_callback)
        self.stop_event = asyncio.Event()
        self._attr_native_value = "Initializing"

    async def connect(self) -> None:
        """Connect to the NMEA2000 gateway."""
        await self.gateway.connect()
        
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.stop)
        # Start the task that updates the sensor availability every 5 minutes
        self.hass.loop.create_task(self.update_sensor_availability())


    async def update_sensor_availability(self) -> None:
        """Update the availability of all sensors every 5 minutes."""
        
        while not await event_wait(self.stop_event, 300):
            _LOGGER.debug("Running update_sensor_availability for %s", self._attr_name)
            for sensor in self.sensors.values():
                sensor.update_availability()

        _LOGGER.debug("Stopping update_sensor_availability for %s", self._attr_name)

    async def status_callback(self, state: State) -> None:
        if state == State.CONNECTED:
            self._attr_native_value = "Running"
        elif state == State.DISCONNECTED:
            self._attr_native_value = "Disconnected"
        else:
            self._attr_native_value = ""
        _LOGGER.debug("Got new state: %s. sensor state will be: %s", state, self._attr_state)
        self.schedule_update_ha_state()

    async def receive_callback(self, message: NMEA2000Message) -> None:
        """Process a received NMEA 2000 message."""
        _LOGGER.debug("Processing message: %s", message)

        # BUild primary key for the sensor
        primary_key_prefix = ""
        for field in message.fields:
            if field.part_of_primary_key:
                primary_key_prefix += "_" + str(field.value)
        #Using MD% as we dont need secure hashing and speed matters.
        primary_key_prefix_hash = hashlib.md5(primary_key_prefix.encode()).hexdigest()
        sensor_name_prefix = f"{self._attr_name}_{message.id}_{primary_key_prefix_hash}_"

        for field in message.fields:
            # Skip undefined fields
            if field.type in [FieldTypes.RESERVED, FieldTypes.SPARE, FieldTypes.BINARY, FieldTypes.VARIABLE, FieldTypes.FIELD_INDEX]:
                _LOGGER.debug(
                    "Skipping field with name: %s and type: %s", field.name, field.type
                )
                continue

            # Construct unique sensor name
            sensor_name = sensor_name_prefix + field.id
            # Check for sensor existence and create/update accordingly
            sensor = self.sensors.get(field.id)
            value = field.value if field.value is not None else field.raw_value
            if sensor is None:
                _LOGGER.info("Creating new sensor for %s", sensor_name)
                # If sensor does not exist, create and add it
                sensor = NMEA2000Sensor(
                    sensor_name,
                    field.name,
                    value,
                    field.unit_of_measurement,
                    message.description,
                    self._attr_name,
                )

                self.async_add_entities([sensor])
                self.sensors[field.id] = sensor
            else:
                # If sensor exists, update its state
                _LOGGER.debug(
                    "Updating existing sensor %s with new value: %s",
                    sensor.name,
                    value,
                )
                sensor.set_state(value)

    @property
    def extra_state_attributes(self):
        """Return the attributes of the entity (if any JSON present)."""
        return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._attr_native_value 

    @callback
    def stop(self, event):
        """Close resources for the TCP connection."""
        _LOGGER.debug("Sensor %s closed", self._attr_name)
        self.stop_event.set()
        self.gateway.close()
