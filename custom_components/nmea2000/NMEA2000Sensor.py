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
        via_device=None,
        update_frequncy_ms=0,
    ) -> None:
        """Initialize the sensor."""
        _LOGGER.info("Initializing NMEA2000Sensor: name=%s, friendly_name=%s, initial_state: %s, unit_of_measurement=%s, device_name=%s, via_device=%s, update_frequncy=%d",
                      name, friendly_name, initial_state, unit_of_measurement, device_name, via_device, update_frequncy_ms)
        self._attr_unique_id = name.lower().replace(" ", "_")
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._attr_name = friendly_name
        self._device_name = device_name
        self._attr_native_value = initial_state
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_name)},
            manufacturer="NMEA 2000",
            model=device_name,
            name=device_name,
            via_device=((DOMAIN, via_device) if via_device is not None else None))
        self._last_updated = datetime.now()
        self.update_frequncy_ms = update_frequncy_ms
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
        now = datetime.now()

        if (self.update_frequncy_ms != 0) and ((now - self._last_updated) < timedelta(milliseconds=self.update_frequncy_ms)):
            # If the update frequency is not met, bail out without any changes
            return
        self._last_updated = now
        
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
