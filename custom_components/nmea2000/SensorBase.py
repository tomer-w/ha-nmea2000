import datetime
import logging
import pprint
import binascii

from .NMEA2000Sensor import NMEA2000Sensor
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity
import nmea2000parser


_LOGGER = logging.getLogger(__name__)


class SensorBase(SensorEntity):
    def __init__(
        self, name: str, hass: HomeAssistant, async_add_entities: AddEntitiesCallback
    ) -> None:
        """Initialize the SensorBase."""
        self._name = name
        self.hass = hass
        self.async_add_entities = async_add_entities
        self.parser = nmea2000parser.get_parser()
        self.sensors = {}

    def process_frame(self, packet: bytearray) -> None:
        """Process a received packet and extract the PGN, source ID, and CAN data."""
        if len(packet) < 5:  # E8 + Frame ID (4 bytes min)
            _LOGGER.error("Invalid packet length: %s", binascii.hexlify(packet))
            return

        nmea2000Message = self.parser.process_packet(packet)
        if nmea2000Message is None:
            _LOGGER.debug(
                f"skipping packet: {binascii.hexlify(packet)}. Might be fast packet."
            )
            return

        _LOGGER.debug(f"processed nmea message: {nmea2000Message}")

        for field in nmea2000Message.fields:
            # Construct unique sensor name
            sensor_name = f"{self.name}_{self.id}_{field.id}"
            # Check for sensor existence and create/update accordingly
            if sensor_name not in self.sensors[field.id]:
                _LOGGER.debug(f"Creating new sensor for {sensor_name}")
                # If sensor does not exist, create and add it
                sensor = NMEA2000Sensor(
                    sensor_name,
                    field.description,
                    field.value,
                    "NMEA 2000",
                    field.unit_of_measurement,
                    nmea2000Message.pgn_description,
                    nmea2000Message.id,
                    self.name,
                )

                self.async_add_entities([sensor])
                self.sensors[field.id] = sensor
            else:
                # If sensor exists, update its state
                _LOGGER.debug(
                    f"Updating existing sensor {sensor_name} with new value: {field.value}"
                )
                sensor = self.sensors[field.id]
                sensor.set_state(field.value)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return the attributes of the entity (if any JSON present)."""
        return self._attributes

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
