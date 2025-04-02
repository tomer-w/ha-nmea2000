from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# SmartSensor class representing a basic sensor entity with state
class NMEA2000Sensor(SensorEntity):
    """Representation of a NMEA2000 sensor."""
    _attr_should_poll = False

    def __init__(
        self,
        name,
        friendly_name,
        initial_state,
        unit_of_measurement=None,
        device_name=None,
        sentence_type=None,
        instance_name=None,
    ) -> None:
        """Initialize the sensor."""
        _LOGGER.info("Initializing sensor: %s with state: %s", name, initial_state)

        self._attr_unique_id = name.lower().replace(" ", "_")
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._attr_name = friendly_name
        self._attr_native_value = initial_state
        self._attr_native_unit_of_measurement = unit_of_measurement if unit_of_measurement is not None e
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN)},
            manufacturer="NMEA 2000",
            model=sentence_type,
            name=device_name,
            via_device=(DOMAIN, instance_name))
        self._last_updated = datetime.now()
        if initial_state is None or initial_state == "":
            self._available = False
            _LOGGER.info("Creating sensor: '%s' as unavailable", self._attr_name)
        else:
            self._available = True

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._attr_native_value

    @property
    def last_updated(self):
        """Return the last updated timestamp of the sensor."""
        return self._last_updated

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._available

    def update_availability(self):
        """Update the availability status of the sensor."""

        new_availability = (datetime.now() - self._last_updated) < timedelta(minutes=4)

        if self._available != new_availability:
            _LOGGER.warning("Setting sensor:'%s' as unavailable", self._attr_name)
            self._available = new_availability
            self.async_schedule_update_ha_state()

    def set_state(self, new_state):
        """Set the state of the sensor."""
        should_update = False
        self._last_updated = datetime.now()

        if new_state not in [None, "", self._attr_native_value]:
            # Since the state is valid, update the sensor's state
            self._attr_native_value = new_state
            _LOGGER.info("Setting state for sensor: '%s' to %s", self._attr_name, new_state)
            should_update = True

        if not self._available:
            self._available = True
            should_update = True
            _LOGGER.info("Setting sensor:'%s' as available", self._attr_name)

        if should_update:
            self.async_schedule_update_ha_state()
