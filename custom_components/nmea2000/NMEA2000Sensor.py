from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorStateClass

import logging

_LOGGER = logging.getLogger(__name__)


# SmartSensor class representing a basic sensor entity with state
class NMEA2000Sensor(Entity):
    """Representation of a NMEA2000 sensor."""

    def __init__(
        self,
        name,
        friendly_name,
        initial_state,
        group=None,
        unit_of_measurement=None,
        device_name=None,
        sentence_type=None,
        instance_name=None,
    ) -> None:
        """Initialize the sensor."""
        _LOGGER.info("Initializing sensor: %s with state: %s", name, initial_state)

        self._unique_id = name.lower().replace(" ", "_")
        self.entity_id = f"sensor.{self._unique_id}"
        self._name = friendly_name if friendly_name else self._unique_id
        self._state = initial_state
        self._group = group if group is not None else "Other"
        self._device_name = device_name
        self._sentence_type = sentence_type
        self._instance_name = instance_name
        self._unit_of_measurement = unit_of_measurement
        self._state_class = SensorStateClass.MEASUREMENT
        self._last_updated = datetime.now()
        if initial_state is None or initial_state == "":
            self._available = False
            _LOGGER.info("Creating sensor: '%s' as unavailable", self._name)
        else:
            self._available = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def device_info(self):
        """Return device information about this sensor."""
        return {
            "identifiers": {
                ("smart2000usb", f"{self._instance_name}_{self._device_name}")
            },
            "name": self._device_name,
            "manufacturer": self._group,
            "model": self._sentence_type,
        }

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return self._state_class

    @property
    def last_updated(self):
        """Return the last updated timestamp of the sensor."""
        return self._last_updated

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._available

    @property
    def should_poll(self) -> bool:
        """Return the polling requirement for this sensor."""
        return False

    def update_availability(self):
        """Update the availability status of the sensor."""

        new_availability = (datetime.now() - self._last_updated) < timedelta(minutes=4)

        if self._available != new_availability:
            _LOGGER.warning("Setting sensor:'%s' as unavailable", self._name)
            self._available = new_availability
            self.async_schedule_update_ha_state()

    def set_state(self, new_state):
        """Set the state of the sensor."""
        should_update = False
        self._last_updated = datetime.now()

        if new_state not in [None, "", self._state]:
            # Since the state is valid, update the sensor's state
            self._state = new_state
            _LOGGER.info("Setting state for sensor: '%s' to %s", self._name, new_state)
            should_update = True

        if not self._available:
            self._available = True
            should_update = True
            _LOGGER.info("Setting sensor:'%s' as available", self._name)

        if should_update:
            self.async_schedule_update_ha_state()
